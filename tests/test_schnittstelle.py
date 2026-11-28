"""Der Abgleich mit HUBIplan (tests/schnittstelle.py) erkennt Abweichungen."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from . import schnittstelle

WURZEL = Path(__file__).resolve().parents[1]
SERVER = WURZEL.parent / "hubiplan" / "backend" / "config"


def test_unbekannte_adresse_faellt_auf():
    assert schnittstelle.pruefe("GET", "/api/public/site/v1/abc/gibt-es-nicht/", 200, {}) == [
        "/api/public/site/v1/abc/gibt-es-nicht/: Adresse gibt es im Server nicht"
    ]
    assert schnittstelle.pruefe("GET", "/api/public/site/v1/abc/board/?x=1", 200, {}) == []
    assert schnittstelle.pruefe("GET", "/media/logos/wappen.png", 200, None) == []


def test_unbekanntes_feld_und_falsche_art_fallen_auf():
    gut = {"events": [{"title": "Sommerfest", "all_day": False}], "ics_url": "/x.ics"}
    assert schnittstelle.pruefe("GET", "/api/public/site/v1/abc/events/", 200, gut) == []
    falsch = {"events": [{"titel": "Sommerfest", "all_day": "nein"}]}
    assert schnittstelle.pruefe("GET", "/api/public/site/v1/abc/events/", 200, falsch) == [
        "events/.events[].titel: Feld gibt es im Server nicht",
        "events/.events[].all_day: text statt bool",
    ]


def test_jedes_feld_ist_belegt():
    """Der Prüfverein im Server belegt jedes Feld: Auch tief verschachtelte Felder werden
    geprüft, und keine Adresse bleibt ohne Beispiel."""
    daten = {"events": [{"registration": {"offen": True}, "attachments": [{"titel": "Plan"}]}]}
    assert schnittstelle.pruefe("GET", "/api/public/site/v1/abc/events/", 200, daten) == [
        "events/.events[].registration.offen: Feld gibt es im Server nicht",
        "events/.events[].attachments[].titel: Feld gibt es im Server nicht",
    ]
    assert schnittstelle.pruefe("GET", "/api/public/site/v1/abc/join/", 200, {"x": 1}) == [
        "join/.x: Feld gibt es im Server nicht"
    ]
    assert schnittstelle.DATEN["ohne_beispiel"] == []


def test_null_und_freie_schluessel():
    # ``null`` darf die Nachbildung überall liefern (die Webseite muss damit umgehen)
    leer = {"events": None}
    assert schnittstelle.pruefe("GET", "/api/public/site/v1/abc/events/", 200, leer) == []
    # Zuordnungen mit freien Schlüsseln (Name des Designs, Bereich): Die Werte werden geprüft
    falsch = {"intros": {"irgendein-bereich": {"titel": "x"}}}
    assert schnittstelle.pruefe("GET", "/api/public/site/v1/abc/", 200, falsch) == [
        "/.intros.irgendein-bereich.titel: Feld gibt es im Server nicht"
    ]
    # Adressen ohne Schlüssel der Webseite
    ziel = {"key": "a"}
    assert schnittstelle.pruefe("GET", "/api/public/site/v1/resolve/?host=x", 200, ziel) == []


def test_kopie_passt_zum_server_im_nachbarordner():
    """Liegt ein hubiplan-Klon daneben, muss die Kopie zu ihm passen (scripts/schnittstelle.sh)."""
    if not (SERVER / "webseite_schnittstelle.json").exists():
        pytest.skip("kein hubiplan-Klon im Nachbarordner")
    routen = json.loads((SERVER / "api_routen.json").read_text(encoding="utf-8"))
    form = json.loads((SERVER / "webseite_schnittstelle.json").read_text(encoding="utf-8"))
    assert schnittstelle.DATEN == {
        "routen": sorted(r for r in routen if r.startswith("^api/public/site/v1/")),
        "antworten": form["antworten"],
        "ohne_beispiel": form["ohne_beispiel"],
    }, "tests/data/hubiplan_schnittstelle.json ist veraltet: scripts/schnittstelle.sh ausführen"
    echt = json.loads((SERVER / "webseite_antworten.json").read_text(encoding="utf-8"))
    kopie = json.loads((WURZEL / "tests/data/hubiplan_antworten.json").read_text(encoding="utf-8"))
    assert kopie == echt, (
        "tests/data/hubiplan_antworten.json ist veraltet: scripts/schnittstelle.sh ausführen"
    )


def test_skript_ist_gueltig():
    ergebnis = subprocess.run(  # noqa: S603
        ["bash", "-n", str(WURZEL / "scripts" / "schnittstelle.sh")],  # noqa: S607
        capture_output=True,
        check=False,
    )
    assert ergebnis.returncode == 0, ergebnis.stderr.decode()
    assert sys.version_info >= (3, 12)
