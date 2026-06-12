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


def _format_note_body(body: object) -> str:
    """Render a note body that may be missing or stored under a non-string type.

    Hand-edited notes files (or older notes written before the body field was
    mandatory) can leave the body as None, an int, or a list. The previous
    list_notes() crashed with TypeError on every one of those because
    `note["body"][:80]` requires a string slice and `len(note["body"]) > 80`
    is a comparison that raises on a non-container. Coerce to a safe
    preview here so the rest of the row can render.
    """
    if isinstance(body, str):
        return body
    if body is None:
        return ""
    return str(body)


def list_notes() -> None:
    """Print all notes, newest first, tolerating hand-edited entries."""
    notes = load_notes()
    if not notes:
        print("No notes yet. Add one with: notes-cli add <title>")
        return
    for note_id, note in sorted(notes.items(), reverse=True):
        if not isinstance(note, dict):
            # A hand-merge that left a non-dict in the file (a bare string,
            # number, or null) used to crash list_notes() with TypeError on
            # the very first row. Print a placeholder so the rest of the
            # file still gets listed.
            print(f"\n[{note_id}] (skipped: not a dict)")
            continue
        created = note.get("created", note_id)
        title = note.get("title", "(untitled)")
        body = _format_note_body(note.get("body"))
        preview = body[:80]
        suffix = "..." if len(body) > 80 else ""
        print(f"\n[{created}] {title}")
        print(f"  {preview}{suffix}")


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
    add_p.add_argument("body", nargs=argparse.REMAINDER, help="Note body (one or more words; joins into a single body)")

    sub.add_parser("list", help="List all notes")

    del_p = sub.add_parser("delete", help="Delete a note")
    del_p.add_argument("title", help="Title to search for and delete")

    args = parser.parse_args()

    if args.command == "add":
        add_note(args.title, " ".join(args.body) if args.body else "")
    elif args.command == "list":
        list_notes()
    elif args.command == "delete":
        delete_note(args.title)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
