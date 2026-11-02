"""Seiten der Vereinswebseite.

Jede Seite lädt die Webseite zur Anfrage (Hostname → Schlüssel → Grunddaten).
Im Wartungsmodus gibt es nur Wartungsseite, Impressum und Datenschutz, außer mit
gültiger Vorschau.
"""

from __future__ import annotations

import functools
import io
import logging
import re
from collections import OrderedDict

import qrcode
import qrcode.image.svg
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import formats, timezone, translation
from django.utils.dateparse import parse_datetime
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET

from . import api, archiv
from .site import DESIGN_COOKIE, DESIGNS, PREVIEW_COOKIE, Site, global_maintenance, host_of, load
from .zeitleiste import gliedern

log = logging.getLogger(__name__)


def _page(request, template: str, site: Site | None, context: dict, status: int = 200):
    response = render(request, template, {"site": site, **context}, status=status)
    if site is not None and (site.is_preview or site.maintenance):
        response["Cache-Control"] = "private, no-store"
        response["X-Robots-Tag"] = "noindex"
    elif site is not None and not site.info.get("allow_indexing"):
        response["X-Robots-Tag"] = "noindex"
    return response


def maintenance_page(request, site: Site | None):
    response = _page(request, "seite/wartung.html", site, {}, status=503)
    response["Retry-After"] = "3600"
    response["X-Robots-Tag"] = "noindex"
    return response


def error_page(request, status: int, title: str, text: str, site: Site | None = None):
    return _page(request, "seite/fehler.html", site, {"title": title, "text": text}, status)


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


# --- Termine ---


def _events(site: Site, unit: str | None = None) -> list[dict]:
    path = "events/" + (f"?einheit={unit}" if unit else "")
    events = []
    for e in site.get(path).get("events", []):
        start = parse_datetime(e["starts_at"]) if e.get("starts_at") else None
        end = parse_datetime(e["ends_at"]) if e.get("ends_at") else None
        if start is None:
            continue
        start = timezone.localtime(start)
        end = timezone.localtime(end) if end else None
        events.append({**e, "start": start, "end": end})
    events.sort(key=lambda e: e["start"])
    return events


POST_KINDS = ("instagram", "facebook")


def has_posts(info: dict, kind: str | None = None) -> bool:
    """Gibt es sichtbare Beiträge (aus HUBIplan-Info oder Info einer Untereinheit)?"""
    flags = info.get("posts") or {}
    if not isinstance(flags, dict):
        return False
    return bool(flags.get(kind)) if kind else any(flags.get(k) for k in POST_KINDS)


def _posts(
    site: Site, kind: str | None = None, unit: str | None = None, limit: int = 24
) -> list[dict]:
    """Beiträge aus Instagram/Facebook, von HUBIplan lokal gespeichert (nie von Meta)."""
    if not site.block("posts"):
        return []
    query = [f"anzahl={limit}"]
    if kind:
        query.append(f"art={kind}")
    if unit:
        query.append(f"einheit={unit}")
    try:
        items = site.get("posts/?" + "&".join(query)).get("posts", [])
    except api.NotFound:
        return []
    result = []
    for p in items:
        when = parse_datetime(p["published_at"]) if p.get("published_at") else None
        permalink = p.get("permalink") or ""
        if not permalink.startswith("https://"):
            permalink = ""
        result.append(
            {
                **p,
                "when": timezone.localtime(when) if when else None,
                "permalink": permalink,
                "images": [i for i in p.get("images") or [] if i.get("url")],
            }
        )
    return result


def _upcoming(events: list[dict], limit: int | None = None) -> list[dict]:
    now = timezone.now()
    today = timezone.localdate()
    result = [
        e
        for e in events
        if (e["end"] or e["start"]) >= now or (e["all_day"] and e["start"].date() >= today)
    ]
    return result[:limit] if limit else result


def _by_month(events: list[dict]) -> list[tuple[str, list[dict]]]:
    groups: OrderedDict[str, list[dict]] = OrderedDict()
    for e in events:
        groups.setdefault(formats.date_format(e["start"], "F Y"), []).append(e)
    return list(groups.items())


