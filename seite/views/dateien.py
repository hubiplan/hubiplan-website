"""Dateien und technische Adressen: Bilder, Dokumente, Favicon, Gesundheit, robots, Design-CSS."""

from __future__ import annotations

import re

from django.http import (
    HttpResponse,
    HttpResponseRedirect,
    StreamingHttpResponse,
)
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET

from .. import api, bilder, designpaket
from ..site import (
    DESIGNS,
    Site,
    confirmed_preview,
    global_maintenance,
    host_of,
    load,
)
from .rahmen import site_view

# --- Bilder und Logos über diese Seite ---

ALLOWED_API_FILES = re.compile(
    r"^(images/[A-Za-z0-9_\-]{4,40}/|photos/[a-f0-9]{20}/|honors/photos/[a-f0-9]{20}/"
    r"|posts/images/[A-Za-z0-9_\-]{4,40}/|statute/preview/|fee-rules/preview/"
    r"|founding-deed/preview/|files/[A-Za-z0-9_\-]{8,24}/|events/attachments/[0-9]{1,12}/"
    # Favicon und Handy-Symbol (Wappen quadratisch, Ralf 09.11.2026)
    r"|icon-(?:32|180|192|512)\.png)$"
)


ALLOWED_MEDIA = re.compile(r"^[A-Za-z0-9_\-/.]{1,300}\.(png|jpe?g|webp)$")


# Adressen, die sich bei jeder Änderung ändern: Logos mit Zeitstempel im Namen
# (logos/…/<id>-<JJJJMMTThhmmss>.png), Webseitenbilder mit Fassung (images/<key>-v3/)
LOGO_STAMPED = re.compile(r"^logos/.+-\d{14}\.(png|jpe?g|webp)$")


IMAGE_VERSIONED = re.compile(r"^images/[A-Za-z0-9_\-]+-v\d+/$")


# Bilder von Beiträgen aus den eigenen Kanälen: Kennung je Bild, Inhalt ändert sich nie
POST_IMAGE = re.compile(r"^posts/images/[A-Za-z0-9_\-]{4,40}/$")


# Bilder in der Vorschau: Seiten und Daten prüft HUBIplan bei jedem Aufruf (Widerruf
# wirkt sofort), Bilder darf aber der eigene Browser kurz behalten. Sonst lädt jeder
# Seitenwechsel alle Bilder neu, und jedes kostet einen Abruf in HUBIplan.
PREVIEW_MEDIA_CACHE = "private, max-age=300"


def _media_cache(private: bool, kind: str, path: str) -> str:
    """Wie lange der Browser ein Bild behalten darf. Vorschau und Wartung: nur der eigene
    Browser, 10 Minuten (sonst lädt z. B. das Wappen bei jedem Seitenwechsel neu).
    Danach fragt der Browser mit dem ETag nach und bekommt meist nur „unverändert“ (304)."""
    if private:
        return "private, max-age=600"
    if kind == "m" and LOGO_STAMPED.match(path):
        return "public, max-age=31536000, immutable"
    if kind == "a" and (IMAGE_VERSIONED.match(path) or POST_IMAGE.match(path)):
        # Ein Tag: Ein aus der Webseite genommenes Bild verschwindet so bald auch aus
        # fremden Zwischenspeichern
        return "public, max-age=86400"
    return "public, max-age=600"


def _media_size(request, kind: str) -> tuple[str, int | None, int | None]:
    """Gewünschte Fassung: ``?size=small`` (800 px aus HUBIplan), ``?size=medium``
    (1200 px, hier aus der großen Fassung gerechnet), bei Logos ``?w=<Breite>`` und
    ``?h=<Höhe>`` (passt in beide, hubiplan #557)."""
    if kind == "a":
        size = request.GET.get("size")
        if size == "small":
            return "?size=small", None, None
        if size == "medium":
            return "", bilder.MEDIUM_WIDTH, None
        return "", None, None

    def zahl(name: str, erlaubt: tuple[int, ...]) -> int | None:
        try:
            value = int(request.GET.get(name) or 0)
        except ValueError:
            return None
        return value if value in erlaubt else None

    return "", zahl("w", bilder.LOGO_WIDTHS), zahl("h", bilder.LOGO_HEIGHTS)


