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
        # Webseite #89: normale Überschriftengröße ist die Grundstellung aus seite.css
        ("heading_size", "normal"),
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
    for family in (
        '"Open Sans"',
        '"Roboto"',
        '"Great Vibes"',
        '"Source Sans 3"',
        '"Crimson Pro"',
        '"Oswald"',
        '"Atkinson Hyperlegible"',
        '"UnifrakturMaguntia"',
    ):
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


def test_seitentitel_band_randlos_und_auf_textseiten(client, hubiplan):
    """#94: Das Band reicht von Rand zu Rand, schließt an den Kopf an und gilt auch für
    Textseiten und die Seite einer Einheit."""
    hubiplan.info["style"] = {"page_title": "band"}
    cache.clear()
    html = text(client.get("/seite/anfahrt/"))
    assert 'data-st-page-title="band"' in html_tag(html)
    # die Überschrift der Textseite steht als erstes Kind in .textseite direkt im main
    assert '<div class="textseite">\n<h1>Anfahrt</h1>' in html
    css = (STATIC / "stil.css").read_text()
    band = (
        'html:is([data-st-page-title="band"], [data-st-page-title="image"])'
        ' body:not([data-seite="start"])'
    )
    assert f"{band} main > :is(h1, .einheit-kopf),\n{band} main > .textseite > h1 {{" in css
    regel = css.split(f"{band} main > .textseite > h1 {{", 1)[1].split("}", 1)[0]
    assert "margin: .3em calc(50% - 50vw) 1.1rem" in regel and "border-radius: 0" in regel
    assert "max-width: none" in regel
    # ohne Lücke unter dem Kopf, auch bei engem und großzügigem Abstand
    oben = f"{band} main > .textseite:first-child > h1:first-child {{"
    assert oben in css
    assert "margin-top: calc(-1 * var(--st-main-oben, 1.5rem))" in css
    assert 'html[data-st-spacing="compact"] { --st-main-oben: 1rem; }' in css
    assert 'html[data-st-spacing="generous"] { --st-main-oben: 2.2rem; }' in css
    # das Bild-Band gilt für dieselben Stellen
    bild = 'html[data-st-page-title="image"] body:not([data-seite="start"])'
    assert f"{bild} main > .textseite > h1 {{" in css
    # schmale Seite: nur bis zum Rand des Kastens; kein waagerechtes Rollen
    assert "margin-left: -16px; margin-right: -16px" in css
    assert f"{band} {{ overflow-x: clip; }}" in css


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


def test_feinschliff_89_neue_stufen(client, hubiplan):
    """Webseite #89: kurze Zierlinie, weiße Kacheln mit Farbstreifen, Etikett-Knöpfe,
    größere Überschriften und warme helle Abschnitte als Regler für alle Einheiten."""
    hubiplan.info["style"] = {
        "headings": "short",
        "cards": "accent",
        "buttons": "label",
        "heading_size": "large",
        "section_bg": "warm",
    }
    tag = html_tag(seite(client))
    for merkmal in (
        'data-st-headings="short"',
        'data-st-cards="accent"',
        'data-st-buttons="label"',
        'data-st-heading-size="large"',
        'data-st-section-bg="warm"',
    ):
        assert merkmal in tag


