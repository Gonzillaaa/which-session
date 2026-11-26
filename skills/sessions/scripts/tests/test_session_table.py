import errno
import fcntl
import io
import json
import os
import pty
import struct
import subprocess
import sys
import termios
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

CLI = [sys.executable, str(Path(__file__).resolve().parents[1] / "sessions.py")]
IDS = [f"12345678-1234-4321-8000-{i:012d}" for i in range(2)]
TITLES = ["調査 e\u0301 " + "long title " * 9, "Fix retry"]
FOLDER = "paper-planes"
MESSAGE = "Compare the retry policy before continuing the rollout."


@pytest.fixture(autouse=True)
def history(tmp_path, monkeypatch):
    project = tmp_path / "claude/projects/demo"
    project.mkdir(parents=True)
    for sid, title in zip(IDS, TITLES):
        records = [
            {"type": "custom-title", "customTitle": title},
            {"type": "user", "cwd": f"/work/{FOLDER}", "message": {"content": MESSAGE},
             "timestamp": datetime.now(timezone.utc).isoformat()},
        ]
        (project / f"{sid}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "claude"))
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex"))
    monkeypatch.delenv("COLUMNS", raising=False)


def terminal_output(columns, *args):
    master, slave = pty.openpty()
    with os.fdopen(master, "rb", buffering=0) as screen:
        with os.fdopen(slave, "wb") as output:
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 24, columns, 0, 0))
            process = subprocess.Popen([*CLI, *args], stdin=subprocess.DEVNULL, stdout=output)
        chunks = []
        with process:
            try:
                while chunk := screen.read(io.DEFAULT_BUFFER_SIZE):
                    chunks.append(chunk)
            except OSError as exc:
                if exc.errno != errno.EIO:  # Linux signals EOF on a PTY with EIO.
                    raise
            assert process.wait() == 0
    return b"".join(chunks).decode().splitlines()


def test_terminal_aligns_columns_and_keeps_full_ids():
    lines = terminal_output(108, "list")
    header = lines[0]
    assert header.startswith("Session")
    for sid in IDS:
        line, = (line for line in lines if sid in line)
        # Each ideograph takes two cells and the combining accent takes zero.
        visible = line.replace("調査", "xxxx").replace("\u0301", "")
        assert visible.index("claude") == header.index("Tool")
        assert visible.index(FOLDER) == header.index("Folder")
        assert visible.index(sid) == header.index("Full ID")
        assert len(visible) <= 108 and "`" not in line
    assert "…" in next(line for line in lines if IDS[0] in line)


@pytest.mark.parametrize("columns", [40, 80])
def test_narrow_search_preserves_ids_and_matching_passages(columns):
    lines = terminal_output(columns, "search", "retry policy")
    for sid in IDS:
        assert any(line.strip() == sid for line in lines)
    assert " ".join(" ".join(lines).split()).count("user: " + MESSAGE) == len(IDS)
    for line in lines:
        assert len(line.replace("調査", "xxxx").replace("\u0301", "")) <= columns


def test_piped_and_json_outputs_still_work_for_agents():
    markdown = subprocess.check_output([*CLI, "search", "retry policy"], text=True)
    assert markdown.startswith("| Session |") and "| Match |" in markdown
    for sid in IDS:
        assert f"`{sid}`" in markdown
    rows = json.loads("\n".join(terminal_output(40, "list", "--json")))
    assert {row["id"]: row["title"] for row in rows} == dict(zip(IDS, TITLES))


def test_terminal_groups_runs_before_limiting_but_flat_views_keep_each_session(tmp_path):
    project = tmp_path / "claude/projects/demo"
    prompt = "Read and execute system/skills/hb/prompts/heartbeat-runner.md for adapter scope: local"
    runs = [f"11111111-1111-4111-8111-{i:012d}" for i in range(2)]
    for index, sid in enumerate(runs):
        stamp = datetime.now(timezone.utc) + timedelta(seconds=index + 1)
        record = {"type": "user", "cwd": f"/work/{FOLDER}", "timestamp": stamp.isoformat(),
                  "message": {"content": prompt}}
        (project / f"{sid}.jsonl").write_text(json.dumps(record) + "\n")
    table = "\n".join(terminal_output(140, "list", "--limit", "2"))
    assert "Heartbeat runner · 2 runs" in table and runs[1] in table and runs[0] not in table
    assert sum(sid in table for sid in IDS) == 1
    assert "2 runs" in "\n".join(terminal_output(96, "list", "--limit", "2"))
    for args in (("list", "--ungrouped"), ("search", "adapter scope")):
        output = "\n".join(terminal_output(140, *args))
        assert all(sid in output for sid in runs) and "2 runs" not in output
    flat = subprocess.check_output([*CLI, "list"], text=True)
    assert all(sid in flat for sid in runs)
    rows = json.loads(subprocess.check_output([*CLI, "list", "--json"]))
    assert len(rows) == 4 and all("members" not in row and "job" not in row for row in rows)


def test_redirected_alias_prints_the_same_markdown_as_list():
    def redirected(command):
        return subprocess.check_output([*CLI, command], stdin=subprocess.DEVNULL, text=True)

    markdown = redirected("pick")
    assert markdown == redirected("list") and all(f"`{sid}`" in markdown for sid in IDS)


def test_inspection_prints_terminal_safe_metadata(tmp_path):
    sid = IDS[0]
    path = tmp_path / "claude/projects/demo" / (sid + ".jsonl")
    record = {"type": "user", "cwd": "/work/\x1b[2Jproject", "gitBranch": "feature/\x07cleanup",
              "message": {"content": "Investigate the build"}}
    path.write_text(json.dumps(record) + "\n")
    inspection = subprocess.check_output([*CLI, "inspect", sid, "--file", str(path)], text=True)
    assert "project" in inspection and "cleanup" in inspection
    assert "\x1b" not in inspection and "\x07" not in inspection
