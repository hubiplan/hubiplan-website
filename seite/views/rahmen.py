"""Rahmen jeder Seite: Vorlage wählen, Wartung, Fehlerseiten, Sprache."""

from __future__ import annotations

import functools
import re

from django.http import (
    HttpResponse,
    HttpResponsePermanentRedirect,
)
from django.shortcuts import render
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext as _

from .. import api
from ..site import (
    Site,
    global_maintenance,
    load,
)


def _page(request, template: str, site: Site | None, context: dict, status: int = 200):
    # Vorlage des Designs (Paket aus HUBIplan oder seite/designs/<design>/…), sonst Standard
    chosen = site.vorlage(template) if site is not None and not site.maintenance else template
    if hasattr(chosen, "render"):
        content = chosen.render({"site": site, **context}, request)
        response = HttpResponse(content, status=status)
    else:
        response = render(request, chosen, {"site": site, **context}, status=status)
    if site is not None and (site.is_preview or site.maintenance):
        response["Cache-Control"] = "private, no-store"
        response["X-Robots-Tag"] = "noindex"
    elif site is not None and not site.info.get("allow_indexing"):
        response["X-Robots-Tag"] = "noindex"
    if site is not None and site.several_header_images and "Cache-Control" not in response:
        # hubiplan #480: jedes Mal ein anderes Kopfbild, auch hinter einem Zwischenspeicher
        response["Cache-Control"] = "no-cache"
    return response


def maintenance_page(request, site: Site | None):
    response = _page(request, "seite/wartung.html", site, {}, status=503)
    response["Retry-After"] = "3600"
    response["X-Robots-Tag"] = "noindex"
    return response


def error_page(request, status: int, title: str, text: str, site: Site | None = None):
    return _page(request, "seite/fehler.html", site, {"title": title, "text": text}, status)


def not_found(request, exception=None):
    """Unbekannte Adresse (handler404, UX-Audit 16.11. WS-16): eigene Seite im Design des Vereins,
    in seiner Sprache, mit Suche und Weg zur Startseite, statt der rohen englischen Serverseite.
    Auch im Wartungszustand (dann ohne Menü, wie die Wartungsseite)."""
    title = _("Seite nicht gefunden")
    if global_maintenance():
        return maintenance_page(request, None)
    try:
        site = load(request)
    except (api.NotFound, api.Unavailable):
        return error_page(request, 404, title, _("Diese Adresse gibt es nicht."))

    def seite():
        return _page(
            request,
            "seite/fehler.html",
            site,
            {
                "title": _("Seite nicht gefunden"),
                "text": _(
                    "Diese Seite gibt es nicht oder nicht mehr. Vielleicht hilft die Suche "
                    "oder der Weg über die Startseite."
                )
                if site.block("search") and not site.maintenance
                else _("Diese Seite gibt es nicht oder nicht mehr."),
                "mit_suche": site.block("search") and not site.maintenance,
            },
            404,
        )

    return in_language(site, seite)


def in_language(site: Site, func, *args, **kwargs):
    """Seite in der Sprache der Webseite erzeugen (aus HUBIplan, Standard Deutsch). Gilt für
    die Rahmentexte, nicht für Vereinsdaten."""
    with translation.override(site.language):
        response = func(*args, **kwargs)
    response.setdefault("Content-Language", site.language)
    return response


def _run(view, request, site: Site, maintenance_ok: bool, *args, **kwargs):
    if site.maintenance and not maintenance_ok:
        return maintenance_page(request, site)
    try:
        return view(request, site, *args, **kwargs)
    except api.NotFound:
        return error_page(request, 404, _("Seite nicht gefunden"), "", site)
    except api.Maintenance:
        return maintenance_page(request, site)
    except api.Unavailable:
        return error_page(
            request,
            503,
            _("Gerade nicht erreichbar"),
            _("Ein Teil der Seite ist gerade nicht erreichbar. Bitte später erneut versuchen."),
            site,
        )


def site_view(*, maintenance_ok: bool = False):
    """Lädt die Webseite; zeigt Wartung oder Fehler, wo nötig."""

    def decorator(view):
        @functools.wraps(view)
        def wrapper(request, *args, **kwargs):
            if global_maintenance():
                return maintenance_page(request, None)
            try:
                site = load(request)
            except api.NotFound:
                return error_page(
                    request,
                    404,
                    _("Seite nicht gefunden"),
                    _("Zu dieser Adresse gibt es keine Webseite."),
                )
            except api.Unavailable:
                return error_page(
                    request,
                    503,
                    _("Gerade nicht erreichbar"),
                    _("Die Seite ist gerade nicht erreichbar. Bitte später erneut versuchen."),
                )
            # Sprache der Webseite (aus HUBIplan, Standard Deutsch); gilt für alle Texte
            # der Seite, nicht für Vereinsdaten
            return in_language(site, _run, view, request, site, maintenance_ok, *args, **kwargs)

        return wrapper

    return decorator


def _area(site: Site, area: str) -> dict:
    """Darstellung und Einleitung eines festen Bereichs (G5) für die Vorlage."""
    return {"darstellung": site.layout(area), "einleitung": site.intro(area)}


# Webseite #149: lesbare Adresse oder Kennung
ADRESSE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _readable(data: dict, kennung: str, name: str, *extra) -> HttpResponsePermanentRedirect | None:
    """Dauerhafte Weiterleitung auf die lesbare Adresse, wenn die Seite über ihre Kennung oder
    eine frühere Adresse aufgerufen wurde (Webseite #149)."""
    slug = data.get("slug")
    if isinstance(slug, str) and ADRESSE.match(slug) and slug != kennung:
        return HttpResponsePermanentRedirect(reverse(name, args=[slug, *extra]))
    return None
