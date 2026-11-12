# Install and restore Zed settings

`install-zed.sh` installs the configuration from its own clone. It does not install Zed itself.

## Usage

Close Zed, then run:

```bash
./install-zed.sh --dry-run
./install-zed.sh
```

Bash and Python 3.9+ are required. Run as your normal user. The default destination is `~/.config/zed`, or `$XDG_CONFIG_HOME/zed` when set to an absolute path.

All inputs are validated and replacement content is staged before managed configuration changes. Settings require a JSONC object; keymaps/tasks require arrays. Theme and snippet JSON files are also validated. This checks syntax and expected root types, not every setting against a specific Zed release.

## Extension restoration

`extensions.txt` supplies enabled IDs. Blank lines are ignored, duplicates are removed, and the last line works with or without a final newline. Explicit `false` entries in the source settings take precedence over the text list.

The resulting `auto_install_extensions` map is written as a single root property. Zed performs the actual extension work when opened. Other installed extensions are not removed simply because they are absent from the text list. If `extensions.txt` is absent, the source settings' extension property is copied unchanged.

## Copy versus mirror

The default copies present files, merges theme/snippet trees and preserves destination-only content in those trees. Missing optional source entries leave the corresponding destination entries intact.

```bash
# Review an exact mirror of the managed configuration entries.
./install-zed.sh --mirror --dry-run
./install-zed.sh --mirror
```

`--mirror` additionally removes absent optional keymaps/tasks/trees and replaces theme/snippet trees exactly. Only the documented managed entries are affected. A missing source `settings.json` is an error in every mode.

## Recovery

Every changed run prints its backup path under `$XDG_CONFIG_HOME/zed-settings-backups/`, defaulting to `~/.config/zed-settings-backups/`. Backups are unique and their top-level directories are private to your account.

```bash
./install-zed.sh --restore /absolute/path/to/backup --dry-run
./install-zed.sh --restore /absolute/path/to/backup
```

Restoring recovers previous files/directories and removes entries created by the original operation. It first backs up the current affected entries, allowing another restore to undo it. Backups must match the operation and destination, so moving a clone/configuration root may require manual recovery.

Replacement files use atomic rename. Nonempty directories require moving the old tree aside before installing the staged replacement. Ordinary transfer errors trigger rollback; if recovery cannot complete, the persistent backup path is available. Changes across several files are not one filesystem transaction. An abrupt shutdown or `SIGKILL` can interrupt recovery; use the persistent backup afterward and inspect any `.zed-stage-*` directory before removing it.

Do not edit the destination concurrently during a transfer. The script checks for changes after preparing the plan, but cannot lock out Zed or other applications. Backups are retained until you remove them manually.

[Back to README](../README.md)
