# Which Session 0.1.0

Find a Claude Code or Codex conversation from a phrase you remember. Inspect the last exchange, see whether an interrupted tool call recorded a result, and copy the command to reopen the conversation in its original directory.

## Try it

On macOS or Linux with Python 3.9 or newer, use the following commands. The demo creates two disposable histories.

```sh
git clone --branch v0.1.0 https://github.com/Gonzillaaa/which-session.git
cd which-session
python3 examples/demo.py
```

To install the terminal command and both agent skills for your account, run `python3 install.py` from a checkout you will keep. Run `which-session --version` to confirm the install. In a fresh agent session, use `/sessions:help` in Claude Code or `$sessions help` in Codex.

## What you can recover

- List sessions by their last recorded activity, or search for a phrase in user and assistant messages. Background Codex workers are hidden by default. Use `--all` to include them.
- Inspect a session to see file targets, available tool results, and what to do next. If a call ended without a recorded result, inspect its target before retrying.
- Distinguish restored copies with the same ID using the printed file choices. If the native client cannot tell two copies apart, the CLI explains the ambiguity.

Which Session reads local Claude project transcripts and dated Codex rollouts. Cloud-only conversations and separately archived rollouts fall outside that scope. Terminal searches run locally. When a hosted agent shows an excerpt, it becomes part of that agent conversation.

For a bug report, include the OS, host version, command and a synthetic example. [Report an issue](https://github.com/Gonzillaaa/which-session/issues) · [Quickstart](https://github.com/Gonzillaaa/which-session/tree/v0.1.0#readme)
