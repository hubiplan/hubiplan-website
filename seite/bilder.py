"""Bildfassungen für schnellere Ladezeiten (Messung 14.11.2026).

HUBIplan liefert Webseitenbilder in 2000 und 800 px als JPEG/PNG und Logos bis 1024 px.
Hier entstehen daraus bei Bedarf:

- eine mittlere Fassung (1200 px) für Handys und schmale Spalten,
- kleine Logos (z. B. 120 px für eine 60-px-Anzeige),
- AVIF oder WebP für Browser, die es können (``Accept: image/avif`` bzw. ``image/webp``;
  AVIF auf Ralfs Wunsch 14.11., noch etwas kleiner als WebP).

Jede Fassung wird einmal gerechnet und unter der Prüfsumme des Ausgangsbildes im
Zwischenspeicher „varianten“ abgelegt. Ob ein Bild gezeigt werden darf, entscheidet weiter
HUBIplan bei jedem Abruf: Die Fassung wird nur ausgeliefert, nachdem HUBIplan das
Ausgangsbild geliefert hat. Ein geändertes Bild hat eine andere Prüfsumme.
"""

from __future__ import annotations

import hashlib
import io
import logging
import threading

from django.core.cache import caches

log = logging.getLogger(__name__)

# Mittlere Fassung (Webseitenbilder): zwischen „klein“ (800) und „groß“ (2000) aus HUBIplan
MEDIUM_WIDTH = 1200
# Erlaubte Breiten für Logos (doppelte Anzeigegröße für scharfe Darstellung auf Handys)
LOGO_WIDTHS = (64, 112, 120, 200, 256)
# Größer rechnen wir nicht um (HUBIplan begrenzt Bilder ohnehin auf 4000 px)
MAX_PIXELS = 20_000_000
WEBP_QUALITY = 80
AVIF_QUALITY = 60
# Mittlere Geschwindigkeit: 2000 px dauern so etwa 0,7 s, einmal je Bild
AVIF_SPEED = 6
FORMATS = {"avif": "image/avif", "webp": "image/webp"}
CONVERTIBLE = ("image/jpeg", "image/png")

_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _lock_for(key: str) -> threading.Lock:
    with _locks_guard:
        if len(_locks) > 500:
            _locks.clear()
        return _locks.setdefault(key, threading.Lock())


def wanted_format(request) -> str | None:
    """Bestes Format, das der Browser annimmt: ``avif``, ``webp`` oder None (wie geliefert)."""
    accept = request.headers.get("Accept", "")
    for fmt, mime in FORMATS.items():
        if mime in accept:
            return fmt
    return None


def variant(
    body: bytes,
    ctype: str,
    *,
    width: int | None = None,
    fmt: str | None = None,
    store: bool = True,
) -> tuple[bytes, str]:
    """Fassung von ``body`` (höchstens ``width`` px breit, auf Wunsch AVIF oder WebP).

    Ist die Fassung nicht kleiner als das Ausgangsbild oder lässt es sich nicht lesen,
    kommt das Ausgangsbild zurück. ``store=False`` (Vorschau): nichts ablegen."""
    if fmt not in FORMATS:
        fmt = None
    if ctype not in CONVERTIBLE or (width is None and fmt is None):
        return body, ctype
    digest = hashlib.sha256(body).hexdigest()[:40]
    key = f"v1:{digest}:{width or 0}:{fmt or 'orig'}"
    cache = caches["varianten"] if store else None
    if cache is not None:
        hit = cache.get(key)
        if hit is not None:
            return hit
    with _lock_for(key):
        if cache is not None:
            hit = cache.get(key)
            if hit is not None:
                return hit
        result = _convert(body, ctype, width, fmt)
        if cache is not None:
            cache.set(key, result)
        return result


def _convert(body: bytes, ctype: str, width: int | None, fmt: str | None) -> tuple[bytes, str]:
    from PIL import Image

    try:
        with Image.open(io.BytesIO(body)) as img:
            if img.width * img.height > MAX_PIXELS:
                return body, ctype
            img.load()
            resized = bool(width and img.width > width)
            if not resized and fmt is None:
                return body, ctype
            if resized:
                height = max(1, round(img.height * width / img.width))
                img = img.resize((width, height), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            if fmt is not None:
                if img.mode not in ("RGB", "RGBA"):
                    alpha = "A" in img.getbands() or "transparency" in img.info
                    img = img.convert("RGBA" if alpha else "RGB")
                if fmt == "avif":
                    img.save(buf, "AVIF", quality=AVIF_QUALITY, speed=AVIF_SPEED)
                else:
                    img.save(buf, "WEBP", quality=WEBP_QUALITY, method=4)
                out_type = FORMATS[fmt]
            elif ctype == "image/png":
                img.save(buf, "PNG", optimize=True)
                out_type = ctype
            else:
                img.convert("RGB").save(buf, "JPEG", quality=82, optimize=True, progressive=True)
                out_type = ctype
    except Exception:  # Bild nicht lesbar: lieber das Original als gar nichts
        log.warning("Bildfassung nicht möglich (%s, %d Byte)", ctype, len(body), exc_info=True)
        return body, ctype
    data = buf.getvalue()
    if len(data) >= len(body) and not resized:
        return body, ctype
    return data, out_type


def etag(body: bytes) -> str:
    return '"' + hashlib.sha256(body).hexdigest()[:32] + '"'


def matches(request, tag: str) -> bool:
    """Passt If-None-Match (auch Liste oder W/-Form) auf ``tag``?"""
    header = request.headers.get("If-None-Match", "")
    if not header:
        return False
    if header.strip() == "*":
        return True
    candidates = {t.strip().removeprefix("W/") for t in header.split(",")}
    return tag in candidates
