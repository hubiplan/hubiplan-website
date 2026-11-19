"""Öffentliche Anmeldung am Termin (HUBIplan A4): Stand, Preise, Plätze und Knopf zum
Formular im Terminfenster (erfundene Daten)."""

from . import fake

ANMELDUNG = {
    "state": "open",
    "state_text": "",
    "opens_at": None,
    "closes_at": "2099-05-20T21:59:00+00:00",
    "closes_text": "",
    "free": 12,
    "waitlist": True,
    "prices": [
        {
            "name": "Erwachsene",
            "name_en": "Adults",
            "amount": "25.00",
            "step": "Frühbucher",
            "until_date": "2099-04-30",
        },
        {"name": "Kinder", "name_en": "", "amount": "0.00", "step": "", "until_date": None},
    ],
    "url": "https://verein.example.org/anmeldung/abc123",
    "can_join": True,
}


def _mit_anmeldung(monkeypatch, **extra):
    original = fake.events

    def events(future="2099-06-01T18:00:00+02:00"):
        data = original(future)
        data["events"][0]["registration"] = {**ANMELDUNG, **extra}
        data["events"][0]["programme"] = "14:00 Begrüßung\n15:00 Kaffee"
        return data

    monkeypatch.setattr(fake, "events", events)


def _fenster(html: str) -> str:
    detail = html[html.index('<template id="termin-e1-') :]
    return detail[: detail.index("</template>")]


def test_anmeldung_im_fenster(client, hubiplan, monkeypatch):
    _mit_anmeldung(monkeypatch)
    html = client.get("/termine/").content.decode()
    assert "Anmeldung möglich" in html  # Hinweis auf der Karte
    detail = _fenster(html)
    assert "möglich bis" in detail and "noch 12 Plätze frei" in detail
    assert "Erwachsene: 25,00 €" in detail and "bis 30.4.2099" in detail
    assert "Kinder: kostenlos" in detail
    assert 'href="https://verein.example.org/anmeldung/abc123"' in detail
    assert "Jetzt anmelden" in detail
    assert "Programm:" in detail and "15:00 Kaffee" in detail


def test_voll_mit_warteliste(client, hubiplan, monkeypatch):
    _mit_anmeldung(monkeypatch, state="full", free=0)
    detail = _fenster(client.get("/termine/").content.decode())
    assert "Auf die Warteliste" in detail and "Jetzt anmelden" not in detail


def test_geschlossen_ohne_knopf(client, hubiplan, monkeypatch):
    _mit_anmeldung(monkeypatch, state="closed", can_join=False)
    html = client.get("/termine/").content.decode()
    detail = _fenster(html)
    assert "geschlossen" in detail and "/anmeldung/abc123" not in detail
    assert "Anmeldung möglich" not in html


def test_fremder_link_wird_nicht_gezeigt(client, hubiplan, monkeypatch):
    _mit_anmeldung(monkeypatch, url="javascript:alert(1)")
    html = client.get("/termine/").content.decode()
    assert "javascript:" not in html and "Anmeldung:" not in html


def test_ohne_anmeldung_wie_bisher(client, hubiplan):
    html = client.get("/termine/").content.decode()
    assert "Anmeldung:" not in html and "Jetzt anmelden" not in html


def test_englisch(client, hubiplan, monkeypatch):
    _mit_anmeldung(monkeypatch)
    hubiplan.info["language"] = "en"
    detail = _fenster(client.get("/termine/").content.decode())
    assert "Adults: €25.00" in detail and "Kinder: free" in detail
    assert "12 places left" in detail and "Register now" in detail


SEITE = {
    "slug": "sommerfest-2099",
    "title": "Sommerfest 2099",
    "text": "Alle sind eingeladen.",
    "image": None,
    "sections": [],
    "event": {
        "title": "Sommerfest",
        "starts_at": "2099-06-13T14:00:00+02:00",
        "ends_at": "2099-06-13T22:00:00+02:00",
        "all_day": False,
        "hide_end_time": False,
        "is_cancelled": False,
        "location": "Festwiese",
        "address": "Musterweg 1, 12345 Musterstadt",
        "directions": "Parken am Sportplatz",
        "description": "Mit Musik und Kuchen.",
        "programme": "14:00 Begrüßung",
        "attachments": [],
        "registration": {
            **ANMELDUNG,
            "terms": "Abmeldung nur schriftlich.",
            "cancel_text": "Bis 1. Juni kostenfrei.",
        },
        "ended": False,
    },
}


def test_veranstaltungsseite(client, hubiplan):
    hubiplan.antworten["pages/sommerfest-2099/"] = SEITE
    html = client.get("/veranstaltung/sommerfest-2099/").content.decode()
    assert "<h1>Sommerfest 2099</h1>" in html and "Alle sind eingeladen." in html
    assert "Festwiese" in html and "Parken am Sportplatz" in html
    assert "14:00 Begrüßung" in html and "Erwachsene: 25,00 €" in html
    assert 'href="https://verein.example.org/anmeldung/abc123"' in html
    assert "Teilnahmebedingungen" in html and "Abmeldung nur schriftlich." in html
    assert "Bis 1. Juni kostenfrei." in html
    # Eine Adresse je Seite
    alt = client.get("/seite/sommerfest-2099/")
    assert alt.status_code == 302 and alt["Location"] == "/veranstaltung/sommerfest-2099/"
    assert client.get("/veranstaltung/anfahrt/").status_code == 404


def test_termin_verweist_auf_veranstaltungsseite(client, hubiplan, monkeypatch):
    _mit_anmeldung(monkeypatch)
    original = fake.events

    def events(future="2099-06-01T18:00:00+02:00"):
        data = original(future)
        data["events"][0]["page"] = "sommerfest-2099"
        data["events"][1]["page"] = "../boese"
        return data

    monkeypatch.setattr(fake, "events", events)
    html = client.get("/termine/").content.decode()
    assert 'href="/veranstaltung/sommerfest-2099/"' in _fenster(html)
    assert "boese" not in html


def test_menuepunkt_der_veranstaltungsseite(client, hubiplan):
    hubiplan.antworten["pages/sommerfest-2099/"] = SEITE
    hubiplan.info["nav"] = [
        {"key": "page", "label": "Sommerfest", "slug": "sommerfest-2099", "event": True}
    ]
    html = client.get("/").content.decode()
    assert 'href="/veranstaltung/sommerfest-2099/"' in html


def test_hervorgehobener_termin_mit_anmeldung(client, hubiplan):
    import datetime

    from django.utils import timezone

    from .test_abschnitte import layout, text

    start = timezone.localtime() + datetime.timedelta(days=5)
    hubiplan.info["home_layout"] = layout(
        {
            "key": "c:e1",
            "kind": "event",
            "title": "Bald ist Sommerfest",
            "event": {
                "id": "e9",
                "title": "Sommerfest",
                "starts_at": start.isoformat(),
                "ends_at": (start + datetime.timedelta(hours=3)).isoformat(),
                "all_day": False,
                "location": "Festwiese",
                "is_cancelled": False,
                "registration": ANMELDUNG,
                "page": "sommerfest-2099",
            },
        },
    )
    html = text(client.get("/"))
    assert "Jetzt anmelden" in html and "Erwachsene: 25,00 €" in html
    assert 'href="/veranstaltung/sommerfest-2099/"' in html
