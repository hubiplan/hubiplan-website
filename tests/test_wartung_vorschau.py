"""Wartungsmodus und Vorschau."""

import pytest

from seite import api

from .fake import KEY, PNG


def text(response) -> str:
    return response.content.decode()


def test_wartung_zeigt_wartungsseite(client, hubiplan):
    hubiplan.maintenance = True
    for path in ("/", "/vorstand/", "/termine/", "/kontakt/"):
        r = client.get(path)
        assert r.status_code == 503, path
        assert "Bald geht es los." in text(r)
        assert r["X-Robots-Tag"] == "noindex"
    # Kein Menü in der Wartung
    assert ">Vorstand</a>" not in text(client.get("/"))
    assert "Disallow: /" in text(client.get("/robots.txt"))


def test_wartung_impressum_bleibt(client, hubiplan):
    hubiplan.maintenance = True
    assert client.get("/impressum/").status_code == 200
    assert client.get("/datenschutz/").status_code == 200


def test_wartung_keine_bilder(client, hubiplan):
    hubiplan.maintenance = True
    assert client.get("/medien/a/images/festbild1/").status_code == 404
    # Logo und Wappen bleiben (Kopf der Wartungsseite)
    assert client.get("/medien/m/logos/wappen.png").status_code == 200


def test_allgemeine_wartung(client, hubiplan, settings):
    settings.MAINTENANCE = True
    r = client.get("/")
    assert r.status_code == 503
    assert not hubiplan.calls


def test_vorschau(client, hubiplan, settings):
    hubiplan.maintenance = True
    r = client.get("/vorschau/?schluessel=gut")
    assert r.status_code == 302
    assert r["Location"] == "/"
    cookie = r.cookies["vorschau"]
    assert cookie.value == hubiplan.preview_session
    assert cookie["httponly"]
    assert cookie["samesite"] == "Lax"
    r = client.get("/vorstand/")
    assert r.status_code == 200
    html = text(r)
    assert "Vorschau beenden" in html
    assert "Max Muster" in html
    assert r["Cache-Control"] == "private, no-store"
    # Kontaktformular in der Vorschau trägt die Vorschau-Sitzung
    assert f'data-vorschau="{hubiplan.preview_session}"' in text(client.get("/kontakt/"))
    # Bilder in der Vorschau
    r = client.get("/medien/a/images/festbild1/")
    assert r.content == PNG
    assert r["Cache-Control"] == "private, no-store"
    # Every preview read revalidates authorization, even within the old fresh TTL.
    n = len(hubiplan.calls)
    client.get("/vorstand/")
    assert len(hubiplan.calls) > n
    # Beenden
    r = client.get("/vorschau/ende/")
    assert r.cookies["vorschau"].value == ""
    client.cookies.pop("vorschau")
    assert client.get("/vorstand/").status_code == 503


def test_vorschau_ungueltig(client, hubiplan):
    r = client.get("/vorschau/?schluessel=falsch")
    assert r.status_code == 403
    assert "vorschau" not in r.cookies
    assert client.get("/vorschau/").status_code == 400


def test_vorschau_cookie_unsauber(client, hubiplan):
    hubiplan.maintenance = True
    client.cookies["vorschau"] = "<b>"
    assert client.get("/").status_code == 503
    assert all(c[2] is None for c in hubiplan.calls)


def _resolved(hubiplan) -> list[str]:
    return [p.split("host=")[1] for _, p, _ in hubiplan.calls if "resolve/" in p]


