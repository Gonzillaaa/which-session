import fcntl
import json
import os
import pty
import select
import struct
import subprocess
import sys
import termios
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
CLI = [sys.executable, str(SCRIPTS / "sessions.py")]
HARNESS = """
import json, sys
from session_picker import choose_session
from sessions import SETTINGS
def preview(row):
    return ["Full ID: " + row["id"], "Last request: " + row["title"]]
selected = choose_session(json.loads(sys.argv[1]), preview, SETTINGS)
print("PICKED=" + (selected["path"] if selected else "cancel"))
"""


def row(title, path):
    return {"id": path, "title": title, "tool": "codex", "cwd": "/work/planes", "folder": "planes",
            "path": path, "last_active": "2026-01-01 10:00"}


def keyboard_run(command, keys, *, size=(24, 100), env=None):
    actions = deque([(b"Filter", keys)] if isinstance(keys, bytes) else keys)
    master, slave = pty.openpty()
    with os.fdopen(master, "r+b", buffering=0), os.fdopen(slave, "r+b", buffering=0):
        original = termios.tcgetattr(slave)
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", *size, 0, 0))
        child_env = {**os.environ, "TERM": "xterm-256color", **(env or {})}
        with subprocess.Popen(command, cwd=SCRIPTS, stdin=slave, stdout=slave, stderr=slave, env=child_env) as child:
            output = bytearray()
            deadline = time.monotonic() + 10
            try:
                while time.monotonic() < deadline:
                    ready, _, _ = select.select([master], [], [], 0.05)
                    if ready:
                        output.extend(os.read(master, 8192))
                    elif child.poll() is not None:
                        break
                    if actions and actions[0][0] in output:
                        _, action = actions.popleft()
                        os.write(master, action() if callable(action) else action)
                else:
                    pytest.fail(f"picker timed out: {bytes(output)!r}")
            finally:
                if child.poll() is None:
                    child.kill()
            assert child.wait() == 0, bytes(output)
        restored = termios.tcgetattr(slave)
        # macOS marks input pending when returning to canonical mode.
        restored[3] &= ~termios.PENDIN
        original[3] &= ~termios.PENDIN
        assert restored == original
        return bytes(output)


@pytest.fixture
def entries():
    runs = [row("Routine run", "latest"), row("Historical audit", "older")]
    return [dict(runs[0], title="Runner · 2 runs", job="Runner", members=runs), row("Deploy", "manual")]


@pytest.mark.parametrize(("keys", "expected"), [
    (b"\r\x1bOB\r", "older"),  # Enter the group, then move to the older run.
    (b"\x1bOC\x1bOD\x1bOB\r", "manual"),  # Expand, collapse, move to the next entry.
    (b"hISTorical\r", "older"),  # A concrete member may match even if the group title does not.
])
def test_group_navigation_and_filtering(entries, keys, expected):
    output = keyboard_run([sys.executable, "-c", HARNESS, json.dumps(entries)], keys)
    assert b"PICKED=" + expected.encode() in output


def test_expanded_runs_show_their_dates_in_a_narrow_terminal(entries):
    latest, older = entries[0]["members"]
    latest["last_active"] = "2026-01-12 10:10"
    older["last_active"] = "2026-01-10 08:30"
    output = keyboard_run([sys.executable, "-c", HARNESS, json.dumps(entries)], b"\r\x1b", size=(20, 36))
    assert latest["last_active"].encode() in output and older["last_active"].encode() in output


def picker_frame(entries, size):
    # Read the cells from a real curses window, independently of its ANSI update strategy.
    script = """
import curses, json, sys
from session_picker import draw, metadata_widths, visible_rows
from sessions import SETTINGS
entries = json.loads(sys.argv[1])
rows = visible_rows(entries, "", set())
def capture(screen):
    draw(screen, curses, rows, 0, "", set(), lambda row: ["Last request: Continue"], 0, metadata_widths(entries), SETTINGS)
    return [screen.instr(y, 0).decode().rstrip() for y in range(screen.getmaxyx()[0])]
print("FRAME=" + json.dumps(curses.wrapper(capture)))
"""
    output = keyboard_run([sys.executable, "-c", script, json.dumps(entries)], [], size=size)
    return json.loads(output.split(b"FRAME=")[-1])


@pytest.mark.parametrize("size", [(28, 110), (15, 80)])
def test_picker_columns_and_preview_have_distinct_positions(size):
    entries = [row("Short", "a"), row("A much longer session title", "b")]
    entries[1].update(tool="claude", folder="workbench")
    lines = picker_frame(entries, size)
    header = next(line for line in lines if "Session" in line and "Tool" in line)
    first = next(line for line in lines if "Short" in line)
    second = next(line for line in lines if "A much longer" in line)
    assert header.index("Tool") == first.index("codex") == second.index("claude")
    assert header.index("Folder") == first.index("planes") == second.index("workbench")
    assert header.index("Last active") == first.index("2026") == second.index("2026")
    assert lines.index(second) - lines.index(first) == (2 if size[0] == 28 else 1)
    preview = next(i for i, line in enumerate(lines) if "Preview" in line)
    assert lines.index(second) < preview < next(i for i, line in enumerate(lines) if "Last request" in line)


