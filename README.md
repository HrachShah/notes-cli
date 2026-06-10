# Notes CLI

A simple command-line note-taking tool backed by a single JSON file in your
home directory. No database, no sync, no daemon — every note is a dict entry
in `~/.notescli/notes.json`, so you can `cat` it, `jq` it, or sync it with the
rest of your dotfiles.

## Install

```bash
# Just run it directly
python3 notes.py add "Groceries" "milk, eggs, bread"

# Or expose it on $PATH
ln -s "$(pwd)/notes.py" ~/.local/bin/notes
```

The tool only depends on the Python 3.10+ standard library, so there is no
`pip install` step and no virtualenv to maintain.

## Commands

### `add <title> <body>`

Create a new note. The note id is the current time with seconds precision
(ISO 8601), so adding two notes in the same second produces the same id and
the second add silently overwrites the first. Use `add` deliberately.

```bash
$ python3 notes.py add "Read later" "https://example.com/article"
Note saved: Read later
```

The body argument is everything after the title, so put quotes around multi-
word bodies in your shell.

### `list`

Print every note, newest first. Truncates the body to 80 characters with a
trailing `...` so the output stays scannable.

```bash
$ python3 notes.py list

[2026-06-10T13:45:00] Read later
  https://example.com/article

[2026-06-10T09:12:33] Groceries
  milk, eggs, bread...
```

### `delete <title-fragment>`

Delete the first note whose title contains `<title-fragment>` (case-insensitive).
There is no confirmation prompt and no undo — the entry is removed from
`notes.json` immediately.

```bash
$ python3 notes.py delete grocery
Deleted: Groceries
```

If no note matches, the command prints `No note found matching: <fragment>`
and exits successfully.

## Storage

Notes live in `~/.notescli/notes.json`. The directory and file are created
on first write. Set `NOTESCLI_HOME` in the environment to redirect the tool
at a different root (useful for tests, ephemeral containers, or per-project
note files):

```bash
export NOTESCLI_HOME=/tmp/notes
python3 notes.py add "scratch" "throwaway"
unset NOTESCLI_HOME
```

The on-disk format is a JSON object whose keys are ISO 8601 timestamps and
whose values are `{ "title": str, "body": str, "created": str }` dicts:

```json
{
  "2026-06-10T13:45:00": {
    "title": "Read later",
    "body": "https://example.com/article",
    "created": "2026-06-10T13:45:00"
  }
}
```

## Limitations

- One note per second. Two `add` calls in the same second overwrite each
  other because the timestamp is the key.
- `delete` matches on the first title fragment it finds. There is no
  multi-select and no confirmation.
- No encryption, no access control, no multi-device sync. The file is a
  plain JSON object readable by anything with read access to your home
  directory.
- The on-disk format is not a stable API. The keys and value shape can
  change between versions.
