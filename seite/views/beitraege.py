"""Beiträge: Aktuelles, Presse und weitere Beitragsarten."""

from __future__ import annotations

import datetime
import re

from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_GET

from .. import api
from ..site import (
    Site,
)
from .rahmen import _page, site_view
from .termine import _anzahl, _zeit

POST_KINDS = ("instagram", "facebook", "own")


# Beiträge je Seite unter „Aktuelles“; ältere stehen im Archiv (?seite=2 …, #707)
POSTS_PER_PAGE = 24


POST_PAGES_MAX = 200


def has_posts(info: dict, kind: str | None = None) -> bool:
    """Gibt es sichtbare Beiträge (aus HUBIplan-Info oder Info einer Untereinheit)?
    „own“ sind eigene Beiträge des Vereins (HUBIplan ab 23.11.2026)."""
    flags = info.get("posts") or {}
    if not isinstance(flags, dict):
        return False
    return bool(flags.get(kind)) if kind else any(flags.get(k) for k in POST_KINDS)


def _posts_page(
    site: Site,
    kind: str | None = None,
    unit: str | None = None,
    limit: int = POSTS_PER_PAGE,
    page: int = 1,
) -> tuple[list[dict], bool]:
    """Eigene Beiträge und die aus Instagram/Facebook, von HUBIplan lokal gespeichert (nie
    von Meta), nach Datum gemischt; dazu, ob es ältere gibt."""
    if not site.block("posts"):
        return [], False
    query = [f"anzahl={limit}"]
    if kind:
        query.append(f"art={kind}")
    if unit:
        query.append(f"einheit={unit}")
    if page > 1:
        query.append(f"seite={page}")
    try:
        data = site.get("posts/?" + "&".join(query))
    except api.NotFound:
        return [], False
    items = [_post(p) for p in data.get("posts", []) if isinstance(p, dict)]
    return items, bool(data.get("more"))


def _posts(
    site: Site, kind: str | None = None, unit: str | None = None, limit: int = 24
) -> list[dict]:
    return _posts_page(site, kind, unit, limit)[0]


def _post(p: dict) -> dict:
    when = parse_datetime(p["published_at"]) if p.get("published_at") else None
    permalink = p.get("permalink") or ""
    if not permalink.startswith("https://"):
        permalink = ""
    entry = {
        **p,
        "when": timezone.localtime(when) if when else None,
        "permalink": permalink,
        "images": [i for i in p.get("images") or [] if isinstance(i, dict) and i.get("url")],
        # Likes und Kommentarzahl nur, wenn HUBIplan sie liefert (Schalter je Kanal)
        "likes": _anzahl(p.get("likes")),
        "comment_count": _anzahl(p.get("comment_count")),
        "comments": [
            {
                "author": str(k.get("author") or ""),
                "text": str(k.get("text") or ""),
                "when": timezone.localtime(w) if (w := _zeit(k.get("published_at"))) else None,
            }
            for k in p.get("comments") or []
            if isinstance(k, dict) and k.get("text")
        ],
    }
    if p.get("kind") == "own":
        # Eigener Beitrag (#707): Datum ohne Uhrzeit, Videos als Link mit Vorschaubild
        try:
            entry["day"] = datetime.date.fromisoformat(p.get("date") or "")
        except ValueError:
            entry["day"] = None
        entry["videos"] = [
            v
            for v in p.get("videos") or []
            if isinstance(v, dict) and str(v.get("url") or "").startswith("https://")
        ]
        slug = p.get("slug") or ""
        entry["url"] = reverse("beitrag", args=[slug]) if re.fullmatch(r"[-a-z0-9]+", slug) else ""
    return entry


@require_GET
@site_view()
def news(request, site: Site):
    if not site.block("posts") or not has_posts(site.info):
        raise api.NotFound()
    kind = request.GET.get("kanal")
    if kind not in POST_KINDS or not has_posts(site.info, kind):
        kind = None
    kinds = [k for k in POST_KINDS if has_posts(site.info, k)]
    try:
        page = max(1, min(int(request.GET.get("seite") or 1), POST_PAGES_MAX))
    except ValueError:
        page = 1
    posts, more = _posts_page(site, kind, page=page)
    if page > 1 and not posts:
        raise api.NotFound()
    return _page(
        request,
        "seite/aktuelles.html",
        site,
        {
            "posts": posts,
            "kind": kind,
            "kinds": kinds if len(kinds) > 1 else [],
            "seite": page,
            "aeltere": page + 1 if more else None,
            "neuere": page - 1 if page > 1 else None,
        },
    )


@require_GET
@site_view()
def news_post(request, site: Site, slug: str):
    """Ein eigener Beitrag mit ganzem Text, Bildern und Videos (#707)."""
    if not site.block("posts"):
        raise api.NotFound()
    data = site.get(f"posts/eigene/{slug}/").get("post")
    if not isinstance(data, dict):
        raise api.NotFound()
    return _page(request, "seite/beitrag.html", site, {"post": _post(data)})


@require_GET
@site_view()
def press(request, site: Site):
    if not site.block("press"):
        raise api.NotFound()
    items = []
    for d in site.get("documents/?section=press").get("documents", []):
        try:
            when = datetime.date.fromisoformat(d["date"]) if d.get("date") else None
        except ValueError:
            when = None
        items.append(
            {
                **d,
                "when": when,
                "url": site.local(d.get("url")),
                "preview": site.local(d.get("preview_url")),
            }
        )
    return _page(request, "seite/presse.html", site, {"artikel": items})
