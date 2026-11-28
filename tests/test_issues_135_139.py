"""Webseite #135–#139 (Ralf 16.11.2026): Würdenträger als Band, Personenkarten ohne
Platzhalter, Kontakt mit Du und Kasten, Chronik-Band, Podium in den Ergebnissen.
Alle Daten erfunden."""

from pathlib import Path

from django.core.cache import cache

from seite import markdown, stil

from .fake import BASE, COMP

STATIC = Path(__file__).resolve().parents[1] / "seite" / "static" / "seite"


def text(response) -> str:
    return response.content.decode()


def hole(client, pfad: str) -> str:
    cache.clear()
    return text(client.get(pfad))


def test_neue_regler_im_katalog():
    assert stil.CATALOG["honors_layout"] == ("list", "band")
    assert stil.CATALOG["portrait_placeholder"] == ("initial", "none")
    assert stil.CATALOG["person_cards"] == ("normal", "label")
    assert stil.CATALOG["address"] == ("formal", "informal")
    assert stil.CATALOG["timeline_chapter"] == ("plain", "band", "slim")
    assert stil.CATALOG["ranking"] == ("table", "podium")


# --- #135 Würdenträger ---


def test_wuerdentraeger_ohne_regler_wie_bisher(client, hubiplan):
    html = hole(client, "/wuerden/")
    assert "majestaet-band" not in html
    assert '<div class="majestaet">' in html
    assert '<details class="chronik">' in html


def test_wuerdentraeger_als_band(client, hubiplan):
    hubiplan.info["style"] = {"honors_layout": "band"}
    html = hole(client, "/wuerden/")
    assert 'data-st-honors-layout="band"' in html
    assert '<div class="majestaet-band ohne-bild">' in html
    assert '<p class="majestaet-oberzeile">König</p>' in html
    assert '<p class="majestaet-name">Karl Krone' in html
    # Vorgänger als Karten ohne den Amtierenden, darunter die ganze Liste aufklappbar
    vorher = html[html.index('<ul class="vorgaenger">') :]
    vorher = vorher[: vorher.index("</ul>")]
    assert "Otto Ober" in vorher and "Karl Krone" not in vorher
    assert '<summary class="knopf">Alle 2 Einträge (Könige)</summary>' in html
    assert '<table class="zeitliste">' in html


def test_vorgaenger_hoechstens_acht():
    from seite.hilfen.anzeige import vorgaenger

    d = {
        "current": [{"year": 2026, "period": "2026", "holder": {"name": "Neu"}}],
        "reigns": [
            {"year": 2026 - i, "period": str(2026 - i), "holder": {"name": f"P{i}"}}
            for i in range(12)
        ],
    }
    d["reigns"][0]["holder"]["name"] = "Neu"
    namen = [r["holder"]["name"] for r in vorgaenger(d)]
    assert namen == [f"P{i}" for i in range(1, 9)]


# --- #136 Personenkarten ---


def test_platzhalter_ohne_foto_abschaltbar(client, hubiplan):
    assert 'class="ohne-foto"' in hole(client, "/vorstand/")
    hubiplan.info["style"] = {"portrait_placeholder": "none", "person_cards": "label"}
    html = hole(client, "/vorstand/")
    assert 'class="ohne-foto"' not in html
    # Fotos bleiben
    assert 'alt="Foto von Max Muster"' in html
    assert 'data-st-person-cards="label"' in html
    assert '<section class="karte personenkarte">' in html
    assert '<section class="karte personenkarte ehrung">' in html
    assert '<p class="nachricht"><a class="knopf klein-knopf"' in html


def test_personenkarten_regeln():
    css = (STATIC / "stil.css").read_text()
    karte = 'html[data-st-person-cards="label"] .karte.personenkarte {'
    assert karte + " padding: 20px 22px 22px; border-top: 3px solid var(--primaer); }" in css
    assert "letter-spacing: .18em; text-transform: uppercase; color: var(--st-kasten)" in css
    assert ".ehrung .personen { grid-template-columns: repeat(3, minmax(0, 1fr));" in css


# --- #137 Kontakt ---


def test_kontakt_sie_wie_bisher(client, hubiplan):
    html = hole(client, "/kontakt/")
    assert "Ihr Name" in html and 'data-anrede="sie"' in html
    # Ohne eigenen Kasten stehen seit dem UX-Audit 16.11. (WS-13) die Vereinsdaten daneben
    assert "kontakt-angaben" in html and "kontakt-kasten-titel" not in html


