---
description: "Find a remembered phrase in recent Claude Code or Codex conversations."
argument-hint: '"phrase" [--days N] [--folder TEXT] [--source claude|codex|all]'
---

# /sessions:search

Resolve the skill directory from the loaded sessions skill. Run Python with the
absolute path to its `scripts/sessions.py`, the `search` subcommand, and the
user's phrase as one literal argument. Keep the original working directory.
Pass requested list filters. Return the matching passage, speaker, session ID,
and folder. Inspect a selected match before suggesting recovery.
