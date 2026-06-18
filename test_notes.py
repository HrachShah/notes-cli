"""Tests for notes-cli. Run with: python3 -m pytest test_notes.py"""
import json
import sys
from pathlib import Path

# Make notes.py importable when run from this directory
sys.path.insert(0, str(Path(__file__).resolve().parent))

import notes  # noqa: E402


def _isolated_notes(tmp_path, monkeypatch):
    """Point notes.NOTES_FILE at a fresh tmp_path and re-import the module state."""
    notes.NOTES_DIR = tmp_path
    notes.NOTES_FILE = tmp_path / "notes.json"


def test_add_note_writes_entry_to_file(tmp_path, monkeypatch, capsys):
    _isolated_notes(tmp_path, monkeypatch)
    notes.add_note("shopping", "milk, eggs, bread")
    out = capsys.readouterr().out
    assert "Note saved: shopping" in out
    data = json.loads(notes.NOTES_FILE.read_text(encoding="utf-8"))
    assert len(data) == 1
    (note_id, note), = data.items()
    assert note["title"] == "shopping"
    assert note["body"] == "milk, eggs, bread"
    assert note["created"] == note_id


def test_two_adds_in_the_same_second_do_not_overwrite(tmp_path, monkeypatch, capsys):
    """Regression: a single second-resolution timestamp used as a dict key
    means a rapid second add silently clobbered the first one. Now the second
    add gets a numeric suffix and both notes survive."""
    _isolated_notes(tmp_path, monkeypatch)
    # Pin the clock so both adds are reported as the same second.
    from datetime import datetime

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 1, 1, 12, 0, 0)

    monkeypatch.setattr(notes, "datetime", FrozenDatetime)

    notes.add_note("first", "alpha")
    notes.add_note("second", "beta")

    data = json.loads(notes.NOTES_FILE.read_text(encoding="utf-8"))
    assert len(data) == 2, f"expected 2 notes, got {list(data)}"
    titles = {n["title"] for n in data.values()}
    assert titles == {"first", "second"}


def test_three_adds_in_the_same_second_get_distinct_ids(tmp_path, monkeypatch, capsys):
    _isolated_notes(tmp_path, monkeypatch)
    from datetime import datetime

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 1, 1, 12, 0, 0)

    monkeypatch.setattr(notes, "datetime", FrozenDatetime)

    notes.add_note("a", "1")
    notes.add_note("b", "2")
    notes.add_note("c", "3")

    data = json.loads(notes.NOTES_FILE.read_text(encoding="utf-8"))
    assert len(data) == 3
    assert {n["title"] for n in data.values()} == {"a", "b", "c"}


def test_list_notes_prints_newest_first(tmp_path, monkeypatch, capsys):
    _isolated_notes(tmp_path, monkeypatch)
    from datetime import datetime, timedelta

    real_now = datetime(2026, 1, 1, 12, 0, 0)

    class SteppingDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return real_now

    # Add three notes spaced one second apart by mutating real_now between calls.
    monkeypatch.setattr(notes, "datetime", SteppingDatetime)
    notes.add_note("alpha", "first body")
    real_now = real_now + timedelta(seconds=1)
    notes.add_note("beta", "second body")
    real_now = real_now + timedelta(seconds=1)
    notes.add_note("gamma", "third body")

    notes.list_notes()
    out = capsys.readouterr().out
    # Newest first means gamma appears before beta, which appears before alpha.
    import re
    headings = re.findall(r"^\[[^\]]+\] (\w+)$", out, re.M)
    assert headings == ["gamma", "beta", "alpha"], headings


def test_delete_note_removes_first_match_case_insensitive(tmp_path, monkeypatch, capsys):
    _isolated_notes(tmp_path, monkeypatch)
    notes.add_note("Shopping List", "milk")
    notes.add_note("shopping list backup", "cereal")

    notes.delete_note("shopping list")
    data = json.loads(notes.NOTES_FILE.read_text(encoding="utf-8"))
    assert len(data) == 1
    remaining = next(iter(data.values()))
    assert remaining["title"] == "shopping list backup"


def test_delete_note_with_no_match_is_a_no_op(tmp_path, monkeypatch, capsys):
    _isolated_notes(tmp_path, monkeypatch)
    notes.add_note("only", "one")
    notes.delete_note("not present")
    data = json.loads(notes.NOTES_FILE.read_text(encoding="utf-8"))
    assert len(data) == 1


def test_load_notes_returns_empty_when_file_missing(tmp_path, monkeypatch):
    _isolated_notes(tmp_path, monkeypatch)
    assert notes.load_notes() == {}


def test_load_notes_tolerates_corrupt_json(tmp_path, monkeypatch):
    _isolated_notes(tmp_path, monkeypatch)
    notes.NOTES_FILE.write_text("{ this is not json", encoding="utf-8")
    # The current behavior is to return {} on decode failure. Pin it so a
    # future change to surface the error can't break the contract silently.
    assert notes.load_notes() == {}


def test_long_body_is_truncated_in_list_output(tmp_path, monkeypatch, capsys):
    _isolated_notes(tmp_path, monkeypatch)
    long_body = "x" * 200
    notes.add_note("long", long_body)
    notes.list_notes()
    out = capsys.readouterr().out
    # 80 chars of body + the '...' marker
    assert "x" * 80 + "..." in out
    assert "x" * 81 not in out.split("long")[1]
