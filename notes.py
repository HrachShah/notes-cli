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
    """Print all notes, newest first.

    Tolerant of stray non-dict values in the notes file. A hand-edited
    file or a partially-recovered write can contain a bare string, list,
    int, or float where a note dict is expected; reading the title with
    note["title"] on any of those would raise TypeError and hide every
    valid note. Skip the bad value and print a one-line marker instead.
    """
    notes = load_notes()
    if not notes:
        print("No notes yet. Add one with: notes-cli add <title>")
        return
    for note_id, note in sorted(notes.items(), reverse=True):
        if not isinstance(note, dict):
            print(f"\n[{note_id}] (skipped: not a note object)")
            continue
        created = note.get("created", note_id)
        title = note.get("title", "(untitled)")
        body = note.get("body", "")
        if not isinstance(title, str):
            title = str(title)
        if not isinstance(body, str):
            body = str(body)
        print(f"\n[{created}] {title}")
        print(f"  {body[:80]}{'...' if len(body) > 80 else ''}")


def delete_note(title: str) -> None:
    """Delete the first note whose title contains the given string (case-insensitive).

    Skips non-dict entries (stray strings, lists, ints in the JSON file
    from a hand-edit or partial recovery) and notes whose title is
    missing or not a string, so a corrupted notes file does not crash
    the delete command.
    """
    notes = load_notes()
    needle = title.lower()
    matches = [
        (note_id, note)
        for note_id, note in notes.items()
        if isinstance(note, dict)
        and isinstance(note.get("title"), str)
        and needle in note["title"].lower()
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
