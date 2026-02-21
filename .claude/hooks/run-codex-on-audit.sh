#!/usr/bin/env bash
set -euo pipefail

INPUT="$(cat)"

# Claude Code sends JSON on stdin; for Write/Edit tools it includes tool_input.file_path
FILE_PATH="$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')"

# Only trigger when Claude writes AUDIT.md
if [[ "$FILE_PATH" != *"AUDIT.md" ]]; then
  exit 0
fi

# Run Codex to fix based on AUDIT.md
codex exec --full-auto --sandbox workspace-write \
"Read AUDIT.md.
Fix all BLOCKER and SHOULD items.
Run tests (best effort).
Commit changes with message: 'fix: address audit'."




