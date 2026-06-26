#!/usr/bin/env python3
import curses
import locale
import sys

from wcwidth import wcwidth

HSCROLL_STEP = 8
TRUNC_MARKER = '▶'


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


def display_width(s):
    """Return the display width of s in terminal columns."""
    total = 0
    for ch in s:
        w = wcwidth(ch)
        if w > 0:
            total += w
    return total


def slice_from_column(s, col):
    """Return the suffix of s that starts at display column `col`."""
    if col <= 0:
        return s
    total = 0
    for i, ch in enumerate(s):
        w = wcwidth(ch)
        if w < 0:
            continue
        if total >= col:
            return s[i:]
        total += w
    return ''


def trunc_marker_width():
    w = wcwidth(TRUNC_MARKER)
    return w if w > 0 else 1


def pad_to_width(s, width):
    """Pad s with spaces to fill `width` display columns."""
    visible, _ = truncate_to_width(s, width)
    pad_cols = width - display_width(visible)
    if pad_cols > 0:
        visible += ' ' * pad_cols
    return visible


def safe_addstr(win, y, x, text, max_cols):
    """Draw text clipped to max_cols. Returns an error message on failure."""
    if max_cols <= 0:
        return "terminal too narrow"
    visible, _ = truncate_to_width(text, max_cols)
    try:
        win.addstr(y, x, visible)
    except curses.error as e:
        return str(e) or "display error"
    return None


def format_line_range(scroll_pos, end_line, num_lines):
    if num_lines == 0:
        return "Lines 0 of 0"
    if end_line <= scroll_pos:
        return f"Line {scroll_pos + 1} of {num_lines}"
    return f"Lines {scroll_pos + 1}-{end_line} of {num_lines}"


def setup_locale():
    # Must be set before curses initializes the screen so multi-byte/wide
    # characters (e.g. the truncation marker, CJK text) render correctly.
    for loc in ('', 'C.UTF-8', 'en_US.UTF-8', 'C'):
        try:
            locale.setlocale(locale.LC_ALL, loc)
            return
        except locale.Error:
            continue


def file_viewer(stdscr, filepath):
    # Hide the terminal cursor
    curses.curs_set(0)

    # Enable mouse events to capture scroll wheel inputs and prevent terminal buffer scrolling
    curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)

    # Read as UTF-8; invalid bytes are replaced rather than crashing the viewer.
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
    max_scroll = 0
    max_hscroll = 0
    marker_w = trunc_marker_width()

    def update_dimensions():
        nonlocal max_scroll, max_hscroll
        max_scroll = max(0, len(lines) - (max_rows - 1))
        visible_cols = max(1, max_cols - 1)
        if lines:
            max_w = max(display_width(line.rstrip('\n\r')) for line in lines)
            max_hscroll = max(0, max_w - visible_cols)
        else:
            max_hscroll = 0

    def clamp_vscroll(pos):
        return max(0, min(max_scroll, pos))

    def clamp_hscroll(pos):
        return max(0, min(max_hscroll, pos))

    update_dimensions()
    render_error = None

    key_actions = {
        ord('k'):          lambda: clamp_vscroll(scroll_pos - 1),
        ord('j'):          lambda: clamp_vscroll(scroll_pos + 1),
        curses.KEY_UP:     lambda: clamp_vscroll(scroll_pos - 1),
        curses.KEY_DOWN:   lambda: clamp_vscroll(scroll_pos + 1),
        curses.KEY_PPAGE:  lambda: clamp_vscroll(scroll_pos - max(1, max_rows - 2)),
        curses.KEY_NPAGE:  lambda: clamp_vscroll(scroll_pos + max(1, max_rows - 2)),
        curses.KEY_HOME:   lambda: 0,
        curses.KEY_END:    lambda: max_scroll,
    }

    while True:
        stdscr.clear()
        end_line = min(len(lines), scroll_pos + max_rows - 1)
        content_width = max(1, max_cols - 1)

        # Display file lines that fit on the screen
        for i in range(scroll_pos, end_line):
            line_content = lines[i].rstrip('\n\r')
            if hscroll_pos:
                line_content = slice_from_column(line_content, hscroll_pos)
            visible, has_more = truncate_to_width(line_content, content_width)
            if has_more:
                visible, _ = truncate_to_width(
                    line_content, max(0, content_width - marker_w))
                visible += TRUNC_MARKER
            err = safe_addstr(stdscr, i - scroll_pos, 0, visible, content_width)
            if err and render_error is None:
                render_error = f"Line {i + 1}: {err}"

        # Draw a persistent status bar at the bottom
        stdscr.attron(curses.A_REVERSE)
        status_width = max(0, max_cols - 1)
        if render_error:
            status_bar = f"! {render_error} (any key to dismiss)"
        else:
            line_info = format_line_range(scroll_pos, end_line, len(lines))
            status_bar = (
                f"File: {filepath} | {line_info} "
                f"| Col {hscroll_pos + 1} | Arrows/PGUP/PGDN/Home/End scroll, "
                f"Left/Right pan, q to quit"
            )
        err = safe_addstr(
            stdscr, max_rows - 1, 0, pad_to_width(status_bar, status_width), status_width)
        if err and render_error is None:
            render_error = f"Status bar: {err}"
        stdscr.attroff(curses.A_REVERSE)

        # Force a full repaint of every cell. Windows Terminal's scrollbar
        # scrolls the underlying console buffer directly, which desyncs
        # curses' diff-based redraw from what's actually on screen.
        stdscr.touchwin()
        stdscr.refresh()

        key = stdscr.getch()
        if render_error is not None:
            render_error = None
        if key == ord('q'):
            break
        elif key == curses.KEY_RESIZE:
            max_rows, max_cols = stdscr.getmaxyx()
            update_dimensions()
            scroll_pos = clamp_vscroll(scroll_pos)
            hscroll_pos = clamp_hscroll(hscroll_pos)
        elif key == curses.KEY_LEFT:
            hscroll_pos = clamp_hscroll(hscroll_pos - HSCROLL_STEP)
        elif key == curses.KEY_RIGHT:
            hscroll_pos = clamp_hscroll(hscroll_pos + HSCROLL_STEP)
        elif key == curses.KEY_MOUSE:
            try:
                _, _, _, _, bstate = curses.getmouse()
                step = max(1, max_rows // 4)
                if bstate & curses.BUTTON4_PRESSED:
                    scroll_pos = clamp_vscroll(scroll_pos - step)
                elif bstate & curses.BUTTON5_PRESSED:
                    scroll_pos = clamp_vscroll(scroll_pos + step)
            except curses.error:
                pass
        elif key in key_actions:
            scroll_pos = key_actions[key]()


def main():
    if len(sys.argv) < 2:
        print("Usage: python viewer.py <filepath>")
        sys.exit(1)

    setup_locale()

    filepath = sys.argv[1]
    curses.wrapper(file_viewer, filepath)


if __name__ == "__main__":
    main()
