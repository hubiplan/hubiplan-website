"""Breite Logos (Schriftzüge) im Kopf (hubiplan #527): Die Höhe kommt aus Design und
Kopfhöhe, die Breite folgt dem Seitenverhältnis bis zu einer Obergrenze. Wächtertest auf die
CSS-Regel und ihre Spezifität gegenüber den Design- und Stilregler-Regeln."""

import re
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "seite" / "static" / "seite"
REGEL = "html body .kopf .marke:not(.marke-bild) img"


def test_breite_folgt_dem_seitenverhaeltnis():
    css = (STATIC / "seite.css").read_text()
    treffer = re.search(r"(?m)^" + re.escape(REGEL) + r" \{([^}]*)\}", css)
    assert treffer, "Regel für breite Logos fehlt"
    assert "width: auto" in treffer.group(1)
    assert "max-width:" in treffer.group(1)


def test_designs_und_stilregler_setzen_nur_schwaecher():
    """Keine andere Regel für das Kopflogo ist so spezifisch oder nutzt !important; sonst
    würde sie die Breite wieder auf ein Quadrat festlegen."""
    for datei in STATIC.glob("*.css"):
        for selektor, rumpf in re.findall(r"([^{}]+)\{([^}]*)\}", datei.read_text()):
            selektor = selektor.strip()
            if ".marke" not in selektor or "img" not in selektor or REGEL in selektor:
                continue
            if "marke-bild" in selektor and ":not(" not in selektor:
                continue
            assert "!important" not in rumpf, (datei.name, selektor)
            assert not selektor.startswith("html body"), (datei.name, selektor)
