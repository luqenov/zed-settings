# zed-settings

<div align="center">

[![Shell](https://img.shields.io/badge/Shell-bash-121212?logo=gnu-bash&logoColor=white)](https://www.gnu.org/software/bash/)
[![Zed](https://img.shields.io/badge/Editor-Zed-3b82f6)](https://zed.dev)
[![Platform](https://img.shields.io/badge/Platform-Linux-18181b)](https://www.kernel.org/)
[![License](https://img.shields.io/badge/License-MIT-0891b2)](LICENSE)

</div>

A lightweight backup-and-restore setup for your [Zed editor](https://zed.dev) configuration, keymaps, and installed extensions.

## Overview

This repository keeps the configuration files you usually want to carry between machines:

- `settings.json` — editor settings
- `keymap.json` — keyboard shortcuts
- `extensions.txt` — extension list used for automatic installation
- `tasks.json` — optional task definitions
- `themes/` and `snippets/` — optional custom theme and snippet folders
- `export-zed.sh` — saves your current Zed setup into this repo
- `install-zed.sh` — restores the setup on another machine

## Why this exists

Zed does not provide a clean CLI for installing extensions directly, so the workflow here is:

- export the installed extensions to `extensions.txt`
- strip the auto-install block from your local `settings.json`
- restore the managed configuration on a new machine
- let Zed install the missing extensions automatically on startup

## Backup

Run this from any directory:

```bash
./export-zed.sh
git add .
git commit -m "zed: update settings and extensions"
git push
```

The export script reads from the default Zed paths:

- `~/.config/zed`
- `~/.local/share/zed`

or the equivalents defined by `XDG_CONFIG_HOME` and `XDG_DATA_HOME`.

## Restore on a new machine

1. Install Zed.
2. Clone this repository.
3. Run:

```bash
./install-zed.sh
```

4. Open Zed and let it install the configured extensions on startup.

## How extension restoration works

The key piece is the `auto_install_extensions` block in `settings.json`.

- `extensions.txt` is the source of truth for the extension list.
- `export-zed.sh` removes the `auto_install_extensions` section before saving the repository version.
- `install-zed.sh` regenerates that block from `extensions.txt` and inserts it at the top of `settings.json`.
- If an older version exists, it is backed up as `settings.json.bak`.

This keeps the repository state clean while ensuring the local setup is restored exactly as expected.

## Notes

If your system uses non-default paths, make sure the environment variables are set before running the scripts:

```bash
export XDG_CONFIG_HOME="$HOME/.config"
export XDG_DATA_HOME="$HOME/.local/share"
```

Also, `settings.json` may contain a machine-specific Biome path. If needed, update it manually to match the binary location on your system.

## License

MIT
