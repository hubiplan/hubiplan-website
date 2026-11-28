"""Echte Antworten von HUBIplan statt der Nachbildung.

``tests/data/hubiplan_antworten.json`` zeichnet der Server in seinen Tests auf (dort
``tests/webseite_form.py``; neu ziehen mit ``scripts/schnittstelle.sh``): alle Adressen der
öffentlichen Schnittstelle für mehrere Beispielvereine.

- ``demoverein``: der Demoverein, wie HUBIplan ihn anlegt
- ``pruefverein``: derselbe Verein, in dem jedes Feld der Schnittstelle belegt ist und jede
  Art von Abschnitt vorkommt
- ``pruefverein-vorschau``: der Prüfverein, wie ihn die Vorschau sieht (Entwürfe,
  Platzhalter für fehlende Bilder)
- ``demokapelle``: ein Musikverein
- ``leer``: ein Verein ohne Inhalte, alle Bereiche eingeschaltet

``EchtesHubiplan`` liefert diese Antworten anstelle von ``seite.api._request`` aus.
"""

from __future__ import annotations

import datetime
import json
from collections import Counter
from pathlib import Path

from seite import api

from .fake import PNG

DATEI = Path(__file__).parent / "data" / "hubiplan_antworten.json"
_DATEN = json.loads(DATEI.read_text(encoding="utf-8"))
AUFZEICHNUNG: list[dict] = _DATEN["antworten"]
# Zeitpunkt der Aufzeichnung: Termine der Beispiele liegen von dort aus in der Zukunft
STAND = datetime.datetime.fromisoformat(_DATEN["stand"])
BEISPIELE = sorted({a["beispiel"] for a in AUFZEICHNUNG})

# Adressen ohne JSON (Bilder, Dateien, Kalender): Die Aufzeichnung enthält sie nicht
DATEIEN = (
    "images/",
    "photos/",
    "honors/photos/",
    "posts/images/",
    "files/",
    "events/attachments/",
    "statute/preview/",
    "fee-rules/preview/",
    "founding-deed/preview/",
    "icon-",
)


# Angaben in der Abfrage, die eine andere Antwort wählen; Seitenzahl, Anzahl, Suchwort und
# Zeitraum ändern nur den Ausschnitt
WAEHLT = ("einheit", "section", "start")


def _schluessel(pfad: str) -> str:
    """Pfad mit den Angaben aus WAEHLT, in fester Reihenfolge."""
    ohne, _, abfrage = pfad.partition("?")
    teile = sorted(t for t in abfrage.split("&") if t.split("=", 1)[0] in WAEHLT)
    if ohne.endswith("bookings/"):
        teile = []  # ``start`` ist dort der erste Tag des Ausschnitts
    return ohne + ("?" + "&".join(teile) if teile else "")


class EchtesHubiplan:
    """Liefert die aufgezeichneten Antworten eines Beispiels aus."""

    def __init__(self, beispiel: str):
        eigene = [a for a in AUFZEICHNUNG if a["beispiel"] == beispiel]
        assert eigene, f"kein Beispiel {beispiel}"
        self.key = next(a["pfad"].split("/")[0] for a in eigene if a["adresse"] == "")
        self.antworten = {_schluessel(a["pfad"]): a["antwort"] for a in eigene}
        self.instanz = self.antworten.get("instance/")
        self.gefragt: Counter[str] = Counter()
        self.unbekannt: set[str] = set()

    def __call__(self, method, path, *, data=None, preview=None, base=None, stream_from=0):
        assert method == "GET", f"{method} {path}: die Aufzeichnung kennt nur Abrufe"
        if not path.startswith(api.PREFIX):
            return api.Response(200, PNG, "image/png")
        rest = path[len(api.PREFIX) :]
        if rest.startswith("resolve/"):
            return self._json({"key": self.key, "version": 1})
        if rest.startswith(f"{self.key}/") and rest[len(self.key) + 1 :].startswith(DATEIEN):
            return api.Response(200, PNG, "image/png")
        antwort = self.antworten.get(_schluessel(rest))
        if antwort is None:
            self.unbekannt.add(rest)
            return self._json({"detail": "nicht gefunden"}, 404)
        self.gefragt[_schluessel(rest)] += 1
        return self._json(antwort)

    @staticmethod
    def _json(daten, status=200):
        return api.Response(status, json.dumps(daten).encode(), "application/json")
