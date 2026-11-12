"""Hilfen für die Vorlagen: Markdown, lokale Bildadressen, Menü."""

from __future__ import annotations

import datetime
import functools
import re
from pathlib import Path
from urllib.parse import urlsplit

from django import template
from django.urls import NoReverseMatch, reverse
from django.utils.formats import date_format
from django.utils.html import format_html, json_script
from django.utils.translation import get_language, gettext_noop
from django.utils.translation import gettext as _

from .. import markdown

register = template.Library()


@register.filter
def md(text, site=None):
    """Markdown → HTML; mit ``site`` führen Links auf Untereinheiten zum richtigen Pfad."""
    return markdown.render(text, site.units_path if site is not None else "einheiten")


@register.simple_tag
def lokal(site, url):
    return site.local(url) if site is not None else None


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
    items = [(_("Start"), reverse("start"))]
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


def _nav_url(site, node: dict) -> str | None:
    """Adresse eines Menüpunkts aus HUBIplan (None: unbekannt oder unvollständig)."""
    key = node.get("key")
    if key == "page":
        return reverse("seite", args=[node["slug"]]) if node.get("slug") else None
    if key == "dignity":
        return reverse("wuerde", args=[node["id"]]) if node.get("id") else None
    if key == "units":
        return einheiten_url(site)
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
            (c["label"], url, _extra({**c, "button": False}))
            for c in node.get("children") or []
            if isinstance(c, dict) and c.get("label") and (url := _nav_url(site, c))
        ]
        url = None if node.get("heading") else _nav_url(site, node)
        if url and children:
            own = _extra({**node, "button": False})
            items.append((node["label"], [(node["label"], url, own), *children]))
        elif url:
            items.append((node["label"], url, _extra(node)))
        elif len(children) == 1:
            items.append(children[0])
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
            (d["label"], reverse("wuerde", args=[d["id"]]))
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
        items.append((info.get("honors_label") or _("Majestäten"), reverse("majestaeten")))
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


@register.simple_tag
def ziel(site, target) -> dict | None:
    """Ziel eines Knopfs oder einer Kachel der Startseite (G3): ``url`` und ``extern``."""
    if not isinstance(target, dict):
        return None
    try:
        url = _nav_url(site, target)
    except (KeyError, TypeError, ValueError, NoReverseMatch):  # unvollständig: kein Link
        return None
    if not url:
        return None
    return {"url": url, "extern": target.get("key") == "link"}


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


@register.simple_tag
def jahr():
    return datetime.date.today().year


QUELLCODE = "https://github.com/hubiplan/hubiplan-website"
FASSUNG = Path(__file__).resolve().parents[2] / ".fassung"


@functools.cache
def _fassung() -> str:
    """Commit der laufenden Fassung (deploy/deploy.sh legt ``.fassung`` ab), sonst leer."""
    try:
        sha = FASSUNG.read_text().strip()
    except OSError:
        return ""
    return sha if re.fullmatch(r"[0-9a-f]{40}", sha) else ""


@register.simple_tag
def quellcode():
    """Quellcode dieser Webseite (AGPL § 13): der laufende Commit, sonst das Repository."""
    sha = _fassung()
    return f"{QUELLCODE}/tree/{sha}" if sha else QUELLCODE


@register.filter
def mit_begleitung(reigns) -> bool:
    """Hat mindestens eine Regentschaft Begleitpersonen? Sonst entfällt die Spalte."""
    return any(r.get("companions") for r in reigns or [])


# Datumsformate je Sprache (Englisch nach britischer Schreibweise, Konzept F4)
DATE_FORMATS = {
    "de": {
        "kurz": "j.n.Y",
        "tag": "j. F Y",
        "lang": "l, j. F Y",
        "zeit": r"j. F Y, H:i \U\h\r",
        "uhr": r"H:i \U\h\r",
    },
    "en": {
        "kurz": "d/m/Y",
        "tag": "j F Y",
        "lang": "l j F Y",
        "zeit": "j F Y, H:i",
        "uhr": "H:i",
    },
}


