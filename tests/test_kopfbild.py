"""Kopfbild statt Wappen und Name, Schriften für Designpakete (Ralf 05.11.2026, erfunden)."""

from pathlib import Path

from . import fake

STATIC = Path(__file__).resolve().parents[1] / "seite" / "static" / "seite"


def text(response) -> str:
    return response.content.decode()


def test_ohne_kopfbild_wappen_und_name(client, hubiplan):
    html = text(client.get("/"))
    assert 'class="marke marke-bild"' not in html
    assert "/medien/m/logos/wappen.png" in html


def test_kopfbild_ersetzt_wappen_und_name(client, hubiplan):
    hubiplan.info["header_image"] = {
        "key": "banner",
        "url": f"{fake.BASE}images/banner-v2/",
        "small_url": f"{fake.BASE}images/banner-v2/?size=small",
        "width": 1200,
        "height": 300,
        "caption": "",
        "alt": "Schützenverein Musterdorf 1900",
    }
    html = text(client.get("/"))
    kopf = html.split('<header class="kopf">', 1)[1].split("</header>", 1)[0]
    assert '<a class="marke marke-bild" href="/">' in kopf
    assert 'src="/medien/a/images/banner-v2/"' in kopf
    assert 'alt="Schützenverein Musterdorf 1900"' in kopf
    assert 'width="1200" height="300"' in kopf
    # Wappen und Name stehen nicht zusätzlich daneben
    assert "logos/wappen.png" not in kopf
    assert "hubiplan.example" not in html
    # Das Bild kommt über diese Seite
    assert client.get("/medien/a/images/banner-v2/").status_code == 200


def test_schriften_liegen_lokal():
    css = (STATIC / "seite.css").read_text()
    for name in ("open-sans", "roboto"):
        for weight in (400, 600, 700):
            assert f'url("schriften/{name}-{weight}.woff2")' in css
            assert (STATIC / "schriften" / f"{name}-{weight}.woff2").stat().st_size > 1000
        assert "SIL Open Font License" in (STATIC / "schriften" / f"OFL-{name}.txt").read_text()
    # Keine Schrift von fremden Servern
    assert "fonts.googleapis" not in css and "http" not in css.split("@font-face", 1)[1][:2000]
