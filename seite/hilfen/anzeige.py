"""Hilfen für die Anzeige: Text, Datum, Beträge, Telefon, Listen."""

from __future__ import annotations

import datetime
import functools
import re
from decimal import Decimal
from pathlib import Path

from django.utils.formats import date_format, number_format
from django.utils.html import format_html, json_script
from django.utils.translation import get_language, gettext_noop
from django.utils.translation import gettext as _

from .. import markdown
from .register import register


@register.filter
def md(text, site=None):
    """Markdown → HTML; mit ``site`` führen Links auf Untereinheiten zum richtigen Pfad."""
    return markdown.render(text, site.units_path if site is not None else "einheiten")


@register.simple_tag
def jahr():
    return datetime.date.today().year


QUELLCODE = "https://github.com/hubiplan/hubiplan-website"


FASSUNG = Path(__file__).resolve().parents[2] / ".fassung"


@functools.cache
def _fassung() -> str:
    """Commit der laufenden Fassung (deploy/deploy.sh legt ``.fassung`` ab), sonst leer."""
    try:
        sha = FASSUNG.read_text().strip()
    except OSError:
        return ""
    return sha if re.fullmatch(r"[0-9a-f]{40}", sha) else ""


@register.simple_tag
def quellcode():
    """Quellcode dieser Webseite (AGPL § 13): der laufende Commit, sonst das Repository."""
    sha = _fassung()
    return f"{QUELLCODE}/tree/{sha}" if sha else QUELLCODE


@register.filter
def mit_begleitung(reigns) -> bool:
    """Hat mindestens eine Regentschaft Begleitpersonen? Sonst entfällt die Spalte."""
    return any(r.get("companions") for r in reigns or [])


# Webseite #135: so viele Vorgänger stehen als Karten unter dem Band
VORGAENGER_KARTEN = 8


@register.filter
def vorgaenger(d) -> list:
    """Regentschaften einer Würde ohne die amtierenden, die neuesten zuerst, höchstens acht
    (Webseite #135); die vollständige Liste steht weiter aufklappbar darunter."""
    if not isinstance(d, dict):
        return []
    current = {
        (r.get("period") or r.get("year"), (r.get("holder") or {}).get("name"))
        for r in d.get("current") or []
        if isinstance(r, dict)
    }
    rest = [
        r
        for r in d.get("reigns") or []
        if isinstance(r, dict)
        and (r.get("period") or r.get("year"), (r.get("holder") or {}).get("name")) not in current
    ]
    return rest[:VORGAENGER_KARTEN]


@register.filter
def podest(rows) -> list:
    """Plätze 1 bis 3 einer Wertung (Webseite #139), bei Platzgleichheit alle Gleichplatzierten."""
    return [r for r in rows or [] if isinstance(r, dict) and r.get("place") in (1, 2, 3)]


@register.filter
def ohne_podest(rows) -> list:
    """Übrige Zeilen der Rangliste unter den Karten: ab Platz 4 und ohne Platz."""
    return [r for r in rows or [] if not (isinstance(r, dict) and r.get("place") in (1, 2, 3))]


# Datumsformate je Sprache (Englisch nach britischer Schreibweise, Konzept F4)
DATE_FORMATS = {
    "de": {
        "kurz": "j.n.Y",
        "tag": "j. F Y",
        "lang": "l, j. F Y",
        "wkurz": "D., j.n.Y",
        "zeit": r"j. F Y, H:i \U\h\r",
        "uhr": r"H:i \U\h\r",
    },
    "en": {
        "kurz": "d/m/Y",
        "tag": "j F Y",
        "lang": "l j F Y",
        "wkurz": "D d/m/Y",
        "zeit": "j F Y, H:i",
        "uhr": "H:i",
    },
}


@register.filter(expects_localtime=True)
def datum(value, art: str = "kurz"):
    """Datum (ISO-Text, date oder datetime) in der Sprache der Seite: ``kurz`` 1.4.2020,
    ``tag`` 1. April 2020, ``lang`` mit Wochentag, ``wkurz`` Sa., 1.4.2020, ``zeit`` mit
    Uhrzeit, ``uhr`` nur Uhrzeit."""
    if not value:
        return ""
    if isinstance(value, str):
        try:
            value = datetime.date.fromisoformat(value[:10])
        except ValueError:
            return value
    formate = DATE_FORMATS.get((get_language() or "de")[:2], DATE_FORMATS["de"])
    return date_format(value, formate.get(art, formate["kurz"]))


@register.filter
def nur_jahr(value):
    """ISO-Datum (Text) → Jahr. Ämter und Vorstand zeigen nur Jahre (Ralf 2026-10-31)."""
    if not value:
        return ""
    if isinstance(value, str):
        return value[:4] if value[:4].isdigit() else value
    return str(value.year)


@register.filter
def web_ziel(url: str) -> str:
    """Nur http(s)-Adressen als Linkziel; alles andere wird leer (kein javascript: o. Ä.)."""
    url = (url or "").strip()
    return url if url.lower().startswith(("https://", "http://")) else ""


@register.filter
def web_anzeige(url: str) -> str:
    """Adresse zum Lesen: ohne https:// und ohne Schrägstrich am Ende."""
    text = (url or "").strip().split("://", 1)[-1]
    return text.rstrip("/")