def test_vorschau_waehlt_webseite_bei_fester_zuordnung(client, hubiplan, settings):
    """Testserver: eine Adresse für alle Webseiten; der Vorschau-Link nennt die Webseite."""
    settings.SITE_HOST_OVERRIDE = "www.musterdorf.test"
    hubiplan.hosts["www.zweiter-verein.test"] = hubiplan.hosts["www.musterdorf.test"]
    hubiplan.maintenance = True
    r = client.get("/vorschau/?schluessel=gut&seite=www.zweiter-verein.test")
    assert r.status_code == 302
    assert r.cookies["vorschau-seite"].value == "www.zweiter-verein.test"
    assert r.cookies["vorschau-seite"]["httponly"]
    assert _resolved(hubiplan)[-1] == "www.zweiter-verein.test"
    assert client.get("/vorstand/").status_code == 200
    assert _resolved(hubiplan)[-1] == "www.zweiter-verein.test"
    # Beenden: wieder die fest eingestellte Webseite
    r = client.get("/vorschau/ende/")
    assert r.cookies["vorschau-seite"].value == ""
    client.cookies.pop("vorschau")
    client.cookies.pop("vorschau-seite")
    client.get("/vorstand/")
    assert _resolved(hubiplan)[-1] == "www.musterdorf.test"


def test_vorschau_seite_nur_bei_fester_zuordnung(client, hubiplan, settings):
    hubiplan.maintenance = True
    # Ohne feste Zuordnung entscheidet der Hostname, ?seite= zählt nicht
    r = client.get("/vorschau/?schluessel=gut&seite=www.musterdorf.test")
    assert r.status_code == 302
    assert r.cookies["vorschau-seite"].value == ""
    assert _resolved(hubiplan)[-1] == "testserver"
    # Gewählte Webseite gilt nur zusammen mit einer Vorschau
    settings.SITE_HOST_OVERRIDE = "www.musterdorf.test"
    client.cookies.pop("vorschau")
    client.cookies["vorschau-seite"] = "www.zweiter-verein.test"
    client.get("/")
    assert _resolved(hubiplan)[-1] == "www.musterdorf.test"


def test_vorschau_seite_ungueltig(client, hubiplan, settings):
    settings.SITE_HOST_OVERRIDE = "www.musterdorf.test"
    hubiplan.maintenance = True
    r = client.get("/vorschau/?schluessel=gut&seite=<b>evil")
    assert r.status_code == 302
    assert r.cookies["vorschau-seite"].value == ""
    assert _resolved(hubiplan)[-1] == "www.musterdorf.test"


def test_widerruf_vorschau_ohne_cache_grace(client, hubiplan, monkeypatch, settings):
    from django.core.cache import cache

    hubiplan.maintenance = True
    token = hubiplan.preview_session
    client.cookies["vorschau"] = token
    assert client.get("/vorstand/").status_code == 200
    # Poison an old fresh/stale cache and hold the refresh lock. Revocation still
    # goes to the backend instead of serving either cached privileged response.
    full = f"{api.PREFIX}{KEY}/board/"
    ck = api._key("get", full, token)
    cache.set(ck, (api.time.monotonic(), (200, {"leaked": "secret"})), 600)
    lock = api._lock_for(ck)
    lock.acquire()
    hubiplan.preview_session = "revoked-and-replaced-session"
    try:
        assert client.get("/vorstand/").status_code == 503
        assert client.get("/medien/a/images/festbild1/").status_code == 404
    finally:
        lock.release()


@pytest.mark.parametrize("age", [0, 6, 599])
@pytest.mark.parametrize("path", ["", "board/"])
def test_api_widerruf_trotz_frischem_oder_veraltetem_cache(hubiplan, age, path):
    from django.core.cache import cache

    hubiplan.maintenance = True
    token = hubiplan.preview_session
    api.get(KEY, path, preview=token)
    ck = api._key("get", f"{api.PREFIX}{KEY}/{path}", token)
    cache.set(ck, (api.time.monotonic() - age, (200, {"private": "old-value"})), 700)
    lock = api._lock_for(ck)
    lock.acquire()
    hubiplan.preview_session = "revoked-and-replaced-session"
    before = len(hubiplan.calls)
    try:
        with pytest.raises(api.Maintenance):
            api.get(KEY, path, preview=token)
        assert len(hubiplan.calls) == before + 1
    finally:
        lock.release()
