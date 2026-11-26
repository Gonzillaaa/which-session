---
description: "Print the installed Which Session version."
---

# /sessions:version

Run `python3` with the absolute path to `scripts/sessions.py` in the loaded `sessions` skill directory and the argument `version`. Use the script in the skill that handled the request so a different CLI on the shell’s path cannot supply its version. For example, in a default Claude Code installation run the following command.

```sh
python3 "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/sessions/scripts/sessions.py" version
```

Return the one line printed by the command. This reads the version shipped with the loaded skill, including when it is installed from a source archive or toolkit bundle.
