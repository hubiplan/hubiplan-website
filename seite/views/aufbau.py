"""Aufbau der Seiten aus Abschnitten: Reihenfolge, eigene Abschnitte, Aussehen."""

from __future__ import annotations

import re

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from ..farben import gradient_css, text_on, text_on_all
from ..site import SAFE_URL, Site
from .beitraege import _post
from .ergebnisse import TOKEN, _with_date
from .termine import _event, _qr_svg

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
    "join": "mitglied",
    "donation": "spende",
    "hours": "zeiten",
    "columns": "spalten",
    "table": "tabelle",
    "timeline": "zeitstrahl",
    "program": "programm",
    "callout": "hinweis_kasten",
    "accordion": "aufklappbar",
    "images": "bilder",
    "downloads": "downloads",
    "unit_honors": "majestaeten_einheit",
    "competition": "wettbewerb",
    "albums": "alben",
    "posts": "neueste_beitraege",
    "app": "app",
    "live_facts": "zahlen",
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
            on = text_on(color.lower(), on.lower())  # UX-Audit 16.11. X-03: gegen die Fläche
            klassen.append("abschnitt-hg")
            klassen.append("abschnitt-farbig")
            stil = f"background:{color};color:{on};--abschnitt-auf:{on};--abschnitt-farbe:{color}"
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
            on = text_on_all(pair, on.lower())
            klassen.append("abschnitt-hg")
            klassen.append("abschnitt-farbig")
            stil = (
                f"background:{pair[0]};background-image:{css};color:{on};--abschnitt-auf:{on};"
                f"--abschnitt-farbe:{pair[0]}"
            )
    if "abschnitt-hg" in klassen and (zeichen := _mark_url(site, s.get("mark"))):
        # Webseite #123: Wasserzeichen groß, zart und angeschnitten hinter dem Abschnitt
        klassen.append("mit-zeichen")
        stil = f'{stil};--zeichen:url("{zeichen}")'
    return {"klassen": klassen, "stil": stil}


def _mark_url(site: Site, mark) -> str | None:
    """Wasserzeichen eines Abschnitts: ``"logo"`` (Wappen) oder ein Bild aus HUBIplan; nur
    Adressen über diese Seite ohne Zeichen, die im CSS ``url("…")`` etwas bedeuten."""
    if mark == "logo":
        url = site.local(site.info.get("logo_url"))
    elif isinstance(mark, dict):
        url = site.local(mark.get("url"))
    else:
        return None
    return url if url and SAFE_URL.match(url) else None


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
            event = _event(s.get("event"), site)
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
        elif kind == "posts":
            posts = [_post(p) for p in s.get("posts") or [] if isinstance(p, dict)]
            if not posts:
                continue
            entry["posts"] = posts
        elif kind == "competition":
            comp = s.get("competition")
            if not isinstance(comp, dict) or not TOKEN.match(str(comp.get("id", ""))):
                continue
            entry["competition"] = _with_date(comp)
        elif kind == "app":
            login = s.get("login_url") if isinstance(s.get("login_url"), str) else ""
            if not login.startswith(("https://", "http://")):
                continue
            entry["qr_svg"] = _qr_svg(login) if s.get("qr") else ""
        elif kind == "event_list":
            events = [_event(e, site) for e in s.get("events") or []]
            events = [e for e in events if e is not None]
            if not events:
                continue
            entry["events"] = events
        result.append(entry)
    return result


# Feste Blöcke der Seite einer Untereinheit (HUBIplan ab #491) → Vorlage unter seite/einheit/
UNIT_BLOCKS = {
    "body": "text",
    "contact": "kontakt",
    "homepage": "homepage",
    "honors": "majestaeten",
    "events": "termine",
    "news": "beitraege",
    "follow": "folgen",
}


def _unit_layout(site: Site, data: dict) -> list[dict] | None:
    """Abschnitte der Seite einer Untereinheit: feste Blöcke und eigene Abschnitte in der
    Reihenfolge aus HUBIplan. ``None`` bei älteren Ständen ohne Abschnitte (Seite wie bisher)."""
    sections = data.get("sections") if isinstance(data, dict) else None
    if not isinstance(sections, list):
        return None
    result = []
    for s in sections:
        if not isinstance(s, dict):
            continue
        kind = s.get("kind")
        if kind in UNIT_BLOCKS:
            result.append(
                {**s, "vorlage": f"seite/einheit/{UNIT_BLOCKS[kind]}.html", **_look(site, s)}
            )
        elif kind in CUSTOM_SECTIONS:
            result.extend(_layout_entries(site, [s]))
    # Steht die Homepage direkt hinter dem Kontakt, erscheint sie wie bisher als Karte daneben
    for first, second in zip(result, result[1:], strict=False):
        if (
            first["kind"] == "contact"
            and second["kind"] == "homepage"
            and not (first["klassen"] or first["stil"] or second["klassen"] or second["stil"])
        ):
            first["mit_homepage"] = True
            second["bei_kontakt"] = True
    return result


def _page_layout(site: Site, sections: list) -> list[dict]:
    """Abschnitte einer Textseite: fester Abschnitt „body“ (Bild und Text) und eigene."""
    result = []
    for s in sections:
        if isinstance(s, dict) and s.get("kind") == "body":
            result.append({**s, "vorlage": "seite/seite_text.html", **_look(site, s)})
        elif isinstance(s, dict) and s.get("kind") in CUSTOM_SECTIONS:
            result.extend(_layout_entries(site, [s]))
    return result
