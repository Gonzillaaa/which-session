---
description: "Table of recent Claude Code and Codex sessions (title, tool, folder, last active, full id) for recovering lost work."
argument-hint: "[days] [limit] [--folder TEXT] [--here] [--all] [--source claude|codex|all]"
---

# /sessions:list

Read-only. Defaults to the last 7 days and 15 rows.

## Steps

1. Turn the request into flags: a number of days, a row limit, an optional
   `--folder` or `--here`. "last 4" means `--limit 4`.
2. Run:
   ```bash
   sessions_skill="${CLAUDE_SKILL_DIR:-${CLAUDE_HOME:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}}/skills/sessions}"
   if [[ ! -f "$sessions_skill/scripts/sessions.py" && -f system/registries/paths.yaml ]]; then
       sessions_skill=system/skills/sessions
   fi
   python3 "$sessions_skill/scripts/sessions.py" list --plain --ungrouped --days <days> --limit <limit>
   ```
3. Show the table exactly as printed, with the full ids.
4. Inspect the selected session and use the next step and resume command it prints.
