"""Tests for notes-cli.

Run with: python3 -m unittest test_notes.py
or:       python3 test_notes.py
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import notes  # noqa: E402


class GenerateNoteIdTests(unittest.TestCase):
    """Unit tests for the collision-free note id generator."""

    def test_returns_iso_timestamp_with_microseconds(self):
        from datetime import datetime as real_dt

        fixed = real_dt(2026, 6, 17, 12, 0, 0, 123456)
        new_id = notes._generate_note_id({}, now=lambda: fixed)
        self.assertEqual(new_id, "2026-06-17T12:00:00.123456")

    def test_avoids_collision_with_existing_key(self):
        from datetime import datetime as real_dt

        fixed = real_dt(2026, 6, 17, 12, 0, 0, 123456)
        existing = {"2026-06-17T12:00:00.123456": {"title": "old"}}
        new_id = notes._generate_note_id(existing, now=lambda: fixed)
        self.assertEqual(new_id, "2026-06-17T12:00:00.123456-1")

    def test_increments_suffix_on_repeated_collision(self):
        from datetime import datetime as real_dt

        fixed = real_dt(2026, 6, 17, 12, 0, 0, 123456)
        existing = {
            "2026-06-17T12:00:00.123456": {"title": "old"},
            "2026-06-17T12:00:00.123456-1": {"title": "old"},
            "2026-06-17T12:00:00.123456-2": {"title": "old"},
        }
        new_id = notes._generate_note_id(existing, now=lambda: fixed)
        self.assertEqual(new_id, "2026-06-17T12:00:00.123456-3")

    def test_does_not_mutate_existing_dict(self):
        from datetime import datetime as real_dt

        fixed = real_dt(2026, 6, 17, 12, 0, 0, 123456)
        existing = {"2026-06-17T12:00:00.123456": {"title": "old"}}
        before = dict(existing)
        notes._generate_note_id(existing, now=lambda: fixed)
        self.assertEqual(existing, before)

    def test_unrelated_existing_keys_dont_trigger_suffix(self):
        from datetime import datetime as real_dt

        fixed = real_dt(2026, 6, 17, 12, 0, 0, 123456)
        existing = {"2026-06-17T12:00:00.999999": {"title": "other"}}
        new_id = notes._generate_note_id(existing, now=lambda: fixed)
        self.assertEqual(new_id, "2026-06-17T12:00:00.123456")


class AddNoteRegressionTests(unittest.TestCase):
    """End-to-end tests for the add_note data-loss bug.

    Before the fix, add_note used datetime.now().isoformat(timespec="seconds")
    as the dict key, so two notes added in the same second silently
    overwrote each other in the JSON store.
    """

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._orig_dir = notes.NOTES_DIR
        self._orig_file = notes.NOTES_FILE
        notes.NOTES_DIR = Path(self._tmpdir.name) / ".notescli"
        notes.NOTES_FILE = notes.NOTES_DIR / "notes.json"

    def tearDown(self):
        notes.NOTES_DIR = self._orig_dir
        notes.NOTES_FILE = self._orig_file
        self._tmpdir.cleanup()

    def test_two_notes_added_in_same_second_are_both_kept(self):
        from datetime import datetime as real_dt

        fixed = real_dt(2026, 6, 17, 12, 0, 0, 0)
        now = lambda: fixed
        notes.add_note("First", "body1", now=now)
        notes.add_note("Second", "body2", now=now)
        data = json.loads(notes.NOTES_FILE.read_text(encoding="utf-8"))
        self.assertEqual(len(data), 2)
        titles = {n["title"] for n in data.values()}
        self.assertEqual(titles, {"First", "Second"})

    def test_five_notes_added_in_same_microsecond_are_all_kept(self):
        from datetime import datetime as real_dt

        fixed = real_dt(2026, 6, 17, 12, 0, 0, 42)
        now = lambda: fixed
        for letter in "ABCDE":
            notes.add_note(letter, f"body-{letter}", now=now)
        data = json.loads(notes.NOTES_FILE.read_text(encoding="utf-8"))
        self.assertEqual(len(data), 5)
        ids = list(data.keys())
        # First one is the bare timestamp, the rest get a -N suffix.
        self.assertEqual(ids[0], "2026-06-17T12:00:00.000042")
        self.assertEqual(ids[1], "2026-06-17T12:00:00.000042-1")
        self.assertEqual(ids[2], "2026-06-17T12:00:00.000042-2")
        self.assertEqual(ids[3], "2026-06-17T12:00:00.000042-3")
        self.assertEqual(ids[4], "2026-06-17T12:00:00.000042-4")
        # And the created field always matches the id.
        for note_id, note in data.items():
            self.assertEqual(note["created"], note_id)


class LoadNotesTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._orig_dir = notes.NOTES_DIR
        self._orig_file = notes.NOTES_FILE
        notes.NOTES_DIR = Path(self._tmpdir.name) / ".notescli"
        notes.NOTES_FILE = notes.NOTES_DIR / "notes.json"

    def tearDown(self):
        notes.NOTES_DIR = self._orig_dir
        notes.NOTES_FILE = self._orig_file
        self._tmpdir.cleanup()

    def test_missing_file_returns_empty_dict(self):
        self.assertEqual(notes.load_notes(), {})

    def test_corrupt_json_returns_empty_dict(self):
        notes.NOTES_DIR.mkdir(parents=True, exist_ok=True)
        notes.NOTES_FILE.write_text("not json {", encoding="utf-8")
        self.assertEqual(notes.load_notes(), {})

    def test_json_null_returns_empty_dict(self):
        notes.NOTES_DIR.mkdir(parents=True, exist_ok=True)
        notes.NOTES_FILE.write_text("null", encoding="utf-8")
        self.assertEqual(notes.load_notes(), {})

    def test_json_list_returns_empty_dict(self):
        notes.NOTES_DIR.mkdir(parents=True, exist_ok=True)
        notes.NOTES_FILE.write_text("[]", encoding="utf-8")
        self.assertEqual(notes.load_notes(), {})

    def test_json_empty_object_returns_empty_dict(self):
        notes.NOTES_DIR.mkdir(parents=True, exist_ok=True)
        notes.NOTES_FILE.write_text("{}", encoding="utf-8")
        self.assertEqual(notes.load_notes(), {})

    def test_json_number_returns_empty_dict(self):
        notes.NOTES_DIR.mkdir(parents=True, exist_ok=True)
        notes.NOTES_FILE.write_text("123", encoding="utf-8")
        self.assertEqual(notes.load_notes(), {})

    def test_json_string_returns_empty_dict(self):
        notes.NOTES_DIR.mkdir(parents=True, exist_ok=True)
        notes.NOTES_FILE.write_text('"hello"', encoding="utf-8")
        self.assertEqual(notes.load_notes(), {})

    def test_add_note_after_load_notes_sees_non_dict_does_not_crash(self):
        notes.NOTES_DIR.mkdir(parents=True, exist_ok=True)
        notes.NOTES_FILE.write_text("[]", encoding="utf-8")
        notes.load_notes()
        notes.add_note("Test", "body")


class TestDeleteNote(unittest.TestCase):
    """Tests for delete_note()."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._orig_dir = notes.NOTES_DIR
        self._orig_file = notes.NOTES_FILE
        notes.NOTES_DIR = Path(self._tmpdir.name) / ".notescli"
        notes.NOTES_FILE = notes.NOTES_DIR / "notes.json"

    def tearDown(self):
        notes.NOTES_DIR = self._orig_dir
        notes.NOTES_FILE = self._orig_file
        self._tmpdir.cleanup()

    def test_delete_note_removes_note_from_store(self):
        notes.add_note("Test", "body")
        data = json.loads(notes.NOTES_FILE.read_text(encoding="utf-8"))
        self.assertEqual(len(data), 1)
        notes.delete_note("Test")
        data = json.loads(notes.NOTES_FILE.read_text(encoding="utf-8"))
        self.assertEqual(len(data), 0)


if __name__ == "__main__":
    unittest.main()
