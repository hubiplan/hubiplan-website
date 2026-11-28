"""Startseite."""

from __future__ import annotations

import random

from django.views.decorators.http import require_GET

from ..site import (
    Site,
)
from .aufbau import HOME_SECTIONS, _layout
from .beitraege import POST_KINDS, _posts, has_posts
from .ergebnisse import _home_results, _results_on
from .rahmen import _page, site_view
from .termine import _events, _upcoming


@require_GET
@site_view()
def start(request, site: Site):
    layout = _layout(site)
    home = [s["kind"] for s in layout if s["kind"] in HOME_SECTIONS]
    greeting = _random_title_image(site, site.info.get("greeting") or None)
    events = _upcoming(_events(site), 3) if "events" in home and site.block("events") else []
    honors = (
        site.get("honors/").get("dignities", [])
        if "honors" in home and site.block("honors")
        else []
    )
    results = _home_results(site) if "results" in home and _results_on(site) else []
    response = _page(
        request,
        "seite/start.html",
        site,
        {
            "greeting": greeting,
            # Abschnitte mit Gestaltung (G3); Zeitung: Spalte je Abschnitt aus HUBIplan
            "abschnitte": layout,
            "abschnitte_seite": [s for s in layout if s.get("column") == "side"],
            "abschnitte_haupt": [s for s in layout if s.get("column") != "side"],
            # Für Designpakete mit eigener start.html: nur die Vorlagen wie bisher
            "sections": [s["vorlage"] for s in layout],
            "sections_side": [s["vorlage"] for s in layout if s.get("column") == "side"],
            "sections_main": [s["vorlage"] for s in layout if s.get("column") != "side"],
            "greeting_title": bool(greeting and greeting.get("title") and "greeting" in home),
            "carousel": bool(
                greeting and "carousel" in home and len(greeting.get("gallery") or []) > 1
            ),
            "events": events,
            "results": results,
            # Ralf 2026-10-31: auf der Startseite nur Träger des laufenden Jahres
            "honors": [
                d for d in honors if d.get("current") and d.get("current_year") is not False
            ][:2],
            # Je Netzwerk die 3 neuesten Beiträge (von HUBIplan gespeichert, nichts von Meta)
            **{
                f"{kind}_posts": _posts(site, kind, limit=3)
                if kind in home and has_posts(site.info, kind)
                else []
                for kind in POST_KINDS
            },
        },
    )
    if site.style.get("carousel") == "random" and not site.is_preview:
        # jedes Mal neu wählen, auch hinter einem Zwischenspeicher
        response["Cache-Control"] = "no-cache"
    return response


def _random_title_image(site: Site, greeting: dict | None) -> dict | None:
    """hubiplan #477: Stilregler „Bilderkarussell“ auf „zufällig“: Bei jedem Aufruf wird ein
    Bild des Karussells gewählt und steht dann fest wie ein einzelnes Titelbild. Die Wahl
    geschieht hier auf dem Server, daher gilt sie auch für Designpakete (ohne Skript)."""
    if not isinstance(greeting, dict) or site.style.get("carousel") != "random":
        return greeting
    gallery = [b for b in greeting.get("gallery") or [] if isinstance(b, dict)]
    if len(gallery) < 2:
        return greeting
    chosen = random.choice(gallery)  # noqa: S311 – keine Sicherheitsfrage
    return {**greeting, "image": chosen, "gallery": [chosen]}
