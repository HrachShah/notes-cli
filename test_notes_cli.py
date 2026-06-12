"""End-to-end tests for notes.py corruption tolerance.

These don't import pytest so they run with `python3 test_notes_cli.py`. They
re-import notes.py after monkey-patching the storage path into a fresh
tempdir so each test is independent.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

# Make notes importable as a module without running main()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import notes  # noqa: E402


def _with_temp_notes_dir(test_method):
    """Decorator that monkey-patches notes.NOTES_DIR/NOTES_FILE per test."""
    def wrapped(self):
        with tempfile.TemporaryDirectory() as d:
            notes.NOTES_DIR = Path(d)
            notes.NOTES_FILE = Path(d) / "notes.json"
            test_method(self)
    return wrapped


class ListNotesCorruptionTolerance(unittest.TestCase):
    @_with_temp_notes_dir
    def test_list_notes_handles_non_dict_entries(self):
        Path(notes.NOTES_FILE).write_text(json.dumps({
            "2024-01-01": None,
            "2024-02-01": "a string",
            "2024-03-01": 42,
        }))
        # The previous code crashed with TypeError on the first row.
        notes.list_notes()  # Should not raise

    @_with_temp_notes_dir
    def test_list_notes_handles_missing_title(self):
        Path(notes.NOTES_FILE).write_text(json.dumps({
            "2024": {"body": "just a body", "created": "2024"},
        }))
        # The previous code crashed with KeyError: 'title'.
        notes.list_notes()

    @_with_temp_notes_dir
    def test_list_notes_handles_missing_body(self):
        Path(notes.NOTES_FILE).write_text(json.dumps({
            "2024": {"title": "no body", "created": "2024"},
        }))
        # The previous code crashed with KeyError: 'body'.
        notes.list_notes()

    @_with_temp_notes_dir
    def test_list_notes_handles_none_body(self):
        Path(notes.NOTES_FILE).write_text(json.dumps({
            "2024": {"title": "none body", "body": None, "created": "2024"},
        }))
        # The previous code crashed with TypeError on None[:80].
        notes.list_notes()

    @_with_temp_notes_dir
    def test_list_notes_handles_int_body(self):
        Path(notes.NOTES_FILE).write_text(json.dumps({
            "2024": {"title": "int body", "body": 42, "created": "2024"},
        }))
        # The previous code crashed with TypeError on int[:80].
        notes.list_notes()

    @_with_temp_notes_dir
    def test_list_notes_handles_missing_file(self):
        notes.NOTES_FILE.unlink(missing_ok=True)
        # Should print the "no notes" message and return.
        notes.list_notes()

    @_with_temp_notes_dir
    def test_list_notes_handles_empty_file(self):
        Path(notes.NOTES_FILE).write_text("{}")
        notes.list_notes()

    @_with_temp_notes_dir
    def test_list_notes_happy_path_unchanged(self):
        notes.add_note("Hello", "world")
        notes.add_note("Multi word", "another body")
        notes.list_notes()


class AddAndDeleteStillWork(unittest.TestCase):
    @_with_temp_notes_dir
    def test_add_then_list(self):
        notes.add_note("Title", "body")
        notes.add_note("Another", "another body")
        notes.list_notes()

    @_with_temp_notes_dir
    def test_delete_by_partial_title(self):
        notes.add_note("Hello world", "body")
        notes.delete_note("hello")
        notes.list_notes()

    @_with_temp_notes_dir
    def test_delete_by_case_insensitive(self):
        notes.add_note("Hello world", "body")
        notes.delete_note("HELLO")
        notes.list_notes()


if __name__ == "__main__":
    unittest.main()
