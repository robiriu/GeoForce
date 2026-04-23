#!/usr/bin/env bash
# Auto-run pytest for files under solver/ or surrogate/ or tools/ when edited.
# Silent no-op for other files.

set -euo pipefail

FILE_PATH="${1:-}"

if [[ -z "$FILE_PATH" ]]; then
  exit 0
fi

# Only trigger for code under these roots
case "$FILE_PATH" in
  *solver/*|*surrogate/*|*tools/*|*agent/*)
    ;;
  *)
    exit 0
    ;;
esac

# Only run if we're in the project root and tests/ exists
if [[ ! -d tests ]]; then
  exit 0
fi

# Run pytest quickly, quietly; don't block on failure (log only)
python -m pytest tests/ -x --tb=short -q 2>&1 | tail -20 || true
