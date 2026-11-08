"""Tempo: Bilder ohne Grunddaten, alter Stand statt gleichzeitiger Neuabrufe."""

from seite import api

from .fake import KEY

SITE = f"{api.PREFIX}{KEY}/"


def test_bild_ohne_grunddaten(client, hubiplan):
    r = client.get("/medien/a/images/festbild1/?size=small")
    assert r.status_code == 200 and r["Content-Type"] == "image/png"
    assert not [c for c in hubiplan.calls if c[1] == SITE]


def test_bild_in_der_vorschau_privat(client, hubiplan):
    hubiplan.maintenance = True
    client.cookies["vorschau"] = hubiplan.preview_session
    r = client.get("/medien/a/images/festbild1/")
    assert r.status_code == 200 and r["Cache-Control"].startswith("private")


def test_bild_der_verborgenen_seite_fehlt(client, hubiplan):
    hubiplan.maintenance = True
    assert client.get("/medien/a/images/festbild1/").status_code == 404


def test_abgelaufen_alter_stand_waehrend_neuabruf(hubiplan, monkeypatch, settings):
    jetzt = [1000.0]
    monkeypatch.setattr(api.time, "time", lambda: jetzt[0])
    assert api.get(KEY)["name"] == hubiplan.info["name"]
    hubiplan.info["name"] = "Neuer Name"
    jetzt[0] += settings.CACHE_SECONDS + 1
    lock = api._lock_for(api._key("get", SITE, ""))
    lock.acquire()  # ein anderer Thread holt gerade neu
    try:
        vorher = len(hubiplan.calls)
        assert api.get(KEY)["name"] != "Neuer Name"
        assert len(hubiplan.calls) == vorher
    finally:
        lock.release()
    assert api.get(KEY)["name"] == "Neuer Name"


def test_vorschau_bilder_und_wappen_im_browser(client, hubiplan):
    """Vorschau: Seiten prüfen den Zugang jedes Mal neu, Bilder und Wappen darf der
    eigene Browser aber kurz behalten (sonst lädt jeder Seitenwechsel alles neu)."""
    hubiplan.maintenance = True
    client.cookies["vorschau"] = hubiplan.preview_session
    assert client.get("/")["Cache-Control"] == "private, no-store"
    for url in ("/medien/a/images/festbild1/?size=small", "/medien/m/logos/wappen.png"):
        r = client.get(url)
        assert r.status_code == 200
        assert r["Cache-Control"] == "private, max-age=300"
