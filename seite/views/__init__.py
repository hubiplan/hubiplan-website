"""Seiten der Vereinswebseite.

Jede Seite lädt die Webseite zur Anfrage (Hostname → Schlüssel → Grunddaten).
Im Wartungsmodus gibt es nur Wartungsseite, Impressum und Datenschutz, außer mit
gültiger Vorschau.

Die Seiten liegen nach Bereich in eigenen Modulen; hier stehen nur die Namen, die
``config/urls.py`` und die Tests brauchen.
"""

from .aufbau import _look
from .beitraege import has_posts, news, news_post, press
from .dateien import STREAM_FROM, design_css, design_export, favicon, health, media, robots
from .ergebnisse import result, result_series, result_table, result_version, results
from .inhalte import _search_url, contact, contact_challenge, event_page, join, page, search
from .rahmen import not_found
from .rechtliches import accessibility, imprint, privacy
from .startseite import start
from .termine import bookings, events
from .verein import (
    album,
    board,
    chronicle,
    dignity,
    documents,
    gallery,
    history,
    honorary,
    honors,
    members,
    memorial,
    offices,
    old_honors_path,
    repertoire,
    unit,
    units,
)
from .vorschau import preview, preview_design, preview_end

__all__ = [
    "STREAM_FROM",
    "_look",
    "_search_url",
    "accessibility",
    "album",
    "board",
    "bookings",
    "chronicle",
    "contact",
    "contact_challenge",
    "design_css",
    "design_export",
    "dignity",
    "documents",
    "event_page",
    "events",
    "favicon",
    "gallery",
    "has_posts",
    "health",
    "history",
    "honorary",
    "honors",
    "imprint",
    "join",
    "media",
    "members",
    "memorial",
    "news",
    "news_post",
    "not_found",
    "offices",
    "old_honors_path",
    "page",
    "press",
    "preview",
    "preview_design",
    "preview_end",
    "privacy",
    "repertoire",
    "result",
    "result_series",
    "result_table",
    "result_version",
    "results",
    "robots",
    "search",
    "start",
    "unit",
    "units",
]
