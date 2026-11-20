"""Read native transcripts once, keeping only the evidence needed for this request."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
import json
import re

TITLES = {"custom-title": ("customTitle", 3), "ai-title": ("aiTitle", 2), "summary": ("summary", 1)}
WRAPPER = re.compile(
    r"^<(system-reminder|command-(name|message|args)|local-command-[a-z]+|"
    r"user-prompt-submit-hook|task-notification|bash-(input|stdout|stderr)|environment_context|"
    r"INSTRUCTIONS|external_codex_apps|user_instructions|turn_aborted|permissions instructions|skill)\b"
    r"|^Base directory for this skill:|^# AGENTS\.md instructions"
)
CALLS = {"function_call", "custom_tool_call", "local_shell_call"}
RESULTS = {"function_call_output", "custom_tool_call_output", "local_shell_call_output"}


def timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        when = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return when.timestamp() if when.tzinfo is not None else None
    except (ValueError, OverflowError, OSError):
        return None


def visible_text(value, kinds):
    if isinstance(value, str):
        return value.strip()
    if not isinstance(value, list):
        return ""
    return " ".join(block["text"] for block in value if isinstance(block, dict)
                    and block.get("type") in kinds and isinstance(block.get("text"), str)).strip()


def excerpt(text, pattern, context):
    line = " ".join(text.split())
    match = pattern.search(line)
    if match is None:
        return None
    start = max(0, match.start() - context)
    end = min(len(line), match.end() + context)
    return ("…" if start else "") + line[start:end] + ("…" if end < len(line) else "")


@dataclass
class Action:
    name: str
    targets: tuple
    result: str = "no result recorded"


def action(name, args):
    # Only expose structured file targets. Bodies, shell commands and arbitrary
    # tool arguments can contain credentials or content unrelated to recovery.
    targets = []
    tool = name.rsplit(".", 1)[-1].lower()
    if isinstance(args, str) and tool != "apply_patch":
        try:
            args = json.loads(args)
        except ValueError:
            args = {}
    if tool == "apply_patch":
        patch = args.get("patch", args.get("input", "")) if isinstance(args, dict) else args
        if isinstance(patch, str):
            targets = re.findall(r"^\*\*\* (?:Add File|Update File|Delete File|Move to): ([^\r\n]+)", patch, re.M)
    elif isinstance(args, dict) and tool in {"write", "edit", "multiedit", "notebookedit", "read"}:
        path = args.get("file_path") or args.get("notebook_path")
        if isinstance(path, str):
            targets = [path]
    return Action(name, tuple(dict.fromkeys(targets)))


@dataclass
class Transcript:
    cwd: str = ""
    branch: str = ""
    title: str = ""
    title_rank: int = 0
    background: bool = False
    first_user: str = ""
    last_user: str = ""
    active: float | None = None
    match_time: float | None = None
    match: str = ""
    match_role: str = ""
    malformed: int = 0
    turns: deque = field(default_factory=deque)
    pending: dict = field(default_factory=dict)
    last_action: Action | None = None


def events(rec, agent, log):
    """Yield (event kind, text/tool name, call id, input/result) in transcript order."""
    kind = rec.get("type")
    if agent == "claude":
        if rec.get("isSidechain"):
            return
        log.cwd = log.cwd or rec.get("cwd") or ""
        log.branch = rec.get("gitBranch") or log.branch
        key, rank = TITLES.get(kind, (None, 0))
        if key and rec.get(key) and rank >= log.title_rank:
            log.title = rec[key]
            log.title_rank = rank
        if kind not in {"user", "assistant"} or rec.get("isMeta"):
            return
        msg = rec.get("message")
        if not isinstance(msg, dict):
            return
        content = msg.get("content")
        text = visible_text(content, {"text"})
        if text and (kind != "user" or not WRAPPER.match(text)):
            yield kind, text, None, None
        for block in content if isinstance(content, list) else ():
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                yield "call", block.get("name") or "tool", block.get("id"), block.get("input")
            elif block.get("type") == "tool_result":
                yield "result", "", block.get("tool_use_id"), block.get("is_error") is True
        return
    data = rec.get("payload")
    if not isinstance(data, dict):
        return
    if kind == "session_meta":
        log.cwd = data.get("cwd") or log.cwd
        git = data.get("git")
        if isinstance(git, dict):
            log.branch = git.get("branch") or log.branch
        log.title = data.get("thread_name") or log.title
        log.background = data.get("thread_source") not in (None, "user") or (
            isinstance(data.get("source"), dict) and "subagent" in data["source"])
    if kind != "response_item":
        return
    item, role = data.get("type"), data.get("role")
    if item == "message" and role in {"user", "assistant"}:
        text = visible_text(data.get("content"), {"input_text", "output_text", "text"})
        if text and (role != "user" or not WRAPPER.match(text)):
            yield role, text, None, None
    elif item in CALLS:
        yield "call", data.get("name") or item, data.get("call_id") or data.get("id"), data.get("arguments", data.get("input"))
    elif item in RESULTS:
        yield "result", "", data.get("call_id") or data.get("id"), False


def scan(path, agent, *, pattern=None, cutoff=None, context=0, turns=0, undated=False):
    log = Transcript(turns=deque(maxlen=turns))
    inspect = turns > 0
    with path.open("rb") as stream:
        for raw in stream:
            try:
                rec = json.loads(raw)
            except (ValueError, UnicodeError):
                log.malformed += 1
                continue
            if not isinstance(rec, dict):
                log.malformed += 1
                continue
            for kind, text, key, args in events(rec, agent, log):
                when = timestamp(rec.get("timestamp"))
                if when is not None and (log.active is None or when > log.active):
                    log.active = when
                if kind in {"user", "assistant"}:
                    if kind == "user":
                        log.first_user = log.first_user or text
                        log.last_user = text
                    if inspect:
                        log.turns.append((kind, text))
                    eligible = (undated and when is None) or (when is not None and cutoff is not None and when >= cutoff)
                    if pattern is not None and eligible and (
                            log.match_time is None or (when is not None and when >= log.match_time)):
                        hit = excerpt(text, pattern, context)
                        if hit:
                            log.match_time, log.match_role, log.match = when, kind, hit
                elif inspect and kind == "call":
                    log.last_action = action(text, args)
                    if key:
                        log.pending[key] = log.last_action
                elif inspect and key in log.pending:
                    finished = log.pending.pop(key)
                    finished.result = "error recorded" if args else "result recorded"
    log.title = log.title or log.first_user or "(no text yet)"
    return log
