"""Seiten der Untereinheiten aus Abschnitten (HUBIplan #491). Alle Daten erfunden."""

import re

from django.core.cache import cache

from .test_abschnitte import bild, layout, text

FEST = ["body", "contact", "homepage", "honors", "events", "news", "follow"]


def feste(*keys):
    return layout(*({"key": k, "kind": k} for k in keys))


def inhalt(html: str) -> str:
    """Hauptbereich ohne Leerraum zwischen den Tags (zum Vergleichen)."""
    main = html[html.index('<main id="inhalt"') : html.index("</main>")]
    return re.sub(r">\s+<", "><", re.sub(r"\s+", " ", main)).strip()


def test_feste_bloecke_wie_bisher(client, hubiplan):
    """Ohne eigene Abschnitte sieht die Seite aus wie vorher (auch mit Homepage daneben)."""
    unit = hubiplan.info["units"][0]
    unit["homepage"] = "https://www.jaegerzug.example/"
    unit["roles"] = []
    vorher = inhalt(text(client.get("/zuege/jaeger/")))
    cache.clear()
    unit["sections"] = feste(*FEST)
    nachher = inhalt(text(client.get("/zuege/jaeger/")))
    assert nachher == vorher
    assert "karte homepage" in nachher and "<h2>Kontakt</h2>" in nachher


def test_eigene_abschnitte_und_reihenfolge(client, hubiplan):
    unit = hubiplan.info["units"][0]
    unit["homepage"] = "https://www.jaegerzug.example/"
    unit["sections"] = [
        *layout({"key": "c:z", "kind": "quote", "text": "Horrido!", "name": "Zugführer"}),
        *feste("honors", "body"),
        *layout(
            {
                "key": "c:t",
                "kind": "text_image",
                "title": "Probe",
                "text": "Jeden Dienstag.",
                "image": bild("probe"),
                "side": "left",
                "size": "half",
            }
        ),
        # Homepage nicht direkt hinter dem Kontakt: eigene Karte ohne Überschrift „Kontakt“
        *feste("homepage", "follow"),
    ]
    html = text(client.get("/zuege/jaeger/"))
    zitat = html.index("Horrido!")
    wuerde = html.index('<section class="wuerde voll">')
    textteil = html.index("Wir sind <em>der</em> Jägerzug.")
    probe = html.index("Jeden Dienstag.")
    assert zitat < wuerde < textteil < probe < html.index("karte homepage")
    assert "<h2>Kontakt</h2>" not in html


def test_ausgeblendete_bloecke_fehlen(client, hubiplan):
    hubiplan.info["units"][0]["sections"] = feste("body")
    html = text(client.get("/zuege/jaeger/"))
    assert "Wir sind <em>der</em> Jägerzug." in html
    assert '<section class="wuerde voll">' not in html


def test_bildplatz_mit_notiz(client, hubiplan):
    hubiplan.info["units"][0]["sections"] = [
        *feste("body"),
        *layout(
            {
                "key": "c:t",
                "kind": "text_image",
                "title": "Probe",
                "text": "Jeden Dienstag.",
                "image": None,
                "placeholder": "Probenszene, Querformat",
            },
            {
                "key": "c:b",
                "kind": "images",
                "title": "",
                "columns": 3,
                "items": [{"image": None, "caption": "", "placeholder": "Gruppenbild"}],
            },
        ),
    ]
    html = text(client.get("/zuege/jaeger/"))
    assert html.count('class="bildplatz"') == 2
    assert "Probenszene, Querformat" in html and "Gruppenbild" in html
    assert "Bild folgt" in html
