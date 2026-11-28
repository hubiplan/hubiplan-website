"""Jede Seite der Webseite aus echten Antworten von HUBIplan (tests/echt.py).

Die Nachbildung (tests/fake.py) zeigt, was die Tests brauchen; hier kommt, was der Server
wirklich liefert: Von der Startseite aus wird jeder Link der Webseite verfolgt. Jede Seite muss
sich zeichnen lassen, mit strengem Lesen der Daten (``STRENGE_DATEN``, seite/daten.py), und
jede Adresse, die HUBIplan für das Beispiel aufgezeichnet hat, muss dabei gefragt worden sein.
"""

import re

import pytest
from django.core.cache import cache, caches
from django.utils import timezone

from seite import api, designpaket

from . import echt, schnittstelle

LINK = re.compile(r'(?:href|src)="(/[^"#]*)')
# Dateien und Bilder (durchgereicht), Kalender, Stile; Formulare und die Vorschau-Anmeldung
OHNE = re.compile(
    r"^/(medien|static|design|design-paket|vorschau|kontakt/pruefung)(/|$)|\.(ics|css|png|ico|zip|txt|xml)$"
)


@pytest.fixture
def echtes(monkeypatch, settings):
    def mit(beispiel: str) -> echt.EchtesHubiplan:
        quelle = echt.EchtesHubiplan(beispiel)
        monkeypatch.setattr(api, "_request", quelle)
        for name in ("default", "bilder", "varianten"):
            caches[name].clear()
        designpaket._compiled.clear()
        return quelle

    assert settings.STRENGE_DATEN
    # Uhr auf den Zeitpunkt der Aufzeichnung: Sonst wären die Termine der Beispiele irgendwann
    # vorbei, und ihre Seiten stünden nicht mehr im Kalender
    monkeypatch.setattr(timezone, "now", lambda: echt.STAND)
    yield mit
    cache.clear()


def _alle_seiten(client) -> dict[str, int]:
    """Verfolgt von der Startseite aus jeden Link; Adresse → Status."""
    # Die Suche erreicht man nur über das Formular
    offen, gesehen = ["/suche/?q=Muster", "/"], {}
    while offen:
        pfad = offen.pop()
        if pfad in gesehen:
            continue
        antwort = client.get(pfad)
        gesehen[pfad] = antwort.status_code
        if antwort.status_code in (301, 302):
            ziel = antwort["Location"]
            if ziel.startswith("/"):
                offen.append(ziel)
            continue
        if antwort.status_code != 200 or "html" not in antwort["Content-Type"]:
            continue
        for ziel in LINK.findall(antwort.content.decode()):
            ziel = ziel.replace("&amp;", "&")
            if not OHNE.search(ziel.split("?")[0]):
                offen.append(ziel)
    return gesehen


@pytest.mark.parametrize("beispiel", echt.BEISPIELE)
def test_jede_seite_laesst_sich_zeichnen(client, echtes, beispiel):
    quelle = echtes(beispiel)
    seiten = _alle_seiten(client)
    kaputt = {pfad: status for pfad, status in seiten.items() if status not in (200, 301, 302)}
    assert not kaputt, f"{beispiel}: {kaputt}"
    # auch ein leerer Verein hat Startseite, Kontakt, Impressum, Datenschutz …
    assert len(seiten) >= 8, seiten
    # Kein Link führt zu einer Adresse, die HUBIplan für dieses Beispiel nicht hat
    assert not quelle.unbekannt, f"{beispiel}: nicht aufgezeichnet: {sorted(quelle.unbekannt)}"


KENNUNG = re.compile(r"/results/(series/)?[a-f0-9]{20}/")

# Adressen, die keine Seite der Webseite liest (mit Grund)
NICHT_GELESEN = {
    # Eigenschaften der Instanz: nur für die Apps
    "instance/",
    # Hostname → Schlüssel: beantwortet tests/echt.py selbst
    "resolve/",
    # Die Untereinheiten nimmt die Webseite aus den Grunddaten
    "units/",
    # Einleitung der Gedenkseite: liefert memorial/ gleich mit
    "pages/in-gedenken/",
}


@pytest.mark.parametrize("beispiel", ["pruefverein"])
def test_jede_aufgezeichnete_antwort_wird_gelesen(client, echtes, beispiel):
    """Was der Server liefert, zeigt die Webseite auch irgendwo: Jede Adresse des Prüfvereins
    wird beim Durchgehen aller Seiten mindestens einmal gefragt."""
    quelle = echtes(beispiel)
    _alle_seiten(client)
    ohne = {
        pfad
        for pfad, antwort in quelle.antworten.items()
        if pfad not in quelle.gefragt
        and pfad.removeprefix(f"{quelle.key}/") not in NICHT_GELESEN
        # Beiträge einer Untereinheit fragt die Webseite nur, wenn die Einheit welche hat
        and not ("posts/?einheit=" in pfad and not antwort["posts"])
        # Ergebnisse gibt es unter Kurzname und Kennung; die Webseite nimmt den Kurznamen
        and not KENNUNG.search(pfad)
    }
    assert not ohne, sorted(ohne)


def test_echte_antworten_passen_zur_form():
    """Die Aufzeichnung und die Form stammen aus demselben Lauf des Servers."""
    for eintrag in echt.AUFZEICHNUNG:
        abweichungen = schnittstelle.abweichungen(
            eintrag["antwort"],
            schnittstelle.ANTWORTEN[eintrag["adresse"]],
            eintrag["adresse"] or "/",
        )
        assert not abweichungen, (eintrag["beispiel"], eintrag["pfad"], abweichungen[:5])
