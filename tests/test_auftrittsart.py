"""Auftrittsart beim Termin (HUBIplan Issue #713, erfundene Termine)."""

from . import fake


def test_auftrittsart_in_karte_und_fenster(client, hubiplan, monkeypatch):
    original = fake.events

    def events(future="2099-06-01T18:00:00+02:00"):
        data = original(future)
        data["events"][0]["performance_kind"] = "Zapfenstreich"
        return data

    monkeypatch.setattr(fake, "events", events)
    html = client.get("/termine/").content.decode()
    card = html[: html.index('<template id="termin-e1-')]
    assert "· Zapfenstreich" in card
    detail = html[html.index('<template id="termin-e1-') :]
    detail = detail[: detail.index("</template>")]
    assert "· Zapfenstreich" in detail


def test_ohne_auftrittsart_kein_zusatz(client, hubiplan):
    html = client.get("/termine/").content.decode()
    assert "Zapfenstreich" not in html
