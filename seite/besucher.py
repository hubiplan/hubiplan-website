"""Adresse des Besuchers der laufenden Anfrage, für die Drosselung in HUBIplan.

HUBIplan zählt Abrufe der öffentlichen Schnittstelle je Adresse. Ohne diese Angabe zählten
alle Besucher aller Webseiten zusammen als dieser Dienst, und ein einzelner Besucher am Limit
sperrte alle anderen aus. Die Adresse wird nur weitergereicht, nicht gespeichert.
"""

from __future__ import annotations

import hmac
import ipaddress
import socket
import threading
import time
from contextvars import ContextVar

from django.conf import settings

_besucher: ContextVar[str] = ContextVar("besucher", default="")

PROXY_HEADER = "HTTP_X_HUBIPLAN_PROXY"
# Namensauflösung der vertrauten Container: so lange gilt ein Ergebnis
_AUFLOESEN_SEKUNDEN = 60
_NEU_VERSUCHEN_SEKUNDEN = 2
_bekannt: dict[tuple[str, ...], tuple[float, float, frozenset[str]]] = {}
_sperre = threading.Lock()


def besucher() -> str:
    return _besucher.get()


def _aufloesen(namen: tuple[str, ...]) -> frozenset[str]:
    gefunden: set[str] = set()
    for name in namen:
        try:
            gefunden.add(str(ipaddress.ip_address(name)))
            continue
        except ValueError:
            pass
        try:
            gefunden.update(info[4][0] for info in socket.getaddrinfo(name, None))
        except OSError:
            continue
    return frozenset(gefunden)


def _adressen(namen, verbindung: str) -> frozenset[str]:
    """Adressen der vertrauten Container im Docker-Netz (kurz gemerkt)."""
    key = tuple(namen)
    jetzt = time.monotonic()
    treffer = _bekannt.get(key)
    if treffer is not None:
        geladen, versucht, adressen = treffer
        if verbindung in adressen and jetzt - geladen < _AUFLOESEN_SEKUNDEN:
            return adressen
        if verbindung not in adressen and jetzt - versucht < _NEU_VERSUCHEN_SEKUNDEN:
            return adressen
    with _sperre:
        adressen = _aufloesen(key)
        if not adressen and treffer is not None:
            adressen = treffer[2]  # Auflösung gerade gestört: letzter Stand gilt weiter
        _bekannt[key] = (jetzt, jetzt, adressen)
    return adressen


def vom_proxy(request) -> bool:
    """Darf diese Anfrage die Besucheradresse in X-Forwarded-For nennen?

    Hinter HestiaCP lauscht der Dienst auf einem lokalen Port, den auf einem geteilten Server
    auch Nachbardienste erreichen. Sie könnten sonst je Aufruf eine andere Adresse vorgeben
    und so jede Grenze je Besucher umgehen oder fremde Adressen aussperren lassen
    (Gesamtaudit 13.11. S-05). Ohne Einstellung (Entwicklung, Tests) gilt jede Anfrage.
    """
    geheim = getattr(settings, "PROXY_GEHEIM", "")
    namen = getattr(settings, "PROXY_HOSTS", None) or []
    if not geheim and not namen:
        return True
    if geheim and hmac.compare_digest(request.META.get(PROXY_HEADER, "").encode(), geheim.encode()):
        return True
    verbindung = request.META.get("REMOTE_ADDR", "")
    return bool(namen) and verbindung in _adressen(namen, verbindung)


def adresse(request) -> str:
    """Adresse laut vorgeschaltetem Proxy (letzter Eintrag in X-Forwarded-For, den der Proxy
    selbst anhängt), sonst die der Verbindung. Leer, wenn es keine gültige Adresse ist."""
    value = request.META.get("REMOTE_ADDR", "")
    if vom_proxy(request):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        if parts:
            value = parts[-1]
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        return ""


class Besucher:
    """Merkt sich die Adresse für die Dauer der Anfrage (seite/api.py reicht sie weiter)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = _besucher.set(adresse(request))
        try:
            return self.get_response(request)
        finally:
            _besucher.reset(token)
