#!/usr/bin/env python3
"""Simple command-line note-taking tool with JSON storage."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

NOTES_DIR = Path.home() / ".notescli"
NOTES_FILE = NOTES_DIR / "notes.json"


def _generate_note_id(notes: dict) -> str:
    """Generate a unique note id based on the current time.

    The id includes microsecond resolution to make collisions unlikely under
    normal usage, and a short incrementing hex suffix is appended if a
    generated id still matches an existing key (which can happen when
    multiple notes are added in the same microsecond, e.g. inside a tight
    loop or in tests).
    """
    base = datetime.now().isoformat(timespec="microseconds")
    note_id = base
    suffix = 0
    while note_id in notes:
        suffix += 1
        # Eight hex chars per collision gives 2^32 unique retries before a
        # same-microsecond duplicate is even plausible.
        note_id = f"{base}-{suffix:08x}"
    return note_id


def load_notes() -> dict[str, dict]:
    """Load notes from disk, returning an empty dict if none exist."""
    if not NOTES_FILE.exists():
        return {}
    try:
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        _quarantine_corrupted_notes_file()
        return {}
    except IOError:
        return {}


def save_notes(notes: dict[str, dict]) -> None:
    """Persist the notes dictionary to disk."""
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(notes, f, indent=2, ensure_ascii=False)


def _quarantine_corrupted_notes_file() -> None:
    """Move an unreadable notes file out of the way before overwriting it.

    Called from load_notes() when the existing notes.json cannot be parsed.
    The bad file is renamed to notes.json.corrupt-<timestamp> so the user's
    prior data is preserved on disk for inspection, and a warning is printed
    pointing at the new path. The next save_notes() call will then create a
    fresh notes.json without destroying the original content.
    """
    import shutil
    from datetime import datetime as _dt
    stamp = _dt.now().strftime("%Y%m%d-%H%M%S")
    backup_path = NOTES_FILE.with_name(f"{NOTES_FILE.name}.corrupt-{stamp}")
    try:
        shutil.move(str(NOTES_FILE), str(backup_path))
    except OSError as e:
        print(f"warning: notes file is unreadable and could not be backed up: {e}")
        return
    print(
        f"warning: notes file at {NOTES_FILE} could not be parsed; "
        f"the original contents have been preserved at {backup_path}"
    )


def add_note(title: str, body: str) -> None:
    """Create a new note with the given title and body."""
    notes = load_notes()
    note_id = _generate_note_id(notes)
    notes[note_id] = {
        "title": title,
        "body": body,
        "created": note_id,
    }
    save_notes(notes)
    print(f"Note saved: {title}")


def list_notes() -> None:
    """Print all notes, newest first."""
    notes = load_notes()
    if not notes:
        print("No notes yet. Add one with: notes-cli add <title>")
        return
    for note_id, note in sorted(notes.items(), reverse=True):
        created = note["created"]
        print(f"\n[{created}] {note['title']}")
        print(f"  {note['body'][:80]}{'...' if len(note['body']) > 80 else ''}")


def delete_note(title: str) -> None:
    """Delete the first note whose title contains the given string (case-insensitive)."""
    notes = load_notes()
    matches = [
        (note_id, note)
        for note_id, note in notes.items()
        if title.lower() in note["title"].lower()
    ]
    if not matches:
        print(f"No note found matching: {title}")
        return
    note_id, note = matches[0]
    del notes[note_id]
    save_notes(notes)
    print(f"Deleted: {note['title']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple CLI notes")
    sub = parser.add_subparsers(dest="command", required=True)

    add_p = sub.add_parser("add", help="Add a new note")
    add_p.add_argument("title", help="Note title")
    add_p.add_argument("body", help="Note body (rest of the line)")

    sub.add_parser("list", help="List all notes")

    del_p = sub.add_parser("delete", help="Delete a note")
    del_p.add_argument("title", help="Title to search for and delete")

    args = parser.parse_args()

    if args.command == "add":
        add_note(args.title, args.body)
    elif args.command == "list":
        list_notes()
    elif args.command == "delete":
        delete_note(args.title)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
