"""Webseite #75: Lupe ausgerichtet, Lage der Suche, Menüpunkte im Fuß, „Start“ ausblendbar.
Alle Daten erfunden."""

import re
from pathlib import Path

from django.core.cache import cache

STATIC = Path(__file__).resolve().parents[1] / "seite" / "static" / "seite"


def seite(client, pfad="/") -> str:
    cache.clear()
    return client.get(pfad).content.decode()


def breit(html: str) -> str:
    return re.search(r'<nav class="menue-breit".*?</nav>', html, re.S).group(0)


def handy(html: str) -> str:
    return re.search(r'<details class="menue">.*?</details>', html, re.S).group(0)


def fuss(html: str) -> str:
    return re.search(r'<footer class="fuss">.*?</footer>', html, re.S).group(0)


def _menue(hubiplan, kontakt_platz=None):
    kontakt = {"key": "contact", "label": "Kontakt"}
    if kontakt_platz:
        kontakt["place"] = kontakt_platz
    hubiplan.info["nav"] = [{"key": "events", "label": "Termine"}, kontakt]
    hubiplan.info["blocks"] = {**hubiplan.info["blocks"], "search": True}


def test_lupe_hat_die_zeilenhoehe_der_textpunkte():
    css = (STATIC / "seite.css").read_text()
    assert re.search(r"\.suche-punkt a::before[^{]*\{[^}]*content: \"\\200b\"", css)


def test_suche_wie_bisher_in_der_menueleiste(client, hubiplan):
    _menue(hubiplan)
    html = seite(client)
    assert 'class="suche-punkt"' in breit(html)
    assert "kopf-suche" not in html and "fuss-suche" not in html
    assert "/suche/" in handy(html)


def test_suche_oben_rechts_im_kopf(client, hubiplan):
    _menue(hubiplan)
    hubiplan.info["style"] = {"search": "header"}
    html = seite(client)
    assert "suche-punkt" not in breit(html)
    assert re.search(r'<div class="kopf-sozial"><a class="kopf-suche" href="/suche/"', html)
    # Handy: weiter im Aufklappmenü
    assert "/suche/" in handy(html)


def test_suche_im_fuss(client, hubiplan):
    _menue(hubiplan)
    hubiplan.info["style"] = {"search": "footer"}
    html = seite(client)
    assert "suche-punkt" not in breit(html) and "kopf-suche" not in html
    assert "/suche/" not in handy(html)
    assert re.search(
        r'<form class="fuss-suche" action="/suche/" method="get" role="search">', fuss(html)
    )


def test_ohne_baustein_keine_suche(client, hubiplan):
    _menue(hubiplan)
    hubiplan.info["blocks"]["search"] = False
    for lage in ("nav", "header", "footer"):
        hubiplan.info["style"] = {"search": lage}
        html = seite(client)
        assert "/suche/" not in html, lage


def test_kontakt_nur_im_fuss(client, hubiplan):
    _menue(hubiplan, "footer")
    html = seite(client)
    assert "/kontakt/" not in breit(html) and "/kontakt/" not in handy(html)
    recht = re.search(r'<ul class="recht">.*?</ul>', fuss(html), re.S).group(0)
    assert recht.index("Kontakt") < recht.index("Impressum")
    assert client.get("/kontakt/").status_code == 200


def test_kontakt_im_menue_und_im_fuss(client, hubiplan):
    _menue(hubiplan, "both")
    html = seite(client)
    assert "/kontakt/" in breit(html) and "/kontakt/" in handy(html)
    assert "/kontakt/" in fuss(html)


def test_ohne_platz_nicht_im_fuss(client, hubiplan):
    _menue(hubiplan)
    html = seite(client)
    assert "/kontakt/" not in fuss(html)


def test_unbekannter_platz_bleibt_im_menue(client, hubiplan):
    _menue(hubiplan, "irgendwo")
    html = seite(client)
    assert "/kontakt/" in breit(html) and "/kontakt/" not in fuss(html)


def test_start_am_bildschirm_ausblendbar(client, hubiplan):
    _menue(hubiplan)
    html = seite(client, "/termine/")
    assert ">Start<" in breit(html)
    hubiplan.info["style"] = {"nav_start": False}
    html = seite(client, "/termine/")
    assert ">Start<" not in breit(html)
    assert ">Start<" in handy(html)


def test_marke_fuehrt_hoerbar_zur_startseite(client, hubiplan):
    html = seite(client)
    marke = re.search(r'<a class="marke[^"]*" href="/">.*?</a>', html, re.S).group(0)
    assert "zur Startseite" in marke and "nur-vorlesen" in marke
