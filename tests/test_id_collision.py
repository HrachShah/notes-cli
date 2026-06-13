"""Tests that add_note generates unique IDs even when called multiple times in the same second."""
import json
import time
import datetime
import tempfile
import importlib.util
from pathlib import Path


def _load_fresh(home):
    spec = importlib.util.spec_from_file_location("notes_id_test", "notes.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.NOTES_DIR = Path(home) / ".notescli"
    m.NOTES_FILE = m.NOTES_DIR / "notes.json"
    m.NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return m


def test_rapid_add_same_second_unique_ids():
    with tempfile.TemporaryDirectory() as home:
        m = _load_fresh(home)
        for label in ("a", "b", "c", "d"):
            m.add_note(label, label)
        notes = m.load_notes()
        assert len(notes) == 4, f"Expected 4, got {len(notes)}: {list(notes)}"
        assert len(set(notes.keys())) == 4, f"IDs collided: {list(notes)}"
        ids = sorted(notes.keys())
        # First id has no -N suffix; subsequent ones do.
        assert "-2" not in ids[0] and "-3" not in ids[0], f"first id should be a bare timestamp, got {ids[0]!r}"
        for k in ids[1:]:
            assert "-2" in k or "-3" in k or "-4" in k or "-5" in k, f"expected collision suffix on {k!r}"


def test_no_suffix_across_seconds():
    with tempfile.TemporaryDirectory() as home:
        m = _load_fresh(home)
        m.add_note("a", "A")
        time.sleep(1.1)
        m.add_note("b", "B")
        notes = m.load_notes()
        assert len(notes) == 2
        for k in notes.keys():
            assert "-2" not in k, f"unwanted collision suffix on {k!r}"


def test_delete_frees_base_id_for_reuse():
    with tempfile.TemporaryDirectory() as home:
        m = _load_fresh(home)
        m.add_note("a", "A")
        m.add_note("b", "B")
        m.delete_note("a")
        notes = m.load_notes()
        assert len(notes) == 1
        # Now add a new note; the base id is free, so it should get the base
        m.add_note("c", "C")
        notes = m.load_notes()
        assert len(notes) == 2
        # The new id should be the bare timestamp (no -N suffix) since the
        # base was freed by the delete.
        new_id = [k for k in notes if notes[k]["title"] == "c"][0]
        assert "-2" not in new_id and "-3" not in new_id, f"got collision suffix on free id: {new_id!r}"


def test_list_shows_all_rapid_notes_without_loss():
    with tempfile.TemporaryDirectory() as home:
        m = _load_fresh(home)
        for i in range(5):
            m.add_note(f"note-{i}", f"body-{i}")
        notes = m.load_notes()
        assert len(notes) == 5
        # list_notes should print all 5
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            m.list_notes()
        out = buf.getvalue()
        for i in range(5):
            assert f"note-{i}" in out, f"note-{i} missing from list output:\n{out}"


def test_save_load_preserves_collision_suffixes():
    with tempfile.TemporaryDirectory() as home:
        m = _load_fresh(home)
        m.add_note("a", "A")
        m.add_note("b", "B")
        m.add_note("c", "C")
        # Re-load from disk
        notes2 = m.load_notes()
        assert len(notes2) == 3
        # All 3 distinct
        assert len(set(notes2.keys())) == 3
