#!/usr/bin/env python3
"""Simple command-line note-taking tool with JSON storage."""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

NOTES_DIR = Path.home() / ".notescli"
NOTES_FILE = NOTES_DIR / "notes.json"


def _new_note_id(notes: dict[str, dict]) -> str:
    """Return a unique note id, appending a numeric suffix on collision.

    ``datetime.now().isoformat(timespec="seconds")`` only has one-second
    resolution, so two ``notes add`` calls issued in the same second used
    to silently overwrite each other. Append ``-2``, ``-3`` ... until the
    id is free.
    """
    base = datetime.now().isoformat(timespec="seconds")
    candidate = base
    suffix = 2
    while candidate in notes:
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def load_notes() -> dict[str, dict]:
    """Load notes from disk, returning an empty dict if none exist."""
    if not NOTES_FILE.exists():
        return {}
    try:
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as exc:
        print(f"warning: failed to read {NOTES_FILE}: {exc}", file=sys.stderr)
        return {}


def save_notes(notes: dict[str, dict]) -> None:
    """Persist the notes dictionary to disk atomically.

    Writes to a sibling temp file in the same directory and then
    ``os.replace``s it onto the target path. If the process dies
    mid-write, the previous notes.json is still intact.
    """
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=".notes.", suffix=".json.tmp", dir=NOTES_DIR
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(notes, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, NOTES_FILE)
    except Exception:
        # Best-effort cleanup of the orphan temp file on failure.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def add_note(title: str, body: str) -> None:
    """Create a new note with the given title and body."""
    notes = load_notes()
    note_id = _new_note_id(notes)
    notes[note_id] = {
        "title": title,
        "body": body,
        "created": note_id,
    }
    save_notes(notes)
    print(f"Note saved: {title}")


def _is_valid_note(note: object) -> bool:
    """A note row is a dict with at least title/body/created string fields.

    Older versions and external edits can leave non-dict entries in the
    file; ``list_notes``/``delete_note`` should ignore those rather than
    crashing with ``TypeError: string indices must be integers``.
    """
    if not isinstance(note, dict):
        return False
    return all(isinstance(note.get(k), str) for k in ("title", "body", "created"))


def list_notes() -> None:
    """Print all notes, newest first."""
    notes = load_notes()
    valid = {nid: note for nid, note in notes.items() if _is_valid_note(note)}
    skipped = len(notes) - len(valid)
    if skipped:
        print(
            f"warning: skipped {skipped} malformed note row(s)",
            file=sys.stderr,
        )
    if not valid:
        print("No notes yet. Add one with: notes-cli add <title>")
        return
    for note_id, note in sorted(valid.items(), reverse=True):
        body = note["body"]
        print(f"\n[{note['created']}] {note['title']}")
        print(
            f"  {body[:80]}{'...' if len(body) > 80 else ''}"
        )


def delete_note(title: str) -> None:
    """Delete the first note whose title contains the given string (case-insensitive).

    An empty or whitespace-only ``title`` is rejected: the substring match
    ``"".lower() in note["title"].lower()`` is always true, so without this
    guard an empty argument would silently delete the first note. Print a
    clear error and leave the store intact instead.
    """
    if not title or not title.strip():
        print("error: cannot delete with an empty title", file=sys.stderr)
        return
    notes = load_notes()
    matches = [
        (note_id, note)
        for note_id, note in notes.items()
        if _is_valid_note(note)
        and title.lower() in note["title"].lower()
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