def test_kontakt_duzt(client, hubiplan):
    hubiplan.info["style"] = {"address": "informal"}
    html = hole(client, "/kontakt/")
    assert 'data-anrede="du"' in html
    assert "Dein Name" in html and "Deine E-Mail-Adresse" in html
    assert "Schreib uns. Die Nachricht geht per E-Mail an" in html
    assert "die Antwort kommt an deine E-Mail-Adresse." in html
    assert "Ihr Name" not in html and "Schreiben Sie" not in html
    js = (STATIC / "kontakt.js").read_text()
    assert '"Danke! Ihre Nachricht ist angekommen.": "Danke! Deine Nachricht ist angekommen."' in js


def test_kontakt_mit_kasten(client, hubiplan):
    hubiplan.info["intros"] = {
        "contact": {
            "title": "Du möchtest mitmachen?",
            "text": "Wir freuen uns über neue Gesichter.\n\n[Mitmachen](seite:seite/mitmachen)",
            "image": None,
        }
    }
    html = hole(client, "/kontakt/")
    assert '<div class="kontakt-spalten"><div class="kontakt-haupt">' in html
    assert '<h2 id="kontakt-kasten-titel">Du möchtest mitmachen?</h2>' in html
    knopf = '<a class="knopf" href="/seite/mitmachen/">Mitmachen</a>'
    assert f'<p class="kasten-knopf">{knopf}</p>' in html
    # Formular steht vor dem Kasten
    assert html.index('id="kontakt"') < html.index("kontakt-kasten")


def test_letzter_link_nur_allein_als_knopf():
    html = markdown.render("Text mit [Link](https://example.org) mitten drin.")
    assert markdown.last_link_as_button(html) == html
    html = markdown.render("Text\n\n[Los](https://example.org)")
    assert 'class="knopf"' in markdown.last_link_as_button(html)


def test_kontakt_felder_eckig():
    css = (STATIC / "stil.css").read_text()
    regel = 'html[data-st-corners="square"] .formular :is(input, select, textarea)'
    assert regel + " { border-radius: 0; }" in css


# --- #138 Chronik ---


def test_chronik_band_regeln():
    css = (STATIC / "stil.css").read_text()
    band = 'html:is([data-st-timeline-chapter="band"], [data-st-timeline-chapter="slim"])'
    assert band + " .zeitleiste-kapitelkopf {" in css
    assert "font-family: var(--schrift-titel); font-size: 64px;" in css
    assert "border-bottom: 2px solid var(--farbe-zier); border-radius: 0;" in css
    eckig = ":is(.zeitleiste-bild, .zeitleiste-karte, .zeitleiste-bild img)"
    assert 'html[data-st-corners="square"] ' + eckig in css


# --- #139 Ergebnisse ---


def test_podium(client, hubiplan):
    hubiplan.info["results_url"] = BASE + "results/"
    html = hole(client, f"/ergebnisse/{COMP}/")
    assert '<ul class="podest">' not in html
    hubiplan.info["style"] = {"ranking": "podium"}
    html = hole(client, f"/ergebnisse/{COMP}/")
    assert '<ul class="podest">' in html
    assert '<li class="podest-karte platz-1">' in html
    assert '<span class="podest-ziffer"><span class="unsichtbar">Platz </span>1</span>' in html


def test_podest_filter_gleichstand():
    from seite.hilfen.anzeige import ohne_podest, podest

    rows = [{"place": 1}, {"place": 1}, {"place": 3}, {"place": 4}, {"place": None}]
    assert len(podest(rows)) == 3
    assert ohne_podest(rows) == [{"place": 4}, {"place": None}]


def test_suche_findet_kontakt_einleitung():
    from seite.site import Site
    from seite.views import _search_url

    site = Site.__new__(Site)
    assert _search_url(site, {"kind": "intro", "area": "contact"}) == "/kontakt/"


# --- #141 flaches Epochen-Band ---


def test_chronik_flaches_band_regeln():
    css = (STATIC / "stil.css").read_text()
    slim = 'html[data-st-timeline-chapter="slim"]'
    assert slim + " .zeitleiste-kapitelkopf { padding-top: 18px; padding-bottom: 16px; }" in css
    assert "display: flex; flex-wrap: wrap; align-items: baseline; gap: 0 18px;" in css
    text = " .zeitleiste-kapiteltext { max-width: 46rem; margin: 4px 0 0; font-size: 17px;"
    assert slim + text in css
    # band bleibt, wie es war
    assert "font-family: var(--schrift-titel); font-size: 64px;" in css


def test_chronik_flaches_band_attribut(client, hubiplan):
    hubiplan.info["style"] = {"timeline_chapter": "slim"}
    assert 'data-st-timeline-chapter="slim"' in hole(client, "/")
