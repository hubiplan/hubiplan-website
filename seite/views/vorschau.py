"""Vorschau aus HUBIplan: betreten, Design wählen, beenden."""

from __future__ import annotations

import datetime

from django.conf import settings
from django.http import (
    HttpResponseRedirect,
)
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET

from .. import api, designpaket
from ..site import (
    DESIGN_COOKIE,
    DESIGNS,
    PREVIEW_COOKIE,
    SITE_COOKIE,
    chosen_host,
    host_of,
)
from .rahmen import error_page

# Letzte Prüfung der Vorlage nach WCAG 2.2 AA (UX-Audit 16./17.11.2026). Bei der nächsten Prüfung
# hier nachziehen; die Seite „Barrierefreiheit“ nennt das Datum.
VORLAGE_GEPRUEFT = datetime.date(2026, 11, 17)


# --- Vorschau ---


@require_GET
def preview(request):
    """Vorschau-Schlüssel aus HUBIplan gegen ein Vorschau-Cookie tauschen."""
    token = request.GET.get("schluessel", "")
    if not token or len(token) > 500:
        return error_page(request, 400, _("Vorschau"), _("Der Vorschau-Link ist unvollständig."))
    # Testserver mit fester Zuordnung: der Vorschau-Link nennt die Webseite (?seite=…)
    chosen = chosen_host(request.GET.get("seite"))
    try:
        key = api.resolve(chosen or settings.SITE_HOST_OVERRIDE or _host(request))
        res = api.post(key, "preview/", {"token": token})
    except api.NotFound:
        return error_page(request, 404, _("Seite nicht gefunden"), "")
    except api.Unavailable:
        return error_page(
            request, 503, _("Gerade nicht erreichbar"), _("Bitte später erneut versuchen.")
        )
    if res.status != 200:
        return error_page(
            request,
            403,
            _("Vorschau nicht möglich"),
            _(
                "Der Vorschau-Link ist ungültig oder abgelaufen. "
                "Bitte in HUBIplan einen neuen öffnen."
            ),
        )
    data = res.json()
    # Weiterleitung im Rahmen: auch über die Vereinsadresse der Einheit (Issue #729)
    request.vorschau_rahmen = data.get("frame_origins") or []
    response = HttpResponseRedirect(reverse("start"))
    # Anderes Design nur ansehen (Webseite › Gestaltung › „Vorschau ansehen“)
    _set_design_cookie(response, request.GET.get("design", ""))
    until = parse_datetime(data.get("until") or "")
    max_age = 8 * 3600
    if until is not None:
        max_age = max(60, min(max_age, int((until - timezone.now()).total_seconds())))
    response.set_cookie(
        PREVIEW_COOKIE,
        data["session"],
        max_age=max_age,
        secure=settings.PREVIEW_COOKIE_SECURE,
        httponly=True,
        samesite="Lax",
        path=settings.BASE_PATH + "/" if settings.BASE_PATH else "/",
    )
    path = settings.BASE_PATH + "/" if settings.BASE_PATH else "/"
    if chosen:
        response.set_cookie(
            SITE_COOKIE,
            chosen,
            max_age=max_age,
            secure=settings.PREVIEW_COOKIE_SECURE,
            httponly=True,
            samesite="Lax",
            path=path,
        )
    else:
        response.delete_cookie(SITE_COOKIE, path=path, samesite="Lax")
    response["Cache-Control"] = "private, no-store"
    return response


def _set_design_cookie(response, design: str) -> None:
    path = settings.BASE_PATH + "/" if settings.BASE_PATH else "/"
    # Standarddesign oder Paket (ob es freigegeben ist, prüft die Seite beim Zeichnen)
    if design in DESIGNS or designpaket.KEY.match(design or ""):
        response.set_cookie(
            DESIGN_COOKIE,
            design,
            max_age=8 * 3600,
            secure=settings.PREVIEW_COOKIE_SECURE,
            httponly=True,
            samesite="Lax",
            path=path,
        )
    else:
        response.delete_cookie(DESIGN_COOKIE, path=path, samesite="Lax")


# Unterseiten, die die Vorschau in HUBIplan direkt zeigen kann (Stilregler mit Wirkung dort)
PREVIEW_TARGETS = {"unterseite": "impressum", "termine": "termine"}


@require_GET
def preview_design(request):
    """In der Vorschau ein anderes Design zeigen (?design=…) oder zurück zum gewählten.

    ``?ziel=`` führt danach auf eine feste Unterseite statt auf die Startseite (HUBIplan zeigt
    so die Stelle, die ein Stilregler ändert, Ralf 14.11.2026); nur Namen aus PREVIEW_TARGETS."""
    target = PREVIEW_TARGETS.get(request.GET.get("ziel", ""), "start")
    response = HttpResponseRedirect(reverse(target))
    _set_design_cookie(response, request.GET.get("design", ""))
    response["Cache-Control"] = "private, no-store"
    return response


@require_GET
def preview_end(request):
    """Vorschau beenden (UX-Audit 31.10. R03): Cookie unter allen Pfaden löschen, unter
    denen es je gesetzt wurde, und den Abschluss sichtbar melden."""
    response = HttpResponseRedirect(reverse("start") + "?vorschau=beendet")
    _set_design_cookie(response, "")
    main = settings.BASE_PATH + "/" if settings.BASE_PATH else "/"
    response.delete_cookie(PREVIEW_COOKIE, path=main, samesite="Lax")
    response.delete_cookie(SITE_COOKIE, path=main, samesite="Lax")
    if main != "/":
        # Ein früher unter „/“ gesetztes Cookie ebenfalls löschen (zweiter Set-Cookie-Kopf;
        # response.cookies kennt je Name nur einen Eintrag)
        response["Set-Cookie"] = (
            f"{PREVIEW_COOKIE}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; Max-Age=0; Path=/; "
            "SameSite=Lax"
        )
    response["Cache-Control"] = "private, no-store"
    return response


def _host(request) -> str:
    return host_of(request)
