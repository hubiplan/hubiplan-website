"""Stilregler aus HUBIplan (Konzept G1, Ralf 10.11.2026). Alle Daten erfunden."""

import re
from pathlib import Path

import pytest
from django.core.cache import cache

from seite import stil
from seite.site import DESIGNS, contrast

from . import fake

STATIC = Path(__file__).resolve().parents[1] / "seite" / "static" / "seite"
KEY = fake.KEY


def text(response) -> str:
    return response.content.decode()


def seite(client) -> str:
    """Startseite frisch holen: die Antwort von HUBIplan ist sonst zwischengespeichert."""
    cache.clear()
    return text(client.get("/"))


def html_tag(html: str) -> str:
    return re.search(r"<html[^>]*>", html).group(0)


@pytest.mark.parametrize("design", list(DESIGNS))
def test_ohne_regler_alles_wie_bisher(client, hubiplan, design):
    hubiplan.info["design"] = design
    html = seite(client)
    assert "data-st-" not in html
    assert "stil.css" not in html
    assert "--grund:" not in html


def test_regler_als_merkmale_am_html(client, hubiplan):
    hubiplan.info["style"] = {
        "font": "modern",
        "corners": "round",
        "sticky": True,
        "image_frame": False,
        "footer_align": "center",
    }
    html = seite(client)
    tag = html_tag(html)
    assert 'data-st-font="modern"' in tag
    assert 'data-st-corners="round"' in tag
    assert 'data-st-sticky="on"' in tag
    assert 'data-st-image-frame="off"' in tag
    assert 'data-st-footer-align="center"' in tag
    # stil.css nach dem Design
    assert html.index("design-classic.css") < html.index("seite/stil.css")


def test_unbekannte_regler_und_stufen_fallen_weg(client, hubiplan):
    hubiplan.info["style"] = {
        "font": "comic",
        "corners": '"><script>alert(1)</script>',
        "sticky": "ja",
        "farbe": "rot",
        "width": "wide",
    }
    tag = html_tag(seite(client))
    assert tag.count("data-st-") == 1 and 'data-st-width="wide"' in tag
    assert "<script>alert" not in seite(client)


def test_kein_dict_ist_kein_regler(client, hubiplan):
    hubiplan.info["style"] = ["font", "modern"]
    assert "data-st-" not in seite(client)


def test_wappen_und_name_nie_beide_aus():
    assert stil.clean({"logo": False, "name": False}, "classic") == {"logo": "off"}
    assert stil.clean({"name": False}, "classic") == {"name": "off"}


def test_vom_design_gesperrte_regler(client, hubiplan):
    hubiplan.info["design"] = "sidebar"
    hubiplan.info["style"] = {"logo_pos": "center", "width": "narrow", "corners": "square"}
    tag = html_tag(seite(client))
    assert "data-st-logo-pos" not in tag and "data-st-width" not in tag
    assert 'data-st-corners="square"' in tag
    hubiplan.info["design"] = "stage"
    hubiplan.info["style"] = {"width": "wide", "hero_name": True}
    tag = html_tag(seite(client))
    assert 'data-st-width="wide"' in tag and "data-st-hero-name" not in tag


def test_jede_stufe_hat_regeln():
    css = (STATIC / "stil.css").read_text()
    # Vorgaben ohne eigene Regel, oder in Vorlage bzw. --grund gelöst
    ohne_regel = {
        ("script_greeting", "off"),
        ("spacing", "normal"),
        ("date", "tile"),
        ("header_bg", "image"),
        ("logo", "on"),
        ("name", "on"),
        ("hero_name", "on"),
        ("hero_name", "off"),
        # Ralf 13.11.: Grundstellung ohne Regel, Karussell im Skript, Knopf in der Vorlage
        ("nav_mobile", "toggle"),
        ("dark", "off"),
        ("contrast", "off"),
        ("to_top", "off"),
        ("to_top", "on"),
        ("carousel", "off"),
        ("carousel", "slow"),
        ("carousel", "normal"),
        # Webseite #75: Start und Suche löst die Vorlage (kopf.html, fuss.html)
        ("nav_start", "on"),
        ("nav_start", "off"),
        ("search", "nav"),
        ("search", "header"),
        ("search", "footer"),
        # Ralf 14.11.2026: Einblenden im Skript, Datum in der Vorlage termin_zeit.html
        ("motion", "off"),
        ("date_text", "weekday"),
        ("date_text", "short"),
        ("date_text", "long"),
    }
    for key, allowed in stil.CATALOG.items():
        if key == "background":
            continue  # als --grund im <style> (test_getoenter_grund_und_lesbare_links)
        values = ("on", "off") if allowed is bool else allowed
        attr = key.replace("_", "-")
        for value in values:
            if (key, value) not in ohne_regel:
                assert f'data-st-{attr}="{value}"' in css, (key, value)


