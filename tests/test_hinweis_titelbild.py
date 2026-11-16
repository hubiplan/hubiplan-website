"""Hinweisleiste und Titelbild je Textseite aus HUBIplan (Konzept webseite-baukasten G6,
Ralf 10.11.2026). Alle Daten erfunden."""

from .test_abschnitte import bild, layout, text


def leiste_von(html):
    return html.split('<div class="hinweisleiste', 1)[1].split("</div></div>", 1)[0]


def test_ohne_hinweis_keine_leiste(client, hubiplan):
    hubiplan.info.pop("notice", None)
    html = text(client.get("/"))
    assert "hinweisleiste" not in html and "hinweis.js" not in html


def test_hinweisleiste_mit_ziel_auf_allen_seiten(client, hubiplan):
    hubiplan.info["notice"] = {
        "text": "Sommerfest 22.–25.8.: Programm",
        "target": {"key": "contact"},
    }
    for path in ("/", "/seite/anfahrt/"):
        html = text(client.get(path))
        leiste = leiste_von(html)
        assert "<strong>Sommerfest 22.–25.8.: Programm</strong>" in leiste
        # Ältere HUBIplan-Fassung ohne Aussehen: Akzentfarbe unter dem Kopf, Knopf „Mehr erfahren“
        assert leiste.startswith(' hinweis-accent hinweis-platz-below" role="note"')
        assert '<a class="hinweis-knopf" href="/kontakt/">Mehr erfahren' in leiste
    # Die Leiste steht unter dem Kopf, vor dem Inhalt
    assert html.index('class="kopf') < html.index("hinweisleiste") < html.index('<main id="inhalt"')


def test_hinweisleiste_aussehen_aus_hubiplan(client, hubiplan):
    """Ralf 16.11.2026: Stil, Platz, Symbol, Knopf und Countdown."""
    import datetime

    from django.utils import timezone

    tag = timezone.localdate() + datetime.timedelta(days=5)
    hubiplan.info["notice"] = {
        "text": "Sommerfest",
        "target": {"key": "contact"},
        "style": "festive",
        "place": "top",
        "icon": "star",
        "button": "Zum Programm",
        "date": tag.isoformat(),
    }
    html = text(client.get("/"))
    leiste = leiste_von(html)
    assert leiste.startswith(' hinweis-festive hinweis-platz-top" role="note"')
    assert '<span class="hinweis-symbol"><svg' in leiste
    assert '<span class="hinweis-countdown">noch 5 Tage</span>' in leiste
    assert ">Zum Programm<" in leiste
    # Über dem Kopf
    assert html.index("hinweisleiste") < html.index('class="kopf')
    # Heute, morgen, vorbei (direkt am Baustein, die Seiteninfo ist zwischengespeichert)
    from seite.templatetags.seite import hinweis_ansicht

    heute = timezone.localdate()
    assert hinweis_ansicht({"date": heute.isoformat()})["tage"] == 0
    assert hinweis_ansicht({"date": (heute + datetime.timedelta(days=1)).isoformat()})["tage"] == 1
    assert (
        hinweis_ansicht({"date": (heute - datetime.timedelta(days=1)).isoformat()})["tage"] is None
    )
    assert hinweis_ansicht({"date": "kaputt"})["tage"] is None
    assert hinweis_ansicht(None) == {"stil": "accent", "platz": "below", "symbol": "", "tage": None}
    # Unbekannte Werte fallen auf die Vorgabe zurück, kein Symbol ohne bekanntes
    a = hinweis_ansicht({"style": 'x" onclick="y', "place": "links", "icon": "bombe"})
    assert (a["stil"], a["platz"], a["symbol"]) == ("accent", "below", "")


def test_hinweisleiste_schwebend_schliessbar(client, hubiplan):
    hubiplan.info["notice"] = {"text": "Sommerfest", "target": None, "place": "float"}
    html = text(client.get("/"))
    leiste = leiste_von(html)
    assert "data-hinweis-schwebend" in leiste
    assert '<button type="button" class="hinweis-zu" hidden>' in leiste
    assert "Hinweis schließen" in leiste
    assert "seite/hinweis.js" in html


def test_hinweisleiste_nach_aussen_und_ohne_ziel(client, hubiplan):
    hubiplan.info["notice"] = {
        "text": "Neues Programm",
        "target": {"key": "link", "url": "https://example.org/fest"},
    }
    html = text(client.get("/"))
    assert 'href="https://example.org/fest" target="_blank" rel="noopener noreferrer"' in html


def test_hinweisleiste_nur_text(client, hubiplan):
    hubiplan.info["notice"] = {"text": "Heute <b>geschlossen</b>", "target": None}
    html = text(client.get("/"))
    leiste = leiste_von(html)
    assert "Heute &lt;b&gt;geschlossen&lt;/b&gt;" in leiste and "<a " not in leiste
    assert "hinweis-zu" not in leiste and "hinweis.js" not in html


def test_titelbild_ueber_der_ueberschrift(client, hubiplan):
    hubiplan.antworten["pages/anfahrt/"] = {
        "slug": "anfahrt",
        "title": "Anfahrt",
        "text": "Mit dem Bus.",
        "image": None,
        "sections": layout(
            {"key": "body", "kind": "body"},
            {"key": "c:tb", "kind": "cover", "image": bild("festwiese")},
        ),
    }
    html = text(client.get("/seite/anfahrt/"))
    assert '<figure class="seiten-titelbild">' in html
    assert html.index("seiten-titelbild") < html.index("<h1>Anfahrt</h1>")
    assert 'alt="Bild festwiese"' in html
    # Nur das Titelbild: der Text erscheint wie bisher, nicht als Abschnitt
    assert "Mit dem Bus." in html and "abschnitt-text" not in html


def test_titelbild_ohne_bild_faellt_weg(client, hubiplan):
    hubiplan.antworten["pages/anfahrt/"] = {
        "slug": "anfahrt",
        "title": "Anfahrt",
        "text": "Mit dem Bus.",
        "image": None,
        "sections": layout({"key": "body", "kind": "body"}, {"key": "c:tb", "kind": "cover"}),
    }
    assert "seiten-titelbild" not in text(client.get("/seite/anfahrt/"))
