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


def test_unbelegte_felder_bleiben_ungeprueft():
    # Im Demoverein leer oder null: Die Form sagt nichts über den Inhalt
    daten = {"events": [{"registration": {"open": True}, "attachments": [{"name": "Plan"}]}]}
    assert schnittstelle.pruefe("GET", "/api/public/site/v1/abc/events/", 200, daten) == []
    assert schnittstelle.pruefe("GET", "/api/public/site/v1/abc/join/", 200, {"x": 1}) == []


def test_neue_abweichung_steht_nicht_im_bestand():
    neu = schnittstelle.pruefe("GET", "/api/public/site/v1/abc/repertoire/", 200, {"erfunden": 1})
    assert neu == ["repertoire/.erfunden: Feld gibt es im Server nicht"]
    assert not set(neu) & schnittstelle.BESTAND
    # Was im Bestand steht, gilt als bekannt
    assert "board/.roles[].holders[].email: Feld gibt es im Server nicht" in schnittstelle.BESTAND
    # Adressen ohne Schlüssel der Webseite zählen nicht als Grunddaten
    assert (
        schnittstelle.pruefe("GET", "/api/public/site/v1/resolve/?host=x", 200, {"key": "a"}) == []
    )


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


def test_skript_ist_gueltig():
    ergebnis = subprocess.run(  # noqa: S603
        ["bash", "-n", str(WURZEL / "scripts" / "schnittstelle.sh")],  # noqa: S607
        capture_output=True,
        check=False,
    )
    assert ergebnis.returncode == 0, ergebnis.stderr.decode()
    assert sys.version_info >= (3, 12)
