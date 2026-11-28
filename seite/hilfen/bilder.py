"""Hilfen für Bilder und Logos: lokale Adressen, Bildsätze, Bildnachweise."""

from __future__ import annotations

from django.utils.html import format_html
from django.utils.translation import gettext as _

from .register import register


@register.simple_tag
def lokal(site, url):
    return site.local(url) if site is not None else None


def _with_query(url: str, query: str) -> str:
    return f"{url}{'&' if '?' in url else '?'}{query}"


@register.simple_tag
def bildsatz(site, image, sizes="100vw"):
    """``srcset``/``sizes`` für ein Webseitenbild aus HUBIplan (Ladezeiten 14.11.): klein
    (800 px), mittel (1200 px, von der Webseite gerechnet) und groß. Leer, wenn das Bild
    ohnehin klein ist oder keine kleine Fassung hat."""
    if site is None or not isinstance(image, dict):
        return ""
    url = site.local(image.get("url"))
    small = site.local(image.get("small_url"))
    width = image.get("width") or 0
    if not url or not small or not isinstance(width, int) or width <= 800:
        return ""
    parts = [f"{small} 800w"]
    if width > 1200:
        parts.append(f"{_with_query(url, 'size=medium')} 1200w")
    parts.append(f"{url} {width}w")
    return format_html(' srcset="{}" sizes="{}"', ", ".join(parts), sizes)


def _urheber(image) -> str:
    credit = image.get("credit") if isinstance(image, dict) else None
    return " ".join(credit.split()) if isinstance(credit, str) else ""


@register.simple_tag
def bildunterschrift(caption, image, klasse=""):
    """``<figcaption>`` mit Bildunterschrift und Urheber/in (Ralf 15.11.): „Foto: …“
    steht auch dann, wenn die Bildunterschrift leer oder ausgeschaltet ist
    (Namensnennung, § 13 UrhG). Ohne beides: nichts."""
    caption = caption if isinstance(caption, str) else ""
    credit = _urheber(image)
    if not caption and not credit:
        return ""
    attrs = format_html(' class="{}"', klasse) if klasse else ""
    nachweis = (
        format_html('<span class="bildnachweis">{}</span>', _("Foto: {name}").format(name=credit))
        if credit
        else ""
    )
    trenner = " " if caption and credit else ""
    return format_html("<figcaption{}>{}{}{}</figcaption>", attrs, caption, trenner, nachweis)


@register.filter
def mit_nachweis(caption, image) -> str:
    """Text unter dem großen Bild im Fenster: Bildunterschrift und „Foto: …“."""
    caption = caption if isinstance(caption, str) else ""
    credit = _urheber(image)
    if not credit:
        return caption
    nachweis = _("Foto: {name}").format(name=credit)
    return f"{caption} · {nachweis}" if caption else nachweis


@register.filter
def bildbreite(side, size) -> str:
    """``sizes`` für das Bild in „Text mit Bild“: neben dem Text höchstens halbe Breite,
    über oder unter dem Text die ganze Breite (klein: höchstens 22rem)."""
    if side in ("top", "bottom"):
        return (
            "(max-width: 22rem) 100vw, 22rem"
            if size == "small"
            else "(max-width: 64rem) 100vw, 64rem"
        )
    return "(max-width: 40rem) 100vw, 32rem"


@register.simple_tag
def logo_url(site, url, breite=120, hoehe=None):
    """Logo in der Größe für die Anzeige (doppelte Breite für scharfe Handys) statt bis
    1024 px aus HUBIplan (Ladezeiten 14.11.). Mit ``hoehe`` passt es in Breite × Höhe:
    Wo die Höhe die Anzeige begrenzt (Kopf, Fuß), bekommen breite Schriftzüge so genug
    Pixel (hubiplan #557)."""
    local = site.local(url) if site is not None else None
    if not local or "/medien/m/" not in local:
        return local
    query = f"w={int(breite)}" + (f"&h={int(hoehe)}" if hoehe else "")
    return _with_query(local, query)


@register.simple_tag
def kopflogo(site, url):
    """``src`` und ``srcset`` für das Logo im Kopf (hubiplan #557). Angezeigt wird es
    höchstens 104 px hoch (hoher Kopf) und 16 rem breit; 1x und 2x für scharfe Bildschirme.
    Leer ohne Logo."""
    einfach = logo_url(site, url, 256, 104)
    if not einfach:
        return ""
    if "/medien/m/" not in einfach:
        return format_html(' src="{}"', einfach)
    doppelt = logo_url(site, url, 512, 208)
    return format_html(' src="{}" srcset="{} 1x, {} 2x"', einfach, einfach, doppelt)
