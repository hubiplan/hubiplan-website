"""Weitere Stilregler (Ralf 13.11.2026): Titelbild „mittel“, Schrift „sehr groß“, Kontrast
erhöht, Menü auf dem Handy, Bildformat der Kacheln, Karussell, „Nach oben“ und die dunkle
Darstellung nach Gerät (Dunkelmodus D2). Alle Daten erfunden."""

import re

from seite.site import DARK_BACKGROUNDS, contrast, link_color_dark

from .test_stilregler import STATIC, html_tag, seite


def css() -> str:
    return (STATIC / "stil.css").read_text()


def test_neue_stufen_als_merkmale(client, hubiplan):
    hubiplan.info["style"] = {
        "hero": "medium",
        "size": "xlarge",
        "contrast": True,
        "nav_mobile": "scroll",
        "tile_ratio": "square",
        "carousel": "slow",
        "to_top": True,
        "dark": "auto",
    }
    html = seite(client)
    tag = html_tag(html)
    for attr in (
        'data-st-hero="medium"',
        'data-st-size="xlarge"',
        'data-st-contrast="on"',
        'data-st-nav-mobile="scroll"',
        'data-st-tile-ratio="square"',
        'data-st-carousel="slow"',
        'data-st-to-top="on"',
        'data-st-dark="auto"',
    ):
        assert attr in tag, attr
    # Knopf „Nach oben“, erst per Skript sichtbar
    assert '<a class="nach-oben" href="#top" hidden>' in html
    # Linkfarbe für dunkel und für erhöhten Kontrast im <style>
    dunkel = re.search(r"--link-dunkel:(#[0-9a-f]{6})", html).group(1)
    assert all(contrast(dunkel, bg) >= 7 for bg in DARK_BACKGROUNDS)
    links = re.findall(r"--link:(#[0-9a-fA-F]{6})", html)
    assert contrast(links[-1], "#ffffff") >= 7


def test_ohne_schalter_kein_knopf_und_keine_dunkelfarbe(client, hubiplan):
    hubiplan.info["style"] = {"font": "modern"}
    html = seite(client)
    assert "nach-oben" not in html and "--link-dunkel" not in html


def test_dunkel_nur_nach_geraet_und_nicht_fuer_pakete(client, hubiplan):
    rules = css()
    block = rules.split("@media (prefers-color-scheme: dark)", 1)[1]
    assert 'html[data-st-dark="auto"]' in block and "color-scheme: dark" in block
    # Die Linkfarbe wird für dunkle Flächen aufgehellt
    for primary in ("#1f4e2c", "#003366", "#8b0000"):
        color = link_color_dark(primary)
        assert all(contrast(color, bg) >= 4.5 for bg in DARK_BACKGROUNDS), primary


def test_handymenue_als_leiste():
    rules = css()
    block = rules.split("Leiste zum Wischen", 1)[1].split("\n}\n", 1)[0]
    assert '[data-st-nav-mobile="scroll"] .kopf .menue { display: none; }' in block
    assert "overflow-x: auto" in block
    # Untermenüs hängen am Kopf, nicht an der wischbaren Leiste (sonst abgeschnitten)
    assert ".hat-unter { position: static; }" in block


def test_hoehen_des_titelbilds_steigen():
    rules = css()
    heights = [
        float(
            re.search(
                rf'data-st-hero="{s}"\] \.titelbild img {{ max-height: ([\d.]+)rem', rules
            ).group(1)
        )
        for s in ("low", "medium", "normal", "high")
    ]
    assert heights == sorted(heights) and len(set(heights)) == 4


def test_karussell_regler_im_skript():
    js = (STATIC / "karussell.js").read_text()
    assert "stCarousel" in js and "art === 'off'" in js and "art === 'slow' ? 2 : 1" in js
