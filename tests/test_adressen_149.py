"""Lesbare Adressen für Würden, Wettbewerbe und Reihen (Webseite #149; alles erfunden).

HUBIplan liefert je Eintrag eine lesbare Adresse („slug“) und frühere Adressen („aliases“).
Aufrufe über die Kennung oder eine frühere Adresse leiten dauerhaft (301) weiter."""

from . import fake
from .fake import COMP, SERIES
from .test_ergebnisse import mit_ergebnissen

WUERDE = "d" * 20


def text(response) -> str:
    return response.content.decode()


def _wuerde_mit_adresse(hubiplan, monkeypatch):
    koenig = {**fake.HONORS["dignities"][0], "slug": "koenige", "aliases": ["koenig"]}
    monkeypatch.setitem(fake.HONORS, "dignities", [koenig])
    hubiplan.info["honors_menu"] = {
        "label": "Würdenträger",
        "dignities": [{"id": WUERDE, "label": "Könige", "slug": "koenige"}],
        "honorary": False,
    }


def test_wuerde_unter_lesbarer_adresse(client, hubiplan, monkeypatch):
    _wuerde_mit_adresse(hubiplan, monkeypatch)
    r = client.get("/majestaeten/koenige/")
    assert r.status_code == 200
    assert "Karl Krone" in text(r)
    assert 'href="/majestaeten/koenige/">Könige</a>' in text(r)
    assert f"/majestaeten/{WUERDE}/" not in text(r)


def test_alte_adressen_leiten_dauerhaft_weiter(client, hubiplan, monkeypatch):
    _wuerde_mit_adresse(hubiplan, monkeypatch)
    for alt in (WUERDE, "koenig"):
        r = client.get(f"/majestaeten/{alt}/")
        assert r.status_code == 301
        assert r["Location"] == "/majestaeten/koenige/"
    assert client.get("/majestaeten/unbekannt/").status_code == 404


def test_wuerde_ohne_adresse_bleibt_bei_der_kennung(client, hubiplan):
    r = client.get(f"/majestaeten/{WUERDE}/")
    assert r.status_code == 200 and "Karl Krone" in text(r)


def test_unbrauchbare_adresse_wird_nicht_verlinkt(client, hubiplan):
    hubiplan.info["honors_menu"] = {
        "label": "Würdenträger",
        "dignities": [{"id": WUERDE, "label": "Könige", "slug": "Kö nige/"}],
        "honorary": False,
    }
    assert f'href="/majestaeten/{WUERDE}/">Könige</a>' in text(client.get("/"))


def _wettbewerb_mit_adresse(hubiplan, monkeypatch):
    mit_ergebnissen(hubiplan)
    detail, series, overview = fake.results_detail, fake.results_series, fake.results_overview

    def mit_slug(token, version="v1"):
        return {**detail(token, version), "slug": "vm-2027"} if token == COMP else detail(token)

    def reihe():
        data = series()
        data["slug"] = "vereinsmeisterschaft"
        data["years"][0]["slug"] = "vm-2027"
        return data

    def uebersicht():
        data = overview()
        for c in data["competitions"]:
            if c["id"] == COMP:
                c["slug"] = "vm-2027"
        data["series"][0]["slug"] = "vereinsmeisterschaft"
        return data

    monkeypatch.setattr(fake, "results_detail", mit_slug)
    monkeypatch.setattr(fake, "results_series", reihe)
    monkeypatch.setattr(fake, "results_overview", uebersicht)
    echt = hubiplan.results

    def results(base, rest):
        # HUBIplan findet Wettbewerb und Reihe auch über die lesbare Adresse
        for slug, token in (("vm-2027", COMP), ("vereinsmeisterschaft", SERIES)):
            base, rest = (
                base.replace(f"/{slug}/", f"/{token}/"),
                rest.replace(f"/{slug}/", f"/{token}/"),
            )
        return echt(base, rest)

    monkeypatch.setattr(hubiplan, "results", results)


def test_wettbewerb_unter_lesbarer_adresse(client, hubiplan, monkeypatch):
    _wettbewerb_mit_adresse(hubiplan, monkeypatch)
    r = client.get("/ergebnisse/vm-2027/")
    assert r.status_code == 200
    assert "Vereinsmeisterschaft 2027" in text(r)
    alt = client.get(f"/ergebnisse/{COMP}/")
    assert alt.status_code == 301 and alt["Location"] == "/ergebnisse/vm-2027/"


def test_uebersicht_und_reihe_verlinken_lesbar(client, hubiplan, monkeypatch):
    _wettbewerb_mit_adresse(hubiplan, monkeypatch)
    html = text(client.get("/ergebnisse/"))
    assert 'href="/ergebnisse/vm-2027/"' in html
    assert 'href="/ergebnisse/reihe/vereinsmeisterschaft/"' in html
    alt = client.get(f"/ergebnisse/reihe/{SERIES}/")
    assert alt.status_code == 301 and alt["Location"] == "/ergebnisse/reihe/vereinsmeisterschaft/"
    reihe = text(client.get("/ergebnisse/reihe/vereinsmeisterschaft/"))
    assert 'href="/ergebnisse/vm-2027/"' in reihe


def test_fremde_zeichen_in_der_adresse(client, hubiplan):
    mit_ergebnissen(hubiplan)
    assert client.get("/ergebnisse/VM_2027/").status_code == 404
    assert client.get("/ergebnisse/vm--2027/").status_code == 404
