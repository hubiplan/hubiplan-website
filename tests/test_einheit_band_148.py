"""Webseite #148: Das Band auf den Seiten der Einheiten lässt sich absetzen (unit_title), damit
es nicht wie ein zweiter Seitenkopf wirkt. Wächtertest auf Katalog und CSS-Regeln."""

import re
from pathlib import Path

from seite import stil

STATIC = Path(__file__).resolve().parents[1] / "seite" / "static" / "seite"


def _regeln(stufe: str) -> list[str]:
    css = (STATIC / "stil.css").read_text()
    return [
        rumpf
        for selektor, rumpf in re.findall(r"([^{}]+)\{([^}]*)\}", css)
        if f'[data-st-unit-title="{stufe}"]' in selektor
    ]


def test_regler_im_katalog():
    assert stil.CATALOG["unit_title"] == ("primary", "box", "light", "plain")
    assert stil.clean({"unit_title": "light"}, "classic") == {"unit_title": "light"}
    assert stil.clean({"unit_title": "bunt"}, "classic") == {}


def test_stufen_setzen_eigene_farben():
    assert any("var(--farbe-datum)" in r and "var(--auf-datum)" in r for r in _regeln("box"))
    hell = " ".join(_regeln("light"))
    assert "var(--abschnitt-hell)" in hell and "1px solid var(--linie)" in hell
    schlicht = " ".join(_regeln("plain"))
    assert "var(--grund)" in schlicht and "3px solid var(--primaer)" in schlicht
    # Name in der abgedunkelten Vereinsfarbe, Zeile darunter leise
    assert "color: var(--link)" in hell and "color: var(--link)" in schlicht
    assert "var(--text-leise)" in hell


def test_nur_seiten_der_einheiten_und_nur_als_band():
    css = (STATIC / "stil.css").read_text()
    for selektor in re.findall(r"([^{}]+)\{", css):
        if "data-st-unit-title" not in selektor:
            continue
        assert ".einheit-kopf" in selektor, selektor
        assert '[data-st-page-title="band"]' in selektor, selektor
        assert "> :is(h1" not in selektor and ".textseite" not in selektor, selektor
