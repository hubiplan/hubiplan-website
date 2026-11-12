"""Seite „Mitglied werden“: zeigt Arten und Beitrag und verlinkt den Online-Antrag in HUBIplan.
Die Webseite nimmt selbst keine Angaben an. Alle Daten erfunden."""

import pytest
from django.core.cache import cache


def text(response) -> str:
    return response.content.decode()


ANTRAG = "https://verein.example.org/mitglied-werden/abc123"


@pytest.fixture
def beitritt(hubiplan):
    hubiplan.info["blocks"]["join"] = True
    hubiplan.info["nav"] = [{"key": "join", "label": "Mitglied werden", "button": True}]
    hubiplan.antworten = {
        "join/": {
            "intro": "Wir freuen uns auf dich.\nDas Training ist dienstags.",
            "types": [
                {"id": 1, "label": "Aktiv", "text": "mit Schießtraining", "fee": "36,00"},
                {"id": 2, "label": "Fördernd", "text": "", "fee": None},
            ],
            "units": [{"id": 7, "name": "Jägerzug Musterdorf"}],
            "sepa": "offer",
            "form_url": ANTRAG,
        }
    }
    return hubiplan


def test_seite_mit_arten_und_link(client, beitritt):
    html = text(client.get("/mitglied-werden/"))
    assert "<h1>Mitglied werden</h1>" in html
    assert "Wir freuen uns auf dich." in html
    assert "<strong>Aktiv</strong> · 36,00 € im Jahr" in html
    assert "Fördernd" in html
    assert f'href="{ANTRAG}"' in html
    assert f'href="{ANTRAG}?einheit=7"' in html
    assert "Lastschrift" in html
    # keine Eingabefelder auf der Webseite
    assert "<input" not in html.split("<main", 1)[-1].split("</main>", 1)[0]


def test_menue_verlinkt_die_seite(client, beitritt):
    assert 'href="/mitglied-werden/"' in text(client.get("/"))


def test_ohne_baustein_nicht_da(client, beitritt):
    beitritt.info["blocks"]["join"] = False
    cache.clear()
    assert client.get("/mitglied-werden/").status_code == 404


def test_nur_sichere_formularadresse(client, beitritt):
    beitritt.antworten["join/"]["form_url"] = "javascript:alert(1)"
    assert client.get("/mitglied-werden/").status_code == 404


def test_englisch(client, beitritt):
    beitritt.info["language"] = "en"
    html = text(client.get("/mitglied-werden/"))
    assert "Become a member" in html or "Mitglied werden" in html
    assert "To the membership application" in html