@register.filter(expects_localtime=True)
def datum(value, art: str = "kurz"):
    """Datum (ISO-Text, date oder datetime) in der Sprache der Seite: ``kurz`` 1.4.2020,
    ``tag`` 1. April 2020, ``lang`` mit Wochentag, ``zeit`` mit Uhrzeit, ``uhr`` nur Uhrzeit."""
    if not value:
        return ""
    if isinstance(value, str):
        try:
            value = datetime.date.fromisoformat(value[:10])
        except ValueError:
            return value
    formate = DATE_FORMATS.get((get_language() or "de")[:2], DATE_FORMATS["de"])
    return date_format(value, formate.get(art, formate["kurz"]))


@register.filter
def nur_jahr(value):
    """ISO-Datum (Text) → Jahr. Ämter und Vorstand zeigen nur Jahre (Ralf 2026-10-31)."""
    if not value:
        return ""
    if isinstance(value, str):
        return value[:4] if value[:4].isdigit() else value
    return str(value.year)


# Symbole für Social-Media-Kanäle (schlichte Formen; Farbe über CSS). Die Pfade für
# Facebook, TikTok und X entsprechen weitgehend den Symbolen von Simple Icons
# (simpleicons.org, CC0 1.0; X verglichen mit Version 11.15.0); ob sie von dort
# stammen, ist nicht belegt (Lizenzaudit 31.10.2026, L11). CC0 verlangt keine Nennung.
# Die Zeichen sind Marken der jeweiligen Unternehmen und dienen nur als Link auf
# den eigenen Kanal des Vereins. Das LinkedIn-Symbol ist selbst aus Grundformen gezeichnet
# (abgerundetes Quadrat mit „in“), Simple Icons führt LinkedIn nicht mehr.
_STROKE = 'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"'
ICONS = {
    "facebook": '<circle cx="12" cy="12" r="12" fill="currentColor"/>'
    '<path fill="var(--sm-auf, #fff)" '
    'd="M13.4 24v-8.4h2.8l.4-3.3h-3.2v-2.1c0-1 .3-1.6 1.6-1.6h1.7V5.7c-.3 0-1.3-.1-2.5-.1-2.5 '
    '0-4.2 1.5-4.2 4.3v2.4H7.2v3.3H10V24z"/>',
    "instagram": f'<rect x="3" y="3" width="18" height="18" rx="5" {_STROKE}/>'
    f'<circle cx="12" cy="12" r="4.2" {_STROKE}/><circle cx="17.4" cy="6.6" r="1.2" '
    'fill="currentColor"/>',
    "tiktok": '<path fill="currentColor" d="M12.5 0h3.9c.1 1.5.6 3.1 1.8 4.2 1.1 1.1 2.7 1.6 '
    "4.2 1.8v4c-1.4 0-2.9-.3-4.2-1-.6-.3-1.1-.6-1.6-.9v8.8c-.1 1.4-.5 2.8-1.4 3.9a7 7 0 0 1-5.9 "
    "3.2A7 7 0 0 1 2.4 19a7 7 0 0 1 2-11.7 7 7 0 0 1 4.1-.4v4.4c-1-.3-2.2-.2-3 .4a2.9 2.9 0 0 "
    '0 1.9 5.2 2.9 2.9 0 0 0 2.8-2.7V0h2.3z"/>',
    "x": '<path fill="currentColor" d="M18.9 1.2h3.7l-8 9.1L24 22.8h-7.4l-5.8-7.6-6.6 '
    '7.6H.5l8.6-9.8L0 1.2h7.6l5.2 6.9 6.1-6.9zm-1.3 19.5h2L6.5 3.2H4.3l13.3 17.5z"/>',
    "linkedin": '<rect x="1" y="1" width="22" height="22" rx="3.5" fill="currentColor"/>'
    '<g fill="var(--sm-auf, #fff)"><rect x="5.2" y="9.4" width="3" height="9.4"/>'
    '<circle cx="6.7" cy="6.4" r="1.75"/>'
    '<path d="M10.4 9.4h2.9v1.3c.5-.9 1.6-1.6 3.2-1.6 2.6 0 3.3 1.7 3.3 4.2v5.5h-3v-4.9c0-1.2'
    '-.3-2.1-1.5-2.1s-1.9.9-1.9 2.1v4.9h-3z"/></g>',
    "youtube": '<rect x="1.5" y="4.5" width="21" height="15" rx="4" fill="currentColor"/>'
    '<path d="M10 8.8v6.4l5.5-3.2z" fill="var(--sm-auf, #fff)"/>',
}
_LINK = (
    f'<circle cx="12" cy="12" r="9" {_STROKE}/><path {_STROKE} d="M3 12h18M12 3c2.5 2.7 '
    '3.8 5.7 3.8 9s-1.3 6.3-3.8 9c-2.5-2.7-3.8-5.7-3.8-9S9.5 5.7 12 3z"/>'
)


