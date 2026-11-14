"""Ladezeiten (Messung 14.11.2026): Bildfassungen, AVIF/WebP, ETag, srcset, Schriften,
leeres Design-CSS, Auffrischen im Hintergrund. Alle Bilder hier werden erzeugt."""

import io
import threading

import pytest
from PIL import Image

from seite import api, bilder

from .fake import KEY

SITE = f"{api.PREFIX}{KEY}/"
GROSS = f"https://hubiplan.example{api.PREFIX}{KEY}/images/gross-v0/"


def foto(width=2000, height=1333, fmt="JPEG") -> bytes:
    img = Image.new("RGB", (width, height))
    # Etwas Struktur, damit die Kompression etwas zu tun hat
    for x in range(0, width, 37):
        for y in range(0, height, 53):
            img.putpixel((x, y), (x % 255, y % 255, (x + y) % 255))
    buf = io.BytesIO()
    img.save(buf, fmt)
    return buf.getvalue()


def logo(side=1024) -> bytes:
    img = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    for x in range(side // 4, side * 3 // 4):
        for y in range(side // 4, side * 3 // 4, 3):
            img.putpixel((x, y), (20, 120, 60, 255))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def groesse(body: bytes) -> tuple[int, int]:
    return Image.open(io.BytesIO(body)).size


@pytest.fixture
def grosses_bild(hubiplan):
    body = foto()
    hubiplan.antworten["images/gross-v0/"] = api.Response(200, body, "image/jpeg")
    return body


def test_mittlere_fassung(client, grosses_bild):
    r = client.get("/medien/a/images/gross-v0/?size=medium")
    assert r.status_code == 200 and r["Content-Type"] == "image/jpeg"
    assert groesse(r.content) == (1200, 800)


@pytest.mark.parametrize(
    "accept,ctype",
    [
        ("image/avif,image/webp,image/*,*/*;q=0.8", "image/avif"),
        ("image/webp,*/*", "image/webp"),
        ("image/*,*/*", "image/jpeg"),
    ],
)
def test_format_nach_browser(client, grosses_bild, accept, ctype):
    r = client.get("/medien/a/images/gross-v0/", HTTP_ACCEPT=accept)
    assert r["Content-Type"] == ctype
    assert r["Vary"] == "Accept"
    if ctype != "image/jpeg":
        assert len(r.content) < len(grosses_bild)


def test_fassung_wird_nur_einmal_gerechnet(client, grosses_bild, monkeypatch):
    client.get("/medien/a/images/gross-v0/?size=medium", HTTP_ACCEPT="image/webp")
    gerechnet = []
    original = bilder._convert
    monkeypatch.setattr(bilder, "_convert", lambda *a: gerechnet.append(a) or original(*a))
    r = client.get("/medien/a/images/gross-v0/?size=medium", HTTP_ACCEPT="image/webp")
    assert r["Content-Type"] == "image/webp" and not gerechnet


def test_vorschau_rechnet_ohne_ablage(client, grosses_bild, hubiplan):
    from django.core.cache import caches

    client.cookies["vorschau"] = hubiplan.preview_session
    r = client.get("/medien/a/images/gross-v0/?size=medium", HTTP_ACCEPT="image/webp")
    assert r.status_code == 200 and r["Content-Type"] == "image/webp"
    assert r["Cache-Control"].startswith("private")
    assert not caches["varianten"]._cache


def test_widerruf_vor_fassung(client, grosses_bild, hubiplan):
    """Auch eine schon gerechnete Fassung gibt es nur, wenn HUBIplan das Bild noch liefert."""
    assert client.get("/medien/a/images/gross-v0/", HTTP_ACCEPT="image/webp").status_code == 200
    hubiplan.maintenance = True
    assert client.get("/medien/a/images/gross-v0/", HTTP_ACCEPT="image/webp").status_code == 404


def test_etag_und_304(client, grosses_bild):
    r = client.get("/medien/a/images/gross-v0/", HTTP_ACCEPT="image/webp")
    tag = r["ETag"]
    assert tag.startswith('"') and r["Cache-Control"] == "public, max-age=86400"
    again = client.get(
        "/medien/a/images/gross-v0/", HTTP_ACCEPT="image/webp", HTTP_IF_NONE_MATCH=tag
    )
    assert again.status_code == 304 and not again.content
    assert again["ETag"] == tag
    # Anderes Format → anderer Inhalt → anderes ETag
    jpeg = client.get("/medien/a/images/gross-v0/", HTTP_IF_NONE_MATCH=tag)
    assert jpeg.status_code == 200 and jpeg["ETag"] != tag


def test_beitragsbilder_einen_tag(client, hubiplan):
    r = client.get("/medien/a/posts/images/abcd1234/")
    assert r["Cache-Control"] == "public, max-age=86400"
    assert client.get("/medien/a/images/festbild1/")["Cache-Control"] == "public, max-age=600"


def test_logo_klein(client, hubiplan):
    hubiplan.medien["logos/abteilungen/9-20261031191237.png"] = api.Response(
        200, logo(), "image/png"
    )
    path = "/medien/m/logos/abteilungen/9-20261031191237.png"
    gross = client.get(path)
    klein = client.get(path + "?w=120")
    assert groesse(klein.content) == (120, 120) and klein["Content-Type"] == "image/png"
    assert len(klein.content) < len(gross.content) / 4
    assert klein["Cache-Control"] == "public, max-age=31536000, immutable"
    webp = client.get(path + "?w=120", HTTP_ACCEPT="image/webp")
    assert webp["Content-Type"] == "image/webp"
    assert Image.open(io.BytesIO(webp.content)).mode == "RGBA"
    # Andere Breiten rechnet die Seite nicht (kein Spielzeug für beliebige Größen)
    assert groesse(client.get(path + "?w=333").content) == (1024, 1024)


def test_symbole_bleiben_png(client, hubiplan):
    hubiplan.info["icon"] = True
    r = client.get("/medien/a/icon-192.png", HTTP_ACCEPT="image/avif,image/webp")
    assert r["Content-Type"] == "image/png"


def test_kaputtes_bild_kommt_unveraendert(client, hubiplan):
    hubiplan.antworten["images/kaputt-v0/"] = api.Response(200, b"\xff\xd8kein bild", "image/jpeg")
    r = client.get("/medien/a/images/kaputt-v0/?size=medium", HTTP_ACCEPT="image/webp")
    assert r.status_code == 200 and r.content == b"\xff\xd8kein bild"


def bild(width=2000):
    return {
        "key": "gross",
        "url": GROSS,
        "small_url": GROSS + "?size=small",
        "width": width,
        "height": width * 2 // 3,
        "caption": "",
        "alt": "Festzug",
    }


def test_srcset_mit_mittlerer_fassung(client, hubiplan):
    hubiplan.info["greeting"] = {"title": "Hallo", "text": "", "image": bild()}
    html = client.get("/").content.decode()
    assert (
        'srcset="/medien/a/images/gross-v0/?size=small 800w, '
        '/medien/a/images/gross-v0/?size=medium 1200w, /medien/a/images/gross-v0/ 2000w"'
    ) in html
    assert 'fetchpriority="high"' in html


def test_srcset_ohne_mittel_bei_kleinen_bildern(client, hubiplan):
    hubiplan.info["greeting"] = {"title": "Hallo", "text": "", "image": bild(1000)}
    html = client.get("/").content.decode()
    assert "?size=small 800w, /medien/a/images/gross-v0/ 1000w" in html
    assert "size=medium" not in html


def test_karussell_erstes_bild_bevorzugt(client, hubiplan):
    hubiplan.info["greeting"] = {
        "title": "Hallo",
        "text": "",
        "image": None,
        "gallery": [bild(), {**bild(), "alt": "Zelt"}],
    }
    html = client.get("/").content.decode()
    assert html.count('fetchpriority="high"') == 1
    assert html.count("size=medium 1200w") == 2


def test_logos_in_anzeigegroesse(client, hubiplan):
    html = client.get("/").content.decode()
    assert "/medien/m/logos/wappen.png?w=112" in html


def test_schriften_vorladen(client, hubiplan):
    hubiplan.info["style"] = {"font": "festive"}
    html = client.get("/").content.decode()
    assert html.count('rel="preload"') == 3
    assert 'as="font" type="font/woff2" crossorigin' in html
    hubiplan.info["style"] = {"font": "system"}
    from django.core.cache import cache

    cache.clear()
    assert 'rel="preload"' not in client.get("/").content.decode()


@pytest.mark.parametrize(
    "css,erwartet",
    [
        ("/* Keine Abweichungen von seite.css */\n", False),
        ("  \n", False),
        (".kopf { color: red; }", True),
    ],
)
def test_leeres_design_css_ohne_abruf(monkeypatch, css, erwartet):
    from seite.site import Site

    monkeypatch.setattr(Site, "package", property(lambda self: {"css": css, "hash": "x"}))
    assert Site.package_has_css.fget(object.__new__(Site)) is erwartet


def test_auffrischen_im_hintergrund(hubiplan, monkeypatch, settings):
    settings.REFRESH_IN_BACKGROUND = True
    jetzt = [1000.0]
    monkeypatch.setattr(api.time, "time", lambda: jetzt[0])
    assert api.get(KEY)["name"] == hubiplan.info["name"]
    hubiplan.info["name"] = "Neuer Name"
    jetzt[0] += settings.CACHE_SECONDS + 1
    gestartet = []
    echt = threading.Thread

    def thread(*a, **kw):
        t = echt(*a, **kw)
        gestartet.append(t)
        return t

    monkeypatch.setattr(api.threading, "Thread", thread)
    # Sofort der letzte Stand, neu geholt wird nebenher
    assert api.get(KEY)["name"] != "Neuer Name"
    assert len(gestartet) == 1
    gestartet[0].join(5)
    assert api.get(KEY)["name"] == "Neuer Name"
    # Nach mehr als 15 Minuten ohne Besuch wartet der Aufruf wieder auf HUBIplan
    hubiplan.info["name"] = "Noch neuer"
    jetzt[0] += settings.CACHE_SECONDS + api.STALE_SECONDS + 1
    assert api.get(KEY)["name"] == "Noch neuer"
    assert len(gestartet) == 1
