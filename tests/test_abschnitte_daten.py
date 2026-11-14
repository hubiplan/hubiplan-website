"""Abschnittsarten mit Daten aus HUBIplan (ab 14.11.2026): Majestäten einer Untereinheit,
Ergebnisse eines Wettbewerbs, Galerie-Übersicht, Neueste Beiträge, Mitgliederbereich und App,
Zahlen aus HUBIplan. Alle Daten erfunden."""

from . import fake
from .test_abschnitte import bild, layout, text


def test_daten_abschnitte(client, hubiplan):
    hubiplan.info["home_layout"] = layout(
        {
            "key": "c:m",
            "kind": "unit_honors",
            "title": "",
            "unit": {"name": "Jägerzug", "slug": "jaegerzug"},
            "honors": fake.HONORS["dignities"],
        },
        {
            "key": "c:w",
            "kind": "competition",
            "title": "Unser Pokalschießen",
            "competition": {
                "id": fake.COMP,
                "title": "Pokalschießen 2026",
                "date": "2026-10-03",
                "final": True,
                "scorings": [{"scoring": "Einzel", "rows": [{"place": 1, "name": "Erika B."}]}],
                "prizes": [],
            },
        },
        {
            "key": "c:a",
            "kind": "albums",
            "title": "",
            "albums": [
                {
                    "slug": "festzug",
                    "title": "Festzug",
                    "cover": bild("f1"),
                    "images": 4,
                    "albums": 0,
                }
            ],
        },
        {
            "key": "c:p",
            "kind": "posts",
            "title": "",
            "channel": "instagram",
            "posts": [fake._post(1, "instagram", "Schönes Fest!")],
        },
        {
            "key": "c:x",
            "kind": "app",
            "title": "",
            "text": "Termine und Rundschreiben immer dabei.",
            "login_url": "https://verein.example.org/anmelden",
            "qr": True,
            "store_url": "https://play.google.com/store/apps/details?id=de.hubiplan.app",
        },
        {
            "key": "c:z",
            "kind": "live_facts",
            "title": "Der Verein",
            "items": [{"value": "312", "label": "Mitglieder"}],
        },
    )
    html = text(client.get("/"))
    assert "Majestäten: Jägerzug" in html and "Karl Krone" in html
    assert 'href="/zuege/jaegerzug/"' in html or 'href="/einheiten/jaegerzug/"' in html
    assert "Unser Pokalschießen" in html and "1. Erika B." in html
    assert f'href="/ergebnisse/{fake.COMP}/"' in html
    assert "galerie-alben" in html and "Festzug" in html
    assert 'class="beitraege"' in html and "/aktuelles/?kanal=instagram" in html
    assert 'href="https://verein.example.org/anmelden"' in html and "<svg" in html
    assert "App bei Google Play" in html
    assert '<span class="zahl">312</span>' in html


def test_daten_abschnitte_unvollstaendig(client, hubiplan):
    hubiplan.info["home_layout"] = layout(
        {"key": "c:w", "kind": "competition", "title": "Kaputt", "competition": {"id": "x"}},
        {"key": "c:p", "kind": "posts", "title": "Leer", "posts": []},
        {"key": "c:x", "kind": "app", "title": "Ohne", "login_url": "javascript:alert(1)"},
    )
    html = text(client.get("/"))
    assert "Kaputt" not in html and "Leer" not in html and "javascript:" not in html