def _webcal(url: str | None) -> str | None:
    if not url:
        return None
    return re.sub(r"^https?://", "webcal://", url)


def _qr_svg(text: str) -> str:
    img = qrcode.make(text, image_factory=qrcode.image.svg.SvgPathImage, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf)
    svg = buf.getvalue().decode()
    return svg[svg.find("<svg") :]


def _public_ics(site: Site, unit: str | None = None) -> str | None:
    """Abo-Adresse der Kalenderdatei (öffentlich bei HUBIplan)."""
    if not site.block("events"):
        return None
    url = f"{settings.HUBIPLAN_PUBLIC_URL}{api.PREFIX}{site.key}/events.ics"
    return url + (f"?einheit={unit}" if unit else "")


# --- Seiten ---


# Bausteine der Startseite; ältere HUBIplan-Stände ohne „home“ zeigen die
# bisherige Startseite in dieser Reihenfolge
HOME_SECTIONS = (
    "carousel",
    "greeting",
    "events",
    "honors",
    "results",
    "units",
    "instagram",
    "facebook",
)
DEFAULT_HOME = ("carousel", "greeting", "events", "honors", "units")


def _home(site: Site) -> list[str]:
    home = site.info.get("home")
    if not isinstance(home, list):
        home = DEFAULT_HOME
    keys = []
    for key in home:
        if key in HOME_SECTIONS and key not in keys:
            keys.append(key)
    return keys


SIDE_SECTIONS = {"events", "honors", "units"}

# Wettbewerbsergebnisse (Wettbewerbe Schritt 5): Stand laufender Wettbewerbe nur kurz
# zwischenspeichern; die Rangliste selbst hängt am Stand und ist dann sofort neu
LIVE_SECONDS = 5
OVERVIEW_SECONDS = 30
TOKEN = re.compile(r"^[a-f0-9]{20}$")


def _results_on(site: Site) -> bool:
    return bool(site.info.get("results_url"))


def _home_results(site: Site) -> list[dict]:
    try:
        data = site.get("results/?start=1", seconds=OVERVIEW_SECONDS)
    except api.NotFound:
        return []
    return [_with_date(c) for c in data.get("competitions", [])]


def _with_date(comp: dict) -> dict:
    from datetime import date

    try:
        when = date.fromisoformat(comp.get("date") or "")
    except ValueError:
        when = None
    return {**comp, "when": when}


@require_GET
@site_view()
def start(request, site: Site):
    home = _home(site)
    greeting = site.info.get("greeting") or None
    events = _upcoming(_events(site), 3) if "events" in home and site.block("events") else []
    honors = (
        site.get("honors/").get("dignities", [])
        if "honors" in home and site.block("honors")
        else []
    )
    results = _home_results(site) if "results" in home and _results_on(site) else []
    return _page(
        request,
        "seite/start.html",
        site,
        {
            "greeting": greeting,
            "sections": [f"seite/start/{key}.html" for key in home],
            # Zeitung: Termine, Majestäten und Untereinheiten in der rechten Spalte
            "sections_side": [f"seite/start/{key}.html" for key in home if key in SIDE_SECTIONS],
            "sections_main": [
                f"seite/start/{key}.html" for key in home if key not in SIDE_SECTIONS
            ],
            "greeting_title": bool(greeting and greeting.get("title") and "greeting" in home),
            "carousel": bool(
                greeting and "carousel" in home and len(greeting.get("gallery") or []) > 1
            ),
            "events": events,
            "results": results,
            # Ralf 2026-10-31: auf der Startseite nur Träger des laufenden Jahres
            "honors": [
                d for d in honors if d.get("current") and d.get("current_year") is not False
            ][:2],
            # Je Netzwerk die 3 neuesten Beiträge (von HUBIplan gespeichert, nichts von Meta)
            **{
                f"{kind}_posts": _posts(site, kind, limit=3)
                if kind in home and has_posts(site.info, kind)
                else []
                for kind in POST_KINDS
            },
        },
    )


