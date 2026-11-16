"""Stilregler aus HUBIplan (Webseite › Gestaltung › Feinabstimmung, Konzept G1).

HUBIplan schickt unter ``style`` nur die Regler, die jemand verstellt hat. Die Seite nimmt
davon nur bekannte Regler mit bekannten Stufen und schreibt sie als ``data-st-…`` an das
``<html>``-Element; ``stil.css`` hat für jede Stufe feste Regeln. Ohne Regler bleibt jedes
Design (und jedes Paket) genau wie bisher.
"""

from __future__ import annotations

import re

# Regler → erlaubte Stufen; ``bool`` = Schalter (Ausgabe "on"/"off")
CATALOG: dict[str, tuple[str, ...] | type] = {
    # Schrift
    "font": ("system", "modern", "festive", "clear", "elegant", "readable"),
    "size": ("normal", "large", "xlarge"),
    "leading": ("tight", "normal", "airy"),
    "headings": ("plain", "line", "color", "short"),
    "heading_align": ("left", "center"),
    # Webseite #89: Überschriften etwas größer
    "heading_size": ("normal", "large"),
    # Webseite #96: Seitentitel (h1) eigens einstellbar, auch kleiner als die Grundstellung;
    # ohne diesen Regler gilt für den Seitentitel weiter ``heading_size``
    "title_size": ("small", "medium", "normal", "large"),
    "script_greeting": bool,
    # Seite
    "width": ("narrow", "normal", "wide"),
    "background": ("light", "tinted", "grey"),
    "spacing": ("compact", "normal", "generous"),
    "corners": ("square", "slight", "round"),
    # Webseite #89: Farbe der hellen Abschnittsflächen (Hintergrund „hell“ eines Abschnitts)
    "section_bg": ("tinted", "warm", "grey"),
    "dark": ("off", "auto"),
    "contrast": bool,
    "to_top": bool,
    # Karten, Bilder, Knöpfe
    "cards": ("border", "shadow", "flat", "accent"),
    "images": ("cards", "square"),
    "tile_ratio": ("wide", "classic", "square"),
    "image_frame": bool,
    "buttons": ("filled", "outline", "label"),
    # Webseite #124: nächste Termine als Karten nebeneinander mit großem Datum
    "date": ("tile", "strip", "card"),
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
    # hubiplan #477: „zufällig“ zeigt bei jedem Aufruf ein Bild des Karussells, fest stehend
    "carousel": ("off", "slow", "normal", "random"),
    # Ralf 16.11.2026: Knöpfe am Karussell immer sichtbar oder nur bei Mauszeiger (auf
    # Touch-Geräten immer); ohne Regler auf der Bühne immer (#130), sonst bei Mauszeiger
    "carousel_controls": ("always", "hover"),
    # Ralf 14.11.2026: Titelbild abdunkeln oder in Vereinsfarbe färben (halb durchsichtig),
    # Bildausschnitt und Lage des Namens auf dem Bild
    "hero_shade": ("none", "light", "strong"),
    "hero_tint": ("dark", "primary", "accent"),
    "hero_focus": ("top", "center", "bottom"),
    "hero_text": ("top", "center", "band"),
    # Webseite #122: Titelfoto randlos als Bühne unter dem Kopf, mit Verlauf und Titelzeilen
    "hero_width": ("content", "stage", "full"),
    # Webseite #128: Bühne in Inhaltsbreite (hero_width=stage), Breite und Fläche daneben
    "hero_stage_width": ("content", "wider", "wide"),
    "hero_side": ("page", "color"),
    # Abschnitte der Startseite trennen
    "sections": ("none", "line", "alternate"),
    # Fuß
    "footer": ("dark", "light", "color"),
    "footer_align": ("left", "center", "right"),
    # Webseite #125: Fuß mit Wappen, Vereinsname und Links untereinander; Linie darüber
    "footer_layout": ("simple", "full"),
    "footer_line": ("none", "ornament", "accent", "primary"),
    # Webseite #127: im vollen Fuß Vereinsname und Gründungszeile einzeln ausblenden
    "footer_name": bool,
    "footer_founded": bool,
    # Ralf 14.11.2026: weitere Regler
    # Überschrift der Unterseiten: schlicht, farbiges Band, Band mit dem Titelbild der Startseite
    "page_title": ("plain", "band", "image"),
    # Webseite #148: Band der Einheiten in Vereinsfarbe, Kastenfarbe, hell oder schlicht mit Linie
    "unit_title": ("primary", "box", "light", "plain"),
    # Schrift der Überschriften unabhängig vom Text
    "heading_font": ("text", "modern", "festive", "clear", "elegant", "fraktur", "strong"),
    # Menü am Bildschirm: Großbuchstaben, größere Schrift
    "nav_case": ("normal", "upper"),
    "nav_size": ("normal", "large"),
    # Inhalte beim Blättern sanft einblenden (nie bei „weniger Bewegung“ am Gerät)
    "motion": ("off", "subtle"),
    # Tabellen abwechselnd hinterlegt
    "stripes": bool,
    # Datum in der Terminliste neben dem Datumsfeld: Wochentag, kurz oder lang
    "date_text": ("weekday", "short", "long"),
    # Webseite #135: amtierende Würdenträger als Band unter dem Titel, Vorgänger als Karten
    "honors_layout": ("list", "band"),
    # Webseite #136: Personen ohne Foto ohne Platzhalter; Personenkarten mit Amt als Etikett
    "portrait_placeholder": ("initial", "none"),
    "person_cards": ("normal", "label"),
    # Webseite #137: Anrede auf der Webseite (Kontaktformular): Sie oder du
    "address": ("formal", "informal"),
    # Webseite #138: Epochen der Chronik als Band, Sprungmarken als Links; #141 flaches Band
    "timeline_chapter": ("plain", "band", "slim"),
    # Webseite #139: Plätze 1 bis 3 einer Wertung als Karten über der Rangliste
    "ranking": ("table", "podium"),
    # Webseite #145: lange, schmale Tabellen (ab 20 Zeilen, bis zwei Spalten) am Bildschirm
    # zweispaltig; ohne Regler untereinander wie bisher
    "long_tables": ("rows", "columns"),
    # Webseite #143: Ehrungen als eigene Karte je Person, Ehrung oder Titel als Etikett
    "honorary_layout": ("list", "cards"),
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
    # Bühne zeigt ihr Titelbild ohnehin randlos; in der Zeitung steht es in der Hauptspalte
    "stage": {
        "width": ("narrow",),
        "hero_name": None,
        "hero_width": None,
        "hero_side": None,
        "hero_stage_width": None,
    },
    "newspaper": {"nav": None, "hero_width": None, "hero_side": None, "hero_stage_width": None},
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


# hubiplan #526: eigene Schriftfolge aus Schriften, die auf dem Gerät installiert sind (Text mit
# Komma, in HUBIplan schon geprüft). Hier noch einmal streng geprüft, weil der Wert ungeschützt
# im <style> steht: nur Buchstaben, Ziffern, Leerzeichen und Bindestrich, höchstens sechs Namen.
FONT_STACKS = ("font_family", "heading_font_family")
FONT_NAME = re.compile(r"^[^\W_][\w -]{0,39}$")
GENERIC_FAMILIES = ("sans-serif", "serif")
MAX_FONTS = 6


def font_stack(value) -> str | None:
    """CSS ``font-family`` aus der Schriftfolge oder None (leer oder ungültig)."""
    if not isinstance(value, str) or len(value) > 400:
        return None
    names: list[str] = []
    generic = "sans-serif"
    for raw in value.split(","):
        name = " ".join(raw.split())
        if not name:
            continue
        if name.lower() in GENERIC_FAMILIES:
            generic = name.lower()
            continue
        if not FONT_NAME.match(name):
            return None
        names.append(name)
    if not names or len(names) > MAX_FONTS:
        return None
    return ", ".join([f'"{n}"' for n in names] + [generic])


def font_stacks(given) -> dict[str, str]:
    """Schriftfolgen für Text und Überschriften. Ohne eigene Folge der Überschriften gilt die des
    Textes auch dort, solange keine Schrift der Überschriften (``heading_font``) gewählt ist."""
    if not isinstance(given, dict):
        return {}
    text = font_stack(given.get("font_family"))
    heading = font_stack(given.get("heading_font_family"))
    if (
        heading is None
        and text is not None
        and given.get("heading_font") not in CATALOG.get("heading_font", ())
    ):
        heading = text
    return {k: v for k, v in (("text", text), ("heading", heading)) if v is not None}
