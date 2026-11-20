"""Show a phrase lookup and two interrupted-work scenarios using synthetic history."""
import argparse
import json
import os
import shlex
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

CLI = Path(__file__).resolve().parents[1] / "which-session"
CLAUDE_ID = "11111111-1111-4111-8111-111111111111"
CODEX_ID = "22222222-2222-4222-8222-222222222222"


def write_log(path, records, timestamp):
    path.parent.mkdir(parents=True)
    with path.open("x", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps({"timestamp": timestamp, **record}) + "\n")


def demonstrate(root):
    project = root / "Paper plane's workshop"
    project.mkdir()
    claude, codex = root / "claude", root / "codex"
    now = datetime.now(timezone.utc)
    stamp = now.isoformat(timespec="milliseconds")

    write_log(claude / "projects" / "demo" / (CLAUDE_ID + ".jsonl"), [
        {"type": "custom-title", "customTitle": "Backoff notes", "cwd": str(project)},
        {"type": "user", "message": {"content": "Document the retry policy for the demo."}},
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "edit-1",
         "name": "Write", "input": {"file_path": "retry-notes.md", "content": "SYNTHETIC_EDIT_BODY"}}]}},
    ], stamp)
    write_log(codex / "sessions" / now.strftime("%Y/%m/%d") / ("rollout-demo-" + CODEX_ID + ".jsonl"), [
        {"type": "session_meta", "payload": {"id": CODEX_ID, "cwd": str(project), "thread_name": "Backoff tests"}},
        {"type": "response_item", "payload": {"type": "message", "role": "user",
         "content": [{"type": "input_text", "text": "Check the retry policy tests."}]}},
        {"type": "response_item", "payload": {"type": "function_call", "name": "exec_command",
         "call_id": "test-1", "arguments": "{}"}},
        {"type": "event_msg", "payload": {"type": "exec_command_end", "call_id": "test-1", "exit_code": 1}},
        {"type": "response_item", "payload": {"type": "function_call_output",
         "call_id": "test-1", "output": "Test run complete."}},
    ], stamp)

    env = {**os.environ, "CLAUDE_CONFIG_DIR": str(claude), "CODEX_HOME": str(codex)}
    for args in [("search", "retry policy", "--all"), ("inspect", CLAUDE_ID), ("inspect", CODEX_ID)]:
        print("$ which-session " + shlex.join(args))
        output = subprocess.check_output([sys.executable, str(CLI), *args], cwd=project, env=env, text=True)
        # Keep machine-specific temporary directories out of the printed example.
        example_project = "<demo>/" + project.name
        output = output.replace(shlex.quote(str(project)), shlex.quote(example_project))
        print(output.replace(str(root), "<demo>"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep", type=Path, metavar="NEW_DIRECTORY",
                        help="create this directory and keep the synthetic histories for further checks")
    args = parser.parse_args()
    if args.keep:
        directory = args.keep.resolve()
        try:
            directory.mkdir()
        except OSError as exc:
            parser.exit(1, f"Could not create demo directory: {exc}\n")
        demonstrate(directory)
    else:
        with tempfile.TemporaryDirectory() as folder:
            demonstrate(Path(folder).resolve())


if __name__ == "__main__":
    main()
