#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
command -v python3 >/dev/null || { echo 'Python 3.9+ is required.' >&2; exit 1; }
exec python3 -B "$SCRIPT_DIR/lib/zed_config.py" install "$@"
