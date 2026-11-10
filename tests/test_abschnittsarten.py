"""Neun weitere Arten eigener Abschnitte (Konzept webseite-baukasten, Ralf 10.11.2026):
häufige Fragen, Partner, Anfahrt, Termine einer Art, Dokument, Video als Link, Auszug aus der
Chronik, Zahlen und Trenner. Alle Daten erfunden."""

from . import fake
from .test_abschnitte import bild, layout, text


def _sections():
    return layout(
        {
            "key": "c:f",
            "kind": "faq",
            "title": "Häufige Fragen",
            "items": [{"question": "Wie werde ich Mitglied?", "answer": "Über das **Formular**."}],
        },
        {
            "key": "c:p",
            "kind": "partners",
            "title": "Unsere Partner",
            "items": [
                {
                    "name": "Bäckerei Muster",
                    "image": bild("baecker"),
                    "url": "https://example.org/b",
                },
                {"name": "Getränke Beispiel", "image": None, "url": "javascript:alert(1)"},
            ],
        },
        {
            "key": "c:a",
            "kind": "directions",
            "title": "Schützenhalle",
            "name": "Schützenhalle",
            "address": "Musterweg 1\n12345 Musterdorf",
            "directions": "",
            "text": "Eingang links.",
            "route_url": "https://www.openstreetmap.org/directions?to=51.0,6.0",
        },
        {
            "key": "c:t",
            "kind": "event_list",
            "title": "Training",
            "events": [
                {"id": 1, "title": "Training am Stand", "starts_at": "2099-03-01T19:00:00+01:00"},
            ],
        },
        {
            "key": "c:d",
            "kind": "document",
            "title": "",
            "label": "Aufnahmeantrag",
            "url": fake.BASE + "files/antrag12345678/",
            "file_type": "pdf",
        },
        {
            "key": "c:v",
            "kind": "video",
            "title": "Festzug 2099",
            "url": "https://video.example.org/festzug",
            "image": bild("festzug"),
            "text": "",
        },
        {
            "key": "c:c",
            "kind": "chronicle",
            "title": "",
            "entries": [{"year": 1920, "until": None, "title": "Gründung", "text": "Im Saal."}],
        },
        {
            "key": "c:z",
            "kind": "facts",
            "title": "",
            "items": [{"value": "1920", "label": "gegründet"}, {"value": "6", "label": "Züge"}],
        },
        {"key": "c:x", "kind": "divider", "style": "line", "size": "large"},
    )


def test_neue_arten_auf_der_startseite(client, hubiplan):
    hubiplan.info["home_layout"] = _sections()
    html = text(client.get("/"))
    assert (
        '<details class="frage">' in html and "<summary>Wie werde ich Mitglied?</summary>" in html
    )
    assert "<strong>Formular</strong>" in html
    assert 'href="https://example.org/b"' in html and 'alt="Bäckerei Muster"' in html
    # Kein javascript:-Link, der Name bleibt stehen
    assert "javascript:" not in html and "Getränke Beispiel" in html
    assert "Musterweg 1<br>12345 Musterdorf" in html
    assert 'href="https://www.openstreetmap.org/directions?to=51.0,6.0"' in html
    assert "Route planen" in html
    assert "Training am Stand" in html
    assert 'href="/medien/a/files/antrag12345678/"' in html and "Aufnahmeantrag" in html
    assert 'href="https://video.example.org/festzug"' in html and "Video ansehen" in html
    assert "Gründung" in html and 'href="/chronik/"' in html
    assert '<span class="zahl">1920</span>' in html
    assert 'class="trenner-line trenner-large"' in html
    # Links nach außen öffnen in einem neuen Fenster und sagen es
    assert html.count('target="_blank" rel="noopener noreferrer"') >= 3


def test_ohne_termine_kein_abschnitt(client, hubiplan):
    hubiplan.info["home_layout"] = layout(
        {"key": "c:t", "kind": "event_list", "title": "Training", "events": []},
        {"key": "c:v", "kind": "video", "title": "Kaputt", "url": "javascript:alert(1)"},
    )
    html = text(client.get("/"))
    assert "terminliste" not in html and "Kaputt" not in html


def test_auch_auf_textseiten(client, hubiplan):
    hubiplan.antworten["pages/anfahrt/"] = {
        "slug": "anfahrt",
        "title": "Anfahrt",
        "text": "Mit dem Bus.",
        "image": None,
        "sections": layout(
            {"key": "body", "kind": "body"},
            {
                "key": "c:f",
                "kind": "faq",
                "title": "",
                "items": [{"question": "Gibt es Parkplätze?", "answer": "Ja."}],
            },
        ),
    }
    html = text(client.get("/seite/anfahrt/"))
    assert "<summary>Gibt es Parkplätze?</summary>" in html
