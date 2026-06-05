# Notes CLI

A small command-line tool for jotting down short notes, listing them, and deleting them by title. Backed by a single JSON file in your home directory.

## Install

```bash
git clone https://github.com/HrachShah/notes-cli.git
cd notes-cli
python3 notes.py --help
```

No dependencies beyond the Python 3 standard library.

## Usage

```bash
# Add a note
python3 notes.py add "Deploy checklist" "Push to staging, run smoke tests, then promote"

# List all notes (newest first)
python3 notes.py list

# Delete a note whose title contains the given substring (case-insensitive)
python3 notes.py delete "Deploy"
```

## Storage

Notes live at `~/.notescli/notes.json`. The file is plain JSON; you can read, back up, or migrate it with any text tool. If the file is missing or corrupted, the CLI starts fresh.

## Project layout

```
notes-cli/
├── notes.py       # Single-file CLI
└── README.md
```

## Why

I wanted a note-taking tool that does not require a database, a daemon, or an account. Everything lives in one Python file and one JSON file on disk. The CLI covers the three actions I actually use (add, list, delete) and nothing else.

## License

MIT
