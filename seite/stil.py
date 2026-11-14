"""Stilregler aus HUBIplan (Webseite › Gestaltung › Feinabstimmung, Konzept G1).

HUBIplan schickt unter ``style`` nur die Regler, die jemand verstellt hat. Die Seite nimmt
davon nur bekannte Regler mit bekannten Stufen und schreibt sie als ``data-st-…`` an das
``<html>``-Element; ``stil.css`` hat für jede Stufe feste Regeln. Ohne Regler bleibt jedes
Design (und jedes Paket) genau wie bisher.
"""

from __future__ import annotations

# Regler → erlaubte Stufen; ``bool`` = Schalter (Ausgabe "on"/"off")
CATALOG: dict[str, tuple[str, ...] | type] = {
    # Schrift
    "font": ("system", "modern", "festive"),
    "size": ("normal", "large", "xlarge"),
    "leading": ("tight", "normal", "airy"),
    "headings": ("plain", "line", "color"),
    "heading_align": ("left", "center"),
    "script_greeting": bool,
    # Seite
    "width": ("narrow", "normal", "wide"),
    "background": ("light", "tinted", "grey"),
    "spacing": ("compact", "normal", "generous"),
    "corners": ("square", "slight", "round"),
    "dark": ("off", "auto"),
    "contrast": bool,
    "to_top": bool,
    # Karten, Bilder, Knöpfe
    "cards": ("border", "shadow", "flat"),
    "images": ("cards", "square"),
    "tile_ratio": ("wide", "classic", "square"),
    "image_frame": bool,
    "buttons": ("filled", "outline"),
    "date": ("tile", "strip"),
    # Kopf und Menü
    "header_bg": ("white", "color", "image"),
    "logo": bool,
    "logo_pos": ("left", "center", "right"),
    "name": bool,
    "header_height": ("low", "medium", "normal", "high"),
    "line": ("none", "thin", "strong"),
    "nav": ("bar", "buttons", "text"),
    "nav_active": ("underline", "filled"),
    "sticky": bool,
    "nav_mobile": ("toggle", "scroll"),
    # Webseite #75: „Start“ in der Menüleiste am Bildschirm; Lage der Suche
    "nav_start": bool,
    "search": ("nav", "header", "footer"),
    # Startseite
    "hero": ("low", "medium", "normal", "high"),
    "hero_name": bool,
    "carousel": ("off", "slow", "normal"),
    # Ralf 14.11.2026: Titelbild abdunkeln oder in Vereinsfarbe färben (halb durchsichtig),
    # Bildausschnitt und Lage des Namens auf dem Bild
    "hero_shade": ("none", "light", "strong"),
    "hero_tint": ("dark", "primary", "accent"),
    "hero_focus": ("top", "center", "bottom"),
    "hero_text": ("top", "center", "band"),
    # Abschnitte der Startseite trennen
    "sections": ("none", "line", "alternate"),
    # Fuß
    "footer": ("dark", "light", "color"),
    "footer_align": ("left", "center", "right"),
    # Ralf 14.11.2026: weitere Regler
    # Überschrift der Unterseiten: schlicht, farbiges Band, Band mit dem Titelbild der Startseite
    "page_title": ("plain", "band", "image"),
    # Schrift der Überschriften unabhängig vom Text
    "heading_font": ("text", "modern", "festive"),
    # Menü am Bildschirm: Großbuchstaben, größere Schrift
    "nav_case": ("normal", "upper"),
    "nav_size": ("normal", "large"),
    # Inhalte beim Blättern sanft einblenden (nie bei „weniger Bewegung“ am Gerät)
    "motion": ("off", "subtle"),
    # Tabellen abwechselnd hinterlegt
    "stripes": bool,
    # Datum in der Terminliste neben dem Datumsfeld: Wochentag, kurz oder lang
    "date_text": ("weekday", "short", "long"),
}

# Was ein Design selbst festlegt; HUBIplan zeigt diese Wahl ausgegraut (gleiche Liste dort).
# ``None`` = ganzer Regler gesperrt, sonst nur die genannten Stufen.
LOCKS: dict[str, dict[str, tuple[str, ...] | None]] = {
    "sidebar": {
        "width": ("narrow",),
        "logo_pos": None,
        "header_height": None,
        "line": None,
        "nav": None,
        "sticky": None,
        "nav_mobile": None,
    },
    "stage": {"width": ("narrow",), "hero_name": None},
    "newspaper": {"nav": None},
}

# Hintergrund der Seite (--grund); getönt wird aus der Vereinsfarbe gemischt
BACKGROUNDS = {"light": "#fbfaf7", "grey": "#eff1f0"}
TINT = 0.07


def _locked(design: str, key: str, value: str) -> bool:
    lock = LOCKS.get(design, {})
    if key not in lock:
        return False
    values = lock[key]
    return values is None or value in values


def clean(given, design: str) -> dict[str, str]:
    """Nur bekannte Regler und Stufen, ohne die vom Design gesperrten."""
    if not isinstance(given, dict):
        return {}
    result: dict[str, str] = {}
    for key, allowed in CATALOG.items():
        value = given.get(key)
        if allowed is bool:
            if not isinstance(value, bool):
                continue
            value = "on" if value else "off"
        elif not (isinstance(value, str) and value in allowed):
            continue
        if not _locked(design, key, value):
            result[key] = value
    # Wappen und Name nie beide aus: dann bleibt der Name sichtbar
    if result.get("logo") == "off" and result.get("name") == "off":
        del result["name"]
    return result


def attrs(style: dict[str, str]) -> str:
    """``data-st-…``-Merkmale; Schlüssel und Werte stammen nur aus CATALOG."""
    return "".join(f' data-st-{k.replace("_", "-")}="{v}"' for k, v in style.items())


def mix(color: str, base: str, amount: float) -> str:
    """``amount`` Anteil ``color`` in ``base`` (beides #rrggbb)."""
    a = [int(color[i : i + 2], 16) for i in (1, 3, 5)]
    b = [int(base[i : i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(
        f"{round(x * amount + y * (1 - amount)):02x}" for x, y in zip(a, b, strict=True)
    )


def background(style: dict[str, str], primary: str) -> str | None:
    value = style.get("background")
    if value == "tinted":
        return mix(primary, "#ffffff", TINT)
    return BACKGROUNDS.get(value) if value else None
