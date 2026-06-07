# Notes CLI

A small, dependency-free command-line tool for jotting down notes that you can
reach from any shell. Notes are stored as JSON under `~/.notescli/notes.json`,
so they're plain text, easy to back up, and editable by hand if you ever need
to merge or audit them.

## Why a separate tool?

There are plenty of GUI note apps. This one is for the moments when you have a
terminal already open and just want to capture a thought without switching
context. Three subcommands is all it takes:

- `notes-cli add <title> <body...>` — record a note
- `notes-cli list` — print every note, newest first
- `notes-cli delete <title>` — remove the first note whose title matches

The body is captured with `nargs="+"`, so a title and a multi-word body work
the way you'd expect:

```text
$ notes-cli add "groceries" "buy milk and bread"
Note saved: groceries
```

## Storage

Each note is keyed by an ISO-8601 timestamp (`datetime.now().isoformat(timespec="seconds")`),
so the JSON file looks roughly like:

```json
{
  "2026-06-07T07:35:00": {
    "title": "groceries",
    "body": "buy milk and bread",
    "created": "2026-06-07T07:35:00"
  }
}
```

The `add` command writes the file, and `list` / `delete` read it back. Reading
is wrapped in a `try/except (json.JSONDecodeError, IOError)` so a half-written
file (or one with invalid JSON) doesn't crash the CLI — it just behaves like
there are no notes yet. `save_notes` raises on `OSError` so the caller can
decide what to do if the disk is full or the path isn't writable.

## Where it lives

By default the tool stores notes in `~/.notescli/notes.json`. The directory is
created on first write. You can move that file between machines with a plain
`scp`/`rsync`; the format is stable.

## Requirements

Python 3.10+ (uses PEP 604 `dict[str, dict]` and PEP 604-style type hints in
docstrings). No third-party dependencies.

## Running

```text
$ python3 notes.py --help
$ python3 notes.py add "title" "body text..."
$ python3 notes.py list
$ python3 notes.py delete "title"
```

## Tests

There aren't any yet — the CLI is small enough to test by hand, and the
behaviors (save → list → delete) are obvious from the help text. If you add
features, please add tests too.
