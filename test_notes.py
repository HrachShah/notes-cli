"""Tests for notes-cli."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import notes


def _isolated_notes(tmp_path: Path):
    """Redirect notes.py at a tmp NOTES_FILE and clear the in-module cache."""
    notes_file = tmp_path / "notes.json"
    notes_module = notes
    # Reset the module-level reference for the duration of the test.
    saved = notes_module.NOTES_FILE
    notes_module.NOTES_FILE = notes_file
    return notes_module, saved


def test_add_note_preserves_note_added_in_same_second(tmp_path: Path) -> None:
    """Two notes created in the same second must both be stored."""
    notes_mod, saved = _isolated_notes(tmp_path)
    try:
        notes_mod.add_note("first", "body1")
        notes_mod.add_note("second", "body2")
        stored = notes_mod.load_notes()
        assert len(stored) == 2
        titles = {n["title"] for n in stored.values()}
        assert titles == {"first", "second"}
    finally:
        notes_mod.NOTES_FILE = saved


def test_add_note_uses_distinct_ids_for_same_second(tmp_path: Path) -> None:
    """The keys used to store the two notes must be different."""
    notes_mod, saved = _isolated_notes(tmp_path)
    try:
        notes_mod.add_note("a", "x")
        notes_mod.add_note("b", "y")
        ids = list(notes_mod.load_notes().keys())
        assert len(ids) == 2
        assert ids[0] != ids[1]
    finally:
        notes_mod.NOTES_FILE = saved


def test_list_notes_handles_many_same_second_adds(tmp_path: Path) -> None:
    """list_notes must print every note even when many share a timestamp prefix."""
    notes_mod, saved = _isolated_notes(tmp_path)
    try:
        for i in range(5):
            notes_mod.add_note(f"n{i}", f"body{i}")
        assert len(notes_mod.load_notes()) == 5
    finally:
        notes_mod.NOTES_FILE = saved


def test_add_note_does_not_overwrite_existing_note(tmp_path: Path) -> None:
    """Re-using a pre-existing id (e.g. a hand-imported notes file) must not
    silently clobber the existing note.
    """
    notes_mod, saved = _isolated_notes(tmp_path)
    try:
        existing_id = "2026-01-01T00:00:00.000000"
        notes_mod.save_notes({existing_id: {"title": "old", "body": "b", "created": existing_id}})

        # Force the clock so the auto-generated id collides with the existing one.
        class _FixedDatetime:
            @classmethod
            def now(cls, tz=None):  # noqa: D401 - mimic datetime.now signature
                from datetime import datetime
                return datetime(2026, 1, 1, 0, 0, 0, 0)

        import datetime as _dt
        notes_mod.datetime = _FixedDatetime  # type: ignore[attr-defined]
        try:
            notes_mod.add_note("new", "n")
        finally:
            notes_mod.datetime = _dt.datetime  # type: ignore[attr-defined]

        stored = notes_mod.load_notes()
        assert len(stored) == 2
        titles = {n["title"] for n in stored.values()}
        assert titles == {"old", "new"}
    finally:
        notes_mod.NOTES_FILE = saved


def test_delete_note_skips_non_dict_entries(tmp_path: Path) -> None:
    """A stray non-dict entry in the notes file must not crash delete_note.

    list_notes already tolerates this case; the matching guard the file's
    own comment promised for delete_note was missing.
    """
    notes_mod, saved = _isolated_notes(tmp_path)
    try:
        notes_mod.save_notes({
            "leak": "this is a stray string, not a note dict",
            "2026-01-01T00:00:00.000000": {
                "title": "real note", "body": "hi", "created": "2026-01-01T00:00:00.000000",
            },
        })
        notes_mod.delete_note("real note")
        stored = notes_mod.load_notes()
        assert "leak" in stored
        assert len(stored) == 1
    finally:
        notes_mod.NOTES_FILE = saved


def test_delete_note_handles_non_string_title(tmp_path: Path) -> None:
    """A note whose stored title is a non-string must not crash delete_note."""
    notes_mod, saved = _isolated_notes(tmp_path)
    try:
        notes_mod.save_notes({
            "weird": {"title": 42, "body": "b", "created": "x"},
            "2026-01-01T00:00:00.000000": {
                "title": "real", "body": "hi", "created": "2026-01-01T00:00:00.000000",
            },
        })
        notes_mod.delete_note("real")
        stored = notes_mod.load_notes()
        assert "weird" in stored
        assert "2026-01-01T00:00:00.000000" not in stored
    finally:
        notes_mod.NOTES_FILE = saved