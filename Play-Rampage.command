#!/bin/bash
# Hulk-in-Manhattan fan homage (unofficial, non-commercial). Same as Play-Brute.command, but the Brute wears the
# Paragon: Rampage "Elemental" rock skin (free Fab pack from Epic, Unreal-only licence, not stored in this repo)
# driven by the same 17 clips, retargeted by tools/brute/retarget_rampage.py. Needs Content/ParagonRampage + Content/Brute/Rampage.
HERE="$(cd "$(dirname "$0")" && pwd)"
if [ ! -d "$HERE/unreal/WebHomage/Content/Brute/Rampage" ]; then
  echo "Rampage content missing: add Paragon: Rampage via the editor's Fab panel, then run tools/brute/retarget_rampage.py" >&2; exit 1
fi
exec "$HERE/Play-Brute.command" -WHBruteRampage "$@"
