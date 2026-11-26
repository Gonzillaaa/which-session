import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "sessions"


@pytest.fixture
def install_env(tmp_path):
    return {**os.environ, "HOME": str(tmp_path / "user"),
            "XDG_STATE_HOME": str(tmp_path / "state"),
            "CODEX_HOME": str(tmp_path / "codex"),
            "CLAUDE_CONFIG_DIR": str(tmp_path / "claude"),
            "PYTHONDONTWRITEBYTECODE": "1"}


def install(env, *args, check=True):
    return subprocess.run([sys.executable, str(ROOT / "install.py"), *args],
                          env=env, capture_output=True, text=True, check=check)


def destinations(env):
    return (Path(env["HOME"]) / ".local/bin/which-session",
            Path(env["CODEX_HOME"]) / "skills/sessions",
            Path(env["CLAUDE_CONFIG_DIR"]) / "skills/sessions",
            Path(env["CLAUDE_CONFIG_DIR"]) / "commands/sessions")


def test_live_install_reinstall_and_uninstall(install_env, tmp_path):
    cli, codex, claude, commands = destinations(install_env)
    install(install_env)
    before = [p.lstat().st_ino for p in (cli, codex, claude, commands)]
    install(install_env)
    assert [p.lstat().st_ino for p in (cli, codex, claude, commands)] == before
    assert cli.samefile(ROOT / "which-session") and cli.samefile(ROOT / "sessions")
    assert codex.samefile(SKILL) and claude.samefile(SKILL)
    for name in ("list.md", "search.md", "inspect.md", "help.md", "version.md"):
        assert (commands / name).samefile(SKILL / "commands" / name)
    result = subprocess.check_output([cli, "list", "--json"], env=install_env,
                                     cwd=tmp_path, text=True)
    assert result.strip() == "[]"
    install(install_env, "--uninstall")
    install(install_env, "--uninstall")
    assert not any(p.is_symlink() for p in (cli, codex, claude, commands))


@pytest.mark.parametrize("existing", ["file", "dangling-link"])
def test_conflict_aborts_before_adding_other_links(install_env, existing):
    cli, codex, claude, commands = destinations(install_env)
    commands.parent.mkdir(parents=True)
    if existing == "file":
        commands.write_text("user file")
    else:
        commands.symlink_to("another checkout")
    result = install(install_env, check=False)
    assert result.returncode != 0 and str(commands) in result.stderr
    assert not any(p.is_symlink() for p in (cli, codex, claude))
    if existing == "file":
        assert commands.read_text() == "user file"
    else:
        assert os.readlink(commands) == "another checkout"


def test_preserve_existing_toolkit_and_manually_managed_links(install_env, tmp_path):
    cli, codex, claude, commands = destinations(install_env)
    alias = tmp_path / "toolkit" / ".source.local"
    alias.parent.mkdir()
    alias.symlink_to(SKILL)
    for p in (codex, claude):
        p.parent.mkdir(parents=True)
        p.symlink_to(alias)
    commands.mkdir(parents=True)
    (commands / "mine.md").write_text("local")
    existing = [codex, claude]
    for src in (SKILL / "commands").glob("*.md"):
        if src.name != "help.md":
            p = commands / src.name
            p.symlink_to(alias / "commands" / src.name)
            existing.append(p)
    cli.parent.mkdir(parents=True)
    cli.symlink_to(ROOT / "sessions")
    existing.append(cli)
    targets = [os.readlink(p) for p in existing]
    install(install_env)
    assert (commands / "help.md").samefile(SKILL / "commands/help.md")
    install(install_env, "--uninstall")
    assert [os.readlink(p) for p in existing] == targets
    assert not (commands / "help.md").is_symlink()
    assert (commands / "mine.md").read_text() == "local"


def test_uninstall_keeps_a_replaced_destination(install_env):
    cli, *_ = destinations(install_env)
    install(install_env)
    cli.unlink()
    cli.write_text("different command")
    install(install_env, "--uninstall")
    assert cli.read_text() == "different command"


def test_readme_quickstart_runs_with_empty_histories(install_env, tmp_path):
    section = (ROOT / "README.md").read_text().split("## Try it", 1)[1].split("\n## ", 1)[0]
    blocks = re.findall(r"```sh\n(.*?)\n```", section, re.DOTALL)
    assert blocks
    for block in blocks:
        result = subprocess.run(["sh", "-ec", block], input="", cwd=ROOT,
                                env=install_env, capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stderr


def test_download_install_instructions_connect_both_agents(install_env, tmp_path):
    folder = Path(install_env["HOME"]) / "Documents/which-session"
    folder.mkdir(parents=True)
    for filename in ("install.py", "which-session", "README.md"):
        shutil.copy2(ROOT / filename, folder / filename)
    shutil.copytree(SKILL, folder / "skills/sessions")
    readme = (folder / "README.md").read_text()
    section = readme.split("## Install on macOS or Linux\n", 1)[1].split("\n## ", 1)[0]
    blocks = re.findall(r"```sh\n(.*?)\n```", section, re.DOTALL)
    assert blocks
    result = subprocess.run(["sh", "-ec", "\n".join(blocks)], env=install_env, cwd=tmp_path,
                            capture_output=True, text=True, check=True)
    cli, codex, claude, commands = destinations(install_env)
    expected = json.loads((folder / "skills/sessions/scripts/settings.json").read_text())["version"]
    assert result.stdout.splitlines()[-1] == f"which-session {expected}"
    assert cli.samefile(folder / "which-session") and claude.samefile(codex)
    assert {p.stem for p in commands.glob("*.md")} == {"list", "search", "inspect", "help", "version"}

    # Run the same search via both installed scripts, using only synthetic history.
    history = tmp_path / "demo"
    subprocess.run([sys.executable, ROOT / "examples/demo.py", "--keep", history], check=True, capture_output=True)
    env = {**install_env, "CLAUDE_CONFIG_DIR": str(history / "claude"), "CODEX_HOME": str(history / "codex")}

    def search(entry):
        return json.loads(subprocess.check_output([*entry, "search", "retry policy", "--all", "--json"], env=env))

    rows = search([cli])
    assert {r["tool"] for r in rows} == {"claude", "codex"}
    for skill in (codex, claude):
        assert search([sys.executable, skill / "scripts/sessions.py"]) == rows