def test_seitentitel_eigene_groesse(client, hubiplan):
    """Webseite #96: Seitentitel eigens einstellbar, auch kleiner; er geht vor der Größe der
    Überschriften, schrumpft mit dem Fenster und das Band wird bei kleinem Titel flacher."""
    assert stil.CATALOG["title_size"] == ("small", "medium", "normal", "large")
    hubiplan.info["style"] = {"title_size": "small", "heading_size": "large"}
    tag = html_tag(seite(client))
    assert 'data-st-title-size="small"' in tag and 'data-st-heading-size="large"' in tag
    hubiplan.info["style"] = {"title_size": "tiny"}
    assert "data-st-title-size" not in html_tag(seite(client))
    css = (STATIC / "stil.css").read_text()
    groessen = {}
    for stufe in stil.CATALOG["title_size"]:
        regel = re.search(
            rf'html\[data-st-title-size="{stufe}"\] main h1 '
            r"\{ font-size: clamp\(([\d.]+)rem, [\d.]+vw, ([\d.]+)rem\); \}",
            css,
        )
        assert regel, stufe
        groessen[stufe] = (float(regel.group(1)), float(regel.group(2)))
    # Stufen steigen an, „klein“ und „mittel“ bleiben unter der Grundstellung (2,3 rem)
    werte = [groessen[s] for s in stil.CATALOG["title_size"]]
    assert werte == sorted(werte)
    assert groessen["small"][1] <= 1.5 and groessen["medium"][1] <= 1.75
    assert groessen["normal"] == (1.6, 2.3)
    # eigene Größe steht hinter der Regel für größere Überschriften und gewinnt damit
    assert css.index('html[data-st-heading-size="large"] main h1') < css.index(
        'html[data-st-title-size="small"] main h1'
    )
    # flacheres Band
    assert 'html[data-st-title-size="small"] { --st-band-polster: .7rem; }' in css
    assert "padding: var(--st-band-polster, 1.1rem) max(16px," in css


def test_feinschliff_89_regeln():
    css = (STATIC / "stil.css").read_text()
    seite_css = (STATIC / "seite.css").read_text()
    # kurze Linie 48 × 3 px
    assert "width: 48px; height: 3px;" in css
    # eckig auch für Initialen, Sozialsymbole und Chronik
    eckig = css[css.index('html[data-st-corners="square"] :is(.person img') :]
    for teil in (".ohne-foto", ".sozial-symbole a", ".zeitleiste-sprung a"):
        assert teil in eckig.split("\n", 1)[0]
    assert 'html[data-st-corners="square"] .zeitleiste-eintrag::before' in css
    # farbige Abschnitte: Linie und Knöpfe in der Schriftfarbe des Abschnitts
    assert "html main .abschnitt-farbig h2::after { background: currentColor; }" in css
    assert "html[data-st-buttons] .abschnitt-farbig .knopf:not(.hell)" in css
    # Titelbild in voller Breite ohne Innenpolster
    voll = "main.start > .begruessung-bilder.abschnitt-voll { padding-left: 0; padding-right: 0; }"
    assert voll in seite_css
    # Kacheln weiß, im Dunkelmodus Fläche
    dunkel = 'html[data-st-dark="auto"][data-st-cards="accent"] { --st-karte: var(--flaeche); }'
    assert dunkel in css


def test_farbiger_abschnitt_nennt_seine_farbe(client, hubiplan):
    """Knöpfe auf farbigen Abschnitten bekommen die Abschnittsfarbe als Schrift (#89)."""
    from seite.views import _look

    class S:
        info = {"palette": [{"color": "#33503c", "on_color": "#ffffff"}]}

    look = _look(S(), {"bg": "p0", "width": "full"})
    assert "abschnitt-farbig" in look["klassen"]
    assert "--abschnitt-farbe:#33503c" in look["stil"]


@pytest.mark.parametrize("stufe", ["clear", "elegant"])
def test_source_sans_und_crimson_pro(client, hubiplan, stufe):
    """Ralf 14.11.2026: Source Sans 3 und Crimson Pro als Schrift der Webseite wählbar."""
    hubiplan.info["style"] = {"font": stufe, "heading_font": stufe}
    tag = html_tag(seite(client))
    assert f'data-st-font="{stufe}"' in tag and f'data-st-heading-font="{stufe}"' in tag
    css = (STATIC / "stil.css").read_text()
    assert f'html[data-st-font="{stufe}"] body' in css
    assert f'html[data-st-heading-font="{stufe}"] body' in css


def test_fraktur_oswald_atkinson(client, hubiplan):
    """Ralf 14.11.2026: Fraktur und Oswald für Überschriften, Atkinson Hyperlegible als Text."""
    hubiplan.info["style"] = {"font": "readable", "heading_font": "fraktur"}
    tag = html_tag(seite(client))
    assert 'data-st-font="readable"' in tag and 'data-st-heading-font="fraktur"' in tag
    css = (STATIC / "stil.css").read_text()
    for regel in (
        'html[data-st-font="readable"] body',
        'html[data-st-heading-font="fraktur"] body',
        'html[data-st-heading-font="strong"] body',
    ):
        assert regel in css
    # Fraktur hat nur einen Schnitt: Überschriften nicht künstlich fett
    assert 'html[data-st-heading-font="fraktur"] :is(h1, h2, h3, .marke) { font-weight: 400;' in css


