import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sessions


@pytest.fixture(autouse=True)
def isolated_codex(tmp_path_factory, monkeypatch):
    """Never read the developer's real ~/.codex."""
    monkeypatch.setenv("CODEX_HOME", str(tmp_path_factory.mktemp("codex-empty")))
    monkeypatch.setattr(sessions, "ps_text", lambda: "")


def write(root, project, sid, records, age_days=0.0):
    d = root / "projects" / project
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{sid}.jsonl"
    t = time.time() - age_days * 86400
    stamp = datetime.fromtimestamp(t, timezone.utc).isoformat()
    f.write_text("\n".join(json.dumps({"timestamp": stamp, **r}) for r in records) + "\n")
    os.utime(f, (t, t))
    return f


def user(text, cwd="/work/alpha"):
    return {"type": "user", "cwd": cwd, "message": {"content": text}}


def test_list_titles_filters_and_temp(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    sid = "11111111-1111-1111-1111-111111111111"
    write(tmp_path, "-work-alpha", sid, [user("fix the build"), {"type": "ai-title", "aiTitle": "Fix build"}], 1)
    write(tmp_path, "-work-beta", "22222222-2222-2222-2222-222222222222", [user("old", "/work/beta")], 30)
    write(tmp_path, "-private-var-folders-x-T-wb-kit-1", "33333333-3333-3333-3333-333333333333", [user("kit")], 0)
    write(tmp_path, "-work-alpha", "44444444-4444-4444-4444-444444444444", [{"type": "user", "message": {"content": "<system-reminder>hook</system-reminder>"}}], 0)
    assert sessions.main(["list", "--days", "7"]) == 0
    out = capsys.readouterr().out
    assert sid in out and "Fix build" in out and "alpha" in out
    assert "22222222" not in out and "33333333" not in out and "44444444" not in out
    sessions.main(["list", "--days", "7", "--all"])
    out = capsys.readouterr().out
    assert "33333333" in out and "44444444" in out


def test_title_prefers_custom_and_falls_back_to_first_message(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    f = write(tmp_path, "-work-alpha", "a" * 8 + "-0000-0000-0000-000000000000",
              [user("first words here"), {"type": "custom-title", "customTitle": "Named"}])
    assert sessions.scan(f, "claude").title == "Named"
    g = write(tmp_path, "-work-alpha", "b" * 8 + "-0000-0000-0000-000000000000", [user("only a message")])
    assert sessions.scan(g, "claude").title == "only a message"


def test_limit_and_recency_order(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    for i in range(3):
        write(tmp_path, "-work-alpha", f"0000000{i}-0000-0000-0000-000000000000", [user(f"m{i}")], age_days=i + 0.5)
    sessions.main(["list", "--limit", "2"])
    out = capsys.readouterr().out
    assert "00000000" in out and "00000001" in out and "00000002" not in out
    assert out.index("00000000") < out.index("00000001")


def test_tail_flags_unfinished_tool_call(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    sid = "55555555-5555-5555-5555-555555555555"
    write(tmp_path, "-work-alpha", sid, [
        user("do it"),
        {"type": "assistant", "message": {"content": [
            {"type": "text", "text": "on it"},
            {"type": "tool_use", "id": "t1", "name": "Bash", "input": {}}]}},
    ], age_days=1)
    assert sessions.main(["tail", "55555555"]) == 0
    out = capsys.readouterr().out
    assert "Unfinished tool call" in out and "Bash" in out and "before retrying" in out
    assert sessions.main(["tail", "nomatch"]) == 1


def test_timestamps_use_owner_timezone(monkeypatch):
    from datetime import timedelta, timezone
    monkeypatch.setattr(sessions, "owner_tz", lambda: timezone(timedelta(hours=14)))
    assert sessions.fmt_time(0, "%H:%M") == "14:00"


def test_tail_sees_oversized_unanswered_write(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    sid = "66666666-6666-6666-6666-666666666666"
    big = "x" * ((512 * 1024) + 4096)
    write(tmp_path, "-work-alpha", sid, [
        user("write the file"),
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "w1", "name": "Write", "input": {"content": big}}]}},
    ], age_days=1)
    assert sessions.main(["tail", "66666666"]) == 0
    out = capsys.readouterr().out
    assert "Unfinished tool call" in out and "Write" in out
    assert "before retrying" in out


def test_markup_prompts_are_kept_but_wrappers_skipped(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    write(tmp_path, "-work-alpha", "77777777-7777-7777-7777-777777777777",
          [user("<task>fix the build</task>")])
    write(tmp_path, "-work-alpha", "88888888-8888-8888-8888-888888888888",
          [user("<system-reminder>hook noise</system-reminder>")])
    sessions.main(["list"])
    out = capsys.readouterr().out
    assert "77777777" in out and "88888888" not in out


def test_custom_title_survives_later_generated_title(tmp_path):
    f = write(tmp_path, "-work-alpha", "99999999-0000-0000-0000-000000000000", [
        user("hello"),
        {"type": "custom-title", "customTitle": "My name"},
        {"type": "ai-title", "aiTitle": "Generated"},
        {"type": "summary", "summary": "Summary"},
    ])
    assert sessions.scan(f, "claude").title == "My name"
    g = write(tmp_path, "-work-alpha", "aaaaaaaa-0000-0000-0000-000000000000", [
        user("hello"),
        {"type": "custom-title", "customTitle": "First"},
        {"type": "custom-title", "customTitle": "Renamed"},
    ])
    assert sessions.scan(g, "claude").title == "Renamed"


def test_pending_tool_call_on_live_session_is_not_called_a_crash(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    write(tmp_path, "-work-alpha", "66666666-6666-6666-6666-666666666666", [
        user("build it"),
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "t1", "name": "Bash", "input": {}}]}},
    ])
    monkeypatch.setattr(sessions, "ps_text", lambda: "claude --resume 66666666-6666-6666-6666-666666666666")
    assert sessions.main(["tail", "66666666"]) == 0
    out = capsys.readouterr().out
    assert "still pending" in out and "interrupted" not in out


