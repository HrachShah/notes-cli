"""Tests for notes-cli."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import notes as notes_mod  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_notes_home(tmp_path, monkeypatch):
    """Redirect NOTES_FILE to a per-test temp file."""
    notes_dir = tmp_path / ".notescli"
    notes_dir.mkdir()
    notes_file = notes_dir / "notes.json"
    monkeypatch.setattr(notes_mod, "NOTES_DIR", notes_dir)
    monkeypatch.setattr(notes_mod, "NOTES_FILE", notes_file)
    return notes_file


def test_add_persists_note(isolated_notes_home):
    notes_mod.add_note("Hello", "World")
    data = json.loads(isolated_notes_home.read_text("utf-8"))
    assert len(data) == 1
    note = next(iter(data.values()))
    assert note["title"] == "Hello"
    assert note["body"] == "World"


def test_add_rejects_empty_title(isolated_notes_home, capsys):
    with pytest.raises(SystemExit) as exc:
        notes_mod.add_note("", "body")
    assert exc.value.code == 2
    assert not isolated_notes_home.exists()
    err = capsys.readouterr().err
    assert "title" in err.lower()


def test_add_rejects_missing_title(isolated_notes_home, capsys):
    with pytest.raises(SystemExit) as exc:
        notes_mod.add_note("   ", "body")
    assert exc.value.code == 2
    assert not isolated_notes_home.exists()


def test_list_handles_malformed_note(isolated_notes_home, capsys):
    """A note entry that isn't a dict (e.g. null, a number) shouldn't crash list."""
    isolated_notes_home.write_text(
        json.dumps({"a": "not-a-dict", "b": {"title": "Real", "body": "ok", "created": "x"}})
    )
    notes_mod.list_notes()
    out = capsys.readouterr().out
    assert "Real" in out


def test_list_skips_note_without_title(isolated_notes_home, capsys):
    isolated_notes_home.write_text(
        json.dumps({"a": {"body": "orphan", "created": "x"}})
    )
    notes_mod.list_notes()
    out = capsys.readouterr().out
    assert "untitled" in out.lower()


def test_delete_rejects_empty_search(isolated_notes_home, capsys):
    notes_mod.add_note("real", "body")
    with pytest.raises(SystemExit) as exc:
        notes_mod.delete_note("")
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "empty" in err.lower()
    data = json.loads(isolated_notes_home.read_text("utf-8"))
    assert len(data) == 1


def test_delete_empty_string_would_match_every_note_without_guard(
    isolated_notes_home, capsys
):
    """A guard against `delete_note("")` matching every note."""
    notes_mod.add_note("A", "x")
    import time

    time.sleep(1.05)
    notes_mod.add_note("B", "y")
    with pytest.raises(SystemExit) as exc:
        notes_mod.delete_note("")
    assert exc.value.code == 2
    data = json.loads(isolated_notes_home.read_text("utf-8"))
    assert len(data) == 2


def test_delete_finds_case_insensitive(isolated_notes_home, capsys):
    notes_mod.add_note("Project Plan", "secret")
    notes_mod.delete_note("project")
    out = capsys.readouterr().out
    assert "Deleted" in out
    data = json.loads(isolated_notes_home.read_text("utf-8"))
    assert data == {}


def test_delete_skips_malformed_notes(isolated_notes_home, capsys):
    isolated_notes_home.write_text(
        json.dumps({"x": "not-a-dict", "y": {"title": "Real", "body": "", "created": "y"}})
    )
    notes_mod.delete_note("real")
    data = json.loads(isolated_notes_home.read_text("utf-8"))
    # The matched note is deleted; the malformed entry is left in place
    # (the fix only filters at the matching step, not at the save step).
    assert "y" not in data
    assert "x" in data  # malformed entry still present after the delete


def test_load_notes_recovers_from_non_dict_file(isolated_notes_home):
    isolated_notes_home.write_text("[]")
    assert notes_mod.load_notes() == {}
    isolated_notes_home.write_text("null")
    assert notes_mod.load_notes() == {}
    isolated_notes_home.write_text('"a string"')
    assert notes_mod.load_notes() == {}


def test_cli_add_then_list_via_subprocess(tmp_path, monkeypatch):
    """Smoke test the actual CLI script with a temp HOME."""
    notes_dir = tmp_path / ".notescli"
    notes_file = notes_dir / "notes.json"
    env = os.environ.copy()
    env["HOME"] = str(tmp_path)
    script = Path(__file__).resolve().parent.parent / "notes.py"
    result = subprocess.run(
        [sys.executable, str(script), "add", "Smoke", "from pytest"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert notes_file.exists()
    data = json.loads(notes_file.read_text("utf-8"))
    assert len(data) == 1
    assert "Smoke" in next(iter(data.values()))["title"]


def test_cli_delete_rejects_empty_arg(tmp_path):
    env = os.environ.copy()
    env["HOME"] = str(tmp_path)
    script = Path(__file__).resolve().parent.parent / "notes.py"
    result = subprocess.run(
        [sys.executable, str(script), "delete", ""],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "empty" in result.stderr.lower()


def test_add_note_same_second_keeps_all_notes(isolated_notes_home, monkeypatch):
    """Two notes added in the same second should both persist, not clobber.

    The pre-fix code used the wall-clock second as the only key, so the
    second add_note() call would silently overwrite the first. The fix
    keeps the same base id (so a list of the file still orders by it)
    and appends a -N suffix for each subsequent collision.
    """
    from datetime import datetime

    frozen = datetime(2026, 1, 2, 3, 4, 5)
    monkeypatch.setattr(notes_mod, "_now", lambda: frozen)

    notes_mod.add_note("First", "body1")
    notes_mod.add_note("Second", "body2")
    notes_mod.add_note("Third", "body3")

    data = json.loads(isolated_notes_home.read_text("utf-8"))
    assert len(data) == 3, f"all three notes should persist, got {list(data)}"

    titles = {entry["title"] for entry in data.values()}
    assert titles == {"First", "Second", "Third"}

    bodies = {entry["body"] for entry in data.values()}
    assert bodies == {"body1", "body2", "body3"}

    for note_id, entry in data.items():
        assert entry["created"] == note_id, (
            f"created field should match id for stable round-tripping; "
            f"id={note_id!r} created={entry['created']!r}"
        )


def test_list_coerces_malformed_fields(isolated_notes_home, capsys):
    isolated_notes_home.write_text(
        json.dumps(
            {
                "a": {"title": 123, "body": None, "created": 456},
                "b": {"title": None, "body": 789},
            }
        )
    )

    notes_mod.list_notes()
    out = capsys.readouterr().out
    assert "123" in out
    assert "456" in out
    assert "untitled" in out.lower()
    assert "789" in out


def test_delete_matches_numeric_title(isolated_notes_home, capsys):
    isolated_notes_home.write_text(json.dumps({"a": {"title": 123, "body": "body"}}))

    notes_mod.delete_note("23")

    assert "Deleted" in capsys.readouterr().out
    assert json.loads(isolated_notes_home.read_text("utf-8")) == {}
