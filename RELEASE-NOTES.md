# Which Session release notes

## 0.2.0

Run `which-session list` in a terminal to browse recent conversations from Claude Code and Codex, newest activity first. Type a title or folder, use the arrows to preview where a conversation stopped, and press Enter to inspect it. Repeated runs of a configured job appear together. Expand a group to inspect an older run.

**Upgrading from 0.1.0.** Add `--plain` if you want the previous print-and-exit behavior in a terminal. Add `--ungrouped` to see every run. Piped Markdown and JSON keep one row per transcript. Printed output defaults to 15 entries. The browser includes all eligible entries within the date window unless you pass a limit.

**Using the skill.** Claude Code and Codex install the same instructions, program and settings. In a new chat, try `/sessions:list 7 4` in Claude Code or `$sessions list my last four sessions` in Codex. Both support listing, searching, inspecting, help and version. [Install and first-use guide](README.md#install-on-macos-or-linux) · [All commands and options](README.md#terminal-command-reference)

## 0.1.0

Find a Claude Code or Codex conversation from a phrase you remember. Inspect the last exchange, see whether an interrupted tool call recorded a result, and copy the command to reopen the conversation in its original directory.

### Try it

On macOS or Linux with Python 3.9 or newer, use the following commands. The demo creates two disposable histories.

```sh
git clone --branch v0.1.0 https://github.com/Gonzillaaa/which-session.git
cd which-session
python3 examples/demo.py
```

To install the terminal command and both agent skills for your account, run `python3 install.py` from a checkout you will keep. Run `which-session --version` to confirm the install. In a fresh agent session, use `/sessions:help` in Claude Code or `$sessions help` in Codex.

### What you can recover

- List sessions by their last recorded activity, or search for a phrase in user and assistant messages. Background Codex workers are hidden by default. Use `--all` to include them.
- Inspect a session to see file targets, available tool results, and what to do next. If a call ended without a recorded result, inspect its target before retrying.
- Distinguish restored copies with the same ID using the printed file choices. If the native client cannot tell two copies apart, the CLI explains the ambiguity.

Which Session reads local Claude project transcripts and dated Codex rollouts. Cloud-only conversations and separately archived rollouts fall outside that scope. Terminal searches run locally. When a hosted agent shows an excerpt, it becomes part of that agent conversation.

For a bug report, include the OS, host version, command and a synthetic example. [Report an issue](https://github.com/Gonzillaaa/which-session/issues) · [Quickstart](https://github.com/Gonzillaaa/which-session/tree/v0.1.0#readme)
