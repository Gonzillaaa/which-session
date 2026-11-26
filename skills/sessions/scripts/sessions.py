#!/usr/bin/env python3
"""Find, search and inspect local Claude Code and Codex transcripts. Read-only."""
import argparse
import functools
import json
import math
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from uuid import UUID
from zoneinfo import ZoneInfo

if __name__ == "__main__":
    sys.dont_write_bytecode = True

from session_groups import JobConfigError, configured_jobs, group_runs, recurring_job
from session_picker import PickerError, choose_session
from session_preview import describe_action, preview_lines, resume_guidance
from session_table import print_terminal_table, print_wrapped, printable, single_line
from transcript import codex_session_id, scan

SETTINGS = json.loads(Path(__file__).with_name("settings.json").read_text())
TEMP_PREFIXES = ("/private/var/folders/", "/var/folders/", "/private/tmp/", "/tmp/")


@functools.lru_cache(maxsize=1)
def owner_tz():
    """Use the vault's owner timezone when invoked from a vault installation."""
    entry = Path(__file__).absolute()
    if len(entry.parents) < 5:
        return None
    vault = entry.parents[4]
    installed = vault / "system" / "skills" / "sessions" / "scripts" / "sessions.py"
    script = vault / "system" / "scripts" / "dateutil.py"
    if not script.is_file() or installed.resolve() != entry.resolve():
        return None
    try:
        out = subprocess.run([sys.executable, "-I", str(script), "today"], capture_output=True,
                             text=True, timeout=10, cwd=vault, check=True)
        info = json.loads(out.stdout)
        return None if info.get("timezone_fallback") else ZoneInfo(info["timezone"])
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        return None


def fmt_time(epoch, fmt="%Y-%m-%d %H:%M"):
    return datetime.fromtimestamp(epoch, owner_tz()).strftime(fmt) if epoch is not None else "unknown"


def clean(text, width):
    text = single_line(text).replace("|", "/")
    return text if len(text) <= width else text[:width - 1] + "…"


