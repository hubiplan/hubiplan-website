"""Designpakete: Export der Standarddesigns, eingespielte Designs zeichnen (erfundene Daten)."""

import io
import json
import zipfile

import pytest
from django.core.cache import cache

from seite import designpaket
from seite.site import DESIGNS

from .test_designs import ROLLEN

KATALOG = {
    k: {"label": str(v), "hint": "Beschreibung", "roles": {"header": [0], "footer": "dark"}}
    for k, v in DESIGNS.items()
}

KOPF = """{% load seite i18n %}<header class="kopf paket-kopf"><a class="marke" href="{% url 'start' %}">
<span>{{ site.info.name }}</span></a>{% if punkte %}<nav class="menue-breit" aria-label="{% translate "Hauptmenü" %}"><ul>{% for p in punkte %}<li><a href="{{ p.url }}">{{ p.label }}</a></li>{% endfor %}</ul></nav>{% endif %}</header>"""  # noqa: E501
START = """{% extends "seite/start.html" %}
{% block bausteine %}<div class="paket-start">{% for vorlage in sections %}{% include vorlage %}{% endfor %}</div>{% endblock %}"""  # noqa: E501


def text(response) -> str:
    return response.content.decode()


def paket(**over):
    data = {
        "version": 1,
        "key": "hubertus",
        "hash": "abc123def4567890",
        "label": "Hubertus",
        "css": ".paket-kopf { padding: 2rem; }",
        "templates": {"seite/kopf.html": KOPF, "seite/start.html": START},
    }
    data.update(over)
    return data


@pytest.fixture
def mit_paket(hubiplan):
    designpaket._compiled.clear()
    hubiplan.info["design"] = "hubertus"
    hubiplan.info["designs"] = {k: dict(ROLLEN) for k in [*DESIGNS, "hubertus"]}
    hubiplan.info["design_packages"] = {
        "hubertus": {"label": "Hubertus", "hash": "abc123def4567890"}
    }
    hubiplan.info["design_catalog"] = KATALOG
    hubiplan.packages["hubertus"] = paket()
    yield hubiplan
    designpaket._compiled.clear()


def test_paket_wird_gezeichnet(client, mit_paket):
    html = text(client.get("/"))
    assert 'class="design-hubertus"' in html
    assert "paket-kopf" in html and "paket-start" in html
    assert "/design/hubertus.css?v=abc123def4567890" in html
    # Fuß bleibt der Standard, Unterseiten ebenso
    assert "Impressum</a>" in html
    for path in ("/vorstand/", "/termine/", "/kontakt/", "/impressum/"):
        r = client.get(path)
        assert r.status_code == 200, path
        assert "paket-kopf" in text(r)


def test_paket_css(client, mit_paket):
    r = client.get("/design/hubertus.css?v=abc123def4567890")
    assert r.status_code == 200
    assert r["Content-Type"].startswith("text/css")
    assert "max-age=86400" in r["Cache-Control"]
    assert text(r) == ".paket-kopf { padding: 2rem; }"
    assert client.get("/design/gibtsnicht.css").status_code == 404


def test_paket_nur_einmal_geholt(client, mit_paket):
    """Gleicher Stand (Hash) = gleicher Inhalt: Das Paket wird nicht bei jedem Aufruf neu
    bei HUBIplan geholt, auch nicht in der Vorschau. Neuer Stand → neu holen."""

    def abrufe():
        return sum(1 for c in mit_paket.calls if c[1].endswith("/design/hubertus/"))

    client.get("/")
    assert abrufe() == 1
    cache.clear()  # auch ohne Zwischenspeicher der Antworten (z. B. Vorschau)
    client.get("/vorstand/")
    client.get("/design/hubertus.css?v=abc123def4567890")
    assert abrufe() == 1
    cache.clear()
    mit_paket.info["design_packages"]["hubertus"]["hash"] = "neu0000000000000"
    mit_paket.packages["hubertus"] = paket(hash="neu0000000000000")
    assert "/design/hubertus.css?v=neu0000000000000" in text(client.get("/"))
    assert abrufe() == 2


