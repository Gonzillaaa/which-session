import json
import os
import shlex
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "sessions.py"
SID = "11111111-2222-4333-8444-555555555555"


@pytest.fixture(params=["claude", "codex"])
def sample(request, tmp_path, monkeypatch):
    agent = request.param
    claude, codex = tmp_path / "claude", tmp_path / "codex"
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(claude))
    monkeypatch.setenv("CODEX_HOME", str(codex))
    path = (claude / "projects/demo" / (SID + ".jsonl") if agent == "claude" else
            codex / "sessions/2026/01/01" / ("rollout-test-" + SID + ".jsonl"))
    path.parent.mkdir(parents=True)
    cwd = Path("/work/team's draft $(demo)")

    def emit(kind, value, days=0, stamp=True):
        if agent == "claude":
            event = {"type": kind, "cwd": str(cwd), "message": {"content": value}}
        else:
            payload = ({"type": "message", "role": kind, "content": [{"type": "input_text" if kind == "user" else "output_text", "text": value}]}
                       if kind in {"user", "assistant"} else value)
            event = {"type": "response_item", "payload": payload}
        if stamp:
            event["timestamp"] = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with path.open("a") as stream:
            stream.write(json.dumps(event) + "\n")

    if agent == "codex":
        path.write_text(json.dumps({"type": "session_meta", "payload": {"id": SID, "cwd": str(cwd)}}) + "\n")

    def cli(*args, ok=True):
        result = subprocess.run([sys.executable, str(SCRIPT), *args], text=True, capture_output=True)
        assert (result.returncode == 0) == ok, result.stderr
        return result.stdout + result.stderr

    return agent, path, cwd, emit, cli


def test_activity_uses_latest_conversation_time_and_never_fresh_mtime(sample):
    agent, path, cwd, emit, cli = sample
    emit("user", "old work", 30)
    assert json.loads(cli("list", "--days", "1", "--json")) == []
    emit("assistant", "current reply")
    emit("user", "out-of-order record", 29)
    os.utime(path, (1000, 1000))
    row, = json.loads(cli("list", "--days", "1", "--json"))
    assert row["id"] == SID and row["live"] is False
    assert row["last_active"].startswith(datetime.now().strftime("%Y-%m-%d"))


def test_undated_activity_is_explicit(sample):
    agent, path, cwd, emit, cli = sample
    emit("user", "legacy message", stamp=False)
    assert json.loads(cli("list", "--json")) == []
    row, = json.loads(cli("list", "--all", "--json"))
    assert row["last_active"] == "unknown" and not row["live"]
    assert json.loads(cli("search", "legacy", "--all", "--json"))[0]["match_epoch"] is None


def test_phrase_search_scope_excerpt_and_role(sample):
    agent, path, cwd, emit, cli = sample
    emit("user", "unrelated title")
    emit("assistant", "long introduction " * 20 + "Email\n  draft is ready.")
    emit("user", "an older EMAIL DRAFT", 20)
    hidden = "<system-reminder>hidden phrase</system-reminder>" if agent == "claude" else "<environment_context>hidden phrase</environment_context>"
    emit("user", hidden)
    rows = json.loads(cli("search", "email draft", "--source", agent, "--folder", cwd.name, "--all", "--json"))
    row, = rows
    assert row["match_role"] == "assistant" and "Email draft" in row["match"]
    assert json.loads(cli("search", "hidden phrase", "--json", "--all")) == []
    assert json.loads(cli("search", "older EMAIL", "--days", "1", "--all", "--json")) == []
    assert json.loads(cli("search", "Email draft", "--folder", "unrelated-dir", "--all", "--json")) == []
    cli("search", "   ", ok=False)


def test_inspection_names_outstanding_target_and_quotes_resume(sample):
    agent, path, cwd, emit, cli = sample
    emit("user", "update the file")
    if agent == "claude":
        emit("assistant", [{"type": "tool_use", "id": "t", "name": "Write", "input": {"file_path": "draft notes.md", "content": "PRIVATE_PAYLOAD"}}])
    else:
        emit("tool", {"type": "custom_tool_call", "call_id": "t", "name": "apply_patch", "input": "*** Begin Patch\n*** Update File: draft notes.md\n@@\n+PRIVATE_PAYLOAD\n*** End Patch"})
    out = cli("tail", SID)
    assert "draft notes.md" in out and "PRIVATE_PAYLOAD" not in out
    assert "before retrying" in out and "no result" in out.lower()
    cmd = out.splitlines()[-1]
    assert shlex.split(cmd) == ["cd", "--", str(cwd), "&&", agent, "--resume" if agent == "claude" else "resume", SID]
    if agent == "claude":
        emit("user", [{"type": "tool_result", "tool_use_id": "t", "content": "ok"}])
    else:
        emit("tool", {"type": "custom_tool_call_output", "call_id": "t", "output": "ok"})
    out = cli("tail", SID)
    assert "result recorded" in out.lower() and "before retrying" not in out


def test_literal_search_and_activity_ignore_nonconversation_events(sample):
    agent, path, cwd, emit, cli = sample
    emit("user", "Test a.b on the old build", days=30)
    emit("assistant", "Test aXb on the old build", days=29)
    with path.open("a") as stream:
        stream.write(json.dumps({"type": "progress" if agent == "claude" else "event_msg",
                                 "timestamp": datetime.now(timezone.utc).isoformat(), "data": "a.b"}) + "\n")
        stream.write('{"partial":')
    assert json.loads(cli("list", "--days", "1", "--json")) == []
    row, = json.loads(cli("search", "a.b", "--days", "40", "--json"))
    assert row["match_role"] == "user" and "a.b" in row["match"]
    assert "Partial history" in cli("inspect", SID)


def test_inspect_undeclared_directory_and_ambiguous_id(sample):
    agent, path, cwd, emit, cli = sample
    emit("user", "test")
    second = SID[:-1] + "6"
    duplicate = path.with_name(path.name.replace(SID, second))
    duplicate.write_bytes(path.read_bytes().replace(SID.encode(), second.encode()))
    assert "2 transcripts match" in cli("inspect", SID[:8], ok=False)
    text = path.read_text().replace(str(cwd), "")
    path.write_text(text)
    out = cli("inspect", SID)
    assert "Verify the original working directory" in out
    assert "cd --" not in out
