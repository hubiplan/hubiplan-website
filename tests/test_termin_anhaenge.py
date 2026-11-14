"""Freigegebene Anhänge öffentlicher Termine im Termin-Fenster (erfundene Daten)."""

from seite import api

from . import fake

PDF = b"%PDF-1.4\n%erfunden\n"


def test_anhang_im_fenster_und_ausgeliefert(client, hubiplan, monkeypatch):
    original = fake.events

    def events(future="2099-06-01T18:00:00+02:00"):
        data = original(future)
        data["events"][0]["attachments"] = [
            {"name": "Ablaufplan", "kind": "pdf", "url": fake.BASE + "events/attachments/7/"}
        ]
        return data

    monkeypatch.setattr(fake, "events", events)
    hubiplan.antworten["events/attachments/7/"] = api.Response(200, PDF, "application/pdf")
    html = client.get("/termine/").content.decode()
    detail = html[html.index('<dialog id="termin-e1-') :]
    detail = detail[: detail.index("</dialog>")]
    assert "Unterlagen:" in detail
    assert 'href="/medien/a/events/attachments/7/"' in detail and "Ablaufplan" in detail
    pdf = client.get("/medien/a/events/attachments/7/")
    assert pdf.status_code == 200 and pdf["Content-Type"] == "application/pdf"
    assert pdf["Content-Disposition"] == "inline"
    # Chrome/Edge blockieren PDFs mit CSP-sandbox (ERR_BLOCKED_BY_CLIENT)
    assert "sandbox" not in pdf["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in pdf["Content-Security-Policy"]


def test_ohne_anhaenge_kein_abschnitt(client, hubiplan):
    html = client.get("/termine/").content.decode()
    assert "Unterlagen:" not in html


def test_fremde_pfade_bleiben_gesperrt(client, hubiplan):
    assert client.get("/medien/a/events/attachments/x7/").status_code == 404
    assert client.get("/medien/a/events/7/").status_code == 404
