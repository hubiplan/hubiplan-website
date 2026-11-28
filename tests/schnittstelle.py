"""Abgleich der nachgebildeten Schnittstelle (``tests/fake.py``) mit HUBIplan.

``tests/data/hubiplan_schnittstelle.json`` ist eine Kopie aus dem Server (Adressen unter
``/api/public/site/v1/`` und die Form der Antworten für den Demoverein; neu ziehen mit
``scripts/schnittstelle.sh``). Geprüft wird bei jedem Aufruf der Nachbildung in den Tests:

- Die Adresse gibt es im Server.
- Die Antwort der Nachbildung hat nur Felder, die der Server auch liefert, und Werte der
  Art, die der Server liefert. So fällt auf, wenn die Webseite sich auf ein Feld verlässt,
  das es im Server nicht (mehr) gibt.

Was der Demoverein nicht belegt (leere Listen, ``null``, Adressen unter ``ohne_beispiel``),
bleibt ungeprüft. Felder, die die Nachbildung schon hatte, als der Abgleich kam, stehen in
``tests/data/schnittstelle_bestand.txt``: meist Felder, die HUBIplan nur bei bestimmten
Einstellungen liefert und die der Demoverein deshalb nicht zeigt. Neue Abweichungen lassen
den Test scheitern; der Bestand soll kleiner werden, wenn das Beispiel im Server wächst
(neu schreiben: ``scripts/schnittstelle.sh --bestand``).
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

DATEN = json.loads(
    (Path(__file__).parent / "data" / "hubiplan_schnittstelle.json").read_text(encoding="utf-8")
)
ROUTEN = [re.compile(muster) for muster in DATEN["routen"]]
ANTWORTEN: dict[str, object] = DATEN["antworten"]
PREFIX = "/api/public/site/v1/"

# Adresse der Antwort (wie in der Datei) → Muster des Pfads hinter dem Schlüssel
VORLAGEN = {
    name: re.compile(
        "^"
        + re.sub(r"<\w+>", "[^/]+", re.escape(name).replace(r"\<", "<").replace(r"\>", ">"))
        + "$"
    )
    for name in ANTWORTEN
    if name != "instance/"
}

BESTAND_DATEI = Path(__file__).parent / "data" / "schnittstelle_bestand.txt"
BESTAND = {
    zeile
    for zeile in BESTAND_DATEI.read_text(encoding="utf-8").splitlines()
    if zeile and not zeile.startswith("#")
}


def adresse_bekannt(pfad: str) -> bool:
    """Gibt es die Adresse (ohne Abfrage) im Server?"""
    ohne = pfad.split("?", 1)[0].lstrip("/")
    return any(muster.match(ohne) for muster in ROUTEN)


def vorlage_zu(rest: str) -> str | None:
    """Name der Antwort in der Datei zum Pfad hinter dem Schlüssel (ohne Abfrage)."""
    rest = rest.split("?", 1)[0]
    if rest in ANTWORTEN:
        return rest
    for name, muster in VORLAGEN.items():
        if muster.match(rest):
            return name
    return None


def _art(wert) -> str:
    if wert is None:
        return "null"
    if isinstance(wert, bool):
        return "bool"
    if isinstance(wert, (int, float)):
        return "zahl"
    if isinstance(wert, str):
        return "text"
    return "bau"


def abweichungen(wert, form, weg: str) -> list[str]:
    """Felder und Arten in ``wert``, die die Form des Servers nicht kennt."""
    if isinstance(form, str):
        arten = set(form.split("|"))
        # Nur „null“ oder „fehlt“ im Beispiel: der Demoverein belegt das Feld nicht
        if arten <= {"null", "fehlt"} or wert is None:
            return []
        return [] if _art(wert) in arten else [f"{weg}: {_art(wert)} statt {form}"]
    if isinstance(form, list):
        if not form or wert is None:
            return []
        if not isinstance(wert, list):
            return [f"{weg}: {_art(wert)} statt Liste"]
        return [a for eintrag in wert for a in abweichungen(eintrag, form[0], weg + "[]")]
    if isinstance(form, dict):
        if "auswahl" in form:
            return min((abweichungen(wert, f, weg) for f in form["auswahl"]), key=len)
        if "?" in form:
            if not isinstance(wert, (dict, list)):
                return abweichungen(wert, form["?"], weg)
            form = form["form"] if "form" in form else {k: v for k, v in form.items() if k != "?"}
            return abweichungen(wert, form, weg)
        if wert is None:
            return []
        if not isinstance(wert, dict):
            return [f"{weg}: {_art(wert)} statt Objekt"]
        out = []
        for feld, inhalt in wert.items():
            if feld not in form:
                out.append(f"{weg}.{feld}: Feld gibt es im Server nicht")
            else:
                out += abweichungen(inhalt, form[feld], f"{weg}.{feld}")
        return out
    return []


def pruefe(method: str, pfad: str, status: int, daten) -> list[str]:
    """Abweichungen eines Aufrufs der Nachbildung (leer = passt)."""
    if not pfad.startswith("/api/"):
        return []
    if not adresse_bekannt(pfad):
        return [f"{pfad}: Adresse gibt es im Server nicht"]
    if method != "GET" or status != 200 or not isinstance(daten, (dict, list)):
        return []
    rest = pfad[len(PREFIX) :].split("?", 1)[0]
    if rest in ("instance/", "resolve/"):
        # Ohne Schlüssel der Webseite
        name = rest
    else:
        teile = rest.split("/", 1)
        name = vorlage_zu(teile[1]) if len(teile) == 2 else None
    if name is None or name not in ANTWORTEN:
        return []
    return abweichungen(daten, ANTWORTEN[name], name or "/")


def neue_abweichungen(method: str, pfad: str, status: int, daten) -> list[str]:
    """Abweichungen, die nicht im Bestand stehen. Mit ``SCHNITTSTELLE_LOG`` werden alle
    Abweichungen in diese Datei geschrieben (zum Neuschreiben des Bestands)."""
    alle = pruefe(method, pfad, status, daten)
    ziel = os.environ.get("SCHNITTSTELLE_LOG")
    if ziel and alle:
        with open(ziel, "a", encoding="utf-8") as datei:
            datei.write("\n".join(alle) + "\n")
    return [a for a in alle if a not in BESTAND]
