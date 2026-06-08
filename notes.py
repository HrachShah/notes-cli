#!/usr/bin/env python3
"""Simple command-line note-taking tool with JSON storage."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

NOTES_DIR = Path.home() / ".notescli"
NOTES_FILE = NOTES_DIR / "notes.json"


def _shape_note(value: object) -> dict[str, str] | None:
    """Return a validated note dict, or None if the parsed value is malformed.

    The notes.json file is plain JSON and users can edit it by hand, run an
    older version of this tool that wrote a different shape, or have a write
    truncated by a full disk. Returning None for invalid entries lets the
    list and delete code paths skip them with a warning instead of crashing
    the whole command.
    """
    if not isinstance(value, dict):
        return None
    title = value.get("title")
    body = value.get("body")
    created = value.get("created")
    if not isinstance(title, str) or not isinstance(body, str) or not isinstance(created, str):
        return None
    return {"title": title, "body": body, "created": created}


def load_notes() -> dict[str, dict]:
    """Load notes from disk, returning an empty dict if none exist."""
    if not NOTES_FILE.exists():
        return {}
    try:
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_notes(notes: dict[str, dict]) -> None:
    """Persist the notes dictionary to disk."""
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(notes, f, indent=2, ensure_ascii=False)


def add_note(title: str, body: str) -> None:
    """Create a new note with the given title and body."""
    notes = load_notes()
    note_id = datetime.now().isoformat(timespec="seconds")
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
    if not isinstance(notes, dict):
        print(
            f"Warning: {NOTES_FILE} did not contain a JSON object; "
            "treating it as empty.",
            file=sys.stderr,
        )
        return
    rendered = 0
    for note_id, raw in notes.items():
        shaped = _shape_note(raw)
        if shaped is None:
            print(
                f"Warning: skipping note {note_id!r} with unexpected shape",
                file=sys.stderr,
            )
            continue
        rendered += 1
        print(f"\n[{shaped['created']}] {shaped['title']}")
        body = shaped["body"]
        print(f"  {body[:80]}{'...' if len(body) > 80 else ''}")
    if rendered == 0:
        if notes:
            print(
                "No valid notes to display. Run 'notes-cli add <title> <body>' to start fresh."
            )
        else:
            print("No notes yet. Add one with: notes-cli add <title>")


def delete_note(title: str) -> None:
    """Delete the first note whose title contains the given string (case-insensitive)."""
    notes = load_notes()
    if not isinstance(notes, dict):
        print(f"No note found matching: {title}")
        return
    match_id: str | None = None
    match_note: dict[str, str] | None = None
    for note_id, raw in notes.items():
        shaped = _shape_note(raw)
        if shaped is None:
            continue
        if title.lower() in shaped["title"].lower():
            match_id, match_note = note_id, shaped
            break
    if match_id is None or match_note is None:
        print(f"No note found matching: {title}")
        return
    del notes[match_id]
    save_notes(notes)
    print(f"Deleted: {match_note['title']}")


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