def test_title_between_head_and_tail_is_found(tmp_path):
    filler = [{"type": "progress", "data": "x" * 1000} for _ in range(700)]
    f = write(tmp_path, "-work-alpha", "77777777-7777-7777-7777-777777777777",
              [user("first prompt")] + [{"type": "progress"}] * 450
              + [{"type": "custom-title", "customTitle": "Named mid-run"}] + filler + [user("last prompt")])
    assert sessions.scan(f, "claude").title == "Named mid-run"


def test_latest_rename_beats_older_title_in_head(tmp_path):
    filler = [{"type": "progress", "data": "x" * 1000} for _ in range(700)]
    f = write(tmp_path, "-work-alpha", "88888888-8888-8888-8888-888888888888",
              [{"type": "custom-title", "customTitle": "Old name"}, user("first")]
              + [{"type": "progress"}] * 450
              + [{"type": "custom-title", "customTitle": "New name"}] + filler + [user("last")])
    assert sessions.scan(f, "claude").title == "New name"


def test_project_named_tmp_something_is_not_throwaway(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    write(tmp_path, "-home-alice-src-tmp-cleaner", "99999999-9999-9999-9999-999999999999",
          [user("clean it", "/home/alice/src/tmp-cleaner")], 1)
    write(tmp_path, "-tmp-scratch", "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", [user("scratch", "/tmp/scratch")], 1)
    sessions.main(["list"])
    out = capsys.readouterr().out
    assert "99999999" in out and "aaaaaaaa" not in out


def test_skill_expansion_is_not_a_title(tmp_path):
    f = write(tmp_path, "-work-alpha", "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
              [user("Base directory for this skill: /x/y"), user("real question")])
    assert sessions.scan(f, "claude").title == "real question"


def codex_rollout(home, sid, records, day="2026/11/01", age_days=1.0):
    d = home / "sessions" / day
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"rollout-2026-11-01T10-00-00-{sid}.jsonl"
    t = time.time() - age_days * 86400
    stamp = datetime.fromtimestamp(t, timezone.utc).isoformat()
    f.write_text("\n".join(json.dumps({"timestamp": stamp, **r}) for r in records) + "\n")
    os.utime(f, (t, t))
    return f


def cmsg(role, text):
    kind = "input_text" if role == "user" else "output_text"
    return {"type": "response_item", "payload": {"type": "message", "role": role,
                                                  "content": [{"type": kind, "text": text}]}}


def meta(sid, source="user", cwd="/work/gamma"):
    return {"type": "session_meta", "payload": {"id": sid, "cwd": cwd, "thread_source": source}}


def test_codex_sessions_listed_named_and_filtered(tmp_path, monkeypatch, capsys):
    home = tmp_path / "codex"
    monkeypatch.setenv("CODEX_HOME", str(home))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "claude"))
    real = "01a00000-0000-7000-8000-000000000001"
    guard = "01a00000-0000-7000-8000-000000000002"
    unnamed = "01a00000-0000-7000-8000-000000000003"
    codex_rollout(home, real, [meta(real), cmsg("user", "# AGENTS.md instructions for /work"),
                               cmsg("user", "<environment_context>x</environment_context>"), cmsg("user", "plan the launch")])
    codex_rollout(home, guard, [meta(guard, "guardian_review"), cmsg("user", "judge this")])
    codex_rollout(home, unnamed, [meta(unnamed), cmsg("user", "tidy the repo")], age_days=2)
    (home / "session_index.jsonl").write_text(json.dumps({"id": real, "thread_name": "Launch plan"}) + "\n")
    sessions.main(["list", "--source", "codex"])
    out = capsys.readouterr().out
    assert "Launch plan" in out and "| codex |" in out and real in out
    assert "tidy the repo" in out and guard not in out
    sessions.main(["list", "--source", "claude"])
    assert "Launch plan" not in capsys.readouterr().out
    sessions.main(["list", "--source", "codex", "--all"])
    assert guard in capsys.readouterr().out


