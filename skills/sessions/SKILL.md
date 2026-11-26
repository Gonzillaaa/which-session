---
name: sessions
description: "Lists your recent Claude Code and Codex sessions (title, tool, folder, last active, full id) so you can recover work after a crash, an accidental quit, or a closed editor. Finds remembered phrases in user and assistant messages. Use when the owner says 'my sessions', 'list sessions', 'I lost my sessions', 'recover sessions', 'what was I working on', or 'resume a session'. Also handles sessions:help and sessions:version."
trigger_patterns:
  - "sessions:help"
  - "sessions:version"
  - "my sessions"
  - "list sessions"
  - "recent sessions"
  - "lost my sessions"
  - "recover sessions"
  - "what was I working on"
allowed-tools: [Bash, Read]
tier: extension
---

# sessions: find and recover recent sessions

## 1. Role

Claude Code stores local project transcripts under `~/.claude/projects/<folder>/<id>.jsonl`.
This skill also reads file-backed Codex rollouts under `~/.codex/sessions/YYYY/MM/DD/rollout-*-<id>.jsonl`.
The corresponding overrides are `CLAUDE_CONFIG_DIR` and `CODEX_HOME`. Recovery requires a saved transcript in one of those locations. This skill lists those transcripts as
a table and checks whether a session died mid-task, so you can reopen the ones
you still need. It is read-only: it never writes, resumes, or deletes anything.

## 2. Commands

| Command | What it does |
|---|---|
| `/sessions:list [days] [limit]` | Table of recent sessions. Defaults: last 7 days, 15 rows. |
| `/sessions:search "phrase"` | Search recent conversations and show one matching passage per session. |
| `/sessions:inspect <id>` | Last few messages of one session, and whether it died mid-task. |
| `/sessions:help` | Show commands and usage examples. |
| `/sessions:version` | Print the installed skill version. |

In Codex, route `$sessions help` or `sessions:help` to [commands/help.md](commands/help.md).
Route `$sessions version` or `sessions:version` to [commands/version.md](commands/version.md).
These requests do not need a history search.

For session recovery in Codex, invoke `$sessions` or ask in plain words ("list my sessions",
"inspect session 01a1...") and run the scripts in section 3 yourself. The
script and its output are identical in both tools.

## 3. How to run it

If the global CLI is installed, use `which-session list`, `which-session search` or
`which-session inspect`. Otherwise use the full path to `scripts/sessions.py` inside the skill directory supplied by
the agent. Keep the caller's working directory so `--here` filters the right project.
The script uses the Python standard library. For example, with the global Codex install:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/sessions/scripts/sessions.py" list --days 7 --limit 15
python3 "${CODEX_HOME:-$HOME/.codex}/skills/sessions/scripts/sessions.py" search "email draft" --days 30
python3 "${CODEX_HOME:-$HOME/.codex}/skills/sessions/scripts/sessions.py" tail <id-or-prefix>
```

`list` options: `--days N`, `--limit N`, `--folder TEXT` (match part of the
folder path), `--here` (only this directory), `--all` (include empty and
throwaway sessions), `--source claude|codex|all` (default all), `--json`.

For “find where we discussed X,” use `search "X"`. Pass the phrase as one literal argument.
Search matches user and assistant text case-insensitively across line breaks. It returns
one excerpt per session, ordered by the newest matching message in the selected window.
It accepts the same filters as list. Both commands default to seven days.

Plain requests map directly: "my last 4 sessions" is `--limit 4`; "this week"
is `--days 7`; "yesterday's work in myproject" is `--days 2 --folder myproject`.

For interactive browsing, a user can run `which-session pick` in their own terminal, type a title or project, preview the selected conversation, and press Enter to inspect it. For agent requests, use the noninteractive `list`, `search` and `inspect` commands. Captured Markdown and JSON include individual transcripts. The terminal list groups configured recurring jobs by agent and project. Use `list --ungrouped` to see each run in a terminal.

## 4. Reading the table

- **Session** is the session's name, or its first message when it has none.
- **Tool** is `claude` or `codex`. Codex background threads (safety reviewers,
  sub-agents) are hidden unless `--all`. The rollout’s own metadata identifies workers even when they inherit a parent’s prompt and metadata. With `--all`, worker rows are labeled `codex (background)`. Inspection shows their recorded parent ID when available.
- **Last active** comes from the latest dated conversation turn, tool call or result.
  File copies and metadata updates do not move a session up the list. Undated histories
  appear as `unknown` with `--all` or can be inspected by ID.
- **(live)** means a visible agent process explicitly names that session. An unmarked
  session can still be open. File modification time is available separately in JSON.
- **Full id** is the whole id, never shortened, ready to paste.
- Empty sessions and throwaway sessions in temp folders (review kits, test
  runs) are hidden unless `--all`.

## 5. Recovering one

Run `tail <id-or-prefix>` or `inspect <id-or-prefix>`. Report the recorded tool, file targets, outcome and printed next step. A recorded nonzero exit code calls for reviewing the error. An output with no structured success or failure leaves the outcome unknown. When several transcripts match, present the CLI’s file choices and inspect the selected copy with `--file`. For duplicate IDs within one host, explain why the client cannot select that copy by ID. A missing result
leaves the effect of the operation unknown. If a matching process is running, check
it first. Copy the script's quoted resume command exactly. If it cannot identify
the original directory or full ID, ask the user for the missing information.

## 6. Hard rules

- Report only what the script printed. Do not guess a title, folder, or id.
- A transcript missing from the table is not a session that never existed:
  widen `--days` or add `--all` before saying it is gone.
- Never delete or move transcripts.
