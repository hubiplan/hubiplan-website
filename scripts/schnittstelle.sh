#!/usr/bin/env bash
# Zieht die Beschreibung der öffentlichen HUBIplan-Schnittstelle aus einem hubiplan-Klon:
# tests/data/hubiplan_schnittstelle.json (Adressen und Form der Antworten) und
# tests/data/hubiplan_antworten.json (echte Antworten der Beispielvereine). Die Tests prüfen
# die nachgebildete Schnittstelle (tests/fake.py) gegen die Form (tests/schnittstelle.py) und
# bauen jede Seite aus den echten Antworten (tests/test_echte_antworten.py).
#
#   scripts/schnittstelle.sh [Pfad zum hubiplan-Klon, sonst ../hubiplan]
set -euo pipefail
cd "$(dirname "$0")/.."
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
echt = Path("tests/data/hubiplan_antworten.json")
echt.write_text((quelle / "webseite_antworten.json").read_text(encoding="utf-8"), encoding="utf-8")
aufzeichnung = json.loads(echt.read_text(encoding="utf-8"))
print(f"{echt}: {len(aufzeichnung['antworten'])} echte Antworten, Stand {aufzeichnung['stand']}")
PY
