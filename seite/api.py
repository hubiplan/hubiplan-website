"""Zugriff auf die öffentliche Schnittstelle von HUBIplan (/api/public/site/v1/…).

Nur lesen (außer Vorschau-Tausch). Antworten werden kurz zwischengespeichert,
in der Vorschau nur wenige Sekunden und je Vorschau getrennt (sonst kostet jedes Bild
einen vollen Abruf der Grunddaten in HUBIplan).
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import quote, urlparse

from django.conf import settings
from django.core.cache import cache, caches

from .besucher import besucher

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
    visitor = besucher()
    if visitor and path.startswith("/api/"):
        # HUBIplan drosselt je Besucher, nicht alle Besucher zusammen als diesen Dienst
        headers["X-Hubiplan-Besucher"] = visitor
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
    return "api2:" + hashlib.sha256("\x00".join(parts).encode()).hexdigest()


def resolve(host: str) -> str:
    """Schlüssel der Webseite zu einem Hostnamen.

    Ist HUBIplan nicht erreichbar (z. B. beim Ausrollen), gilt die letzte bekannte
    Zuordnung weiter (bis ``STALE_IF_ERROR_SECONDS``)."""
    ck = _key("resolve", host)
    cached = cache.get(ck)
    if cached == "":
        raise NotFound(host)
    if isinstance(cached, tuple) and 0 <= _now() - cached[0] < RESOLVE_SECONDS:
        return cached[1]
    try:
        res = _request("GET", f"{PREFIX}resolve/?host={quote(host)}")
    except Unavailable:
        if isinstance(cached, tuple):
            return cached[1]
        raise
    if res.status == 404:
        cache.set(ck, "", 60)
        raise NotFound(host)
    if res.status != 200:
        if isinstance(cached, tuple) and res.status in (429, 502, 504):
            return cached[1]
        raise Unavailable(f"resolve {res.status}")
    key = res.json()["key"]
    cache.set(ck, (_now(), key), settings.STALE_IF_ERROR_SECONDS)
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
    # Preview permissions and revocation are checked on every request.
    use_cache = cached and not preview
    ck = _key("get", full, preview or "")
    ttl = seconds or settings.CACHE_SECONDS
    if not use_cache:
        return _result(*_fetch(full, path, preview))
    hit = cache.get(ck)
    age = _now() - hit[0] if hit is not None else None
    if hit is not None and 0 <= age < ttl:
        return _result(*hit[1])
    lock = _lock_for(ck)
    if hit is not None and 0 <= age < ttl + STALE_SECONDS:
        # Abgelaufen, aber noch recht frisch: Der Besucher bekommt sofort den letzten Stand,
        # neu geholt wird im Hintergrund (Ladezeiten 14.11., sonst wartet nach einer
        # Ruhepause der erste Besucher 0,25 bis 0,5 s). Holt schon ein anderer Thread,
        # bleibt es beim alten Stand, statt HUBIplan doppelt zu fragen.
        if not lock.acquire(blocking=False):
            return _result(*hit[1])
        if settings.REFRESH_IN_BACKGROUND:
            try:
                threading.Thread(
                    target=_refresh, args=(ck, full, path, hit, ttl, lock), daemon=True
                ).start()
            except RuntimeError:  # kein Thread möglich: Sperre freigeben, Stand bleibt
                lock.release()
            return _result(*hit[1])
    elif not lock.acquire(timeout=settings.API_TIMEOUT):
        return _result(*_fetch_or_stale(full, path, hit)[0])
    try:
        again = cache.get(ck)
        if again is not None and 0 <= _now() - again[0] < ttl:
            return _result(*again[1])
        result, fresh = _fetch_or_stale(full, path, again or hit)
        if fresh and result[0] in (200, 404, 503):
            cache.set(ck, (_now(), result), settings.STALE_IF_ERROR_SECONDS)
        return _result(*result)
    finally:
        lock.release()


def _refresh(ck: str, full: str, path: str, hit, ttl: int, lock: threading.Lock) -> None:
    """Abgelaufenen Stand im Hintergrund neu holen (``lock`` ist schon gehalten)."""
    try:
        again = cache.get(ck)
        if again is not None and 0 <= _now() - again[0] < ttl:
            return
        result, fresh = _fetch_or_stale(full, path, again or hit)
        if fresh and result[0] in (200, 404, 503):
            cache.set(ck, (_now(), result), settings.STALE_IF_ERROR_SECONDS)
    except Exception:  # Hintergrund: der nächste Aufruf versucht es wieder
        log.warning("Neu holen im Hintergrund fehlgeschlagen: %s", path, exc_info=True)
    finally:
        lock.release()


def _fetch_or_stale(full: str, path: str, hit) -> tuple[tuple[int, object], bool]:
    """Neu holen; ist HUBIplan nicht erreichbar (Ausrollen, Neustart), den letzten guten
    Stand liefern statt einer Fehlerseite. Wartung (503) und „gibt es nicht“ (404) kommen
    von HUBIplan selbst und wirken daher sofort, sobald es wieder antwortet."""
    try:
        return _fetch(full, path, None), True
    except Unavailable:
        if hit is None:
            raise
        log.warning("HUBIplan nicht erreichbar, Stand von vor %d s: %s", _now() - hit[0], path)
        return hit[1], False


def _now() -> float:
    # Wanduhr statt monotonic: Der Zwischenspeicher liegt auf der Platte und übersteht
    # Neustarts des Containers (negative Alter gelten als abgelaufen)
    return time.time()


# So lange nach Ablauf dient der letzte Stand noch, während im Hintergrund neu geholt wird
# (bis 14.11. 600 s und nur für gleichzeitige Aufrufe). Danach wartet der Aufruf auf HUBIplan.
# Mit CACHE_SECONDS zusammen höchstens 15 Minuten (Fachfrage 10 zum Gesamtaudit 10.11.).
STALE_SECONDS = 780
# Zuordnung Hostname → Webseite so lange ohne Rückfrage
RESOLVE_SECONDS = 300
_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _lock_for(ck: str) -> threading.Lock:
    with _locks_guard:
        if len(_locks) > 2000:
            _locks.clear()
        return _locks.setdefault(ck, threading.Lock())


def _fetch(full: str, path: str, preview: str | None) -> tuple[int, object]:
    res = _request("GET", full, preview=preview)
    # 429: HUBIplan drosselt gerade; wie ein Ausfall zählt dann der letzte gute Stand
    if res.status == 429 or (res.status >= 500 and res.status != 503):
        raise Unavailable(f"{path} {res.status}")
    try:
        return res.status, res.json()
    except ValueError as exc:
        raise Unavailable(f"{path}: keine JSON-Antwort") from exc


def cached_maintenance(key: str) -> bool:
    """Steht die Webseite laut zwischengespeicherten Grunddaten in Wartung? Ruft
    HUBIplan nicht auf; unbekannt gilt als nein."""
    hit = cache.get(_key("get", f"{PREFIX}{key}/", ""))
    return bool(hit) and hit[1][0] == 503


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

    Ohne Vorschau bleibt eine Kopie (bis ``STALE_IMAGE_MAX_BYTES``) im Zwischenspeicher
    „bilder“. Sie wird nur ausgeliefert, wenn HUBIplan nicht erreichbar ist (Ausrollen);
    ob ein Bild gezeigt werden darf, entscheidet sonst immer HUBIplan.
    """
    base = settings.HUBIPLAN_MEDIA_URL if path.startswith("/media/") else None
    store = None if preview else caches["bilder"]
    ck = _key("datei", path)
    try:
        res = _request("GET", path, preview=preview, base=base)
    except Unavailable:
        stale = store.get(ck) if store is not None else None
        if stale is not None:
            return stale
        raise
    if res.status == 404:
        if store is not None:
            store.delete(ck)
        raise NotFound(path)
    if res.status in (429, 502, 504) and store is not None:
        stale = store.get(ck)
        if stale is not None:
            return stale
    if res.status != 200 or len(res.body) > MAX_FILE_BYTES:
        raise Unavailable(f"{path} {res.status}")
    if store is not None and len(res.body) <= settings.STALE_IMAGE_MAX_BYTES:
        # Nur anlegen, nicht bei jedem Abruf neu schreiben: geänderte Bilder bekommen in
        # HUBIplan eine neue Adresse (Fassung bzw. Zeitstempel im Pfad)
        store.add(ck, res)
    return res