@require_GET
@site_view()
def news(request, site: Site):
    if not site.block("posts") or not has_posts(site.info):
        raise api.NotFound()
    kind = request.GET.get("kanal")
    if kind not in POST_KINDS or not has_posts(site.info, kind):
        kind = None
    kinds = [k for k in POST_KINDS if has_posts(site.info, k)]
    return _page(
        request,
        "seite/aktuelles.html",
        site,
        {"posts": _posts(site, kind), "kind": kind, "kinds": kinds if len(kinds) > 1 else []},
    )


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
            # Menü „Würdenträger“: Ehrungen stehen dort auf einer eigenen Seite
            "honorary": [] if site.info.get("honors_menu") else data.get("honorary", []),
        },
    )


@require_GET
@site_view()
def events(request, site: Site):
    if not site.block("events"):
        raise api.NotFound()
    unit = request.GET.get("einheit") or None
    if unit and not re.fullmatch(r"[a-z0-9\-]{1,80}", unit):
        unit = None
    items = _upcoming(_events(site, unit))
    ics = _public_ics(site, unit)
    return _page(
        request,
        "seite/termine.html",
        site,
        {
            "months": _by_month(items),
            "ics_url": ics,
            "webcal_url": _webcal(ics),
            "qr": mark_safe(_qr_svg(_webcal(ics))) if ics else "",  # noqa: S308
            "unit": unit,
            # Nur Einheiten mit Terminen zur Auswahl (ältere HUBIplan-Stände: alle)
            "units": [u for u in site.info.get("units", []) if u.get("has_events", True)],
        },
    )


@require_GET
@site_view()
def units(request, site: Site, pfad: str):
    if not site.info.get("units"):
        raise api.NotFound()
    return _page(request, "seite/einheiten.html", site, {"units": site.info["units"]})


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
        {"unit": data, "events": events, "webcal_url": _webcal(ics), "posts": posts},
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
@site_view()
def dignity(request, site: Site, kennung: str):
    """Eine Würde als eigene Seite (Unterpunkt von „Würdenträger“)."""
    if not site.block("honors"):
        raise api.NotFound()
    found = [d for d in site.get("honors/")["dignities"] if d.get("id") == kennung]
    if not found:
        raise api.NotFound()
    return _page(request, "seite/majestaeten.html", site, {"dignities": found})


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


# --- Wettbewerbsergebnisse ---


@require_GET
@site_view()
def results(request, site: Site):
    """Übersicht: veröffentlichte Wettbewerbe, Reihen und Wanderpokale."""
    if not _results_on(site):
        raise api.NotFound()
    data = site.get("results/", seconds=OVERVIEW_SECONDS)
    comps = [_with_date(c) for c in data.get("competitions", [])]
    return _page(
        request,
        "seite/ergebnisse.html",
        site,
        {
            "live": [c for c in comps if not c.get("final")],
            "years": _by_year([c for c in comps if c.get("final")]),
            "series": data.get("series", []),
            "trophies": data.get("trophies", []),
        },
    )


def _by_year(comps: list[dict]) -> list[tuple[int, list[dict]]]:
    groups: OrderedDict[int, list[dict]] = OrderedDict()
    for c in comps:
        groups.setdefault(c.get("year"), []).append(c)
    return list(groups.items())


def _result(site: Site, kennung: str) -> dict:
    """Rangliste eines Wettbewerbs; zuerst den kleinen Stand, dann die Rangliste zu genau
    diesem Stand (neues Ergebnis → neuer Stand → sofort neue Tabelle)."""
    if not _results_on(site) or not TOKEN.match(kennung):
        raise api.NotFound()
    stand = site.get(f"results/{kennung}/version/", seconds=LIVE_SECONDS)
    version = re.sub(r"[^A-Za-z0-9]", "", str(stand.get("version", "")))[:64]
    return _with_date(site.get(f"results/{kennung}/?stand={version}"))


