"""Welche Webseite gehört zur Anfrage, und wie werden Adressen aus HUBIplan lokal?

Bilder und Logos lädt der Browser nie direkt bei HUBIplan, sondern über
``/medien/…`` dieser Seite: So gelten Vorschau und Wartung auch für Bilder, und
die Seite lädt nichts von fremden Adressen.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from pathlib import Path

from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from . import api, designpaket, stil

PREVIEW_COOKIE = "vorschau"
# Testserver mit fester Zuordnung (SITE_HOST_OVERRIDE): In der Vorschau eine andere
# Webseite derselben Instanz zeigen (Hostname aus dem Vorschau-Link)
SITE_COOKIE = "vorschau-seite"
HOSTNAME = re.compile(
    r"^(?=.{1,253}$)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$"
)
# Anderes Design nur in der Vorschau ansehen, ohne es zu übernehmen
DESIGN_COOKIE = "vorschau-design"
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
# Bildadresse im CSS (url("…")): nur Pfad- und Abfragezeichen
SAFE_URL = re.compile(r"^/[A-Za-z0-9/._~%=&?-]*$")
DEFAULT_THEME = {
    "primary": "#1f4e2c",
    "on_primary": "#ffffff",
    "accent": "#c9a227",
    "on_accent": "#1d2421",
}


# Standarddesigns (Auswahl in HUBIplan unter Webseite › Gestaltung); unbekannt = Klassisch
DESIGNS = {
    "classic": _("Klassisch"),
    "festive": _("Festlich"),
    "sidebar": _("Seitenleiste"),
    "stage": _("Bühne"),
    "newspaper": _("Zeitung"),
}
DEFAULT_DESIGN = "classic"
# Sprachen der Webseite (Vereinsdaten werden nicht übersetzt)
LANGUAGES = ("de", "en")
COLOR_ROLES = ("header", "nav", "line", "footer", "band", "band2", "date")
DARK = "#1d2421"
# Rollen für Text, Flächen und Hintergrund (HUBIplan ab 10.11.2026): nur gesetzt, wenn
# gewählt; sie überschreiben die Variablen aus seite.css
COMMON_ROLES = {"text": "text", "muted": "text-leise", "surface": "flaeche", "background": "grund"}
# Rollen, die statt einer Farbe einen Verlauf haben können (verlauf.css)
GRADIENT_ROLES = ("header", "footer", "band", "band2", "line")
DIRECTIONS = {"right": "to right", "down": "to bottom"}


# Hintergründe, auf denen Links stehen (seite.css: --flaeche, --grund)
LINK_BACKGROUNDS = ("#ffffff", "#fbfaf7")


def _channel(value: int) -> float:
    c = value / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_color: str) -> float:
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def darken(hex_color: str, amount: float) -> str:
    """Farbe mit Schwarz mischen (0 = unverändert, 1 = schwarz)."""
    parts = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    return "#" + "".join(f"{round(c * (1 - amount)):02x}" for c in parts)


def link_color(
    primary: str, background: str | None = None, *more: str | None, target: float = 4.5
) -> str:
    """Linkfarbe aus der Vereinsfarbe: so wenig wie nötig abgedunkelt, bis Text auf
    Weiß und auf dem Seitengrund 4,5 : 1 erreicht (WCAG 1.4.3; wie HUBIplan). „Kontrast
    erhöht“ verlangt 7 : 1 (WCAG 1.4.6)."""
    backgrounds = LINK_BACKGROUNDS + tuple(b for b in (background, *more) if b)
    for step in range(21):
        color = darken(primary, step * 0.05)
        if min(contrast(color, bg) for bg in backgrounds) >= target:
            return color
    return "#000000"


def lighten(hex_color: str, amount: float) -> str:
    """Farbe mit Weiß mischen (0 = unverändert, 1 = weiß)."""
    parts = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    return "#" + "".join(f"{round(c + (255 - c) * amount):02x}" for c in parts)


# Grundflächen der dunklen Darstellung (stil.css: --grund, --flaeche)
DARK_BACKGROUNDS = ("#121514", "#1c201e")


def link_color_dark(primary: str, target: float = 4.5) -> str:
    """Linkfarbe für die dunkle Darstellung: so wenig wie nötig aufgehellt."""
    for step in range(21):
        color = lighten(primary, step * 0.05)
        if min(contrast(color, bg) for bg in DARK_BACKGROUNDS) >= target:
            return color
    return "#ffffff"


def readable(color: str, backgrounds, target: float = 4.5) -> str:
    """Schriftfarbe, die auf allen ``backgrounds`` ``target`` erreicht (UX-Audit 16.11. X-03):
    so wenig wie nötig abgedunkelt oder aufgehellt, je nachdem, was eher reicht. Die Farbe wird
    korrigiert, nicht nur gewarnt; besteht sie schon, bleibt sie, wie gewählt."""
    backgrounds = [b for b in backgrounds if isinstance(b, str) and HEX.match(b)]
    if not backgrounds or min(contrast(color, bg) for bg in backgrounds) >= target:
        return color
    for step in range(1, 21):
        for change in (darken, lighten):
            candidate = change(color, step * 0.05)
            if min(contrast(candidate, bg) for bg in backgrounds) >= target:
                return candidate
    return max(("#000000", "#ffffff"), key=lambda c: min(contrast(c, bg) for bg in backgrounds))


def text_on(color: str, on: str, target: float = 4.5) -> str:
    """Schrift auf einer Fläche der Vereinsfarbe: die gewählte, wenn sie reicht, sonst Weiß oder
    Dunkel, je nachdem, was sich besser abhebt (UX-Audit 16.11. WS-18)."""
    if contrast(on, color) >= target:
        return on
    return max(("#ffffff", DARK), key=lambda c: contrast(c, color))


def text_on_all(colors, on: str, target: float = 4.5) -> str:
    """Wie text_on, aber für einen Verlauf: die Schrift muss auf beiden Enden reichen."""
    colors = [c.lower() for c in colors if isinstance(c, str) and HEX.match(c)]
    if not colors or min(contrast(on, c) for c in colors) >= target:
        return on
    return max(("#ffffff", DARK), key=lambda c: min(contrast(c, x) for x in colors))


# Darstellung der festen Bereiche (HUBIplan website/variants.py); erste = Standard
LAYOUTS = {
    "board": ("cards", "list"),
    "events": ("list", "calendar"),
    "units": ("large", "small", "list"),
    "gallery": ("tiles", "masonry"),
}


def gradient_css(item) -> str | None:
    """{from, to, direction} aus HUBIplan → linear-gradient(…); sonst None."""
    if not isinstance(item, dict):
        return None
    start, end = item.get("from"), item.get("to")
    if not all(isinstance(v, str) and HEX.match(v) for v in (start, end)):
        return None
    direction = DIRECTIONS.get(item.get("direction"), DIRECTIONS["right"])
    return f"linear-gradient({direction},{start.lower()},{end.lower()})"


@dataclass
class Site:
    key: str
    info: dict
    preview: str | None = None
    maintenance: bool = False
    design_preview: str | None = None
    cache: dict = field(default_factory=dict)

    def __post_init__(self):
        # hubiplan #480: mehrere Kopfbilder – bei jedem Aufruf eines wählen. Die Wahl steht in
        # einer eigenen Kopie von ``info`` (nie im Zwischenspeicher), so dass Vorlagen und
        # Designpakete wie bisher ``site.info.header_image`` nehmen, ohne Skript.
        if isinstance(self.info, dict) and self.several_header_images:
            images = [b for b in self.info["header_images"] if isinstance(b, dict)]
            i = random.randrange(len(images))  # noqa: S311 – keine Sicherheitsfrage
            narrow = [b for b in self.info.get("header_images_narrow") or [] if isinstance(b, dict)]
            if len(narrow) == len(images):
                chosen_narrow = narrow[i]  # gleich viele: als Paare
            elif narrow:
                chosen_narrow = random.choice(narrow)  # noqa: S311
            else:
                chosen_narrow = self.info.get("header_image_narrow")
            self.info = {
                **self.info,
                "header_image": images[i],
                "header_image_narrow": chosen_narrow,
            }

    @property
    def several_header_images(self) -> bool:
        """Mehr als ein Kopfbild oder mehr als eine Fassung für Handys (hubiplan #480)."""
        info = self.info if isinstance(self.info, dict) else {}
        wide = info.get("header_images")
        narrow = info.get("header_images_narrow")
        wide = len(wide) if isinstance(wide, list) else 0
        narrow = len(narrow) if isinstance(narrow, list) else 0
        return wide > 1 or (wide == 1 and narrow > 1)

    # --- Daten ---

    def get(self, path: str, *, cached: bool = True, seconds: int | None = None):
        if (path, cached) not in self.cache:
            self.cache[(path, cached)] = api.get(
                self.key, path, preview=self.preview, cached=cached, seconds=seconds
            )
        return self.cache[(path, cached)]

    def block(self, name: str) -> bool:
        blocks = self.info.get("blocks") or {}
        if name == "history" and name not in blocks:
            # Ältere HUBIplan-Stände kennen den Schalter „Geschichte“ noch nicht
            return bool(blocks.get("board", False))
        if name == "offices" and name not in blocks:
            # Ältere HUBIplan-Stände: „Ämter“ gehörten zum Schalter „Geschichte“
            return self.block("history")
        return bool(blocks.get(name, False))

    def layout(self, area: str) -> str:
        """Darstellung eines festen Bereichs (G5); unbekannt oder ältere Stände: erste Variante."""
        chosen = (self.info.get("layouts") or {}).get(area)
        choices = LAYOUTS.get(area, ())
        return chosen if chosen in choices else (choices[0] if choices else "")

    def intro(self, area: str) -> dict | None:
        """Einleitungstext oben in einem festen Bereich (G5), sonst None."""
        intro = (self.info.get("intros") or {}).get(area)
        return intro if isinstance(intro, dict) else None

    def history_parts(self) -> tuple[bool, bool]:
        """Menü „Geschichte“: (Chronik, Ämter) vorhanden? Ältere HUBIplan-Stände
        melden den Inhalt nicht; dann zählt nur der Schalter."""
        info = self.info
        chronik = self.block("history") and info.get("has_history_text", True)
        aemter = self.block("offices") and info.get("has_offices", True)
        return bool(chronik), bool(aemter)

    @property
    def units_label(self) -> str:
        """Bezeichnung der Untereinheiten (Mehrzahl), sonst „Einheiten“ in der Rahmensprache
        (UX-Audit WS-11)."""
        return str(self.info.get("unit_label_plural") or "").strip() or str(_("Einheiten"))

    @property
    def language(self) -> str:
        """Sprache der Rahmentexte (aus HUBIplan ``language``); unbekannt = Deutsch."""
        lang = str(self.info.get("language") or "").strip().lower()[:2]
        return lang if lang in LANGUAGES else "de"

    @property
    def content_language(self) -> str:
        """Sprache der Vereinsinhalte (HUBIplan ``content_language`` = Vereinssprache), sonst
        die der Rahmentexte."""
        lang = str(self.info.get("content_language") or "").strip().lower()[:2]
        return lang if lang in LANGUAGES else self.language

    @property
    def content_lang_attr(self):
        """`` lang="…"`` für Inhaltsblöcke, wenn die Vereinsinhalte in einer anderen Sprache als die
        Rahmentexte stehen (UX-Audit WS-11, WCAG 3.1.2), sonst leer."""
        from django.utils.html import format_html

        lang = self.content_language
        return format_html(' lang="{}"', lang) if lang != self.language else ""

    @property
    def is_preview(self) -> bool:
        return bool(self.info.get("preview"))

    @property
    def theme(self) -> dict:
        theme = dict(DEFAULT_THEME)
        for k, v in (self.info.get("theme") or {}).items():
            if k in theme and isinstance(v, str) and HEX.match(v):
                theme[k] = v
        # Für Text und Fokusrahmen im Inhalt; die Vereinsfarbe selbst bleibt für Flächen.
        # Gilt auch auf einem per Stilregler getönten oder grauen Seitengrund.
        # Eigene Flächenfarbe (Rolle „surface“) zählt ebenfalls
        # Schrift auf Haupt- und Akzentfarbe gegen genau diese Farbe prüfen (UX-Audit X-03)
        theme["on_primary"] = text_on(theme["primary"], theme["on_primary"])
        theme["on_accent"] = text_on(theme["accent"], theme["on_accent"])
        theme["link"] = link_color(
            theme["primary"],
            self.background_for(theme["primary"]),
            self.common_colors.get("surface"),
        )
        return theme

    # --- Stilregler (Konzept G1) ---

    @property
    def style(self) -> dict[str, str]:
        """Verstellte Stilregler aus HUBIplan (geprüft, ohne die vom Design gesperrten)."""
        if "_style" not in self.cache:
            style = stil.clean(self.info.get("style"), self.design)
            # Designpakete bringen eigenes CSS mit festen Farben mit: dort bleibt es hell
            if self.package is not None:
                style.pop("dark", None)
            self.cache["_style"] = style
        return self.cache["_style"]

    @property
    def style_attrs(self) -> str:
        attrs = stil.attrs(self.style)
        fonts = self.font_stacks
        if "text" in fonts:
            attrs += ' data-st-font-own="on"'
        if "heading" in fonts:
            attrs += ' data-st-heading-font-own="on"'
        return attrs

    @property
    def font_stacks(self) -> dict[str, str]:
        """Eigene Schriftfolgen (hubiplan #526); nicht bei Designpaketen mit eigenem CSS."""
        if "_fonts" not in self.cache:
            fonts = {} if self.package is not None else stil.font_stacks(self.info.get("style"))
            self.cache["_fonts"] = fonts
        return self.cache["_fonts"]

    @property
    def font_vars(self) -> str:
        """CSS-Variablen der eigenen Schriftfolgen; nur geprüfte Namen (stil.font_stack), daher
        sicher ungeschützt im <style>."""
        names = {"text": "--st-schrift", "heading": "--st-schrift-titel"}
        return "".join(f";{names[k]}:{v}" for k, v in self.font_stacks.items())

    def background_for(self, primary: str) -> str | None:
        # Rolle „Seitenhintergrund“ aus HUBIplan geht dem Stilregler vor
        return self.common_colors.get("background") or stil.background(self.style, primary)

    @property
    def header_image_shown(self) -> bool:
        """Kopfbild statt Wappen und Name, außer ein Regler wählt weißen oder farbigen Kopf."""
        image = self.info.get("header_image")
        has = isinstance(image, dict) and bool(image.get("url"))
        return has and self.style.get("header_bg") not in ("white", "color")

    @property
    def hero_name(self) -> bool:
        """Name auf dem Titelbild (Bühne zeigt ihn immer)."""
        return self.style.get("hero_name") == "on"

    @property
    def page_title_image(self) -> str | None:
        """Bild für das Überschriften-Band der Unterseiten (Stilregler page_title=image):
        das Titelbild der Startseite oder das erste Bild ihres Karussells, über diese Seite.
        Nur Adressen ohne Zeichen, die im CSS ``url("…")`` etwas bedeuten."""
        if self.style.get("page_title") != "image":
            return None
        greeting = self.info.get("greeting")
        if not isinstance(greeting, dict):
            return None
        image = greeting.get("image")
        gallery = greeting.get("gallery")
        gallery = [b for b in gallery if isinstance(b, dict)] if isinstance(gallery, list) else []
        if len(gallery) > 1 and self.style.get("carousel") == "random":
            # hubiplan #477: wie auf der Startseite ein zufälliges Bild des Karussells
            image = random.choice(gallery)  # noqa: S311 – keine Sicherheitsfrage
        elif not isinstance(image, dict):
            image = gallery[0] if gallery else None
        if not isinstance(image, dict):
            return None
        url = self.local(image.get("small_url") or image.get("url"))
        return url if url and SAFE_URL.match(url) else None

    @property
    def packages(self) -> dict:
        """Für diese Webseite freigegebene Designpakete aus HUBIplan: {schlüssel: {label, hash}}."""
        given = self.info.get("design_packages")
        if not isinstance(given, dict):
            return {}
        return {
            k: v
            for k, v in given.items()
            if isinstance(k, str)
            and designpaket.KEY.match(k)
            and k not in DESIGNS
            and isinstance(v, dict)
        }

    def _known(self, key) -> bool:
        return key in DESIGNS or key in self.packages

    @property
    def design(self) -> str:
        """Gewähltes Design; in der Vorschau ggf. ein anderes zum Ansehen. Lässt sich ein
        Paket nicht laden oder ist es ungültig, gilt Klassisch."""
        if "_design" not in self.cache:
            key = self.info.get("design")
            if self.is_preview and self._known(self.design_preview):
                key = self.design_preview
            if key in self.packages and self.package_for(key) is None:
                key = DEFAULT_DESIGN
            self.cache["_design"] = key if self._known(key) else DEFAULT_DESIGN
        return self.cache["_design"]

    def package_for(self, key: str) -> dict | None:
        if key not in self.packages:
            return None
        ck = ("_package", key)
        if ck not in self.cache:
            known = designpaket.cached_package(key, self.packages[key].get("hash"))
            if known is not None:
                self.cache[ck] = known
                return known
            try:
                data = self.get(f"design/{key}/")
            except (api.NotFound, api.Unavailable, api.Maintenance):
                data = None
            self.cache[ck] = designpaket.compile_package(data) if data else None
        return self.cache[ck]

    @property
    def package(self) -> dict | None:
        """Gezeichnetes Designpaket (oder None bei einem Standarddesign)."""
        return self.package_for(self.design)

    def vorlage(self, name: str):
        """Vorlage für das Design: aus dem Paket, sonst seite/designs/<design>/…, sonst Standard."""
        package = self.package
        layout = package["layout"] if package else self.design
        if name.startswith("seite/"):
            return [name.replace("seite/", f"seite/designs/{layout}/", 1), name]
        return name

    @property
    def package_has_css(self) -> bool:
        """Bringt das Designpaket eigenes CSS mit? Ein leeres (nur Kommentar) braucht keinen
        eigenen, das Zeichnen aufhaltenden Abruf (Ladezeiten 14.11.)."""
        package = self.package
        if not package:
            return False
        css = re.sub(r"/\*.*?\*/", "", package.get("css") or "", flags=re.S)
        return bool(css.strip())

    @property
    def preload_fonts(self) -> list[str]:
        """Schriften, die die Seite sicher braucht, gleich im Kopf anfordern: Sonst findet
        der Browser sie erst, wenn das CSS geladen ist (Ladezeiten 14.11.)."""
        font = self.style.get("font")
        if font in ("festive", "modern"):
            files = ["open-sans-400", "open-sans-600", "open-sans-700"]
            if font == "modern":
                files.append("roboto-700")
        elif font in ("clear", "elegant"):
            # Source Sans 3 (Ralf 14.11.2026); Crimson Pro nur für die fetten Überschriften
            files = ["source-sans-3-400", "source-sans-3-600", "source-sans-3-700"]
            if font == "elegant":
                files.append("crimson-pro-700")
        elif font == "readable":
            files = ["atkinson-hyperlegible-400", "atkinson-hyperlegible-700"]
        else:
            return []
        return [f"seite/schriften/{name}.woff2" for name in files]

    @property
    def kopf_vorlage(self):
        return self.vorlage("seite/kopf.html")

    @property
    def fuss_vorlage(self):
        return self.vorlage("seite/fuss.html")

    @property
    def design_label(self) -> str:
        if self.design in DESIGNS:
            return DESIGNS[self.design]
        return str(self.packages.get(self.design, {}).get("label") or self.design)[:60]

    @property
    def design_is_preview(self) -> bool:
        return self.design != (self.info.get("design") or DEFAULT_DESIGN)

    @property
    def _given_roles(self) -> dict:
        """Farben je Rolle des gewählten Designs, wie HUBIplan sie schickt (ungeprüft)."""
        designs = self.info.get("designs") if isinstance(self.info.get("designs"), dict) else {}
        given = designs.get(self.design) or {}
        if not given and self.design not in DESIGNS:
            # Paket ohne eigene Farben aus HUBIplan: wie Klassisch
            given = designs.get(DEFAULT_DESIGN) or {}
        return given if isinstance(given, dict) else {}

    @property
    def common_colors(self) -> dict[str, str]:
        """Gewählte Farben für Text, Sekundärtext, Flächen und Hintergrund (nur geprüfte)."""
        result = {}
        for role in COMMON_ROLES:
            item = self._given_roles.get(role)
            color = item.get("color") if isinstance(item, dict) else None
            if isinstance(color, str) and HEX.match(color):
                result[role] = color.lower()
        # Text und Sekundärtext müssen auf Fläche und Seitengrund lesbar sein (UX-Audit 16.11.
        # WS-04): HUBIplan prüft beim Speichern nicht jedes Paar; hier wird nachgebessert.
        flaechen = (result.get("surface", "#ffffff"), result.get("background", "#fbfaf7"))
        for role in ("text", "muted"):
            if role in result:
                result[role] = readable(result[role], flaechen)
        return result

    @property
    def gradients(self) -> dict[str, str]:
        """Verläufe je Rolle als CSS (nur geprüfte Farben und bekannte Richtungen)."""
        result = {}
        for role in GRADIENT_ROLES:
            item = self._given_roles.get(role)
            css = gradient_css(item.get("gradient") if isinstance(item, dict) else None)
            if css:
                result[role] = css
        return result

    @property
    def colors(self) -> dict:
        """Farben je Rolle des Designs aus HUBIplan; ältere Stände: aus den zwei Farben."""
        t = self.theme
        fallback = {
            "header": (t["primary"], t["on_primary"]),
            "nav": (t["accent"], t["on_accent"]),
            "line": (t["accent"], t["on_accent"]),
            "footer": (DARK, "#ffffff"),
            "band": (t["primary"], t["on_primary"]),
            "band2": (t["primary"], t["on_primary"]),
            "date": (t["primary"], t["on_primary"]),
        }
        given = self._given_roles
        result = {}
        for role in COLOR_ROLES:
            item = given.get(role) if isinstance(given, dict) else None
            color = item.get("color") if isinstance(item, dict) else None
            on = item.get("on_color") if isinstance(item, dict) else None
            if all(isinstance(v, str) and HEX.match(v) for v in (color, on)):
                result[role] = (color.lower(), on.lower())
            else:
                result[role] = fallback[role]
            # Schrift auf der Farbe der Rolle gegen genau diese Fläche prüfen (WS-18)
            color, on = result[role]
            result[role] = (color, text_on(color, on))
        return result

    @property
    def css_vars(self) -> str:
        """CSS-Variablen der Rollen (nur geprüfte Hex-Werte, sicher im <style>)."""
        names = {
            "header": "kopf",
            "nav": "menue",
            "line": "zier",
            "footer": "fuss",
            "date": "datum",
        }
        parts = []
        for role, (color, on) in self.colors.items():
            name = names.get(role, role)
            parts.append(f"--farbe-{name}:{color};--auf-{name}:{on}")
        # Verläufe: als Fläche (--bild-…) und für gerade Linien (--linie-…, border-image)
        for role, css in self.gradients.items():
            name = names.get(role, role)
            parts.append(f"--bild-{name}:{css};--linie-{name}:{css} 1")
        common = self.common_colors
        for role, var in COMMON_ROLES.items():
            if role in common and role != "background":
                parts.append(f"--{var}:{common[role]}")
        # Tabellenzeilen abwechselnd in der Flächenfarbe (Ralf 13.11.2026), nur wenn gewählt
        if "surface" in common:
            parts.append(f"--zeile:{common['surface']}")
        grund = self.background_for(self.theme["primary"])
        if grund:
            parts.append(f"--grund:{grund}")
        primary = self.theme["primary"]
        target = 7.0 if self.style.get("contrast") == "on" else 4.5
        if target > 4.5 and HEX.match(primary or ""):
            surface = common.get("surface")
            parts.append(f"--link:{link_color(primary, grund, surface, target=target)}")
        if self.style.get("dark") == "auto" and HEX.match(primary or ""):
            parts.append(f"--link-dunkel:{link_color_dark(primary, target)}")
        # Datumsfarbe als Schrift (Countdown, Zeitstrahl; UX-Audit 16.11. WS-04): wie die
        # Linkfarbe gegen Fläche und Seitengrund gerechnet, im Dunkeln aufgehellt
        date = self.colors["date"][0]
        datum_text = link_color(date, grund, common.get("surface"), target=target)
        parts.append(f"--datum-text:{datum_text}")
        if self.style.get("dark") == "auto":
            parts.append(f"--datum-text-dunkel:{link_color_dark(date, target)}")
        return ";".join(parts)

    @property
    def units_path(self) -> str:
        return units_slug(self.info)

    # --- Adressen ---

    def local(self, url: str | None) -> str | None:
        """Adresse aus HUBIplan → Adresse über diese Seite (nur Bilder und Logos)."""
        if not url:
            return None
        public = settings.HUBIPLAN_PUBLIC_URL
        rest = url[len(public) :] if url.startswith(public) else None
        if rest is None:
            for prefix in ("http://", "https://"):
                if url.startswith(prefix):
                    # Andere Herkunft (z. B. interne Adresse): nur den Pfad nehmen
                    after = url[len(prefix) :]
                    rest = after[after.find("/") :] if "/" in after else None
                    break
            else:
                rest = url if url.startswith("/") else None
        if rest is None:
            return None
        site_prefix = f"{api.PREFIX}{self.key}/"
        if rest.startswith(site_prefix):
            return reverse("medien", args=["a", rest[len(site_prefix) :].split("?")[0]]) + (
                "?" + rest.split("?", 1)[1] if "?" in rest else ""
            )
        if rest.startswith("/media/"):
            return reverse("medien", args=["m", rest[len("/media/") :]])
        return None


def units_slug(info: dict) -> str:
    label = (info.get("unit_label_plural") or "").strip().lower()
    return "zuege" if label in ("züge", "zuege") else "einheiten"


def global_maintenance() -> bool:
    return settings.MAINTENANCE or Path(settings.MAINTENANCE_FILE).exists()


def chosen_host(value: str | None) -> str | None:
    """Gewählte Webseite der Vorschau, nur bei fester Zuordnung und gültigem Hostnamen."""
    value = (value or "").strip().lower()
    if settings.SITE_HOST_OVERRIDE and HOSTNAME.match(value):
        return value
    return None


def host_of(request) -> str:
    if settings.SITE_HOST_OVERRIDE:
        if request.COOKIES.get(PREVIEW_COOKIE):
            chosen = chosen_host(request.COOKIES.get(SITE_COOKIE))
            if chosen:
                return chosen
        return settings.SITE_HOST_OVERRIDE
    return request.get_host().split(":")[0].lower()


def preview_session(request) -> str | None:
    """Vorschau-Sitzung aus dem Cookie (nur in gültiger Form); prüft HUBIplan."""
    preview = request.COOKIES.get(PREVIEW_COOKIE) or None
    if preview and not re.fullmatch(r"[A-Za-z0-9:_\-.]{10,400}", preview):
        return None
    return preview


# Gesamtaudit 15.11., WEB-01: Ein Vorschau-Cookie gilt erst, wenn HUBIplan die Sitzung
# bestätigt hat. Vorher schaltete schon ein frei erfundenes Cookie Zwischenspeicher und
# Bildablage ab. Das Ergebnis der Prüfung liegt kurz unter einem Hash der Sitzung (nie der Wert
# selbst); Prüfungen unbekannter Sitzungen sind je Besucher begrenzt.
PREVIEW_CONFIRM_SECONDS = 60
PREVIEW_CHECKS_PER_MINUTE = 20


def _preview_key(preview: str) -> str:
    import hashlib

    return "vorschau-ok:" + hashlib.sha256(preview.encode()).hexdigest()[:40]


def _may_check(request) -> bool:
    from django.core.cache import cache

    from .besucher import adresse

    ck = "vorschau-pruefen:" + (adresse(request) or "unbekannt")
    if cache.add(ck, 1, 60):
        return True
    try:
        return cache.incr(ck) <= PREVIEW_CHECKS_PER_MINUTE
    except ValueError:
        return True


def confirmed_preview(request, key: str) -> str | None:
    """Vorschau-Sitzung, wenn HUBIplan sie bestätigt hat (kurz gemerkt), sonst None."""
    from django.core.cache import cache

    preview = preview_session(request)
    if not preview:
        return None
    known = cache.get(_preview_key(preview))
    if known is not None:
        return preview if known else None
    if not _may_check(request):
        return None
    try:
        info = api.get(key, "", preview=preview)
    except (api.NotFound, api.Unavailable, api.Maintenance):
        return None
    ok = bool(info.get("preview"))
    cache.set(_preview_key(preview), ok, PREVIEW_CONFIRM_SECONDS)
    return preview if ok else None


def load(request) -> Site:
    """Webseite zur Anfrage. Wirft api.NotFound, api.Unavailable oder api.Maintenance."""
    from django.core.cache import cache

    key = api.resolve(host_of(request))
    preview = preview_session(request)
    if preview:
        known = cache.get(_preview_key(preview))
        if known is False or (known is None and not _may_check(request)):
            preview = None  # wie ein Besucher: mit Zwischenspeicher
    design = request.COOKIES.get(DESIGN_COOKIE) if preview else None
    # Standarddesign oder Paket; ob es das Paket gibt, prüft Site.design
    design = design if design and designpaket.KEY.match(design) else None
    try:
        info = api.get(key, "", preview=preview)
    except api.Maintenance as exc:
        return Site(
            key=key, info=exc.data, preview=preview, maintenance=True, design_preview=design
        )
    if preview:
        ok = bool(info.get("preview"))
        cache.set(_preview_key(preview), ok, PREVIEW_CONFIRM_SECONDS)
        if not ok:
            # HUBIplan kennt die Sitzung nicht: öffentliche Sicht, ab jetzt gecacht
            preview, design = None, None
        else:
            # Von diesen Vereinsadressen darf HUBIplan die Vorschau einbetten (Issue #729)
            request.vorschau_rahmen = info.get("frame_origins") or []
    return Site(key=key, info=info, preview=preview, design_preview=design)
