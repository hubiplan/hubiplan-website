"""Titelfoto als Bühne (Webseite #122), Wasserzeichen (#123), Terminkarten (#124) und Fuß
mit Wappen und Name (#125). Alle Daten erfunden."""

import re
from pathlib import Path

from django.core.cache import cache

from seite import stil

from . import fake

STATIC = Path(__file__).resolve().parents[1] / "seite" / "static" / "seite"


def seite(client, pfad="/") -> str:
    cache.clear()
    return client.get(pfad).content.decode()


def bild(key: str) -> dict:
    return {
        "key": key,
        "url": f"{fake.BASE}images/{key}/",
        "small_url": "",
        "width": 1600,
        "height": 900,
        "caption": "",
        "alt": f"Bild {key}",
    }


def layout(*sections):
    return [{"bg": "none", "width": "content", "column": "main", **s} for s in sections]


def _buehne(hubiplan, bilder=3, **carousel):
    hubiplan.info["greeting"] = {
        "title": "Willkommen",
        "text": "Hallo",
        "image": bild("titel") if bilder == 1 else None,
        "gallery": [bild(f"fest{i}") for i in range(bilder)] if bilder > 1 else [],
    }
    hubiplan.info["home_layout"] = layout(
        {"key": "carousel", "kind": "carousel", **carousel},
        {"key": "greeting", "kind": "greeting", "bg": "light", "width": "full"},
    )


def test_ohne_regler_bleibt_das_titelbild_wie_bisher(client, hubiplan):
    _buehne(hubiplan, hero_titles=["Tradition, die verbindet."])
    html = seite(client)
    assert "titel-buehne" not in html
    assert "Tradition, die verbindet." not in html


def test_buehne_mit_wechselnden_titelzeilen(client, hubiplan):
    zeilen = ["Willkommen in Musterdorf.", "Tradition, die verbindet.", "Seit 1900 <dabei>."]
    _buehne(hubiplan, hero_titles=zeilen, hero_kicker="Schützenverein")
    hubiplan.info["style"] = {"hero_width": "full"}
    html = seite(client)
    assert 'data-st-hero-width="full"' in re.search(r"<html[^>]*>", html).group(0)
    assert 'class="begruessung begruessung-bilder titel-buehne"' in html
    assert '<p class="buehne-oberzeile">Schützenverein</p>' in html
    assert "data-buehne-zeilen" in html
    assert '<p class="buehne-zeile aktiv">Willkommen in Musterdorf.</p>' in html
    # weitere Zeilen werden nicht vorgelesen und sind maskiert
    assert '<p class="buehne-zeile" aria-hidden="true">Tradition, die verbindet.</p>' in html
    assert "Seit 1900 &lt;dabei&gt;." in html
    assert "karussell.js" in html


def test_buehne_mit_einem_bild_und_einer_zeile(client, hubiplan):
    _buehne(hubiplan, bilder=1, hero_titles=["Willkommen"])
    hubiplan.info["style"] = {"hero_width": "full"}
    html = seite(client)
    assert "titel-buehne" in html and '<figure class="titelbild">' in html
    assert "data-buehne-zeilen" not in html  # eine Zeile bleibt stehen
    assert '<p class="buehne-zeile aktiv">Willkommen</p>' in html


def test_buehne_ohne_text_zeigt_nur_das_foto(client, hubiplan):
    _buehne(hubiplan)
    hubiplan.info["style"] = {"hero_width": "full"}
    html = seite(client)
    assert "titel-buehne" in html and "buehne-titel" not in html


def test_buehne_in_inhaltsbreite(client, hubiplan):
    """Webseite #128: dieselbe Bühne mit Titelzeilen, nur so breit wie der Inhalt."""
    _buehne(hubiplan, hero_titles=["Willkommen"], hero_kicker="Schützenverein")
    hubiplan.info["style"] = {
        "hero_width": "stage",
        "hero_stage_width": "wider",
        "hero_side": "color",
    }
    html = seite(client)
    tag = re.search(r"<html[^>]*>", html).group(0)
    assert 'data-st-hero-width="stage"' in tag
    assert 'data-st-hero-stage-width="wider"' in tag and 'data-st-hero-side="color"' in tag
    assert "titel-buehne" in html and '<p class="buehne-zeile aktiv">Willkommen</p>' in html
    css = (STATIC / "stil.css").read_text()
    assert '[data-st-hero-width="stage"] main.start > .titel-buehne {' in css
    assert "var(--breite) + 8rem" in css and "var(--breite) + 16rem" in css
    hubiplan.info["design"] = "stage"
    tag = re.search(r"<html[^>]*>", seite(client)).group(0)
    assert "data-st-hero-side" not in tag and "data-st-hero-stage-width" not in tag


