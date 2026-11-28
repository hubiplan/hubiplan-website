"""Impressum, Datenschutz, Barrierefreiheit (auch im Wartungszustand erreichbar)."""

from __future__ import annotations

import functools

from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET

from .. import api, archiv, markdown
from ..site import (
    Site,
    global_maintenance,
    load,
)
from .rahmen import _page, error_page, in_language, maintenance_page, site_view
from .vorschau import VORLAGE_GEPRUEFT, _host


def legal_view(view):
    """Impressum und Datenschutz: auch bei allgemeiner Wartung und wenn HUBIplan nicht
    antwortet, dann mit der letzten geladenen Fassung und ihrem Stand (S02/F15)."""

    @functools.wraps(view)
    def wrapper(request):
        host = _host(request)
        stand = None
        try:
            site = load(request)
            imprint = site.get("imprint/")
        except api.NotFound:
            return error_page(
                request,
                404,
                _("Seite nicht gefunden"),
                _("Zu dieser Adresse gibt es keine Webseite."),
            )
        except (api.Unavailable, api.Maintenance):
            snap = archiv.load(host)
            if snap is None:
                if global_maintenance():
                    return maintenance_page(request, None)
                return error_page(
                    request,
                    503,
                    _("Gerade nicht erreichbar"),
                    _("Die Seite ist gerade nicht erreichbar. Bitte später erneut versuchen."),
                )
            site = Site(key=snap["key"], info=snap["info"], maintenance=True)
            imprint = snap["imprint"]
            stand = timezone.localtime(snap["saved_at"])
        else:
            if not site.is_preview:
                archiv.save(host, site.key, site.info, imprint)
        if global_maintenance():
            # Kopf ohne Menü wie auf der Wartungsseite
            site.maintenance = True
        return in_language(site, view, request, site, imprint, stand)

    return wrapper


@require_GET
@legal_view
def imprint(request, site: Site, data: dict, stand):
    return _page(request, "seite/impressum.html", site, {"imprint": data, "stand": stand})


@require_GET
@legal_view
def privacy(request, site: Site, data: dict, stand):
    return _page(
        request,
        "seite/datenschutz.html",
        site,
        {"privacy": data.get("privacy") or {}, "stand": stand},
    )


@require_GET
@site_view(maintenance_ok=True)
def accessibility(request, site: Site):
    """Erklärung zur Barrierefreiheit (Barrierefreiheit X-02). Seit dem UX-Audit 16.11. (WS-08,
    X-10) nur mit Aussagen, die für jeden Verein stimmen: geprüft ist die Vorlage, mit Datum aus
    VORLAGE_GEPRUEFT; Farben, Bilder und Texte pflegt der Verein. Ergänzungen des Vereins kommen,
    sobald HUBIplan sie schickt, als Einleitung „accessibility“."""
    intro = site.intro("accessibility")
    extra = markdown.render(intro.get("text") or "", site.units_path) if intro else ""
    return _page(
        request,
        "seite/barrierefreiheit.html",
        site,
        {
            "contact_enabled": site.block("contact") and not site.maintenance,
            "geprueft": VORLAGE_GEPRUEFT,
            "ergaenzung": extra,
            "mit_dokumenten": site.block("documents"),
            "mit_beitraegen": site.block("posts"),
        },
    )
