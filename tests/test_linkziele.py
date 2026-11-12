"""Linkziele aus der Schnittstelle nur als http(s) (Gesamtaudit 11.11.2026, H-01).

Adressen, die HUBIplan liefert, laufen in den Vorlagen durch ``web_ziel`` (oder in der
Ansicht durch ``web_ziel``, ``site.local`` bzw. ``_extern``). So wird aus einem
``javascript:``-Wert nie ein Link. Alle Daten sind erfunden.
"""

import json
import re
from pathlib import Path

import pytest
from django.core.cache import cache

from seite import api

from . import fake

VORLAGEN = Path(__file__).resolve().parent.parent / "seite" / "templates"

# Linkziele in Vorlagen, die schon geprüft oder auf der Webseite selbst gebaut sind.
# Neue Linkziele aus der Schnittstelle bitte mit ``|web_ziel`` ausgeben statt sie hier
# einzutragen.
GEPRUEFT = {
    "ziel",  # {% with ziel=…|web_ziel %} oder Telefonnummer aus |tel
    "link",  # {% with link=…|web_ziel %}
    "route",  # {% with route=…|web_ziel %}
    "homepage",  # einheit.html gibt unit.homepage|web_ziel weiter
    "z.url",  # {% ziel %}: _extern bzw. reverse()
    "c.url",  # Menü: _nav_url (_extern bzw. reverse())
    "p.url",  # Menü: _nav_url (_extern bzw. reverse())
    "datei",  # {% lokal %}: nur Adressen über diese Seite
    "gross",  # {% lokal %}
    "a.url",  # Presse: site.local
    "d.url",  # Dokumente: site.local bzw. web_ziel in der Ansicht
    "h.url",  # Suche: _search_url (reverse())
    "webcal_url",  # auf der Webseite gebaut
}

HREF = re.compile(r'href="\{\{\s*([^}|]+?)\s*(\|[^}]*)?\}\}"')


def test_alle_linkziele_in_vorlagen_sind_geprueft():
    offen = []
    for datei in sorted(VORLAGEN.rglob("*.html")):
        for ausdruck, filter_ in HREF.findall(datei.read_text()):
            if "web_ziel" in (filter_ or "") or ausdruck in GEPRUEFT:
                continue
            offen.append(f"{datei.relative_to(VORLAGEN)}: {ausdruck}{filter_}")
    assert offen == [], "Linkziel ohne web_ziel: " + ", ".join(offen)


BOESE = "javascript:alert(1)"
JS_LINK = re.compile(r'href="\s*javascript:', re.I)


@pytest.fixture
def boese(hubiplan, monkeypatch):
    """Schnittstelle liefert überall, wo Adressen stehen, ein javascript:-Ziel."""
    hubiplan.info["member_of"] = {"name": "Bürgerverein Musterdorf", "website": BOESE}
    hubiplan.info["social"] = [
        {"kind": "instagram", "label": "Instagram", "url": BOESE, "display": "@sv"},
        {"kind": "facebook", "label": "Facebook", "url": "https://facebook.example/sv"},
    ]
    hubiplan.info["statute_url"] = BOESE
    hubiplan.info["fee_rules_url"] = "https://hubiplan.example/beitragsordnung/abc/"
    hubiplan.info["blocks"]["posts"] = True
    hubiplan.info["posts"] = {"instagram": True, "facebook": True}
    beitraege = [dict(p) for p in fake.POSTS]
    beitraege[0]["permalink"] = BOESE
    beitraege[1]["permalink"] = "https://www.instagram.com/p/beispiel2/"
    monkeypatch.setattr(fake, "POSTS", beitraege)

    echt = hubiplan.__call__

    def antwort(method, path, **kwargs):
        r = echt(method, path, **kwargs)
        if path.endswith("/imprint/") and r.status == 200:
            data = json.loads(r.body)
            data["mode"] = "link"
            data["external_url"] = BOESE
            data["privacy"] = {"mode": "link", "url": BOESE, "text": ""}
            return fake.FakeHubiplan.json(data)
        return r

    monkeypatch.setattr(api, "_request", antwort)
    cache.clear()
    return hubiplan


@pytest.mark.parametrize(
    "pfad", ["/", "/aktuelles/", "/dokumente/", "/impressum/", "/datenschutz/"]
)
def test_javascript_ziele_werden_keine_links(client, boese, pfad):
    r = client.get(pfad)
    assert r.status_code == 200
    html = r.content.decode()
    assert not JS_LINK.search(html), pfad


def test_gute_ziele_bleiben_links(client, boese):
    html = client.get("/").content.decode()
    assert "Bürgerverein Musterdorf" in html
    assert 'href="https://facebook.example/sv"' in html
    assert "sm-instagram" not in html
    html = client.get("/aktuelles/").content.decode()
    assert 'href="https://www.instagram.com/p/beispiel2/"' in html
    html = client.get("/dokumente/").content.decode()
    assert 'href="https://hubiplan.example/beitragsordnung/abc/"' in html
    assert "<strong>Satzung</strong>" not in html
