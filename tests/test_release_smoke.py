"""Exercise the public demo and the checkout CLI as a user would."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "demo.py"
CLI = ROOT / "which-session"


def run(*command, env=None, cwd=None, check=True):
    return subprocess.run(command, env=env, cwd=cwd, text=True, capture_output=True, check=check)


@pytest.fixture
def preview(tmp_path):
    directory = tmp_path / "demo history"
    result = run(sys.executable, DEMO, "--keep", directory, cwd=tmp_path)
    project = directory / "Paper plane's workshop"
    env = dict(os.environ, CLAUDE_CONFIG_DIR=str(directory / "claude"), CODEX_HOME=str(directory / "codex"))
    return directory, project, env, result.stdout


def test_public_example_and_json_disclosures(preview):
    root, project, env, output = preview
    assert "retry policy" in output.lower()
    assert "before retrying" in output.lower() and "retry-notes.md" in output
    assert "SYNTHETIC_EDIT_BODY" not in output

    table = run(CLI, "list", "--all", env=env, cwd=project).stdout
    rows = json.loads(run(CLI, "list", "--all", "--json", env=env, cwd=project).stdout)
    assert {row["tool"] for row in rows} == {"codex", "claude"}
    for row in rows:
        assert row["id"] in table and row["folder"] in table
        assert row["cwd"] == str(project)
        assert Path(row["path"]).is_file() and root in Path(row["path"]).parents
        assert row["last_user"] and row["last_user"] not in table
        assert str(project) not in table


def test_published_resume_commands_execute_in_original_folder(preview, tmp_path):
    root, project, env, _ = preview
    logs = list(root.rglob("*.jsonl"))
    before = [hashlib.sha256(path.read_bytes()).digest() for path in logs]
    shims = tmp_path / "bin"
    shims.mkdir()
    # Only these two executables are on the shell's PATH. A mistaken resume
    # command cannot start either real agent or fall through to another binary.
    for agent in ("claude", "codex"):
        program = shims / agent
        program.write_text("#!/bin/sh\nprintf '%s\\n' \"$0\" \"$PWD\" \"$#\" \"$@\"\n")
        program.chmod(0o755)
    shell_env = {**env, "PATH": str(shims)}
    rows = json.loads(run(CLI, "search", "retry policy", "--here", "--all", "--json",
                          env=env, cwd=project).stdout)
    assert {row["tool"] for row in rows} == {"claude", "codex"}
    for row in rows:
        agent = row["tool"]
        inspection = run(CLI, "inspect", row["id"], env=env, cwd=tmp_path).stdout
        if agent == "codex":
            advice = next(line for line in inspection.splitlines() if line.startswith("Next step:"))
            assert "error" in advice.lower() or "fail" in advice.lower()
        command = inspection.splitlines()[-1]
        actual = run("/bin/sh", "-c", command, cwd=tmp_path, env=shell_env).stdout.splitlines()
        assert actual == [str(shims / agent), str(project), "2",
                          "--resume" if agent == "claude" else "resume", row["id"]]
    assert before == [hashlib.sha256(path.read_bytes()).digest() for path in logs]


def test_demo_preserves_an_existing_directory(tmp_path):
    marker = tmp_path / "keep-me"
    marker.write_text("existing data")
    result = run(sys.executable, DEMO, "--keep", tmp_path, check=False)
    assert result.returncode != 0 and "exists" in result.stderr.lower()
    assert sorted(tmp_path.iterdir()) == [marker] and marker.read_text() == "existing data"
