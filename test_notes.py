"""Tests for notes CLI module.

Exercises notes.py through importlib so each test can run with its own ``Path.home()`` pointing at a temp directory; the module reads NOTES_DIR from home at import time.

The same-second uniqueness fix has its own TestSameSecondNoteIds class below.
"""

import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


def _import_notes_module(tmp_home: Path):
    """Reload notes.py with Path.home() redirected at ``tmp_home``."""
    spec = importlib.util.spec_from_file_location(
        "notes_under_test", Path(__file__).parent / "notes.py"
    )
    notes = importlib.util.module_from_spec(spec)
    with mock.patch.object(Path, "home", lambda: tmp_home):
        spec.loader.exec_module(notes)
    return notes


class TestSameSecondNoteIds(unittest.TestCase):
    """Regression: notes saved in the same second used to overwrite each other."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_home = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_three_notes_same_second_are_all_persisted(self):
        notes = _import_notes_module(self.tmp_home)
        for title in ("First", "Second", "Third"):
            notes.add_note(title, f"body of {title}")

        data = json.loads((self.tmp_home / ".notescli" / "notes.json").read_text("utf-8"))
        self.assertEqual(len(data), 3, "all three same-second notes should persist")
        self.assertEqual(
            {n["title"] for n in data.values()},
            {"First", "Second", "Third"},
        )

    def test_note_ids_are_unique_within_same_second(self):
        notes = _import_notes_module(self.tmp_home)
        for _ in range(5):
            notes.add_note("a", "b")

        data = json.loads((self.tmp_home / ".notescli" / "notes.json").read_text("utf-8"))
        self.assertEqual(len(data), 5)
        self.assertEqual(len(set(data.keys())), 5, "every persisted key should be unique")


class TestCreatedFieldIsHumanReadable(unittest.TestCase):
    """``created`` should be a plain ISO second timestamp, no random suffix."""

    def test_created_field_format(self):
        with tempfile.TemporaryDirectory() as tmp_home:
            notes = _import_notes_module(Path(tmp_home))
            notes.add_note("hello", "world")
            data = json.loads((Path(tmp_home) / ".notescli" / "notes.json").read_text("utf-8"))
            (note_id, note), = data.items()
            self.assertRegex(note_id, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}-[0-9a-f]{8}$")
            self.assertRegex(note["created"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")


class TestDeleteToleratesMalformedNotes(unittest.TestCase):
    def test_delete_skips_records_without_string_titles(self):
        with tempfile.TemporaryDirectory() as tmp_home:
            notes = _import_notes_module(Path(tmp_home))
            notes.save_notes({
                "bad": {"body": "orphaned"},
                "good": {"title": "Keep this", "body": "body"},
            })
            with redirect_stdout(io.StringIO()) as output:
                notes.delete_note("missing")
            self.assertIn("No note found", output.getvalue())


class TestListOutputsAllNotes(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_home = Path(self._tmp.name)
        self.notes = _import_notes_module(self.tmp_home)

    def tearDown(self):
        self._tmp.cleanup()

    def test_list_prints_each_persisted_note(self):
        for title in ("alpha", "beta", "gamma"):
            self.notes.add_note(title, f"body of {title}")

        buf = io.StringIO()
        with redirect_stdout(buf):
            self.notes.list_notes()
        output = buf.getvalue()
        self.assertIn("alpha", output)
        self.assertIn("beta", output)
        self.assertIn("gamma", output)


if __name__ == "__main__":
    unittest.main()