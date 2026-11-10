"""Verläufe und Farben für Text, Flächen und Hintergrund aus HUBIplan (Ralf 10.11.2026).
Alle Daten erfunden."""

import pytest

from seite.site import DESIGNS, Site, gradient_css

BLAU = {"from": "#05487a", "to": "#032e52", "direction": "right"}
ROLLEN = {
    "header": {"color": "#05487a", "on_color": "#ffffff", "gradient": BLAU},
    "nav": {"color": "#032e52", "on_color": "#ffffff"},
    "line": {"color": "#05487a", "on_color": "#ffffff", "gradient": BLAU},
    "footer": {"color": "#3c3d3e", "on_color": "#ffffff"},
    "date": {"color": "#05487a", "on_color": "#ffffff"},
    "text": {"color": "#3c3d3e", "on_color": "#ffffff"},
    "muted": {"color": "#5c5d5e", "on_color": "#ffffff"},
    "surface": {"color": "#eef2f6", "on_color": "#1d2421"},
    "background": {"color": "#ffffff", "on_color": "#1d2421"},
}


def text(response) -> str:
    return response.content.decode()


def site_mit(rollen, design="classic", **info) -> Site:
    return Site(key="x", info={"design": design, "designs": {design: rollen}, **info})


def test_verlauf_als_css():
    assert gradient_css(BLAU) == "linear-gradient(to right,#05487a,#032e52)"
    assert gradient_css({**BLAU, "direction": "down"}).startswith("linear-gradient(to bottom,")
    assert gradient_css({**BLAU, "direction": "schraeg"}).startswith("linear-gradient(to right,")
    # Nur geprüfte Farben: nichts, was das <style> verlassen könnte
    assert gradient_css({**BLAU, "to": "red;}body{"}) is None
    assert gradient_css(None) is None


def test_css_variablen_mit_verlauf_und_textfarben():
    css = site_mit(ROLLEN).css_vars
    assert "--bild-kopf:linear-gradient(to right,#05487a,#032e52)" in css
    assert "--linie-zier:linear-gradient(to right,#05487a,#032e52) 1" in css
    assert "--bild-fuss" not in css
    assert "--text:#3c3d3e" in css and "--text-leise:#5c5d5e" in css
    assert "--flaeche:#eef2f6" in css and "--grund:#ffffff" in css


def test_ohne_neue_rollen_wie_bisher():
    alt = {
        k: {"color": v["color"], "on_color": v["on_color"]}
        for k, v in ROLLEN.items()
        if k in ("header", "nav", "line", "footer", "date")
    }
    site = site_mit(alt)
    css = site.css_vars
    assert "--bild-" not in css and "--text:" not in css and "--flaeche:" not in css
    assert site.gradients == {}


def test_hintergrund_geht_regler_vor():
    site = site_mit(ROLLEN, style={"background": "grey"})
    assert site.background_for("#05487a") == "#ffffff"


def test_link_auch_auf_eigener_flaeche_lesbar():
    from seite.site import contrast

    dunkel = {**ROLLEN, "surface": {"color": "#c8d3de", "on_color": "#1d2421"}}
    site = site_mit(dunkel, theme={"primary": "#4a7fb0"})
    assert contrast(site.theme["link"], "#c8d3de") >= 4.5


@pytest.mark.parametrize("design", list(DESIGNS))
def test_verlauf_css_nur_mit_verlauf(client, hubiplan, design):
    hubiplan.info["design"] = design
    hubiplan.info["designs"] = {design: ROLLEN}
    html = text(client.get("/"))
    assert "seite/verlauf.css" in html
    assert "--bild-kopf:linear-gradient(to right,#05487a,#032e52)" in html


def test_ohne_verlauf_kein_verlauf_css(client, hubiplan):
    hubiplan.info["designs"] = {
        "classic": {k: {"color": v["color"], "on_color": v["on_color"]} for k, v in ROLLEN.items()}
    }
    assert "seite/verlauf.css" not in text(client.get("/"))


def test_abschnitt_mit_verlauf(client, hubiplan):
    hubiplan.info["gradients"] = [
        {"colors": ["#05487a", "#032e52"], "on_color": "#ffffff", "direction": "down"}
    ]
    hubiplan.info["home_layout"] = [
        {"key": "c:v1", "kind": "text", "bg": "g0", "title": "Verlauf", "text": "Erfunden"},
        {"key": "c:v2", "kind": "text", "bg": "g1", "title": "Ohne", "text": "Erfunden"},
    ]
    html = text(client.get("/"))
    assert (
        "background:#05487a;background-image:linear-gradient(to bottom,#05487a,#032e52);"
        "color:#ffffff" in html
    )
    # Zweiter Verlauf fehlt: kein farbiger Hintergrund
    assert html.count("abschnitt-farbig") == 1
