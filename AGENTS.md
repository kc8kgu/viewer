# viewer

Terminal file viewer: a small Python curses TUI for reading text files with correct wide-character handling.

## Commands

```bash
# Install dependencies (Windows needs windows-curses)
pip install -r requirements.txt

# Run
python viewer.py <filepath>
```

Requires a real terminal (Windows Terminal, etc.). Curses will not work in non-TTY environments.

## Project layout

| Path | Purpose |
|------|---------|
| `viewer.py` | Entire application (single file) |
| `requirements.txt` | `wcwidth`; `windows-curses` on Windows only |

No test suite or build step. Keep changes focused and minimal.

## Architecture

- **`curses.wrapper(file_viewer, filepath)`** — entry into curses; `setup_locale()` must run before this.
- **`file_viewer(stdscr, filepath)`** — main loop: read UTF-8 file, render visible lines, handle input, draw status bar.
- **Width helpers** — `truncate_to_width`, `display_width`, `slice_from_column`, `pad_to_width` use `wcwidth` so CJK and combining characters count correctly in terminal columns.
- **`safe_addstr`** — clips text and catches `curses.error` instead of crashing on narrow terminals.
- **Scrolling** — vertical: `j`/`k`, arrows, PgUp/PgDn, Home/End, mouse wheel. Horizontal: Left/Right (`HSCROLL_STEP = 8`). Quit: `q`.
- **Windows Terminal** — `stdscr.touchwin()` before each `refresh()` avoids desync when the terminal scrollbar moves the underlying buffer.

Render failures surface on the status bar (`render_error`); any key dismisses the message.

## Conventions

- Python 3, stdlib + `wcwidth` only (plus `windows-curses` on Windows).
- Read text files as UTF-8 with `errors='replace'`.
- Prefer small, focused diffs. Do not split into modules unless asked.
- Match existing style: plain functions, module-level constants, minimal comments (only for non-obvious behavior).
- Do not add tests, docs, or refactors beyond what the task requires.

## Common pitfalls

- Call `setup_locale()` before `curses.wrapper`; wide characters and `TRUNC_MARKER` (`▶`) depend on it.
- Terminal width uses display columns, not `len(str)` — always go through the width helpers for drawing.
- On Windows, ensure `windows-curses` is installed or `import curses` fails.
