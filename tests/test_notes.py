import json
import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import notes
from notes import (
    _generate_note_id,
    add_note,
    delete_note,
    list_notes,
    load_notes,
    save_notes,
)


class GenerateNoteIdTest(unittest.TestCase):
    def test_first_id_has_no_suffix_for_fresh_second(self):
        fixed = datetime(2026, 1, 1, 0, 0, 0)
        with mock.patch("notes.datetime") as mdt:
            mdt.now.return_value = fixed
            nid = _generate_note_id({})
        self.assertEqual(nid, "2026-01-01T00:00:00")

    def test_collision_in_same_second_appends_suffix(self):
        fixed = datetime(2026, 1, 1, 0, 0, 0)
        with mock.patch("notes.datetime") as mdt:
            mdt.now.return_value = fixed
            nid = _generate_note_id({"2026-01-01T00:00:00": {"title": "x"}})
        self.assertEqual(nid, "2026-01-01T00:00:00-1")

    def test_repeated_collisions_increment_suffix(self):
        fixed = datetime(2026, 1, 1, 0, 0, 0)
        with mock.patch("notes.datetime") as mdt:
            mdt.now.return_value = fixed
            existing = {
                "2026-01-01T00:00:00": {"title": "a"},
                "2026-01-01T00:00:00-1": {"title": "b"},
            }
            nid = _generate_note_id(existing)
        self.assertEqual(nid, "2026-01-01T00:00:00-2")


class AddNoteTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="notes-cli-test-")
        self.orig_file = notes.NOTES_FILE
        self.orig_dir = notes.NOTES_DIR
        notes.NOTES_DIR = Path(self.tmp)
        notes.NOTES_FILE = notes.NOTES_DIR / "notes.json"

    def tearDown(self):
        notes.NOTES_FILE = self.orig_file
        notes.NOTES_DIR = self.orig_dir

    def test_three_adds_in_same_second_persist_three_notes(self):
        fixed = datetime(2026, 1, 1, 0, 0, 0)
        with mock.patch("notes.datetime") as mdt:
            mdt.now.return_value = fixed
            add_note("A", "first")
            add_note("B", "second")
            add_note("C", "third")
        loaded = load_notes()
        self.assertEqual(len(loaded), 3)
        titles = sorted(n["title"] for n in loaded.values())
        self.assertEqual(titles, ["A", "B", "C"])


if __name__ == "__main__":
    unittest.main()
