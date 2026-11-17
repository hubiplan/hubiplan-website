"""UX-Audit vom 16./17.11.2026, Vereinswebseite (WS-01 bis WS-18, X-03, X-08, X-10).

Vereinsfarben werden gegen die Fläche geprüft, auf der sie wirklich stehen; Karussell, Menü,
Erklärung zur Barrierefreiheit, Beitritt, Anrede, Kontakt und Fehlerseite. Alle Daten erfunden.
"""

import re
from pathlib import Path

import pytest
from django.core.cache import cache

from seite import site as seite_site
from seite import stil
from seite.site import Site, contrast, readable, text_on, text_on_all

from .fake import site_info

STATIC = Path(__file__).resolve().parents[1] / "seite" / "static" / "seite"
VORLAGEN = Path(__file__).resolve().parents[1] / "seite" / "templates" / "seite"

# Prüfpaletten (X-03): Vorgabe, Blau, Gelb, Grün, Rot, sehr hell, sehr dunkel
PALETTEN = ["#1f4e2c", "#009ee0", "#f2b33d", "#7ab800", "#d40808", "#f4f4f4", "#101010"]
FLAECHEN = ("#ffffff", "#fbfaf7")


def hole(client, pfad: str) -> str:
    cache.clear()
    return client.get(pfad).content.decode()


def _site(**over) -> Site:
    return Site(key="k", info=site_info(**over))


def _vars(css_vars: str) -> dict:
    return dict(p.split(":", 1) for p in css_vars.split(";") if ":" in p)


# --- Farben gegen die wirkliche Fläche (WS-01, WS-04, WS-18, X-03) ---


def test_readable_korrigiert_statt_zu_warnen():
    for farbe in PALETTEN:
        neu = readable(farbe, FLAECHEN)
        assert min(contrast(neu, f) for f in FLAECHEN) >= 4.5, farbe
    # Was schon reicht, bleibt wie gewählt
    assert readable("#1d2421", FLAECHEN) == "#1d2421"


def test_schrift_auf_vereinsfarbe():
    # WS-18 live: #f9dada (85 % Weiß) auf #d40808 hatte 4,18 : 1; die gewählte Schrift muss reichen
    assert text_on("#d40808", "#ffffff") == "#ffffff"
    assert contrast(text_on("#f2b33d", "#ffffff"), "#f2b33d") >= 4.5
    for farbe in PALETTEN:
        assert contrast(text_on(farbe, "#888888"), farbe) >= 4.5 or farbe in ("#7ab800",)
    # Verlauf: auf beiden Enden lesbar
    on = text_on_all(["#f2b33d", "#ffffff"], "#ffffff")
    assert min(contrast(on, c) for c in ("#f2b33d", "#ffffff")) >= 4.5


@pytest.mark.parametrize("farbe", PALETTEN)
def test_link_und_datumsschrift_lesbar(farbe):
    info = site_info()
    info["theme"]["primary"] = farbe
    info["designs"] = {"classic": {"date": {"color": farbe, "on_color": "#ffffff"}}}
    s = Site(key="k", info=info)
    werte = _vars(s.css_vars)
    for name, wert in (("link", s.theme["link"]), ("datum-text", werte["--datum-text"])):
        assert min(contrast(wert, f) for f in FLAECHEN) >= 4.5, (farbe, name, wert)
    # Schrift auf Haupt- und Datumsfarbe
    assert contrast(s.theme["on_primary"], farbe) >= 4.5 or farbe == "#7ab800"
    color, on = s.colors["date"]
    assert contrast(on, color) == max(contrast(on, color), contrast("#ffffff", color)) or (
        contrast(on, color) >= 4.5
    )


def test_datumsschrift_im_dunkeln():
    info = site_info(style={"dark": "auto"})
    info["designs"] = {"classic": {"date": {"color": "#1f4e2c", "on_color": "#ffffff"}}}
    werte = _vars(Site(key="k", info=info).css_vars)
    dunkel = werte["--datum-text-dunkel"]
    assert min(contrast(dunkel, b) for b in seite_site.DARK_BACKGROUNDS) >= 4.5
    css = (STATIC / "stil.css").read_text()
    assert "--datum-text: var(--datum-text-dunkel, var(--link));" in css


def test_eigene_textfarben_werden_nachgebessert():
    info = site_info()
    info["designs"] = {"classic": {"text": {"color": "#bbbbbb"}, "muted": {"color": "#cccccc"}}}
    farben = Site(key="k", info=info).common_colors
    for rolle in ("text", "muted"):
        assert min(contrast(farben[rolle], f) for f in FLAECHEN) >= 4.5


