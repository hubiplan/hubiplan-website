"""Designpakete: Standarddesigns exportieren, eingespielte Designs aus HUBIplan zeichnen.

Ein Paket enthält nur ``design.json`` (einschließlich Standardlayout-Auswahl) und
``design.css``. Freies HTML/Django-DTL wird niemals ausgeführt. Standarddesigns
exportiert die Webseite unter ``/design-paket/<schlüssel>.zip``; eingespielte
Datenpakete liefert HUBIplan über ``design/<schlüssel>/`` aus.

HUBIplan prüft Pakete beim Einspielen; diese Webseite prüft beim Abholen noch einmal mit
denselben Regeln (wie ``hubiplan/backend/website/design_packages.py``). Was die Prüfung
nicht besteht, wird nicht gezeichnet; die Webseite zeigt dann Klassisch.
"""

from __future__ import annotations

import io
import json
import logging
import re
import zipfile
from collections import OrderedDict

from django.contrib.staticfiles import finders

log = logging.getLogger(__name__)

FORMAT = "hubiplan-designpaket"
VERSION = 1
MAX_CSS_BYTES = 64 * 1024
MAX_TEMPLATE_BYTES = 64 * 1024
KEY = re.compile(r"^[a-z][a-z0-9-]{1,30}$")

# Vorlagen, die ein Paket ersetzen darf (Name im Paket → Vorlage der Webseite)
TEMPLATES = {
    "vorlagen/kopf.html": "seite/kopf.html",
    "vorlagen/fuss.html": "seite/fuss.html",
    "vorlagen/start.html": "seite/start.html",
}

FORBIDDEN_CSS = [
    re.compile(p, re.I)
    for p in (
        r"@import",
        r"@font-face",
        r"url\s*\(",
        r"image-set\s*\(",
        r"expression\s*\(",
        r"javascript\s*:",
        r"behavior\s*:|-moz-binding",
        r"\\",
        r"<",
    )
]


def css_ok(text) -> bool:
    return (
        isinstance(text, str)
        and len(text.encode()) <= MAX_CSS_BYTES
        and not any(p.search(text) for p in FORBIDDEN_CSS)
    )


def template_ok(text) -> bool:
    """Imported template source is never executable (including conditional output)."""
    return False


# --- Eingespielte Pakete zeichnen --------------------------------------------

# Übersetzte Vorlagen je Prüfsumme (wenige Pakete je Installation)
_compiled: OrderedDict = OrderedDict()
_MAX_COMPILED = 32


def cached_package(key: str, digest) -> dict | None:
    """Schon übersetztes Paket mit genau diesem Stand (Hash), sonst None. Spart den Abruf
    bei HUBIplan: Der Inhalt ändert sich nur mit dem Hash."""
    if not isinstance(digest, str) or not digest:
        return None
    package = _compiled.get((key, digest))
    if package is not None:
        _compiled.move_to_end((key, digest))
    return package


def compile_package(data) -> dict | None:
    """Datenpaket prüfen und geprüftes Repository-Layout wählen; ungültig → None."""
    if not isinstance(data, dict):
        return None
    key, digest = data.get("key"), data.get("hash")
    if not (isinstance(key, str) and KEY.fullmatch(key) and isinstance(digest, str)):
        return None
    cache_key = (key, digest)
    if cache_key in _compiled:
        _compiled.move_to_end(cache_key)
        return _compiled[cache_key]
    css = data.get("css") or ""
    raw = data.get("templates") or {}
    if not css_ok(css) or not isinstance(raw, dict):
        log.warning("Designpaket %s: CSS ungültig, zeige Klassisch", key)
        return None
    # Only maintained repository templates may produce markup. Old free-template
    # packages are quarantined through the existing Classic fallback.
    from .site import DEFAULT_DESIGN, DESIGNS

    layout = data.get("layout", DEFAULT_DESIGN)
    if raw or not isinstance(layout, str) or layout not in DESIGNS:
        log.warning("Designpaket %s: freie Vorlage/ungültiges Layout, zeige Klassisch", key)
        return None
    package = {
        "key": key,
        "hash": digest[:64],
        "label": str(data.get("label") or key)[:60],
        "css": css,
        "templates": {},
        "layout": layout,
    }
    _compiled[cache_key] = package
    while len(_compiled) > _MAX_COMPILED:
        _compiled.popitem(last=False)
    return package


# --- Standarddesigns exportieren ---------------------------------------------


def builtin_css(key: str) -> str:
    path = finders.find(f"seite/design-{key}.css")
    if path:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    return "/* Keine Abweichungen von seite.css (Grundgestaltung aller Designs). */\n"


def builtin_templates(key: str) -> dict[str, str]:
    """Vorlagen, die ein Standarddesign selbst mitbringt (seite/designs/<schlüssel>/…)."""
    from django.template import TemplateDoesNotExist
    from django.template.loader import get_template

    result = {}
    for zip_name, target in TEMPLATES.items():
        name = target.replace("seite/", f"seite/designs/{key}/", 1)
        try:
            origin = get_template(name).origin
        except TemplateDoesNotExist:
            continue
        with open(origin.name, encoding="utf-8") as fh:
            result[zip_name] = fh.read()
    return result


def export_builtin(key: str, label: str, catalog: dict, exported: str) -> bytes:
    """Standarddesign als Paket. ``catalog`` aus HUBIplan: Name, Hinweis, Farbrollen."""
    hint = catalog.get("hint") or ""
    manifest = {
        "format": FORMAT,
        "version": VERSION,
        "key": key,
        "label": {"de": catalog.get("label") or label, "en": catalog.get("label_en") or label},
        "hint": {"de": hint, "en": catalog.get("hint_en") or hint},
        "roles": catalog.get("roles") or {},
        "skizze_wie": key,
        "exportiert": exported,
        # Herkunft: HUBIplan übernimmt beim Einspielen die Farbzuordnung dieses Designs
        "quelle": key,
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("design.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        archive.writestr("design.css", builtin_css(key))
    return buf.getvalue()
