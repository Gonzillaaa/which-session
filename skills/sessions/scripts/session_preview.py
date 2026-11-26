"""Read the selected transcript and show the evidence needed to inspect or resume it."""
from pathlib import Path

from session_table import printable, shorten, single_line
from transcript import scan


def describe_action(action):
    return " ".join([single_line(action.name), *(repr(path) for path in action.targets)]).strip()


def resume_guidance(agent, sid, cwd, *, live, duplicate, resume_command):
    if duplicate:
        return [f"Multiple {agent} transcripts have the same ID. Native resume selects by ID and cannot specify this file."]
    command = resume_command(agent, sid, cwd)
    if not command:
        return ["Verify the original working directory and full session ID to construct a resume command."]
    lines = []
    if not Path(cwd).is_dir():
        lines.append("The recorded folder is unavailable. Locate or restore it before using this command.")
    lines.append("Resume command for later:" if live else "Resume command for the original folder:")
    lines.append(command)
    return lines


def preview_lines(row, *, duplicate, resume_command, settings):
    agent, sid = row["tool"], row["id"]
    path = Path(row["path"])
    identity = f"Full ID: {single_line(sid)}"
    try:
        log = scan(path, agent, turns=settings["turns"])
    except OSError as exc:
        return [identity, f"Cannot read transcript: {single_line(str(exc))}"]

    width = settings["preview_width"]
    request = shorten(single_line(log.last_user), width) if log.last_user else "No user request recorded"
    lines = [f"Last request: {request}"]
    if log.last_action:
        outcome = log.last_action.outcome
        result = outcome.describe() if outcome else "no result recorded"
        lines.append(f"Last tool: {shorten(describe_action(log.last_action), width)} — {result}")
    else:
        lines.append("No tool call recorded.")
    lines.append(identity)
    if log.malformed:
        lines.append(f"Partial history: {log.malformed} unreadable record(s).")

    live = row["live"] and not duplicate
    if live:
        lines.append("Check the running session before resuming.")
    if duplicate:
        lines.append(f"Transcript: {printable(str(path))}")
    lines.extend(resume_guidance(agent, sid, log.cwd, live=live, duplicate=duplicate, resume_command=resume_command))
    return lines