def test_narrow_picker_moves_tool_and_folder_to_selected_preview():
    lines = picker_frame([row("Spring release", "id")], (16, 44))
    heading = next(line for line in lines if "Session" in line)
    assert "Last active" in heading and "Tool" not in heading and "Folder" not in heading
    preview = next(line for line in lines if "Preview" in line)
    assert "codex" in preview and "planes" in preview


def test_group_size_fits_when_its_title_is_shortened(entries):
    group = entries[0]
    group["job"] = "Weekly review and maintenance"
    group["title"] = group["job"] + " · 2 runs"
    lines = picker_frame(entries, (20, 52))
    assert any("▸" in line and "2 runs" in line for line in lines)


def test_cancel_from_empty_results_restores_small_terminal():
    entries = [row("Report\x1b]2;UNTRUSTED\x07", "sample")]
    output = keyboard_run([sys.executable, "-c", HARNESS, json.dumps(entries)], b"xyz\r\x1b", size=(6, 30))
    assert b"No matches" in output and b"PICKED=cancel" in output
    assert b"\x1b]2;UNTRUSTED" not in output


@pytest.mark.parametrize("command", ["list", "pick"])
def test_list_inspects_selected_copy_from_real_transcripts(tmp_path, command):
    session_id = "11111111-2222-4333-8444-555555555555"
    claude = tmp_path / "claude"
    for project, phrase in (("planes", "First project"), ("boats", "Selected restore")):
        folder = claude / "projects" / project
        folder.mkdir(parents=True)
        record = {"type": "user", "cwd": f"/work/{project}", "message": {"content": phrase},
                  "timestamp": datetime.now(timezone.utc).isoformat()}
        (folder / f"{session_id}.jsonl").write_text(json.dumps(record) + "\n")
    output = keyboard_run([*CLI, command, "--all"], b"boats\r",
                          env={"CLAUDE_CONFIG_DIR": str(claude), "CODEX_HOME": str(tmp_path / "codex")})
    inspection = output.split(b"id: " + session_id.encode() + b"\r\n")[-1]
    assert b"folder: /work/boats" in inspection and b"title: Selected restore" in inspection
    assert b"cannot specify this file" in inspection and b"claude --resume" not in inspection


def test_list_browses_past_the_print_limit_and_can_still_print_a_table(tmp_path):
    env = {"CLAUDE_CONFIG_DIR": str(tmp_path / "claude"), "CODEX_HOME": str(tmp_path / "codex")}
    project = tmp_path / "claude/projects/demo"
    project.mkdir(parents=True)
    limit = json.loads((SCRIPTS / "settings.json").read_text())["limit"]
    stamp = datetime.now(timezone.utc).isoformat()
    for i in range(limit + 1):
        record = {"type": "user", "cwd": "/work/demo", "timestamp": stamp,
                  "message": {"content": f"Session number {i}"}}
        (project / f"00000000-0000-4000-8000-{i:012d}.jsonl").write_text(json.dumps(record) + "\n")

    # Equal timestamps sort by descending ID, putting session zero beyond the printed limit.
    result = keyboard_run([*CLI, "list"], b"number 0\r", env=env)
    assert b"title: Session number 0" in result
    limited = keyboard_run([*CLI, "list", "--limit", "1"], b"number 0\x1b", env=env)
    assert b"No matches" in limited
    for args, term in [(["--plain"], "xterm-256color"), ([], "dumb"), ([], "no-such-terminal")]:
        output = keyboard_run([*CLI, "list", *args], [], env={**env, "TERM": term})
        assert f"{limit} of {limit + 1} sessions".encode() in output and b"Filter:" not in output
    rows = json.loads(keyboard_run([*CLI, "list", "--json"], [], env=env))
    assert len(rows) == limit and rows[0]["title"] == f"Session number {limit}"


def test_preview_refreshes_when_the_selected_transcript_changes_or_disappears(tmp_path):
    claude = tmp_path / "claude"
    project = claude / "projects" / "planes"
    project.mkdir(parents=True)
    path = project / "11111111-2222-4333-8444-555555555555.jsonl"

    def append(phrase):
        with path.open("a") as history:
            record = {"type": "user", "cwd": "/work/planes", "message": {"content": phrase},
                      "timestamp": datetime.now(timezone.utc).isoformat()}
            history.write(json.dumps(record) + "\n")
        return b"\x7f"

    def remove_transcript():
        path.unlink()
        return b"\x7f"

    append("Initial request")
    steps = [(b"Last request: Initial", lambda: append("Ship the planes")),
             (b"Ship the planes", remove_transcript), (b"Cannot read transcript:", b"\x1b")]
    output = keyboard_run([*CLI, "list", "--all"], steps,
                          env={"CLAUDE_CONFIG_DIR": str(claude), "CODEX_HOME": str(tmp_path / "codex")})
    assert b"Cannot read transcript:" in output
