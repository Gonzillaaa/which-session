# Finding a session to resume

The approved workflow groups repeated executions of a known job in a project, shows where a selected session stopped, and lets a terminal user filter and inspect sessions with the keyboard. The transcript files are the source of truth. Selecting a session prints its inspection and leaves the choice to run the resume command to the user.

Group the interactive terminal list by configured opening invocations, exact project directory and agent. Order entries by their latest member and apply the display limit after grouping. Keep individual transcripts addressable, including restored copies. Offer a flat list and preserve individual search hits, machine output and agent Markdown.

The picker uses the existing discovery, filters and activity ordering. Typing filters the eligible sessions by title or project. Arrows move selection, groups expand into individual runs, Enter inspects the selected file, and Escape cancels. Show the last user request, last recorded tool call and outcome, full ID and applicable resume guidance. Read detailed evidence only for the selected file. Reuse the inspection rules for duplicate IDs and missing directories.

Python 3.9 on macOS and Linux, standard library only. Verify with synthetic native histories, a real pseudo-terminal, empty results, ambiguous IDs and an unavailable transcript. Update the README, skill guidance and release checklist. Run the full suite and Ruff.
