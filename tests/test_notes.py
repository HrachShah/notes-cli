"""Tests for notes-cli."""

import importlib
import sys
from pathlib import Path

import pytest


@pytest.fixture
def isolated_notes(tmp_path, monkeypatch):
    """Point NOTES_DIR/NOTES_FILE at a tmp directory so tests don't touch the real store."""
    notes_dir = tmp_path / ".notescli"
    notes_file = notes_dir / "notes.json"
    # Drop any cached module so NOTES_DIR/NOTES_FILE bindings recompute
    sys.modules.pop("notes", None)
    notes = importlib.import_module("notes")
    monkeypatch.setattr(notes, "NOTES_DIR", notes_dir)
    monkeypatch.setattr(notes, "NOTES_FILE", notes_file)
    return notes, notes_file


def test_add_then_list_persists(isolated_notes):
    notes, notes_file = isolated_notes
    notes.add_note("hello", "world")
    assert notes_file.exists()
    notes.add_note("second", "note")
    # Both entries should exist with distinct IDs (no overwrite).
    raw = __import__("json").loads(notes_file.read_text())
    assert len(raw) == 2
    assert {"hello", "second"} == {v["title"] for v in raw.values()}


def test_add_in_same_second_does_not_overwrite(isolated_notes):
    """Two notes added back-to-back must keep both — the old code used
    second-resolution datetimes as the key and silently overwrote."""
    notes, notes_file = isolated_notes
    notes.add_note("first", "a")
    notes.add_note("second", "b")
    notes.add_note("third", "c")
    raw = __import__("json").loads(notes_file.read_text())
    assert len(raw) == 3


def test_list_skips_malformed_rows(isolated_notes):
    """A row whose value is not a dict (legacy/corrupted data) must be
    skipped with a warning, not crash list_notes."""
    import json

    notes, notes_file = isolated_notes
    notes_file.parent.mkdir(parents=True, exist_ok=True)
    notes_file.write_text(
        json.dumps(
            {
                "2024-01-01": "this is a string, not a dict",
                "2024-02-01": {
                    "title": "real note",
                    "body": "x",
                    "created": "2024-02-01",
                },
            }
        )
    )
    notes.list_notes()  # must not raise


def test_save_notes_is_atomic(isolated_notes):
    """save_notes writes via a temp file in the same dir and replaces, so
    a crash mid-write can't leave a half-written notes.json."""
    notes, notes_file = isolated_notes
    notes.save_notes({"k": {"title": "t", "body": "b", "created": "k"}})
    leftover = [
        p.name for p in notes_file.parent.iterdir() if p.name.startswith(".notes.json.")
    ]
    assert leftover == [], f"orphan temp file left behind: {leftover}"


def test_delete_removes_matching_note(isolated_notes):
    notes, notes_file = isolated_notes
    notes.add_note("Shopping", "milk")
    notes.add_note("Work", "release")
    notes.delete_note("shopping")
    raw = __import__("json").loads(notes_file.read_text())
    assert len(raw) == 1
    assert "Work" in {v["title"] for v in raw.values()}


def test_delete_with_empty_title_does_not_remove_any_note(isolated_notes, capsys):
    notes, notes_file = isolated_notes
    notes.add_note("Alpha", "1")
    notes.add_note("Beta", "2")
    notes.delete_note("")
    raw = __import__("json").loads(notes_file.read_text())
    assert len(raw) == 2, "empty title must not delete any note"
    captured = capsys.readouterr()
    assert "empty" in captured.err.lower()


def test_delete_with_whitespace_title_does_not_remove_any_note(isolated_notes, capsys):
    notes, notes_file = isolated_notes
    notes.add_note("Alpha", "1")
    notes.delete_note("   \t  ")
    raw = __import__("json").loads(notes_file.read_text())
    assert len(raw) == 1, "whitespace-only title must not delete any note"
    captured = capsys.readouterr()
    assert "empty" in captured.err.lower()


def test_delete_substring_still_works(isolated_notes):
    notes, notes_file = isolated_notes
    notes.add_note("Grocery shopping", "milk")
    notes.add_note("Work tasks", "release")
    notes.delete_note("shop")
    raw = __import__("json").loads(notes_file.read_text())
    assert len(raw) == 1
    assert "Work tasks" in {v["title"] for v in raw.values()}