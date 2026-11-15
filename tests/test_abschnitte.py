"""Abschnitte der Startseite aus HUBIplan (Konzept webseite-baukasten G3, Ralf 10.11.2026).
Alle Daten erfunden."""

import datetime
import re

from django.core.cache import cache
from django.utils import timezone

from . import fake


def text(response) -> str:
    return response.content.decode()


def bild(key: str) -> dict:
    return {
        "key": key,
        "url": f"{fake.BASE}images/{key}/",
        "small_url": f"{fake.BASE}images/{key}/?size=small",
        "width": 1200,
        "height": 400,
        "caption": "",
        "alt": f"Bild {key}",
    }


def layout(*sections):
    return [{"bg": "none", "width": "content", "column": "main", **s} for s in sections]


def test_ohne_home_layout_wie_bisher(client, hubiplan):
    hubiplan.info.pop("home_layout", None)
    hubiplan.info["home"] = ["greeting"]
    html = text(client.get("/"))
    assert '<section class="begruessung">' in html


def test_eigene_abschnitte(client, hubiplan):
    hubiplan.info["palette"] = [
        {"color": "#123456", "on_color": "#ffffff"},
        {"color": "#abcdef", "on_color": "#000000"},
    ]
    hubiplan.info["home_layout"] = layout(
        {"key": "greeting", "kind": "greeting", "bg": "light", "width": "text"},
        {"key": "c:t1", "kind": "text", "title": "Über uns", "text": "Seit **1900**."},
        {
            "key": "c:b1",
            "kind": "banner",
            "image": bild("festzug"),
            "line": "Schützenfest 2099",
            "height": "high",
            "bg": "p1",
            "width": "full",
        },
        {
            "key": "c:k1",
            "kind": "buttons",
            "title": "",
            "align": "center",
            "buttons": [
                {"label": "Mitglied werden", "target": {"key": "contact"}},
                {"label": "Programm", "target": {"key": "link", "url": "https://example.org/p"}},
                {"label": "Kaputt", "target": {"key": "link", "url": "javascript:alert(1)"}},
            ],
        },
        {
            "key": "c:z1",
            "kind": "quote",
            "text": "Einigkeit macht stark.",
            "name": "Erika Beispiel",
            "bg": "p9",
        },
        {
            "key": "c:x1",
            "kind": "tiles",
            "title": "Schnell gefunden",
            "columns": 2,
            "tiles": [
                {
                    "title": "Termine",
                    "text": "Alle Feste",
                    "image": None,
                    "target": {"key": "events"},
                },
                {"title": "Ohne Ziel", "text": "", "image": bild("kachel"), "target": None},
            ],
        },
        {"key": "c:u1", "kind": "unbekannt"},
    )
    html = text(client.get("/"))
    assert (
        '<section class="begruessung abschnitt-text abschnitt-hg" '
        'style="background:var(--abschnitt-hell);color:var(--text)">' in html
    )
    assert "<h2>Über uns</h2>" in html and "<strong>1900</strong>" in html
    assert 'class="banner banner-high abschnitt-voll abschnitt-hg abschnitt-farbig"' in html
    assert "background:#abcdef;color:#000000" in html
    assert 'src="/medien/a/images/festzug/"' in html
    assert "Schützenfest 2099" in html
    assert '<p class="knoepfe knoepfe-center">' in html
    assert '<a class="knopf" href="/kontakt/">Mitglied werden</a>' in html
    assert 'href="https://example.org/p" target="_blank" rel="noopener noreferrer"' in html
    assert "javascript:" not in html and "Kaputt" not in html
    # Unbekannte Palettenfarbe: kein Hintergrund
    assert '<section class="zitat">' in html and "Erika Beispiel" in html
    assert '<ul class="bildkacheln spalten-2">' in html
    assert '<a href="/termine/">Termine</a>' in html
    assert "<h3>Ohne Ziel</h3>" in html


def test_termin_mit_countdown(client, hubiplan):
    start = timezone.localtime() + datetime.timedelta(days=5)
    hubiplan.info["home_layout"] = layout(
        {
            "key": "c:e1",
            "kind": "event",
            "title": "Bald ist Schützenfest",
            "event": {
                "id": "e9",
                "title": "Schützenfest",
                "starts_at": start.isoformat(),
                "ends_at": (start + datetime.timedelta(hours=3)).isoformat(),
                "all_day": False,
                "location": "Festzelt",
                "is_cancelled": False,
            },
        },
        {"key": "c:e2", "kind": "event", "title": "kaputt", "event": {"title": "ohne Beginn"}},
    )
    html = text(client.get("/"))
    assert "Bald ist Schützenfest" in html and "noch 5 Tage" in html
    assert "Festzelt" in html and "kaputt" not in html


