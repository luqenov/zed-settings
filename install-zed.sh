#!/usr/bin/env bash
set -e

cd "$(dirname "${BASH_SOURCE[0]}")"

CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/zed"
mkdir -p "$CONFIG_DIR"

strip_block() {
  awk '
    skip { if ($0 ~ /\}/) skip = 0; next }
    /"auto_install_extensions"/ { if ($0 !~ /\}/) skip = 1; next }
    { print }
  ' "$1"
}

if [ -f ./settings.json ]; then
  if [ -f "$CONFIG_DIR/settings.json" ]; then
    cp "$CONFIG_DIR/settings.json" "$CONFIG_DIR/settings.json.bak"
    echo "-> existing settings.json backed up to settings.json.bak"
  fi
  cp ./settings.json "$CONFIG_DIR/settings.json"
  echo "-> settings.json restored"
fi

for file in keymap.json tasks.json; do
  if [ -f "./$file" ]; then
    cp "./$file" "$CONFIG_DIR/$file"
    echo "-> $file restored"
  fi
done

for dir in themes snippets; do
  if [ -d "./$dir" ]; then
    mkdir -p "$CONFIG_DIR/$dir"
    cp -r "./$dir"/* "$CONFIG_DIR/$dir/"
    echo "-> $dir restored"
  fi
done

#    Zed has no CLI to install extensions, but it installs everything listed in
#    the "auto_install_extensions" setting the next time it starts. So we build
#    that block from extensions.txt and put it at the top of settings.json,
#    replacing any older block so the list always matches extensions.txt.
if [ -f ./extensions.txt ]; then
  [ -f "$CONFIG_DIR/settings.json" ] || printf '{\n}\n' > "$CONFIG_DIR/settings.json"

  tmp="$(mktemp)"
  strip_block "$CONFIG_DIR/settings.json" > "$tmp"
  cp "$tmp" "$CONFIG_DIR/settings.json"

  {
    echo '  "auto_install_extensions": {'
    while read -r ext; do
      [ -z "$ext" ] && continue
      echo "    \"$ext\": true,"
    done < ./extensions.txt
    echo '  },'
  } > "$tmp"
  sed -i '0,/^{/r '"$tmp" "$CONFIG_DIR/settings.json"
  rm -f "$tmp"
  echo "-> auto_install_extensions generated from extensions.txt"
fi

echo ""
echo "Done! Open Zed — it will install the extensions on startup."