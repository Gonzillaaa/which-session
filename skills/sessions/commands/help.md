---
description: "Usage for the sessions skill."
---

# /sessions:help

- `/sessions:list [days] [limit]`: recent sessions as a table. Defaults 7 days, 15 rows.
- `/sessions:search "phrase"`: matching passages from recent conversations, newest match first.
- `/sessions:inspect <id>`: last messages of one session, and whether it died mid-task.

Examples: "my last 4 sessions", "sessions this week", "sessions in myproject".
Inspection prints the next step and, when the original session can be identified, its resume command. If multiple transcripts share an ID, use the printed `--file` choices to inspect a particular copy.
Add `--source claude` or `--source codex` to list one tool only.
