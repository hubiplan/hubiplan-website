"""Brotkrumen-Streifen über Unterseiten nur, wenn kein Menüpunkt die Seite schon markiert
(Ralf 15.11.: der markierte Menüpunkt „Züge“ sagt dasselbe)."""

from .test_galerie import galerie  # noqa: F401
from .test_seiten import text


def test_zugseite_ohne_streifen_wenn_menue_markiert(client, hubiplan):
    hubiplan.info["nav"] = [{"key": "units", "label": "Züge"}]
    html = text(client.get("/zuege/jaeger/"))
    assert 'aria-current="page"' in html
    assert 'class="brotkrumen"' not in html


def test_zugseite_mit_streifen_ohne_menuepunkt(client, hubiplan):
    hubiplan.info["nav"] = [{"key": "events", "label": "Termine"}]
    html = text(client.get("/zuege/jaeger/"))
    assert '<p class="brotkrumen"><a href="/zuege/">' in html


def test_zugseite_mit_streifen_wenn_zuege_nur_im_fuss(client, hubiplan):
    hubiplan.info["nav"] = [{"key": "units", "label": "Züge", "place": "footer"}]
    html = text(client.get("/zuege/jaeger/"))
    assert 'class="brotkrumen"' in html


def test_album_oben_ohne_streifen(client, galerie):  # noqa: F811
    html = text(client.get("/galerie/2024/"))
    assert 'class="brotkrumen"' not in html


def test_unteralbum_zeigt_oberalbum(client, galerie):  # noqa: F811
    html = text(client.get("/galerie/schuetzenfest/"))
    assert 'class="brotkrumen"' in html and 'href="/galerie/2024/"' in html