# Gesamtaudit 15.11., WEB-03: große Dokumente nicht ganz in den Speicher
STREAM_FROM = 2 * 1024 * 1024


PDF_PATHS = ("files/", "events/attachments/")


def _streamed(request, res, ctype, pdf_ok, preview, key, kind, path):
    """Große Datei Stück für Stück, mit denselben Kopfzeilen wie sonst. Ob sie gezeigt werden
    darf, hat HUBIplan mit dieser Antwort schon entschieden."""
    if not (pdf_ok and ctype == "application/pdf"):
        for _ in res.stream:  # Verbindung sauber schließen
            break
        res.stream.close()
        return HttpResponse(status=404)
    private = bool(preview) or api.cached_maintenance(key)
    response = StreamingHttpResponse(res.stream, content_type=ctype)
    response["Content-Length"] = str(res.length)
    response["Content-Disposition"] = "inline"
    response["Cache-Control"] = (
        PREVIEW_MEDIA_CACHE if preview else _media_cache(private, kind, path)
    )
    response["Content-Security-Policy"] = "frame-ancestors 'none'"
    return response


@require_GET
def media(request, kind: str, path: str):
    """Bild aus HUBIplan über diese Seite. Ohne die Grunddaten der Seite: Ob ein Bild
    gezeigt werden darf (Wartung, Vorschau), prüft HUBIplan beim Bild selbst. Sonst
    wartete jedes Bild erneut auf die Grunddaten."""
    if global_maintenance():
        return HttpResponse(status=503)
    size, width, height = _media_size(request, kind)
    try:
        key = api.resolve(host_of(request))
        # Nur eine von HUBIplan bestätigte Vorschau schaltet Ablage und Zwischenspeicher ab
        # (Gesamtaudit 15.11., WEB-01)
        preview = confirmed_preview(request, key)
        if kind == "a":
            if not ALLOWED_API_FILES.match(path):
                raise api.NotFound()
            # Dokumente und Terminanhänge (PDF, bis 20 MB) ab 2 MB gestreamt (WEB-03)
            res = api.fetch_file(
                f"{api.PREFIX}{key}/{path}{size}",
                preview=preview,
                stream_from=STREAM_FROM if path.startswith(PDF_PATHS) else 0,
            )
        else:
            if ".." in path or not ALLOWED_MEDIA.match(path):
                raise api.NotFound()
            res = api.fetch_file(f"/media/{path}")
    except api.NotFound:
        return HttpResponse(status=404)
    except api.Unavailable:
        return HttpResponse(status=503)
    ctype = res.content_type.split(";")[0].strip()
    # PDF nur bei Dokumenten der Webseite (Pressespiegel, Ralf 05.11.) und freigegebenen
    # Anhängen öffentlicher Termine (Ralf 14.11.)
    pdf_ok = kind == "a" and path.startswith(PDF_PATHS)
    if res.stream is not None:
        return _streamed(request, res, ctype, pdf_ok, preview, key, kind, path)
    if ctype not in ("image/png", "image/jpeg", "image/webp") and not (
        pdf_ok and ctype == "application/pdf"
    ):
        return HttpResponse(status=404)
    body = res.body
    # App-Symbole bleiben PNG (Favicon, Startbildschirm)
    convertible = ctype in bilder.CONVERTIBLE and not path.startswith("icon-")
    if convertible:
        # Kleinere Fassung, AVIF/WebP (Ladezeiten 14.11.); in der Vorschau nichts ablegen
        body, ctype = bilder.variant(
            body,
            ctype,
            width=width,
            height=height,
            fmt=bilder.wanted_format(request),
            store=not preview,
        )
    # Mit Vorschau oder in der Wartung nur im eigenen Browser; der Zustand steht im
    # Zwischenspeicher der Grunddaten, wenn eine Seite davor geladen wurde
    private = bool(preview) or api.cached_maintenance(key)
    cache_control = PREVIEW_MEDIA_CACHE if preview else _media_cache(private, kind, path)
    tag = bilder.etag(body)
    if bilder.matches(request, tag):
        response = HttpResponse(status=304)
    else:
        response = HttpResponse(body, content_type=ctype)
        if ctype == "application/pdf":
            response["Content-Disposition"] = "inline"
    response["ETag"] = tag
    if convertible:
        # Je nach Accept JPEG/PNG, WebP oder AVIF unter derselben Adresse
        response["Vary"] = "Accept"
    response["Cache-Control"] = cache_control
    if ctype == "application/pdf":
        # Ohne sandbox: Chrome und Edge zeigen PDFs in einer Sandbox nicht an
        # (ERR_BLOCKED_BY_CLIENT); wie HUBIplan selbst. Fremdes Einbetten bleibt verboten.
        response["Content-Security-Policy"] = "frame-ancestors 'none'"
    else:
        response["Content-Security-Policy"] = "default-src 'none'; sandbox"
    return response