@register.simple_tag
def sm_symbol(kind: str, size: int = 22):
    from django.utils.safestring import mark_safe

    body = ICONS.get(kind or "", _LINK)
    return mark_safe(  # noqa: S308 - feste Symbole aus diesem Modul
        f'<svg class="sm-symbol" viewBox="0 0 24 24" width="{int(size)}" height="{int(size)}" '
        f'aria-hidden="true" focusable="false">{body}</svg>'
    )


@register.filter
def web_ziel(url: str) -> str:
    """Nur http(s)-Adressen als Linkziel; alles andere wird leer (kein javascript: o. Ä.)."""
    url = (url or "").strip()
    return url if url.lower().startswith(("https://", "http://")) else ""


@register.filter
def web_anzeige(url: str) -> str:
    """Adresse zum Lesen: ohne https:// und ohne Schrägstrich am Ende."""
    text = (url or "").strip().split("://", 1)[-1]
    return text.rstrip("/")


@register.filter
def tel(number: str) -> str:
    """Telefonnummer als tel:-Ziel (UX-Audit 31.10. S07): nur Ziffern und führendes +,
    „0049…“ wird „+49…“, die Klammer-Null in „+49 (0) 2131“ entfällt."""
    raw = (number or "").strip()
    raw = re.sub(r"\(0\)", "", raw)
    digits = re.sub(r"[^\d+]", "", raw)
    plus = digits.startswith("+")
    digits = digits.replace("+", "")
    if not plus and digits.startswith("00"):
        plus, digits = True, digits[2:]
    if len(digits) < 3:
        return ""
    return ("+" if plus else "") + digits


# Texte der Skripte (kontakt.js, karussell.js). Auf deutschen Seiten entfällt die Liste,
# die Skripte nehmen dann ihren eigenen Text.
JS_TEXTE = (
    gettext_noop("Bitte Ihren Namen eingeben."),
    gettext_noop("Bitte eine gültige E-Mail-Adresse eingeben, z. B. name@beispiel.de."),
    gettext_noop("Bitte einen Betreff eingeben."),
    gettext_noop("Bitte eine Nachricht mit mindestens 10 Zeichen eingeben."),
    gettext_noop("Bitte die markierten Felder prüfen."),
    gettext_noop("Nachricht wird vorbereitet …"),
    gettext_noop("Nachricht wird gesendet …"),
    gettext_noop("Danke! Ihre Nachricht ist angekommen."),
    gettext_noop("Weitere Nachricht"),
    gettext_noop("Die Nachricht konnte nicht gesendet werden."),
    gettext_noop(
        "Sicherheitsprüfung erneuert. Ihre Nachricht bleibt erhalten. Bitte senden Sie erneut."
    ),
    gettext_noop(
        "Das Formular ist abgelaufen. Bitte kopieren Sie Ihre Nachricht "
        "und laden Sie die Seite neu."
    ),
    gettext_noop(
        "Diese Nachricht ist bereits bei uns angekommen. Sie müssen sie nicht erneut senden."
    ),
    gettext_noop(
        "An diese Stelle kann gerade keine Nachricht gehen. Bitte schreiben Sie über den "
        "Menüpunkt „Kontakt“ an den Verein."
    ),
    gettext_noop("Bitte die Angaben prüfen."),
    gettext_noop("Zu viele Nachrichten. Bitte später erneut versuchen."),
    gettext_noop("Die Nachricht konnte nicht gesendet werden. Bitte später erneut versuchen."),
    gettext_noop("Weiter abspielen"),
    gettext_noop("Anhalten"),
    gettext_noop("Aktualisiert um {zeit} Uhr."),
    gettext_noop("Die Ergebnisse sind endgültig."),
)


@register.simple_tag
def seite_texte():
    """Übersetzungen für die Skripte als JSON-Block (nur, wenn die Seite nicht deutsch ist)."""
    if (get_language() or "de")[:2] == "de":
        return ""
    return json_script({t: _(t) for t in JS_TEXTE}, "seite-texte")
