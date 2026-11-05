"""Belegung von Schützenhaus und Stand auf der Webseite (erfunden)."""

import pytest


def text(response) -> str:
    return response.content.decode()


@pytest.fixture
def belegung(hubiplan):
    hubiplan.info["blocks"]["bookings"] = True
    hubiplan.info["nav"] = [{"key": "bookings", "label": "Belegung"}]
    hubiplan.antworten = {
        "bookings/?start=2026-11-02": {
            "start": "2026-11-02",
            "end": "2026-11-09",
            "items": [{"id": "abc123", "title": "Schützenhaus", "kind": "facility", "area": False}],
            "occurrences": [
                {
                    "item": "abc123",
                    "title": "Seniorennachmittag",
                    "starts_at": "2026-11-04T13:00:00Z",
                    "ends_at": "2026-11-04T15:00:00Z",
                    "all_day": False,
                },
                {
                    "item": "abc123",
                    "title": "Belegt",
                    "starts_at": "2026-11-06T17:00:00Z",
                    "ends_at": "2026-11-06T21:00:00Z",
                    "all_day": False,
                },
            ],
            "ics_url": "https://verein.example.org/api/public/site/v1/k/bookings.ics",
        }
    }
    return hubiplan


def test_wochenansicht(client, belegung):
    html = text(client.get("/belegung/?ab=2026-11-04"))
    assert "Seniorennachmittag" in html
    assert "14:00–16:00" in html
    assert "Belegt" in html
    assert "webcal://verein.example.org/" in html
    assert 'href="?ab=2026-10-26"' in html and 'href="?ab=2026-11-09"' in html
    assert 'href="/belegung/"' in text(client.get("/"))


def test_ohne_baustein_nicht_da(client, belegung):
    belegung.info["blocks"]["bookings"] = False
    assert client.get("/belegung/").status_code == 404
