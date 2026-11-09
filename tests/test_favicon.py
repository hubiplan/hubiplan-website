"""Wappen als Favicon und Handy-Symbol (Ralf 09.11.2026, erfundene Daten)."""


def text(response) -> str:
    return response.content.decode()


def test_ohne_symbol_kein_favicon(client, hubiplan):
    html = text(client.get("/"))
    assert 'rel="icon"' not in html
    assert 'rel="apple-touch-icon"' not in html


def test_favicon_und_handysymbol(client, hubiplan):
    hubiplan.info["icon"] = True
    html = text(client.get("/"))
    assert '<link rel="icon" type="image/png" sizes="32x32" href="/medien/a/icon-32.png">' in html
    assert 'sizes="192x192" href="/medien/a/icon-192.png"' in html
    assert '<link rel="apple-touch-icon" href="/medien/a/icon-180.png">' in html
    r = client.get("/medien/a/icon-32.png")
    assert r.status_code == 200
    assert r["Content-Type"] == "image/png"
    # Nur die Größen, die HUBIplan liefert
    assert client.get("/medien/a/icon-64.png").status_code == 404
    assert client.get("/medien/a/icon-32.png/").status_code == 404


def test_favicon_auch_auf_der_wartungsseite(client, hubiplan):
    hubiplan.info["icon"] = True
    hubiplan.maintenance = True
    r = client.get("/")
    assert r.status_code == 503
    assert 'href="/medien/a/icon-32.png"' in text(r)
    assert client.get("/medien/a/icon-180.png").status_code == 200


def test_favicon_ico_leitet_weiter(client, hubiplan):
    r = client.get("/favicon.ico")
    assert r.status_code == 302
    assert r["Location"] == "/medien/a/icon-32.png"
    # Ohne Symbol in HUBIplan: 404 statt eines fremden Zeichens
    assert client.get(r["Location"]).status_code == 404
