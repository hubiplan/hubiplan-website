#!/usr/bin/env bash
# Zieht die Beschreibung der öffentlichen HUBIplan-Schnittstelle aus einem hubiplan-Klon nach
# tests/data/hubiplan_schnittstelle.json (Adressen und Form der Antworten). Die Tests prüfen
# die nachgebildete Schnittstelle (tests/fake.py) dagegen, siehe tests/schnittstelle.py.
#
#   scripts/schnittstelle.sh [Pfad zum hubiplan-Klon, sonst ../hubiplan]
#   scripts/schnittstelle.sh --bestand    Bestand der Abweichungen neu schreiben
#                                         (tests/data/schnittstelle_bestand.txt; braucht pytest)
set -euo pipefail
cd "$(dirname "$0")/.."
if [ "${1:-}" = "--bestand" ]; then
    LOG=$(mktemp)
    trap 'rm -f "$LOG"' EXIT
    BESTAND=tests/data/schnittstelle_bestand.txt
    KOPF=$(grep '^#' "$BESTAND")
    printf '%s\n' "$KOPF" > "$BESTAND"
    SCHNITTSTELLE_LOG="$LOG" python3 -m pytest -q -p no:cacheprovider > /dev/null || true
    sort -u "$LOG" >> "$BESTAND"
    echo "$BESTAND: $(grep -vc '^#' "$BESTAND") Abweichungen im Bestand"
    exit 0
fi
QUELLE="${1:-../hubiplan}"
python3 - "$QUELLE" <<'PY'
import json
import sys
from pathlib import Path

quelle = Path(sys.argv[1]) / "backend" / "config"
routen = json.loads((quelle / "api_routen.json").read_text(encoding="utf-8"))
form = json.loads((quelle / "webseite_schnittstelle.json").read_text(encoding="utf-8"))
daten = {
    "routen": sorted(r for r in routen if r.startswith("^api/public/site/v1/")),
    "antworten": form["antworten"],
    "ohne_beispiel": form["ohne_beispiel"],
}
ziel = Path("tests/data/hubiplan_schnittstelle.json")
ziel.write_text(json.dumps(daten, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
print(f"{ziel}: {len(daten['routen'])} Adressen, {len(daten['antworten'])} Antworten")
PY
