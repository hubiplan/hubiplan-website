"""Standarddesigns der Webseite (Auswahl in HUBIplan, Ralf 2026-10-31; erfundene Daten)."""

import pytest
from django.contrib.staticfiles import finders

from seite.site import DESIGNS

ROLLEN = {
    "header": {"color": "#1f4e2c", "on_color": "#ffffff"},
    "nav": {"color": "#c9a227", "on_color": "#1d2421"},
    "line": {"color": "#8b1e2d", "on_color": "#ffffff"},
    "footer": {"color": "#1d2421", "on_color": "#ffffff"},
    "band": {"color": "#1f4e2c", "on_color": "#ffffff"},
    "band2": {"color": "#8b1e2d", "on_color": "#ffffff"},
    "date": {"color": "#8b1e2d", "on_color": "#ffffff"},
}


def text(response) -> str:
    return response.content.decode()


def waehle(hubiplan, design, **over):
    hubiplan.info["design"] = design
    hubiplan.info["designs"] = {k: dict(ROLLEN) for k in DESIGNS}
    hubiplan.info.update(over)


@pytest.mark.parametrize("design", list(DESIGNS))
def test_jedes_design_zeigt_alle_seiten(client, hubiplan, design):
    waehle(hubiplan, design)
    for path in ("/", "/vorstand/", "/termine/", "/kontakt/", "/impressum/"):
        r = client.get(path)
        assert r.status_code == 200, (design, path)
        html = text(r)
        assert f'class="design-{design}"' in html
        # Kopf mit Menü, Sprunglink und Fuß in jedem Design
        assert 'href="#inhalt"' in html and 'aria-label="Hauptmenü"' in html
        assert "Impressum</a>" in html
        # Quellcode-Link (AGPL § 13) auch in Designs mit eigenem Fuß (Lizenzaudit 10.11., L01)
        assert 'href="https://github.com/hubiplan/hubiplan-website' in html
        assert f"seite/design-{design}.css" in html
    assert finders.find(f"seite/design-{design}.css")


def test_farben_je_rolle(client, hubiplan):
    waehle(hubiplan, "festive")
    html = text(client.get("/"))
    assert "--farbe-kopf:#1f4e2c;--auf-kopf:#ffffff" in html
    assert "--farbe-datum:#8b1e2d" in html
    assert "--farbe-band2:#8b1e2d" in html


def test_ungueltige_farbe_wird_ersetzt(client, hubiplan):
    waehle(hubiplan, "classic")
    hubiplan.info["designs"]["classic"] = {"header": {"color": "red;}", "on_color": "#fff"}}
    html = text(client.get("/"))
    assert "red;}" not in html
    assert "--farbe-kopf:#123456" in html


def test_aelteres_hubiplan_ohne_design(client, hubiplan):
    hubiplan.info.pop("design", None)
    hubiplan.info.pop("designs", None)
    html = text(client.get("/"))
    assert 'class="design-classic"' in html
    assert "--farbe-kopf:#123456;--auf-kopf:#ffffff" in html
    assert "--farbe-fuss:#1d2421" in html


def test_unbekanntes_design_wie_klassisch(client, hubiplan):
    waehle(hubiplan, "bunt")
    assert 'class="design-classic"' in text(client.get("/"))


def test_zeitung_zwei_spalten(client, hubiplan):
    waehle(hubiplan, "newspaper", home=["greeting", "events", "honors"])
    html = text(client.get("/"))
    haupt, seite = html.split('class="spalte-haupt"')[1].split('class="spalte-seite"')
    assert "Willkommen" in haupt and "Nächste Termine" not in haupt
    assert "Unsere Majestäten" in seite


def test_buehne_mit_namen(client, hubiplan):
    waehle(hubiplan, "stage", home=["greeting", "events"])
    html = text(client.get("/"))
    assert 'class="buehne"' in html
    assert html.index('class="buehne"') < html.index("Willkommen")


def test_design_nur_in_der_vorschau_ansehen(client, hubiplan):
    waehle(hubiplan, "classic")
    # Ohne Vorschau wirkt das Cookie nicht
    client.cookies["vorschau-design"] = "stage"
    assert 'class="design-classic"' in text(client.get("/"))
    del client.cookies["vorschau-design"]
    r = client.get("/vorschau/?schluessel=gut&design=stage")
    assert r.status_code == 302
    assert r.cookies["vorschau-design"].value == "stage"
    html = text(client.get("/"))
    assert 'class="design-stage"' in html
    assert "noch nicht übernommen" in html
    # Zurück zum gewählten Design
    r = client.get("/vorschau/design/")
    assert r.cookies["vorschau-design"].value == ""
    html = text(client.get("/"))
    assert 'class="design-classic"' in html and "noch nicht übernommen" not in html


def test_unbekanntes_design_in_der_vorschau(client, hubiplan):
    waehle(hubiplan, "classic")
    r = client.get("/vorschau/?schluessel=gut&design=<script>")
    assert "vorschau-design" not in r.cookies or r.cookies["vorschau-design"].value == ""
    assert 'class="design-classic"' in text(client.get("/"))


def test_vorschau_beenden_vergisst_design(client, hubiplan):
    waehle(hubiplan, "classic")
    client.get("/vorschau/?schluessel=gut&design=festive")
    r = client.get("/vorschau/ende/")
    assert r.cookies["vorschau-design"].value == ""