def test_codex_tail_reports_pending_tool_call(tmp_path, monkeypatch, capsys):
    home = tmp_path / "codex"
    monkeypatch.setenv("CODEX_HOME", str(home))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "claude"))
    sid = "01a00000-0000-7000-8000-0000000000aa"
    done = {"type": "response_item", "payload": {"type": "custom_tool_call_output", "call_id": "c1"}}
    def call(cid, name):
        return {"type": "response_item", "payload": {"type": "custom_tool_call", "call_id": cid, "name": name}}

    codex_rollout(home, sid, [meta(sid), cmsg("user", "run it"), call("c1", "exec"), done, call("c2", "apply_patch")])
    assert sessions.main(["tail", "01a00000-0000-7000-8000-0000000000"]) == 0
    out = capsys.readouterr().out
    assert "tool: codex" in out and "apply_patch" in out and "exec," not in out and "before retrying" in out


def test_codex_live_needs_a_codex_process_and_ignores_our_own_call():
    sid = "01a00000-0000-7000-8000-0000000000bb"
    assert ("codex", sid) in sessions.live_processes(f"/usr/bin/codex resume {sid}")
    assert ("codex", sid) not in sessions.live_processes(f"python3 sessions.py tail {sid} # codex")
    assert ("codex", sid) not in sessions.live_processes(f"vim {sid}")
    assert ("codex", sid) not in sessions.live_processes(f"codex exec explain resume {sid}")
    assert ("claude", sid) not in sessions.live_processes(f"claude -p explain --resume {sid}")
    assert ("claude", sid) in sessions.live_processes(f"claude --session-id={sid}")
    assert ("codex", sid) in sessions.live_processes(f"node /opt/bin/codex.js -C /work resume {sid}")


