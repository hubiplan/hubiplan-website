"""Vorschau erst nach Bestätigung durch HUBIplan (Gesamtaudit 15.11., WEB-01).

Ein frei erfundenes Cookie ``vorschau`` schaltete Zwischenspeicher und Bildablage ab. Jetzt
gilt eine Vorschau erst, wenn HUBIplan die Sitzung bestätigt hat; sonst wie ein Besucher.
Entwürfe gehen nie an jemanden ohne gültige Vorschau und nie in den öffentlichen Cache.
Erfundene Daten.
"""

from __future__ import annotations

import io

from django.core.cache import cache
from PIL import Image

from seite import api, bilder, site
from tests.fake import KEY

INFO_PATH = f"{api.PREFIX}{KEY}/"
FALSCH = "nichtgueltig-aber-formal-korrekt"


def _info_abrufe(hubiplan) -> int:
    return sum(1 for _m, path, _p in hubiplan.calls if path == INFO_PATH)


def _foto() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (900, 600), "green").save(buf, "JPEG")
    return buf.getvalue()


def test_erfundenes_cookie_nutzt_den_zwischenspeicher(client, hubiplan):
    client.get("/")
    client.cookies["vorschau"] = FALSCH
    assert client.get("/").status_code == 200
    n1 = _info_abrufe(hubiplan)
    r = client.get("/")
    assert _info_abrufe(hubiplan) == n1  # aus dem Zwischenspeicher
    assert "Vorschau beenden" not in r.content.decode()
    # Nur ein Hash der Sitzung liegt im Cache, nie der Wert
    assert cache.get(site._preview_key(FALSCH)) is False
    assert not any(FALSCH in str(k) for k in getattr(cache, "_cache", {}))


def test_erfundenes_cookie_rechnet_bilder_nur_einmal(client, hubiplan, monkeypatch):
    hubiplan.antworten["images/gross-v0/"] = api.Response(200, _foto(), "image/jpeg")
    gerechnet = []
    original = bilder._convert
    monkeypatch.setattr(bilder, "_convert", lambda *a: gerechnet.append(1) or original(*a))
    client.cookies["vorschau"] = FALSCH
    for _ in range(3):
        r = client.get("/medien/a/images/gross-v0/", HTTP_ACCEPT="image/webp")
        assert r.status_code == 200
    assert len(gerechnet) == 1


def test_echte_vorschau_bleibt_vorschau_und_ungecacht(client, hubiplan):
    client.cookies["vorschau"] = hubiplan.preview_session
    assert "Vorschau" in client.get("/").content.decode()
    n1 = _info_abrufe(hubiplan)
    client.get("/")
    assert _info_abrufe(hubiplan) > n1  # Entwürfe nie aus einem Zwischenspeicher
    # Danach ein Besucher ohne Cookie: bekommt nie die Vorschau
    client.cookies.clear()
    assert "Vorschau beenden" not in client.get("/").content.decode()


def test_pruefungen_je_besucher_begrenzt(client, hubiplan, monkeypatch):
    monkeypatch.setattr(site, "PREVIEW_CHECKS_PER_MINUTE", 2)
    for i in range(5):
        client.cookies["vorschau"] = f"erfunden-{i:04d}-abcdef"
        assert client.get("/").status_code == 200
    mit_vorschau = [p for _m, path, p in hubiplan.calls if path == INFO_PATH and p]
    assert len(mit_vorschau) <= 2
