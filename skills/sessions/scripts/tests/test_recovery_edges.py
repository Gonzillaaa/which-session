import json
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "sessions.py"
CODEX_ID = "11111111-1111-4111-8111-111111111111"
CLAUDE_ID = "22222222-2222-4222-8222-222222222222"


def append(path, kind, **fields):
    with path.open("a") as stream:
        record = {"type": kind, "timestamp": datetime.now(timezone.utc).isoformat(), **fields}
        stream.write(json.dumps(record) + "\n")


def run(*args, ok=True):
    result = subprocess.run([sys.executable, str(SCRIPT), *args], text=True, capture_output=True, check=False)
    assert (result.returncode == 0) == ok, result.stdout + result.stderr
    return result


@pytest.fixture
def logs(tmp_path, monkeypatch):
    cx = tmp_path / "codex"
    cl = tmp_path / "claude"
    monkeypatch.setenv("CODEX_HOME", str(cx))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cl))
    a = cl / "projects" / "original" / f"{CLAUDE_ID}.jsonl"
    b = cx / "sessions" / "2026" / "01" / "12" / f"rollout-sample-{CODEX_ID}.jsonl"
    a.parent.mkdir(parents=True)
    b.parent.mkdir(parents=True)
    append(a, "user", cwd="/work/demo", message={"content": "Find my feature work"})
    append(b, "session_meta", payload={"id": CODEX_ID, "cwd": "/work/demo"})
    append(b, "response_item", payload={"type": "message", "role": "user",
                                       "content": [{"type": "input_text", "text": "Find my feature plan"}]})
    return a, b, cx / "session_index.jsonl"


@pytest.mark.parametrize(("exit_code", "output_first"), [(1, True), (9, False), (0, True), (0, False)])
def test_structured_command_outcome_follows_call_id(logs, exit_code, output_first):
    _, path, _ = logs
    for key in ("other", "last"):
        append(path, "response_item", payload={"type": "function_call", "name": "exec_command", "call_id": key})
    output = {"type": "function_call_output", "call_id": "last", "output": "arbitrary output"}
    end = {"type": "exec_command_end", "call_id": "last", "exit_code": exit_code}
    events = [("event_msg", end), ("response_item", output)]
    if output_first:
        events.reverse()
    for kind, payload in events:
        append(path, kind, payload=payload)
    append(path, "event_msg", payload={"type": "exec_command_end", "call_id": "other",
                                      "exit_code": 0 if exit_code else 1})
    out = run("inspect", CODEX_ID).stdout
    assert "Unfinished tool call" not in out
    assert f"exit code {exit_code}" in out
    next_step = next(line for line in out.splitlines() if line.startswith("Next step:"))
    assert ("review the recorded tool error" in next_step) == bool(exit_code)


def test_unstructured_output_is_unknown_and_distinct_from_outstanding(logs):
    _, path, _ = logs
    append(path, "response_item", payload={"type": "function_call", "name": "exec_command", "call_id": "last"})
    assert "Unfinished tool call" in run("inspect", CODEX_ID).stdout
    append(path, "response_item", payload={"type": "function_call_output", "call_id": "last",
                                          "output": "Exit code 1 or 0 is an example in this document"})
    out = run("inspect", CODEX_ID).stdout
    assert "outcome unknown" in out
    assert "Unfinished tool call" not in out
    assert "verify" in next(line for line in out.splitlines() if line.startswith("Next step:")).lower()


@pytest.mark.parametrize("broken", [True, False])
def test_optional_codex_index_preserves_mixed_history_and_json(logs, broken):
    _, _, index = logs
    if broken:
        index.mkdir()  # A real read error even for a privileged test runner.
    for args in [("list", "--json"), ("search", "feature", "--json"), ("inspect", CODEX_ID)]:
        result = run(*args)
        if args[0] == "inspect":
            assert "Find my feature plan" in result.stdout
        else:
            assert {row["id"] for row in json.loads(result.stdout)} == {CLAUDE_ID, CODEX_ID}
        diagnostics = result.stderr.splitlines()
        if broken:
            assert len(diagnostics) == 1 and "session_index.jsonl" in diagnostics[0]
        else:
            assert not diagnostics


def test_select_restored_copy_by_listed_command(logs, tmp_path):
    original, _, _ = logs
    restored = original.parent.parent / "restored user's copy" / original.name
    restored.parent.mkdir()
    append(restored, "user", cwd="/work/demo", message={"content": "restored feature plan"})
    ambiguous = run("inspect", CLAUDE_ID, ok=False).stderr
    assert "longer prefix" not in ambiguous
    choices = [shlex.split(line) for line in ambiguous.splitlines() if line.startswith("which-session ")]
    assert len(choices) == 2
    for launcher, command, sid, flag, path in choices:
        assert (launcher, command, sid, flag) == ("which-session", "inspect", CLAUDE_ID, "--file")
        assert Path(path) in (original, restored)
        out = run(command, sid, flag, path).stdout
        assert ("restored feature plan" in out) == (path == str(restored))
        assert "claude --resume" not in out
        assert "same ID" in out
    outside = tmp_path / original.name
    outside.write_bytes(original.read_bytes())
    assert run("inspect", CLAUDE_ID, "--file", str(outside), ok=False).returncode == 1
