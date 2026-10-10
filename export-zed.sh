#!/usr/bin/env bash
set -e

# Run this script from inside your dotfiles repo

CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/zed"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/zed"

# Zed keeps each installed extension in its own folder named after its ID.
if [ -d "$DATA_DIR/extensions/installed" ]; then
  ls -1 "$DATA_DIR/extensions/installed" > ./extensions.txt
  echo "-> ./extensions.txt ($(wc -l < ./extensions.txt) extensions)"
else
  echo "!! Could not find $DATA_DIR/extensions/installed"
fi

if [ -f "$CONFIG_DIR/settings.json" ]; then
  cp "$CONFIG_DIR/settings.json" ./settings.json
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