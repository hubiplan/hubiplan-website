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


# --- Eigene Beiträge (#707) ---


@pytest.fixture
def eigene(hubiplan, monkeypatch):
    hubiplan.info["blocks"]["posts"] = True
    hubiplan.info["posts"] = {"instagram": True, "facebook": True, "own": True}
    lang = "Ein schöner Tag mit Musik. " * 10
    monkeypatch.setattr(
        fake,
        "OWN_POSTS",
        [
            fake._own(1, "Sommerfest", "2026-10-18", text=lang, images=2),
            fake._own(2, "Jubiläum", "2015-10-03", text="Rückblick.", video=True),
        ],
    )
    return hubiplan


def test_eigene_beitraege_gemischt_nach_datum(client, eigene):
    html = text(client.get("/aktuelles/"))
    # 19.10. Instagram, 18.10. eigener Beitrag, 18.10. Instagram (10 Uhr UTC), … 2015 zuletzt
    assert html.index("Schönes Fest") < html.index("Sommerfest") < html.index("Jubiläum")
    assert '<a href="/aktuelles/sommerfest/">Sommerfest</a>' in html
    assert "18. Oktober 2026" in html and "3. Oktober 2015" in html
    assert "/medien/a/images/foto1x0-v0/" in html
    assert "2 Bilder" in html
    # Auswahl „Eigene Beiträge“
    assert "?kanal=own" in html
    cache.clear()
    html = text(client.get("/aktuelles/?kanal=own"))
    assert "Sommerfest" in html and "Schönes Fest" not in html


def test_seite_eines_beitrags(client, eigene):
    r = client.get("/aktuelles/sommerfest/")
    assert r.status_code == 200
    html = text(r)
    assert "<h1>Sommerfest</h1>" in html
    assert html.count("Ein schöner Tag mit Musik.") == 10
    assert "/medien/a/images/foto1x1-v0/" in html
    assert 'href="/aktuelles/"' in html
    assert client.get("/aktuelles/gibt-es-nicht/").status_code == 404


def test_video_als_link(client, eigene, monkeypatch):
    monkeypatch.setattr(
        fake, "OWN_POSTS", [fake._own(3, "Konzert", "2020-05-01", text="Mitschnitt.", video=True)]
    )
    html = text(client.get("/aktuelles/konzert/"))
    assert 'href="https://video.example/sommerfest" target="_blank"' in html
    assert "Ständchen" in html
    assert "<iframe" not in html


def test_archiv_aeltere_beitraege(client, eigene, monkeypatch):
    many = [fake._own(10 + i, f"Bericht {i}", f"20{10 + i}-04-01") for i in range(30)]
    monkeypatch.setattr(fake, "OWN_POSTS", many)
    html = text(client.get("/aktuelles/"))
    assert 'rel="next" href="/aktuelles/?seite=2"' in html
    assert 'rel="prev"' not in html
    cache.clear()
    html = text(client.get("/aktuelles/?seite=2"))
    assert 'rel="prev" href="/aktuelles/"' in html
    assert 'rel="next"' not in html
    assert "Bericht 0" in html  # der älteste steht hinten
    assert client.get("/aktuelles/?seite=50").status_code == 404


def test_nur_eigene_beitraege_ohne_social_media(client, hubiplan, monkeypatch):
    hubiplan.info["blocks"]["posts"] = True
    hubiplan.info["posts"] = {"instagram": False, "facebook": False, "own": True}
    monkeypatch.setattr(fake, "POSTS", [])
    monkeypatch.setattr(fake, "OWN_POSTS", [fake._own(1, "Sommerfest", "2019-06-15")])
    assert ">Aktuelles</a>" in text(client.get("/"))
    html = text(client.get("/aktuelles/"))
    assert "Sommerfest" in html and "?kanal=" not in html


def test_alle_bilder_im_bildfenster(client, mit_beitraegen):
    """Alle Bilder eines Albums sind zu sehen und lassen sich im Bildfenster blättern."""
    html = text(client.get("/aktuelles/"))
    for i in range(3):
        assert f'class="beitrag-bildlink" href="/medien/a/posts/images/bild1x{i}/"' in html
    assert 'id="bild-fenster"' in html and "seite/bildfenster.js" in html
    js = Path("seite/static/seite/bildfenster.js").read_text(encoding="utf-8")
    assert "a.beitrag-bildlink" in js and ".beitrag-bilder" in js


def test_ohne_schalter_keine_zahlen_und_kommentare(client, mit_beitraegen):
    html = text(client.get("/aktuelles/"))
    assert "beitrag-zahlen" not in html and "beitrag-kommentare" not in html


def test_likes_und_kommentare(client, mit_beitraegen, monkeypatch):
    posts = [dict(p) for p in fake.POSTS]
    posts[0].update(
        likes=12,
        comment_count=1,
        comments=[
            {
                "author": "erika_m",
                "text": "Schön <i>war</i> es!",
                "published_at": "2026-10-12T13:00:00+00:00",
            }
        ],
    )
    posts[2].update(likes=1, comment_count=0, comments=[])
    monkeypatch.setattr(fake, "POSTS", posts)
    cache.clear()
    html = text(client.get("/aktuelles/"))
    assert "12 Likes · 1 Kommentar" in html
    assert "1 Reaktion · 0 Kommentare" in html
    assert "1 Kommentar lesen" in html and "<strong>erika_m</strong>" in html
    assert "Schön &lt;i&gt;war&lt;/i&gt; es!" in html
