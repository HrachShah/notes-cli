"""Tests for notes-cli.

Run with: python3 -m unittest test_notes.py
or:       python3 -m pytest test_notes.py
"""

import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# We import the module under test as ``notes`` even though the file is
# called ``notes.py`` (which would otherwise shadow the stdlib ``notes``
# module on some systems).
import notes  # noqa: E402


class NotesCliTests(unittest.TestCase):
    def setUp(self):
        # Point the module at a temp NOTES_FILE for the duration of the test
        self._tmp = tempfile.TemporaryDirectory()
        self._notes_dir = Path(self._tmp.name) / ".notescli"
        self._notes_dir.mkdir(parents=True, exist_ok=True)
        self._orig_dir = notes.NOTES_DIR
        self._orig_file = notes.NOTES_FILE
        notes.NOTES_DIR = self._notes_dir
        notes.NOTES_FILE = self._notes_dir / "notes.json"
        # Reset the in-process id suffix cache so tests do not see leftover
        # counters from a previous test (or from a prior test process that
        # wrote to the same id-key).
        if hasattr(notes._new_note_id, "_seen"):
            notes._new_note_id._seen.clear()

    def tearDown(self):
        notes.NOTES_DIR = self._orig_dir
        notes.NOTES_FILE = self._orig_file
        self._tmp.cleanup()

    def test_add_note_persists_to_disk(self):
        notes.add_note("Deploy checklist", "Push to staging")
        self.assertTrue(notes.NOTES_FILE.exists())
        data = json.loads(notes.NOTES_FILE.read_text("utf-8"))
        self.assertEqual(len(data), 1)
        [(note_id, payload)] = data.items()
        self.assertEqual(payload["title"], "Deploy checklist")
        self.assertEqual(payload["body"], "Push to staging")
        self.assertEqual(payload["created"], note_id)

    def test_two_adds_in_same_second_get_distinct_ids(self):
        # The original implementation used datetime.isoformat(timespec="seconds")
        # as the key, which collided on sub-second adds and silently
        # overwrote the first note. This test would fail under that
        # implementation.
        notes.add_note("First", "alpha")
        notes.add_note("Second", "beta")
        data = json.loads(notes.NOTES_FILE.read_text("utf-8"))
        self.assertEqual(len(data), 2, f"expected 2 notes, got {len(data)}: {data}")
        titles = {payload["title"] for payload in data.values()}
        self.assertEqual(titles, {"First", "Second"})

    def test_three_adds_in_same_second_get_distinct_ids(self):
        notes.add_note("A", "1")
        notes.add_note("B", "2")
        notes.add_note("C", "3")
        data = json.loads(notes.NOTES_FILE.read_text("utf-8"))
        self.assertEqual(len(data), 3)

    def test_save_notes_removes_temporary_file_after_success(self):
        notes.save_notes({"id": {"title": "Title", "body": "Body"}})
        self.assertEqual(json.loads(notes.NOTES_FILE.read_text("utf-8"))["id"]["title"], "Title")
        self.assertFalse(notes.NOTES_FILE.with_name(".notes.json.tmp").exists())

    def test_load_notes_ignores_invalid_utf8(self):
        notes.NOTES_FILE.write_bytes(b"{\xff")
        self.assertEqual(notes.load_notes(), {})

    def test_load_notes_ignores_non_dict_root(self):
        notes.NOTES_FILE.write_text(json.dumps([{"title": "not a mapping"}]), encoding="utf-8")
        self.assertEqual(notes.load_notes(), {})

    def test_list_notes_handles_non_dict_entries(self):
        # Hand-edited notes.json can have non-dict values; list_notes
        # should warn and skip rather than crash with AttributeError on
        # `note["title"]`.
        notes.NOTES_FILE.write_text(
            json.dumps({"2024-01-01T00:00:00": "not a dict"}), encoding="utf-8"
        )
        # Should not raise.
        notes.list_notes()

    def test_list_notes_stringifies_non_string_body(self):
        notes.NOTES_FILE.write_text(json.dumps({
            "note": {"title": "Numbers", "body": 42, "created": "note"},
        }))
        notes.list_notes()

    def test_delete_by_substring(self):
        notes.add_note("Deploy checklist", "x")
        notes.add_note("Deploy staging", "y")
        notes.add_note("Other", "z")
        notes.delete_note("Deploy")
        data = json.loads(notes.NOTES_FILE.read_text("utf-8"))
        # delete_note removes the first entry whose title contains the
        # substring (insertion order). Both "Deploy checklist" and
        # "Deploy staging" match, so only the first one is removed.
        self.assertEqual(len(data), 2)
        remaining_titles = sorted(p["title"] for p in data.values())
        self.assertEqual(remaining_titles, ["Deploy staging", "Other"])

    def test_delete_matches_unicode_case_variants(self):
        notes.add_note("Straße", "x")
        notes.delete_note("STRASSE")
        self.assertEqual(json.loads(notes.NOTES_FILE.read_text("utf-8")), {})

    def test_delete_no_match(self):
        notes.add_note("Deploy checklist", "x")
        notes.delete_note("NoSuchTitle")
        data = json.loads(notes.NOTES_FILE.read_text("utf-8"))
        self.assertEqual(len(data), 1)


    def test_delete_matches_unicode_casefold_equivalents(self):
        notes.add_note("Straße", "x")
        notes.delete_note("STRASSE")
        self.assertEqual(json.loads(notes.NOTES_FILE.read_text("utf-8")), {})


    def test_delete_note_skips_entries_with_non_string_title(self):
        # A note hand-edited into notes.json (or written by a different
        # version of the tool) can have a missing or null title field.
        # delete_note used to call note["title"].lower() on those entries
        # and crash with AttributeError; it should now silently skip them
        # and still match the legitimate one.
        notes.NOTES_FILE.write_text(json.dumps({
            "broken": {"title": None, "body": "x", "created": "broken"},
            "ok": {"title": "deploy notes", "body": "y", "created": "ok"},
        }))
        notes.delete_note("deploy")
        data = json.loads(notes.NOTES_FILE.read_text("utf-8"))
        self.assertEqual(list(data.keys()), ["broken"])

if __name__ == "__main__":
    unittest.main()
