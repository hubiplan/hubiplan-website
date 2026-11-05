"""Galerie (Ralf 05.11.2026): Alben mit Unteralben und Bilder groß im Fenster (erfundene Daten)."""

import pytest

from . import fake


def text(response) -> str:
    return response.content.decode()


def _bild(key: str, caption: str = "", alt: str = "") -> dict:
    return {
        "key": key,
        "url": f"{fake.BASE}images/{key}-v1/",
        "small_url": f"{fake.BASE}images/{key}-v1/?size=small",
        "width": 60,
        "height": 40,
        "caption": caption,
        "alt": alt or caption,
    }


def _kurz(slug, title, year=None, images=0, albums=0, cover=None) -> dict:
    return {
        "slug": slug,
        "title": title,
        "year": year,
        "date": f"{year}-06-01" if year else None,
        "cover": cover,
        "images": images,
        "albums": albums,
    }


@pytest.fixture
def galerie(hubiplan):
    hubiplan.info["blocks"]["gallery"] = True
    hubiplan.info["nav"] = [{"key": "gallery", "label": "Galerie"}]
    hubiplan.info["galerie"] = {
        "galleries/": {
            "albums": [
                _kurz("2024", "2024", 2024, images=2, albums=1, cover=_bild("umzug")),
                _kurz("ohne-bild", "Leeres Album"),
            ]
        },
        "galleries/2024/": {
            "slug": "2024",
            "title": "2024",
            "description": "Unser Jahr.",
            "year": 2024,
            "date": "2024-06-01",
            "parent": None,
            "albums": [
                _kurz("schuetzenfest", "Schützenfest", 2024, images=2, cover=_bild("umzug"))
            ],
            "images": [],
        },
        "galleries/schuetzenfest/": {
            "slug": "schuetzenfest",
            "title": "Schützenfest",
            "description": "",
            "year": 2024,
            "date": "2024-06-01",
            "parent": {"slug": "2024", "title": "2024"},
            "albums": [],
            "images": [_bild("umzug", "Der Umzug"), _bild("parade", "", "Parade am Markt")],
        },
    }
    return hubiplan


def test_uebersicht(client, galerie):
    html = text(client.get("/galerie/"))
    assert "<h1>Galerie</h1>" in html
    assert 'href="/galerie/2024/"' in html
    # Titelbild über diese Seite, klein
    assert 'src="/medien/a/images/umzug-v1/?size=small"' in html
    assert "2024 · 2 Bilder · 1 Album" in html
    assert "0 Bilder" in html and "galerie-ohne-bild" in html
    assert "hubiplan.example" not in html


def test_menue(client, galerie):
    html = text(client.get("/"))
    assert 'href="/galerie/"' in html


def test_album_mit_unteralbum(client, galerie):
    html = text(client.get("/galerie/2024/"))
    assert "<h1>2024</h1>" in html and "Unser Jahr." in html
    assert 'href="/galerie/schuetzenfest/"' in html
    # Ohne eigene Bilder kein Bildfenster
    assert "bild-fenster" not in html


def test_album_mit_bildern(client, galerie):
    html = text(client.get("/galerie/schuetzenfest/"))
    # Brotkrumen: Galerie › Oberalbum
    assert 'href="/galerie/"' in html and 'href="/galerie/2024/"' in html
    assert 'class="galerie-bild" href="/medien/a/images/umzug-v1/"' in html
    assert 'src="/medien/a/images/parade-v1/?size=small"' in html
    assert 'data-unterschrift="Der Umzug"' in html
    assert 'alt="Parade am Markt"' in html
    assert 'id="bild-fenster"' in html and "bildfenster.js" in html


def test_unbekanntes_album(client, galerie):
    assert client.get("/galerie/gibt-es-nicht/").status_code == 404


def test_bereich_aus(client, galerie):
    galerie.info["blocks"]["gallery"] = False
    assert client.get("/galerie/").status_code == 404
    assert client.get("/galerie/schuetzenfest/").status_code == 404


def test_englisch(client, galerie):
    galerie.info["language"] = "en"
    html = text(client.get("/galerie/"))
    assert "<h1>Gallery</h1>" in html
    assert "2 images · 1 album" in html
