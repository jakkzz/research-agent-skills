#!/usr/bin/env bash
# Optional Bash wrapper. Cross-platform entry: python3 scripts/install.py
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: Python 3 is required to install research-agent-skills." >&2
    exit 1
fi

python3 "${SCRIPT_DIR}/scripts/install.py" "$@"
