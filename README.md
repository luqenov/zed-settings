This repository showcases my [Zed editor](https://zed.dev) configs and extensions.

> [!TIP]
> Also check: [Configuring Zed](https://zed.dev/docs/configuring-zed#user-settings-file).

- `extensions.txt`: List of installed extensions.
- `settings.json`: Core configs.
- `keymap.json`: Keymap.
- `tasks.json`, `themes/`, `snippets/`: Only present if you have custom ones.
- `export-zed.sh`: Dumps your current Zed setup into this repo.
- `install-zed.sh`: Restores the setup from this repo onto a machine.

Both scripts use the default Zed paths (`~/.config/zed` and
`~/.local/share/zed`, or your `XDG_CONFIG_HOME` / `XDG_DATA_HOME` if set).

## Backing up (after changing settings/extensions)

Run from the root of this repo:

```bash
./export-zed.sh
git add .
git commit -m "zed: update settings/extensions"
git push
```

## Restoring on a new machine

1. Install Zed, then close it.
2. Clone this repo and run:
   ```bash
   ./install-zed.sh
   ```
3. Open Zed. The extensions are installed automatically on startup.

## How extensions are restored

Zed doesn't have a command-line way to install extensions. Instead, it installs
everything listed under the `auto_install_extensions` setting when it starts.
`install-zed.sh` builds that block from `extensions.txt` and adds it to the top
of your `settings.json` (your previous `settings.json` is saved as
`settings.json.bak`). If the setting already exists, the script leaves it alone.

## Note: machine-specific paths

`settings.json` points the Biome language server to `/usr/bin/biome`. If Biome
lives somewhere else on your machine, update `lsp.biome.binary.path`.