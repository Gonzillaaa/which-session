#!/usr/bin/env python3
"""Link Which Session from this checkout into the current user's shell and agents."""

import argparse
import fcntl
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKILL = ROOT / "skills" / "sessions"


def env_path(variable, fallback):
    return Path(os.environ.get(variable) or fallback).expanduser().absolute()


def destinations(bin_dir):
    codex = env_path("CODEX_HOME", Path.home() / ".codex")
    claude = env_path("CLAUDE_CONFIG_DIR", Path.home() / ".claude")
    links = {bin_dir / "which-session": ROOT / "which-session",
             codex / "skills/sessions": SKILL, claude / "skills/sessions": SKILL}
    commands = claude / "commands/sessions"
    if commands.is_dir() and not commands.is_symlink():
        for src in sorted((SKILL / "commands").glob("*.md")):
            links[commands / src.name] = src
    else:
        links[commands] = SKILL / "commands"
    return links


def save_receipt(receipt, owned):
    with tempfile.NamedTemporaryFile(dir=receipt.parent, mode="w", delete=False) as out:
        json.dump(owned, out, indent=2, sort_keys=True)
        out.write("\n")
    os.replace(out.name, receipt)


def install(links, owned, receipt):
    new = {}
    for dest, src in links.items():
        if dest.is_symlink() and dest.exists() and dest.samefile(src):
            continue
        if os.path.lexists(dest):
            raise ValueError(f"Install conflict at {dest}. Review that destination before retrying.")
        new[dest] = src
    for dest in new:
        dest.parent.mkdir(parents=True, exist_ok=True)
    for dest, src in new.items():
        # Record this link before creating it so a retry can finish after interruption.
        owned[str(dest)] = str(src)
        save_receipt(receipt, owned)
        try:
            dest.symlink_to(src)
        except OSError:
            del owned[str(dest)]
            save_receipt(receipt, owned)
            raise
    for dest in links:
        print(f"{'Linked' if dest in new else 'Already linked'} {dest}")


def uninstall(links, owned, receipt):
    for dest, src in links.items():
        if owned.get(str(dest)) != str(src):
            continue
        if dest.is_symlink() and os.readlink(dest) == str(src):
            dest.unlink()
            print(f"Removed {dest}")
        elif os.path.lexists(dest):
            print(f"Preserved changed destination {dest}")
        del owned[str(dest)]
    if owned:
        save_receipt(receipt, owned)
    elif receipt.exists():
        receipt.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uninstall", action="store_true", help="remove links created by this installer")
    parser.add_argument("--bin-dir", type=Path, default=Path.home() / ".local/bin",
                        help="CLI destination directory (default: ~/.local/bin)")
    args = parser.parse_args()
    state = env_path("XDG_STATE_HOME", Path.home() / ".local/state") / "which-session"
    try:
        if args.uninstall and not state.exists():
            return 0
        state.mkdir(parents=True, exist_ok=True)
        with (state / "install.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            receipt = state / "links.json"
            try:
                owned = json.loads(receipt.read_text())
            except FileNotFoundError:
                owned = {}
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid installation receipt at {receipt}: {exc}") from exc
            if not isinstance(owned, dict) or any(
                not isinstance(k, str) or not isinstance(v, str) for k, v in owned.items()
            ):
                raise ValueError(f"Invalid installation receipt at {receipt}")
            bin_dir = args.bin_dir.expanduser().absolute()
            links = destinations(bin_dir)
            if args.uninstall:
                uninstall(links, owned, receipt)
            else:
                install(links, owned, receipt)
                if str(bin_dir) not in os.get_exec_path():
                    print(f"Add {bin_dir} to your shell's PATH to run which-session.")
    except (OSError, ValueError) as exc:
        print(f"which-session: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