def test_buehne_in_buehne_und_zeitung_gesperrt(client, hubiplan):
    _buehne(hubiplan, hero_titles=["Willkommen"])
    hubiplan.info["style"] = {"hero_width": "full"}
    hubiplan.info["design"] = "newspaper"
    assert "titel-buehne" not in seite(client)


def test_skript_wechselt_zeilen_mit_den_bildern():
    js = (STATIC / "karussell.js").read_text()
    assert "[data-buehne-zeilen] .buehne-zeile" in js
    assert "aktuell() % zeilen.length" in js
    css = (STATIC / "stil.css").read_text()
    assert "min(62vh, 600px)" in css
    assert "@media (prefers-reduced-motion: reduce) { .buehne-zeile { transition: none; } }" in css


def test_wasserzeichen_hinter_farbigem_abschnitt(client, hubiplan):
    hubiplan.info["palette"] = [{"color": "#123456", "on_color": "#ffffff"}]
    hubiplan.info["home_layout"] = layout(
        {"key": "greeting", "kind": "greeting", "bg": "p0", "width": "full", "mark": "logo"},
        {
            "key": "c:t1",
            "kind": "text",
            "title": "Über uns",
            "text": "Erfunden.",
            "bg": "light",
            "mark": bild("hirsch"),
        },
        # ohne Hintergrund kein Wasserzeichen
        {"key": "c:t2", "kind": "text", "title": "Ohne", "text": "x", "mark": "logo"},
        # fremde Adressen nie
        {
            "key": "c:t3",
            "kind": "text",
            "title": "Fremd",
            "text": "x",
            "bg": "light",
            "mark": {"url": 'https://boese.example/x.png") ; background:red'},
        },
    )
    html = seite(client)
    sections = re.findall(r"<section[^>]*>", html)
    gruss = next(s for s in sections if "begruessung" in s)
    assert "mit-zeichen" in gruss
    assert "--zeichen:url(&quot;/medien/m/logos/wappen.png&quot;)" in gruss
    assert sum("mit-zeichen" in s for s in sections) == 2
    assert "boese.example" not in html


def _termine(hubiplan):
    hubiplan.info["home_layout"] = layout({"key": "events", "kind": "events"})


def test_terminkarten_klasse_und_regeln(client, hubiplan):
    _termine(hubiplan)
    hubiplan.info["style"] = {"date": "card"}
    html = seite(client)
    assert 'data-st-date="card"' in html
    css = (STATIC / "stil.css").read_text()
    assert 'html[data-st-date="card"] .termine-vorschau' in css
    erster = ".termine-vorschau > .termin:first-child .termin-datum { background: var(--primaer)"
    assert erster in css
    # Die Terminseite bleibt eine Liste (nur Vorschauen werden Karten)
    assert "termine-vorschau" not in seite(client, "/termine/")


def test_fuss_schlicht_wie_bisher(client, hubiplan):
    html = seite(client)
    assert 'class="fuss" id="fuss"' in html and "fuss-voll" not in html
    assert "Impressum" in html and "Quellcode" in html


def test_fuss_mit_wappen_und_name(client, hubiplan):
    hubiplan.info["style"] = {"footer_layout": "full", "footer_line": "primary"}
    html = seite(client)
    fuss = html[html.index('<footer class="fuss fuss-voll"') :]
    assert '<p class="fuss-name">Schützenverein Musterdorf 1900</p>' in fuss
    assert "gegründet 1900 · Musterdorf" in fuss
    assert 'class="fuss-bild"' in fuss and "w=256" in fuss
    assert "Bürgerverein Musterdorf" in fuss
    for link in ("Impressum", "Datenschutz", "Barrierefreiheit", "Quellcode"):
        assert link in fuss
    assert "Daten aus" in fuss
    assert 'data-st-footer-line="primary"' in html


def test_fuss_ohne_name_und_gruendung(client, hubiplan):
    """Webseite #127: Name und Gründungszeile ausblendbar; das Wappen nennt dann die Einheit."""
    hubiplan.info["style"] = {"footer_layout": "full", "footer_name": False}
    html = seite(client)
    fuss = html[html.index('<footer class="fuss fuss-voll"') :]
    assert 'class="fuss-name"' not in fuss
    assert 'alt="Schützenverein Musterdorf 1900"' in fuss
    assert "gegründet 1900 · Musterdorf" in fuss
    assert "Bürgerverein Musterdorf" in fuss
    hubiplan.info["style"] = {"footer_layout": "full", "footer_founded": False}
    fuss = seite(client)
    fuss = fuss[fuss.index('<footer class="fuss fuss-voll"') :]
    assert '<p class="fuss-name">Schützenverein Musterdorf 1900</p>' in fuss
    assert "gegründet 1900" not in fuss and 'alt=""' in fuss