@register.filter
def tel(number: str) -> str:
    """Telefonnummer als tel:-Ziel (UX-Audit 31.10. S07): nur Ziffern und führendes +,
    „0049…“ wird „+49…“, die Klammer-Null in „+49 (0) 2131“ entfällt."""
    raw = (number or "").strip()
    raw = re.sub(r"\(0\)", "", raw)
    digits = re.sub(r"[^\d+]", "", raw)
    plus = digits.startswith("+")
    digits = digits.replace("+", "")
    if not plus and digits.startswith("00"):
        plus, digits = True, digits[2:]
    if len(digits) < 3:
        return ""
    return ("+" if plus else "") + digits


# Texte der Skripte (kontakt.js, karussell.js). Auf deutschen Seiten entfällt die Liste,
# die Skripte nehmen dann ihren eigenen Text.
JS_TEXTE = (
    gettext_noop("Bitte Ihren Namen eingeben."),
    gettext_noop("Bitte eine gültige E-Mail-Adresse eingeben, z. B. name@beispiel.de."),
    gettext_noop("Bitte einen Betreff eingeben."),
    gettext_noop("Bitte eine Nachricht mit mindestens 10 Zeichen eingeben."),
    gettext_noop("Bitte die markierten Felder prüfen."),
    gettext_noop("Nachricht wird vorbereitet …"),
    gettext_noop("Nachricht wird gesendet …"),
    gettext_noop("Danke! Ihre Nachricht ist angekommen."),
    gettext_noop("Danke! Ihre Nachricht ist bei {name} angekommen."),
    gettext_noop("Eine Bestätigung geht an {email}."),
    gettext_noop("Weitere Nachricht"),
    gettext_noop("Die Nachricht konnte nicht gesendet werden."),
    gettext_noop(
        "Sicherheitsprüfung erneuert. Ihre Nachricht bleibt erhalten. Bitte senden Sie erneut."
    ),
    gettext_noop(
        "Das Formular ist abgelaufen. Bitte kopieren Sie Ihre Nachricht "
        "und laden Sie die Seite neu."
    ),
    gettext_noop(
        "Diese Nachricht ist bereits bei uns angekommen. Sie müssen sie nicht erneut senden."
    ),
    gettext_noop(
        "An diese Stelle kann gerade keine Nachricht gehen. Bitte schreiben Sie über den "
        "Menüpunkt „Kontakt“ an den Verein."
    ),
    gettext_noop("Bitte die Angaben prüfen."),
    gettext_noop("Zu viele Nachrichten. Bitte später erneut versuchen."),
    gettext_noop("Die Nachricht konnte nicht gesendet werden. Bitte später erneut versuchen."),
    gettext_noop("Bildwechsel anhalten"),
    gettext_noop("Bildwechsel fortsetzen"),
    gettext_noop("Aktualisiert um {zeit} Uhr."),
    gettext_noop("Die Ergebnisse sind endgültig."),
)


@register.simple_tag
def seite_texte():
    """Übersetzungen für die Skripte als JSON-Block (nur, wenn die Seite nicht deutsch ist)."""
    if (get_language() or "de")[:2] == "de":
        return ""
    return json_script({t: _(t) for t in JS_TEXTE}, "seite-texte")


@register.filter
def euro(value) -> str:
    """Ganzer Euro-Betrag mit Tausenderpunkt in der Sprache der Seite (Spendenaufruf)."""
    try:
        amount = int(value)
    except (TypeError, ValueError):
        return ""
    text = number_format(amount, force_grouping=True)
    return f"€{text}" if (get_language() or "de")[:2] == "en" else f"{text} €"


@register.filter
def betrag(value) -> str:
    """Euro-Betrag mit Cent in der Sprache der Seite (Teilnahmegebühr), 0 als „kostenlos“."""
    try:
        amount = Decimal(str(value))
    except (TypeError, ValueError, ArithmeticError):
        return ""
    if amount == 0:
        return _("kostenlos")
    text = number_format(amount, decimal_pos=2, force_grouping=True)
    return f"€{text}" if (get_language() or "de")[:2] == "en" else f"{text} €"


@register.filter
def iban(value) -> str:
    """IBAN in Vierergruppen zum Lesen und Abschreiben."""
    raw = re.sub(r"\s", "", value or "")
    return " ".join(raw[i : i + 4] for i in range(0, len(raw), 4))


@register.filter
def hat_art(abschnitte, kind: str) -> bool:
    """Gibt es unter den Abschnitten einen dieser Art? (z. B. Bilder → Bildfenster laden)"""
    return any(isinstance(s, dict) and s.get("kind") == kind for s in abschnitte or [])


# Webseite #145 (long_tables=columns): ab so vielen Zeilen lohnen zwei Spalten nebeneinander
ZWEISPALTIG_AB = 20


@register.simple_tag
def zweispaltig(site, zeilen, spalten=2) -> int:
    """Zeilen der linken Spalte, wenn eine lange, schmale Tabelle zweispaltig stehen soll, sonst 0.

    Nur mit dem Regler, nur bis zwei Spalten und ab ``ZWEISPALTIG_AB`` Zeilen; bei ungerader
    Zahl bekommt die linke Spalte eine Zeile mehr. Ob es am Bildschirm wirklich zwei Spalten
    werden, entscheidet die Breite (stil.css, ab 800 px Inhaltsbreite)."""
    if site is None or site.style.get("long_tables") != "columns" or int(spalten) > 2:
        return 0
    n = len(zeilen or ())
    return (n + 1) // 2 if n >= ZWEISPALTIG_AB else 0


@register.simple_tag
def rolle(aktiv, name):
    """``role="…"`` nur für zweispaltige Tabellen: Sie werden am Bildschirm als Raster gesetzt,
    die Rollen halten sie für Vorleseprogramme sicher als eine Tabelle zusammen."""
    return format_html(' role="{}"', name) if aktiv else ""
