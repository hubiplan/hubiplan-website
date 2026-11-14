"""Weitere Abschnittsarten ohne Datenbezug (HUBIplan ab 14.11.2026). Alle Daten erfunden."""

from . import fake
from .test_abschnitte import bild, layout, text


def test_inhalte(client, hubiplan):
    hubiplan.info["home_layout"] = layout(
        {
            "key": "c:j",
            "kind": "join",
            "title": "Mach mit",
            "text": "Wir suchen **dich**.",
            "label": "",
            "target": {"key": "join"},
        },
        {
            "key": "c:s",
            "kind": "donation",
            "title": "Neue Fahne",
            "text": "",
            "holder": "Schützenverein Musterstadt",
            "iban": "DE02120300000000202051",
            "bic": "",
            "purpose": "Spende Fahne",
            "goal": 5000,
            "raised": 2300,
            "percent": 46,
            "label": "",
            "url": "https://example.org/spenden",
        },
        {
            "key": "c:h",
            "kind": "hours",
            "title": "Schießzeiten",
            "items": [{"day": "Dienstag", "time": "19–22 Uhr", "note": "nur Luftgewehr"}],
            "text": "",
        },
        {
            "key": "c:c",
            "kind": "columns",
            "title": "",
            "items": [{"title": "Links", "text": "A"}, {"title": "", "text": "B"}],
        },
        {
            "key": "c:t",
            "kind": "table",
            "title": "Beiträge",
            "head": ["Art", "Beitrag"],
            "rows": [["Erwachsene", "60 €"]],
            "text": "",
        },
        {
            "key": "c:z",
            "kind": "timeline",
            "title": "",
            "items": [{"when": "1920", "title": "Gründung", "text": ""}],
        },
        {
            "key": "c:p",
            "kind": "program",
            "title": "Programm",
            "days": [{"day": "Samstag", "items": [{"time": "14:00", "text": "Antreten"}]}],
            "text": "",
        },
        {
            "key": "c:k",
            "kind": "callout",
            "title": "Wichtig",
            "text": "Halle zu",
            "style": "warning",
        },
        {
            "key": "c:a",
            "kind": "accordion",
            "title": "",
            "items": [{"title": "Schießordnung", "text": "§ 1 Ruhe"}],
        },
        {
            "key": "c:b",
            "kind": "images",
            "title": "Bilder",
            "items": [{"image": bild("fest1"), "caption": "Festzug"}],
            "columns": 4,
        },
        {
            "key": "c:d",
            "kind": "downloads",
            "title": "Downloads",
            "items": [
                {
                    "label": "Ordnung",
                    "url": fake.BASE + "files/ordnung12345/",
                    "file_type": "pdf",
                    "size": 51200,
                }
            ],
        },
    )
    html = text(client.get("/"))
    assert "Mach mit" in html and "<strong>dich</strong>" in html
    assert "Jetzt Mitglied werden</a>" in html
    assert "DE02 1203 0000 0000 2020 51" in html and "2.300 € von 5.000 € gesammelt" in html
    assert 'style="width:46%"' in html and "Jetzt spenden" in html
    assert "<dt>Dienstag</dt>" in html and "nur Luftgewehr" in html
    assert '<div class="spalten-paar">' in html and "<h3>Links</h3>" in html
    assert '<th scope="col">Beitrag</th>' in html and "<td>60 €</td>" in html
    assert '<span class="zeitstrahl-wann">1920</span>' in html
    assert "<h3>Samstag</h3>" in html and "<dt>14:00</dt>" in html
    assert 'class="hinweis-kasten hinweis-warning"' in html and "Achtung:" in html
    assert "<summary>Schießordnung</summary>" in html
    assert 'class="galerie-bilder bilder-spalten-4"' in html and "<figcaption" in html
    assert 'id="bild-fenster"' in html and "seite/bildfenster.js" in html
    assert 'href="/medien/a/files/ordnung12345/"' in html and "50,0" in html


def test_ohne_bilder_kein_bildfenster(client, hubiplan):
    hubiplan.info["home_layout"] = layout(
        {"key": "c:k", "kind": "callout", "title": "Info", "text": "", "style": "info"}
    )
    html = text(client.get("/"))
    assert 'id="bild-fenster"' not in html and 'class="hinweis-kasten hinweis-info"' in html
