"""Barrierefreiheit 30.10.2026 (Bericht audit/barrierefreiheit-3010.md, W-01 bis W-09, X-02)."""

import re

import pytest
from django.core.cache import cache

from seite.farben import LINK_BACKGROUNDS, contrast, link_color

from .fake import KEY


def text(response) -> str:
    return response.content.decode()


@pytest.mark.parametrize("primary", ["#ffd700", "#e0a526", "#7fb3d5", "#00a0e0", "#1f4e2c"])
def test_linkfarbe_hat_genug_kontrast(primary):
    link = link_color(primary)
    assert all(contrast(link, bg) >= 4.5 for bg in LINK_BACKGROUNDS)


def test_dunkle_vereinsfarbe_bleibt():
    assert link_color("#1f4e2c") == "#1f4e2c"


def test_helle_vereinsfarbe_wird_fuer_links_abgedunkelt(client, hubiplan):
    hubiplan.info["theme"]["primary"] = "#e0a526"
    cache.clear()
    html = text(client.get("/"))
    assert "--primaer:#e0a526" in html
    link = re.search(r"--link:(#[0-9a-f]{6})", html).group(1)
    assert link != "#e0a526" and contrast(link, "#ffffff") >= 4.5


def test_erklaerung_zur_barrierefreiheit(client, hubiplan):
    r = client.get("/barrierefreiheit/")
    assert r.status_code == 200
    html = text(r)
    assert "<h1>Barrierefreiheit</h1>" in html
    assert 'href="/kontakt/"' in html
    # in der Fußzeile jeder Seite verlinkt
    assert 'href="/barrierefreiheit/">Barrierefreiheit</a>' in text(client.get("/"))


def test_erklaerung_auch_in_der_wartung(client, hubiplan):
    hubiplan.info["state"] = "maintenance"
    cache.clear()
    assert client.get("/barrierefreiheit/").status_code == 200


def test_kontaktformular_fehler_am_feld(client, hubiplan):
    html = text(client.get("/kontakt/"))
    assert "Alle Felder sind Pflicht" in html
    for feld in ("k-name", "k-mail", "k-betreff", "k-text"):
        assert f'id="{feld}" aria-describedby="{feld}-fehler"' in html
        assert f'id="{feld}-fehler" hidden' in html


def test_menue_ohne_irrefuehrende_beschriftung(client, hubiplan):
    html = text(client.get("/"))
    assert 'aria-label="Menü öffnen"' not in html
    assert "menue.js" in html


def test_karussell_steuerung_vor_den_bildern(client, hubiplan):
    bild = {
        "key": "festbild1",
        "url": f"https://hubiplan.example/api/public/site/v1/{KEY}/images/festbild1/",
        "small_url": "",
        "width": 800,
        "height": 400,
        "caption": "",
        "alt": "Festzug",
    }
    hubiplan.info["greeting"] = {
        "title": "Hallo",
        "text": "",
        "image": None,
        "gallery": [bild, bild],
    }
    html = text(client.get("/"))
    assert html.index("data-pause") < html.index("karussell-band")
    assert html.index("data-pause") < html.index("data-zurueck")


def test_neues_fenster_wird_angesagt(client, hubiplan):
    hubiplan.info["statute_url"] = "https://hubiplan.example/satzung/abc/"
    cache.clear()
    assert "öffnet in neuem Fenster" in text(client.get("/dokumente/"))
    assert "(öffnet in neuem Fenster)" in text(client.get("/"))
