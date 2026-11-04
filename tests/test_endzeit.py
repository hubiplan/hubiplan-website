"""Endzeit pro Termin nur auf der Webseite ausblenden (erfundene Termine)."""

import datetime

import pytest
from django.utils import timezone

from . import fake


@pytest.mark.parametrize("path", ["/", "/termine/", "/zuege/jaeger/"])
@pytest.mark.parametrize("hide", [None, False, True])
def test_endzeit_in_karten_und_details(client, hubiplan, monkeypatch, path, hide):
    original = fake.events

    def events(future="2099-06-01T18:00:00+02:00"):
        data = original(future)
        if hide is not None:
            data["events"][0]["hide_end_time"] = hide
        return data

    monkeypatch.setattr(fake, "events", events)
    response = client.get(path)
    assert response.status_code == 200
    html = response.content.decode()
    assert "18:00 Uhr" in html
    assert ("bis 23:00 Uhr" in html) is (hide is not True)
    assert "Schützenfest" in html
    detail = html[html.index('<dialog id="termin-e1-') :]
    detail = detail[: detail.index("</dialog>")]
    assert "18:00 Uhr" in detail
    assert ("bis 23:00 Uhr" in detail) is (hide is not True)


@pytest.mark.parametrize("all_day", [False, True])
def test_mehrtaegige_termine_behalten_enddatum(client, hubiplan, monkeypatch, all_day):
    original = fake.events

    def events(future="2099-06-01T18:00:00+02:00"):
        data = original(future)
        data["events"][0].update(
            ends_at="2099-06-03T23:00:00+02:00", hide_end_time=True, all_day=all_day
        )
        return data

    monkeypatch.setattr(fake, "events", events)
    html = client.get("/termine/").content.decode()
    assert "bis Mittwoch, 3. Juni 2099" in html
    assert "23:00" not in html
    assert ("18:00 Uhr" in html) is (not all_day)


def test_laufender_termin_bleibt_sichtbar(client, hubiplan, monkeypatch):
    original = fake.events

    def events(future="2099-06-01T18:00:00+02:00"):
        data = original(future)
        data["events"][0]["hide_end_time"] = True
        return data

    monkeypatch.setattr(fake, "events", events)
    monkeypatch.setattr(
        timezone,
        "now",
        lambda: datetime.datetime(2099, 6, 1, 18, 30, tzinfo=timezone.get_current_timezone()),
    )
    html = client.get("/").content.decode()
    assert "Schützenfest" in html
    assert "bis 23:00 Uhr" not in html
