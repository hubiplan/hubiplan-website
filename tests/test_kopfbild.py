"""Kopfbild statt Wappen und Name, Schriften für Designpakete (Ralf 05.11.2026, erfunden)."""

import re
from pathlib import Path

from django.core.cache import cache

from . import fake

STATIC = Path(__file__).resolve().parents[1] / "seite" / "static" / "seite"


def text(response) -> str:
    return response.content.decode()


def test_ohne_kopfbild_wappen_und_name(client, hubiplan):
    html = text(client.get("/"))
    assert 'class="marke marke-bild"' not in html
    assert "/medien/m/logos/wappen.png" in html


def test_kopfbild_ersetzt_wappen_und_name(client, hubiplan):
    hubiplan.info["header_image"] = {
        "key": "banner",
        "url": f"{fake.BASE}images/banner-v2/",
        "small_url": f"{fake.BASE}images/banner-v2/?size=small",
        "width": 1200,
        "height": 300,
        "caption": "",
        "alt": "Schützenverein Musterdorf 1900",
    }
    html = text(client.get("/"))
    kopf = re.search(r'<header class="kopf"[^>]*>(.*?)</header>', html, re.S).group(1)
    assert '<a class="marke marke-bild" href="/">' in kopf
    assert 'src="/medien/a/images/banner-v2/"' in kopf
    assert 'alt="Schützenverein Musterdorf 1900"' in kopf
    assert 'width="1200" height="300"' in kopf
    # Ohne Handyfassung (Webseite #73) kein <picture>
    assert "<picture>" not in kopf and "<source" not in kopf
    # Wappen und Name stehen nicht zusätzlich daneben
    assert "logos/wappen.png" not in kopf
    assert "hubiplan.example" not in html
    # Das Bild kommt über diese Seite
    assert client.get("/medien/a/images/banner-v2/").status_code == 200


def test_schriften_liegen_lokal():
    css = (STATIC / "seite.css").read_text()
    for name in ("open-sans", "roboto", "source-sans-3", "crimson-pro"):
        for weight in (400, 600, 700):
            assert f'url("schriften/{name}-{weight}.woff2")' in css
            assert (STATIC / "schriften" / f"{name}-{weight}.woff2").stat().st_size > 1000
        assert "SIL Open Font License" in (STATIC / "schriften" / f"OFL-{name}.txt").read_text()
    for name, weights in (
        ("oswald", (400, 600, 700)),
        ("atkinson-hyperlegible", (400, 700)),
        ("unifraktur-maguntia", (400,)),
    ):
        for weight in weights:
            assert f'url("schriften/{name}-{weight}.woff2")' in css
            assert (STATIC / "schriften" / f"{name}-{weight}.woff2").stat().st_size > 1000
        assert "SIL Open Font License" in (STATIC / "schriften" / f"OFL-{name}.txt").read_text()
    # Keine Schrift von fremden Servern
    assert "fonts.googleapis" not in css and "http" not in css.split("@font-face", 1)[1][:2000]


def test_kopfbild_fuer_schmale_bildschirme(client, hubiplan):
    """Webseite #73: eigene Fassung fürs Handy unter 600 px, sonst das Kopfbild."""
    hubiplan.info["header_image"] = {
        "key": "banner",
        "url": f"{fake.BASE}images/banner-v2/",
        "width": 2200,
        "height": 500,
        "alt": "Schützenverein Musterdorf 1900",
    }
    # Ohne Handyfassung bleibt alles wie bisher (test_kopfbild_ersetzt_wappen_und_name);
    # die Grunddaten bleiben zwischengespeichert, daher gleich mit Handyfassung
    hubiplan.info["header_image_narrow"] = {
        "key": "banner-schmal",
        "url": f"{fake.BASE}images/banner-schmal-v1/",
        "width": 800,
        "height": 400,
        "alt": "",
    }
    html = text(client.get("/"))
    kopf = re.search(r'<header class="kopf"[^>]*>(.*?)</header>', html, re.S).group(1)
    assert (
        '<picture><source media="(max-width: 600px)" srcset="/medien/a/images/banner-schmal-v1/"'
        ' width="800" height="400">'
    ) in kopf
    assert 'src="/medien/a/images/banner-v2/"' in kopf
    assert 'alt="Schützenverein Musterdorf 1900"' in kopf
    assert kopf.count("</picture>") == 1
    assert "hubiplan.example" not in html


def test_mehrere_kopfbilder_zufaellig_auf_jeder_seite(client, hubiplan, monkeypatch):
    """hubiplan #480: mit mehreren Kopfbildern wählt die Webseite bei jedem Aufruf eines,
    auf allen Seiten und ohne Skript; die Fassungen für Handys gehören bei gleicher Zahl
    dazu. Die Antwort wird dann nicht zwischengespeichert."""
    import random

    def bild(n, schmal=False):
        key = f"kopf{'schmal' if schmal else ''}{n}"
        return {
            "key": key,
            "url": f"{fake.BASE}images/{key}/",
            "small_url": "",
            "width": 1200 if not schmal else 600,
            "height": 300,
            "alt": f"Banner {n}",
        }

    hubiplan.info["header_image"] = bild(1)
    hubiplan.info["header_images"] = [bild(1), bild(2), bild(3)]
    hubiplan.info["header_image_narrow"] = bild(1, True)
    hubiplan.info["header_images_narrow"] = [bild(1, True), bild(2, True), bild(3, True)]
    monkeypatch.setattr(random, "randrange", lambda n: 2)
    for pfad in ("/", "/kontakt/"):
        cache.clear()
        r = client.get(pfad)
        html = r.content.decode()
        assert 'src="/medien/a/images/kopf3/"' in html, pfad
        assert 'srcset="/medien/a/images/kopfschmal3/"' in html
        assert "kopf1/" not in html and "kopf2/" not in html
        assert r["Cache-Control"] == "no-cache"
    # nur ein Kopfbild: wie bisher, ohne Vorgabe zum Zwischenspeichern
    hubiplan.info["header_images"] = [bild(1)]
    hubiplan.info["header_images_narrow"] = [bild(1, True)]
    cache.clear()
    r = client.get("/")
    assert 'src="/medien/a/images/kopf1/"' in r.content.decode()
    assert "Cache-Control" not in r
