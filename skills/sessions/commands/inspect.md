---
description: "Show the last messages of one session and whether it died mid-task."
argument-hint: "<session id or unique prefix>"
---

# /sessions:inspect

Read-only.

## Steps

1. Run:
   ```bash
   sessions_skill="${CLAUDE_SKILL_DIR:-${CLAUDE_HOME:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}}/skills/sessions}"
   if [[ ! -f "$sessions_skill/scripts/sessions.py" && -f system/registries/paths.yaml ]]; then
       sessions_skill=system/skills/sessions
   fi
   python3 "$sessions_skill/scripts/sessions.py" tail <id-or-prefix> --n 4
   ```
2. Report the last recorded action, relevant file paths, any missing results and the printed next step.
3. Show the exact resume command emitted by the script. If the folder is unavailable, include that qualification. If no command was printed, report the missing evidence.
