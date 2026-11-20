---
description: "Usage for the sessions skill."
---

# /sessions:help

- `/sessions:list [days] [limit]` lists recent sessions. The default is 15 rows from the past 7 days.
- `/sessions:search "phrase"` finds matching passages, newest first.
- `/sessions:inspect <id>` shows the last exchanges, tool outcomes and next step.
- `/sessions:help` shows these commands.
- `/sessions:version` prints the installed version.

In Codex, use `$sessions help` or `$sessions version`. In a terminal, use `which-session help` or `which-session --version`.

For example, ask for “my last 4 sessions” or “sessions this week”.
Inspection prints the next step and, when the original session can be identified, its resume command. If multiple transcripts share an ID, use the printed `--file` choices to inspect a particular copy.
Add `--source claude` or `--source codex` to list one tool only.
