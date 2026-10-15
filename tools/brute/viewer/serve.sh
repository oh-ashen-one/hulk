#!/bin/bash
# Brute animation review viewer on http://127.0.0.1:8765 (three.js from ~/spiderbench/node_modules, model from ~/hulk-scratch/brute_v2/brute.glb)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PORT="${PORT:-8765}"
SRC="${BRUTE_VIEW_GLB:-$HOME/hulk-scratch/brute_v2/brute.glb}"
[ -e "$HERE/three" ] || ln -s "$HOME/spiderbench/node_modules/three" "$HERE/three"
cp "$SRC" "$HERE/brute.glb"
[ -f "$(dirname "$SRC")/clips.json" ] && cp "$(dirname "$SRC")/clips.json" "$HERE/clips.json"
cd "$HERE" && exec python3 -m http.server "$PORT" --bind 127.0.0.1
