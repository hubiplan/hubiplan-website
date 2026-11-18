"""UX-Audit 16.11., Reste der Vereinswebseite (WS-07, WS-11, WS-12, WS-14). Alle Daten erfunden."""

from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parents[1] / "seite" / "static" / "seite"
VORLAGEN = Path(__file__).resolve().parents[1] / "seite" / "templates" / "seite"


def text(response) -> str:
    return response.content.decode()


# --- WS-07: Rand klickbarer Karten ---


def test_klickbare_karten_mit_deutlichem_rand():
    css = (STATIC / "seite.css").read_text()
    assert (
        ".termin, .kacheln a, .dokumente a, .galerie-alben a "
        "{ --linie: color-mix(in srgb, var(--text) 55%, var(--flaeche)); }"
    ) in css


# --- WS-11: Sprache ---


def test_feste_texte_uebersetzbar():
    for name in ("personen.html", "ehrungen_karten.html"):
        assert 'alt="Foto von' not in (VORLAGEN / name).read_text()
    for name in ("einheiten.html", "einheit.html", "start/units.html"):
        assert 'default:"Einheiten"' not in (VORLAGEN / name).read_text()


def test_einheiten_englisch_ohne_eigene_bezeichnung(client, hubiplan):
    hubiplan.info["language"] = "en"
    hubiplan.info["unit_label_plural"] = ""
    hubiplan.info["blocks"]["units"] = True
    html = text(client.get("/einheiten/"))
    assert "<h1>Units</h1>" in html


def test_inhalt_in_anderer_sprache_ausgezeichnet(client, hubiplan):
    hubiplan.info["language"] = "en"
    hubiplan.info["content_language"] = "de"
    html = text(client.get("/"))
    assert '<html lang="en">' in html
    assert '<div class="text" lang="de">' in html


def test_inhalt_in_gleicher_sprache_ohne_lang(client, hubiplan):
    hubiplan.info["content_language"] = "de"
    html = text(client.get("/"))
    assert 'class="text" lang=' not in html


# --- WS-12: vereinsneutrale Adresse ---


def test_alte_adresse_leitet_weiter(client, hubiplan):
    r = client.get("/majestaeten/")
    assert r.status_code == 301 and r["Location"] == "/wuerden/"
    r = client.get("/majestaeten/hubertuskoenige/?x=1")
    assert r.status_code == 301 and r["Location"] == "/wuerden/hubertuskoenige/?x=1"


# --- WS-14 ---


def test_handymenue_gruppen_und_fokus():
    js = (STATIC / "menue.js").read_text()
    assert 'menue.addEventListener("focusout"' in js
    assert '<details class="menue-gruppe"' in (VORLAGEN / "kopf.html").read_text()


def test_grundschrift_in_rem():
    css = (STATIC / "seite.css").read_text() + (STATIC / "stil.css").read_text()
    assert "font: 17px/1.6" not in css
    for stufe in ("normal", "large", "xlarge"):
        assert f'html[data-st-size="{stufe}"] body {{ font-size: 1.0625rem; }}' in css


def test_hover_ohne_deckkraft():
    assert "a:hover { opacity: .8; }" not in (STATIC / "seite.css").read_text()


def test_qr_code_als_bild(client, hubiplan):
    html = text(client.get("/termine/"))
    if 'class="qr"' in html:
        assert 'class="qr" role="img"' in html


def test_ein_gemeinsames_terminfenster(client, hubiplan):
    html = text(client.get("/termine/"))
    assert 'class="termin-inhalt"' in html
    assert '<dialog id="termin-' not in html
    assert 'dialog.id = "termin-fenster"' in (STATIC / "termin.js").read_text()


@pytest.mark.parametrize(
    "datei,muster",
    [
        ("countdown.js", "prefers-reduced-motion: reduce"),
        ("bildfenster.js", 'bild.removeAttribute("src")'),
    ],
)
def test_kleinigkeiten_in_skripten(datei, muster):
    assert muster in (STATIC / datei).read_text()
