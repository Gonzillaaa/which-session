# Which Session

Find the Claude Code or Codex conversation you remember and reopen it where you left off. Search across both tools by a phrase you typed, inspect the last recorded action, and copy the resume command for the original project.

![Excerpt from a synthetic Codex session. Searching for “retry policy” finds Backoff tests. Inspecting it shows that a command exited with code 1 and suggests reviewing the recorded error before retrying.](examples/recovery-preview.png)

## Get the code

Which Session runs on macOS and Linux with Python 3.9 or newer. It uses the Python standard library.

```sh
git clone https://github.com/Gonzillaaa/which-session.git
cd which-session
```

You can also download and extract the [latest release](https://github.com/Gonzillaaa/which-session/releases/latest).

## Try it

From the checkout or extracted folder, list recent conversations. Replace the quoted phrase with one you remember.

```sh
./which-session list
./which-session search "retry policy" --days 30
```

To inspect a match, paste its full ID or a unique prefix at the prompt. If the transcript identifies a single original session and folder, inspection prints the command to reopen it. You choose when to run it.

```sh
printf 'Session ID: '
if IFS= read -r session_id && [ -n "$session_id" ]; then
    ./which-session inspect "$session_id"
fi
```

If your history is empty, try the same workflow with two disposable sessions. The demo shows an interrupted Claude Code edit and a failed Codex command. [Demo details](examples/README.md)

```sh
python3 examples/demo.py
```

## Install for your account

To run `which-session` from any folder and use the `sessions` skill in both agents, keep the checkout in a permanent location and run:

```sh
python3 install.py
```

Start a fresh agent session to discover the skill.

| | Search | Help | Version |
| --- | --- | --- | --- |
| Terminal | `which-session search "retry policy"` | `which-session help` | `which-session --version` |
| Claude Code | `/sessions:search "retry policy"` | `/sessions:help` | `/sessions:version` |
| Codex | `$sessions search "retry policy"` | `$sessions help` | `$sessions version` |

The installer links the CLI into `~/.local/bin`. If your shell cannot find it, run `export PATH="$HOME/.local/bin:$PATH"` in this terminal. Add the same line to your shell startup file for future terminals. You can also install with `--bin-dir DIRECTORY` to choose a directory already on your PATH. Changes to the checkout reach the linked commands immediately.

Run `python3 install.py --uninstall` from the same checkout to remove the links the installer created. Use the same bin and agent directories you chose at install time. Existing links and transcript files are preserved. The installer reports conflicting destinations and can be run again.

## Finding a missing session

| What you remember | What to run |
| --- | --- |
| The project folder | `which-session list --here` from the project, or `which-session list --folder TEXT` for a partial folder name. |
| The agent | Add `--source claude` or `--source codex` to a list or search. |
| A conversation further back | `which-session list --days 90 --limit 100 --all` widens the default seven-day window and 15-row limit. |
| A session ID | `which-session inspect ID` works outside the list’s date window. If several files share an ID, use one of the printed `--file` choices. |

Activity comes from recorded turns and tool events. Search matches literal phrases in user and assistant messages, ignoring case. The default list and search hide background workers, temporary projects, and empty or undated sessions. `--all` includes them. Independent sessions can share a title.

## History and privacy

The CLI reads transcripts locally without changing them. It looks for Claude Code project logs in `~/.claude/projects` and dated Codex rollouts in `~/.codex/sessions`. Set `CLAUDE_CONFIG_DIR` or `CODEX_HOME` for custom locations. Separately archived rollouts and cloud-only conversations are outside this search.

A list includes project names and full session IDs. A search adds matching text. Inspection shows recent exchanges and paths. JSON output from list or search also includes the full transcript path, working directory and last user message. Excerpts you display inside a hosted agent become part of that conversation.

## Development and feedback

```sh
uv run --with pytest pytest -q
uvx ruff check . which-session
```

For a bug report, include your OS, agent version, `which-session --version`, the command and the result you expected. A synthetic example helps others reproduce it. [Report an issue](https://github.com/Gonzillaaa/which-session/issues) · [MIT license](LICENSE)
