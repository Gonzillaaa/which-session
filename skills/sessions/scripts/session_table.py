"""Render session rows in an interactive terminal using only the standard library."""
import unicodedata

GAP = "  "
HEADERS = ("Session", "Tool", "Folder", "Last active", "Full ID")


def printable(text):
    return "".join(c if c.isprintable() else " " for c in text)


def single_line(text):
    return " ".join(printable(text).split())


def char_width(char):
    if unicodedata.category(char) in {"Mn", "Me"}:
        return 0
    return 2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1


def cells(text):
    return sum(map(char_width, text))


def split_at_width(text, width):
    used = 0
    for index, char in enumerate(text):
        used += char_width(char)
        if used > width:
            return text[:index], text[index:]
    return text, ""


def shorten(text, width):
    if cells(text) <= width:
        return text
    prefix, _ = split_at_width(text, width - 1)
    return prefix.rstrip() + "…"


def wrapped_lines(text, width):
    while text:
        line, rest = split_at_width(text, width)
        if not line:  # A double-width character in a one-column terminal.
            line, rest = "…", text[1:]
        elif rest and not rest.startswith(" "):
            before, space, word = line.rpartition(" ")
            if space and before.strip():
                line, rest = before, word + rest
        yield line.rstrip()
        text = rest.lstrip()


def print_wrapped(text, width, indent=""):
    if width <= len(indent):
        indent = ""
    for line in wrapped_lines(text, width - len(indent)):
        print(indent + line)


def table_widths(data, columns, min_title):
    title, tool, folder, active, sid = [
        max(map(cells, values)) for values in zip(HEADERS, *data)
    ]
    available = columns - tool - active - sid - len(GAP) * (len(HEADERS) - 1)
    # Give up title space first. Switch layouts before either text column becomes unreadable.
    folder = min(folder, available - min(title, min_title))
    if folder < len("Folder"):
        return None
    return min(title, available - folder), tool, folder, active, sid


def print_aligned(values, widths):
    fields = []
    for text, width in zip(values, widths):
        field = shorten(text, width)
        fields.append(field + " " * (width - cells(field)))
    print(GAP.join(fields).rstrip())


def print_terminal_table(rows, columns, settings):
    data = []
    for row in rows:
        tool = row["tool"]
        if row["background"]:
            tool += " (background)"
        if row["live"]:
            tool += " (live)"
        title = shorten(single_line(row["title"]), settings["title_width"])
        data.append((title, tool, single_line(row["folder"]), row["last_active"], single_line(row["id"])))

    widths = table_widths(data, columns, settings["table_min_title_width"])
    if widths:
        print_aligned(HEADERS, widths)
    for index, (values, row) in enumerate(zip(data, rows)):
        if "members" in row:
            count = f"{len(row['members'])} runs"
            room = (widths[0] if widths else columns) - cells(" · " + count)
            title = shorten(single_line(row["job"]), room) + " · " + count if room > 0 else count
            values = (title, *values[1:])
        if widths:
            print_aligned(values, widths)
        else:
            if index:
                print()
            title, tool, folder, active, sid = values
            print(shorten(title, columns))
            print_wrapped(GAP.join((tool, folder, active)), columns)
            print(sid)
        if "match" in row:
            excerpt = shorten(single_line(row["match"]), settings["preview_width"])
            print_wrapped(f"{row['match_role']}: {excerpt}", columns, indent=GAP)