@pytest.mark.parametrize(
    "over",
    [
        {"css": "body { background: url(https://boese.example/x) }"},
        {"css": "@import 'x';"},
        {"templates": {"seite/kopf.html": "<script>alert(1)</script>"}},
        {"templates": {"seite/kopf.html": "{{ site.info.name|safe }}"}},
        {"templates": {"seite/kopf.html": "{% load log %}"}},
        {"templates": {"seite/termine.html": "<p>x</p>"}},
        {"templates": {"seite/kopf.html": "{% if %}"}},
    ],
)
def test_boeses_paket_zeigt_klassisch(client, mit_paket, over):
    mit_paket.packages["hubertus"] = paket(**over)
    html = text(client.get("/"))
    assert 'class="design-classic"' in html
    assert "<script>alert(1)" not in html and "boese.example" not in html
    assert "/design/hubertus.css" not in html


def test_nicht_freigegebenes_paket_zeigt_klassisch(client, mit_paket):
    mit_paket.info["design_packages"] = {}
    assert 'class="design-classic"' in text(client.get("/"))


def test_fehlendes_paket_zeigt_klassisch(client, mit_paket):
    mit_paket.packages.clear()
    assert 'class="design-classic"' in text(client.get("/"))


def _entpacken(data: bytes) -> dict:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        return {n: z.read(n).decode() for n in z.namelist()}


@pytest.mark.parametrize("key", list(DESIGNS))
def test_export_der_standarddesigns(client, hubiplan, key):
    hubiplan.info["design_catalog"] = KATALOG
    r = client.get(f"/design-paket/{key}.zip")
    assert r.status_code == 200
    assert r["Content-Type"] == "application/zip"
    files = _entpacken(r.content)
    manifest = json.loads(files["design.json"])
    assert manifest["format"] == designpaket.FORMAT and manifest["key"] == key
    assert manifest["quelle"] == key and manifest["roles"] == KATALOG[key]["roles"]
    # Alles im Paket besteht die eigene Prüfung
    assert designpaket.css_ok(files["design.css"])
    for name, body in files.items():
        if name.startswith("vorlagen/"):
            assert name in designpaket.TEMPLATES and designpaket.template_ok(body), name
    if key in ("newspaper", "stage"):
        assert "vorlagen/start.html" in files


def test_export_klassisch_mit_menueleiste(client, hubiplan):
    """Das neue Klassisch bringt nur CSS mit (helle Menüleiste), keine eigenen Vorlagen."""
    hubiplan.info["design_catalog"] = KATALOG
    files = _entpacken(client.get("/design-paket/classic.zip").content)
    assert set(files) == {"design.json", "design.css"}
    assert ".menue-breit" in files["design.css"]


def test_export_nur_standarddesigns(client, hubiplan):
    hubiplan.info["design_catalog"] = KATALOG
    assert client.get("/design-paket/hubertus.zip").status_code == 404
    hubiplan.info.pop("design_catalog")
    cache.clear()
    assert client.get("/design-paket/classic.zip").status_code == 404


def test_exportierter_fuss_besteht_pruefung():
    """Kopf und Fuß der Webseite taugen als Vorlage eines Pakets (Paket ersetzt sie)."""
    from django.template.loader import get_template

    for name in ("seite/fuss.html", "seite/kopf.html"):
        with open(get_template(name).origin.name, encoding="utf-8") as fh:
            assert designpaket.template_ok(fh.read()), name


def test_vorschau_eines_pakets(client, mit_paket):
    mit_paket.info["design"] = "classic"
    mit_paket.info["preview"] = True
    client.cookies["vorschau"] = mit_paket.preview_session
    client.cookies["vorschau-design"] = "hubertus"
    html = text(client.get("/"))
    assert 'class="design-hubertus"' in html
    assert "Hubertus" in html
