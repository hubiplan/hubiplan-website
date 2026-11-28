"""UX-Audit 31.10.2026: Rechtstexte bei Wartung, Kontakt, Termine, Telefon, Vorschau."""

from pathlib import Path

import pytest
from django.core.cache import cache

from seite import api
from seite.hilfen.anzeige import tel

from . import fake


def text(response) -> str:
    return response.content.decode()


class TestRechtstexte:
    """S02/F15: Impressum und Datenschutz auch bei allgemeiner Wartung."""

    def test_allgemeine_wartung_zeigt_aktuelle_fassung(self, client, hubiplan, settings):
        settings.MAINTENANCE = True
        r = client.get("/impressum/")
        assert r.status_code == 200
        assert "Dorfstraße 1" in text(r)
        assert "Gespeicherte Fassung" not in text(r)
        assert client.get("/datenschutz/").status_code == 200
        # Startseite bleibt in Wartung
        assert client.get("/").status_code == 503

    def test_ausfall_zeigt_letzte_fassung_mit_stand(self, client, hubiplan, monkeypatch):
        assert client.get("/impressum/").status_code == 200
        cache.clear()

        def down(*args, **kwargs):
            raise api.Unavailable("weg")

        monkeypatch.setattr(api, "_request", down)
        r = client.get("/impressum/")
        assert r.status_code == 200
        assert "Dorfstraße 1" in text(r) and "Gespeicherte Fassung, Stand" in text(r)
        r = client.get("/datenschutz/")
        assert r.status_code == 200 and "Wir speichern wenig." in text(r)

    def test_ohne_gespeicherte_fassung_wartung(self, client, monkeypatch, settings):
        def down(*args, **kwargs):
            raise api.Unavailable("weg")

        monkeypatch.setattr(api, "_request", down)
        cache.clear()
        assert client.get("/impressum/").status_code == 503
        settings.MAINTENANCE = True
        assert client.get("/impressum/").status_code == 503

    def test_vorschau_wird_nicht_gespeichert(self, client, hubiplan, settings):
        hubiplan.maintenance = True
        client.get("/vorschau/?schluessel=gut")
        client.get("/impressum/")
        assert not list(Path(settings.LEGAL_ARCHIVE_DIR).glob("*.json"))


class TestKontakt:
    def test_senden_erst_mit_javascript(self, client, hubiplan):
        html = text(client.get("/kontakt/"))
        assert '<button class="knopf" type="submit" disabled>' in html
        assert 'id="k-ohne-js"' in html and "<noscript>" not in html
        assert 'data-neu="/kontakt/pruefung/"' in html

    def test_neue_aufgabe(self, client, hubiplan):
        r = client.get("/kontakt/pruefung/")
        assert r.status_code == 200
        assert r.json() == {"token": "tok", "salt": "salz", "difficulty": 16}
        assert r["Cache-Control"] == "private, no-store"

    def test_neue_aufgabe_ohne_kontakt(self, client, hubiplan):
        hubiplan.info["blocks"]["contact"] = False
        assert client.get("/kontakt/pruefung/").status_code == 404


class TestTermine:
    def test_anschrift_ohne_ort(self, client, hubiplan, monkeypatch):
        def ohne_ort(future="2099-06-01T18:00:00+02:00"):
            data = original(future)
            data["events"][0]["location"] = ""
            data["events"][0]["address"] = "Dorfstraße 1, 12345 Musterdorf"
            return data

        original = fake.events
        monkeypatch.setattr(fake, "events", ohne_ort)
        html = text(client.get("/termine/"))
        assert "Dorfstraße 1, 12345 Musterdorf</a>" in html
        assert "openstreetmap.org/search?query=Dorfstra" in html

    def test_einheit_ohne_termine_kein_terminblock(self, client, hubiplan, monkeypatch):
        monkeypatch.setattr(fake, "events", lambda future="": {"events": []})
        html = text(client.get("/zuege/jaeger/"))
        assert "Nächste Termine" not in html
        assert "Kalender abonnieren" not in html
        assert "?einheit=jaeger" not in html


@pytest.mark.parametrize(
    ("raw", "target"),
    [
        ("02131 12345", "0213112345"),
        ("+49 (0) 2131 / 12 34-5", "+49213112345"),
        ("0049 2131 12345", "+49213112345"),
        ("", ""),
        ("--", ""),
    ],
)
def test_telefon_ziel(raw, target):
    assert tel(raw) == target


def test_telefon_als_link(client, hubiplan, monkeypatch):
    holder = fake.BOARD["roles"][0]["holders"][0]
    monkeypatch.setitem(holder, "phone", "02131 / 12345")
    html = text(client.get("/vorstand/"))
    assert '<a href="tel:0213112345">02131 / 12345</a>' in html


def test_vorschau_beenden(client, hubiplan, settings):
    hubiplan.maintenance = True
    client.get("/vorschau/?schluessel=gut")
    r = client.get("/vorschau/ende/")
    assert r["Location"] == "/?vorschau=beendet"
    assert r.cookies["vorschau"].value == ""
    assert r["Cache-Control"] == "private, no-store"
    client.cookies.pop("vorschau")
    html = text(client.get("/impressum/?vorschau=beendet"))
    assert "Vorschau beendet." in html
