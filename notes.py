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
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, IOError):
        return {}


def save_notes(notes: dict[str, dict]) -> None:
    """Persist the notes dictionary to disk."""
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(notes, f, indent=2, ensure_ascii=False)


def _coerce_text(value: object, fallback: str = "") -> str:
    if value is None:
        return fallback
    return value if isinstance(value, str) else str(value)


def _generate_note_id(notes: dict[str, dict]) -> str:
    base = datetime.now().isoformat(timespec="seconds")
    if base not in notes:
        return base
    suffix = 2
    while f"{base}-{suffix}" in notes:
        suffix += 1
    return f"{base}-{suffix}"


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
        if not isinstance(note, dict):
            print(f"\n[{note_id}] (skipped malformed note)")
            continue
        created = _coerce_text(note.get("created"), note_id)
        title = _coerce_text(note.get("title"), "(untitled)")
        body = _coerce_text(note.get("body"), "")
        print(f"\n[{created}] {title}")
        print(f"  {body[:80]}{'...' if len(body) > 80 else ''}")


def search_notes(query: str) -> None:
    """Print notes whose title or body contains the query (case-insensitive).

    Uses the same rendering as list_notes() so multi-line and missing-field
    entries (covered by the test suite for list_notes) render consistently
    here. Skips non-dict entries rather than crashing on hand-merged JSON.
    """
    notes = load_notes()
    if not notes:
        print("No notes yet. Add one with: notes-cli add <title>")
        return
    needle = query.lower()
    matches = []
    for note_id, note in sorted(notes.items(), reverse=True):
        if not isinstance(note, dict):
            continue
        title = _coerce_text(note.get("title"))
        body = _coerce_text(note.get("body"))
        if needle in title.lower() or needle in body.lower():
            matches.append((note_id, note))
    if not matches:
        print(f"No notes match: {query}")
        return
    for note_id, note in matches:
        created = _coerce_text(note.get("created"), note_id)
        title = _coerce_text(note.get("title"), "(untitled)")
        body = _coerce_text(note.get("body"), "")
        print(f"\n[{created}] {title}")
        print(f"  {body[:80]}{'...' if len(body) > 80 else ''}")


def delete_note(title: str) -> None:
    """Delete the first note whose title contains the given string (case-insensitive)."""
    notes = load_notes()
    query = title.lower()
    matches = [
        (note_id, note)
        for note_id, note in notes.items()
        if isinstance(note, dict) and query in _coerce_text(note.get("title")).lower()
    ]
    if not matches:
        print(f"No note found matching: {title}")
        return
    note_id, note = matches[0]
    del notes[note_id]
    save_notes(notes)
    print(f"Deleted: {_coerce_text(note.get('title'), note_id)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple CLI notes")
    sub = parser.add_subparsers(dest="command", required=True)

    add_p = sub.add_parser("add", help="Add a new note")
    add_p.add_argument("title", help="Note title")
    # REMAINDER so multi-word bodies don't trigger
    # 'unrecognized arguments' when the shell passes them unquoted.
    add_p.add_argument("body", nargs=argparse.REMAINDER,
                       help="Note body (rest of the line)")

    sub.add_parser("list", help="List all notes")

    search_p = sub.add_parser("search", help="Search notes by title or body")
    search_p.add_argument("query", help="Substring to search for (case-insensitive)")

    del_p = sub.add_parser("delete", help="Delete a note")
    del_p.add_argument("title", help="Title to search for and delete")

    args = parser.parse_args()

    if args.command == "add":
        # REMAINDER returns a list of tokens; re-join with single spaces
        # so `add Title push to staging` and `add Title "push to staging"`
        # both store the body verbatim. Empty remainder → empty body.
        body_tokens = args.body or []
        add_note(args.title, " ".join(body_tokens))
    elif args.command == "list":
        list_notes()
    elif args.command == "search":
        search_notes(args.query)
    elif args.command == "delete":
        delete_note(args.title)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
