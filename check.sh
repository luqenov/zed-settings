#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
for dependency in python3 shellcheck; do
    command -v "$dependency" >/dev/null || { printf 'Missing dependency: %s\n' "$dependency" >&2; exit 1; }
done
for script in export-zed.sh install-zed.sh check.sh; do bash -n "$script"; done
shellcheck export-zed.sh install-zed.sh check.sh
python3 -B - <<'PY'
from pathlib import Path
import sys
if sys.version_info < (3, 9):
    raise SystemExit('Python 3.9+ is required.')
sys.path.insert(0, 'lib')
import zed_config
for name in zed_config.CONFIG_FILES:
    entry = zed_config.read_entry(Path(name))
    if name == 'settings.json' and entry is None:
        raise SystemExit('settings.json is required.')
    zed_config.validate_entry(name, entry)
extensions = zed_config.read_entry(Path('extensions.txt'))
if extensions is not None:
    zed_config.extension_ids(extensions)
print('Repository configuration is valid JSONC.')
PY
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -v