@require_GET
def favicon(request):
    """Browser fragen ohne Seite oft /favicon.ico ab: auf das Symbol aus HUBIplan
    weiterleiten (ohne Symbol antwortet es mit 404)."""
    response = HttpResponseRedirect(reverse("medien", args=["a", "icon-32.png"]))
    response["Cache-Control"] = "public, max-age=86400"
    return response


@require_GET
def health(request):
    """Für den Healthcheck des Containers (ohne Aufruf von HUBIplan)."""
    return HttpResponse("ok\n", content_type="text/plain")


@require_GET
def robots(request):
    allow = False
    if not global_maintenance():
        try:
            site = load(request)
            allow = bool(site.info.get("allow_indexing")) and not site.maintenance
        except (api.NotFound, api.Unavailable):
            allow = False
    lines = ["User-agent: *", "Allow: /" if allow else "Disallow: /"]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")


# --- Designpakete (Ralf 2026-11-02) ---


@site_view(maintenance_ok=True)
def design_css(request, site: Site, key: str):
    """CSS eines eingespielten Designpakets (geprüft, nur für freigegebene Webseiten)."""
    package = site.package_for(key)
    if package is None:
        raise api.NotFound()
    response = HttpResponse(package["css"], content_type="text/css; charset=utf-8")
    response["X-Content-Type-Options"] = "nosniff"
    # Mit passender Kennung ändert sich der Inhalt nie (neuer Stand = neuer Hash); in
    # Vorschau und Wartung nur im eigenen Browser
    if request.GET.get("v") != package["hash"]:
        response["Cache-Control"] = "private, no-store"
    elif site.is_preview:
        # Sonst holt jeder Seitenwechsel die Grunddaten noch einmal nur für das CSS
        response["Cache-Control"] = PREVIEW_MEDIA_CACHE
    elif site.maintenance:
        response["Cache-Control"] = "private, max-age=86400"
    else:
        response["Cache-Control"] = "public, max-age=86400"
    return response


@site_view(maintenance_ok=True)
def design_export(request, site: Site, key: str):
    """Standarddesign als Paket (ZIP) zum Einspielen als eigenes Design in HUBIplan.

    Inhalt ist ohnehin öffentlich (CSS und Vorlagen der Webseite); Name, Hinweis und
    Farbrollen kommen aus HUBIplan."""
    catalog = (site.info.get("design_catalog") or {}).get(key)
    if key not in DESIGNS or not isinstance(catalog, dict):
        raise api.NotFound()
    today = timezone.localdate().isoformat()
    data = designpaket.export_builtin(key, str(DESIGNS[key]), catalog, today)
    response = HttpResponse(data, content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="design-{key}-{today}.zip"'
    response["Cache-Control"] = "private, no-store"
    response["X-Robots-Tag"] = "noindex"
    return response
