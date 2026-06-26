# viewer

A small terminal file viewer built with Python curses. It reads UTF-8 text files and renders them with correct wide-character handling (CJK, combining marks, and similar).

## Requirements

- Python 3
- A real terminal (Windows Terminal, iTerm2, etc.). Curses does not work in non-TTY environments.

## Install

```bash
pip install -r requirements.txt
```

On Windows, `requirements.txt` installs `windows-curses` because curses is not in the standard library there.

## Usage

```bash
python viewer.py <filepath>
```

Example:

```bash
python viewer.py README.md
```

## Controls

| Key | Action |
|-----|--------|
| `j` / `k` or ↑ / ↓ | Scroll up / down one line |
| PgUp / PgDn | Scroll up / down one page |
| Home / End | Jump to start / end of file |
| ← / → | Pan horizontally (8 columns) |
| Mouse wheel | Scroll up / down |
| `q` | Quit |

Long lines are truncated with a `▶` marker when they extend past the right edge of the screen.

## Features

- UTF-8 input with invalid bytes replaced instead of crashing
- Display width uses terminal columns, not Python string length
- Terminal resize support
- Status bar shows file path, line range, and horizontal scroll position
- Render errors appear on the status bar; press any key to dismiss

## Project layout

| Path | Purpose |
|------|---------|
| `viewer.py` | Application source |
| `requirements.txt` | Runtime dependencies |
