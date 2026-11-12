# Checks and tests

Run from any directory using the check script's path:

```bash
./check.sh
```

Requirements: Bash, Python 3.9+ and ShellCheck. No pip packages, editor installation, provider credentials or network are required for the checks.

| Check | Coverage |
| --- | --- |
| Shell syntax and ShellCheck | Both transfer entry points and the check script |
| Repository validation | Settings, keymaps, optional tasks/assets and extension IDs |
| `test_jsonc.py` | Comments, strings, trailing commas, root-property edits and malformed input |
| `test_transfer.py` | Export/install round trips, XDG paths with spaces, hidden files, mirrors, backups, restores and injected write failures |

Integration tests create isolated temporary clones and XDG directories. They do not alter your actual Zed settings, launch Zed, install extensions or call provider APIs. They validate file behavior rather than compatibility with every Zed release or extension.

## Output

Normal runs show one line per check and a final test count. A small spinner appears only in interactive terminals; CI and redirected logs use static text. Failed checks show their diagnostics and keep the original exit status.

```bash
./check.sh --verbose
./check.sh --plain
```

`--verbose` also shows successful command output and individual test results. `--plain` disables animation and colors. `NO_COLOR` disables colors, and `CI` disables terminal animation automatically.

## CI

The Woodpecker workflow runs the same check script in a single Debian container on main-branch pushes, pull requests and manual runs. Dependency installation needs network; the test suite does not.

Codeberg's hosted service requires onboarding and enabling this repository at [ci.codeberg.org](https://ci.codeberg.org/repos/add). Adding the workflow does not activate hosting. See [Codeberg's CI documentation](https://docs.codeberg.org/ci/).

[Back to README](../README.md)
