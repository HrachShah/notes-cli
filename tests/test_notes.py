"""Tests for notes-cli notes.py defensive handling."""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import notes  # noqa: E402


def _with_notes_file(payload):
    """Context manager: patch notes.NOTES_FILE to a temp file containing payload."""
    fd, path = tempfile.mkstemp(suffix=".json")
    with open(fd, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    old = notes.NOTES_FILE
    notes.NOTES_FILE = type(notes.NOTES_FILE)(path)
    return path, old


def _restore(old_file, tmp_path):
    notes.NOTES_FILE = old_file
    Path(tmp_path).unlink(missing_ok=True)


def test_load_returns_empty_when_file_missing(tmp_path):
    notes.NOTES_FILE = notes.NOTES_FILE.__class__(str(tmp_path / "absent.json"))
    assert notes.load_notes() == {}


def test_load_returns_empty_when_top_level_not_dict(tmp_path):
    path, old = _with_notes_file(["a", "b"])
    try:
        assert notes.load_notes() == {}
    finally:
        _restore(old, path)


def test_load_returns_empty_when_top_level_is_string(tmp_path):
    path, old = _with_notes_file("just-a-string")
    try:
        assert notes.load_notes() == {}
    finally:
        _restore(old, path)


def test_load_returns_empty_when_file_malformed(tmp_path):
    fd, path = tempfile.mkstemp(suffix=".json")
    with open(fd, "w", encoding="utf-8") as f:
        f.write("{not valid json")
    old = notes.NOTES_FILE
    notes.NOTES_FILE = type(notes.NOTES_FILE)(path)
    try:
        assert notes.load_notes() == {}
    finally:
        _restore(old, path)


def test_list_skips_non_dict_entries(capsys, tmp_path):
    path, old = _with_notes_file({
        "id1": "just a string",
        "id2": 42,
        "id3": [1, 2, 3],
        "id4": {"title": "Real", "body": "Hello", "created": "2026-01-01T00:00:00"},
    })
    try:
        notes.list_notes()
        out = capsys.readouterr().out
        assert "Real" in out
        assert "skipped malformed note" in out
        assert "id1" in out and "id2" in out and "id3" in out
    finally:
        _restore(old, path)


def test_list_handles_non_string_body(capsys, tmp_path):
    path, old = _with_notes_file({
        "id1": {"title": "T1", "body": None, "created": "2026-01-01T00:00:00"},
        "id2": {"title": "T2", "body": [1, 2], "created": "2026-01-01T00:00:01"},
        "id3": {"title": "T3", "body": 99, "created": "2026-01-01T00:00:02"},
        "id4": {"title": "T4", "created": "2026-01-01T00:00:03"},
    })
    try:
        notes.list_notes()
        out = capsys.readouterr().out
        for title in ("T1", "T2", "T3", "T4"):
            assert title in out, f"missing {title} in output: {out!r}"
    finally:
        _restore(old, path)


def test_list_handles_missing_title(capsys, tmp_path):
    path, old = _with_notes_file({
        "id1": {"body": "B", "created": "2026-01-01T00:00:00"},
    })
    try:
        notes.list_notes()
        out = capsys.readouterr().out
        assert "(untitled)" in out
    finally:
        _restore(old, path)


def test_list_uses_note_id_when_created_missing(capsys, tmp_path):
    path, old = _with_notes_file({
        "id1": {"title": "T1", "body": "B"},
    })
    try:
        notes.list_notes()
        out = capsys.readouterr().out
        assert "[id1]" in out
    finally:
        _restore(old, path)


def test_add_disambiguates_same_second_collisions(tmp_path):
    notes.NOTES_DIR = notes.NOTES_DIR.__class__(str(tmp_path))
    notes.NOTES_FILE = notes.NOTES_DIR / "notes.json"
    notes.add_note("A", "body A")
    notes.add_note("B", "body B")
    notes.add_note("C", "body C")
    with open(notes.NOTES_FILE, encoding="utf-8") as f:
        stored = json.load(f)
    assert len(stored) == 3
    titles = sorted(v["title"] for v in stored.values())
    assert titles == ["A", "B", "C"]
    ids = list(stored.keys())
    base = ids[0]
    assert "-" not in base.rsplit(":", 1)[-1], f"base should be unsuffixed, got {base!r}"
    assert ids[1] == f"{base}-2"
    assert ids[2] == f"{base}-3"


def test_delete_skips_non_dict_entries(capsys, tmp_path):
    path, old = _with_notes_file({
        "id1": 42,
        "id2": "not a dict",
        "id3": {"title": "Real", "body": "B", "created": "2026-01-01"},
    })
    try:
        notes.delete_note("Real")
        out = capsys.readouterr().out
        assert "Deleted: Real" in out
        with open(path, encoding="utf-8") as f:
            assert json.load(f) == {"id1": 42, "id2": "not a dict"}
    finally:
        _restore(old, path)


def test_delete_with_missing_title_field(capsys, tmp_path):
    path, old = _with_notes_file({
        "id1": {"body": "B", "created": "2026-01-01"},
        "id2": {"title": "X", "body": "B", "created": "2026-01-01"},
    })
    try:
        notes.delete_note("X")
        out = capsys.readouterr().out
        assert "Deleted: X" in out
    finally:
        _restore(old, path)


def test_delete_no_match(capsys, tmp_path):
    path, old = _with_notes_file({"id1": {"title": "X", "body": "B", "created": "2026"}})
    try:
        notes.delete_note("nothing-matches-this")
        out = capsys.readouterr().out
        assert "No note found matching" in out
    finally:
        _restore(old, path)


def test_add_accepts_multi_word_body_via_remainder(capsys, tmp_path, monkeypatch):
    """argparse positional 'body' is REMAINDER so a multi-word unquoted body
    lands as one string instead of triggering 'unrecognized arguments'."""
    notes.NOTES_DIR = notes.NOTES_DIR.__class__(str(tmp_path))
    notes.NOTES_FILE = notes.NOTES_DIR / "notes.json"
    monkeypatch.setattr(sys, "argv", ["notes.py", "add", "Title", "push", "to", "staging"])
    notes.main()
    out = capsys.readouterr().out
    assert "Note saved: Title" in out
    with open(notes.NOTES_FILE, encoding="utf-8") as f:
        stored = json.load(f)
    assert len(stored) == 1
    body = next(iter(stored.values()))["body"]
    assert body == "push to staging", f"expected joined body, got {body!r}"


def test_add_joins_remainder_tokens_with_single_space(capsys, tmp_path, monkeypatch):
    """REMAINDER returns a list of tokens; main() should re-join with spaces
    so a quoted single-string body and an unquoted multi-token body produce
    the same stored value."""
    notes.NOTES_DIR = notes.NOTES_DIR.__class__(str(tmp_path))
    notes.NOTES_FILE = notes.NOTES_DIR / "notes.json"
    monkeypatch.setattr(sys, "argv", ["notes.py", "add", "T", "a", "b", "c"])
    notes.main()
    with open(notes.NOTES_FILE, encoding="utf-8") as f:
        stored = json.load(f)
    assert next(iter(stored.values()))["body"] == "a b c"


def test_add_with_no_body_tokens_stores_empty_string(capsys, tmp_path, monkeypatch):
    notes.NOTES_DIR = notes.NOTES_DIR.__class__(str(tmp_path))
    notes.NOTES_FILE = notes.NOTES_DIR / "notes.json"
    monkeypatch.setattr(sys, "argv", ["notes.py", "add", "Tonly"])
    notes.main()
    with open(notes.NOTES_FILE, encoding="utf-8") as f:
        stored = json.load(f)
    assert next(iter(stored.values()))["body"] == ""
