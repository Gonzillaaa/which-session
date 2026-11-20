import os
from pathlib import Path
import re
import subprocess
import sys

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
    assert (commands / "inspect.md").samefile(SKILL / "commands/inspect.md")
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
    blocks = re.findall(r"```sh\n(.*?)\n```", section, re.S)
    assert blocks
    for block in blocks:
        result = subprocess.run(["sh", "-ec", block], input="", cwd=ROOT,
                                env=install_env, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
