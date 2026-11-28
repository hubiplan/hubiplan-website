"""Feste Datentypen für das, was aus HUBIplan in die Vorlagen geht.

HUBIplan liefert Wörterbücher. Für Termin, Beitrag und Wettbewerb macht die Seite daraus
Objekte mit festen Feldern: die Felder aus HUBIplan (unbekannte, neuere Felder fallen weg)
und die hier berechneten (z. B. Beginn in Ortszeit). Vorlagen und Designpakete lesen die
Felder wie bisher (``termin.title``).

Wozu: Ein Tippfehler im Feldnamen zeigte bisher still nichts an. Mit ``STRENGE_DATEN``
(in den Tests und bei ``DJANGO_DEBUG`` an) ist das Lesen eines Feldes, das es nicht gibt,
ein Fehler. Im Betrieb bleibt es beim leeren Wert, damit ein Designpaket mit einem veralteten
Feld keine Seite zu Fall bringt.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field, fields

from django.conf import settings


class UnbekanntesFeld(Exception):
    """Eine Vorlage oder der Code liest ein Feld, das der Datentyp nicht hat."""


class Daten:
    """Grundlage der festen Datentypen (Unterklassen sind ``dataclass``)."""

    @classmethod
    def aus(cls, quelle: dict, **berechnet):
        """Objekt aus einer Antwort von HUBIplan; ``berechnet`` ergänzt oder ersetzt Felder."""
        namen = {f.name for f in fields(cls)}
        werte = {k: v for k, v in quelle.items() if k in namen}
        werte.update(berechnet)
        return cls(**werte)

    def __getattr__(self, name: str):
        # Nur für Namen, die es nicht gibt. Interne Namen (Kopieren, Zwischenspeichern) und
        # der Betrieb: wie bei jedem Objekt
        if name.startswith("_") or not getattr(settings, "STRENGE_DATEN", False):
            raise AttributeError(name)
        raise UnbekanntesFeld(f"{type(self).__name__} hat kein Feld „{name}“ (seite/daten.py)")


@dataclass
class Termin(Daten):
    """Ein Termin (``events/`` und hervorgehobene Termine in Abschnitten)."""

    # Aus HUBIplan
    id: str = ""
    title: str = ""
    starts_at: str = ""
    ends_at: str | None = None
    all_day: bool = False
    hide_end_time: bool = False
    location: str = ""
    address: str = ""
    description: str = ""
    category: str | None = None
    performance_kind: str | None = None
    color: str | None = None
    unit: str | None = None
    owner: str | None = None
    is_cancelled: bool = False
    note: str = ""
    attachments: list = field(default_factory=list)
    programme: str = ""
    registration: dict | None = None
    page: str | None = None
    # Nur auf der Veranstaltungsseite
    directions: str = ""
    ended: bool = False
    # Hier berechnet
    start: datetime.datetime | None = None
    end: datetime.datetime | None = None
    anhaenge: list = field(default_factory=list)
    anmeldung: dict | None = None


@dataclass
class Beitrag(Daten):
    """Ein Beitrag: aus Instagram oder Facebook (von HUBIplan gespeichert) oder ein eigener."""

    # Aus HUBIplan
    id: str = ""
    kind: str = ""
    kind_label: str = ""
    account: str = ""
    media_type: str = ""
    text: str = ""
    published_at: str = ""
    permalink: str = ""
    likes: int | None = None
    comment_count: int | None = None
    comments: list = field(default_factory=list)
    images: list = field(default_factory=list)
    # Nur eigene Beiträge
    slug: str = ""
    title: str = ""
    date: str = ""
    excerpt: str = ""
    has_more: bool = False
    videos: list = field(default_factory=list)
    unit: str | None = None
    # Hier berechnet
    when: datetime.datetime | None = None
    day: datetime.date | None = None
    url: str = ""


@dataclass
class Wettbewerb(Daten):
    """Ein Wettbewerb in Übersichten (die Rangliste selbst bleibt ein Wörterbuch)."""

    # Aus HUBIplan
    id: str = ""
    title: str = ""
    date: str = ""
    year: int | None = None
    occasion: str = ""
    discipline: str = ""
    location: str = ""
    own: bool = False
    organizer: str = ""
    status: str = ""
    live: bool = False
    provisional: bool = False
    final: bool = False
    url: str = ""
    slug: str = ""
    aliases: list = field(default_factory=list)
    # Nur auf der Startseite: Sieger je Wertung, gefallene Preise, Stand
    scorings: list = field(default_factory=list)
    prizes: list = field(default_factory=list)
    version: str = ""
    # Hier berechnet
    when: datetime.date | None = None
