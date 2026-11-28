"""Hilfen für Menü, Adressen und Linkziele."""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html
from django.utils.translation import gettext as _

from .register import register


@register.simple_tag
def einheiten_url(site):
    return reverse("einheiten", kwargs={"pfad": site.units_path})


@register.simple_tag
def einheit_url(site, slug):
    return reverse("einheit", kwargs={"pfad": site.units_path, "slug": slug})


@register.simple_tag(takes_context=True)
def menue(context):
    """Menüpunkte je nach eingeschalteten Bereichen."""
    site = context.get("site")
    if site is None or site.maintenance and not site.is_preview:
        return []
    info = site.info
    # „Start“ setzt die Webseite selbst davor; am Bildschirm ausblendbar (Stilregler nav_start)
    items = [(_("Start"), reverse("start"), {"start": True})]
    nav = info.get("nav")
    if isinstance(nav, list):
        items += _nav_items(site, nav)
    else:
        items += _legacy_items(site)
    path = context["request"].path
    start = reverse("start")

    def entry(label, url, extra=None):
        if isinstance(url, list):
            children = [entry(*c) for c in url]
            return {
                "label": label,
                "children": children,
                "active": any(c["active"] for c in children),
            }
        extra = extra or {}
        if extra.get("extern"):
            # Link nach außen (Ralf 10.11.): neuer Tab, nie „aktiv“
            return {"label": label, "url": url, "active": False, **extra}
        return {
            "label": label,
            "url": url,
            "active": path == url or (url != start and path.startswith(url)),
            **extra,
        }

    return [entry(*item) for item in items]


@register.simple_tag(takes_context=True)
def menue_teile(context, punkte):
    """Menüpunkte je Ort (Webseite #75): ``breit`` (Menüleiste am Bildschirm), ``handy``
    (Aufklappmenü) und ``fuss`` (Links im Fuß). Punkte „nur im Fuß“ fehlen in beiden Menüs;
    „Start“ fehlt am Bildschirm, wenn der Stilregler ``nav_start`` aus ist (Logo und Kopfbild
    führen dann zur Startseite), im Handymenü bleibt er."""
    site = context.get("site")
    style = site.style if site is not None else {}
    ohne_start = style.get("nav_start") == "off"
    handy = [p for p in punkte if p.get("place") != "footer"]
    breit = [p for p in handy if not (ohne_start and p.get("start"))]
    fuss = [p for p in punkte if p.get("place") in ("footer", "both") and not p.get("children")]
    return {"breit": breit, "handy": handy, "fuss": fuss}


@register.filter
def menue_markiert(punkte) -> bool:
    """Ist im Hauptmenü ein Punkt als aktuelle Seite markiert (unterstrichen)? Dann braucht
    eine Unterseite keinen eigenen Brotkrumen-Streifen darüber (Ralf 15.11.). Punkte nur im
    Fuß und „Start“ zählen nicht."""
    return any(
        p.get("active") and not p.get("start") and p.get("place") != "footer" for p in punkte or ()
    )


_ADRESSE = re.compile(r"^[a-z0-9-]{1,80}$")


def _lesbar(slug) -> bool:
    return isinstance(slug, str) and bool(_ADRESSE.match(slug))


def dignity_address(site, kennung: str) -> str:
    """Lesbare Adresse einer Würde aus dem Menü von HUBIplan, sonst die Kennung (#149)."""
    menu = (site.info.get("honors_menu") or {}) if site is not None else {}
    for d in menu.get("dignities") or []:
        if isinstance(d, dict) and d.get("id") == kennung and _lesbar(d.get("slug")):
            return d["slug"]
    return kennung


@register.filter
def adresse(item) -> str:
    """Lesbare Adresse eines Wettbewerbs oder einer Reihe, sonst die Kennung (#149)."""
    if not isinstance(item, dict):
        return ""
    slug = item.get("slug")
    return slug if _lesbar(slug) else str(item.get("id", ""))


