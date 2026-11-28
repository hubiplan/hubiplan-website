"""Ergebnisse der Wettbewerbe: Übersicht, Einzelseite, Tabellen, Reihen."""

from __future__ import annotations

import re
from collections import OrderedDict

from django.http import (
    JsonResponse,
)
from django.views.decorators.http import require_GET

from .. import api
from ..site import (
    Site,
)
from .rahmen import ADRESSE, _page, _readable, site_view

# Wettbewerbsergebnisse (Wettbewerbe Schritt 5): Stand laufender Wettbewerbe nur kurz
# zwischenspeichern; die Rangliste selbst hängt am Stand und ist dann sofort neu
LIVE_SECONDS = 5


OVERVIEW_SECONDS = 30


TOKEN = re.compile(r"^[a-f0-9]{20}$")


def _results_on(site: Site) -> bool:
    return bool(site.info.get("results_url"))


def _home_results(site: Site) -> list[dict]:
    try:
        data = site.get("results/?start=1", seconds=OVERVIEW_SECONDS)
    except api.NotFound:
        return []
    return [_with_date(c) for c in data.get("competitions", [])]


def _with_date(comp: dict) -> dict:
    from datetime import date

    try:
        when = date.fromisoformat(comp.get("date") or "")
    except ValueError:
        when = None
    return {**comp, "when": when}


# --- Wettbewerbsergebnisse ---


@require_GET
@site_view()
def results(request, site: Site):
    """Neuester veröffentlichter Wettbewerb direkt, ältere als Links im Archiv."""
    if not _results_on(site):
        raise api.NotFound()
    data = site.get("results/", seconds=OVERVIEW_SECONDS)
    comps = [_with_date(c) for c in data.get("competitions", [])]
    # HUBIplan liefert veröffentlichte Wettbewerbe nach Datum absteigend.
    latest = _result(site, comps[0]["id"]) if comps else None
    older = comps[1:]
    response = _page(
        request,
        "seite/ergebnisse.html",
        site,
        {
            "latest": latest,
            "live": [c for c in older if not c.get("final")],
            "years": _by_year([c for c in older if c.get("final")]),
            "series": data.get("series", []),
            "trophies": data.get("trophies", []),
        },
    )
    if latest and not latest.get("final"):
        response["Cache-Control"] = "no-cache"
    return response


def _by_year(comps: list[dict]) -> list[tuple[int, list[dict]]]:
    groups: OrderedDict[int, list[dict]] = OrderedDict()
    for c in comps:
        groups.setdefault(c.get("year"), []).append(c)
    return list(groups.items())


def _result(site: Site, kennung: str) -> dict:
    """Rangliste eines Wettbewerbs; zuerst den kleinen Stand, dann die Rangliste zu genau
    diesem Stand (neues Ergebnis → neuer Stand → sofort neue Tabelle)."""
    if not _results_on(site) or not ADRESSE.match(kennung):
        raise api.NotFound()
    stand = site.get(f"results/{kennung}/version/", seconds=LIVE_SECONDS)
    version = re.sub(r"[^A-Za-z0-9]", "", str(stand.get("version", "")))[:64]
    return _with_date(site.get(f"results/{kennung}/?stand={version}"))


@require_GET
@site_view()
def result(request, site: Site, kennung: str):
    data = _result(site, kennung)
    redirect = _readable(data, kennung, "ergebnis")
    if redirect is not None:
        return redirect
    response = _page(request, "seite/ergebnis.html", site, {"c": data})
    if not data.get("final"):
        response["Cache-Control"] = "no-cache"
    return response


@require_GET
@site_view()
def result_table(request, site: Site, kennung: str):
    """Nur die Rangliste (für das Nachladen während „live“)."""
    data = _result(site, kennung)
    response = _page(
        request,
        "seite/ergebnis_inhalt.html",
        site,
        {"c": data, "embedded": request.GET.get("eingebettet") == "1"},
    )
    response["Cache-Control"] = "no-cache"
    return response


@require_GET
@site_view()
def result_version(request, site: Site, kennung: str):
    """Kleiner Stand für den Browser: Er fragt ihn während „live“ alle 15 Sekunden ab."""
    if not _results_on(site) or not ADRESSE.match(kennung):
        raise api.NotFound()
    stand = site.get(f"results/{kennung}/version/", seconds=LIVE_SECONDS)
    response = JsonResponse(
        {"version": str(stand.get("version", "")), "final": bool(stand.get("final"))}
    )
    response["Cache-Control"] = "no-cache"
    return response


@require_GET
@site_view()
def result_series(request, site: Site, kennung: str):
    """Archiv einer Reihe: Sieger je Jahr und Titel über alle Jahre."""
    if not _results_on(site) or not ADRESSE.match(kennung):
        raise api.NotFound()
    data = site.get(f"results/series/{kennung}/")
    redirect = _readable(data, kennung, "reihe")
    if redirect is not None:
        return redirect
    for y in data.get("years", []):
        slug = y.get("slug")
        readable = isinstance(slug, str) and ADRESSE.match(slug)
        y["kennung"] = slug if readable else _token_of(y.get("url"))
    return _page(request, "seite/ergebnis_reihe.html", site, {"s": data})


def _token_of(url: str | None) -> str | None:
    """Kennung eines Wettbewerbs aus seiner Adresse bei HUBIplan (…/results/<kennung>/)."""
    m = re.search(r"/results/([a-f0-9]{20})/$", url or "")
    return m.group(1) if m else None
