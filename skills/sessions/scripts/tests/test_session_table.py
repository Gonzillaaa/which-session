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
from datetime import datetime, timezone
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
            process = subprocess.Popen([*CLI, *args], stdout=output)
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
