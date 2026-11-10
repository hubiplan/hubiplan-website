"""Hinweisleiste und Titelbild je Textseite aus HUBIplan (Konzept webseite-baukasten G6,
Ralf 10.11.2026). Alle Daten erfunden."""

from .test_abschnitte import bild, layout, text


def test_ohne_hinweis_keine_leiste(client, hubiplan):
    hubiplan.info.pop("notice", None)
    assert "hinweisleiste" not in text(client.get("/"))


def test_hinweisleiste_mit_ziel_auf_allen_seiten(client, hubiplan):
    hubiplan.info["notice"] = {
        "text": "Schützenfest 22.–25.8.: Programm",
        "target": {"key": "contact"},
    }
    for path in ("/", "/seite/anfahrt/"):
        html = text(client.get(path))
        leiste = html.split('<div class="hinweisleiste" role="note">', 1)[1].split("</div>", 1)[0]
        assert '<a href="/kontakt/">Schützenfest 22.–25.8.: Programm</a>' in leiste
    # Die Leiste steht über dem Kopf
    assert html.index("hinweisleiste") < html.index('<main id="inhalt"')


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
    leiste = html.split('<div class="hinweisleiste" role="note">', 1)[1].split("</div>", 1)[0]
    assert "Heute &lt;b&gt;geschlossen&lt;/b&gt;" in leiste and "<a " not in leiste


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
