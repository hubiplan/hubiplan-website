"""Suche, Textseiten, Veranstaltungsseiten, Kontakt und Mitglied werden."""

from __future__ import annotations

import re
from urllib.parse import quote

from django.conf import settings
from django.http import (
    HttpResponseRedirect,
    JsonResponse,
)
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET

from .. import api, markdown
from ..site import (
    Site,
)
from .aufbau import _page_layout
from .rahmen import _page, site_view
from .termine import _event

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
    if kind == "news" and re.fullmatch(r"[-a-z0-9]+", str(hit.get("slug") or "")):
        return reverse("beitrag", args=[hit["slug"]])
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
        name = {
            "board": "vorstand",
            "events": "termine",
            "gallery": "galerie",
            "contact": "kontakt",
        }.get(hit.get("area"))
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
        return {
            "board": _("Vorstand"),
            "events": _("Termine"),
            "gallery": _("Galerie"),
            "contact": _("Kontakt"),
        }.get(area, "")
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
    return _text_page(request, site, slug, event_url=False)


@require_GET
@site_view()
def event_page(request, site: Site, slug: str):
    """Veranstaltungsseite (HUBIplan A4): Textseite zu einem öffentlichen Termin."""
    return _text_page(request, site, slug, event_url=True)


def _veranstaltung(data, site: Site) -> dict | None:
    """Eckdaten des Termins einer Veranstaltungsseite (ältere Stände von HUBIplan: None)."""
    e = data.get("event") if isinstance(data, dict) else None
    if not isinstance(e, dict):
        return None
    event = _event({**e, "id": "v"}, site)
    if event is None:
        return None
    reg = e.get("registration") if isinstance(e.get("registration"), dict) else {}
    if event["anmeldung"] is not None:
        event["anmeldung"]["terms"] = str(reg.get("terms") or "")
        event["anmeldung"]["cancel_text"] = str(reg.get("cancel_text") or "")
    return event


def _text_page(request, site: Site, slug: str, event_url: bool):
    data = site.get(f"pages/{slug}/")
    veranstaltung = _veranstaltung(data, site)
    # Eine Adresse je Seite: Veranstaltungsseiten unter /veranstaltung/, die übrigen unter /seite/
    if event_url and veranstaltung is None and not (isinstance(data, dict) and data.get("event")):
        raise api.NotFound
    if not event_url and isinstance(data, dict) and data.get("event"):
        return HttpResponseRedirect(reverse("veranstaltung", args=[slug]))
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
            "veranstaltung": veranstaltung,
            "abschnitte": layout if custom else [],
            "titelbild": cover if cover and isinstance(cover.get("image"), dict) else None,
        },
    )


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


def _contact_box(site: Site) -> dict | None:
    """Kasten neben dem Kontaktformular (Webseite #137): Einleitung des Bereichs „Kontakt“
    aus HUBIplan (Überschrift, Text; ein Link allein im letzten Absatz wird zum Knopf).
    Ohne Inhalt bleibt die Seite einspaltig."""
    intro = site.intro("contact")
    if not intro:
        return None
    title = intro.get("title") if isinstance(intro.get("title"), str) else ""
    body = markdown.render(intro.get("text") or "", site.units_path)
    if not (title.strip() or body):
        return None
    return {"title": title.strip(), "html": markdown.last_link_as_button(body)}


def _contact_details(site: Site) -> dict | None:
    """Zweiter Kontaktweg neben dem Formular (UX-Audit 16.11. WS-13): Anschrift, Telefon und
    E-Mail aus den Vereinsdaten, sofern vorhanden. Abschaltbar mit dem Regler contact_details."""
    if site.style.get("contact_details") == "off":
        return None
    info = site.info
    address = info.get("address") if isinstance(info.get("address"), dict) else {}
    street = str(address.get("street") or "").strip()
    place = " ".join(
        str(address.get(k) or "").strip() for k in ("postal_code", "city") if address.get(k)
    )
    phone = str(info.get("phone") or "").strip()
    email = str(info.get("email") or "").strip()
    tel = re.sub(r"[^0-9+]", "", phone)
    details = {
        "name": str(info.get("name") or "").strip(),
        "street": street,
        "place": place,
        "phone": phone,
        "tel": tel if len(tel) >= 4 else "",
        "email": email if "@" in email else "",
    }
    if not (street or place or phone or details["email"]):
        return None
    return details


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
            "kasten": _contact_box(site),
            "angaben": _contact_details(site),
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
