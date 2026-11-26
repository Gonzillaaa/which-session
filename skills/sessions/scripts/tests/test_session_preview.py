import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sessions
from session_preview import preview_lines

SID = "11111111-2222-4333-8444-555555555555"


def append(path, kind, **fields):
    with path.open("a") as stream:
        stream.write(json.dumps({"type": kind, **fields}) + "\n")


def preview(path, tool, *, duplicate=False, live=False):
    row = {"path": str(path), "tool": tool, "id": SID, "live": live}
    return preview_lines(row, duplicate=duplicate, resume_command=sessions.resume_command,
                         settings=sessions.SETTINGS)


def test_preview_reads_selected_copy_and_quotes_actual_project(tmp_path):
    project = tmp_path / "Bird's  nest"
    project.mkdir()
    path = tmp_path / f"{SID}.jsonl"
    append(path, "user", cwd=str(project), message={"content": "First request"})
    append(path, "user", message={"content": "Ship the\nchange\x1b[2J"})
    append(path, "assistant", message={"content": [{"type": "tool_use", "id": "edit", "name": "Write",
           "input": {"file_path": "draft.md", "content": "Private tool body"}}]})
    append(path, "user", message={"content": [{"type": "tool_result", "tool_use_id": "edit"}]})
    for _ in range(sessions.SETTINGS["turns"] + 1):
        append(path, "assistant", message={"content": "More detail"})
    lines = preview(path, "claude", live=True)
    text = "\n".join(lines)
    assert "Ship the change" in text and "\x1b" not in text and "First request" not in text
    assert "Write" in text and "draft.md" in text and "successful result" in text
    assert "Private tool body" not in text and f"Full ID: {SID}" in lines
    assert "running session" in text and sessions.resume_command("claude", SID, str(project)) in lines


@pytest.mark.parametrize(("result_type", "payload", "description"), [
    ("event_msg", {"type": "exec_command_end", "exit_code": 7}, "error recorded (exit code 7)"),
    ("response_item", {"type": "function_call_output", "output": "ok"}, "outcome unknown"),
    (None, None, "no result recorded"),
])
def test_preview_reports_only_the_selected_codex_calls_outcome(tmp_path, result_type, payload, description):
    path = tmp_path / f"rollout-demo-{SID}.jsonl"
    append(path, "session_meta", payload={"id": SID, "cwd": str(tmp_path)})
    append(path, "response_item", payload={"type": "function_call", "call_id": "last", "name": "exec_command"})
    append(path, "event_msg", payload={"type": "exec_command_end", "call_id": "other", "exit_code": 0})
    if result_type:
        append(path, result_type, payload={**payload, "call_id": "last"})
    lines = preview(path, "codex")
    assert any("exec_command" in line and description in line for line in lines)
    assert not any("successful result" in line for line in lines)


def test_duplicate_and_missing_folder_qualify_resume(tmp_path):
    path = tmp_path / f"{SID}.jsonl"
    cwd = str(tmp_path / "missing")
    append(path, "user", cwd=cwd, message={"content": "Selected restored copy"})
    duplicate = "\n".join(preview(path, "claude", duplicate=True, live=True))
    assert "Selected restored copy" in duplicate and "same ID" in duplicate
    assert "claude --resume" not in duplicate and "running session" not in duplicate
    lines = preview(path, "claude")
    assert any("unavailable" in line for line in lines)
    assert sessions.resume_command("claude", SID, cwd) in lines


def test_disappeared_transcript_returns_inline_error(tmp_path):
    lines = preview(tmp_path / "missing.jsonl", "claude")
    assert SID in "\n".join(lines) and any("Cannot read" in line for line in lines)
    assert not any("claude --resume" in line for line in lines)
