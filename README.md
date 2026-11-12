# zed-settings

<div align="center">

[![Shell](https://img.shields.io/badge/Shell-Bash-121212?logo=gnubash&logoColor=white)](https://www.gnu.org/software/bash/)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Zed](https://img.shields.io/badge/Editor-Zed-3b82f6)](https://zed.dev)
![Platform](https://img.shields.io/badge/Platform-Linux-18181b)

**Personal Zed settings, with previews and recoverable backups.**

[Export](docs/export.md) · [Install and restore](docs/install.md) · [Configuration](docs/configuration.md) · [Checks](tests/README.md)

</div>

Keep editor settings, keymaps and extensions together without rewriting configuration by line number. The scripts understand JSONC comments and trailing commas, validate inputs before changing configuration files, and preserve unrelated settings/comments.

## Quick start

Requires Bash and Python 3.9+. No pip packages, sudo or Zed CLI are needed by the transfer scripts.

```bash
git clone https://codeberg.org/luqenov/zed-settings.git
cd zed-settings

# Inspect the changes before applying them.
./install-zed.sh --dry-run
./install-zed.sh
```

Close Zed before applying configuration changes. Then reopen it to apply settings and install enabled extensions. The scripts do not launch the editor, install fonts or authenticate AI providers.

## Export your setup

```bash
./export-zed.sh --dry-run
./export-zed.sh
git diff
```

Review the diff before committing, especially provider configuration, task commands and private machine details. Exporting does not commit or push anything.

## Copy or mirror

| Mode | Missing optional source entries | Themes and snippets |
| --- | --- | --- |
| Default | Keep destination entries | Merge; keep destination-only files |
| `--mirror` | Remove managed destination entries absent from the source | Replace the managed trees exactly |

Preview either mode with `--dry-run`. Neither mode deletes unrelated files in the repository or Zed configuration directory. A source `settings.json` is always required. See the [export](docs/export.md) and [install](docs/install.md) guides for exact behavior.

## Backups and recovery

Each operation that changes files creates a unique, private backup of the affected destination entries, including which entries did not previously exist. An unchanged run creates no backup. Previous backups are never reused.

- Export backups: `.zed-backups/` inside this clone, ignored by Git.
- Installation backups: `zed-settings-backups/` alongside the Zed configuration directory.

```bash
# Use the exact backup path printed by the original operation.
./install-zed.sh --restore /absolute/path/to/backup --dry-run
./install-zed.sh --restore /absolute/path/to/backup
```

Use `export-zed.sh --restore ...` for export backups. Restoration creates its own backup, so it can also be undone. Keep backups private: they can contain local credentials or task commands. See [recovery details](docs/install.md#recovery).

## Local checks

```bash
./check.sh
```

Checks require ShellCheck in addition to Bash/Python. Tests use temporary repositories and XDG directories; they do not alter your editor configuration or call external APIs. [Test and CI guide](tests/README.md).
