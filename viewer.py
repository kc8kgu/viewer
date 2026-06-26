#!/usr/bin/env python3
import curses
import locale
import sys

from wcwidth import wcwidth

HSCROLL_STEP = 8


def truncate_to_width(s, width):
    """Truncate s to fit within `width` display columns, accounting for
    double-width (e.g. CJK) and zero-width (e.g. combining) characters.
    Returns (truncated, had_more)."""
    width = max(0, width)
    total = 0
    result = []
    for ch in s:
        w = wcwidth(ch)
        if w < 0:
            # Unprintable/control character; skip it rather than
            # miscounting its width.
            continue
        if total + w > width:
            return ''.join(result), True
        result.append(ch)
        total += w
    return ''.join(result), False


def file_viewer(stdscr, filepath):
    # Hide the terminal cursor
    curses.curs_set(0)

    # Enable mouse events to capture scroll wheel inputs and prevent terminal buffer scrolling
    curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)

    # Read file content safely. errors='replace' avoids crashing the whole
    # viewer when the file's encoding doesn't match the locale's default.
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    except Exception as e:
        stdscr.addstr(0, 0, f"Error opening file: {e}")
        stdscr.getch()
        return

    # Initialize variables
    scroll_pos = 0
    hscroll_pos = 0
    max_rows, max_cols = stdscr.getmaxyx()
    max_scroll = max(0, len(lines) - (max_rows - 1))

    def clamp(pos):
        return max(0, min(max_scroll, pos))

    key_actions = {
        ord('k'):          lambda: clamp(scroll_pos - 1),
        ord('j'):          lambda: clamp(scroll_pos + 1),
        curses.KEY_UP:     lambda: clamp(scroll_pos - 1),
        curses.KEY_DOWN:   lambda: clamp(scroll_pos + 1),
        curses.KEY_PPAGE:  lambda: clamp(scroll_pos - (max_rows - 2)),
        curses.KEY_NPAGE:  lambda: clamp(scroll_pos + (max_rows - 2)),
        curses.KEY_HOME:   lambda: 0,
        curses.KEY_END:    lambda: max_scroll,
    }

    while True:
        stdscr.clear()
        end_line = min(len(lines), scroll_pos + max_rows - 1)

        # Display file lines that fit on the screen
        for i in range(scroll_pos, end_line):
            line_content = lines[i].rstrip('\n\r')
            if hscroll_pos:
                line_content = line_content[hscroll_pos:]
            visible, has_more = truncate_to_width(line_content, max_cols - 1)
            if has_more:
                visible, _ = truncate_to_width(line_content, max(0, max_cols - 2))
                visible += '▶'
            try:
                stdscr.addstr(i - scroll_pos, 0, visible)
            except curses.error:
                pass

        # Draw a persistent status bar at the bottom
        stdscr.attron(curses.A_REVERSE)
        status_bar = (
            f"File: {filepath} | Lines {scroll_pos + 1}-{end_line} of {len(lines)} "
            f"| Col {hscroll_pos + 1} | Arrows/PGUP/PGDN/Home/End scroll, "
            f"Left/Right pan, q to quit"
        )
        try:
            stdscr.addstr(max_rows - 1, 0, status_bar.ljust(max_cols - 1)[:max_cols - 1])
        except curses.error:
            pass
        stdscr.attroff(curses.A_REVERSE)

        # Force a full repaint of every cell. Windows Terminal's scrollbar
        # scrolls the underlying console buffer directly, which desyncs
        # curses' diff-based redraw from what's actually on screen.
        stdscr.touchwin()
        stdscr.refresh()

        key = stdscr.getch()
        if key == ord('q'):
            break
        elif key == curses.KEY_RESIZE:
            max_rows, max_cols = stdscr.getmaxyx()
            max_scroll = max(0, len(lines) - (max_rows - 1))
            scroll_pos = clamp(scroll_pos)
        elif key == curses.KEY_LEFT:
            hscroll_pos = max(0, hscroll_pos - HSCROLL_STEP)
        elif key == curses.KEY_RIGHT:
            hscroll_pos = hscroll_pos + HSCROLL_STEP
        elif key == curses.KEY_MOUSE:
            try:
                _, _, _, _, bstate = curses.getmouse()
                step = max(1, max_rows // 4)
                if bstate & curses.BUTTON4_PRESSED:
                    scroll_pos = clamp(scroll_pos - step)
                elif bstate & curses.BUTTON5_PRESSED:
                    scroll_pos = clamp(scroll_pos + step)
            except curses.error:
                pass
        elif key in key_actions:
            result = key_actions[key]()
            if result is not None:
                scroll_pos = result


def main():
    if len(sys.argv) < 2:
        print("Usage: python viewer.py <filepath>")
        sys.exit(1)

    # Must be set before curses initializes the screen so multi-byte/wide
    # characters (e.g. the '▶' truncation marker, CJK text) render correctly.
    locale.setlocale(locale.LC_ALL, '')

    filepath = sys.argv[1]
    curses.wrapper(file_viewer, filepath)


if __name__ == "__main__":
    main()
