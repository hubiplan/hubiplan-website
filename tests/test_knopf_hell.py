"""Heller Knopf („Kalender abonnieren“) so hoch wie ein gefüllter daneben (Webseite #118).
Wächtertest auf die CSS-Regeln: der 2-px-Rahmen geht vom Polster ab, und bei Etikett-Knöpfen
bekommt der helle Knopf dieselbe Schrift."""

import re
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "seite" / "static" / "seite"


def _regel(css: str, selektor: str) -> str:
    treffer = re.search(r"(?m)^" + re.escape(selektor) + r" \{([^}]*)\}", css)
    assert treffer, f"Regel {selektor} fehlt"
    return treffer.group(1)


def test_rahmen_geht_vom_polster_ab():
    css = (STATIC / "seite.css").read_text()
    hell = _regel(css, ".knopf.hell")
    assert "border: 2px solid" in hell
    assert "padding: calc(.65rem - 2px) calc(1.1rem - 2px)" in hell
    assert "padding: calc(.35rem - 2px) calc(.8rem - 2px)" in _regel(css, ".knopf.hell.klein-knopf")


def test_etikett_gilt_auch_fuer_hellen_knopf():
    css = (STATIC / "stil.css").read_text()
    hell = _regel(css, 'html[data-st-buttons="label"] .knopf.hell')
    assert "text-transform: uppercase" in hell
    assert "font-size: .85rem" in hell
    assert "padding: calc(.8rem - 2px) calc(1.4rem - 2px)" in hell
    klein = _regel(css, 'html[data-st-buttons="label"] .knopf.hell.klein-knopf')
    assert "font-size: .78rem" in klein
    assert "padding: calc(.45rem - 2px) calc(1rem - 2px)" in klein
