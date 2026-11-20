import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_checkout_command_from_another_project(tmp_path):
    project = tmp_path / "demo"
    project.mkdir()
    env = {**os.environ, "CLAUDE_CONFIG_DIR": str(tmp_path / "claude"),
           "CODEX_HOME": str(tmp_path / "codex")}
    session_id = "11111111-2222-4333-8444-555555555555"
    log = Path(env["CLAUDE_CONFIG_DIR"]) / "projects" / "demo" / f"{session_id}.jsonl"
    log.parent.mkdir(parents=True)
    log.write_text(json.dumps({"type": "user", "cwd": str(project),
                               "timestamp": datetime.now(timezone.utc).isoformat(),
                               "message": {"content": "Compare the retry policies"}}) + "\n")
    entry = tmp_path / "sessions"
    entry.symlink_to(ROOT / "sessions")

    def run(*args, check=True):
        return subprocess.run([entry, *args], env=env, cwd=project, text=True,
                              capture_output=True, check=check)

    row, = json.loads(run("search", "retry policies", "--here", "--all", "--json").stdout)
    assert (row["id"], row["match_role"], row["cwd"]) == (session_id, "user", str(project))
    assert f"claude --resume {session_id}" in run("inspect", session_id).stdout
    assert run("inspect", "absent", check=False).returncode != 0


def test_help_and_version_from_checkout_and_packaged_skill(tmp_path):
    # A toolkit distribution can contain only this directory, with no upstream Git metadata.
    bundle = tmp_path / "bundle"
    shutil.copytree(ROOT / "skills" / "sessions", bundle)
    index = tmp_path / "codex" / "session_index.jsonl"
    index.mkdir(parents=True)  # Accessing session history would emit a diagnostic.
    env = {**os.environ, "CODEX_HOME": str(index.parent), "CLAUDE_CONFIG_DIR": str(tmp_path / "claude")}
    release = json.loads((bundle / "scripts/settings.json").read_text())["version"]

    def run(cmd, arg):
        result = subprocess.run([*cmd, arg], cwd=tmp_path, env=env, text=True,
                                capture_output=True, check=True)
        assert not result.stderr
        return result.stdout

    for cmd in ([str(ROOT / "which-session")], [sys.executable, str(bundle / "scripts/sessions.py")]):
        assert run(cmd, "help") == run(cmd, "--help")
        assert run(cmd, "version") == run(cmd, "--version") == f"which-session {release}\n"