def test_ansprechpartner_und_album(client, hubiplan):
    hubiplan.info["home_layout"] = layout(
        {
            "key": "c:a1",
            "kind": "contacts",
            "title": "",
            "roles": [
                {
                    "id": "r1",
                    "name": "1. Vorsitzende",
                    "holders": [{"name": "Erika Beispiel", "photo_url": None}],
                    "vacant": False,
                    "email": None,
                    "contact_form": True,
                }
            ],
        },
        {
            "key": "c:g1",
            "kind": "album",
            "title": "Festzug",
            "album": {"slug": "festzug-2099", "title": "Festzug 2099"},
            "images": [bild("f1"), bild("f2")],
        },
    )
    html = text(client.get("/"))
    assert "<h2>Ansprechpartner</h2>" in html and "Erika Beispiel" in html
    assert 'href="/kontakt/?an=r1"' in html
    assert html.count('href="/galerie/festzug-2099/"') == 3
    assert "Album „Festzug 2099“ ansehen" in html


def test_zeitung_spalte_je_abschnitt(client, hubiplan):
    hubiplan.info["design"] = "newspaper"
    hubiplan.info["home_layout"] = layout(
        {"key": "greeting", "kind": "greeting", "column": "side"},
        {"key": "c:t1", "kind": "text", "title": "Hauptspalte", "text": ""},
    )
    html = text(client.get("/"))
    haupt = html.split('<div class="spalte-haupt">', 1)[1].split("</div>", 1)[0]
    seite = html.split('<div class="spalte-seite">', 1)[1]
    assert "Hauptspalte" in haupt and "begruessung" not in haupt
    assert "begruessung" in seite.split("</main>", 1)[0]


def test_textseite_ohne_abschnitte_wie_bisher(client, hubiplan):
    html = text(client.get("/seite/anfahrt/"))
    assert "<h1>Anfahrt</h1>" in html and "Mit dem Bus." in html
    # #77/#101: Titel an der Inhaltskante, Text in Lesebreite (.textseite, .seite-text)
    assert '<div class="textseite">' in html and '<div class="seite-text">' in html
    assert "abschnitt-" not in html.split("<h1>", 1)[1].split("</main>", 1)[0]


def test_textseite_volle_breite_ohne_weitere_abschnitte(client, hubiplan):
    """#77: Breite des Textes der Seite gilt auch, wenn es sonst keine Abschnitte gibt."""
    hubiplan.antworten["pages/anfahrt/"] = {
        "slug": "anfahrt",
        "title": "Anfahrt",
        "text": "Mit dem Bus.",
        "image": None,
        "sections": layout({"key": "body", "kind": "body", "width": "full"}),
    }
    html = text(client.get("/seite/anfahrt/"))
    assert '<section class="seite-text abschnitt-voll">' in html
    assert "Mit dem Bus." in html


def test_textseite_titel_und_text_an_der_inhaltskante():
    """#101: Titel und Text stehen in der Flucht der übrigen Abschnitte; die Breite des
    Textes der Seite wirkt in allen drei Stufen."""
    from pathlib import Path

    static = Path(__file__).resolve().parent.parent / "seite/static/seite"
    css = (static / "seite.css").read_text()
    # Lesebreite ja, aber nicht mehr mittig; der Titel hat keine eigene Spalte mehr
    assert "\n.seite-text .text { max-width: 44rem; }\n" in css
    assert ".textseite > h1" not in css
    # „Textbreite“ = Lesespalte mittig, „volle Breite“ = ohne Lesebreite
    assert ".abschnitt-text { max-width: 44rem; margin-left: auto; margin-right: auto; }" in css
    assert ".seite-text:is(.abschnitt-text, .abschnitt-voll) .text { max-width: none; }" in css
    # Band: kein eigener Einzug für Textseiten, es gilt der Einzug aller Seiten
    stil = (static / "stil.css").read_text()
    assert "22rem" not in stil and "19.5rem))" not in stil


def test_textseite_breite_des_textes_wirkt(client, hubiplan):
    """#101: „content“ (Standard) ohne Klasse, „text“ und „full“ je mit eigener Klasse."""
    for width, erwartet in (
        ("content", '<div class="seite-text">'),
        ("text", '<section class="seite-text abschnitt-text">'),
        ("full", '<section class="seite-text abschnitt-voll">'),
    ):
        hubiplan.antworten["pages/anfahrt/"] = {
            "slug": "anfahrt",
            "title": "Anfahrt",
            "text": "Mit dem Bus.",
            "image": None,
            "sections": layout({"key": "body", "kind": "body", "width": width}),
        }
        cache.clear()
        html = text(client.get("/seite/anfahrt/"))
        assert erwartet in html, width


