"""Zugriff auf die öffentliche Schnittstelle von HUBIplan (/api/public/site/v1/…).

Nur lesen (außer Vorschau-Tausch). Antworten werden kurz zwischengespeichert,
in der Vorschau nur wenige Sekunden und je Vorschau getrennt (sonst kostet jedes Bild
einen vollen Abruf der Grunddaten in HUBIplan).
"""

from __future__ import annotations

import hashlib
import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import quote, urlparse

from django.conf import settings
from django.core.cache import cache

log = logging.getLogger(__name__)

PREFIX = "/api/public/site/v1/"
MAX_FILE_BYTES = 20 * 1024 * 1024


class NotFound(Exception):
    """Gibt es nicht (oder nicht öffentlich)."""


class Unavailable(Exception):
    """HUBIplan ist gerade nicht erreichbar oder antwortet mit einem Fehler."""


class Maintenance(Exception):
    """Die Webseite ist im Wartungsmodus; ``data`` enthält die Wartungsangaben."""

    def __init__(self, data: dict):
        super().__init__("Wartung")
        self.data = data


@dataclass
class Response:
    status: int
    body: bytes
    content_type: str

    def json(self):
        return json.loads(self.body.decode() or "null")


def _request(
    method: str, path: str, *, data=None, preview: str | None = None, base: str | None = None
) -> Response:
    """Ein Aufruf an HUBIplan; ``path`` beginnt mit „/“ (z. B. /api/public/site/v1/…)."""
    base = base or settings.HUBIPLAN_API_URL
    url = base + path
    headers = {"Accept": "application/json", "User-Agent": "hubiplan-website"}
    if settings.HUBIPLAN_HOST and urlparse(base).hostname != settings.HUBIPLAN_HOST:
        # Interner Aufruf (z. B. http://backend:8000): HUBIplan erwartet seinen Hostnamen
        headers["Host"] = settings.HUBIPLAN_HOST
        headers["X-Forwarded-Proto"] = "https"
    if preview:
        headers["X-Preview-Session"] = preview
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)  # noqa: S310
    try:
        with urllib.request.urlopen(req, timeout=settings.API_TIMEOUT) as res:  # noqa: S310
            content = res.read(MAX_FILE_BYTES + 1)
            return Response(res.status, content, res.headers.get("Content-Type", ""))
    except urllib.error.HTTPError as exc:
        return Response(exc.code, exc.read(64 * 1024), exc.headers.get("Content-Type", ""))
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        log.warning("HUBIplan nicht erreichbar: %s", exc)
        raise Unavailable(str(exc)) from exc


def _key(*parts: str) -> str:
    return "api:" + hashlib.sha256("\x00".join(parts).encode()).hexdigest()


def resolve(host: str) -> str:
    """Schlüssel der Webseite zu einem Hostnamen."""
    ck = _key("resolve", host)
    cached = cache.get(ck)
    if cached is not None:
        if cached == "":
            raise NotFound(host)
        return cached
    res = _request("GET", f"{PREFIX}resolve/?host={quote(host)}")
    if res.status == 404:
        cache.set(ck, "", 60)
        raise NotFound(host)
    if res.status != 200:
        raise Unavailable(f"resolve {res.status}")
    key = res.json()["key"]
    cache.set(ck, key, 300)
    return key


def get(
    key: str,
    path: str = "",
    *,
    preview: str | None = None,
    cached: bool = True,
    seconds: int | None = None,
):
    """JSON einer Adresse der Webseite, z. B. ``board/``. 503 → Maintenance.

    ``seconds``: eigene, kürzere Zwischenspeicherung (z. B. Stand laufender Wettbewerbe)."""
    full = f"{PREFIX}{key}/{path}"
    use_cache = cached and (not preview or settings.PREVIEW_CACHE_SECONDS > 0)
    ck = _key("get", full, preview or "")
    ttl = seconds or settings.CACHE_SECONDS
    if preview:
        ttl = min(ttl, settings.PREVIEW_CACHE_SECONDS)
    if use_cache:
        hit = cache.get(ck)
        if hit is not None:
            status, data = hit
            return _result(status, data)
    res = _request("GET", full, preview=preview)
    if res.status >= 500 and res.status != 503:
        raise Unavailable(f"{path} {res.status}")
    try:
        data = res.json()
    except ValueError as exc:
        raise Unavailable(f"{path}: keine JSON-Antwort") from exc
    if use_cache and res.status in (200, 404, 503):
        cache.set(ck, (res.status, data), ttl)
    return _result(res.status, data)


def _result(status: int, data):
    if status == 404:
        raise NotFound()
    if status == 503:
        raise Maintenance(data or {})
    if status != 200:
        raise Unavailable(str(status))
    return data


def post(key: str, path: str, data: dict, *, preview: str | None = None) -> Response:
    return _request("POST", f"{PREFIX}{key}/{path}", data=data, preview=preview)


def fetch_file(path: str, *, preview: str | None = None) -> Response:
    """Datei (Bild) aus HUBIplan; ``path`` ist der Pfad ab der Wurzel von HUBIplan.

    Hochgeladene Dateien (/media/…) liefert auf dem Server Caddy aus, nicht das
    Backend: Dafür gilt HUBIPLAN_MEDIA_URL.
    """
    base = settings.HUBIPLAN_MEDIA_URL if path.startswith("/media/") else None
    res = _request("GET", path, preview=preview, base=base)
    if res.status == 404:
        raise NotFound(path)
    if res.status != 200 or len(res.body) > MAX_FILE_BYTES:
        raise Unavailable(f"{path} {res.status}")
    return res
