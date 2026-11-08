"""Aktuelles: Beiträge aus Instagram/Facebook, von HUBIplan gespeichert (alles erfunden)."""

from pathlib import Path

import pytest
from django.core.cache import cache

from . import fake


def text(response) -> str:
    return response.content.decode()


@pytest.fixture
def mit_beitraegen(hubiplan):
    hubiplan.info["blocks"]["posts"] = True
    hubiplan.info["posts"] = {"instagram": True, "facebook": True}
    return hubiplan


def test_seite_aktuelles(client, mit_beitraegen):
    r = client.get("/aktuelles/")
    assert r.status_code == 200
    html = text(r)
    assert "Schönes Fest!<br>Danke an alle &lt;b&gt;Helfer&lt;/b&gt;." in html
    assert "Einladung zur Versammlung." in html
    # Bilder laufen über diese Seite, nie zu Meta oder direkt zu HUBIplan
    assert "/medien/a/posts/images/bild1x0/" in html
    assert "cdninstagram" not in html and "fbcdn" not in html
    assert "hubiplan.example/api" not in html
    assert "3 Bilder" in html and ">Video<" in html
    assert (
        'href="https://www.instagram.com/p/beispiel1/" '
        'rel="noopener noreferrer nofollow" target="_blank"' in html
    )
    assert "Video auf Instagram ansehen" in html
    # Auswahl nach Netzwerk
    assert "?kanal=facebook" in html
    cache.clear()
    html = text(client.get("/aktuelles/?kanal=facebook"))
    assert "Einladung zur Versammlung." in html and "Schönes Fest" not in html
    assert ">Aktuelles</a>" in html


def test_bild_ueber_diese_seite(client, mit_beitraegen):
    r = client.get("/medien/a/posts/images/bild1x0/")
    assert r.status_code == 200 and r["Content-Type"] == "image/png"


def test_ohne_beitraege_kein_menuepunkt(client, hubiplan):
    hubiplan.info["blocks"]["posts"] = True
    hubiplan.info["posts"] = {"instagram": False, "facebook": False}
    assert ">Aktuelles</a>" not in text(client.get("/"))
    assert client.get("/aktuelles/").status_code == 404


def test_baustein_aus(client, mit_beitraegen):
    mit_beitraegen.info["blocks"]["posts"] = False
    cache.clear()
    assert client.get("/aktuelles/").status_code == 404
    assert ">Aktuelles</a>" not in text(client.get("/"))


def test_startseite_bausteine(client, mit_beitraegen):
    mit_beitraegen.info["home"] = ["facebook", "greeting", "instagram"]
    html = text(client.get("/"))
    assert "Neu auf Instagram" in html and "Neu auf Facebook" in html
    assert (
        html.index("Neu auf Facebook") < html.index("Willkommen") < html.index("Neu auf Instagram")
    )
    mit_beitraegen.info["home"] = ["greeting"]
    cache.clear()
    html = text(client.get("/"))
    assert "Neu auf Instagram" not in html


def test_zugseite(client, mit_beitraegen):
    mit_beitraegen.info["unit_posts"] = {"instagram": True, "facebook": False}
    html = text(client.get("/zuege/jaeger/"))
    assert "<h2>Aktuelles</h2>" in html and "Probe für den Umzug." in html
    calls = [c[1] for c in mit_beitraegen.calls if "posts/" in c[1]]
    assert any("einheit=jaeger" in c for c in calls)


def test_weiterlesen_ersetzt_anriss(client, mit_beitraegen, monkeypatch):
    """Langer Text: Anriss plus „Weiterlesen“; aufgeklappt verschwindet der Anriss (CSS),
    damit der Text nicht doppelt dasteht."""
    lang = " ".join(f"Wort{i}" for i in range(60))
    monkeypatch.setattr(fake, "POSTS", [fake._post(9, "instagram", lang)])
    html = text(client.get("/aktuelles/"))
    assert '<p class="beitrag-text beitrag-anriss">Wort0' in html
    assert html.count("Wort59") == 1  # nur im vollen Text, nicht im Anriss
    assert 'class="beitrag-mehr"' in html
    css = (Path(__file__).parent.parent / "seite/static/seite/seite.css").read_text()
    assert ".beitrag-anriss:has(+ .beitrag-mehr[open]) { display: none; }" in css
