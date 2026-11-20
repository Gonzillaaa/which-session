# Session Reentry

Find the Claude Code or Codex conversation you were working in, see where it stopped, and get the command to reopen it in its original directory.

## Try it

From the checkout, with Python 3.9 or newer installed, run:

```sh
./sessions list
./sessions search "retry policy" --days 30
./sessions inspect <id-or-unique-prefix>
```

Replace `<id-or-unique-prefix>` with an ID from the results. To use the command from any project, place a symlink to the checkout’s `sessions` executable in a directory on your PATH. Then `sessions list --here` shows work from your current directory.

| If you remember… | Use |
| --- | --- |
| Working on something recently | `sessions list` orders conversations by their latest recorded message or tool activity. Copying a log leaves that ordering intact. |
| A few words from the discussion | `sessions search "retry policy"` shows the matching speaker, text and session ID for each conversation. |
| An edit that might have been interrupted | `sessions inspect ID` shows the last exchanges and recorded tool results. If a file operation lacks a result, it tells you what to check before retrying. |

The CLI reads the native logs under `~/.claude/projects` and `~/.codex/sessions`. It honors `CLAUDE_CONFIG_DIR` and `CODEX_HOME`. Searches run locally, on demand. Any matching excerpts you choose to show inside a coding agent become part of that agent’s conversation. Inspection prints a resume command for you to run.

## Agent skill

The same implementation powers the [sessions skill](skills/sessions/SKILL.md). To install it manually on macOS or Linux, run the commands for your host from this checkout. The link destinations must be available.

**Codex**

```sh
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
ln -s "$PWD/skills/sessions" "${CODEX_HOME:-$HOME/.codex}/skills/"
```

**Claude Code**

```sh
claude_dir="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
mkdir -p "$claude_dir/skills" "$claude_dir/commands"
ln -s "$PWD/skills/sessions" "$claude_dir/skills/"
[ ! -e "$claude_dir/commands/sessions" ] && ln -s "$PWD/skills/sessions/commands" "$claude_dir/commands/sessions"
```

Invoke `$sessions` in Codex or `/sessions:list` in Claude Code.

## Development

The runtime uses the Python standard library. Tests generate synthetic transcripts in temporary directories. Run the suite and linter with:

```sh
uv run --with pytest pytest -q
uvx ruff check .
```

[MIT license](LICENSE)
