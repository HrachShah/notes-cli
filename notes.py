#!/usr/bin/env python3
"""Simple command-line note-taking tool with JSON storage."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

NOTES_DIR = Path.home() / ".notescli"
NOTES_FILE = NOTES_DIR / "notes.json"


def _generate_note_id(notes: dict[str, dict], now=None) -> str:
    """Return a note id that does not collide with any key already in `notes`.

    Uses a microsecond-precision ISO timestamp and appends a `-N` suffix only
    when the base timestamp is already taken, so a burst of notes added in the
    same microsecond still get unique ids (the previous code used
    `timespec="seconds"`, so two notes added in the same second silently
    overwrote each other in the JSON store).

    `now` is an optional zero-arg callable returning a datetime; it defaults to
    `datetime.now`. Exposed for tests.
    """
    if now is None:
        now = datetime.now
    base = now().isoformat(timespec="microseconds")
    candidate = base
    suffix = 1
    while candidate in notes:
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def load_notes() -> dict[str, dict]:
    """Load notes from disk, returning an empty dict if none exist.

    The on-disk file is always written as a JSON object (see
    :func:`save_notes`), but the previous code returned whatever
    :func:`json.load` produced without checking the type. Three real-world
    failure modes followed:

    1. A user (or a migration tool) wrote ``[]`` (an empty list) into the
       file, e.g. by running ``echo '[]' > ~/.notescli/notes.json`` to
       reset their notes. The next :func:`add_note` call then crashed
       with ``TypeError: list indices must be integers or slices, not str``
       on the line ``notes[note_id] = {...}``.
    2. A user wrote ``null``, ``42``, or a bare string to the file (a
       common hand-edit mistake), and the next add/delete call crashed
       with a similarly confusing TypeError.
    3. A partial write (e.g. from a power loss while :func:`save_notes`
       was in the middle of writing) left the file containing an
       incomplete JSON value such as ``{"abc": {"title":`` —
       :func:`json.load` raises ``JSONDecodeError`` which was already
       caught, but a completed-but-wrong-type value (e.g. ``{"abc": 42}``)
       returned a dict that :func:`add_note` happily wrote the new key
       into, only for the next read to crash when it tried to do
       ``note["title"]``.

    Validate the root type and return an empty dict if it is not a JSON
    object. This is consistent with the contract documented in the type
    hint and means callers never have to handle a list/number/None.
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
    try:
        with open(NOTES_FILE, "w", encoding="utf-8") as f:
            json.dump(notes, f, indent=2, ensure_ascii=False)
    except (IOError, UnicodeEncodeError) as e:
        print(f"Failed to save notes: {e}", file=sys.stderr)
        sys.exit(1)


def add_note(title: str, body: str, now=None) -> None:
    """Create a new note with the given title and body.

    `now` is an optional callable that returns a datetime; it defaults to
    `datetime.now`. Tests use it to force the same timestamp across multiple
    calls and verify the collision-handling path in `_generate_note_id`.
    """
    if now is None:
        now = datetime.now
    notes = load_notes()
    note_id = _generate_note_id(notes, now=now)
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
    if not title:
        print("Error: title is empty")
        return
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