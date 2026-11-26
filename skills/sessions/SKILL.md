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

Recover a local Claude Code or Codex conversation. Read its recorded messages and tool outcomes, explain where it stopped, and show the user how to reopen it. Both hosts install this same skill directory. Claude history lives under `CLAUDE_CONFIG_DIR` (default `~/.claude`) and Codex history under `CODEX_HOME` (default `~/.codex`). Each host can read both histories if its shell has access.

## 2. Commands

Use the same command guide in either host. In Claude Code the user can invoke a slash command. In Codex the user types `$sessions` and asks for the action. Run the command for them and return its output in chat.

| Task | Claude Code | Codex | Guide |
| --- | --- | --- | --- |
| List recent sessions | `/sessions:list 7 4` | `$sessions list my last four sessions` | [List](commands/list.md) |
| Search messages | `/sessions:search "retry policy" --days 30` | `$sessions find "retry policy" from the past 30 days` | [Search](commands/search.md) |
| Inspect one session | `/sessions:inspect ID --n 8` | `$sessions inspect ID and show the last eight messages` | [Inspect](commands/inspect.md) |
| Show usage | `/sessions:help` | `$sessions help` | [Help](commands/help.md) |
| Show the installed version | `/sessions:version` | `$sessions version` | [Version](commands/version.md) |

Also route plain requests such as “what was I working on?” to list, and `sessions:help` or `sessions:version` to the corresponding guides. Help and version require no transcript access.

## 3. Running the bundled command

Run Python 3 with the absolute path to `scripts/sessions.py` inside the loaded skill. Keep the caller’s working directory so `--here` selects the right project. At the default user installation the script is under `~/.claude/skills/sessions/` or `~/.codex/skills/sessions/`. A standalone checkout uses the same script through `which-session`.

- **List** with `list --plain --ungrouped` for one row per transcript in chat. The default is the past 7 days, newest activity first, up to 15 rows. “My last four” adds `--limit 4`.
- **Search** with `search "retry policy"` for one excerpt per session, newest matching message first. Pass the phrase as one literal argument. List and search accept `--days N`, `--limit N`, `--folder TEXT`, `--here`, `--source claude|codex|all`, `--all` and `--json`. Only list accepts `--plain` and `--ungrouped`.
- **Inspect** with `inspect ID` for up to four recent messages, recorded tool outcomes and resume guidance. Pass `--n N` for more messages or `--file PATH` to select a copy from the CLI’s printed choices.
- **Terminal browsing** is for the user’s own terminal. `which-session list` opens the keyboard browser. `pick` is a CLI alias for `list`, and `tail` is an alias for `inspect`.

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

Report the recorded tool, file targets, outcome and printed next step. A recorded nonzero exit code calls for reviewing the error. An output with no structured success or failure leaves the outcome unknown. When several transcripts match, present the CLI’s file choices and inspect the selected copy with `--file`. For duplicate IDs within one host, explain why the client cannot select that copy by ID. A missing result
leaves the effect of the operation unknown. If a matching process is running, check
it first. Copy the script's quoted resume command exactly. If it cannot identify
the original directory or full ID, ask the user for the missing information.

## 6. Hard rules

- Report only what the script printed. Do not guess a title, folder, or id.
- A transcript missing from the table is not a session that never existed:
  widen `--days` or add `--all` before saying it is gone.
- Never delete or move transcripts.