def test_textseite_aus_abschnitten(client, hubiplan):
    """G4: Textseiten aus denselben Abschnitten; der bisherige Text ist „body“."""
    hubiplan.antworten["pages/anfahrt/"] = {
        "slug": "anfahrt",
        "title": "Anfahrt",
        "text": "Mit dem Bus.",
        "image": None,
        "sections": layout(
            {"key": "c:z1", "kind": "quote", "text": "Herzlich willkommen!", "name": ""},
            {"key": "body", "kind": "body", "width": "text"},
            {
                "key": "c:k1",
                "kind": "buttons",
                "title": "",
                "align": "left",
                "buttons": [{"label": "Schreiben Sie uns", "target": {"key": "contact"}}],
            },
        ),
    }
    html = text(client.get("/seite/anfahrt/"))
    main = html.split("<h1>Anfahrt</h1>", 1)[1]
    assert main.index("Herzlich willkommen!") < main.index("Mit dem Bus.")
    assert main.index("Mit dem Bus.") < main.index("Schreiben Sie uns")
    assert '<section class="seite-text abschnitt-text">' in main
    assert '<a class="knopf" href="/kontakt/">Schreiben Sie uns</a>' in main


def test_farbige_abschnitte_oben_und_unten_gleich():
    """#108: Farbige Abschnitte haben oben und unten denselben Innenabstand, egal ob sie mit
    einer Überschrift oder mit Text beginnen; Innen- und Außenabstand folgen der Stufe."""
    from pathlib import Path

    static = Path(__file__).resolve().parents[1] / "seite" / "static" / "seite"
    css = (static / "seite.css").read_text()
    regel = css.split(".abschnitt-hg {", 1)[1].split("}", 1)[0]
    assert "padding: var(--abschnitt-innen) 1.2rem" in regel
    assert "margin-block: var(--abschnitt-aussen)" in regel
    assert ":root { --abschnitt-innen: 1.4rem; --abschnitt-aussen: 2.2rem; }" in css
    assert (
        ".abschnitt-hg > :first-child, .abschnitt-hg > :first-child > :first-child"
        " { margin-top: 0; }" in css
    )
    assert (
        ".abschnitt-hg > :last-child, .abschnitt-hg > :last-child > :last-child"
        " { margin-bottom: 0; }" in css
    )
    stil = (static / "stil.css").read_text()
    for stufe in ("compact", "generous"):
        assert f'html[data-st-spacing="{stufe}"] {{ --abschnitt-innen:' in stil
    # die Linie zwischen Abschnitten verkleinert farbige Kästen nicht mehr oben
    assert "section:not(.begruessung-bilder, .abschnitt-hg) { padding-top: .4rem; }" in stil


def test_ziel_untereinheit_und_eigene_adresse(client, hubiplan):
    """Webseite #111: Kacheln und Knöpfe führen zur Seite einer Untereinheit; eine volle
    Adresse auf die eigene Webseite öffnet im selben Fenster, ohne „↗“."""
    hubiplan.info["home_layout"] = layout(
        {
            "key": "c:x1",
            "kind": "tiles",
            "title": "Mitmachen",
            "columns": 3,
            "tiles": [
                {
                    "title": "Im Jägerzug",
                    "text": "",
                    "image": None,
                    "target": {"key": "unit", "slug": "jaeger"},
                },
                {
                    "title": "Nachwuchs",
                    "text": "",
                    "image": None,
                    "target": {"key": "link", "url": "https://testserver/seite/nachwuchs/"},
                },
                {
                    "title": "Mit www",
                    "text": "",
                    "image": None,
                    "target": {"key": "link", "url": "https://www.testserver/kontakt/"},
                },
                {"title": "Ohne Slug", "text": "", "image": None, "target": {"key": "unit"}},
            ],
        },
        {
            "key": "c:k1",
            "kind": "buttons",
            "title": "",
            "align": "left",
            "buttons": [
                {"label": "Zum Zug", "target": {"key": "unit", "slug": "jaeger"}},
                {"label": "Dachverband", "target": {"key": "link", "url": "https://example.org/"}},
            ],
        },
    )
    cache.clear()
    html = text(client.get("/"))
    zug = re.search(r'<a href="(/[^"]*/jaeger/)">Im Jägerzug</a>', html)
    assert zug, html
    assert f'<a class="knopf" href="{zug.group(1)}">Zum Zug</a>' in html
    assert '<a href="https://testserver/seite/nachwuchs/">Nachwuchs</a>' in html
    assert '<a href="https://www.testserver/kontakt/">Mit www</a>' in html
    assert "<h3>Ohne Slug</h3>" in html
    # fremde Adresse bleibt ein Link nach außen
    assert (
        '<a class="knopf" href="https://example.org/" target="_blank" rel="noopener noreferrer">'
        "Dachverband" in html
    )
