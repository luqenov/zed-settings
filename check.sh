#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
# shellcheck source=tests/check-output.sh
source tests/check-output.sh
check_init zed-settings "$@"

check_syntax() {
    for script in export-zed.sh install-zed.sh check.sh tests/check-output.sh; do bash -n "$script"; done
}

check_step 'Required tools' check_dependencies python3 shellcheck
check_step 'Shell syntax' check_syntax
check_step 'Shell script quality' shellcheck -x export-zed.sh install-zed.sh check.sh tests/check-output.sh
check_step 'Configuration files and extension list' python3 -B - <<'PY'
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
check_step 'JSONC, export and recovery behavior' python3 -B -m unittest discover -s tests "$CHECK_TEST_FLAG"
check_finish
