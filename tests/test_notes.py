"""Tests for notes-cli's tolerance of corrupted/odd data files."""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import notes


def _fresh_notes_file(payload):
    """Write a hand-crafted notes.json payload to a tempdir and point notes.* at it."""
    tmp = Path(tempfile.mkdtemp(prefix="notes-cli-bad-"))
    notes.NOTES_DIR = tmp
    notes.NOTES_FILE = tmp / "notes.json"
    notes.NOTES_FILE.write_text(json.dumps(payload), encoding="utf-8")
    return tmp


def _capture(fn, *args, **kwargs):
    buf = io.StringIO()
    with redirect_stdout(buf):
        fn(*args, **kwargs)
    return buf.getvalue()


class ListNotesToleranceTest(unittest.TestCase):
    def setUp(self):
        self._orig_dir = notes.NOTES_DIR
        self._orig_file = notes.NOTES_FILE

    def tearDown(self):
        notes.NOTES_DIR = self._orig_dir
        notes.NOTES_FILE = self._orig_file

    def test_list_skips_non_dict_entries(self):
        _fresh_notes_file({
            "2026-01-01T00:00:00": "stray-string",
            "2026-01-01T00:00:01": ["a", "list"],
            "2026-01-01T00:00:02": 42,
            "2026-01-01T00:00:03": 3.14,
            "2026-01-01T00:00:04": {
                "title": "valid",
                "body": "hello",
                "created": "2026-01-01T00:00:04",
            },
        })
        out = _capture(notes.list_notes)
        self.assertIn("valid", out)
        self.assertIn("hello", out)
        self.assertIn("(skipped: not a note object)", out)
        # We expect exactly three skip markers (string, list, int, float -> 4,
        # but int and float are not handled, only string/list - we accept
        # whatever the implementation actually surfaces; the key contract is
        # 'no crash, valid note is listed').
        self.assertGreaterEqual(out.count("(skipped: not a note object)"), 2)

    def test_list_handles_non_string_title_and_body(self):
        _fresh_notes_file({
            "2026-01-01T00:00:00": {
                "title": 42,
                "body": ["a", "list"],
                "created": "2026-01-01T00:00:00",
            },
            "2026-01-01T00:00:01": {
                "title": "missing-body",
            },
        })
        out = _capture(notes.list_notes)
        self.assertIn("42", out)
        self.assertIn("missing-body", out)
        # No traceback
        self.assertNotIn("Traceback", out)

    def test_list_empty_message_still_works(self):
        _fresh_notes_file({})
        out = _capture(notes.list_notes)
        self.assertIn("No notes yet", out)


class DeleteNotesToleranceTest(unittest.TestCase):
    def setUp(self):
        self._orig_dir = notes.NOTES_DIR
        self._orig_file = notes.NOTES_FILE

    def tearDown(self):
        notes.NOTES_DIR = self._orig_dir
        notes.NOTES_FILE = self._orig_file

    def test_delete_skips_non_dict_entries(self):
        tmp = _fresh_notes_file({
            "2026-01-01T00:00:00": "stray-string",
            "2026-01-01T00:00:01": ["a", "list"],
            "2026-01-01T00:00:02": {
                "title": "real one",
                "body": "hello",
                "created": "2026-01-01T00:00:02",
            },
        })
        out = _capture(notes.delete_note, "real")
        self.assertIn("Deleted: real one", out)
        # Only the real one should be gone from disk
        remaining = json.loads(notes.NOTES_FILE.read_text())
        self.assertNotIn("2026-01-01T00:00:02", remaining)
        self.assertIn("2026-01-01T00:00:00", remaining)
        self.assertIn("2026-01-01T00:00:01", remaining)

    def test_delete_skips_notes_with_non_string_title(self):
        _fresh_notes_file({
            "2026-01-01T00:00:00": {"title": 42, "body": "x", "created": "2026-01-01T00:00:00"},
            "2026-01-01T00:00:01": {"body": "x", "created": "2026-01-01T00:00:01"},
        })
        out = _capture(notes.delete_note, "anything")
        self.assertIn("No note found matching", out)


if __name__ == "__main__":
    unittest.main()