def test_getoenter_grund_und_lesbare_links(client, hubiplan):
    hubiplan.info["theme"] = {**hubiplan.info["theme"], "primary": "#3a7d44"}
    hubiplan.info["style"] = {"background": "tinted"}
    html = seite(client)
    grund = re.search(r"--grund:(#[0-9a-f]{6})", html).group(1)
    assert grund == stil.mix("#3a7d44", "#ffffff", stil.TINT)
    link = re.search(r"--link:(#[0-9a-fA-F]{6})", html).group(1)
    assert contrast(link, grund) >= 4.5
    hubiplan.info["style"] = {"background": "grey"}
    assert "--grund:#eff1f0" in seite(client)


def test_kopf_weiss_statt_kopfbild(client, hubiplan):
    hubiplan.info["header_image"] = {
        "key": "banner",
        "url": f"{fake.BASE}images/banner/",
        "width": 1200,
        "height": 300,
        "alt": "Banner",
    }
    assert 'class="marke marke-bild"' in seite(client)
    hubiplan.info["style"] = {"header_bg": "image"}
    assert 'class="marke marke-bild"' in seite(client)
    hubiplan.info["style"] = {"header_bg": "white"}
    html = seite(client)
    assert 'class="marke marke-bild"' not in html
    assert "/medien/m/logos/wappen.png" in html


def _galerie(hubiplan, anzahl):
    bild = {
        "key": "festbild1",
        "url": f"{fake.BASE}images/festbild1/",
        "small_url": "",
        "width": 800,
        "height": 400,
        "caption": "",
        "alt": "Festzug",
    }
    hubiplan.info["home"] = ["carousel", "greeting"]
    hubiplan.info["greeting"] = {
        "title": "Willkommen",
        "text": "Hallo",
        "image": bild if anzahl == 1 else None,
        "gallery": [bild] * anzahl if anzahl > 1 else [],
    }


@pytest.mark.parametrize("anzahl", [1, 2])
def test_name_auf_dem_titelbild(client, hubiplan, anzahl):
    _galerie(hubiplan, anzahl)
    assert 'class="titel-name"' not in seite(client)
    hubiplan.info["style"] = {"hero_name": True}
    html = seite(client)
    assert '<p class="titel-name" aria-hidden="true">Schützenverein Musterdorf 1900</p>' in html


def test_schriften_der_regler_liegen_lokal():
    css = (STATIC / "stil.css").read_text()
    assert "url(" not in css and "@import" not in css
    for family in ('"Open Sans"', '"Roboto"', '"Great Vibes"'):
        assert family in css
        assert f"font-family: {family}" in (STATIC / "seite.css").read_text()


def test_menuestile_lassen_den_menueknopf_in_ruhe():
    """Regeln der Stilregler für Menüpunkte dürfen den hervorgehobenen Knopf („Mitglied werden“)
    nicht umfärben; sonst steht etwa bei „Menü: Text“ die Kopfschrift auf der Menüfarbe (#64)."""
    css = (STATIC / "stil.css").read_text()
    for match in re.finditer(r"\.menue-breit > ul > li > a([^,{]*)", css):
        assert ":not(.menue-knopf)" in match.group(1), match.group(0)
    # Für die Leiste behält der Knopf eigene Farben
    assert 'html[data-st-nav="bar"] .menue-breit a.menue-knopf' in css


def test_menueleiste_schneidet_untermenues_nicht_ab():
    """Das farbige Band der Leiste reicht über die ganze Breite, ohne clip-path: das schnitt
    die Aufklappmenüs unter dem Menü ab (#66)."""
    for name in ("stil.css", "design-newspaper.css"):
        css = re.sub(r"/\*.*?\*/", "", (STATIC / name).read_text(), flags=re.S)
        for block in re.findall(r"\.menue-breit\s*\{[^}]*\}", css):
            assert "clip-path" not in block, (name, block)
    assert "fill 0 / 0 / 0 100vmax" in (STATIC / "stil.css").read_text()


def test_aufklappmenue_hover_und_regler():
    """Hover und Fokus im Aufklappmenü sind deutlich markiert; Ecken und Karten wirken (#66)."""
    seite = (STATIC / "seite.css").read_text()
    rule = re.search(
        r"\.untermenue ul a:hover,\s*\n?[^{]*\.untermenue ul a:focus-visible \{([^}]*)\}", seite
    )
    assert rule and "var(--farbe-zier)" in rule.group(1) and "var(--farbe-menue)" in rule.group(1)
    stil = (STATIC / "stil.css").read_text()
    corners = "html[data-st-corners] .menue-breit .untermenue ul { border-radius: var(--rund); }"
    assert corners in stil
    assert re.search(r'data-st-cards="flat"\][^{]*\.untermenue ul[^{]*\{\s*box-shadow: none', stil)


