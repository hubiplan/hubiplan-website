"""Termine: Aufbereitung, Kalender, Abo-Adressen, Terminseite, Belegung."""

from __future__ import annotations

import calendar as kalender
import datetime
import io
import re
from collections import OrderedDict

import qrcode
import qrcode.image.svg
from django.conf import settings
from django.utils import formats, timezone, translation
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_GET

from .. import api
from ..daten import Termin
from ..site import (
    Site,
)
from .rahmen import _area, _page, site_view

# --- Termine ---


def _event(e, site: Site | None = None) -> Termin | None:
    """Termin aus HUBIplan mit Beginn und Ende in Ortszeit (None ohne Beginn).

    ``anhaenge``: in HUBIplan einzeln für die Webseite freigegebene Anhänge, über diese
    Seite ausgeliefert (ältere Stände von HUBIplan liefern keine)."""
    if not isinstance(e, dict):
        return None
    start = parse_datetime(e["starts_at"]) if e.get("starts_at") else None
    end = parse_datetime(e["ends_at"]) if e.get("ends_at") else None
    if start is None:
        return None
    start = timezone.localtime(start)
    end = timezone.localtime(end) if end else None
    files = []
    for a in (e.get("attachments") or []) if site is not None else []:
        url = site.local(a.get("url")) if isinstance(a, dict) else None
        if url:
            files.append({"name": a.get("name") or "", "kind": a.get("kind") or "", "url": url})
    return Termin.aus(
        e,
        start=start,
        end=end,
        anhaenge=files,
        anmeldung=_anmeldung(e.get("registration")),
        # Veranstaltungsseite (HUBIplan A4): Adresse, nur wenn sie als Adresse taugt
        page=e["page"] if _ist_adresse(e.get("page")) else None,
    )


def _ist_adresse(value) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value) is not None


ANMELDE_STAENDE = ("not_yet", "open", "closed", "full", "cancelled")


def _anmeldung(r) -> dict | None:
    """Öffentliche Anmeldung am Termin (HUBIplan A4): Stand, Preise, freie Plätze, Link.

    Ältere Stände von HUBIplan liefern nichts; dann bleibt die Karte wie bisher. Texte
    entstehen hier in der Sprache der Seite, Namen der Tarife kommen aus HUBIplan."""
    if not isinstance(r, dict):
        return None
    url = r.get("url") or ""
    if not isinstance(url, str) or not url.startswith(("https://", "http://")):
        return None
    state = r.get("state") if r.get("state") in ANMELDE_STAENDE else "closed"
    english = (translation.get_language() or "de")[:2] == "en"
    prices = []
    for p in r.get("prices") or []:
        if not isinstance(p, dict) or p.get("amount") in (None, ""):
            continue
        name = (p.get("name_en") if english else "") or p.get("name") or ""
        until = parse_date(p["until_date"]) if p.get("until_date") else None
        prices.append({"name": name, "amount": p["amount"], "until": until})
    opens = parse_datetime(r["opens_at"]) if r.get("opens_at") else None
    closes = parse_datetime(r["closes_at"]) if r.get("closes_at") else None
    free = r.get("free")
    return {
        "url": url,
        "state": state,
        "can_join": bool(r.get("can_join")) and state in ("open", "full"),
        "waitlist": bool(r.get("waitlist")),
        "free": free if isinstance(free, int) and free >= 0 else None,
        "opens": timezone.localtime(opens) if opens else None,
        "closes": timezone.localtime(closes) if closes else None,
        "prices": prices,
    }


def _events(site: Site, unit: str | None = None) -> list[Termin]:
    path = "events/" + (f"?einheit={unit}" if unit else "")
    events = []
    for e in site.get(path).get("events", []):
        event = _event(e, site)
        if event is not None:
            events.append(event)
    events.sort(key=lambda e: e.start)
    return events


def _anzahl(value) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _zeit(value):
    try:
        return parse_datetime(value) if isinstance(value, str) else None
    except ValueError:
        return None


def _upcoming(events: list[Termin], limit: int | None = None) -> list[Termin]:
    now = timezone.now()
    today = timezone.localdate()
    result = [
        e for e in events if (e.end or e.start) >= now or (e.all_day and e.start.date() >= today)
    ]
    return result[:limit] if limit else result


def _by_month(events: list[Termin]) -> list[tuple[str, list[Termin]]]:
    groups: OrderedDict[str, list[Termin]] = OrderedDict()
    for e in events:
        groups.setdefault(formats.date_format(e.start, "F Y"), []).append(e)
    return list(groups.items())


def _calendar(events: list[Termin]) -> list[dict]:
    """Monatskalender (G5): je Monat mit Terminen ein Blatt, Woche ab Montag. Ein Termin
    steht an seinem ersten Tag."""
    months: OrderedDict[tuple[int, int], dict] = OrderedDict()
    for e in events:
        day = e.start.date()
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
