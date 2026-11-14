"""Suchseite: Knopf „Suchen“ so hoch wie das Feld, auf einer Linie, gleiche Ecken (Ralf 14.11.2026).
Wächtertest auf die CSS-Regeln. Alle Daten erfunden."""

import re
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "seite" / "static" / "seite"


def _regel(css: str, selektor: str) -> str:
    treffer = re.search(r"(?m)^" + re.escape(selektor) + r" \{([^}]*)\}", css)
    assert treffer, f"Regel {selektor} fehlt"
    return treffer.group(1)


def test_feld_und_knopf_strecken_sich_auf_eine_hoehe():
    css = (STATIC / "seite.css").read_text()
    assert "align-items: stretch" in _regel(css, ".suche")


def test_knopf_ohne_aussenabstand_und_mit_gleichen_ecken():
    css = (STATIC / "seite.css").read_text()
    knopf = _regel(css, ".suche .knopf")
    feld = _regel(css, ".suche input")
    # .knopf hat sonst oben/unten .25rem Außenabstand, dann sitzt er versetzt
    assert "margin: 0" in knopf
    # Ecken folgen dem Stilregler (eckig/leicht/rund), bei Feld und Knopf gleich
    assert "border-radius: var(--rund)" in knopf
    assert "border-radius: var(--rund)" in feld


def test_fokusrahmen_liegt_innen():
    css = (STATIC / "seite.css").read_text()
    regel = _regel(css, ".suche input:focus-visible, .suche .knopf:focus-visible")
    assert "outline-offset: -3px" in regel


def test_suchseite_nutzt_die_klassen(client, hubiplan):
    hubiplan.info["blocks"] = {**hubiplan.info["blocks"], "search": True}
    html = client.get("/suche/").content.decode()
    assert re.search(r'<form class="suche"[^>]*>', html)
    assert '<button class="knopf" type="submit">' in html
