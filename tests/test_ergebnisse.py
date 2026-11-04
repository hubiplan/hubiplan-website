"""Wettbewerbsergebnisse auf der Webseite (Wettbewerbe Schritt 5; alles erfunden).

Ralf 2026-11-01: eigener Baustein „Ergebnisse“ und Block auf der Startseite; live fragt der
Browser alle 15 Sekunden nach dem Stand und lädt die Rangliste nur bei Änderung neu."""

from . import fake
from .fake import BASE, COMP, LIVE, SERIES


def text(response) -> str:
    return response.content.decode()


def mit_ergebnissen(hubiplan, home=None):
    hubiplan.info["results_url"] = BASE + "results/"
    hubiplan.info["nav"] = [{"key": "results", "label": "Ergebnisse", "children": []}]
    if home is not None:
        hubiplan.info["home"] = home


def test_ohne_modul_keine_seite(client, hubiplan):
    assert client.get("/ergebnisse/").status_code == 404
    assert client.get(f"/ergebnisse/{COMP}/").status_code == 404
    assert not any("results/" in c[1] for c in hubiplan.calls)


def test_uebersicht_und_menue(client, hubiplan):
    mit_ergebnissen(hubiplan)
    r = client.get("/ergebnisse/")
    html = text(r)
    assert r.status_code == 200
    assert 'href="/ergebnisse/" aria-current="page"' in html
    assert '<h2 id="aktuelles-ergebnis">Pokalschießen</h2>' in html
    assert "Max M." in html and "ohne Namen" in html
    assert "Gerade im Gange" not in html
    assert f'href="/ergebnisse/{LIVE}/"' not in html
    assert f'data-stand="/ergebnisse/{LIVE}/stand/"' in html
    assert f'data-tabelle="/ergebnisse/{LIVE}/tabelle/?eingebettet=1"' in html
    assert "ergebnisse.js" in html and "<h3>Einzel</h3>" in html
    assert r["Cache-Control"] == "no-cache"
    assert not any(f"results/{COMP}/" in c[1] for c in hubiplan.calls)
    assert f'href="/ergebnisse/{COMP}/"' in html
    assert "<h2>2027</h2>" in html
    assert f'href="/ergebnisse/reihe/{SERIES}/"' in html
    assert "Zugpokal" in html and "Zug 1" in html


def test_rangliste_endgueltig(client, hubiplan):
    mit_ergebnissen(hubiplan)
    html = text(client.get(f"/ergebnisse/{COMP}/"))
    assert "Max M." in html and "ohne Namen" in html and "(Nachbarverein)" in html
    assert "Vereinsmeister 2027" in html
    # Endgültig: kein Nachfragen
    assert "ergebnisse.js" not in html and "data-stand" not in html
    # Rangliste zu genau diesem Stand abgerufen
    assert any(f"results/{COMP}/?stand=v1" in c[1] for c in hubiplan.calls)


def test_live_stand_und_neue_tabelle(client, hubiplan):
    mit_ergebnissen(hubiplan)
    r = client.get(f"/ergebnisse/{LIVE}/")
    html = text(r)
    assert 'data-sekunden="15"' in html and 'data-version="v1"' in html
    assert f'data-stand="/ergebnisse/{LIVE}/stand/"' in html
    assert "ergebnisse.js" in html and ">Aktualisieren</a>" in html
    assert r["Cache-Control"] == "no-cache"
    stand = client.get(f"/ergebnisse/{LIVE}/stand/")
    assert stand.json() == {"version": "v1", "final": False}
    # Neues Ergebnis in HUBIplan → neuer Stand; die Tabelle kommt sofort neu (nicht aus
    # dem Zwischenspeicher), der Stand selbst höchstens wenige Sekunden alt
    from django.core.cache import cache

    hubiplan.versions[LIVE] = "v2"
    cache.clear()
    teil = client.get(f"/ergebnisse/{LIVE}/tabelle/")
    assert teil.status_code == 200 and "<html" not in text(teil) and "Max M." in text(teil)
    assert any(f"results/{LIVE}/?stand=v2" in c[1] for c in hubiplan.calls)