def test_fuss_ohne_wappen_behaelt_den_namen(client, hubiplan):
    hubiplan.info["logo_url"] = None
    hubiplan.info["style"] = {"footer_layout": "full", "footer_name": False}
    html = seite(client)
    fuss = html[html.index('<footer class="fuss fuss-voll"') :]
    assert 'class="fuss-bild"' not in fuss
    assert '<p class="fuss-name">Schützenverein Musterdorf 1900</p>' in fuss


def test_buehne_knoepfe_immer_sichtbar_und_ueber_bild_und_verlauf():
    """Webseite #130: Auf der Bühne (full und stage) stehen Anhalten, zurück und weiter immer
    sichtbar und klickbar über Bild, Verlauf und Titelzeilen; eine Abschnittsbreite „Text“
    drückt die Bühne nicht zusammen."""
    css = (STATIC / "stil.css").read_text()
    buehne = (
        'html:is([data-st-hero-width="full"], [data-st-hero-width="stage"]) '
        "main.start > .titel-buehne"
    )
    assert f"{buehne} .karussell-steuerung {{ z-index: 3; opacity: 1; }}" in css
    assert f"{buehne} .karussell-steuerung > * {{ pointer-events: auto; }}" in css
    regel = css.split(f"{buehne} {{", 1)[1].split("}", 1)[0]
    assert "max-width: none" in regel and "isolation: isolate" in regel
    # Titelzeilen (z-index 1) bleiben unter den Knöpfen
    assert "position: absolute; z-index: 1; inset: 0 0 auto; height: var(--buehne-hoehe)" in css


def _regel(css: str, auswahl: str) -> str:
    treffer = re.search(re.escape(auswahl) + r"\s*\{([^}]*)\}", css)
    assert treffer, auswahl
    return treffer.group(1)


def test_voller_fuss_kompakt():
    """Webseite #132: Der volle Fuß stellt die Rechtslinks nebeneinander, das Wappen ist
    kleiner und der Innenabstand knapper; auf dem Handy bleibt das Wappen neben dem Text."""
    css = (STATIC / "stil.css").read_text()
    recht = _regel(css, ".fuss-voll .recht")
    assert "flex-direction: row" in recht and "flex-wrap: wrap" in recht
    assert "height: 76px" in _regel(css, ".fuss-voll .fuss-bild")
    innen = _regel(css, ".fuss-voll .fuss-innen")
    assert "padding-top: 1.25rem" in innen and "padding-bottom: .9rem" in innen
    handy = css[css.index(".fuss-voll .fuss-innen { grid-template-columns: 1fr;") :]
    handy = handy[: handy.index("\n}")]
    assert ".fuss-voll .fuss-marke { flex-direction: row;" in handy
    assert ".fuss-voll .fuss-bild { height: 64px; }" in handy
    # „Mitglied im …“ im Fuß erbt nicht Linie und Abstand der Personenzeilen (.mitglied)
    seite_css = (STATIC / "seite.css").read_text()
    assert "border-bottom: 0" in _regel(seite_css, ".fuss .mitglied")


def test_knoepfe_am_karussell_einstellbar():
    """Ralf 16.11.2026: Knöpfe am Karussell „immer sichtbar“ für alle Karussells oder „bei
    Mauszeiger“, dann auch auf der Bühne nur bei Maus/Fokus; ohne Maus bleiben sie sichtbar."""
    css = (STATIC / "stil.css").read_text()
    assert 'html[data-st-carousel-controls="always"] .karussell-steuerung { opacity: 1; }' in css
    mit_maus = css.split("@media (hover: hover) {", 1)[1].split("\n}", 1)[0]
    assert (
        'html[data-st-carousel-controls="hover"]:is([data-st-hero-width="full"], '
        '[data-st-hero-width="stage"]) main.start > .titel-buehne '
        ".karussell:not(:hover, :focus-within, .zeigen) .karussell-steuerung { opacity: 0; }"
    ) in mit_maus
    ohne_maus = css.split("@media (hover: none) {", 1)[1].split("\n}", 1)[0]
    hover = 'html[data-st-carousel-controls="hover"]'
    assert f"{hover} .karussell-steuerung {{ opacity: 1; }}" in ohne_maus
    assert stil.CATALOG["carousel_controls"] == ("always", "hover")
