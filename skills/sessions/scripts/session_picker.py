"""Read-only terminal selection for discovered sessions."""
import os
import sys

from session_table import GAP, cells, printable, shorten, wrapped_lines


class PickerError(RuntimeError):
    """The picker cannot use this terminal."""


def matches(row, query):
    return any(query in row[field].casefold() for field in ("title", "folder", "cwd"))


def visible_rows(entries, query, expanded):
    visible = []
    query = query.casefold()
    for row in entries:
        members = row.get("members", ())
        if matches(row, query):
            visible.append((row, None))
            if members and row["path"] in expanded:
                visible.extend((member, row) for member in members)
        elif members:
            visible.extend((member, None) for member in members if matches(member, query))
    return visible


def row_label(row, member, expanded, width):
    tool = row["tool"]
    if row.get("background"):
        tool += " (background)"
    if row.get("live"):
        tool += " (live)"
    if member:
        return "    " + GAP.join((row["last_active"], tool, printable(row["title"])))
    prefix = ""
    if "members" in row:
        prefix = "▾ " if expanded else "▸ "
    details = GAP.join((tool, row["folder"], row["last_active"]))
    available = width - cells(prefix)
    title_width = max(available // 2, available - cells(details) - len(GAP), 1)
    return prefix + shorten(printable(row["title"]), title_width) + GAP + details


def draw(screen, curses, visible, current, query, expanded, preview, scroll):
    height, columns = screen.getmaxyx()
    # Leave the last cell free. Writing it can scroll or raise on a small screen.
    width = max(1, columns - 1)
    screen.erase()

    def put(y, text, attr=0):
        if y < height and columns > 1:
            line = shorten(printable(text), width).encode(screen.encoding, "replace")
            screen.addstr(y, 0, line, attr)

    put(0, "Filter: " + query, curses.A_BOLD)
    slots = min(len(visible) or 1, max(1, (height - 3) // 2))
    start = max(0, current - slots + 1)
    for idx, (row, parent) in enumerate(visible[start:start + slots], start):
        attr = curses.A_REVERSE if idx == current else 0
        put(1 + idx - start, row_label(row, parent, row["path"] in expanded, width), attr)
    if not visible:
        put(1, "No matches")

    details = []
    if visible:
        row = visible[current][0]
        if "members" in row:
            details = [f"{len(row['members'])} runs. Press Enter to browse individual sessions."]
        else:
            details = preview(row)
    detail_start = slots + 2
    page = max(1, height - detail_start - 1)
    lines = [part for line in details for part in wrapped_lines(printable(line), width)]
    scroll = max(0, min(scroll, len(lines) - page))
    for i, line in enumerate(lines[scroll:scroll + page], detail_start):
        put(i, line)
    if height > 2:
        put(height - 1, "Esc cancel  ↑↓ move  Enter inspect/expand  ← collapse  PgUp/PgDn preview", curses.A_DIM)
    screen.refresh()
    return page, scroll


def run(screen, curses, entries, preview):
    try:
        curses.curs_set(0)
    except curses.error:  # Some terminals have no cursor-visibility capability.
        pass
    expanded = set()
    cache = {}

    def cached(row):
        try:
            stat = os.stat(row["path"])
        except OSError:
            cache.clear()
            return preview(row)
        key = (row["path"], stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)
        if key not in cache:
            cache.clear()
            cache[key] = preview(row)
        return cache[key]

    query = ""
    current = scroll = 0
    while True:
        visible = visible_rows(entries, query, expanded)
        current = max(0, min(current, len(visible) - 1))
        size = screen.getmaxyx()
        try:
            page, scroll = draw(screen, curses, visible, current, query, expanded, cached, scroll)
        except curses.error:
            if size != screen.getmaxyx():
                continue
            raise
        key = screen.get_wch()
        if key in ("\x1b", "\x03"):
            return None
        if key in (curses.KEY_PPAGE, curses.KEY_NPAGE):
            scroll += -page if key == curses.KEY_PPAGE else page
            continue
        if key == curses.KEY_RESIZE:
            continue
        scroll = 0
        if key == curses.KEY_DOWN:
            current += 1
        elif key == curses.KEY_UP:
            current -= 1
        elif key in (curses.KEY_BACKSPACE, "\x7f", "\b"):
            query = query[:-1]
            current = 0
        elif isinstance(key, str) and key.isprintable():
            query += key
            current = 0
        elif visible:
            row, parent = visible[current]
            if key == curses.KEY_LEFT:
                if parent:
                    current = next(i for i, (entry, _) in enumerate(visible) if entry is parent)
                expanded.discard((parent or row)["path"])
            elif key in (curses.KEY_RIGHT, curses.KEY_ENTER, "\r", "\n"):
                if "members" in row:
                    expanded.add(row["path"])
                    current += 1
                elif key != curses.KEY_RIGHT:
                    return row


def choose_session(entries, preview):
    """Return the chosen raw session row, or None when selection is cancelled."""
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise PickerError("pick requires an interactive terminal for input and output. Use list or search here.")
    try:
        import curses
    except ImportError as exc:
        raise PickerError("pick requires Python with curses support. Use list or search here.") from exc
    try:
        curses.setupterm(fd=sys.stdout.fileno())
        if not curses.tigetstr("cup"):
            raise PickerError("This terminal does not support cursor movement. Use list or search here.")
        return curses.wrapper(run, curses, entries, preview)
    except KeyboardInterrupt:
        return None
    except curses.error as exc:
        raise PickerError(f"Could not use the terminal for pick ({exc}). Use list or search here.") from exc
