"""Tests for delete_note() rejecting empty/whitespace titles."""
from __future__ import annotations

import importlib.util
import io
import tempfile
from contextlib import redirect_stdout
from pathlib import Path


def _load_fresh(home):
    spec = importlib.util.spec_from_file_location("notes_delete_test", "notes.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.NOTES_DIR = Path(home) / ".notescli"
    m.NOTES_FILE = m.NOTES_DIR / "notes.json"
    m.NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return m


def test_delete_empty_string_does_not_match_every_note():
    with tempfile.TemporaryDirectory() as home:
        m = _load_fresh(home)
        m.add_note("Important note", "body")
        before = dict(m.load_notes())
        buf = io.StringIO()
        with redirect_stdout(buf):
            m.delete_note("")
        out = buf.getvalue()
        after = m.load_notes()
        assert after == before, f"empty delete wiped the store: {list(after)}"
        assert "must be non-blank" in out, f"expected non-blank error, got {out!r}"


def test_delete_whitespace_only_does_not_match_every_note():
    with tempfile.TemporaryDirectory() as home:
        m = _load_fresh(home)
        m.add_note("Important note", "body")
        before = dict(m.load_notes())
        buf = io.StringIO()
        with redirect_stdout(buf):
            m.delete_note("   \t  ")
        out = buf.getvalue()
        after = m.load_notes()
        assert after == before, f"whitespace delete wiped the store: {list(after)}"
        assert "must be non-blank" in out, f"expected non-blank error, got {out!r}"


def test_delete_real_title_still_works():
    with tempfile.TemporaryDirectory() as home:
        m = _load_fresh(home)
        m.add_note("hello", "world")
        buf = io.StringIO()
        with redirect_stdout(buf):
            m.delete_note("hello")
        out = buf.getvalue()
        assert m.load_notes() == {}
        assert "Deleted:" in out


def test_delete_nonexistent_title_prints_no_match():
    with tempfile.TemporaryDirectory() as home:
        m = _load_fresh(home)
        m.add_note("hello", "world")
        buf = io.StringIO()
        with redirect_stdout(buf):
            m.delete_note("nope")
        out = buf.getvalue()
        assert "No note found matching" in out
        assert len(m.load_notes()) == 1