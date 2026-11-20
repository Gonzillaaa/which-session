# Which Session release checklist

Use this checklist for each release. The packaged version, tag and source archive should identify the same build.

## Before tagging

- Check the version in `skills/sessions/scripts/settings.json`, the release notes and the output of `which-session --version`. Check the author, committer and tagger identities on the refs being published.
- Run the hosted test matrix on the intended commit. It covers macOS and Linux, Python 3.9 and current Python, Ruff, the full test suite and a smoke test from the source archive. [Release checks](https://github.com/Gonzillaaa/which-session/actions/workflows/ci.yml)
- Try the README from a clean checkout and isolated home. Run the synthetic demo, install twice, check the version, and uninstall. Confirm that pre-existing links and histories survive.
- Rehearse search, inspect and native resume from a different working directory. Check an interrupted edit, a failed command, ambiguous IDs and a worker hidden in the default list.
- Reproduce the public visual from disposable inputs and check the release files for private paths, IDs, excerpts and email addresses.

## Publishing

- Tag the green commit. Build or download its source archive and follow the quickstart again.
- Publish the release notes and check the release page, README image, issues link and archive without a GitHub login. Install from the downloaded archive and confirm its version.
- When updating a downstream bundle, compare its committed skill tree with `git rev-parse v<VERSION>:skills/sessions` in this project.

## Verification history

Native recovery was rehearsed on macOS with Claude Code 2.1.303 and Codex CLI 0.171.0. Each client reopened a disposable conversation in its original project. The v0.1.0 release candidate passed 52 tests on macOS and in an offline Debian Linux container. The cases include repeated installs, destination conflicts, duplicate transcript IDs, missing indexes, Codex worker filtering, and resuming from a directory with spaces.
