"""Die Adresse des Besuchers geht an HUBIplan, damit dort je Besucher gedrosselt wird."""

import io

import pytest
from django.test import RequestFactory

from seite import api, besucher


class _Antwort(io.BytesIO):
    status = 200
    headers = {"Content-Type": "application/json"}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def gesendet(monkeypatch):
    anfragen = []

    def urlopen(req, timeout=None):
        anfragen.append(req)
        return _Antwort(b"{}")

    monkeypatch.setattr(api.urllib.request, "urlopen", urlopen)
    return anfragen


def _mit_besucher(**meta):
    seen = []

    def view(request):
        api._request("GET", f"{api.PREFIX}schluessel/")
        api._request("GET", "/media/logos/wappen.png")
        seen.append(besucher.besucher())

    besucher.Besucher(view)(RequestFactory().get("/", **meta))
    return seen[0]


def test_adresse_des_proxys_wird_weitergereicht(gesendet):
    # Der vorgeschaltete Proxy hängt die Adresse an; was der Besucher selbst schickt, zählt nicht
    seen = _mit_besucher(HTTP_X_FORWARDED_FOR="198.51.100.1, 203.0.113.7")
    assert seen == "203.0.113.7"
    assert gesendet[0].get_header("X-hubiplan-besucher") == "203.0.113.7"
    # Hochgeladene Dateien liefert Caddy aus: dorthin geht die Angabe nicht
    assert gesendet[1].get_header("X-hubiplan-besucher") is None
    # nach der Anfrage ist nichts mehr gemerkt
    assert besucher.besucher() == ""


def test_ohne_proxy_adresse_der_verbindung(gesendet):
    assert _mit_besucher(REMOTE_ADDR="203.0.113.9") == "203.0.113.9"
    assert gesendet[0].get_header("X-hubiplan-besucher") == "203.0.113.9"


def test_unbrauchbare_angabe_wird_nicht_gesendet(gesendet):
    assert _mit_besucher(HTTP_X_FORWARDED_FOR="keine-adresse\r\nX-Böse: 1") == ""
    assert gesendet[0].get_header("X-hubiplan-besucher") is None


def test_ausserhalb_einer_anfrage_keine_angabe(gesendet):
    api._request("GET", f"{api.PREFIX}schluessel/")
    assert gesendet[0].get_header("X-hubiplan-besucher") is None


def test_mit_geheimnis_gilt_die_kopfzeile_nur_vom_proxy(gesendet, settings):
    """Gesamtaudit 13.11. S-05: Ein Nachbardienst am lokalen Port kann keine Adresse vorgeben."""
    settings.PROXY_GEHEIM = "ab" * 32
    # ohne Kopfwert: Adresse der Verbindung, die behauptete zählt nicht
    seen = _mit_besucher(HTTP_X_FORWARDED_FOR="203.0.113.7", REMOTE_ADDR="127.0.0.1")
    assert seen == "127.0.0.1"
    # falscher Kopfwert ebenso
    seen = _mit_besucher(
        HTTP_X_FORWARDED_FOR="203.0.113.7", REMOTE_ADDR="127.0.0.1", HTTP_X_HUBIPLAN_PROXY="falsch"
    )
    assert seen == "127.0.0.1"
    # der nginx mit Kopfwert
    seen = _mit_besucher(
        HTTP_X_FORWARDED_FOR="203.0.113.7",
        REMOTE_ADDR="127.0.0.1",
        HTTP_X_HUBIPLAN_PROXY="ab" * 32,
    )
    assert seen == "203.0.113.7"


def test_vertrauter_container_ohne_kopfwert(gesendet, settings):
    """Caddy von HUBIplan (Testserver, Unterpfad) reicht die Adresse ohne Kopfwert weiter."""
    settings.PROXY_GEHEIM = "ab" * 32
    settings.PROXY_HOSTS = ["172.18.0.5"]
    seen = _mit_besucher(HTTP_X_FORWARDED_FOR="203.0.113.7", REMOTE_ADDR="172.18.0.5")
    assert seen == "203.0.113.7"
    seen = _mit_besucher(HTTP_X_FORWARDED_FOR="203.0.113.7", REMOTE_ADDR="172.18.0.9")
    assert seen == "172.18.0.9"
