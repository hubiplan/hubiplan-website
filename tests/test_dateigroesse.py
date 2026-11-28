"""Obergrenze für die Größe der Programmdateien.

Große Dateien mischen Aufbereitung, Steuerung und Darstellung und führen zu Konflikten, wenn
mehrere Arbeiten sie gleichzeitig anfassen. Neue Dateien bleiben deshalb unter der Grenze;
wer sie erreicht, teilt nach Thema (wie ``seite/views/``).
"""

from pathlib import Path

GRENZE = 800
WURZEL = Path(__file__).resolve().parents[1]
# Dateien aus dem Bestand über der Grenze: Pfad → Zeilen. Kleiner werden ist erwünscht
# (dann hier senken oder streichen), größer werden nicht.
BESTAND: dict[str, int] = {}


def _zeilen(pfad: Path) -> int:
    with pfad.open(encoding="utf-8") as datei:
        return sum(1 for _ in datei)


def test_keine_neue_grosse_datei():
    zu_gross = {}
    for pfad in sorted((WURZEL / "seite").rglob("*.py")):
        name = pfad.relative_to(WURZEL).as_posix()
        zeilen = _zeilen(pfad)
        if zeilen > BESTAND.get(name, GRENZE):
            zu_gross[name] = zeilen
    assert not zu_gross, f"Über {GRENZE} Zeilen, bitte nach Thema teilen: {zu_gross}"


def test_bestand_ist_aktuell():
    veraltet = [
        name for name in BESTAND if not (WURZEL / name).exists() or _zeilen(WURZEL / name) <= GRENZE
    ]
    assert not veraltet, f"Nicht mehr über der Grenze, aus BESTAND streichen: {veraltet}"