@require_GET
@site_view()
def result(request, site: Site, kennung: str):
    data = _result(site, kennung)
    response = _page(request, "seite/ergebnis.html", site, {"c": data})
    if not data.get("final"):
        response["Cache-Control"] = "no-cache"
    return response


@require_GET
@site_view()
def result_table(request, site: Site, kennung: str):
    """Nur die Rangliste (für das Nachladen während „live“)."""
    data = _result(site, kennung)
    response = _page(request, "seite/ergebnis_inhalt.html", site, {"c": data})
    response["Cache-Control"] = "no-cache"
    return response


@require_GET
@site_view()
def result_version(request, site: Site, kennung: str):
    """Kleiner Stand für den Browser: Er fragt ihn während „live“ alle 15 Sekunden ab."""
    if not _results_on(site) or not TOKEN.match(kennung):
        raise api.NotFound()
    stand = site.get(f"results/{kennung}/version/", seconds=LIVE_SECONDS)
    response = JsonResponse(
        {"version": str(stand.get("version", "")), "final": bool(stand.get("final"))}
    )
    response["Cache-Control"] = "no-cache"
    return response


@require_GET
@site_view()
def result_series(request, site: Site, kennung: str):
    """Archiv einer Reihe: Sieger je Jahr und Titel über alle Jahre."""
    if not _results_on(site) or not TOKEN.match(kennung):
        raise api.NotFound()
    data = site.get(f"results/series/{kennung}/")
    for y in data.get("years", []):
        y["kennung"] = _token_of(y.get("url"))
    return _page(request, "seite/ergebnis_reihe.html", site, {"s": data})


def _token_of(url: str | None) -> str | None:
    """Kennung eines Wettbewerbs aus seiner Adresse bei HUBIplan (…/results/<kennung>/)."""
    m = re.search(r"/results/([a-f0-9]{20})/$", url or "")
    return m.group(1) if m else None


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
    if site.info.get("statute_url"):
        docs.append(
            {
                "title": _("Satzung"),
                "url": site.info["statute_url"],
                "kind": "§",
                # Erste Seite als Bild (ältere HUBIplan-Stände: nur das Symbol)
                "preview": site.local(site.info.get("statute_preview_url")),
            }
        )
    if site.info.get("fee_rules_url"):
        docs.append(
            {
                "title": _("Beitragsordnung"),
                "url": site.info["fee_rules_url"],
                "kind": "€",
                "preview": site.local(site.info.get("fee_rules_preview_url")),
            }
        )
    if site.info.get("founding_deed_url"):
        docs.append(
            {
                "title": _("Gründungsurkunde"),
                "url": site.info["founding_deed_url"],
                "kind": "§",
                "preview": site.local(site.info.get("founding_deed_preview_url")),
            }
        )
    if not docs:
        raise api.NotFound()
    return _page(request, "seite/dokumente.html", site, {"documents": docs})


@require_GET
@site_view()
def page(request, site: Site, slug: str):
    if slug == "geschichte":
        return HttpResponseRedirect(reverse("chronik"))
    return _page(request, "seite/textseite.html", site, {"page": site.get(f"pages/{slug}/")})


def _contact_recipient(recipients: list, wanted: str) -> dict | None:
    """Fester Empfänger statt Auswahl (Ralf 31.10.): kommt man über „Nachricht schreiben“
    bei einer Rolle (?an=…), geht die Nachricht dorthin; sonst an den Verein allgemein."""
    by_id = {r.get("id"): r for r in recipients if r.get("id")}
    r = by_id.get(wanted) or by_id.get("allgemein") or (recipients[0] if recipients else None)
    if not r:
        return None
    name = r.get("name", "")
    if r.get("id") == "allgemein" and name.endswith(" (allgemein)"):
        name = name[: -len(" (allgemein)")]
    return {"id": r["id"], "name": name}


