#!/bin/bash
# PostToolUse hook: auto-lint Python files after Edit/Write
FILE=$(jq -r '.tool_input.file_path')
[[ "$FILE" == *.py ]] || exit 0
cd "$CLAUDE_PROJECT_DIR" || exit 0
uv run ruff check --fix "$FILE" 2>&1
uv run ruff format "$FILE" 2>&1
exit 0
