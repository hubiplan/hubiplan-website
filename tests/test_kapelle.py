"""Seiten für eine Kapelle (Ralf 05.11.2026): Mitgliederlisten, Gedenken, Repertoire, Presse,
Suche, Instrument und Anschrift beim Vorstand, Startseite mit eigener Klasse (erfunden)."""

import copy

import pytest
from django.core.cache import cache

from seite import api

from . import fake


def text(response) -> str:
    return response.content.decode()


PDF = b"%PDF-1.4\n%erfunden\n"


@pytest.fixture
def kapelle(hubiplan):
    info = hubiplan.info
    info["blocks"].update(
        {"members": True, "memorial": True, "repertoire": True, "press": True, "search": True}
    )
    info["nav"] = [
        {
            "key": "heading",
            "label": "Mitglieder",
            "heading": True,
            "children": [
                {"key": "board", "label": "Vorstand"},
                {"key": "membertype", "label": "Aktive", "id": "aktive"},
                {"key": "memorial", "label": "In Gedenken"},
            ],
        },
        {"key": "repertoire", "label": "Repertoire"},
        {"key": "press", "label": "Presse"},
    ]
    hubiplan.antworten = {
        "members/aktive/": {
            "title": "Aktive",
            "members": [
                {"name": "Anna Alt", "photo_url": None, "since": 2012, "instrument": "Tuba"},
                {"name": "Bernd Blau", "photo_url": None, "since": 2019},
            ],
        },
        "memorial/": {
            "intro": {
                "slug": "in-gedenken",
                "title": "In Gedenken",
                "text": "Wir **denken** an sie.",
            },
            "members": [{"name": "Carl Christ", "photo_url": None, "died": 2023, "since": 2009}],
        },
        "repertoire/": {
            "pieces": [
                {"title": "Alte Kameraden", "composer": "C. Teike"},
                {"title": "Zapfenstreich", "composer": ""},
            ]
        },
        "documents/?section=press": {
            "documents": [
                {
                    "id": "presse12345678",
                    "title": "Konzert im Park",
                    "source": "Musterblatt",
                    "date": "2019-05-02",
                    "kind": "pdf",
                    "url": fake.BASE + "files/presse12345678/",
                    "preview_url": fake.BASE + "files/presse12345678/?size=small",
                    "size": 20,
                }
            ]
        },
        "documents/?section=documents": {
            "documents": [
                {
                    "id": "eigenes12345678",
                    "title": "Probenplan",
                    "source": "",
                    "date": None,
                    "kind": "pdf",
                    "url": fake.BASE + "files/eigenes12345678/",
                    "preview_url": None,
                    "size": 20,
                }
            ]
        },
        "files/presse12345678/": api.Response(200, PDF, "application/pdf"),
        "search/": {
            "query": "park",
            "results": [
                {
                    "kind": "press",
                    "id": "presse12345678",
                    "title": "Konzert im Park",
                    "text": "Musterblatt",
                },
                {
                    "kind": "page",
                    "slug": "anfahrt",
                    "title": "Anfahrt",
                    "text": "Mit dem Bus zum Park.",
                },
                {"kind": "home", "key": "c:k1", "title": "", "text": "Picknick im Park"},
                {"kind": "unit", "slug": "jaegerzug", "title": "Jägerzug", "text": "Parkfest"},
                {"kind": "intro", "area": "events", "title": "", "text": "Im Park"},
                {"kind": "intro", "area": "unbekannt", "title": "Fällt weg"},
                {"kind": "unbekannt", "title": "Fällt weg"},
            ],
        },
    }
    return hubiplan


def test_menue_mit_ueberschrift_und_lupe(client, kapelle):
    html = text(client.get("/"))
    assert 'href="/mitglieder/aktive/"' in html
    assert 'href="/in-gedenken/"' in html
    assert 'href="/repertoire/"' in html and 'href="/presse/"' in html
    assert 'class="suche-punkt"' in html and 'href="/suche/"' in html
    # Startseite mit eigener Klasse für Designpakete
    assert '<body class="design-classic" data-seite="start">' in html
    assert 'data-seite="start"' not in text(client.get("/termine/"))


def test_ohne_suche_keine_lupe(client, kapelle):
    kapelle.info["blocks"]["search"] = False
    assert 'class="suche-punkt"' not in text(client.get("/"))
    assert client.get("/suche/").status_code == 404


def test_mitgliederliste(client, kapelle):
    html = text(client.get("/mitglieder/aktive/"))
    assert "<h1>Aktive</h1>" in html
    assert "Anna Alt" in html and "Tuba" in html and "seit 2012" in html
    assert client.get("/mitglieder/passive/").status_code == 404
    kapelle.info["blocks"]["members"] = False
    cache.clear()  # Grunddaten sind zwischengespeichert
    assert client.get("/mitglieder/aktive/").status_code == 404


def test_gedenken_mit_einleitung(client, kapelle):
    html = text(client.get("/in-gedenken/"))
    assert "<strong>denken</strong>" in html
    assert "Carl Christ" in html and "2009 – † 2023" in html


def test_repertoire_und_presse(client, kapelle):
    html = text(client.get("/repertoire/"))
    assert "Alte Kameraden" in html and "C. Teike" in html
    html = text(client.get("/presse/"))
    assert "Konzert im Park" in html and "Musterblatt, 2. Mai 2019" in html
    assert 'href="/medien/a/files/presse12345678/"' in html
    pdf = client.get("/medien/a/files/presse12345678/")
    assert pdf.status_code == 200 and pdf["Content-Type"] == "application/pdf"
    assert pdf["Content-Disposition"] == "inline"


def test_pdf_nur_bei_dokumenten(client, kapelle):
    # Ein PDF unter einer Bildadresse wird nicht durchgereicht
    kapelle.antworten["photos/" + "b" * 20 + "/"] = api.Response(200, PDF, "application/pdf")
    assert client.get("/medien/a/photos/" + "b" * 20 + "/").status_code == 404


def test_eigene_dokumente_neben_satzung(client, kapelle):
    kapelle.info["blocks"]["statutes"] = True
    html = text(client.get("/dokumente/"))
    assert "Probenplan" in html and 'href="/medien/a/files/eigenes12345678/"' in html


def test_suche(client, kapelle):
    html = text(client.get("/suche/?q=park"))
    assert 'href="/presse/"' in html and 'href="/seite/anfahrt/"' in html
    assert "Fällt weg" not in html
    assert "5 Treffer" in html
    # Startseite, Untereinheit und Einleitung eines Bereichs (HUBIplan ab 14.11.2026)
    assert '<a href="/"><strong>Startseite</strong></a>' in html
    assert 'href="/zuege/jaegerzug/"' in html or 'href="/einheiten/jaegerzug/"' in html
    assert '<a href="/termine/"><strong>Termine</strong></a>' in html
    leer = text(client.get("/suche/"))
    assert "Treffer" not in leer and 'name="q"' in leer


def test_vorstand_mit_instrument_und_anschrift(client, kapelle, monkeypatch):
    board = copy.deepcopy(fake.BOARD)
    board["roles"][0]["holders"][0]["instrument"] = "Flügelhorn"
    board["roles"][0]["holders"][0]["address"] = {
        "street": "Lindenweg 4",
        "postal_code": "12345",
        "city": "Musterdorf",
    }
    kapelle.antworten["board/"] = board
    html = text(client.get("/vorstand/"))
    assert '<span class="instrument">Flügelhorn</span>' in html
    assert "Lindenweg 4<br>12345 Musterdorf" in html
