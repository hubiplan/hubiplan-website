"""Sprache der Webseite (hubiplan/konzepte/englisch.md, W1): Rahmentexte je Webseite
deutsch oder englisch, Vereinsdaten bleiben, wie sie sind. Alle Daten erfunden."""

import re
from pathlib import Path

import pytest

PO = Path(__file__).resolve().parents[1] / "locale" / "en" / "LC_MESSAGES" / "django.po"


def text(response) -> str:
    return response.content.decode()


@pytest.fixture
def englisch(hubiplan):
    hubiplan.info["language"] = "en"
    return hubiplan


def test_standard_ist_deutsch(client, hubiplan):
    r = client.get("/")
    html = text(r)
    assert '<html lang="de">' in html
    assert r["Content-Language"] == "de"
    assert "Zum Inhalt springen" in html
    assert 'id="seite-texte"' not in html


def test_unbekannte_sprache_ist_deutsch(client, hubiplan):
    hubiplan.info["language"] = "fr"
    assert '<html lang="de">' in text(client.get("/"))


def test_startseite_englisch(client, englisch):
    r = client.get("/")
    html = text(r)
    assert '<html lang="en">' in html
    assert r["Content-Language"] == "en"
    assert "Skip to content" in html
    assert "Zum Inhalt springen" not in html
    # Vereinsdaten bleiben unverändert
    assert "Schützenverein Musterdorf 1900" in html
    assert "Event by Bürgerverein Musterdorf" in html
    # Texte für die Skripte stehen als JSON bereit (kein ausführbares Skript)
    assert '<script id="seite-texte" type="application/json">' in html
    assert "Please check the marked fields." in html


def test_termine_englisch(client, englisch):
    html = text(client.get("/termine/"))
    assert "Events" in html
    # Monatsüberschrift und Datum englisch, ohne „Uhr“
    assert re.search(r"June 2099", html)
    sichtbar = re.sub(r'<script id="seite-texte".*?</script>', "", html, flags=re.S)
    assert "Uhr" not in sichtbar


def test_kontakt_englisch(client, englisch):
    html = text(client.get("/kontakt/"))
    assert "Send message" in html
    assert "Your email address" in html


def test_fehlerseite_englisch(client, englisch):
    r = client.get("/zuege/gibtsnicht/")
    assert r.status_code == 404
    assert "Page not found" in text(r)


def test_menue_englisch(client, englisch):
    html = text(client.get("/"))
    assert ">Home<" in html
    assert ">Contact<" in html


def test_katalog_vollstaendig():
    """Jeder Text im englischen Katalog hat eine Übersetzung."""
    eintraege = PO.read_text(encoding="utf-8").split("\n\n")[1:]
    leer = [e for e in eintraege if re.search(r'^msgstr(\[\d\])? ""\Z', e.strip(), re.M)]
    assert leer == []
    # Unscharfe Vorschläge von makemessages gelten nicht als übersetzt
    assert "#, fuzzy" not in PO.read_text(encoding="utf-8")


def test_rechtstexte_mit_hinweis(client, englisch):
    html = text(client.get("/impressum/"))
    assert "Legal notice" in html
    assert "the German version is authoritative" in html


def test_rechtstexte_deutsch_ohne_hinweis(client, hubiplan):
    assert "maßgeblich ist die deutsche Fassung" not in text(client.get("/impressum/"))


def test_ergebnisse_englisch(client, englisch):
    from .fake import BASE, COMP

    englisch.info["results_url"] = BASE + "results/"
    englisch.info["nav"] = [{"key": "results", "label": "Results", "children": []}]
    html = text(client.get("/ergebnisse/"))
    assert "<h1>Results</h1>" in html and "Place" in html
    assert "Max M." in html and "ergebnisse.js" in html
    assert "Platz" not in html
    html = text(client.get(f"/ergebnisse/{COMP}/"))
    assert "All results" in html and "Place" in html
    assert "Platz" not in html
