# Notes CLI

A simple command-line note-taking tool written in Python. Notes are stored as JSON in `~/.notescli/`.

## Features

- **Add notes**: Create notes with a title and body
- **List notes**: View all saved notes, newest first
- **Delete notes**: Remove notes by title search
- **Persistent storage**: Notes stored in `~/.notescli/notes.json`

## Usage

```bash
# Add a note
notes-cli add "My Note Title" "Note body text goes here"

# List all notes
notes-cli list

# Delete a note
notes-cli delete "My Note"
```

## Installation

```bash
pip install notes-cli
```

## Storage

Notes are stored in `~/.notescli/notes.json` as a JSON dictionary keyed by ISO timestamp.