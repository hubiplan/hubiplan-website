"""Titelfoto als Bühne (Webseite #122), Wasserzeichen (#123), Terminkarten (#124) und Fuß
mit Wappen und Name (#125). Alle Daten erfunden."""

import re
from pathlib import Path

from django.core.cache import cache

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