def test_accent_streifen_gewinnt_gegen_kartenregel():
    """Termine bekommen bei cards=accent links den Streifen, Kacheln oben (Webseite #91).

    Die gemeinsame Kartenregel nutzt :is(… .dokumente a …) und zählt damit 0,2,2; die
    Streifenregeln müssen spezifischer sein, sonst setzt deren border den Streifen zurück."""
    css = (STATIC / "stil.css").read_text()
    termine = (
        'html[data-st-cards="accent"] ul.termine > .termin '
        "{ border-left: 3px solid var(--primaer); }"
    )
    kacheln = (
        'html[data-st-cards="accent"] ul.kacheln a '
        "{ border-left-width: 1px; border-top: 3px solid var(--primaer); }"
    )
    assert termine in css
    assert kacheln in css
    assert 'html[data-st-cards="accent"] .termin { border-left' not in css


def test_tabellen_und_kleiner_text_lesbar():
    """Webseite #98: Tabellen so groß wie der Fließtext, kleiner Text mindestens 15 px,
    Source Sans 3 an die Lesegröße der übrigen Schriften angeglichen."""
    css = (STATIC / "seite.css").read_text()
    tabelle = re.search(r"^table \{[^}]*\}", css, re.M).group(0)
    assert "font-size: 1em;" in tabelle
    # Zellen bringen keine eigene, kleinere Größe mit
    assert "font-size" not in re.search(r"^th, td \{[^}]*\}", css, re.M).group(0)
    klein = re.search(r"^\.klein \{[^}]*\}", css, re.M).group(0)
    assert "font-size: max(.88em, .9375rem);" in klein
    assert 16 * 0.9375 == 15
    quellen = re.findall(r'@font-face \{ font-family: "Source Sans 3";[^}]*\}', css)
    assert len(quellen) == 3 and all("size-adjust: 105%;" in q for q in quellen)
    # nur diese beiden Schriften werden angeglichen (Crimson Pro: Webseite #103)
    assert css.count("size-adjust:") - css.count("-webkit-text-size-adjust:") == 6


def test_kleine_ueberschriften_groesser_als_fliesstext():
    """Webseite #103: Crimson Pro auf die Buchstabenhöhe des Fließtexts angehoben, kleine
    Überschriften rund das 1,2-Fache der Grundschrift, Abschnittstitel bleiben darüber."""
    css = (STATIC / "seite.css").read_text()
    stil = (STATIC / "stil.css").read_text()
    quellen = re.findall(r'@font-face \{ font-family: "Crimson Pro";[^}]*\}', css)
    assert len(quellen) == 3 and all("size-adjust: 115%;" in q for q in quellen)

    def rem(muster, text=css):
        return float(re.search(muster, text, re.M).group(1))

    grund = 17 / 16  # Fließtext in rem
    h2 = rem(r"^h2 \{ font-size: ([\d.]+)rem;")
    h3 = rem(r"^h3 \{ font-size: ([\d.]+)rem;")
    assert 1.15 <= h3 / grund <= 1.25
    assert h2 >= h3 + 0.2
    for muster in (
        r"^\.bildkachel h3 \{[^}]*font-size: ([\d.]+)rem;",
        r"^\.aemter h2 \{ font-size: ([\d.]+)rem;",
        r"^\.zeitleiste-karte h3 \{[^}]*font-size: ([\d.]+)rem;",
        r"^\.hinweis-kasten h2 \{[^}]*font-size: ([\d.]+)rem;",
    ):
        assert rem(muster) / grund >= 1.12, muster
    # große Überschriften bleiben über den normalen, der kleinste Seitentitel nicht unter h3
    gross = rem(r'heading-size="large"\] main h2[^{]*\{ font-size: ([\d.]+)rem;', stil)
    assert gross >= h2 + 0.2
    klein = rem(r'title-size="small"\] main h1 \{ font-size: clamp\([\d.]+rem, [\d.]+vw, ([\d.]+)rem\)', stil)
    assert klein >= h2
