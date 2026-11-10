"""Abschnitte der Startseite aus HUBIplan (Konzept webseite-baukasten G3, Ralf 10.11.2026).
Alle Daten erfunden."""

import datetime

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