def test_kopfhoehe_mittel(client, hubiplan):
    """Zwischenstufe „mittel“ für die Kopfhöhe, etwa für ein queres Kopfbild (#68)."""
    hubiplan.info["style"] = {"header_bg": "image", "header_height": "medium"}
    assert 'data-st-header-height="medium"' in html_tag(seite(client))
    css = (STATIC / "stil.css").read_text()
    heights = {
        stage: float(
            re.search(
                rf'data-st-header-height="{stage}"\] \.marke\.marke-bild img '
                r"\{ max-height: ([\d.]+)rem",
                css,
            ).group(1)
        )
        for stage in ("low", "medium", "high")
    }
    normal = float(
        re.search(
            r"\.marke\.marke-bild img \{[^}]*max-height: ([\d.]+)rem",
            (STATIC / "seite.css").read_text(),
        ).group(1)
    )
    assert heights["low"] < heights["medium"] < normal < heights["high"]


# --- Weitere Regler (Ralf 14.11.2026) ---


def test_titelbild_abdunkeln_und_faerben(client, hubiplan):
    hubiplan.info["style"] = {"hero_shade": "strong", "hero_tint": "primary", "hero_focus": "top"}
    tag = html_tag(seite(client))
    assert 'data-st-hero-shade="strong"' in tag
    assert 'data-st-hero-tint="primary"' in tag
    assert 'data-st-hero-focus="top"' in tag
    css = (STATIC / "stil.css").read_text()
    # halb durchsichtige Schicht in der gewählten Farbe, Bildunterschrift bleibt frei
    assert 'html[data-st-hero-tint="primary"] { --st-schleier: var(--primaer); }' in css
    assert 'html[data-st-hero-tint="accent"] { --st-schleier: var(--akzent); }' in css
    assert "opacity: var(--st-deckung)" in css and "grid-area: 1 / 1" in css


def test_neue_regler_als_merkmale(client, hubiplan):
    hubiplan.info["style"] = {
        "hero_text": "band",
        "sections": "alternate",
        "page_title": "band",
        "heading_font": "festive",
        "nav_case": "upper",
        "nav_size": "large",
        "motion": "subtle",
        "stripes": True,
        "date_text": "long",
    }
    tag = html_tag(seite(client))
    for attr in (
        'data-st-hero-text="band"',
        'data-st-sections="alternate"',
        'data-st-page-title="band"',
        'data-st-heading-font="festive"',
        'data-st-nav-case="upper"',
        'data-st-nav-size="large"',
        'data-st-motion="subtle"',
        'data-st-stripes="on"',
        'data-st-date-text="long"',
    ):
        assert attr in tag, attr


def test_einblenden_nur_mit_skript_und_ohne_weniger_bewegung():
    js = (STATIC / "menue.js").read_text()
    assert 'getAttribute("data-st-motion") !== "subtle"' in js
    assert "prefers-reduced-motion: reduce" in js
    css = (STATIC / "stil.css").read_text()
    # ohne Skript gibt es .st-ein nie: nichts bleibt unsichtbar
    assert 'html[data-st-motion="subtle"] .st-ein { opacity: 0;' in css


def test_seitenkopf_mit_titelbild_der_startseite(client, hubiplan):
    hubiplan.info["style"] = {"page_title": "image"}
    hubiplan.info["greeting"] = {
        "title": "Willkommen",
        "text": "",
        "image": {
            "url": f"{fake.BASE}images/titel-v1/",
            "small_url": f"{fake.BASE}images/titel-v1/?size=small",
            "alt": "",
        },
        "gallery": [],
    }
    cache.clear()
    html = text(client.get("/impressum/"))
    assert 'data-st-page-title="image"' in html_tag(html)
    assert '--st-seitenbild:url("/' in html


def test_seitenbild_nur_mit_sicherer_adresse(client, hubiplan):
    from seite.site import SAFE_URL

    assert SAFE_URL.match("/medien/a/bild.jpg?v=3")
    assert not SAFE_URL.match('/medien/a/bild.jpg");}body{x:url("')
    assert not SAFE_URL.match("/medien/a/bild (1).jpg")


def test_datum_neben_dem_datumsfeld():
    vorlage = (STATIC.parents[1] / "templates" / "seite" / "termin_zeit.html").read_text()
    assert 'art == "long"' in vorlage and 'datum:"wkurz"' in vorlage


def test_vorschau_springt_auf_unterseite(client):
    r = client.get("/vorschau/design/?ziel=unterseite")
    assert r.status_code == 302 and r["Location"].endswith("/impressum/")
    r = client.get("/vorschau/design/?ziel=http://boese.example/")
    assert r["Location"].endswith("/") and "boese" not in r["Location"]


def test_vorschau_hervorhebung_nur_in_der_vorschau(client, hubiplan):
    html = seite(client)
    assert "data-vorschau" not in html_tag(html)
    assert 'id="kopf"' in html and 'id="fuss"' in html
    css = (STATIC / "seite.css").read_text()
    assert "html[data-vorschau] :is(#kopf, #fuss, #inhalt):target" in css
