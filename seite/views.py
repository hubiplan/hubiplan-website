"""Seiten der Vereinswebseite.

Jede Seite lädt die Webseite zur Anfrage (Hostname → Schlüssel → Grunddaten).
Im Wartungsmodus gibt es nur Wartungsseite, Impressum und Datenschutz, außer mit
gültiger Vorschau.
"""

from __future__ import annotations

import calendar as kalender
import datetime
import functools
import io
import logging
import re
from collections import OrderedDict
from urllib.parse import quote

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

from . import api, archiv, designpaket
from .site import (
    DESIGN_COOKIE,
    DESIGNS,
    PREVIEW_COOKIE,
    SITE_COOKIE,
    Site,
    chosen_host,
    global_maintenance,
    gradient_css,
    host_of,
    load,
    preview_session,
)
from .templatetags.seite import web_ziel
from .zeitleiste import gliedern

log = logging.getLogger(__name__)


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


def _event(e) -> dict | None:
    """Termin aus HUBIplan mit Beginn und Ende in Ortszeit (None ohne Beginn)."""
    if not isinstance(e, dict):
        return None
    start = parse_datetime(e["starts_at"]) if e.get("starts_at") else None
    end = parse_datetime(e["ends_at"]) if e.get("ends_at") else None
    if start is None:
        return None
    start = timezone.localtime(start)
    end = timezone.localtime(end) if end else None
    return {**e, "start": start, "end": end}


def _events(site: Site, unit: str | None = None) -> list[dict]:
    path = "events/" + (f"?einheit={unit}" if unit else "")
    events = []
    for e in site.get(path).get("events", []):
        event = _event(e)
        if event is not None:
            events.append(event)
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


def _calendar(events: list[dict]) -> list[dict]:
    """Monatskalender (G5): je Monat mit Terminen ein Blatt, Woche ab Montag. Ein Termin
    steht an seinem ersten Tag."""
    months: OrderedDict[tuple[int, int], dict] = OrderedDict()
    for e in events:
        day = e["start"].date()
        months.setdefault((day.year, day.month), {}).setdefault(day, []).append(e)
    today = timezone.localdate()
    result = []
    for (year, month), days in months.items():
        weeks = kalender.Calendar(firstweekday=0).monthdatescalendar(year, month)
        result.append(
            {
                "title": formats.date_format(datetime.date(year, month, 1), "F Y"),
                "weekdays": [formats.date_format(d, "D") for d in weeks[0]],
                "weeks": [
                    [
                        {
                            "date": d,
                            "in_month": d.month == month,
                            "today": d == today,
                            "events": days.get(d, []) if d.month == month else [],
                        }
                        for d in week
                    ]
                    for week in weeks
                ],
            }
        )
    return result


def _area(site: Site, area: str) -> dict:
    """Darstellung und Einleitung eines festen Bereichs (G5) für die Vorlage."""
    return {"darstellung": site.layout(area), "einleitung": site.intro(area)}


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

# Eigene Abschnitte der Startseite (G3, Ralf 10.11.2026) → Vorlage unter seite/start/
CUSTOM_SECTIONS = {
    "text": "text",
    "text_image": "text_bild",
    "banner": "banner",
    "buttons": "knoepfe",
    "tiles": "kacheln",
    "event": "termin",
    "album": "album",
    "quote": "zitat",
    "contacts": "ansprechpartner",
    "faq": "fragen",
    "partners": "partner",
    "directions": "anfahrt",
    "event_list": "terminliste",
    "document": "dokument",
    "video": "video",
    "chronicle": "chronik",
    "facts": "zahlen",
    "divider": "trenner",
    "countdown": "countdown",
}
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
PALETTE_BG = re.compile(r"^p([0-9])$")
GRADIENT_BG = re.compile(r"^g([01])$")