def test_call_far_before_tail_window_is_still_pending(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    pad = [{"type": "progress", "data": "x" * 1000} for _ in range(700)]
    write(tmp_path, "-work-alpha", "cccccccc-cccc-cccc-cccc-cccccccccccc", [
        user("run two"),
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "a", "name": "Bash", "input": {}},
            {"type": "tool_use", "id": "b", "name": "Edit", "input": {}}]}},
    ] + pad + [
        {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "a", "content": "ok"}]}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "waiting"}]}},
    ], age_days=1)
    assert sessions.main(["tail", "cccccccc"]) == 0
    out = capsys.readouterr().out
    assert "Edit" in out and "Bash," not in out and "Unfinished" in out

def test_timezone_resolver_accepts_a_linked_vault_install(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    packaged = tmp_path / "toolkit" / "skills" / "util" / "sessions"
    (packaged / "scripts").mkdir(parents=True)
    (packaged / "scripts" / "sessions.py").touch()
    local = vault / "system" / "skills" / "sessions"
    local.parent.mkdir(parents=True)
    local.symlink_to(packaged, target_is_directory=True)
    scripts = vault / "system" / "scripts"
    scripts.mkdir()
    (scripts / "dateutil.py").write_text("""print('{"timezone": "Asia/Tokyo"}')""")
    monkeypatch.setattr(sessions, "__file__", str(local / "scripts" / "sessions.py"))
    sessions.owner_tz.cache_clear()
    try:
        assert str(sessions.owner_tz()) == "Asia/Tokyo"
    finally:
        sessions.owner_tz.cache_clear()


@pytest.mark.parametrize("parent_last", [True, False])
def test_codex_copied_parent_header_does_not_change_session_identity(tmp_path, monkeypatch, capsys, parent_last):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "empty"))
    parent, worker, user_fork = [f"11111111-2222-4333-8444-{n:012d}" for n in range(1, 4)]
    p = meta(parent, cwd="/work/parent")
    w = meta(worker, source="subagent", cwd="/work/worker")
    w["payload"].update(parent_thread_id=parent, agent_path="/root/test")
    # A user-created fork also carries a parent ID and can share its opening prompt.
    u = meta(user_fork, cwd="/work/fork")
    u["payload"]["parent_thread_id"] = parent
    prompt = cmsg("user", "Revisit the same question")
    codex_rollout(tmp_path, parent, [p, prompt])
    for sid, own in ((worker, w), (user_fork, u)):
        inherited = p if sid == worker else w
        records = [own, inherited] if parent_last else [inherited, own]
        codex_rollout(tmp_path, sid, [*records, prompt])

    for args in (["list"], ["search", "same question"]):
        sessions.main([*args, "--json"])
        assert {r["id"] for r in json.loads(capsys.readouterr().out)} == {parent, user_fork}
    sessions.main(["list", "--all", "--json"])
    data = {r["id"]: r for r in json.loads(capsys.readouterr().out)}
    assert data[worker]["background"] and data[worker]["parent_id"] == parent
    assert data[worker]["cwd"] == "/work/worker" and data[user_fork]["cwd"] == "/work/fork"
    sessions.main(["list", "--all"])
    row = next(line for line in capsys.readouterr().out.splitlines() if worker in line)
    assert "background" in row
    sessions.main(["inspect", worker])
    inspected = capsys.readouterr().out
    assert "folder: /work/worker" in inspected
    assert parent in inspected


def test_codex_legacy_worker_header_without_id_still_resolves(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "empty"))
    sid = "33333333-3333-4333-8333-333333333333"
    parent = "44444444-4444-4444-8444-444444444444"
    legacy = {"type": "session_meta", "payload": {"cwd": "/work/legacy",
              "source": {"subagent": {"thread_spawn": {"parent_thread_id": parent}}}}}
    codex_rollout(tmp_path, sid, [meta(parent), legacy, cmsg("user", "legacy work")])
    sessions.main(["list", "--json"])
    assert json.loads(capsys.readouterr().out) == []
    sessions.main(["list", "--json", "--all"])
    row, = json.loads(capsys.readouterr().out)
    assert (row["cwd"], row["background"], row["parent_id"]) == ("/work/legacy", True, parent)
