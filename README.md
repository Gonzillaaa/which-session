# Which Session

Find the Claude Code or Codex conversation you remember, see where it stopped and get the command to reopen it in its original directory.

## Try it

Start in a checkout of this repository on macOS or Linux with Python 3.9 or newer. These commands work before installation.

```sh
./which-session list
./which-session search "retry policy" --days 30
```

To inspect a result, run the following in your terminal and paste the full ID or a unique prefix when prompted.

```sh
printf 'Session ID: '
if IFS= read -r session_id && [ -n "$session_id" ]; then
    ./which-session inspect "$session_id"
fi
```

An empty history prints a short message and exits successfully. To try both hosts with disposable data, run the [synthetic walkthrough](examples/README.md).

## Install for your account

From the checkout, run:

```sh
python3 install.py
```

The installer links `which-session` into `~/.local/bin` and registers the `sessions` skill in Codex and Claude Code. It also registers the Claude `/sessions:list`, `/sessions:search`, `/sessions:inspect` and `/sessions:help` commands. New agent sessions can discover the skill. In Codex, invoke `$sessions` or ask it to find a conversation.

Keep the checkout in place. Changes to it reach your installed commands immediately. If the shell cannot find `which-session`, run `export PATH="$HOME/.local/bin:$PATH"` and add that line to your shell startup file. You can choose an existing directory on your PATH with `python3 install.py --bin-dir DIRECTORY`. The original checkout command `./sessions` remains an alias.

Running the installer again recognizes existing links to this checkout, including links managed by another installer. It reports the path of any conflicting command or skill so you can review it. To uninstall the links it created, run:

```sh
python3 install.py --uninstall
```

Use the same `--bin-dir` and agent configuration directories for uninstall. The installer tracks its links under `${XDG_STATE_HOME:-~/.local/state}/which-session/` and preserves pre-existing links and transcript files.

## Finding a conversation

| What you remember | Command |
| --- | --- |
| Roughly when you worked | `which-session list --days 14` orders sessions by recorded message or tool activity. |
| A few words from the conversation | `which-session search "retry policy"` finds literal, case-insensitive phrases in user and assistant messages and shows the speaker and an excerpt. |
| The project | `which-session list --here` limits results to the current directory. `--folder TEXT` matches part of a recorded path. |
| An interrupted edit | `which-session inspect ID` shows recent exchanges, recorded tool outcomes and what to check next. It prints the native resume command for you to run. |

List and search default to the last seven days and 15 results. To widen a search, try `which-session list --days 90 --limit 100 --all`. The default view hides temporary projects, background or empty sessions, and undated histories. `--all` includes these within the selected window and includes undated histories as unknown. Codex worker sessions can inherit the parent’s opening prompt. List and search hide these workers by default. With `--all` they are labeled `codex (background)`; inspecting one shows its recorded parent when available. Independent user sessions and user-created forks can share a title and appear separately. Use `--source claude` or `--source codex` to narrow either command. Inspection by ID also works outside the list’s date window.

The CLI reads Claude project logs under `${CLAUDE_CONFIG_DIR:-~/.claude}/projects/*/*.jsonl` and Codex rollouts under `${CODEX_HOME:-~/.codex}/sessions/YYYY/MM/DD/rollout-*.jsonl`. If you use a custom agent directory, set the corresponding environment variable before searching or installing. Archived Codex rollouts stored separately, cloud-only conversations and other agents fall outside these locations.

Search runs locally and on demand. Normal output can reveal session IDs, project names and matching passages. Inspection can include recent conversation text, local paths and file targets. With `--json`, list and search also expose the transcript path, working directory and last user message. Any excerpts shown inside a hosted agent enter that conversation.

## Development

The CLI uses the Python standard library. Tests generate synthetic transcripts in temporary directories.

```sh
uv run --with pytest pytest -q
uvx ruff check .
```

[MIT license](LICENSE)