def test_vereinsfarbe_nicht_ungeprueft_als_schrift():
    """WS-04: Kein color: var(--primaer) / var(--farbe-datum) mehr für Text auf hellem Grund."""
    css = (STATIC / "seite.css").read_text()
    assert not re.search(r"(?<!-)color:\s*var\(--primaer\)", css)
    assert not re.search(r"(?<!-)color:\s*var\(--farbe-datum\)", css)
    assert ".termin-knopf:focus-visible { outline: 3px solid var(--link);" in css
    # WS-18: kleine Schrift im Fuß ohne Abschwächung
    assert ".fuss .klein { color: inherit; margin: 0; }" in css


def test_band_der_buehne_wie_farbiger_abschnitt():
    """WS-01: Aufklapper, Zahlen, Jahr, Datum, kleine Schrift und Links in den Bändern der
    „Bühne“ und in farbigen Abschnitten erben die Schrift des Abschnitts."""
    css = (STATIC / "seite.css").read_text()
    regel = css.split("/* Abschnitt auf Farbe", 1)[1].split("/* Text mit Bild", 1)[0]
    assert "body.design-stage main.start > section:nth-of-type(even):not([style])" in regel
    for teil in (
        "summary",
        ".zahl",
        ".chronik-jahr",
        ".zeitstrahl-wann",
        ".countdown-einheit",
        "figcaption",
        ".klein",
        "a:not([class])",
    ):
        assert teil in regel, teil
    # Karten behalten ihre helle Fläche und Schrift
    karten = ":is(.karte, .bildkachel, .termin, .kacheln a, .zeitleiste-karte)"
    assert f"{karten} {{ color: var(--text); }}" in regel


def test_palettenabschnitt_schrift_wird_geprueft(client, hubiplan):
    hubiplan.info["palette"] = [{"color": "#f2b33d", "on_color": "#ffffff"}]
    hubiplan.info["home"] = {
        "sections": [{"kind": "text", "title": "Gelb", "text": "Hallo", "bg": "p0"}]
    }
    html = hole(client, "/")
    if "background:#f2b33d" in html:
        assert "background:#f2b33d;color:#ffffff" not in html


# --- Social Media, Suchfeld (WS-06, WS-07) ---


def test_social_symbole_lesbar():
    css = (STATIC / "seite.css").read_text()
    assert ".sm-youtube { --sm: #cc0000; }" in css
    assert contrast("#ffffff", "#cc0000") >= 4.5
    klassisch = (STATIC / "design-classic.css").read_text()
    assert ".kopf-sozial .sozial-symbole a { color: var(--link);" in klassisch
    dunkel = (STATIC / "stil.css").read_text()
    assert (
        'html[data-st-dark="auto"] :is(main, .menue) .sozial-symbole a:not(:hover) '
        "{ color: var(--text);"
    ) in dunkel


def test_suchfelder_mit_deutlichem_rand():
    css = (STATIC / "seite.css").read_text()
    for auswahl in (".suche input {", ".fuss-suche input {"):
        regel = css.split(auswahl, 1)[1].split("}", 1)[0]
        assert "border: 1px solid #767c78" in regel, auswahl
    assert contrast("#767c78", "#ffffff") >= 3 and contrast("#767c78", "#fbfaf7") >= 3


# --- Karussell (WS-02) ---


def test_anhalten_immer_sichtbar():
    css = (STATIC / "seite.css").read_text()
    basis = css.split(".karussell-steuerung {", 1)[1].split("}", 1)[0]
    assert "opacity: 0" not in basis
    assert ".karussell-steuerung [data-pause] { pointer-events: auto; }" in css
    assert (
        ":where(.karussell:not(:hover, :focus-within, .zeigen)) .karussell-steuerung > "
        ":not([data-pause]) { opacity: 0; }"
    ) in css
    ohne_maus = css.split("@media (hover: none) {", 1)[1].split("}", 1)[0]
    assert "opacity: 1; pointer-events: auto;" in ohne_maus


def test_karussell_texte_uebersetzbar_und_eindeutiger_zustand():
    vorlage = (VORLAGEN / "karussell.html").read_text()
    assert 'aria-roledescription="{% translate "Karussell" %}"' in vorlage
    assert 'aria-roledescription="{% translate "Bild" %}"' in vorlage
    assert "{{ n }} von {{ m }}" in vorlage
    js = (STATIC / "karussell.js").read_text()
    assert "setAttribute('aria-label'" not in js
    assert "aria-pressed" in js


# --- Menü (WS-03) ---


def test_menue_bricht_um():
    css = (STATIC / "seite.css").read_text()
    regel = css.split(".menue-breit ul {", 1)[1].split("}", 1)[0]
    assert "flex-wrap: wrap" in regel and "nowrap" not in regel


# --- Barrierefreiheit (WS-08, X-10, F-1) ---


