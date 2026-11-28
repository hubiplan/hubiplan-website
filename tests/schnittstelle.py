"""Abgleich der nachgebildeten Schnittstelle (``tests/fake.py``) mit HUBIplan.

``tests/data/hubiplan_schnittstelle.json`` ist eine Kopie aus dem Server (Adressen unter
``/api/public/site/v1/`` und die Form der Antworten; neu ziehen mit
``scripts/schnittstelle.sh``). Der Server legt dafür in seinen Tests einen Prüfverein an, der
jedes Feld belegt und jede Art von Abschnitt zeigt; die Form ist deshalb vollständig. Geprüft
wird bei jedem Aufruf der Nachbildung in den Tests:

- Die Adresse gibt es im Server.
- Die Antwort der Nachbildung hat nur Felder, die der Server auch liefert, und Werte der
  Art, die der Server liefert. So fällt auf, wenn die Webseite sich auf ein Feld verlässt,
  das es im Server nicht (mehr) gibt.

Ausnahmen gibt es keine. Tests, die absichtlich liefern, was HUBIplan nie liefert (kaputte
oder böswillige Antworten), tragen den Merker ``falsche_daten`` (tests/conftest.py).

Die Gegenrichtung prüft ``tests/test_echte_antworten.py``: Jede Seite wird aus den echten
Antworten des Servers gezeichnet (``tests/echt.py``).
"""

from __future__ import annotations

import json
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


NUMMER = re.compile(r"^(\w+):\d+$")


def abweichungen(wert, form, weg: str) -> list[str]:
    """Felder und Arten in ``wert``, die die Form des Servers nicht kennt.

    Form wie im Server (``tests/webseite_form.py``): Text mit Arten („text|null“), Liste mit
    der Form ihrer Einträge, Objekt mit Feldern; bei mehreren Bauarten stehen die einfachen
    Arten unter „?“ und die Liste unter „?liste“."""
    if wert is None:
        # ``null`` darf die Nachbildung überall liefern: Das prüft die Webseite nur strenger
        return []
    if isinstance(form, str):
        return [] if _art(wert) in form.split("|") else [f"{weg}: {_art(wert)} statt {form}"]
    if isinstance(form, list):
        if not isinstance(wert, list):
            return [f"{weg}: {_art(wert)} statt Liste"]
        if not form:
            return [f"{weg}: Liste ist im Server immer leer"] if wert else []
        return [a for eintrag in wert for a in abweichungen(eintrag, form[0], weg + "[]")]
    einfach = form.get("?")
    if isinstance(wert, list):
        if "?liste" not in form:
            return [f"{weg}: Liste statt Objekt"]
        return abweichungen(wert, form["?liste"], weg)
    if not isinstance(wert, dict):
        if einfach and _art(wert) in einfach.split("|"):
            return []
        return [f"{weg}: {_art(wert)} statt {einfach or 'Objekt'}"]
    out = []
    if "*" in form:
        # Zuordnung mit freien Schlüsseln: alle Werte haben dieselbe Form
        return [a for k, v in wert.items() for a in abweichungen(v, form["*"], f"{weg}.{k}")]
    for feld, inhalt in wert.items():
        name = NUMMER.sub(r"\1:<nr>", feld)
        if name not in form or name in ("?", "?liste"):
            out.append(f"{weg}.{feld}: Feld gibt es im Server nicht")
        else:
            out += abweichungen(inhalt, form[name], f"{weg}.{feld}")
    return out


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