def ps_text():
    try:
        return subprocess.run(["ps", "-eo", "command="], capture_output=True, text=True,
                              timeout=SETTINGS["process_timeout_seconds"], check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def live_processes(ps):
    """Only accept an agent process that explicitly identifies the session."""
    found = set()
    for line in ps.splitlines():
        args = line.split()
        if not args:
            continue
        if Path(args[0]).name in {"node", "nodejs", "bun"}:
            args = args[1:]
        if not args:
            continue
        binary = Path(args[0]).name
        if binary in {"codex", "codex.js"}:
            agent, flags = "codex", {"resume"}
        elif binary in {"claude", "claude.exe"}:
            agent, flags = "claude", {"--resume", "--session-id", "-r"}
        else:
            continue
        index = 1
        while index < len(args):
            arg = args[index]
            flag, sep, value = arg.partition("=")
            if flag in flags:
                sid = value if sep else (args[index+1] if index+1 < len(args) else "")
                found.add((agent, sid))
                break
            if not arg.startswith("-") or arg == "--":
                break
            # Skip a known option's value. Stop at positional prompts or other
            # subcommands so a quoted example cannot mark a session as live.
            if not sep and flag in {"-m", "--model", "-C", "--cd", "-c", "--config", "--profile"}:
                index += 1
            index += 1
    return found


def sources(source):
    if source in {"all", "claude"}:
        base = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
        for path in (base / "projects").glob("*/*.jsonl"):
            yield "claude", path.stem, path
    if source in {"all", "codex"}:
        for path in (codex_dir() / "sessions").glob("*/*/*/rollout-*.jsonl"):
            yield "codex", codex_session_id(path), path


def codex_dir():
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")


def codex_names():
    names = {}
    try:
        with (codex_dir() / "session_index.jsonl").open("rb") as stream:
            for raw in stream:
                try:
                    rec = json.loads(raw)
                except ValueError:
                    continue
                if isinstance(rec, dict) and isinstance(rec.get("id"), str) and isinstance(rec.get("thread_name"), str):
                    names[rec["id"]] = rec["thread_name"]
    except FileNotFoundError:
        pass  # Codex can have usable transcripts before it creates this optional index.
    except OSError as exc:
        print(f"Could not read optional Codex session_index.jsonl ({exc.strerror}). Using transcript titles.", file=sys.stderr)
    return names


def recent_rows(args, transcripts, *, pattern=None, grouped=False):
    rules = configured_jobs(SETTINGS) if grouped else ()
    cutoff = time.time() - args.days * 86400
    names = codex_names() if args.source != "claude" else {}
    live = live_processes(ps_text())
    rows = []
    unreadable = 0
    for agent, sid, path in transcripts:
        try:
            stat = path.stat()
            log = scan(path, agent, pattern=pattern, cutoff=cutoff, context=SETTINGS["match_context"], undated=args.all)
        except OSError:
            unreadable += 1
            continue
        if log.active is None:
            if not args.all:
                continue
        elif log.active < cutoff:
            continue
        if pattern and (not log.match or (log.active is not None and log.match_time is None)):
            continue
        if not args.all and (not log.first_user or log.background or log.cwd.startswith(TEMP_PREFIXES)
                             or (agent == "claude" and path.parent.name.startswith(("-private-var-folders-", "-private-tmp-", "-tmp-")))):
            continue
        folder = Path(log.cwd).name or (path.parent.name if agent == "claude" else "")
        if args.here and log.cwd != os.getcwd():
            continue
        if args.folder.lower() not in (log.cwd or folder).lower():
            continue
        title = (names.get(sid) if agent == "codex" else None) or log.title
        row = {
            "tool": agent, "id": sid, "title": title, "folder": folder, "cwd": log.cwd,
            "branch": log.branch, "background": log.background, "parent_id": log.parent_id or None,
            "last_user": log.last_user, "last_active": fmt_time(log.active), "activity_epoch": log.active,
            "mtime": stat.st_mtime, "size_kb": stat.st_size // 1024, "live": (agent, sid) in live,
            "path": str(path),
        }
        if pattern:
            row.update(match=log.match, match_role=log.match_role, match_epoch=log.match_time)
        if grouped:
            row["job"] = recurring_job(log.first_user, rules)
        rows.append(row)
    if unreadable:
        print(f"Skipped {unreadable} unreadable transcript(s).", file=sys.stderr)
    order = "match_epoch" if pattern else "activity_epoch"
    rows.sort(key=lambda row: (row[order] is not None, row[order], row["id"]), reverse=True)
    return rows


def cmd_list(args):
    query = getattr(args, "phrase", None)
    pattern = re.compile(re.escape(" ".join(query.split())), re.IGNORECASE) if query else None
    terminal_list = not query and sys.stdout.isatty() and not args.json
    grouped = terminal_list and not args.ungrouped
    browse = terminal_list and not args.plain and sys.stdin.isatty() and os.environ.get("TERM") not in (None, "", "dumb")
    transcripts = sources(args.source)
    if browse:
        print("Reading local session histories…", file=sys.stderr, flush=True)
        transcripts = list(transcripts)  # Preview needs all paths to identify restored copies.
    sessions = recent_rows(args, transcripts, pattern=pattern, grouped=grouped)
    entries = group_runs(sessions) if grouped else sessions
    if browse and entries:
        try:
            return inspect_selection(entries[:args.limit], transcripts)
        except PickerError as exc:
            print(f"{exc} Showing the session table.", file=sys.stderr)
    rows = entries[:args.limit or SETTINGS["limit"]]
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    if not rows:
        print(f"No {'matching ' if pattern else ''}sessions in the last {args.days:g} day(s).")
        return 0
    summary = f"{len(rows)} of {len(sessions)} sessions. Inspect one with its ID or a unique prefix."
    if len(entries) < len(sessions):
        summary = (f"{len(rows)} of {len(entries)} entries ({len(sessions)} sessions). "
                   "Group IDs identify the latest run. Use which-session list in a terminal to expand a group.")
    if sys.stdout.isatty():
        fallback = SETTINGS["terminal_fallback_width"]
        columns = shutil.get_terminal_size(fallback=(fallback, 0)).columns or fallback
        print_terminal_table(rows, columns, SETTINGS)
        print()
        print_wrapped(summary, columns)
    else:
        print_markdown_table(rows, pattern)
        print("\n" + summary)
    return 0


def inspect_selection(entries, transcripts):
    copies = Counter((tool, sid) for tool, sid, _ in transcripts)

    def preview(row):
        return preview_lines(row, duplicate=copies[row["tool"], row["id"]] > 1,
                             resume_command=resume_command, settings=SETTINGS)

    selected = choose_session(entries, preview, SETTINGS)
    if selected is None:
        return 0
    return cmd_tail(argparse.Namespace(id=selected["id"], file=selected["path"], n=SETTINGS["turns"]))


def print_markdown_table(rows, pattern):
    extra = " Match |" if pattern else ""
    print("| Session | Tool | Folder | Last active | Full id |" + extra)
    print("|---|---|---|---|---|" + ("---|" if pattern else ""))
    for row in rows:
        title = clean(row["title"], SETTINGS["title_width"])
        mark = " (live)" if row["live"] else ""
        tool = row["tool"] + (" (background)" if row["background"] else "")
        snippet = (" " + row["match_role"] + ": " + clean(row["match"], SETTINGS["preview_width"]) + " |") if pattern else ""
        print(f"| {title}{mark} | {tool} | {row['folder']} | {row['last_active']} | `{row['id']}` |" + snippet)


def resume_command(agent, sid, cwd):
    if not cwd or not Path(cwd).is_absolute() or not cwd.isprintable():
        return None
    try:
        if str(UUID(sid)) != sid.lower():
            return None
    except ValueError:
        return None
    args = [agent, "--resume" if agent == "claude" else "resume", sid]
    return f"cd -- {shlex.quote(cwd)} && {shlex.join(args)}"


def cmd_tail(args):
    candidates = [(a, s, p) for a, s, p in sources("all") if s.startswith(args.id)]
    matches = candidates
    if args.file is not None:
        selected = os.path.abspath(args.file)
        matches = [item for item in candidates if os.path.abspath(item[2]) == selected]
    if not matches:
        message = (f"No discovered transcript matching {args.id!r} has path {args.file!r}."
                   if args.file is not None else f"No transcript starts with {args.id!r}.")
        print(message, file=sys.stderr)
        return 1
    if len(matches) > 1:
        print(f"{len(matches)} transcripts match {args.id!r}. Inspect a specific file:", file=sys.stderr)
        for _, sid, path in sorted(matches):
            print(shlex.join(["which-session", "inspect", sid, "--file", os.path.abspath(path)]), file=sys.stderr)
        return 1
    agent, sid, path = matches[0]
    same_host_copies = sum(1 for a, s, _ in candidates if (a, s) == (agent, sid)) > 1
    try:
        log = scan(path, agent, turns=args.n)
    except OSError as exc:
        print(f"Cannot inspect transcript: {exc}", file=sys.stderr)
        return 1
    live = not same_host_copies and (agent, sid) in live_processes(ps_text())
    name = (codex_names().get(sid) if agent == "codex" else None) or log.title
    print(f"id: {printable(sid)}\ntool: {agent}\nfolder: {printable(log.cwd)}\nbranch: {printable(log.branch)}"
          f"\ntitle: {clean(name, SETTINGS['title_width'])}")
    if log.background:
        print("session kind: background")
    if log.parent_id:
        print(f"parent session: {printable(log.parent_id)}")
    print(f"last active: {fmt_time(log.active)}\n")
    for role, text in log.turns:
        who = "you" if role == "user" else agent
        print(f"[{who}] {clean(text, SETTINGS['preview_width'])}\n")
    if log.malformed:
        print(f"Partial history: {log.malformed} unreadable record(s).")
    last_outcome = log.last_action.outcome if log.last_action else None
    if log.last_action:
        result = last_outcome.describe() if last_outcome else "no result recorded"
        print("Last recorded tool call: " + describe_action(log.last_action) + " — " + result)
    if log.pending:
        for action in log.pending.values():
            print(("Tool call still pending" if live else "Unfinished tool call") + ": " + describe_action(action) + " — no result recorded.")
    if live:
        print("Next step: return to the running session and check its progress.")
    elif log.pending:
        targets = list(dict.fromkeys(target for call in log.pending.values() for target in call.targets))
        what = ", ".join(repr(t) for t in targets) if targets else "the effects of the outstanding tool calls"
        print(f"Next step: check {what} before retrying. The transcript records no outcome for the outstanding calls.")
    elif last_outcome and last_outcome.failed:
        print("Next step: review the recorded tool error before retrying.")
    elif last_outcome and last_outcome.failed is None:
        print("Next step: verify the outcome of the last tool call before continuing.")
    elif log.malformed or (log.last_action and last_outcome is None):
        print("Next step: review the incomplete history and verify the last action before continuing.")
    elif same_host_copies:
        print("Next step: identify the intended copy in the client before resuming.")
    elif log.turns and log.turns[-1][0] == "user":
        print("Next step: reopen the session and pick up the last user request.")
    else:
        print("Next step: reopen the session and review the last exchange.")
    for line in resume_guidance(agent, sid, log.cwd, live=live, duplicate=same_host_copies, resume_command=resume_command):
        print(line)
    return 0


def positive(value):
    n = int(value)
    if n < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return n


def main(argv=None):
    parser = argparse.ArgumentParser(prog="which-session", description=__doc__)
    version = f"{parser.prog} {SETTINGS['version']}"
    parser.add_argument("--version", action="version", version=version)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, summary in (("list", "Browse recent sessions or print a table"), ("search", "Find a remembered phrase")):
        command = sub.add_parser(name, aliases=["pick"] if name == "list" else [], help=summary)
        if name == "search":
            command.add_argument("phrase", help="literal phrase in a user or assistant message")
        command.add_argument("--days", type=float, default=SETTINGS["days"])
        command.add_argument("--limit", type=positive, help=f"maximum entries (printed output defaults to {SETTINGS['limit']})")
        command.add_argument("--folder", default="")
        command.add_argument("--here", action="store_true")
        command.add_argument("--all", action="store_true", help="include background, empty and undated sessions")
        command.add_argument("--source", choices=["claude", "codex", "all"], default="all")
        if name == "list":
            command.add_argument("--plain", action="store_true", help="print the session table and exit")
            command.add_argument("--ungrouped", action="store_true", help="show every recurring run separately")
        command.add_argument("--json", action="store_true")
        command.set_defaults(fn=cmd_list)
    tail = sub.add_parser("inspect", aliases=["tail"], help="Inspect one session and see how to resume it")
    tail.add_argument("id")
    tail.add_argument("--file", help="select an exact discovered transcript path when the ID matches several copies")
    tail.add_argument("--n", type=positive, default=SETTINGS["turns"])
    tail.set_defaults(fn=cmd_tail)
    sub.add_parser("help", help="Show available commands")
    sub.add_parser("version", help="Show the installed version")
    args = parser.parse_args(argv)
    if args.cmd == "help":
        parser.print_help()
        return 0
    if args.cmd == "version":
        print(version)
        return 0
    if hasattr(args, "days") and (not math.isfinite(args.days) or args.days < 0):
        parser.error("--days must be a finite, nonnegative number")
    if hasattr(args, "phrase") and not args.phrase.strip():
        parser.error("supply a nonempty search phrase")
    try:
        return args.fn(args)
    except JobConfigError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    sys.exit(main())
