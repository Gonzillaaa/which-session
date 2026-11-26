"""Read-only terminal selection for discovered sessions."""
import os
import sys

from session_table import (
    GAP,
    cells,
    group_title,
    printable,
    shorten,
    tool_label,
    wrapped_lines,
)


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


def metadata_widths(entries):
    widths = {label: len(label) for label in ("Tool", "Folder", "Last active")}
    for entry in entries:
        for row in entry.get("members") or (entry,):
            widths["Tool"] = max(widths["Tool"], cells(tool_label(row)))
            widths["Folder"] = max(widths["Folder"], cells(printable(row["folder"])))
            widths["Last active"] = max(widths["Last active"], cells(row["last_active"]))
    return widths


def picker_columns(width, metadata, settings):
    # Keep a readable title. Drop whole fields when the window is too narrow.
    for fields in (("Tool", "Folder", "Last active"), ("Tool", "Last active"), ("Last active",), ()):
        sizes = {field: metadata[field] for field in fields}
        if "Folder" in sizes:
            text_space = width - len(GAP) * len(fields) - sizes["Tool"] - sizes["Last active"]
            sizes["Folder"] = min(sizes["Folder"], max(len("Folder"), text_space // 2))
        available = width - len(GAP) * len(fields) - sum(sizes.values())
        minimum = settings["table_min_title_width"] if "Tool" in fields else len("Session")
        if "Folder" in sizes and available < minimum:
            reclaimed = min(minimum - available, sizes["Folder"] - len("Folder"))
            sizes["Folder"] -= reclaimed
            available += reclaimed
        if available >= minimum or not fields:
            return {"Session": min(settings["title_width"], available), **sizes}


def draw(screen, curses, visible, current, query, expanded, preview, scroll, metadata, settings):
    height, columns = screen.getmaxyx()
    # Leave the last cell free. Writing it can scroll or raise on a small screen.
    margin = len(GAP) if columns > len("Filter: ") + 2 * len(GAP) else 0
    width = max(1, columns - 2 * margin - 1)
    screen.erase()

    def put(y, text, attr=0, x=0):
        if y < height and x < width and columns > 1:
            line = shorten(printable(text), width - x).encode(screen.encoding, "replace")
            screen.addstr(y, margin + x, line, attr)

    roomy = height >= settings["picker_spaced_rows_min_height"]
    heading = 2 if roomy else 1
    stride = 2 if roomy else 1
    row_start = heading + 1
    list_height = max(1, (height - row_start) // 2)
    slots = min(len(visible) or 1, (list_height - 1) // stride + 1)
    start = max(0, current - slots + 1)
    count = f"{start + 1}–{start + slots} of {len(visible)}" if len(visible) > slots else ""
    filter_width = width - len(count) - len(GAP)
    if count and filter_width >= len("Filter: "):
        put(0, count, curses.A_DIM, width - len(count))
        put(0, shorten("Filter: " + query, filter_width), curses.A_BOLD)
    else:
        put(0, "Filter: " + query, curses.A_BOLD)

    widths = picker_columns(width, metadata, settings)

    def put_row(y, fields, selected=False, header=False):
        x = 0
        if selected:
            span = sum(widths.values()) + len(GAP) * (len(widths) - 1)
            put(y, " " * span, curses.A_REVERSE)
        for field, size in widths.items():
            attr = curses.A_REVERSE if selected else 0
            if header:
                attr |= curses.A_BOLD
            elif field != "Session" and not selected:
                attr |= curses.A_DIM
            put(y, shorten(fields[field], size), attr, x)
            x += size + len(GAP)

    put_row(heading, {field: field for field in widths}, header=True)
    for idx, (row, parent) in enumerate(visible[start:start + slots], start):
        title = printable(row["title"])
        if parent:
            if "Last active" not in widths:
                title = row["last_active"] + GAP + title
            title = GAP + title
        elif "members" in row:
            marker = "▾ " if row["path"] in expanded else "▸ "
            title = marker + group_title(row, widths["Session"] - cells(marker))
        fields = {"Session": title, "Tool": tool_label(row), "Folder": printable(row["folder"]),
                  "Last active": row["last_active"]}
        put_row(row_start + (idx - start) * stride, fields, selected=idx == current)
    if not visible:
        put(row_start, "No matches")

    details = []
    preview_label = "Preview"
    if visible:
        row = visible[current][0]
        if "Tool" not in widths:
            preview_label += " · " + tool_label(row)
        if "Folder" not in widths and row["folder"]:
            preview_label += " · " + printable(row["folder"])
        if "Last active" not in widths:
            preview_label += " · " + row["last_active"]
        if "members" in row:
            details = [f"{len(row['members'])} runs. Press Enter to browse individual sessions."]
        else:
            details = preview(row)
    divider = row_start + (slots - 1) * stride + 2
    detail_start = divider + 1
    if details and detail_start < height - 1:
        put(divider, preview_label + " " + "─" * max(0, width - cells(preview_label) - 1), curses.A_DIM)
    page = max(1, height - detail_start - 1)
    lines = [part for line in details for part in wrapped_lines(printable(line), width)]
    scroll = max(0, min(scroll, len(lines) - page))
    for i, line in enumerate(lines[scroll:scroll + page], detail_start):
        put(i, line)
    if height > 2:
        hints = ["Esc cancel"]
        if visible:
            row, parent = visible[current]
            hints.append("Enter expand" if "members" in row else "Enter inspect")
            if len(lines) > page:
                hints.append("PgUp/Dn")
            hints.append("↑↓ move")
            if parent or row["path"] in expanded:
                hints.append("← collapse")
        footer = ""
        for hint in hints:
            candidate = GAP.join(filter(None, (footer, hint)))
            if cells(candidate) <= width:
                footer = candidate
        put(height - 1, footer, curses.A_DIM)
    screen.refresh()
    return page, scroll


def run(screen, curses, entries, preview, settings):
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
    metadata = metadata_widths(entries)
    while True:
        visible = visible_rows(entries, query, expanded)
        current = max(0, min(current, len(visible) - 1))
        size = screen.getmaxyx()
        try:
            page, scroll = draw(screen, curses, visible, current, query, expanded, cached, scroll, metadata, settings)
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


def choose_session(entries, preview, settings):
    """Return the chosen raw session row, or None when selection is cancelled."""
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise PickerError("Keyboard browsing requires a terminal for input and output.")
    try:
        import curses
    except ImportError as exc:
        raise PickerError("Keyboard browsing requires Python with curses support.") from exc
    try:
        curses.setupterm(fd=sys.stdout.fileno())
        if not curses.tigetstr("cup"):
            raise PickerError("This terminal does not support cursor movement.")
        return curses.wrapper(run, curses, entries, preview, settings)
    except KeyboardInterrupt:
        return None
    except curses.error as exc:
        raise PickerError(f"Could not open the session browser ({exc}).") from exc
