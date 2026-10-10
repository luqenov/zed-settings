#!/usr/bin/env bash
set -e

cd "$(dirname "${BASH_SOURCE[0]}")"

CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/zed"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/zed"

strip_block() {
  awk '
    skip { if ($0 ~ /\}/) skip = 0; next }
    /"auto_install_extensions"/ { if ($0 !~ /\}/) skip = 1; next }
    { print }
  ' "$1"
}

if [ -d "$DATA_DIR/extensions/installed" ]; then
  ls -1 "$DATA_DIR/extensions/installed" > ./extensions.txt
  echo "-> ./extensions.txt ($(wc -l < ./extensions.txt) extensions)"
else
  echo "!! Could not find $DATA_DIR/extensions/installed"
fi

if [ -f "$CONFIG_DIR/settings.json" ]; then
  strip_block "$CONFIG_DIR/settings.json" > ./settings.json
  echo "-> ./settings.json"
else
  echo "!! Could not find $CONFIG_DIR/settings.json"
fi

# (only copied if you've customized it)
if [ -f "$CONFIG_DIR/keymap.json" ]; then
  cp "$CONFIG_DIR/keymap.json" ./keymap.json
  echo "-> ./keymap.json"
fi

# (if you have any)
if [ -f "$CONFIG_DIR/tasks.json" ]; then
  cp "$CONFIG_DIR/tasks.json" ./tasks.json
  echo "-> ./tasks.json"
fi

# (if you have any)
for dir in themes snippets; do
  if [ -d "$CONFIG_DIR/$dir" ] && [ "$(ls -A "$CONFIG_DIR/$dir" 2>/dev/null)" ]; then
    mkdir -p "./$dir"
    cp -r "$CONFIG_DIR/$dir"/* "./$dir/"
    echo "-> ./$dir/"
  fi
done

echo ""
echo "Done. Review the files before committing."