def _nav_url(site, node: dict) -> str | None:
    """Adresse eines Menüpunkts aus HUBIplan (None: unbekannt oder unvollständig)."""
    key = node.get("key")
    if key == "page":
        if not node.get("slug"):
            return None
        # Veranstaltungsseite (HUBIplan A4) unter /veranstaltung/<slug>/
        return reverse("veranstaltung" if node.get("event") else "seite", args=[node["slug"]])
    if key == "dignity":
        if not node.get("id"):
            return None
        return reverse("wuerde", args=[dignity_address(site, node["id"])])
    if key == "units":
        return einheiten_url(site)
    if key == "unit":
        # Seite einer Untereinheit als Ziel eines Knopfs oder einer Kachel (Webseite #111)
        return einheit_url(site, node["slug"]) if node.get("slug") else None
    if key == "membertype":
        return reverse("mitglieder", args=[node["id"]]) if node.get("id") else None
    if key == "link":
        return _extern(node.get("url"))
    name = NAV_URLS.get(key)
    return reverse(name) if name else None


# Menüpunkte aus HUBIplan → Adresse auf der Webseite
NAV_URLS = {
    "posts": "aktuelles",
    "events": "termine",
    "board": "vorstand",
    "honors": "majestaeten",
    "history": "chronik",
    "offices": "aemter",
    "honorary": "ehrungen",
    "results": "ergebnisse",
    "statutes": "dokumente",
    "gallery": "galerie",
    "contact": "kontakt",
    "memorial": "gedenken",
    "repertoire": "repertoire",
    "bookings": "belegung",
    "press": "presse",
    "join": "mitglied_werden",
}


def _extern(url) -> str | None:
    """Adresse eines Links nach außen: nur vollständige http(s)-Adressen."""
    if not isinstance(url, str) or len(url) > 300:
        return None
    parts = urlsplit(url.strip())
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return None
    return url.strip()


def _extra(node: dict) -> dict:
    """Zusätze eines Menüpunkts: Link nach außen, als Knopf hervorgehoben."""
    extra = {}
    if node.get("key") == "link":
        extra["extern"] = True
    if node.get("button") is True:
        extra["knopf"] = True
    # Platz eines Hauptpunkts (Webseite #75): nur im Fuß oder im Hauptmenü und im Fuß
    if node.get("place") in ("footer", "both"):
        extra["place"] = node["place"]
    return extra


def _nav_items(site, nav: list) -> list:
    """Menü in der Anordnung aus HUBIplan (Ralf 2026-10-31: per Ziehen, mit Unterpunkten).
    Ein Punkt mit eigener Seite und Unterpunkten wird ein Aufklappmenü, in dem er selbst
    zuerst steht; eine Überschrift hat nur ihre Unterpunkte."""
    items = []
    for node in nav:
        if not isinstance(node, dict) or not node.get("label"):
            continue
        children = [
            (c["label"], url, _extra({**c, "button": False, "place": None}))
            for c in node.get("children") or []
            if isinstance(c, dict) and c.get("label") and (url := _nav_url(site, c))
        ]
        url = None if node.get("heading") else _nav_url(site, node)
        if url and children:
            own = _extra({**node, "button": False, "place": None})
            items.append((node["label"], [(node["label"], url, own), *children]))
        elif url:
            items.append((node["label"], url, _extra(node)))
        elif len(children) == 1:
            # einziger Unterpunkt rückt hoch und übernimmt den Platz der Überschrift
            label, url, extra = children[0]
            items.append((label, url, {**extra, **_extra({"place": node.get("place")})}))
        elif children:
            items.append((node["label"], children))
    return items


