# Which Session v0.1.0-rc.2

Which Session finds local Claude Code and Codex conversations, searches for words you remember and prints the command to reopen a session in its original directory.

## Try the candidate

In a checkout or extracted source archive on macOS or Linux, run:

```sh
python3 install.py
which-session list --limit 5
```

The installer uses links to the checkout. Pulling a new revision there updates the installed CLI and agent skill. Keep the checkout in place and start a fresh agent chat to pick up changed skill instructions. For a disposable test of an interrupted Claude edit and a failed Codex command, run `python3 examples/demo.py`. [Quickstart](README.md) · [Demo](examples/README.md)

## What to test

- Search for a phrase that appears inside a conversation. Inspect its ID, look at the recorded tool outcome and copy the resume command into your terminal.
- The default list and search hide Codex worker sessions even when they copy their parent’s opening prompt and metadata. Use `--all` to include labeled workers. Independent sessions with the same topic stay visible.
- Inspect a failed Codex command. A structured nonzero exit code directs you to the recorded error. A tool output without a reliable status leaves the outcome unknown.
- If two restored transcripts share an ID, use one of the printed file choices. You can read either copy. The native client selects by ID, so the CLI withholds a resume command when that ID maps to multiple files for that host.
- Sessions remain discoverable if the optional Codex title index is missing or unreadable. An unreadable index produces a warning on stderr.

## Compatibility and known limitations

Python 3.9 or later. Native resume was rehearsed on macOS with Claude Code 2.1.303 and Codex CLI 0.171.0 using disposable conversations and a local test model. Lookup uses locally stored Claude project transcripts and dated Codex rollouts. Archived or cloud-only histories outside those directories are outside this version’s scope. A session can be open without a visible process that names its ID.

For feedback, give the maintainer the candidate revision, OS, host version, exact command and what you expected. A synthetic example is enough to demonstrate most problems. The [demo guide](examples/README.md) lists the private fields that may appear in real output.
