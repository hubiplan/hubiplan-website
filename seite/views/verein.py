"""Seiten über den Verein: Vorstand, Einheiten, Ehrungen, Geschichte, Galerie, Dokumente."""

from __future__ import annotations

from django.http import (
    HttpResponsePermanentRedirect,
    HttpResponseRedirect,
)
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET

from .. import api
from ..hilfen.anzeige import web_ziel
from ..site import (
    Site,
)
from ..zeitleiste import gliedern
from .aufbau import _unit_layout
from .beitraege import _posts, has_posts
from .rahmen import _area, _page, _readable, site_view
from .termine import _events, _public_ics, _upcoming, _webcal


@require_GET
@site_view()
def board(request, site: Site):
    if not site.block("board"):
        raise api.NotFound()
    data = site.get("board/")
    return _page(
        request,
        "seite/vorstand.html",
        site,
        {
            "roles": data.get("roles", []),
            **_area(site, "board"),
            # Menü „Würdenträger“: Ehrungen stehen dort auf einer eigenen Seite
            "honorary": [] if site.info.get("honors_menu") else data.get("honorary", []),
        },
    )


@require_GET
@site_view()
def units(request, site: Site, pfad: str):
    if not site.info.get("units"):
        raise api.NotFound()
    return _page(
        request,
        "seite/einheiten.html",
        site,
        {"units": site.info["units"], **_area(site, "units")},
    )


@require_GET
@site_view()
def unit(request, site: Site, pfad: str, slug: str):
    data = site.get(f"units/{slug}/")
    events = _upcoming(_events(site, slug), 5) if site.block("events") else []
    ics = _public_ics(site, slug)
    posts = _posts(site, unit=slug, limit=6) if has_posts(data) else []
    return _page(
        request,
        "seite/einheit.html",
        site,
        {
            "unit": data,
            "events": events,
            "webcal_url": _webcal(ics),
            "posts": posts,
            "abschnitte": _unit_layout(site, data),
        },
    )


@require_GET
@site_view()
def honors(request, site: Site):
    if not site.block("honors"):
        raise api.NotFound()
    return _page(
        request, "seite/majestaeten.html", site, {"dignities": site.get("honors/")["dignities"]}
    )


@require_GET
def old_honors_path(request, rest: str = ""):
    """Frühere Adresse /majestaeten/… → /wuerden/… (UX-Audit WS-12), dauerhaft, mit Anfrageteil."""
    ziel = "/wuerden/" + rest
    if request.META.get("QUERY_STRING"):
        ziel += "?" + request.META["QUERY_STRING"]
    return HttpResponsePermanentRedirect(ziel)


@require_GET
@site_view()
def dignity(request, site: Site, kennung: str):
    """Eine Würde als eigene Seite (Unterpunkt von „Würdenträger“)."""
    if not site.block("honors"):
        raise api.NotFound()
    dignities = site.get("honors/")["dignities"]
    # Aktuelle lesbare Adresse, dann Kennung, dann frühere Adresse (Webseite #149)
    found = (
        [d for d in dignities if d.get("slug") == kennung]
        or [d for d in dignities if d.get("id") == kennung]
        or [d for d in dignities if kennung in (d.get("aliases") or [])]
    )
    if not found:
        raise api.NotFound()
    redirect = _readable(found[0], kennung, "wuerde")
    if redirect is not None:
        return redirect
    return _page(request, "seite/majestaeten.html", site, {"dignities": found[:1]})


@require_GET
@site_view()
def honorary(request, site: Site):
    """Ehrungen als eigene Seite (Unterpunkt von „Würdenträger“)."""
    menu = site.info.get("honors_menu") or {}
    if not menu.get("honorary"):
        raise api.NotFound()
    return _page(
        request,
        "seite/ehrungen.html",
        site,
        {"honorary": site.get("board/").get("honorary", [])},
    )


@require_GET
@site_view()
def history(request, site: Site):
    """Alte Adresse /geschichte/ (bis 31.10.2026 Text und Ämter auf einer Seite)."""
    chronik, aemter = site.history_parts()
    if chronik:
        return HttpResponseRedirect(reverse("chronik"))
    if aemter:
        return HttpResponseRedirect(reverse("aemter"))
    raise api.NotFound()


