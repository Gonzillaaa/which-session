---
description: "Find a remembered phrase in recent Claude Code or Codex conversations."
argument-hint: '"phrase" [--days N] [--limit N] [--folder TEXT] [--here] [--source claude|codex|all] [--all] [--json]'
---

# /sessions:search

Resolve the skill directory from the loaded sessions skill. Run Python with the
absolute path to its `scripts/sessions.py`, the `search` subcommand, and the
user's phrase as one literal argument. Keep the original working directory.
For example, `/sessions:search "retry policy" --here --days 30` runs `search "retry policy" --here --days 30`. Forward the requested search options shown above.

Return each matching passage with its speaker, session ID and folder, newest match first. Return JSON if requested. Inspect the user’s selected result before suggesting recovery.