@require_GET
@site_view()
def contact(request, site: Site):
    if not site.block("contact"):
        raise api.NotFound()
    data = site.get("contact/", cached=False)
    response = _page(
        request,
        "seite/kontakt.html",
        site,
        {
            "recipient": _contact_recipient(
                data.get("recipients") or [], request.GET.get("an", "")
            ),
            "challenge": data.get("challenge", {}),
            "post_url": f"{settings.HUBIPLAN_PUBLIC_URL}{api.PREFIX}{site.key}/contact/",
            "preview_session": site.preview if site.is_preview else "",
        },
    )
    response["Cache-Control"] = "private, no-store"
    return response


@require_GET
@site_view()
def contact_challenge(request, site: Site):
    """Neue Rechenaufgabe ohne Neuladen der Seite (UX-Audit 31.10. S03)."""
    if not site.block("contact"):
        raise api.NotFound()
    challenge = site.get("contact/", cached=False).get("challenge") or {}
    response = JsonResponse(
        {k: challenge.get(k) for k in ("token", "salt", "difficulty")},
    )
    response["Cache-Control"] = "private, no-store"
    return response


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
    """Freiwillige Erklärung zur Barrierefreiheit (Barrierefreiheit X-02)."""
    return _page(
        request,
        "seite/barrierefreiheit.html",
        site,
        {"contact_enabled": site.block("contact") and not site.maintenance},
    )


# --- Vorschau ---


@require_GET
def preview(request):
    """Vorschau-Schlüssel aus HUBIplan gegen ein Vorschau-Cookie tauschen."""
    token = request.GET.get("schluessel", "")
    if not token or len(token) > 500:
        return error_page(request, 400, _("Vorschau"), _("Der Vorschau-Link ist unvollständig."))
    try:
        key = api.resolve(_host(request))
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
    response["Cache-Control"] = "private, no-store"
    return response


def _set_design_cookie(response, design: str) -> None:
    path = settings.BASE_PATH + "/" if settings.BASE_PATH else "/"
    if design in DESIGNS:
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


@require_GET
def preview_design(request):
    """In der Vorschau ein anderes Design zeigen (?design=…) oder zurück zum gewählten."""
    response = HttpResponseRedirect(reverse("start"))
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


# --- Bilder und Logos über diese Seite ---

ALLOWED_API_FILES = re.compile(
    r"^(images/[A-Za-z0-9_\-]{4,40}/|photos/[a-f0-9]{20}/|honors/photos/[a-f0-9]{20}/"
    r"|posts/images/[A-Za-z0-9_\-]{4,40}/|statute/preview/|fee-rules/preview/"
    r"|founding-deed/preview/)$"
)
ALLOWED_MEDIA = re.compile(r"^[A-Za-z0-9_\-/.]{1,300}\.(png|jpe?g|webp)$")


@require_GET
@site_view(maintenance_ok=True)
def media(request, site: Site, kind: str, path: str):
    if kind == "a":
        if not ALLOWED_API_FILES.match(path):
            raise api.NotFound()
        if site.maintenance and not site.is_preview:
            raise api.NotFound()
        size = "?size=small" if request.GET.get("size") == "small" else ""
        res = api.fetch_file(f"{api.PREFIX}{site.key}/{path}{size}", preview=site.preview)
    else:
        if ".." in path or not ALLOWED_MEDIA.match(path):
            raise api.NotFound()
        res = api.fetch_file(f"/media/{path}")
    ctype = res.content_type.split(";")[0].strip()
    if ctype not in ("image/png", "image/jpeg", "image/webp"):
        raise api.NotFound()
    response = HttpResponse(res.body, content_type=ctype)
    # Vorschau und Wartung: nur im eigenen Browser zwischenspeichern, nicht in fremden
    # Zwischenspeichern; sonst lädt z. B. das Wappen bei jedem Seitenwechsel neu
    response["Cache-Control"] = (
        "private, max-age=600" if site.is_preview or site.maintenance else "public, max-age=600"
    )
    response["Content-Security-Policy"] = "default-src 'none'; sandbox"
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
