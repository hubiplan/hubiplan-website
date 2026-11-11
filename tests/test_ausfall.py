"""HUBIplan nicht erreichbar (Ausrollen): letzter guter Stand statt Fehlerseite."""

import pytest

from seite import api

from .fake import KEY


@pytest.fixture
def uhr(monkeypatch):
    jetzt = [1_000_000.0]
    monkeypatch.setattr(api.time, "time", lambda: jetzt[0])
    return jetzt


@pytest.mark.parametrize("ausfall", ["weg", 429, 502, 504])
def test_seite_bleibt_beim_ausfall(client, hubiplan, uhr, settings, ausfall):
    assert client.get("/").status_code == 200
    assert client.get("/vorstand/").status_code == 200
    assert client.get("/medien/a/images/festbild1/").status_code == 200
    assert client.get("/medien/m/logos/wappen.png").status_code == 200
    uhr[0] += 3600  # Zwischenspeicher und Zuordnung längst abgelaufen
    hubiplan.ausfall = ausfall
    r = client.get("/")
    assert r.status_code == 200
    assert hubiplan.info["name"] in r.content.decode()
    assert client.get("/vorstand/").status_code == 200
    assert client.get("/medien/a/images/festbild1/").status_code == 200
    assert client.get("/medien/m/logos/wappen.png").status_code == 200


def test_ausfall_ueber_der_grenze_zeigt_fehler(client, hubiplan, uhr, settings):
    assert client.get("/").status_code == 200
    uhr[0] += settings.STALE_IF_ERROR_SECONDS + 1
    hubiplan.ausfall = "weg"
    assert client.get("/").status_code == 503


def test_ohne_frueheren_stand_fehlerseite(client, hubiplan):
    hubiplan.ausfall = "weg"
    assert client.get("/").status_code == 503
    assert client.get("/medien/a/images/festbild1/").status_code == 503


def test_wartung_wirkt_sofort_wenn_hubiplan_antwortet(client, hubiplan, uhr, settings):
    assert client.get("/vorstand/").status_code == 200
    uhr[0] += settings.CACHE_SECONDS + 1
    hubiplan.ausfall = "weg"
    assert client.get("/vorstand/").status_code == 200
    hubiplan.ausfall = None
    hubiplan.maintenance = True
    assert client.get("/vorstand/").status_code == 503
    # verborgene Seite: Bild weg und Kopie verworfen, auch beim nächsten Ausfall
    assert client.get("/medien/a/images/festbild1/").status_code == 404
    hubiplan.ausfall = "weg"
    assert client.get("/medien/a/images/festbild1/").status_code == 503


def test_neuer_stand_nach_dem_ausfall(hubiplan, uhr, settings):
    assert api.get(KEY)["name"] == hubiplan.info["name"]
    uhr[0] += settings.CACHE_SECONDS + 1
    hubiplan.ausfall = "weg"
    alt = api.get(KEY)["name"]
    hubiplan.ausfall = None
    hubiplan.info["name"] = "Neuer Name"
    assert alt != "Neuer Name"
    assert api.get(KEY)["name"] == "Neuer Name"


def test_vorschau_nie_aus_dem_altstand(client, hubiplan, uhr):
    hubiplan.maintenance = True
    client.cookies["vorschau"] = hubiplan.preview_session
    assert client.get("/vorstand/").status_code == 200
    assert client.get("/medien/a/images/festbild1/").status_code == 200
    hubiplan.ausfall = "weg"
    assert client.get("/vorstand/").status_code == 503
    assert client.get("/medien/a/images/festbild1/").status_code == 503


def test_grosse_bilder_ohne_kopie(client, hubiplan, settings):
    settings.STALE_IMAGE_MAX_BYTES = 10
    assert client.get("/medien/a/images/festbild1/").status_code == 200
    hubiplan.ausfall = "weg"
    assert client.get("/medien/a/images/festbild1/").status_code == 503
