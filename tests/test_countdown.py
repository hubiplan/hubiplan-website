"""Abschnittsart „Countdown“ (HUBIplan ab 14.11.2026): laufender Zähler bis zu einem Ziel,
danach ausblenden oder Text zeigen. Alle Daten erfunden."""

import datetime

from django.utils import timezone

from .test_abschnitte import layout, text


def test_countdown_zaehler_und_ziel(client, hubiplan):
    ziel = timezone.now() + datetime.timedelta(days=3, hours=4, minutes=5, seconds=30)
    hubiplan.info["home_layout"] = layout(
        {
            "key": "c:c1",
            "kind": "countdown",
            "title": "Bis zum Schützenfest",
            "target": ziel.isoformat(),
            "name": "Schützenfest",
            "text": "Wir freuen uns auf euch!",
            "after_text": "Es geht los!",
        },
        {"key": "c:c2", "kind": "countdown", "title": "Ohne Ziel", "target": "", "after_text": ""},
        {"key": "c:c3", "kind": "countdown", "title": "Kaputt", "target": "morgen"},
    )
    html = text(client.get("/"))
    assert '<section class="countdown-abschnitt" data-countdown>' in html
    assert f'data-ziel="{ziel.isoformat()}"' in html
    assert '<span class="countdown-zahl" data-teil="tage">3</span>' in html
    assert '<span class="countdown-zahl" data-teil="stunden">4</span>' in html
    assert 'data-ein="Tag" data-mehr="Tage">Tage</span>' in html
    assert "Bis zum Schützenfest" in html and "Schützenfest ·" in html
    assert "Wir freuen uns auf euch!" in html
    assert '<p class="countdown-danach" hidden>Es geht los!</p>' in html
    assert "Ohne Ziel" not in html and "Kaputt" not in html
    assert "seite/countdown.js" in html


def test_countdown_nach_ablauf(client, hubiplan):
    vorbei = (timezone.now() - datetime.timedelta(minutes=1)).isoformat()
    hubiplan.info["home_layout"] = layout(
        {
            "key": "c:c1",
            "kind": "countdown",
            "title": "Schon vorbei",
            "target": vorbei,
            "after_text": "",
        },
        {
            "key": "c:c2",
            "kind": "countdown",
            "title": "Fest",
            "target": "",
            "after_text": "Das Schützenfest hat begonnen!",
        },
    )
    html = text(client.get("/"))
    assert "Schon vorbei" not in html
    assert '<p class="countdown-danach">Das Schützenfest hat begonnen!</p>' in html
    assert "countdown-zaehler" not in html
