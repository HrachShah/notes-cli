#!/usr/bin/env python3
"""Simple command-line note-taking tool with JSON storage."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

NOTES_DIR = Path.home() / ".notescli"
NOTES_FILE = NOTES_DIR / "notes.json"


def load_notes() -> dict[str, dict]:
    """Load notes from disk, returning an empty dict if none exist.

    The on-disk file is always written as a JSON object (see
    :func:`save_notes`), but the previous code returned whatever
    :func:`json.load` produced without checking the type. A hand-edited
    or partially-written file containing a list, number, or null would
    therefore crash the next :func:`add_note` call with a confusing
    ``TypeError: list indices must be integers or slices, not str``.

    Validate the root type and return an empty dict if it is not a JSON
    object. Per-entry type checks are the caller's job (see
    :func:`list_notes` and :func:`delete_note`).
    """
    if not NOTES_FILE.exists():
        return {}
    try:
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def save_notes(notes: dict[str, dict]) -> None:
    """Persist the notes dictionary to disk."""
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(notes, f, indent=2, ensure_ascii=False)


def _now() -> datetime:
    """Return the current wall-clock time.

    Wrapped in its own function so tests can monkeypatch the time source
    without touching the immutable ``datetime`` C class.
    """
    return datetime.now()


def add_note(title: str, body: str) -> None:
    """Create a new note with the given title and body.

    An empty or whitespace-only title is rejected with a non-zero exit
    code so the call site (the CLI ``add`` subcommand) can fail fast
    instead of writing a note that the user cannot identify.
    """
    title = (title or "").strip()
    body = body or ""
    if not title:
        print("Error: note title must not be empty.", file=sys.stderr)
        sys.exit(2)
    notes = load_notes()
    base_id = _now().isoformat(timespec="seconds")
    note_id = base_id
    suffix = 1
    while note_id in notes:
        note_id = f"{base_id}-{suffix}"
        suffix += 1
    notes[note_id] = {
        "title": title,
        "body": body,
        "created": note_id,
    }
    save_notes(notes)
    print(f"Note saved: {title}")


def list_notes() -> None:
    """Print all notes, newest first.

    Tolerates note entries that are missing the expected fields (e.g.
    a hand-edited ``notes.json``) or are not dicts at all; a malformed
    entry is shown as ``(untitled)`` with an empty body and the
    iteration moves on, instead of crashing the whole ``list`` call.
    """
    notes = load_notes()
    if not notes:
        print("No notes yet. Add one with: notes-cli add <title>")
        return
    for note_id, note in sorted(notes.items(), reverse=True):
        if not isinstance(note, dict):
            continue
        title = note.get("title", "(untitled)")
        body = note.get("body", "")
        created = note.get("created", note_id)
        print(f"\n[{created}] {title}")
        preview = body[:80]
        if len(body) > 80:
            preview += "..."
        print(f"  {preview}")


def delete_note(title: str) -> None:
    """Delete the first note whose title contains the given string (case-insensitive).

    The previous implementation used ``title.lower() in note["title"].lower()``
    as the match predicate without first checking whether ``title`` was empty.
    An empty needle is a substring of every string, so ``delete_note("")``
    silently deleted the first note in the store regardless of what the user
    intended. The same applied to a whitespace-only needle. Reject both
    explicitly with a non-zero exit code and a clear error message.
    """
    needle = (title or "").strip()
    if not needle:
        print("Error: delete search text must not be empty.", file=sys.stderr)
        sys.exit(2)
    notes = load_notes()
    matches = [
        (note_id, note)
        for note_id, note in notes.items()
        if isinstance(note, dict)
        and needle.lower() in (note.get("title") or "").lower()
    ]
    if not matches:
        print(f"No note found matching: {needle}")
        return
    note_id, note = matches[0]
    del notes[note_id]
    save_notes(notes)
    print(f"Deleted: {note.get('title', '(untitled)')}")


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
