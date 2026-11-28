"""Farbrechnung für die Gestaltung: Kontrast nach WCAG, lesbare Schrift- und Linkfarben,
Verläufe. Reine Rechnung ohne Anfrage und ohne Daten der Webseite."""

from __future__ import annotations

import re

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
DARK = "#1d2421"
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


def gradient_css(item) -> str | None:
    """{from, to, direction} aus HUBIplan → linear-gradient(…); sonst None."""
    if not isinstance(item, dict):
        return None
    start, end = item.get("from"), item.get("to")
    if not all(isinstance(v, str) and HEX.match(v) for v in (start, end)):
        return None
    direction = DIRECTIONS.get(item.get("direction"), DIRECTIONS["right"])
    return f"linear-gradient({direction},{start.lower()},{end.lower()})"