def _legacy_items(site) -> list:
    """Menü für ältere HUBIplan-Stände ohne ``nav`` (feste Reihenfolge)."""
    info = site.info
    items = []
    from seite.views import has_posts

    if site.block("posts") and has_posts(info):
        items.append((_("Aktuelles"), reverse("aktuelles")))
    if site.block("events"):
        items.append((_("Termine"), reverse("termine")))
    if site.block("board"):
        items.append((_("Vorstand"), reverse("vorstand")))
    if info.get("units"):
        items.append((info.get("unit_label_plural") or _("Einheiten"), einheiten_url(site)))
    grouped = info.get("honors_menu")
    if grouped:
        # Menüpunkt „Würdenträger“ mit Unterpunkten je Würde und „Ehrungen“ (Ralf 2026-10-31)
        children = [
            (d["label"], reverse("wuerde", args=[d["slug"] if _lesbar(d.get("slug")) else d["id"]]))
            for d in grouped.get("dignities") or []
            if d.get("id") and d.get("label")
        ]
        if grouped.get("honorary"):
            children.append((grouped.get("honorary_label") or _("Ehrungen"), reverse("ehrungen")))
        if len(children) == 1:
            items.append(children[0])
        elif children:
            items.append((grouped.get("label") or _("Würdenträger"), children))
    elif site.block("honors"):
        # Bei nur einer Würde ihr Name (in der Mehrzahl), sonst „Majestäten“
        items.append((info.get("honors_label") or _("Würdenträger"), reverse("majestaeten")))
    pages = info.get("menu") or []
    # Menü „Geschichte“ mit „Chronik“ und „Ämter“ (Ralf 2026-10-31); nur eins: direkt
    chronik, aemter = site.history_parts()
    parts = [(_("Chronik"), reverse("chronik"))] if chronik else []
    if aemter:
        parts.append((_("Ämter"), reverse("aemter")))
    if len(parts) == 1:
        items.append(parts[0])
    elif parts:
        items.append((_("Geschichte"), parts))
    for p in pages:
        if p.get("slug") and p["slug"] != "geschichte":
            items.append((p.get("title") or p["slug"], reverse("seite", args=[p["slug"]])))
    if info.get("statute_url") or info.get("fee_rules_url") or info.get("founding_deed_url"):
        items.append((_("Dokumente"), reverse("dokumente")))
    if site.block("contact"):
        items.append((_("Kontakt"), reverse("kontakt")))
    return items


@register.simple_tag
def baustein(site, key, standard=""):
    """Name eines Bausteins für Überschrift und Seitentitel: eigener Name aus HUBIplan
    (Ralf 2026-11-01, ``names``) oder der Standardname."""
    names = (site.info.get("names") if site is not None else None) or {}
    name = names.get(key) if isinstance(names, dict) else None
    return name.strip() if isinstance(name, str) and name.strip() else standard


def _eigene_hosts(request) -> set[str]:
    """Namen, unter denen diese Webseite gerade aufgerufen wird (mit und ohne „www.“)."""
    if request is None:
        return set()
    from ..site import host_of

    hosts = {request.get_host().split(":")[0].lower(), host_of(request)}
    return {h for x in hosts if x for h in (x, x.removeprefix("www."), "www." + x)}


@register.simple_tag(takes_context=True)
def ziel(context, site, target) -> dict | None:
    """Ziel eines Knopfs oder einer Kachel der Startseite (G3): ``url`` und ``extern``.
    Eine volle Adresse auf diese Webseite selbst gilt nicht als Link nach außen (Webseite
    #111): sie öffnet im selben Fenster, ohne „↗“."""
    if not isinstance(target, dict):
        return None
    try:
        url = _nav_url(site, target)
    except (KeyError, TypeError, ValueError, NoReverseMatch):  # unvollständig: kein Link
        return None
    if not url:
        return None
    extern = target.get("key") == "link"
    if extern:
        host = (urlsplit(url).hostname or "").lower()
        extern = host not in _eigene_hosts(context.get("request"))
    return {"url": url, "extern": extern}


@register.simple_tag(takes_context=True)
def abschnitt(context, klassen: str = ""):
    """Klassen und Hintergrund eines Abschnitts der Startseite (G3) als Attribute.

    Breite und Hintergrund kommen aus HUBIplan; Palettenfarben nur als geprüfte Hex-Werte."""
    a = context.get("abschnitt") or {}
    parts = [klassen] if klassen else []
    parts += a.get("klassen") or []
    style = a.get("stil") or ""
    if parts and style:
        return format_html(' class="{}" style="{}"', " ".join(parts), style)
    if parts:
        return format_html(' class="{}"', " ".join(parts))
    return format_html(' style="{}"', style) if style else ""
