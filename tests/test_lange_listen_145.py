"""Webseite #145 (Ralf 16.11.2026): lange, schmale Tabellen am Bildschirm zweispaltig
(long_tables=columns). Alle Daten erfunden."""

import re
from pathlib import Path
from types import SimpleNamespace

from django.core.cache import cache

from seite import stil
from seite.templatetags.seite import ZWEISPALTIG_AB, rolle, zweispaltig

from .fake import HONORS

STATIC = Path(__file__).resolve().parents[1] / "seite" / "static" / "seite"


def _site(**style):
    return SimpleNamespace(style=style)


def _koenige(n: int) -> list[dict]:
    return [
        {
            "year": 2026 - i,
            "period": str(2026 - i),
            "holder": {"name": f"König Muster {i + 1}"},
            "companions": [],
            "note": "",
            "photo_url": None,
            "times": 1,
        }
        for i in range(n)
    ]


def test_regler_im_katalog():
    assert stil.CATALOG["long_tables"] == ("rows", "columns")
    assert stil.clean({"long_tables": "columns"}, "classic") == {"long_tables": "columns"}
    assert stil.clean({"long_tables": "quer"}, "classic") == {}


def test_nur_mit_regler_lang_und_schmal():
    zeilen = list(range(ZWEISPALTIG_AB))
    assert zweispaltig(_site(), zeilen) == 0
    assert zweispaltig(_site(long_tables="rows"), zeilen) == 0
    assert zweispaltig(_site(long_tables="columns"), zeilen) == 10
    # kürzere Listen und breite Tabellen bleiben einspaltig
    assert zweispaltig(_site(long_tables="columns"), zeilen[:-1]) == 0
    assert zweispaltig(_site(long_tables="columns"), zeilen, 3) == 0
    assert zweispaltig(None, zeilen) == 0


def test_ungerade_zeilen_links_eine_mehr():
    assert zweispaltig(_site(long_tables="columns"), list(range(93))) == 47
    assert zweispaltig(_site(long_tables="columns"), list(range(21))) == 11


def test_rollen_nur_bei_zwei_spalten():
    assert rolle(0, "cell") == ""
    assert rolle(11, "cell") == ' role="cell"'


def _seite(client, hubiplan, monkeypatch, style, n):
    monkeypatch.setitem(HONORS["dignities"][0], "reigns", _koenige(n))
    hubiplan.info["style"] = style
    cache.clear()
    return client.get("/wuerden/").content.decode()


def test_ohne_regler_wie_bisher(client, hubiplan, monkeypatch):
    html = _seite(client, hubiplan, monkeypatch, {}, 93)
    assert '<table class="zeitliste">' in html
    assert "zweispaltig" not in html
    assert "kopf-rechts" not in html


def test_kurze_liste_bleibt_einspaltig(client, hubiplan, monkeypatch):
    html = _seite(client, hubiplan, monkeypatch, {"long_tables": "columns"}, 19)
    assert '<table class="zeitliste">' in html
    assert "zeitliste-spalten" not in html


def test_lange_liste_zweispaltig(client, hubiplan, monkeypatch):
    html = _seite(client, hubiplan, monkeypatch, {"long_tables": "columns"}, 93)
    assert 'data-st-long-tables="columns"' in html
    assert '<div class="zeitliste-spalten">' in html
    assert '<table class="zeitliste zweispaltig" role="table" style="--zeilen: 47">' in html
    # eine Tabelle, Zeilen in Lesereihenfolge; zweite Kopfzeile nur fürs Auge
    tabelle = html.split('<table class="zeitliste zweispaltig"', 1)[1].split("</table>", 1)[0]
    namen = re.findall(r"König Muster (\d+)<", tabelle)
    assert namen == [str(i) for i in range(1, 94)]
    assert '<tr class="kopf-rechts" aria-hidden="true"><th>Jahr</th><th>König</th></tr>' in tabelle
    assert tabelle.count('role="row"') == 94
    assert tabelle.count('role="columnheader"') == 2


def test_regeln_im_stil():
    css = (STATIC / "stil.css").read_text()
    assert ".zeitliste-spalten { container-type: inline-size; }" in css
    assert "@container (min-width: 800px)" in css
    assert "grid-template-rows: repeat(var(--zeilen), auto); grid-auto-flow: column;" in css
    assert "column-gap: 48px" in css
    assert "table.zweispaltig > thead > tr.kopf-rechts { display: none; }" in css
