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
    try:
        with open(NOTES_FILE, "w", encoding="utf-8") as f:
            json.dump(notes, f, indent=2, ensure_ascii=False)
    except OSError as exc:
        raise OSError(f"Failed to write notes to {NOTES_FILE}: {exc}") from exc


def add_note(title: str, body: str) -> None:
    """Create a new note with the given title and body."""
    try:
        notes = load_notes()
        note_id = datetime.now().isoformat(timespec="seconds")
        notes[note_id] = {
            "title": title,
            "body": body,
            "created": note_id,
        }
        save_notes(notes)
        print(f"Note saved: {title}")
    except OSError as exc:
        print(f"Failed to save note: {exc}")
        sys.exit(1)


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
    try:
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
    except OSError as exc:
        print(f"Failed to delete note: {exc}")
        sys.exit(1)


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
