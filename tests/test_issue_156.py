"""Webseite #156: Anrede auf der Terminseite, Schrift der Einheitsnamen, eckige Reste,
eine Knopfart im Kontakt einer Einheit, Datumsfarbe in der Terminliste. Alle Daten erfunden."""

from pathlib import Path

from django.core.cache import cache

STATIC = Path(__file__).resolve().parents[1] / "seite" / "static" / "seite"


def hole(client, pfad: str) -> str:
    cache.clear()
    return client.get(pfad).content.decode()


def test_terminseite_siezt_wie_bisher(client, hubiplan):
    html = hole(client, "/termine/")
    assert "automatisch in Ihrem Kalender" in html
    assert "<code>" not in html
    assert '<span class="abo-adresse" id="abo-adresse">' in html
    assert 'data-kopieren="abo-adresse"' in html and "Adresse kopieren" in html


def test_terminseite_duzt(client, hubiplan):
    hubiplan.info["style"] = {"address": "informal"}
    html = hole(client, "/termine/")
    assert "automatisch in deinem Kalender" in html
    assert "Ihrem Kalender" not in html


def test_kopierknopf_nur_mit_zwischenablage():
    js = (STATIC / "termin.js").read_text()
    assert "navigator.clipboard" in js and "absatz.hidden = false" in js


def test_naechster_termin_markiert(client, hubiplan):
    html = hole(client, "/termine/")
    assert html.count("termin-naechster") == 1
    css = (STATIC / "stil.css").read_text()
    assert (
        '[data-st-date="card"] .termine > .termin-naechster .termin-datum '
        "{ background: var(--primaer);"
    ) in css


def test_einheitsnamen_in_ueberschriftenschrift(client, hubiplan):
    html = hole(client, "/zuege/")
    assert '<span class="einheit-name">' in html
    assert "wappen-platz" in html or "<img" in html  # Ersatzwappen bleiben
    css = (STATIC / "stil.css").read_text()
    assert ".kacheln .einheit-name { font-family: var(--schrift-titel); }" in css


def test_eckig_ueberall():
    css = (STATIC / "stil.css").read_text()
    regel = css[css.index("Webseite #156: auch Marken") :]
    regel = regel[: regel.index("}")]
    teile = (
        ".beitrag-marke",
        ".beitrag-weitere img",
        ".filter select",
        ".dok-vorschau",
        ".knopf-rund",
        ".karussell-zaehler",
    )
    for teil in teile:
        assert teil in regel
    assert "border-radius: 0" in css[css.index("Webseite #156: auch Marken") :][:600]
    seite = (STATIC / "seite.css").read_text()
    for zeile in seite.splitlines():
        if zeile.startswith((".knopf-rund {", ".karussell-zaehler {")):
            assert "font-family: inherit" in zeile


def test_homepage_knopf_wie_nachricht(client, hubiplan):
    unit = hubiplan.info["units"][0]
    unit["homepage"] = "https://www.jaegerzug.example/"
    html = hole(client, "/zuege/jaeger/")
    assert (
        '<p class="nachricht"><a class="knopf klein-knopf" href="https://www.jaegerzug.example/"'
    ) in html
    css = (STATIC / "stil.css").read_text()
    assert (
        '[data-st-person-cards="label"] .karte:is(.personenkarte, .homepage) '
        ".nachricht a.knopf:not(.hell) {"
    ) in css
