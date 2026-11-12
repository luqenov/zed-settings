# Configuration and machine requirements

The settings in this repository are personal preferences. Installation copies them; it does not silently replace your theme, formatter, shortcuts or AI provider choices with a generic preset.

## Files

| File | Meaning |
| --- | --- |
| `settings.json` | Global editor preferences; JSONC comments/trailing commas are supported |
| `keymap.json` | Binding contexts and actions; an array, including empty/default examples |
| `extensions.txt` | Enabled extension IDs, one per line; no versions are pinned |
| `tasks.json` | Optional task array; review commands before running tasks |
| `themes/` | Optional local theme files |
| `snippets/` | Optional local snippets |

`auto_install_extensions` is generated from the text list while retaining explicitly disabled IDs from `settings.json`. Use `false` there to keep an extension disabled. See [Zed's extension settings](https://zed.dev/docs/reference/all-settings#auto-install-extensions).

## Machine-specific preferences

Review these before installing on another machine:

| Setting | What to check |
| --- | --- |
| `buffer_font_family` | The configured editor font is installed |
| `terminal.font_family` | The configured terminal font is installed |
| `theme` and `icon_theme` | Matching extensions or local themes are available |
| `lsp.biome.binary.path` | The executable exists at that path on this machine |
| `lsp.biome.settings.require_config_file` | Projects contain the required `biome.json`/`biome.jsonc` |
| `agent` and provider settings | Selected models are available and provider authentication is configured locally |
| SSH connections and tasks | Hosts, directories and commands match your machine |

Fonts, provider authentication, language-server binaries and extension versions are not backed up by this repository. Extension downloads, including language-server downloads managed by Zed/extensions, happen outside the transfer scripts. See the [Biome guide](https://zed.dev/docs/languages/biome).

## Local paths

```bash
XDG_CONFIG_HOME="$HOME/.config" XDG_DATA_HOME="$HOME/.local/share" \
  ./install-zed.sh --dry-run
```

Both environment variables must be absolute paths when set. Managed symlink trees and overlapping source/destination roots are refused. Avoid committing API keys, passwords or tokens; review exports before publishing.

[Back to README](../README.md)
