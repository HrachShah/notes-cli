"""Tests for notes-cli."""

import json
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
    assert "y" not in data
    assert "x" in data


def test_load_notes_recovers_from_non_dict_file(isolated_notes_home):
    isolated_notes_home.write_text("[]")
    assert notes_mod.load_notes() == {}
    isolated_notes_home.write_text("null")
    assert notes_mod.load_notes() == {}
    isolated_notes_home.write_text('"a string"')
    assert notes_mod.load_notes() == {}


def test_cli_add_then_list_via_subprocess(tmp_path):
    """Smoke test the actual CLI script with a temp HOME."""
    notes_dir = tmp_path / ".notescli"
    notes_file = notes_dir / "notes.json"
    env = {
        "HOME": str(tmp_path),
        "PATH": "/usr/bin:/usr/local/bin",
    }
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
    env = {
        "HOME": str(tmp_path),
        "PATH": "/usr/bin:/usr/local/bin",
    }
    script = Path(__file__).resolve().parent.parent / "notes.py"
    result = subprocess.run(
        [sys.executable, str(script), "delete", ""],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "empty" in result.stderr.lower()


def test_add_same_second_notes_get_distinct_ids(isolated_notes_home):
    """Two notes saved in the same calendar second must not collide on
    the same storage key. The previous implementation used
    `datetime.now().isoformat(timespec='seconds')` as the note id, so a
    second add_note call in the same second overwrote the first note.
    """
    import time

    notes_mod.add_note("first", "body one")
    # Add a second note back-to-back so both fall inside the same second
    # on any reasonable clock. Mock the timestamp to be deterministic.
    notes_mod.add_note("second", "body two")
    data = json.loads(isolated_notes_home.read_text("utf-8"))
    assert len(data) == 2, f"expected 2 notes, got {len(data)}: {list(data)}"
    titles = sorted(n["title"] for n in data.values())
    assert titles == ["first", "second"]


def test_add_note_id_includes_human_readable_timestamp(isolated_notes_home):
    """The note id is the storage key, but the user-visible 'created'
    field stays a plain ISO timestamp so list() can show it as-is."""
    notes_mod.add_note("alpha", "body")
    data = json.loads(isolated_notes_home.read_text("utf-8"))
    [(note_id, note)] = list(data.items())
    # 'created' is human-readable, not a uuid
    assert note["created"] == note_id[:19], (
        f"expected 'created' to be the leading ISO seconds in the id, "
        f"got created={note['created']!r} id={note_id!r}"
    )
    assert "T" in note["created"]
