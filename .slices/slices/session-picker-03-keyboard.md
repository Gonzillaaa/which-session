# Terminal selection

Implement a standard-library keyboard picker accepting grouped entries and a preview callback. Filter by title and project, navigate with arrows, expand groups, inspect a specific member with Enter, and cancel with Escape. Restore terminal modes on every exit.

Own the picker module and keyboard tests. Use real PTY input for navigation and cancellation. Exercise empty matches, resizing or a small window, and safe display of transcript text. Validate with pytest and Ruff. The integration slice calls the picker from the CLI. Stop if the UI would need an external executable or launch a selected agent. Required by slice 04.