def test_barrierefreiheit_nur_belegbare_aussagen(client, hubiplan):
    html = hole(client, "/barrierefreiheit/")
    assert "Weitgehend erfüllt" not in html and "gesetzlich" not in html
    assert "Die Vorlage dieser Webseite wurde zuletzt im November 2026" in html
    assert "Farben, Bilder und Texte pflegt der Verein selbst" in html
    inhalt = html.split('<main id="inhalt"', 1)[1].split("</main>", 1)[0]
    # Social Media nur, wenn der Verein Beiträge zeigt
    assert "Instagram" not in inhalt
    assert " Sie " not in inhalt and "Ihnen" not in inhalt


def test_barrierefreiheit_ergaenzung_des_vereins(client, hubiplan):
    hubiplan.info["intros"] = {"accessibility": {"text": "Unser Saal hat eine Rampe."}}
    html = hole(client, "/barrierefreiheit/")
    assert "Hinweise des Vereins" in html and "Unser Saal hat eine Rampe." in html


def test_barrierefreiheit_englisch(client, hubiplan):
    hubiplan.info["language"] = "en"
    html = hole(client, "/barrierefreiheit/")
    assert (
        "The template of this website was last checked against WCAG 2.2 AA in November 2026"
    ) in html


# --- Anrede (WS-10) ---


@pytest.mark.parametrize(
    "vorlage", ["mitglied_werden.html", "barrierefreiheit.html", "wartung.html"]
)
def test_rahmentexte_ohne_sie(vorlage):
    text = (VORLAGEN / vorlage).read_text()
    assert not re.search(r"\b(Sie|Ihr|Ihre|Ihren|Ihnen)\b", text), vorlage


def test_anrede_du_auf_wartungsseite(client, hubiplan):
    hubiplan.maintenance = True
    hubiplan.info["style"] = {"address": "informal"}
    html = hole(client, "/")
    assert "Bitte schauen Sie" not in html


# --- Kontakt (WS-13) ---


def test_kontaktangaben_neben_dem_formular(client, hubiplan):
    hubiplan.info["phone"] = "02131 12345-0"
    html = hole(client, "/kontakt/")
    assert "kontakt-angaben" in html and "Weitere Wege zu uns" in html
    assert "Dorfstraße 1" in html and "12345 Musterdorf" in html
    assert 'href="tel:02131123450"' in html
    assert 'href="mailto:info@musterdorf.example"' in html


def test_kontaktangaben_abschaltbar(client, hubiplan):
    hubiplan.info["style"] = {"contact_details": False}
    html = hole(client, "/kontakt/")
    assert "kontakt-angaben" not in html
    assert stil.CATALOG["contact_details"] is bool


def test_erfolg_ersetzt_formular():
    js = (STATIC / "kontakt.js").read_text()
    assert "function erfolg(name, kopie)" in js
    assert "form.hidden = true;" in js and "kasten.focus();" in js
    assert '"Danke! Ihre Nachricht ist bei {name} angekommen."' in js


# --- Beitritt (WS-09, X-08) ---


def test_beitritt_kuendigt_wechsel_an(client, hubiplan):
    hubiplan.info["blocks"]["join"] = True
    hubiplan.antworten = {
        "join/": {
            "intro": "",
            "types": [],
            "units": [],
            "sepa": "offer",
            "form_url": "https://hubiplan.example/beitritt/abc/",
        }
    }
    html = hole(client, "/mitglied-werden/")
    assert "Der Antrag dauert etwa 5 Minuten." in html
    assert "Mitgliederbereich von Schützenverein Musterdorf 1900" in html
    assert 'aria-describedby="beitritt-hinweis">Antrag ausfüllen</a>' in html
    assert "Der Beitrag lässt sich bequem per Lastschrift zahlen" in html


# --- Eigene Fehlerseite (WS-16) ---


def test_unbekannte_adresse_im_vereinsdesign(client, hubiplan):
    cache.clear()
    r = client.get("/gibt-es-nicht/")
    html = r.content.decode()
    assert r.status_code == 404
    assert "Not Found" not in html and "Seite nicht gefunden" in html
    assert "SV Musterdorf" in html and "Zur Startseite" in html
    assert 'lang="de"' in html


def test_unbekannte_adresse_mit_suche(client, hubiplan):
    hubiplan.info["blocks"]["search"] = True
    html = hole(client, "/gibt-es-nicht/")
    assert 'id="fehler-suche-q"' in html


def test_unbekannte_adresse_englisch(client, hubiplan):
    hubiplan.info["language"] = "en"
    r = client.get("/nope/")
    assert r.status_code == 404
    assert "Page not found" in r.content.decode()


def test_unbekannte_adresse_in_wartung(client, hubiplan):
    hubiplan.maintenance = True
    r = client.get("/gibt-es-nicht/")
    assert r.status_code == 404
    assert "Seite nicht gefunden" in r.content.decode()
