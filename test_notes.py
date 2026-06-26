"""Tests for notes CLI module."""

import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


def _import_notes_module(tmp_home: Path):
    """Import a fresh copy of notes.py with HOME pointed at a temp dir."""
    spec = importlib.util.spec_from_file_location("notes_under_test", Path(__file__).parent / "notes.py")
    notes = importlib.util.module_from_spec(spec)
    with mock.patch.object(Path, "home", lambda: tmp_home):
        spec.loader.exec_module(notes)
    return notes


class TestAddNoteIdUniqueness(unittest.TestCase):
    """Regression: two notes saved within the same second used to share an ID and silently overwrite each other."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_home = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_three_notes_same_second_are_all_persisted(self):
        notes = _import_notes_module(self.tmp_home)
        for title in ("Quick one", "Quick two", "Quick three"):
            notes.add_note(title, f"body of {title}")

        data = json.loads((self.tmp_home / ".notescli" / "notes.json").read_text("utf-8"))
        self.assertEqual(len(data), 3, "all three notes should be persisted")
        self.assertEqual(
            {n["title"] for n in data.values()},
            {"Quick one", "Quick two", "Quick three"},
        )

    def test_note_ids_are_unique_even_when_created_field_matches(self):
        notes = _import_notes_module(self.tmp_home)
        notes.add_note("a", "first")
        notes.add_note("a", "second")
        notes.add_note("a", "third")

        data = json.loads((self.tmp_home / ".notescli" / "notes.json").read_text("utf-8"))
        self.assertEqual(len(data), 3)
        self.assertEqual(len(set(data.keys())), 3, "every JSON key should be unique")

    def test_created_field_remains_human_readable_timestamp(self):
        notes = _import_notes_module(self.tmp_home)
        notes.add_note("one", "body one")

        data = json.loads((self.tmp_home / ".notescli" / "notes.json").read_text("utf-8"))
        (note_id, note), = data.items()
        # Format: "<iso-second>-<8 hex chars>"
        self.assertRegex(note_id, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}-[0-9a-f]{8}$")
        self.assertRegex(note["created"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")


class TestListAndDeleteStillWork(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_home = Path(self._tmp.name)
        self.notes = _import_notes_module(self.tmp_home)

    def tearDown(self):
        self._tmp.cleanup()

    def test_list_returns_all_persisted_notes(self):
        for title in ("alpha", "beta", "gamma"):
            self.notes.add_note(title, f"body of {title}")

        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.notes.list_notes()
        output = buf.getvalue()
        self.assertIn("alpha", output)
        self.assertIn("beta", output)
        self.assertIn("gamma", output)

    def test_delete_removes_one_of_same_titled_notes(self):
        self.notes.add_note("dup", "first")
        self.notes.add_note("dup", "second")

        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.notes.delete_note("dup")

        data = json.loads((self.tmp_home / ".notescli" / "notes.json").read_text("utf-8"))
        self.assertEqual(len(data), 1, "exactly one of the two duplicates should be deleted")


if __name__ == "__main__":
    unittest.main()
