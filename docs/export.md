# Export local Zed configuration

`export-zed.sh` reads your local settings and updates the clone containing the script. Invoke it by its path from any working directory.

## Usage

```bash
./export-zed.sh --dry-run
./export-zed.sh

# Also remove optional managed entries absent from the local configuration.
./export-zed.sh --mirror --dry-run
./export-zed.sh --mirror
```

Requirements: Bash and Python 3.9+. Keep `lib/` next to the scripts. No third-party Python package is required.

## Sources

| Content | Default Linux location |
| --- | --- |
| Settings, keymap, tasks, themes and snippets | `~/.config/zed/` |
| Installed extension directory names | `~/.local/share/zed/extensions/installed/` |

`XDG_CONFIG_HOME` and `XDG_DATA_HOME` override these base locations. Values must be absolute paths. The scripts target Linux's directory layout, not macOS, Windows or sandbox-specific layouts.

## Extension handling

Installed extension directory names become sorted, unique IDs in `extensions.txt`. Exported settings retain explicit `false` entries in `auto_install_extensions`, while enabled entries move to the text list. A disabled extension is excluded from that list even if its directory still exists.

If the installed-extension directory is missing, the current `extensions.txt` is preserved and a message explains why. An existing but empty directory exports an empty list. No extensions are downloaded or installed during export.

## File handling

JSONC files are validated before applying the plan. Unrelated settings and comments are preserved; the managed extension property may be reformatted. IDs containing invalid characters and duplicate JSON keys are rejected.

By default, absent optional files are left in the repository and theme/snippet trees are merged. `--mirror` removes missing optional managed entries and replaces those trees, including hidden files and empty directories. It does not remove repository code, documentation or unrelated files.

Source/destination symlinks inside managed content and overlapping repository/configuration roots are refused. This prevents following configuration links into other locations; configurations managed through symlink trees need a separate export copy.

## Backups and recovery

Changed repository entries are backed up under `.zed-backups/<timestamp>-<unique-id>/`. The folder is ignored by Git. Backups include prior bytes/modes and record entries that did not exist before the operation.

```bash
./export-zed.sh --restore /absolute/path/to/clone/.zed-backups/BACKUP --dry-run
./export-zed.sh --restore /absolute/path/to/clone/.zed-backups/BACKUP
```

Restoration accepts only a backup matching this clone and operation. Review `git diff` after exporting or restoring. Nothing is committed or pushed automatically.

[Back to README](../README.md)