@require_GET
@site_view()
def chronicle(request, site: Site):
    """Chronik: Text „geschichte“ aus Webseite › Inhalte, darunter die Zeitleiste."""
    if not site.block("history"):
        raise api.NotFound()
    page = site.get("pages/geschichte/")
    return _page(
        request,
        "seite/chronik.html",
        site,
        {
            "page": page,
            "zeitleiste": gliedern(
                (page or {}).get("timeline"), (page or {}).get("timeline_newest_first", False)
            ),
        },
    )


# --- Galerie (Ralf 05.11.2026): Alben mit Unteralben, Bilder groß im Fenster ---


@require_GET
@site_view()
def gallery(request, site: Site):
    if not site.block("gallery"):
        raise api.NotFound()
    albums = site.get("galleries/").get("albums", [])
    return _page(request, "seite/galerie.html", site, {"albums": albums, **_area(site, "gallery")})


@require_GET
@site_view()
def album(request, site: Site, slug: str):
    if not site.block("gallery"):
        raise api.NotFound()
    return _page(
        request,
        "seite/album.html",
        site,
        {"album": site.get(f"galleries/{slug}/"), "darstellung": site.layout("gallery")},
    )


@require_GET
@site_view()
def offices(request, site: Site):
    """Ämter: heutige und frühere Inhaber der Rollen mit „unter Ämter zeigen“."""
    if not site.block("offices"):
        raise api.NotFound()
    offices = site.get("board/").get("chronicle", [])
    if not offices:
        raise api.NotFound()
    return _page(request, "seite/aemter.html", site, {"offices": offices})


@require_GET
@site_view()
def documents(request, site: Site):
    """Dokumente des Vereins: Satzung, (optional) Beitragsordnung und Gründungsurkunde."""
    docs = []
    if web_ziel(site.info.get("statute_url")):
        docs.append(
            {
                "title": _("Satzung"),
                "url": web_ziel(site.info["statute_url"]),
                "kind": "§",
                # Erste Seite als Bild (ältere HUBIplan-Stände: nur das Symbol)
                "preview": site.local(site.info.get("statute_preview_url")),
            }
        )
    if web_ziel(site.info.get("fee_rules_url")):
        docs.append(
            {
                "title": _("Beitragsordnung"),
                "url": web_ziel(site.info["fee_rules_url"]),
                "kind": "€",
                "preview": site.local(site.info.get("fee_rules_preview_url")),
            }
        )
    if web_ziel(site.info.get("founding_deed_url")):
        docs.append(
            {
                "title": _("Gründungsurkunde"),
                "url": web_ziel(site.info["founding_deed_url"]),
                "kind": "§",
                "preview": site.local(site.info.get("founding_deed_preview_url")),
            }
        )
    # Eigene Dokumente aus HUBIplan (Ralf 05.11.); ältere Stände kennen sie nicht
    try:
        own = site.get("documents/?section=documents").get("documents", [])
    except api.NotFound:
        own = []
    for d in own:
        docs.append(
            {
                "title": d.get("title") or "",
                "url": site.local(d.get("url")),
                "kind": "PDF" if d.get("kind") == "pdf" else "",
                "preview": site.local(d.get("preview_url")),
            }
        )
    if not docs:
        raise api.NotFound()
    return _page(request, "seite/dokumente.html", site, {"documents": docs})


# --- Kapelle (Ralf 05.11.2026): Mitgliederlisten, Gedenken, Repertoire, Presse, Suche ---


@require_GET
@site_view()
def members(request, site: Site, slug: str):
    if not site.block("members"):
        raise api.NotFound()
    data = site.get(f"members/{slug}/")
    return _page(request, "seite/mitglieder.html", site, {"liste": data})


@require_GET
@site_view()
def memorial(request, site: Site):
    if not site.block("memorial"):
        raise api.NotFound()
    data = site.get("memorial/")
    return _page(
        request,
        "seite/gedenken.html",
        site,
        {"intro": data.get("intro"), "personen": data.get("members", [])},
    )


@require_GET
@site_view()
def repertoire(request, site: Site):
    if not site.block("repertoire"):
        raise api.NotFound()
    pieces = site.get("repertoire/").get("pieces", [])
    return _page(request, "seite/repertoire.html", site, {"stuecke": pieces})
