#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFAULT_IDADIR="/home/xd/ida-pro-9.3"

if [[ $# -eq 0 ]]; then
    echo "Usage: $0 <command> [args...]" >&2
    exit 1
fi

if [[ ! -x "$REPO_DIR/.venv/bin/python" ]]; then
    echo "Missing virtual environment: $REPO_DIR/.venv" >&2
    exit 1
fi

export IDADIR="${IDADIR:-$DEFAULT_IDADIR}"

if [[ ! -f "$IDADIR/libidalib.so" ]]; then
    echo "IDADIR does not contain libidalib.so: $IDADIR" >&2
    exit 1
fi

export PATH="$REPO_DIR/.venv/bin:$PATH"
export LD_LIBRARY_PATH="$IDADIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

exec "$@"
