---
description: "Usage for the sessions skill."
---

# /sessions:help

Show the five actions using the syntax for the current chat. Claude Code also accepts a request in plain language after `/sessions`, just as Codex does after `$sessions`.

| Action | Claude Code | Codex |
| --- | --- | --- |
| List up to four sessions from the past week | `/sessions:list 7 4` | `$sessions list my last four sessions this week` |
| Find a phrase from the past month | `/sessions:search "retry policy" --days 30` | `$sessions find "retry policy" in the past month` |
| Inspect a result | `/sessions:inspect ID` | `$sessions inspect ID` |
| Show this guide | `/sessions:help` | `$sessions help` |
| Check the installed version | `/sessions:version` | `$sessions version` |

Both hosts use the same histories and filters. List defaults to 15 sessions from the past 7 days. Use the ID or a unique prefix from a result to inspect it. Inspection shows the last four messages by default, the latest recorded tool outcome, and a resume command when available.

For keyboard browsing in your own terminal, run `which-session list`. Type a title or folder, use the arrow keys to preview, and press Enter to inspect or expand a group. Esc exits. Use `which-session list --plain` for a copyable table or `which-session help` for terminal commands.
