"""Welche Webseite gehört zur Anfrage, und wie werden Adressen aus HUBIplan lokal?

Bilder und Logos lädt der Browser nie direkt bei HUBIplan, sondern über
``/medien/…`` dieser Seite: So gelten Vorschau und Wartung auch für Bilder, und
die Seite lädt nichts von fremden Adressen.
"""

from __future__ import annotations

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


def link_color(primary: str, background: str | None = None) -> str:
    """Linkfarbe aus der Vereinsfarbe: so wenig wie nötig abgedunkelt, bis Text auf
    Weiß und auf dem Seitengrund 4,5 : 1 erreicht (WCAG 1.4.3; wie HUBIplan)."""
    backgrounds = LINK_BACKGROUNDS + ((background,) if background else ())
    for step in range(21):
        color = darken(primary, step * 0.05)
        if min(contrast(color, bg) for bg in backgrounds) >= 4.5:
            return color
    return "#000000"


@dataclass
class Site:
    key: str
    info: dict
    preview: str | None = None
    maintenance: bool = False
    design_preview: str | None = None
    cache: dict = field(default_factory=dict)

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

    def history_parts(self) -> tuple[bool, bool]:
        """Menü „Geschichte“: (Chronik, Ämter) vorhanden? Ältere HUBIplan-Stände
        melden den Inhalt nicht; dann zählt nur der Schalter."""
        info = self.info
        chronik = self.block("history") and info.get("has_history_text", True)
        aemter = self.block("offices") and info.get("has_offices", True)
        return bool(chronik), bool(aemter)

    @property
    def language(self) -> str:
        """Sprache der Rahmentexte (aus HUBIplan ``language``); unbekannt = Deutsch."""
        lang = str(self.info.get("language") or "").strip().lower()[:2]
        return lang if lang in LANGUAGES else "de"

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
        theme["link"] = link_color(theme["primary"], self.background_for(theme["primary"]))
        return theme

    # --- Stilregler (Konzept G1) ---

    @property
    def style(self) -> dict[str, str]:
        """Verstellte Stilregler aus HUBIplan (geprüft, ohne die vom Design gesperrten)."""
        if "_style" not in self.cache:
            self.cache["_style"] = stil.clean(self.info.get("style"), self.design)
        return self.cache["_style"]

    @property
    def style_attrs(self) -> str:
        return stil.attrs(self.style)

    def background_for(self, primary: str) -> str | None:
        return stil.background(self.style, primary)

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
        given = (self.info.get("designs") or {}).get(self.design) or {}
        if not given and self.design not in DESIGNS:
            # Paket ohne eigene Farben aus HUBIplan: wie Klassisch
            given = (self.info.get("designs") or {}).get(DEFAULT_DESIGN) or {}
        result = {}
        for role in COLOR_ROLES:
            item = given.get(role) if isinstance(given, dict) else None
            color = item.get("color") if isinstance(item, dict) else None
            on = item.get("on_color") if isinstance(item, dict) else None
            if all(isinstance(v, str) and HEX.match(v) for v in (color, on)):
                result[role] = (color.lower(), on.lower())
            else:
                result[role] = fallback[role]
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
        grund = self.background_for(self.theme["primary"])
        if grund:
            parts.append(f"--grund:{grund}")
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


def load(request) -> Site:
    """Webseite zur Anfrage. Wirft api.NotFound, api.Unavailable oder api.Maintenance."""
    key = api.resolve(host_of(request))
    preview = preview_session(request)
    design = request.COOKIES.get(DESIGN_COOKIE) if preview else None
    # Standarddesign oder Paket; ob es das Paket gibt, prüft Site.design
    design = design if design and designpaket.KEY.match(design) else None
    try:
        info = api.get(key, "", preview=preview)
    except api.Maintenance as exc:
        return Site(
            key=key, info=exc.data, preview=preview, maintenance=True, design_preview=design
        )
    return Site(key=key, info=info, preview=preview, design_preview=design)
