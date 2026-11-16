"""Webseite #143 (Ralf 16.11.2026): Ehrungen als eigene Karte je Person; das Etikett
nennt den eigenen Titel des Trägers (hubiplan #518) oder den Namen der Ehrung.
Alle Daten erfunden."""

from pathlib import Path

from django.core.cache import cache

from seite import stil

from . import fake
from .test_seiten import _gruppiert

STATIC = Path(__file__).resolve().parents[1] / "seite" / "static" / "seite"

EHRUNG = {
    "title": "Ehrenmitglied",
    "heading": "Ehrenmitglieder",
    "holders": [
        {"name": "Erika Beispiel", "photo_url": None, "title": "Ehrenhauptmann"},
        {"name": "Otto Beispiel", "photo_url": None},
    ],
}


def hole(client, pfad: str) -> str:
    cache.clear()
    return client.get(pfad).content.decode()


def test_regler_im_katalog():
    assert stil.CATALOG["honorary_layout"] == ("list", "cards")


def test_karten_mit_titel_als_etikett(client, hubiplan, monkeypatch):
    monkeypatch.setitem(fake.BOARD, "honorary", [EHRUNG])
    _gruppiert(hubiplan)
    hubiplan.info["style"] = {"honorary_layout": "cards"}
    html = hole(client, "/ehrungen/")
    assert "<h1>Ehrenmitglieder</h1>" in html
    assert '<ul class="ehrungen-karten">' in html
    assert "<small>Ehrenhauptmann</small><strong>Erika Beispiel</strong>" in html
    assert "<small>Ehrenmitglied</small><strong>Otto Beispiel</strong>" in html
    # Kein Platzhalter ohne Foto, keine Zwischenüberschrift
    assert 'class="ohne-foto"' not in html
    assert "<h2>Ehrenmitglied" not in html


def test_mehrere_ehrungen_ein_raster(client, hubiplan, monkeypatch):
    major = {"title": "Ehrenmajor", "holders": [{"name": "Max Major", "photo_url": None}]}
    monkeypatch.setitem(fake.BOARD, "honorary", [EHRUNG, major])
    hubiplan.info["style"] = {"honorary_layout": "cards"}
    html = hole(client, "/vorstand/")
    assert "<h2>Ehrungen</h2>" in html
    assert html.count('<ul class="ehrungen-karten">') == 1
    assert "<h3>Ehrenmajor</h3>" not in html
    # Reihenfolge: nach der Reihenfolge der Ehrungen, darin wie geliefert
    assert html.index("Erika Beispiel") < html.index("Otto Beispiel") < html.index("Max Major")
    assert "<small>Ehrenmajor</small><strong>Max Major</strong>" in html


def test_ohne_regler_wie_bisher(client, hubiplan, monkeypatch):
    monkeypatch.setitem(fake.BOARD, "honorary", [EHRUNG])
    html = hole(client, "/vorstand/")
    assert "ehrungen-karten" not in html
    assert '<section class="karte personenkarte ehrung">' in html


def test_karten_regeln():
    css = (STATIC / "stil.css").read_text()
    assert ".ehrungen-karten { list-style: none;" in css
    assert "border-top: 3px solid var(--st-kasten)" in css
    assert "letter-spacing: .18em; text-transform: uppercase; color: var(--st-kasten)" in css
    assert ".ehrungen-karten { grid-template-columns: minmax(0, 1fr); gap: 14px; }" in css
