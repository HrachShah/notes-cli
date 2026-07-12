import json
import tempfile
import unittest
from pathlib import Path

import notes


class LoadNotesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)
        self.orig_path = notes.NOTES_FILE
        notes.NOTES_FILE = self.tmpdir / "notes.json"

    def tearDown(self):
        notes.NOTES_FILE = self.orig_path
        self.tmp.cleanup()

    def test_missing_file_returns_empty_dict(self):
        self.assertEqual(notes.load_notes(), {})

    def test_corrupt_file_moves_aside_and_returns_empty(self):
        notes.NOTES_FILE.write_text("{not json")
        with self.assertLogs("notes", level="WARNING") as captured:
            result = notes.load_notes()
        self.assertEqual(result, {})
        backups = list(self.tmpdir.glob("notes.json.corrupt-*"))
        self.assertEqual(len(backups), 1)
        self.assertFalse(notes.NOTES_FILE.exists())
        self.assertIn("not valid JSON", captured.records[0].getMessage())

    def test_corrupt_file_does_not_clobber_next_save(self):
        notes.NOTES_FILE.write_text("garbage")
        notes.load_notes()
        notes.save_notes({"a": {"title": "hi", "body": "b", "created": "x"}})
        self.assertEqual(json.loads(notes.NOTES_FILE.read_text()), {
            "a": {"title": "hi", "body": "b", "created": "x"},
        })
        backup = next(self.tmpdir.glob("notes.json.corrupt-*"))
        self.assertEqual(backup.read_text(), "garbage")

    def test_valid_file_round_trips(self):
        payload = {"x": {"title": "x", "body": "y", "created": "2026"}}
        notes.NOTES_FILE.write_text(json.dumps(payload))
        self.assertEqual(notes.load_notes(), payload)


if __name__ == "__main__":
    unittest.main()
