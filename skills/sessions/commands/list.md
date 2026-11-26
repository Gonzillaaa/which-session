---
description: "Table of recent Claude Code and Codex sessions (title, tool, folder, last active, full id) for recovering lost work."
argument-hint: "[days] [limit] [--folder TEXT] [--here] [--all] [--source claude|codex|all] [--json]"
---

# /sessions:list

Read-only. Defaults to the last 7 days and 15 rows.

Use the loaded skill’s `scripts/sessions.py` in the user’s original working directory. In a standalone Claude Code install the script is at `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/sessions/scripts/sessions.py`. A vault installation may provide it at `system/skills/sessions/scripts/sessions.py`.

1. Run `list --plain --ungrouped`. Map the first two positional numbers to `--days` and `--limit`. For example, `/sessions:list 7 4 --here --source claude` runs `list --plain --ungrouped --days 7 --limit 4 --here --source claude`.
2. Pass any requested `--folder TEXT`, `--here`, `--source`, `--all`, or `--json`. Preserve spaces in folder names by passing the name as one argument.
3. Show the table with the full IDs, or return the JSON when requested. When the user chooses a result, follow the inspect guide.
