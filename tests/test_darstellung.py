"""Darstellung der festen Bereiche und Einleitungstexte (Konzept webseite-baukasten G5,
Ralf 10.11.2026). Alle Daten erfunden."""

import datetime

from django.utils import timezone

from . import fake


def text(response) -> str:
    return response.content.decode()


def test_ohne_angaben_wie_bisher(client, hubiplan):
    html = text(client.get("/vorstand/"))
    assert '<div class="karten">' in html and "rollenliste" not in html
    assert 'class="einleitung"' not in html
    assert '<ul class="kacheln gross">' in text(client.get("/einheiten/"))
    assert "monatskalender" not in text(client.get("/termine/"))


def test_vorstand_als_liste_mit_einleitung(client, hubiplan):
    hubiplan.info["layouts"] = {"board": "list"}
    hubiplan.info["intros"] = {
        "board": {"title": "", "text": "Unser Vorstand seit **2099**.", "image": None}
    }
    html = text(client.get("/vorstand/"))
    assert '<dl class="rollenliste">' in html and '<div class="karten">' not in html
    assert "<dt>1. Vorsitzender</dt>" in html and "Max Muster" in html
    assert "Zurzeit nicht besetzt." in html
    einleitung = html.split('<div class="einleitung">', 1)[1]
    assert "<strong>2099</strong>" in einleitung.split("</div>", 1)[0]
    assert html.index("einleitung") < html.index("rollenliste")


def test_unbekannte_darstellung_gilt_als_standard(client, hubiplan):
    hubiplan.info["layouts"] = {"board": "poster", "units": "riesig"}
    assert '<div class="karten">' in text(client.get("/vorstand/"))
    assert '<ul class="kacheln gross">' in text(client.get("/einheiten/"))


def test_einheiten_klein(client, hubiplan):
    hubiplan.info["layouts"] = {"units": "small"}
    assert '<ul class="kacheln">' in text(client.get("/einheiten/"))


def test_einheiten_als_liste(client, hubiplan):
    hubiplan.info["layouts"] = {"units": "list"}
    html = text(client.get("/einheiten/"))
    assert '<ul class="einheiten-liste">' in html and "Jägerzug" in html
    assert "gegründet 1950" in html


def test_termine_als_monatskalender(client, hubiplan):
    start = timezone.localtime().replace(hour=18, minute=30, second=0, microsecond=0)
    start += datetime.timedelta(days=3)
    termine = fake.events(start.isoformat())
    termine["events"][0]["ends_at"] = (start + datetime.timedelta(hours=2)).isoformat()
    hubiplan.antworten["events/"] = termine
    hubiplan.info["layouts"] = {"events": "calendar"}
    html = text(client.get("/termine/"))
    assert '<table class="monatskalender">' in html
    assert '<span class="zeit">18:30</span> Schützenfest' in html
    # Fenster mit allen Angaben wie in der Liste, vergangene Termine fehlen
    assert 'class="termin-fenster"' in html and "Mit Musik" in html
    assert "Alter Termin" not in html
    assert '<td class="mit-termin">' in html and '<td class="fremd">' in html


def test_galerie_als_mauerwerk(client, hubiplan):
    hubiplan.info["blocks"]["gallery"] = True
    hubiplan.info["layouts"] = {"gallery": "masonry"}
    hubiplan.info["intros"] = {"gallery": {"title": "", "text": "Bilder vom Fest.", "image": None}}
    bild = {
        "key": "f1",
        "url": f"{fake.BASE}images/f1/",
        "small_url": f"{fake.BASE}images/f1/?size=small",
        "width": 800,
        "height": 1200,
        "caption": "",
        "alt": "Festzug",
    }
    album = {"slug": "fest", "title": "Fest", "year": 2099, "images": 1, "albums": 0, "cover": bild}
    hubiplan.info["galerie"] = {
        "galleries/": {"albums": [album]},
        "galleries/fest/": {**album, "images": [bild], "albums": [], "parent": None},
    }
    html = text(client.get("/galerie/"))
    assert '<ul class="galerie-alben mauerwerk">' in html and "Bilder vom Fest." in html
    assert '<ul class="galerie-bilder mauerwerk">' in text(client.get("/galerie/fest/"))
