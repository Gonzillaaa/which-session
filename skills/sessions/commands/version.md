---
description: "Print the installed Which Session version."
---

# /sessions:version

Run `python3` with the absolute path to `scripts/sessions.py` in the loaded `sessions` skill directory and the argument `version`. For the default Claude Code user installation:

```sh
python3 "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/sessions/scripts/sessions.py" version
```

Return the one line printed by the command. This reads the version shipped with the loaded skill, including when it is installed from a source archive or toolkit bundle.
