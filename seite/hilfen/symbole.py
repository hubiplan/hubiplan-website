"""Symbole für soziale Medien und Hinweise."""

from __future__ import annotations

import datetime

from .register import register

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


# Hinweisleiste auffälliger (hubiplan, Ralf 16.11.2026): Stil, Platz, Symbol und Countdown.
# Nur bekannte Werte; ältere HUBIplan-Fassungen ohne diese Angaben bekommen die Vorgabe.
HINWEIS_STILE = ("accent", "alert", "festive", "quiet")


HINWEIS_PLAETZE = ("top", "below", "float")


_HS = (
    'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
    'stroke-linejoin="round"'
)


HINWEIS_SYMBOLE = {
    "megaphone": f'<path {_HS} d="M3 10v4a1 1 0 0 0 1 1h2l5 4V5L6 9H4a1 1 0 0 0-1 1z"/>'
    f'<path {_HS} d="M15.5 8.5a5 5 0 0 1 0 7M18.5 5.5a9 9 0 0 1 0 13"/>',
    "calendar": f'<rect x="3.5" y="5" width="17" height="15.5" rx="2" {_HS}/>'
    f'<path {_HS} d="M3.5 10h17M8 3v4M16 3v4"/><path fill="currentColor" d="M7 13h3v3H7z"/>',
    "star": '<path fill="currentColor" d="M12 2.8l2.8 5.8 6.3.9-4.6 4.4 1.1 6.3L12 17.2l-5.6 3 '
    '1.1-6.3-4.6-4.4 6.3-.9z"/>',
    "info": f'<circle cx="12" cy="12" r="9" {_HS}/><path {_HS} d="M12 11v6"/>'
    '<circle cx="12" cy="7.6" r="1.3" fill="currentColor"/>',
    "alert": f'<path {_HS} d="M12 3.5 2.5 20h19z"/><path {_HS} d="M12 10v4.5"/>'
    '<circle cx="12" cy="17.2" r="1.2" fill="currentColor"/>',
}


@register.simple_tag
def hinweis_ansicht(hinweis) -> dict:
    """Aussehen der Hinweisleiste: Stil, Platz, Symbol (SVG) und Tage bis zum Datum."""
    from django.utils import timezone
    from django.utils.safestring import mark_safe

    hinweis = hinweis if isinstance(hinweis, dict) else {}
    stil = hinweis.get("style")
    platz = hinweis.get("place")
    body = HINWEIS_SYMBOLE.get(hinweis.get("icon") or "")
    symbol = (
        mark_safe(  # noqa: S308 - feste Symbole aus diesem Modul
            f'<svg viewBox="0 0 24 24" width="26" height="26" aria-hidden="true" '
            f'focusable="false">{body}</svg>'
        )
        if body
        else ""
    )
    tage = None
    try:
        tag = datetime.date.fromisoformat(str(hinweis.get("date") or ""))
    except ValueError:
        tag = None
    if tag is not None:
        rest = (tag - timezone.localdate()).days
        tage = rest if rest >= 0 else None
    return {
        "stil": stil if stil in HINWEIS_STILE else "accent",
        "platz": platz if platz in HINWEIS_PLAETZE else "below",
        "symbol": symbol,
        "tage": tage,
    }
