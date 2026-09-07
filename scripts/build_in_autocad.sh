#!/bin/bash
# ---------------------------------------------------------------------------
# build_in_autocad.sh -- build the front LED light-bar holder inside AutoCAD,
# headlessly, and save the result as a DWG.
#
#   ./build_in_autocad.sh [-o ../cad/front-led-mount-3D.dwg] [-t <template>]
#
# AutoCAD for Mac ships AcCoreConsole, the same core engine the GUI uses, as a
# command-line helper inside the application bundle.  It loads AutoLISP and
# runs the real BOX / CYLINDER / SUBTRACT commands, so the solids in the output
# file are genuine ACIS bodies made by AutoCAD -- not an approximation written
# by a third-party library.  No GUI, no screen-recording permission needed.
#
# The console has no ActiveX, so front_led_mount.lsp guards vl-load-com and
# falls back to MASSPROP for volumes.  SECURELOAD is set to 0 for the run so
# the script loads from this folder without a Trusted Locations entry.
# ---------------------------------------------------------------------------
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ACAD="/Applications/Autodesk/AutoCAD 2026/AutoCAD 2026.app"
ACC="$ACAD/Contents/Helpers/AcCoreConsole.app/Contents/MacOS/AcCoreConsole"
BLANK="$ACAD/Contents/Resources/UserDataCache/en-us/Template/acadiso3D.dwt"
SHEET="$HERE/../cad/front-led-mount-sheet-A3.dxf"
TEMPLATE=""
OUT="$HERE/../cad/front-led-mount-3D.dwg"
LOG=""

while getopts "o:t:l:h" opt; do
  case $opt in
    o) OUT="$OPTARG" ;;
    t) TEMPLATE="$OPTARG" ;;
    l) LOG="$OPTARG" ;;
    h) sed -n '2,20p' "$0"; exit 0 ;;
    *) exit 2 ;;
  esac
done

[ -x "$ACC" ] || { echo "AcCoreConsole not found at: $ACC" >&2; exit 1; }

# The drawing is seeded from the A3 sheet rather than from a blank template.
# That sheet DXF carries the manufacturing drawing on a paper space layout
# with a real A3 page set up on it, and an empty model space -- so building
# the assembly into model space leaves one file holding both.  Regenerate it
# with:  python3 make_drawing.py --layout "A3 DRAWING" -o ../cad/front-led-mount-sheet-A3.dxf
if [ -z "$TEMPLATE" ]; then
  if [ -f "$SHEET" ]; then TEMPLATE="$SHEET"; else TEMPLATE="$BLANK"; fi
fi
[ -f "$TEMPLATE" ] || { echo "seed drawing not found: $TEMPLATE" >&2; exit 1; }

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
# keep the seed's own extension - the console reads DXF and DWG, but it
# reads them by content, and a DXF named .dwg will not open
SEED="$WORK/seed.${TEMPLATE##*.}"
cp "$TEMPLATE" "$SEED"
mkdir -p "$(dirname "$OUT")"
OUT="$(cd "$(dirname "$OUT")" && pwd)/$(basename "$OUT")"
[ -n "$LOG" ] || LOG="$WORK/build.log"

cat > "$WORK/build.scr" <<SCR
(setvar "FILEDIA" 0)
(setvar "CMDECHO" 0)
(setvar "SECURELOAD" 0)
(setvar "INSUNITS" 4)
(princ "\n>>> FLM-BUILD loading builder\n")
(load "$HERE/front_led_mount.lsp")
(princ "\n>>> FLM-BUILD running FLM\n")
(C:FLM)
(C:FLMVIEWS)
(princ "\n>>> FLM-BUILD mass properties\n")
(C:FLMINFO)
(princ "\n>>> FLM-BUILD saving\n")
(command "_.SAVEAS" "2018" "$WORK/out.dwg")
(princ "\n>>> FLM-BUILD done\n")
SCR

echo "AutoCAD engine : AcCoreConsole $(/usr/libexec/PlistBuddy -c 'Print CFBundleVersion' "$ACAD/Contents/Helpers/AcCoreConsole.app/Contents/Info.plist" 2>/dev/null)"
echo "seed drawing   : $(basename "$TEMPLATE")"
echo "layouts        : $([ "$TEMPLATE" = "$BLANK" ] && echo "none (blank template)" || echo "A3 DRAWING")"
echo "output         : $OUT"
echo

# SAVEAS is pointed at a path that cannot already exist: writing over an
# existing drawing raises a "Do you want to replace it?" prompt that the
# script has no answer for, and the console then hangs forever.
"$ACC" /i "$SEED" /s "$WORK/build.scr" </dev/null > "$LOG" 2>&1 || true
if [ -f "$WORK/out.dwg" ]; then mv -f "$WORK/out.dwg" "$OUT"; fi

# surface the builder's own output and any AutoLISP error
sed -n '/FLM-BUILD loading/,$p' "$LOG" \
  | grep -vE '^Command: *$|^Command: \(|^\*Cancel\*|_\.quit' \
  | sed '/^$/d'

if grep -q "; error" "$LOG"; then
  echo
  echo "!! AutoLISP errors reported:" >&2
  grep -n "; error" "$LOG" | grep -v "acad2026.LSP" >&2 || true
fi

if [ -f "$OUT" ]; then
  echo
  echo "OK  $(basename "$OUT")  $(du -h "$OUT" | cut -f1)"
else
  echo "FAILED - no output written; full log: $LOG" >&2
  exit 1
fi
