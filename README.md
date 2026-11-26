# Which Session

Find a Claude Code or Codex conversation by a phrase you remember, see where it stopped, and get the command to reopen it in its original project. Use the `sessions` skill inside either agent or run `which-session` in your terminal. All three search the same local histories.

![Excerpt from a synthetic Codex session. Searching for “retry policy” finds Backoff tests. Inspecting it shows that a command exited with code 1 and suggests reviewing the recorded error before retrying.](examples/recovery-preview.png)

## Install the skill and CLI

On macOS or Linux with Python 3.9 or newer, clone the repository somewhere you plan to keep it. Run the installer once for both agents and the terminal.

```sh
git clone https://github.com/Gonzillaaa/which-session.git
cd which-session
python3 install.py
```

If you prefer a release archive, extract it to a permanent folder and run `python3 install.py` from that folder. The installer creates links back to these files, so edits and updates take effect in place. [Download the latest release](https://github.com/Gonzillaaa/which-session/releases/latest)

| Interface | Default install location |
| --- | --- |
| Claude Code | `~/.claude/skills/sessions` for the skill and `~/.claude/commands/sessions/` for the slash commands |
| Codex | `~/.codex/skills/sessions` for the skill |
| Terminal | `~/.local/bin/which-session` |

If you use a custom agent directory, set `CLAUDE_CONFIG_DIR` or `CODEX_HOME` before installing. If your shell cannot find `which-session`, run `export PATH="$HOME/.local/bin:$PATH"` and add that line to your shell startup file for future terminals. You can also choose an existing directory on your PATH with `python3 install.py --bin-dir DIRECTORY`.

To uninstall, run `python3 install.py --uninstall` from the same checkout with the same directory settings. It removes only links it created. You can rerun the installer, and it reports any conflicting destinations.

## Use the skill in Claude Code or Codex

Start a fresh chat after installation. In Claude Code, type the slash command in the chat input. In Codex, type `$sessions` followed by your request.

| What you want to do | Claude Code | Codex |
| --- | --- | --- |
| List your last four sessions from the past week | `/sessions:list 7 4` | `$sessions list my last four sessions from the past week` |
| Find a phrase from the past month | `/sessions:search "retry policy" --days 30` | `$sessions find "retry policy" from the past 30 days` |
| See where a session stopped | `/sessions:inspect ID` | `$sessions inspect ID` |
| Show usage or version | `/sessions:help` or `/sessions:version` | `$sessions help` or `$sessions version` |

Replace `ID` with a full ID or a unique prefix from the results. Inspection shows the last recorded action and, when it can identify the original session and folder, prints the resume command. Run that command in your terminal when you want to reopen the conversation.

## Try it in the terminal

From the checkout or extracted folder, these commands work even before installation. After installation, use `which-session` from any folder. Replace the quoted phrase with one you remember.

```sh
./which-session list
./which-session search "retry policy" --days 30
```

In a terminal, columns align to the window width. In a narrow window, each session’s full ID appears on its own line for copying. Piping the output produces a Markdown table. Use `--json` for scripts.

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

For terminal usage or the installed version, run `which-session help` or `which-session --version`.

## Pick a session with the keyboard

Run `which-session pick` in a terminal, or `which-session pick --here` to browse the current project. The picker starts with the past seven days. Type part of a title or project path to filter, then use the arrow keys to move. The preview shows the last user request, the last recorded tool call and its outcome, the full session ID, and available resume instructions.

Press **Enter** on a session to print its inspection and return to your shell. Press **Esc** to leave the picker. To reopen a conversation, run the resume command from its inspection.

### Recurring jobs

The terminal list and picker combine repeated runs of a known job in the same project and agent. For example, six heartbeat runs appear as **Heartbeat runner · 6 runs** at the position of the latest run. The group's time and ID belong to that run. In the picker, **Right** or **Enter** expands a group so you can select an older run. **Left** collapses it.

Use `which-session list --ungrouped` for one row per transcript. Search results, piped Markdown and JSON also show individual sessions. In the grouped terminal list, `--limit` counts visible entries. The picker browses every eligible entry unless you pass a limit.

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

## Why Python?

Claude Code and Codex both write one JSON record per line, but they represent messages and tool results differently. To tell you whether an interrupted command actually failed, Which Session has to match the tool call to its result by ID. Python's standard library handles JSON parsing, timestamps and shell quoting for paths such as `Jane's project`. A shell script would need its own JSON handling or an extra tool such as `jq`. The CLI and both agent integrations reuse the same Python parser.

## Development and feedback

The `recurring_jobs` array in the skill settings defines each job's display `name` and literal `opening`. The first user message must begin with that opening followed by whitespace or the end of the message. Use the complete invocation to distinguish one job from another. An empty array disables grouping. [Skill settings](skills/sessions/scripts/settings.json)

```sh
uv run --with-requirements requirements-dev.txt pytest -q
uv run --with-requirements requirements-dev.txt ruff check . which-session
```

For a bug report, include your OS, agent version, `which-session --version`, the command and the result you expected. A synthetic example helps others reproduce it. [Report an issue](https://github.com/Gonzillaaa/which-session/issues) · [MIT license](LICENSE)
