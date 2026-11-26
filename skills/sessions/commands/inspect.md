---
description: "Show a session’s recent messages, recorded tool outcomes and resume guidance."
argument-hint: "ID [--n N] [--file PATH]"
---

# /sessions:inspect

Run the loaded skill’s `scripts/sessions.py` with `inspect` and the full ID or unique prefix. In a standalone Claude Code install the script is at `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/sessions/scripts/sessions.py`. A vault installation may provide it at `system/skills/sessions/scripts/sessions.py`.

- Show the last four messages by default. For `/sessions:inspect ID --n 8`, pass `inspect ID --n 8`. Replace `ID` with the user’s selection.
- If the ID matches several transcripts, show the CLI’s choices. Pass the selected path as one argument to `--file`. Keep any warning about duplicate IDs or a missing project folder.
- Report the recorded action, relevant files, missing or failed results, and the printed next step. Copy the resume command exactly when one is available. The user runs it in their terminal.