def _look(site: Site, s: dict) -> dict:
    """Breite und Hintergrund eines Abschnitts als Klassen und Stil (nur feste Werte)."""
    klassen = []
    width = s.get("width")
    if width == "text":
        klassen.append("abschnitt-text")
    elif width == "full":
        klassen.append("abschnitt-voll")
    stil = ""
    bg = s.get("bg")
    if bg == "light":
        klassen.append("abschnitt-hg")
        stil = "background:var(--abschnitt-hell);color:var(--text)"
    elif isinstance(bg, str) and (m := PALETTE_BG.match(bg)):
        palette = site.info.get("palette") or []
        i = int(m.group(1))
        entry = palette[i] if isinstance(palette, list) and i < len(palette) else None
        color = entry.get("color") if isinstance(entry, dict) else None
        on = entry.get("on_color") if isinstance(entry, dict) else None
        if isinstance(color, str) and isinstance(on, str) and HEX.match(color) and HEX.match(on):
            klassen.append("abschnitt-hg")
            klassen.append("abschnitt-farbig")
            stil = f"background:{color};color:{on};--abschnitt-auf:{on}"
    elif isinstance(bg, str) and (m := GRADIENT_BG.match(bg)):
        # Verlauf aus Einstellungen › Erscheinungsbild (HUBIplan ab 10.11.2026)
        gradients = site.info.get("gradients") or []
        i = int(m.group(1))
        entry = gradients[i] if isinstance(gradients, list) and i < len(gradients) else None
        entry = entry if isinstance(entry, dict) else {}
        pair = entry.get("colors")
        on = entry.get("on_color")
        css = None
        if isinstance(pair, list) and len(pair) == 2:
            css = gradient_css(
                {"from": pair[0], "to": pair[1], "direction": entry.get("direction")}
            )
        if css and isinstance(on, str) and HEX.match(on):
            klassen.append("abschnitt-hg")
            klassen.append("abschnitt-farbig")
            stil = f"background:{pair[0]};background-image:{css};color:{on};--abschnitt-auf:{on}"
    return {"klassen": klassen, "stil": stil}


def _layout(site: Site) -> list[dict]:
    """Abschnitte der Startseite in Reihenfolge mit Vorlage, Gestaltung und Inhalt.

    Ältere HUBIplan-Stände ohne ``home_layout``: die festen Bausteine aus ``home``."""
    layout = site.info.get("home_layout")
    if not isinstance(layout, list):
        layout = [
            {"key": k, "kind": k, "column": "side" if k in SIDE_SECTIONS else "main"}
            for k in _home(site)
        ]
    return _layout_entries(site, layout)


def _countdown(s: dict) -> dict | None:
    """Countdown (HUBIplan ab 14.11.2026): Ziel mit Zeitzone; der Browser zählt weiter
    (countdown.js). Ohne Skript steht der Stand beim Laden da. Nach Ablauf verschwindet
    der Abschnitt, außer HUBIplan schickt einen Text dafür."""
    after = s.get("after_text") if isinstance(s.get("after_text"), str) else ""
    target = (
        parse_datetime(s["target"]) if isinstance(s.get("target"), str) and s["target"] else None
    )
    if target is not None and timezone.is_naive(target):
        target = None
    texte = {k: s.get(k) if isinstance(s.get(k), str) else "" for k in ("title", "name", "text")}
    now = timezone.now()
    if target is None or target <= now:
        return {**texte, "ziel": None, "danach": after} if after else None
    left = int((target - now).total_seconds())
    return {
        **texte,
        "ziel": timezone.localtime(target),
        "ziel_iso": target.isoformat(),
        "danach": after,
        "rest": {
            "tage": left // 86400,
            "stunden": left % 86400 // 3600,
            "minuten": left % 3600 // 60,
            "sekunden": left % 60,
        },
    }


