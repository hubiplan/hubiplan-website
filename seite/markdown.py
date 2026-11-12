"""Texte aus HUBIplan (Markdown) sicher als HTML ausgeben.

Rohes HTML im Text wird nicht übernommen (nur Text). Bilder aus HUBIplan stehen
als ``bild:<schlüssel>`` im Text und werden zu Adressen dieser Seite. Links auf
eigene Seiten stehen als ``seite:<ziel>`` im Text (z. B. ``seite:termine``,
``seite:seite/<adresse>``, ``seite:einheit/<adresse>``) und werden hier zu
Adressen dieser Seite, auch unter einem Unterpfad wie auf dem Testserver.
"""

from __future__ import annotations

import re

from django.urls import NoReverseMatch, reverse
from django.utils.safestring import mark_safe
from markdown_it import MarkdownIt

_md = MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": False})
_md.enable("table")
_md.enable("strikethrough")

IMAGE_REF = re.compile(r"\]\(bild:([A-Za-z0-9_\-]{4,40})\)")
PAGE_PREFIX = "seite:"
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# seite:<ziel> → Name der Adresse
PAGES = {
    "start": "start",
    "aktuelles": "aktuelles",
    "vorstand": "vorstand",
    "termine": "termine",
    "majestaeten": "majestaeten",
    "geschichte": "chronik",
    "chronik": "chronik",
    "aemter": "aemter",
    "dokumente": "dokumente",
    "kontakt": "kontakt",
    "mitglied-werden": "mitglied_werden",
    "impressum": "impressum",
    "datenschutz": "datenschutz",
    "barrierefreiheit": "barrierefreiheit",
}


def page_href(target: str, units_path: str = "einheiten") -> str | None:
    """Ziel eines Links ``seite:<ziel>`` → Adresse dieser Seite (None: unbekannt)."""
    parts = target.strip("/").split("/")
    try:
        if len(parts) == 1:
            if parts[0] == "einheiten":
                return reverse("einheiten", kwargs={"pfad": units_path})
            if parts[0] in PAGES:
                return reverse(PAGES[parts[0]])
        elif len(parts) == 2 and SLUG.match(parts[1]):
            if parts[0] == "seite":
                return reverse("seite", args=[parts[1]])
            if parts[0] == "einheit":
                return reverse("einheit", kwargs={"pfad": units_path, "slug": parts[1]})
    except NoReverseMatch:
        return None
    return None


def _render_link_open(self, tokens, idx, options, env):
    token = tokens[idx]
    href = token.attrGet("href") or ""
    if href.startswith(PAGE_PREFIX):
        local = page_href(href[len(PAGE_PREFIX) :], env.get("units_path", "einheiten"))
        if local is None:
            # Unbekanntes Ziel: nur der Text bleibt
            env["skip_close"] = True
            return ""
        token.attrSet("href", local)
    if href.startswith(("http://", "https://")):
        token.attrSet("rel", "noopener noreferrer")
    return self.renderToken(tokens, idx, options, env)


def _render_link_close(self, tokens, idx, options, env):
    if env.pop("skip_close", False):
        return ""
    return self.renderToken(tokens, idx, options, env)


_md.add_render_rule("link_open", _render_link_open)
_md.add_render_rule("link_close", _render_link_close)


def render(text: str | None, units_path: str = "einheiten") -> str:
    if not text:
        return ""

    def image(match):
        key = match.group(1)
        url = reverse("medien", args=["a", f"images/{key}/"]) + "?size=small"
        return f"]({url})"

    env = {"units_path": units_path}
    return mark_safe(_md.render(IMAGE_REF.sub(image, text), env))  # noqa: S308
