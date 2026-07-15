#!/usr/bin/env python3
"""Simple command-line note-taking tool with JSON storage."""

import argparse
import json
import os
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
            notes = json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}
    return notes if isinstance(notes, dict) else {}


def save_notes(notes: dict[str, dict]) -> None:
    """Persist the notes dictionary to disk without exposing partial JSON."""
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    temporary_file = NOTES_FILE.with_name(f".{NOTES_FILE.name}.tmp")
    try:
        with open(temporary_file, "w", encoding="utf-8") as f:
            json.dump(notes, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary_file, NOTES_FILE)
    finally:
        temporary_file.unlink(missing_ok=True)


def _new_note_id(existing_ids: set[str] | None = None) -> str:
    """Return a timestamp-based id that does not collide with stored notes."""
    existing_ids = existing_ids or set()
    base = datetime.now().isoformat(timespec="seconds")
    candidate = base
    suffix = 1
    while candidate in existing_ids:
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def add_note(title: str, body: str) -> None:
    """Create a new note with the given title and body."""
    notes = load_notes()
    note_id = _new_note_id(set(notes))
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
        if not isinstance(note, dict):
            print(f"Warning: skipping non-dict entry for note {note_id}")
            continue
        created = note.get("created", "unknown")
        title = note.get("title", "Untitled")
        body = note.get("body", "")
        print(f"\n[{created}] {title}")
        print(f"  {body[:80]}{'...' if len(body) > 80 else ''}")


def delete_note(title: str) -> None:
    """Delete the first note whose title contains the given string (case-insensitive)."""
    notes = load_notes()
    target = title.casefold()
    matches = [
        (note_id, note)
        for note_id, note in notes.items()
        if isinstance(note, dict) and isinstance(note.get("title"), str)
        and target in note["title"].casefold()
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
