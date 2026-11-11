"""Adresse des Besuchers der laufenden Anfrage, für die Drosselung in HUBIplan.

HUBIplan zählt Abrufe der öffentlichen Schnittstelle je Adresse. Ohne diese Angabe zählten
alle Besucher aller Webseiten zusammen als dieser Dienst, und ein einzelner Besucher am Limit
sperrte alle anderen aus. Die Adresse wird nur weitergereicht, nicht gespeichert.
"""

from __future__ import annotations

import ipaddress
from contextvars import ContextVar

_besucher: ContextVar[str] = ContextVar("besucher", default="")


def besucher() -> str:
    return _besucher.get()


def adresse(request) -> str:
    """Adresse laut vorgeschaltetem Proxy (letzter Eintrag in X-Forwarded-For, den der Proxy
    selbst anhängt), sonst die der Verbindung. Leer, wenn es keine gültige Adresse ist."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    parts = [p.strip() for p in forwarded.split(",") if p.strip()]
    value = parts[-1] if parts else request.META.get("REMOTE_ADDR", "")
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