def _layout_entries(site: Site, layout: list) -> list[dict]:
    result = []
    for s in layout:
        if not isinstance(s, dict):
            continue
        kind = s.get("kind")
        if kind in HOME_SECTIONS:
            name = kind
        elif kind in CUSTOM_SECTIONS:
            name = CUSTOM_SECTIONS[kind]
        else:
            continue
        entry = {**s, "vorlage": f"seite/start/{name}.html", **_look(site, s)}
        if kind == "event":
            event = _event(s.get("event"))
            if event is None:
                continue
            # Countdown in Tagen (Ortszeit); am Tag selbst „heute“
            entry["event"] = event
            entry["tage"] = (event["start"].date() - timezone.localdate()).days
        elif kind == "countdown":
            countdown = _countdown(s)
            if countdown is None:
                continue
            entry.update(countdown)
        elif kind == "event_list":
            events = [e for e in map(_event, s.get("events") or []) if e is not None]
            if not events:
                continue
            entry["events"] = events
        result.append(entry)
    return result


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
    layout = _layout(site)
    home = [s["kind"] for s in layout if s["kind"] in HOME_SECTIONS]
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
            # Abschnitte mit Gestaltung (G3); Zeitung: Spalte je Abschnitt aus HUBIplan
            "abschnitte": layout,
            "abschnitte_seite": [s for s in layout if s.get("column") == "side"],
            "abschnitte_haupt": [s for s in layout if s.get("column") != "side"],
            # Für Designpakete mit eigener start.html: nur die Vorlagen wie bisher
            "sections": [s["vorlage"] for s in layout],
            "sections_side": [s["vorlage"] for s in layout if s.get("column") == "side"],
            "sections_main": [s["vorlage"] for s in layout if s.get("column") != "side"],
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
            **_area(site, "board"),
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
    area = _area(site, "events")
    return _page(
        request,
        "seite/termine.html",
        site,
        {
            **area,
            "months": _by_month(items),
            "kalender": _calendar(items) if area["darstellung"] == "calendar" else [],
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
    """Neuester veröffentlichter Wettbewerb direkt, ältere als Links im Archiv."""
    if not _results_on(site):
        raise api.NotFound()
    data = site.get("results/", seconds=OVERVIEW_SECONDS)
    comps = [_with_date(c) for c in data.get("competitions", [])]
    # HUBIplan liefert veröffentlichte Wettbewerbe nach Datum absteigend.
    latest = _result(site, comps[0]["id"]) if comps else None
    older = comps[1:]
    response = _page(
        request,
        "seite/ergebnisse.html",
        site,
        {
            "latest": latest,
            "live": [c for c in older if not c.get("final")],
            "years": _by_year([c for c in older if c.get("final")]),
            "series": data.get("series", []),
            "trophies": data.get("trophies", []),
        },
    )
    if latest and not latest.get("final"):
        response["Cache-Control"] = "no-cache"
    return response


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
    response = _page(
        request,
        "seite/ergebnis_inhalt.html",
        site,
        {"c": data, "embedded": request.GET.get("eingebettet") == "1"},
    )
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
def bookings(request, site: Site):
    """Belegung von Schützenhaus, Stand oder Material (nur „belegt“ bzw. öffentliche Zwecke)."""
    if not site.block("bookings"):
        raise api.NotFound()
    try:
        start = datetime.date.fromisoformat(request.GET.get("ab") or "")
    except ValueError:
        start = timezone.localdate()
    start -= datetime.timedelta(days=start.weekday())
    data = site.get(f"bookings/?start={start.isoformat()}")
    titles = {i["id"]: i["title"] for i in data.get("items", [])}
    days = OrderedDict((start + datetime.timedelta(days=n), []) for n in range(7))
    for row in data.get("occurrences", []):
        begin = parse_datetime(row.get("starts_at") or "")
        end = parse_datetime(row.get("ends_at") or "")
        if begin is None or end is None:
            continue
        begin, end = timezone.localtime(begin), timezone.localtime(end)
        last = (end - datetime.timedelta(seconds=1)).date()
        for day in days:
            if begin.date() <= day <= last:
                days[day].append(
                    {
                        "objekt": titles.get(row.get("item"), ""),
                        "titel": row.get("title", ""),
                        "beginn": begin if begin.date() == day else None,
                        "ende": end if end.date() == day else None,
                        "ganztags": row.get("all_day", False),
                    }
                )
    ics = data.get("ics_url")
    return _page(
        request,
        "seite/belegung.html",
        site,
        {
            "tage": list(days.items()),
            "objekte": data.get("items", []),
            "vorher": (start - datetime.timedelta(days=7)).isoformat(),
            "nachher": (start + datetime.timedelta(days=7)).isoformat(),
            "ics_url": ics,
            "webcal_url": _webcal(ics),
            "qr": mark_safe(_qr_svg(_webcal(ics))) if ics else "",  # noqa: S308
        },
    )


@require_GET
@site_view()
def repertoire(request, site: Site):
    if not site.block("repertoire"):
        raise api.NotFound()
    pieces = site.get("repertoire/").get("pieces", [])
    return _page(request, "seite/repertoire.html", site, {"stuecke": pieces})


@require_GET
@site_view()
def press(request, site: Site):
    if not site.block("press"):
        raise api.NotFound()
    items = []
    for d in site.get("documents/?section=press").get("documents", []):
        try:
            when = datetime.date.fromisoformat(d["date"]) if d.get("date") else None
        except ValueError:
            when = None
        items.append(
            {
                **d,
                "when": when,
                "url": site.local(d.get("url")),
                "preview": site.local(d.get("preview_url")),
            }
        )
    return _page(request, "seite/presse.html", site, {"artikel": items})


SEARCH_MAX = 100


def _search_url(site: Site, hit: dict) -> str | None:
    kind = hit.get("kind")
    if kind == "page" and hit.get("slug"):
        return reverse("seite", args=[hit["slug"]])
    if kind == "history":
        return reverse("chronik")
    if kind == "memorial":
        return reverse("gedenken")
    if kind == "album" and hit.get("slug"):
        return reverse("album", args=[hit["slug"]])
    if kind == "press":
        return reverse("presse")
    if kind == "documents":
        return reverse("dokumente")
    if kind == "event":
        return reverse("termine")
    # Startseite, Untereinheiten und Einleitungen der Bereiche (HUBIplan ab 14.11.2026)
    if kind == "home":
        return reverse("start")
    if kind == "unit" and hit.get("slug"):
        return reverse("einheit", kwargs={"pfad": site.units_path, "slug": hit["slug"]})
    if kind == "intro":
        if hit.get("area") == "units":
            return reverse("einheiten", kwargs={"pfad": site.units_path})
        name = {"board": "vorstand", "events": "termine", "gallery": "galerie"}.get(hit.get("area"))
        return reverse(name) if name else None
    return None


def _search_title(site: Site, hit: dict) -> str:
    """Überschrift für Treffer ohne eigene, etwa ein Banner der Startseite."""
    if hit.get("kind") == "home":
        return _("Startseite")
    if hit.get("kind") == "intro":
        area = hit.get("area")
        if area == "units":
            return site.info.get("unit_label_plural") or ""
        return {"board": _("Vorstand"), "events": _("Termine"), "gallery": _("Galerie")}.get(
            area, ""
        )
    return ""


@require_GET
@site_view()
def search(request, site: Site):
    if not site.block("search"):
        raise api.NotFound()
    query = " ".join((request.GET.get("q") or "").split())[:SEARCH_MAX]
    hits = []
    if query:
        data = site.get(f"search/?q={quote(query)}", cached=False)
        for h in data.get("results", []):
            url = _search_url(site, h)
            if not url:
                continue
            start = parse_datetime(h["starts_at"]) if h.get("starts_at") else None
            if not h.get("title"):
                h = {**h, "title": _search_title(site, h)}
            hits.append({**h, "url": url, "start": timezone.localtime(start) if start else None})
    return _page(request, "seite/suche.html", site, {"query": query, "treffer": hits})


@require_GET
@site_view()
def page(request, site: Site, slug: str):
    if slug == "geschichte":
        return HttpResponseRedirect(reverse("chronik"))
    data = site.get(f"pages/{slug}/")
    # Abschnitte (G4): ohne eigene Abschnitte sieht die Seite aus wie bisher
    sections = data.get("sections") if isinstance(data, dict) else None
    sections = sections if isinstance(sections, list) else []
    # Titelbild (G6) steht immer über der Überschrift, nicht zwischen den Abschnitten
    cover = next((x for x in sections if isinstance(x, dict) and x.get("kind") == "cover"), None)
    layout = _page_layout(site, [x for x in sections if x is not cover])
    # Auch ohne weitere Abschnitte gelten Breite und Hintergrund des Textes der Seite (#77)
    custom = any(s["kind"] != "body" or s["klassen"] or s["stil"] for s in layout)
    return _page(
        request,
        "seite/textseite.html",
        site,
        {
            "page": data,
            "abschnitte": layout if custom else [],
            "titelbild": cover if cover and isinstance(cover.get("image"), dict) else None,
        },
    )


def _page_layout(site: Site, sections: list) -> list[dict]:
    """Abschnitte einer Textseite: fester Abschnitt „body“ (Bild und Text) und eigene."""
    result = []
    for s in sections:
        if isinstance(s, dict) and s.get("kind") == "body":
            result.append({**s, "vorlage": "seite/seite_text.html", **_look(site, s)})
        elif isinstance(s, dict) and s.get("kind") in CUSTOM_SECTIONS:
            result.extend(_layout_entries(site, [s]))
    return result


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
def join(request, site: Site):
    """Mitglied werden: Einleitung, Mitgliedsarten mit Beitrag und Link zum Antrag in HUBIplan.
    Die Webseite nimmt selbst keine Angaben an (hubiplan konzepte/online-beitrittsformular.md)."""
    if not site.block("join"):
        raise api.NotFound()
    data = site.get("join/")
    form_url = data.get("form_url") or ""
    if not form_url.startswith(("https://", "http://")):
        raise api.NotFound()
    units = [
        {"name": u["name"], "url": f"{form_url}?einheit={int(u['id'])}"}
        for u in data.get("units") or []
        if isinstance(u, dict) and u.get("name") and str(u.get("id", "")).isdigit()
    ]
    return _page(
        request,
        "seite/mitglied_werden.html",
        site,
        {
            "einleitung": data.get("intro") or "",
            "arten": data.get("types") or [],
            "lastschrift": data.get("sepa") in ("offer", "required"),
            "formular": form_url,
            "einheiten_links": units,
        },
    )


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


# --- Bilder und Logos über diese Seite ---

ALLOWED_API_FILES = re.compile(
    r"^(images/[A-Za-z0-9_\-]{4,40}/|photos/[a-f0-9]{20}/|honors/photos/[a-f0-9]{20}/"
    r"|posts/images/[A-Za-z0-9_\-]{4,40}/|statute/preview/|fee-rules/preview/"
    r"|founding-deed/preview/|files/[A-Za-z0-9_\-]{8,24}/"
    # Favicon und Handy-Symbol (Wappen quadratisch, Ralf 09.11.2026)
    r"|icon-(?:32|180|192|512)\.png)$"
)
ALLOWED_MEDIA = re.compile(r"^[A-Za-z0-9_\-/.]{1,300}\.(png|jpe?g|webp)$")


# Adressen, die sich bei jeder Änderung ändern: Logos mit Zeitstempel im Namen
# (logos/…/<id>-<JJJJMMTThhmmss>.png), Webseitenbilder mit Fassung (images/<key>-v3/)
LOGO_STAMPED = re.compile(r"^logos/.+-\d{14}\.(png|jpe?g|webp)$")
IMAGE_VERSIONED = re.compile(r"^images/[A-Za-z0-9_\-]+-v\d+/$")


# Bilder in der Vorschau: Seiten und Daten prüft HUBIplan bei jedem Aufruf (Widerruf
# wirkt sofort), Bilder darf aber der eigene Browser kurz behalten. Sonst lädt jeder
# Seitenwechsel alle Bilder neu, und jedes kostet einen Abruf in HUBIplan.
PREVIEW_MEDIA_CACHE = "private, max-age=300"


def _media_cache(private: bool, kind: str, path: str) -> str:
    """Wie lange der Browser ein Bild behalten darf. Vorschau und Wartung: nur der eigene
    Browser, 10 Minuten (sonst lädt z. B. das Wappen bei jedem Seitenwechsel neu)."""
    if private:
        return "private, max-age=600"
    if kind == "m" and LOGO_STAMPED.match(path):
        return "public, max-age=31536000, immutable"
    if kind == "a" and IMAGE_VERSIONED.match(path):
        # Ein Tag: Ein aus der Webseite genommenes Bild verschwindet so bald auch aus
        # fremden Zwischenspeichern
        return "public, max-age=86400"
    return "public, max-age=600"


@require_GET
def media(request, kind: str, path: str):
    """Bild aus HUBIplan über diese Seite. Ohne die Grunddaten der Seite: Ob ein Bild
    gezeigt werden darf (Wartung, Vorschau), prüft HUBIplan beim Bild selbst. Sonst
    wartete jedes Bild erneut auf die Grunddaten."""
    if global_maintenance():
        return HttpResponse(status=503)
    preview = preview_session(request)
    try:
        key = api.resolve(host_of(request))
        if kind == "a":
            if not ALLOWED_API_FILES.match(path):
                raise api.NotFound()
            size = "?size=small" if request.GET.get("size") == "small" else ""
            res = api.fetch_file(f"{api.PREFIX}{key}/{path}{size}", preview=preview)
        else:
            if ".." in path or not ALLOWED_MEDIA.match(path):
                raise api.NotFound()
            res = api.fetch_file(f"/media/{path}")
    except api.NotFound:
        return HttpResponse(status=404)
    except api.Unavailable:
        return HttpResponse(status=503)
    ctype = res.content_type.split(";")[0].strip()
    # PDF nur bei Dokumenten der Webseite (Pressespiegel, Ralf 05.11.)
    pdf_ok = kind == "a" and path.startswith("files/")
    if ctype not in ("image/png", "image/jpeg", "image/webp") and not (
        pdf_ok and ctype == "application/pdf"
    ):
        return HttpResponse(status=404)
    response = HttpResponse(res.body, content_type=ctype)
    if ctype == "application/pdf":
        response["Content-Disposition"] = "inline"
    # Mit Vorschau oder in der Wartung nur im eigenen Browser; der Zustand steht im
    # Zwischenspeicher der Grunddaten, wenn eine Seite davor geladen wurde
    private = bool(preview) or api.cached_maintenance(key)
    response["Cache-Control"] = (
        PREVIEW_MEDIA_CACHE if preview else _media_cache(private, kind, path)
    )
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
