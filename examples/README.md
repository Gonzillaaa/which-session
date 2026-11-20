# Try a recovery with disposable data

Run this from the checkout or an extracted release archive. It requires Python 3.9 or later.

```sh
python3 examples/demo.py
```

The demo generates two conversations under a temporary directory and points Which Session at those histories. It searches both hosts for “retry policy,” then inspects each result.

- **Backoff notes** has a Claude Code write to `retry-notes.md` with no recorded result. Inspect tells you to check that file before retrying.
- **Backoff tests** has a Codex command that exited with code 1. Inspect directs you to review the error.

The demo labels the temporary directory `<demo>` in its output. It prints the native resume commands for illustration. Both IDs are synthetic. Real recovery uses the command printed for a real session.

## Examine the output yourself

This version keeps the fixture in a new directory. The two environment variables apply only to the enclosed commands.

```sh
demo_dir="$(mktemp -d)/which-session"
python3 examples/demo.py --keep "$demo_dir"
(
  export CLAUDE_CONFIG_DIR="$demo_dir/claude" CODEX_HOME="$demo_dir/codex"
  ./which-session list --all
  ./which-session search "retry policy" --all --json
  ./which-session inspect 11111111-1111-4111-8111-111111111111
)
```

Use `--all` for this example because the histories refer to a project in a temporary directory. The default list hides temporary projects.

## What you share

The list table shows titles, host, folder name, activity time and full session IDs. A phrase search adds an excerpt and its speaker. Inspect shows recent messages, the original directory, and file paths associated with supported tools. JSON rows additionally include the absolute working directory, transcript path and last user message. Review those fields before sharing output from a real history. Excerpts you show in a hosted agent become part of that conversation.
