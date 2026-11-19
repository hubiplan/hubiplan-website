"""Dokumentvorschau auf getönter Fläche statt doppeltem weißem Rahmen (Webseite #167).
Wächtertest auf die CSS-Regeln: das Blatt liegt ohne eigene Linie auf einer hellen Fläche in der
Datumsfarbe, und bei Karten mit Farbstreifen trägt die Kachel oben den Streifen wie die Kacheln."""

import re
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "seite" / "static" / "seite"


def _regel(css: str, selektor: str) -> str:
    treffer = re.search(r"(?m)^" + re.escape(selektor) + r" \{([^}]*)\}", css)
    assert treffer, f"Regel {selektor} fehlt"
    return treffer.group(1)


def test_vorschau_liegt_auf_flaeche():
    css = (STATIC / "seite.css").read_text()
    kachel = _regel(css, ".dokumente a.mit-vorschau")
    assert "--dok-grund: color-mix(in srgb, var(--farbe-datum) 16%, var(--flaeche))" in kachel
    assert "padding: 0 0 .8rem" in kachel
    blatt = _regel(css, ".mit-vorschau .dok-vorschau")
    assert "background: var(--dok-grund)" in blatt
    assert "border: 0" in blatt
    assert "padding: 1.2rem" in blatt


def test_streifen_bei_karten_mit_akzent():
    css = (STATIC / "stil.css").read_text()
    regel = _regel(css, 'html[data-st-cards="accent"] ul.dokumente a.mit-vorschau')
    assert "border-top: 3px solid var(--primaer)" in regel
