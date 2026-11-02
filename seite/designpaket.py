"""Designpakete: Standarddesigns exportieren, eingespielte Designs aus HUBIplan zeichnen.

Ein Paket (ZIP) enthält ``design.json`` (Steckbrief), ``design.css`` und höchstens die
Vorlagen Kopf, Fuß und Startseite. Standarddesigns exportiert diese Webseite unter
``/design-paket/<schlüssel>.zip``; eingespielte Pakete liegen in HUBIplan, das sie für
freigegebene Webseiten über ``design/<schlüssel>/`` ausliefert (Konzept
konzepte/designs-import-export.md, Ralf 2026-11-02).

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
from django.template import engines
from django.template.base import Lexer, TokenType

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

ALLOWED_TAGS = {
    "if", "elif", "else", "endif", "for", "empty", "endfor", "with", "endwith", "block",
    "endblock", "extends", "include", "load", "comment", "endcomment", "url", "static",
    "translate", "trans", "blocktranslate", "blocktrans", "plural", "endblocktranslate",
    "endblocktrans", "get_current_language", "now", "cycle", "firstof", "spaceless",
    "endspaceless", "ifchanged", "endifchanged",
    # Bibliothek „seite“
    "menue", "lokal", "baustein", "jahr", "quellcode", "einheiten_url", "einheit_url",
    "sm_symbol", "seite_texte",
}  # fmt: skip
ALLOWED_FILTERS = {
    "default", "default_if_none", "length", "add", "slice", "join", "first", "last", "lower",
    "upper", "title", "capfirst", "yesno", "pluralize", "floatformat", "wordcount",
    "truncatewords", "truncatechars", "urlencode", "date", "time", "linebreaksbr", "linebreaks",
    "striptags", "cut", "divisibleby", "escape", "force_escape",
    # Bibliothek „seite“
    "md", "datum", "nur_jahr", "tel", "web_ziel", "web_anzeige", "mit_begleitung",
}  # fmt: skip
ALLOWED_LIBRARIES = {"seite", "static", "i18n"}
ALLOWED_EXTENDS = {"seite/basis.html", "seite/start.html"}
INCLUDE_LITERAL = re.compile(r"""^(["'])seite/[a-z0-9_/]+\.html\1$""")
FILTER_USE = re.compile(r"\|\s*([A-Za-z_]\w*)")
FORBIDDEN_HTML = [
    re.compile(
        r"<\s*(script|iframe|object|embed|style|link|meta|base|frame|frameset|form)\b", re.I
    ),
    re.compile(r"\son[a-z]+\s*=", re.I),
    re.compile(r"\s(style|srcdoc|formaction)\s*=", re.I),
    re.compile(r"javascript\s*:|vbscript\s*:|data\s*:\s*text/html", re.I),
    re.compile(r"\s(src|srcset|poster|action|data|background)\s*=\s*[\"']?\s*(https?:)?//", re.I),
]
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


def _tag_ok(contents: str) -> bool:
    bits = contents.split()
    tag = bits[0] if bits else ""
    if tag not in ALLOWED_TAGS:
        return False
    if tag == "load":
        return "from" not in bits and set(bits[1:]) <= ALLOWED_LIBRARIES
    if tag == "extends":
        return len(bits) == 2 and bits[1][0] in "\"'" and bits[1].strip("\"'") in ALLOWED_EXTENDS
    if tag == "include":
        target = bits[1] if len(bits) > 1 else ""
        return bool(INCLUDE_LITERAL.match(target) and ".." not in target) or target == "vorlage"
    return True


def template_ok(text) -> bool:
    if not isinstance(text, str) or len(text.encode()) > MAX_TEMPLATE_BYTES:
        return False
    try:
        tokens = Lexer(text).tokenize()
    except Exception:  # noqa: BLE001
        return False
    in_comment = False
    for token in tokens:
        contents = token.contents
        if token.token_type == TokenType.BLOCK:
            tag = contents.split()[0] if contents.split() else ""
            if in_comment:
                in_comment = tag != "endcomment"
                continue
            if tag == "comment":
                in_comment = True
            if not _tag_ok(contents):
                return False
            if not set(FILTER_USE.findall(contents)) <= ALLOWED_FILTERS:
                return False
        elif token.token_type == TokenType.VAR and not in_comment:
            if not set(FILTER_USE.findall(contents)) <= ALLOWED_FILTERS:
                return False
        elif token.token_type == TokenType.TEXT and not in_comment:
            if any(p.search(contents) for p in FORBIDDEN_HTML):
                return False
    return True


# --- Eingespielte Pakete zeichnen --------------------------------------------

# Übersetzte Vorlagen je Prüfsumme (wenige Pakete je Installation)
_compiled: OrderedDict = OrderedDict()
_MAX_COMPILED = 32


def compile_package(data) -> dict | None:
    """Paket aus HUBIplan prüfen und übersetzen: {key, hash, label, css, templates}.

    ``templates``: Vorlage der Webseite → übersetzte Vorlage. Ungültig → None."""
    if not isinstance(data, dict):
        return None
    key, digest = data.get("key"), data.get("hash")
    if not (isinstance(key, str) and KEY.match(key) and isinstance(digest, str)):
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
    allowed = set(TEMPLATES.values())
    templates = {}
    engine = engines["django"]
    for name, text in raw.items():
        if name not in allowed or not template_ok(text):
            log.warning("Designpaket %s: Vorlage %s ungültig, zeige Klassisch", key, name)
            return None
        try:
            templates[name] = engine.from_string(text)
        except Exception:  # noqa: BLE001 - Syntaxfehler: Paket nicht zeichnen
            log.warning("Designpaket %s: Vorlage %s fehlerhaft, zeige Klassisch", key, name)
            return None
    package = {
        "key": key,
        "hash": digest[:64],
        "label": str(data.get("label") or key)[:60],
        "css": css,
        "templates": templates,
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
        for zip_name, text in builtin_templates(key).items():
            archive.writestr(zip_name, text)
    return buf.getvalue()