def test_reihe(client, hubiplan):
    mit_ergebnissen(hubiplan)
    html = text(client.get(f"/ergebnisse/reihe/{SERIES}/"))
    assert "Vereinsmeisterschaft" in html and "Karl F." in html
    assert f'<a href="/ergebnisse/{COMP}/">2027</a>' in html
    assert client.get(f"/ergebnisse/reihe/{'0' * 20}/").status_code == 404


def test_startseite_block(client, hubiplan):
    mit_ergebnissen(hubiplan, home=["greeting", "results"])
    html = text(client.get("/"))
    assert "Aktuelle Ergebnisse" in html and "1. Max M." in html
    assert 'href="/ergebnisse/">Alle Ergebnisse' in html
    # Ohne Block auf der Startseite: kein Abruf
    hubiplan.info["home"] = ["greeting"]
    from django.core.cache import cache

    cache.clear()
    hubiplan.calls.clear()
    assert "Aktuelle Ergebnisse" not in text(client.get("/"))
    assert not any("results/" in c[1] for c in hubiplan.calls)


def test_neuestes_abgeschlossenes_schiessen_direkt(client, hubiplan, monkeypatch):
    mit_ergebnissen(hubiplan)
    overview = fake.results_overview()
    overview["competitions"].reverse()  # Neuester Eintrag laut öffentlicher Schnittstelle.
    monkeypatch.setattr(fake, "results_overview", lambda: overview)
    html = text(client.get("/ergebnisse/"))
    assert '<h2 id="aktuelles-ergebnis">Vereinsmeisterschaft 2027</h2>' in html
    assert "Vereinsmeister 2027" in html and "Max M." in html
    assert f'href="/ergebnisse/{COMP}/"' not in html
    assert f'href="/ergebnisse/{LIVE}/"' in html
    assert "Gerade im Gange" in html
    assert "ergebnisse.js" not in html and "data-stand" not in html
    assert not any(f"results/{LIVE}/" in c[1] for c in hubiplan.calls)


def test_einziges_schiessen_zeigt_ergebnisse_ohne_leermeldung(client, hubiplan, monkeypatch):
    mit_ergebnissen(hubiplan)
    overview = fake.results_overview()
    overview.update(competitions=overview["competitions"][1:], series=[], trophies=[])
    monkeypatch.setattr(fake, "results_overview", lambda: overview)
    html = text(client.get("/ergebnisse/"))
    assert "Max M." in html and "Vereinsmeister 2027" in html
    assert "Hier stehen noch keine Ergebnisse." not in html
    assert f'href="/ergebnisse/{COMP}/"' not in html


def test_leeres_ergebnisarchiv(client, hubiplan, monkeypatch):
    mit_ergebnissen(hubiplan)
    monkeypatch.setattr(fake, "results_overview", lambda: {})
    response = client.get("/ergebnisse/")
    assert response.status_code == 200
    assert "Hier stehen noch keine Ergebnisse." in text(response)
    assert 'id="ergebnis"' not in text(response)
    assert not any("/version/" in c[1] for c in hubiplan.calls)


def test_preisplatz_hinweis_und_eingebettetes_nachladen(client, hubiplan, monkeypatch):
    mit_ergebnissen(hubiplan)
    original = fake.results_detail

    def limited(token, version="v1"):
        data = original(token, version)
        scoring = data["scorings"][0]
        scoring.update(complete=False, rows=scoring["rows"][:2])
        return data

    monkeypatch.setattr(fake, "results_detail", limited)
    for url in (
        "/ergebnisse/",
        f"/ergebnisse/{LIVE}/",
        f"/ergebnisse/{LIVE}/tabelle/?eingebettet=1",
    ):
        html = text(client.get(url))
        assert "Gezeigt sind die Preisplätze von 4 Teilnehmenden." in html
        assert "Plätze 1 bis 3" not in html
        assert "Gerd G." not in html
        if "tabelle" in url:
            assert "<h3>Einzel</h3>" in html and "<h2>Einzel</h2>" not in html
    assert "<h2>Einzel</h2>" in text(client.get(f"/ergebnisse/{LIVE}/tabelle/"))
