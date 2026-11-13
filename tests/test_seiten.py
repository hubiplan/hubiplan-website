"""Seiten der Webseite mit erfundenen Daten aus einer nachgebildeten Schnittstelle."""

import re
from pathlib import Path

import pytest
from django.core.cache import cache

from . import fake
from .fake import KEY


def text(response) -> str:
    return response.content.decode()


def test_startseite(client, hubiplan):
    r = client.get("/")
    assert r.status_code == 200
    html = text(r)
    assert "Schützenverein Musterdorf 1900" in html
    assert "<strong>Welt</strong>" in html
    # Rohes HTML aus dem Text wird nicht übernommen
    assert "<script>alert" not in html
    # Bilder laufen über diese Seite, nicht direkt zu HUBIplan
    assert "/medien/a/images/festbild1/?size=small" in html
    assert "/medien/m/logos/wappen.png" in html
    assert "hubiplan.example/media" not in html
    # Farben aus HUBIplan
    assert "--primaer:#123456" in html
    # Nur künftige Termine
    assert "Schützenfest" in html
    assert "Alter Termin" not in html
    assert "Termin von Bürgerverein Musterdorf" in html
    assert "Karl Krone" in html
    assert 'href="/zuege/jaeger/"' in html
    assert r["Content-Security-Policy"].startswith("default-src 'self'")
    assert "https://hubiplan.example" in r["Content-Security-Policy"]
    # Fußzeile verlinkt die GitHub-Organisation hubiplan, in neuem Fenster
    assert (
        'Daten aus <a href="https://github.com/hubiplan" '
        'target="_blank" rel="noopener noreferrer">HUBIplan<'
    ) in html
    # AGPL § 13: Quellcode der Webseite
    assert (
        '<a href="https://github.com/hubiplan/hubiplan-website" '
        'rel="noopener noreferrer">Quellcode</a>' in html
    )


def test_menue(client, hubiplan):
    html = text(client.get("/vorstand/"))
    labels = ("Termine", "Vorstand", "Züge", "Majestäten", "Chronik", "Ämter", "Anfahrt", "Kontakt")
    for label in labels:
        assert f">{label}</a>" in html
    assert 'href="/vorstand/" aria-current="page"' in html


def test_bereich_aus(client, hubiplan):
    hubiplan.info["blocks"]["honors"] = False
    assert client.get("/majestaeten/").status_code == 404
    assert ">Majestäten</a>" not in text(client.get("/"))


def test_vorstand(client, hubiplan):
    html = text(client.get("/vorstand/"))
    assert "Max Muster" in html
    assert "max@musterdorf.example" in html
    assert "Zurzeit nicht besetzt" in html
    assert "/kontakt/?an=" in html
    assert "Erika Beispiel" in html
    # Ehrungen ohne Datum (Ralf 2026-10-29)
    assert "seit 1.5.2010" not in html
    assert f"/medien/a/photos/{'a' * 20}/" in html
    # Nur eine Ehrung: sein Name ist die Überschrift (Ralf 2026-10-30)
    assert "<h2>Ehrenmitglied</h2>" in html
    assert "<h2>Ehrungen</h2>" not in html


def test_vorstand_ehrung_mehrzahl(client, hubiplan, monkeypatch):
    """Ralf 2026-10-31: mehrere Träger → Überschrift in der Mehrzahl (von HUBIplan)."""
    ehrung = {
        "title": "Ehrenmitglied",
        "heading": "Ehrenmitglieder",
        "holders": [{"name": "Erika Beispiel"}, {"name": "Otto Beispiel"}],
    }
    monkeypatch.setitem(fake.BOARD, "honorary", [ehrung])
    html = text(client.get("/vorstand/"))
    assert "<h2>Ehrenmitglieder</h2>" in html


def test_vorstand_mehrere_ehrungen(client, hubiplan, monkeypatch):
    major = {"title": "Ehrenmajor", "holders": [{"name": "Otto Beispiel", "photo_url": None}]}
    monkeypatch.setitem(fake.BOARD, "honorary", [*fake.BOARD["honorary"], major])
    html = text(client.get("/vorstand/"))
    assert "<h2>Ehrungen</h2>" in html
    assert "<h3>Ehrenmitglied</h3>" in html
    assert "<h3>Ehrenmajor</h3>" in html


def test_termine_mit_abo(client, hubiplan):
    html = text(client.get("/termine/"))
    assert "Juni 2099" in html
    assert "Schützenfest" in html
    assert "Alter Termin" not in html
    # Datum steht nur im Kästchen, sichtbar bleibt der Wochentag (Ralf 2026-10-29)
    assert "Montag, 18:00 Uhr bis 23:00 Uhr" in html
    assert '<span class="nur-vorlesen">1. Juni 2099, </span>' in html
    assert '<small class="termin-jahr">2099</small>' in html
    # Ort und Beschreibung nur im Fenster, das ein Klick auf die Karte öffnet (Ralf 2026-10-31)
    assert "termin-mehr" not in html
    assert 'class="termin-knopf" aria-haspopup="dialog" data-termin="termin-e1-' in html
    fenster = html[html.index('<dialog id="termin-e1-') :]
    fenster = fenster[: fenster.index("</dialog>")]
    assert "Montag, 1. Juni 2099, 18:00 Uhr bis 23:00 Uhr" in fenster
    assert "<strong>Ort:</strong> Festzelt" in fenster
    assert "Mit Musik" in fenster
    assert "Termin von Bürgerverein Musterdorf" in fenster
    assert html.index("Festzelt") > html.index("<dialog")
    assert "seite/termin.js" in html
    assert f"webcal://hubiplan.example/api/public/site/v1/{KEY}/events.ics" in html
    assert "<svg" in html


def test_termine_auswahl_mit_einheiten(client, hubiplan):
    assert 'name="einheit"' in text(client.get("/termine/"))


def test_termine_auswahl_nur_einheiten_mit_terminen(client, hubiplan):
    hubiplan.info["units"][0]["has_events"] = False
    assert 'name="einheit"' not in text(client.get("/termine/"))


def test_termine_filter_unsauber(client, hubiplan):
    assert client.get("/termine/?einheit=../x").status_code == 200
    assert not any("einheit=../x" in c[1] for c in hubiplan.calls)


def test_einheiten(client, hubiplan):
    assert "Jägerzug" in text(client.get("/zuege/"))


def test_einheiten_ohne_wappen_gleicher_platz(client, hubiplan):
    """Ralf 2026-10-31: Namen beginnen alle auf einer Höhe, auch ohne Wappen."""
    html = text(client.get("/zuege/"))
    assert html.count('class="wappen-platz"') + html.count('width="60" height="60"') >= 1
    html = text(client.get("/zuege/jaeger/"))
    assert "<em>der</em>" in html
    assert "Karl Krone" in html
    assert client.get("/zuege/gibtsnicht/").status_code == 404


def test_einheiten_heissen_einheiten(client, hubiplan):
    hubiplan.info["unit_label_plural"] = "Abteilungen"
    html = text(client.get("/"))
    assert 'href="/einheiten/jaeger/"' in html
    assert ">Abteilungen</a>" in html


def test_majestaeten(client, hubiplan):
    html = text(client.get("/majestaeten/"))
    assert "Karl Krone" in html
    assert "(2. Mal)" in html
    assert "Klara Krone" in html
    assert "Otto Ober" in html


def test_majestaeten_nur_eine_wuerde_ohne_ueberschrift(client, hubiplan):
    """Ralf 2026-10-30: bei nur einer Würde reicht ihr Name, ohne „Majestäten“ darüber."""
    hubiplan.info["honors_label"] = "Könige"
    html = text(client.get("/majestaeten/"))
    # mehrere Regentschaften: Mehrzahl, auch im Menü
    assert "<h1>Könige</h1>" in html
    assert ">Könige</a>" in html
    assert "<h1>Majestäten</h1>" not in html
    assert "<h2>König</h2>" not in html
    assert ">Majestäten</a>" not in html


def test_majestaeten_eine_regentschaft_einzahl(client, hubiplan, monkeypatch):
    koenig = {**fake.HONORS["dignities"][0]}
    koenig["reigns"] = koenig["reigns"][:1]
    monkeypatch.setitem(fake.HONORS, "dignities", [koenig])
    assert "<h1>König</h1>" in text(client.get("/majestaeten/"))


def test_chronik_ohne_begleitung_ohne_spalte(client, hubiplan, monkeypatch):
    """Ralf 2026-10-30: ohne Begleitpersonen keine Spalte „Begleitung“."""
    assert ">Begleitung</th>" not in text(client.get("/majestaeten/"))
    koenig = {**fake.HONORS["dignities"][0]}
    koenig["reigns"] = [
        {**koenig["reigns"][0], "companions": [{"label": "Königin", "name": "Klara Krone"}]},
        *koenig["reigns"][1:],
    ]
    monkeypatch.setitem(fake.HONORS, "dignities", [koenig])
    cache.clear()  # Antworten der Schnittstelle werden zwischengespeichert
    html = text(client.get("/majestaeten/"))
    assert ">Begleitung</th>" in html
    assert "<td>Klara Krone</td>" in html


def test_ohne_traeger_im_laufenden_jahr_alle_offen(client, hubiplan, monkeypatch):
    """Ralf 2026-10-31: kein Träger aus dem laufenden Jahr, dann alle zeigen."""
    koenig = {**fake.HONORS["dignities"][0], "current_year": False}
    monkeypatch.setitem(fake.HONORS, "dignities", [koenig])
    html = text(client.get("/majestaeten/"))
    assert '<details class="chronik"' not in html
    assert 'class="majestaet"' not in html
    assert '<table class="zeitliste">' in html
    for r in koenig["reigns"]:
        assert r["holder"]["name"] in html


def test_startseite_nur_traeger_im_laufenden_jahr(client, hubiplan, monkeypatch):
    """Ralf 2026-10-31: Startseite zeigt nur Würdenträger des laufenden Jahres."""
    koenig = {**fake.HONORS["dignities"][0], "current_year": True}
    alt = {**koenig, "id": "p" * 20, "name": "Prinz", "current_year": False}
    monkeypatch.setitem(fake.HONORS, "dignities", [koenig, alt])
    html = text(client.get("/"))
    assert "Unsere Majestäten" in html
    assert "<h2>König</h2>" in html
    assert "<h2>Prinz</h2>" not in html
    monkeypatch.setitem(fake.HONORS, "dignities", [alt])
    cache.clear()
    assert "Unsere Majestäten" not in text(client.get("/"))


def test_majestaeten_mehrere_wuerden(client, hubiplan, monkeypatch):
    prinz = {**fake.HONORS["dignities"][0], "id": "p" * 20, "name": "Prinz"}
    monkeypatch.setitem(fake.HONORS, "dignities", [*fake.HONORS["dignities"], prinz])
    html = text(client.get("/majestaeten/"))
    assert "<h1>Majestäten</h1>" in html
    assert "<h2>König</h2>" in html and "<h2>Prinz</h2>" in html


def test_geschichte_menue(client, hubiplan):
    """Ralf 2026-10-31: Menü „Geschichte“ mit „Chronik“ und „Ämter“."""
    html = text(client.get("/"))
    assert '<details class="untermenue"><summary>Geschichte</summary>' in html
    assert '<a href="/chronik/">Chronik</a>' in html
    assert '<a href="/aemter/">Ämter</a>' in html
    assert ">Geschichte</a>" not in html


def test_chronik(client, hubiplan):
    html = text(client.get("/chronik/"))
    assert "Seit 1900." in html
    assert "Alt Vorsitz" not in html
    assert client.get("/seite/geschichte/")["Location"] == "/chronik/"
    assert client.get("/geschichte/")["Location"] == "/chronik/"


def _ereignis(jahr, titel, bis=None, **mehr):
    return {
        "kind": "event",
        "year": jahr,
        "until": bis,
        "title": titel,
        "text": "",
        "image": None,
        **mehr,
    }


def test_chronik_zeitleiste(client, hubiplan):
    """Ralf 02.11.: Chronik als Zeitleiste, Zeitraum statt Jahr, Bild zum Vergrößern."""
    bild = {
        "key": "fahne1",
        "url": f"{fake.BASE}images/fahne1/",
        "small_url": f"{fake.BASE}images/fahne1/?size=small",
        "width": 60,
        "height": 40,
        "caption": "Die neue Fahne",
        "alt": "Fahne mit Wappen",
    }
    hubiplan.info["zeitleiste"] = [
        _ereignis(1900, "Gründung", text="Zwölf Schützen."),
        _ereignis(1939, "Ruhezeit", bis=1948),
        _ereignis(1995, "Neue Fahne", image=bild),
    ]
    html = text(client.get("/chronik/"))
    assert "Seit 1900." in html
    assert '<ol class="zeitleiste-liste">' in html
    assert "<h3>Gründung</h3>" in html and "Zwölf Schützen." in html
    # Zeitraum ist als solcher gekennzeichnet
    assert '<li class="zeitleiste-eintrag ist-zeitraum">' in html
    assert "Zeitraum </span>1939–1948" in html
    # Bild klein in der Karte, groß über einen Link (mit JavaScript im Fenster)
    assert 'href="/medien/a/images/fahne1/"' in html
    assert 'src="/medien/a/images/fahne1/?size=small"' in html
    assert 'data-unterschrift="Die neue Fahne"' in html
    assert 'alt="Fahne mit Wappen"' in html
    assert 'id="bild-fenster"' in html and "bildfenster.js" in html
    # Ohne Kapitel und mit wenigen Einträgen keine Sprungmarken
    assert "zeitleiste-sprung" not in html


def test_chronik_mehrere_bilder(client, hubiplan):
    """Ralf 02.11.: mehrere Bilder je Ereignis, klein nebeneinander, groß zum Blättern."""

    def plakat(n):
        return {
            "key": f"plakat{n}",
            "url": f"{fake.BASE}images/plakat{n}/",
            "small_url": f"{fake.BASE}images/plakat{n}/?size=small",
            "width": 40,
            "height": 60,
            "caption": "",
            "alt": f"Plakat {n}",
        }

    plakate = [plakat(n) for n in (2020, 2021, 2022)]
    hubiplan.info["zeitleiste"] = [
        _ereignis(2020, "Verschobenes Jubiläum", bis=2022, images=plakate, image=plakate[0]),
        # Älterer HUBIplan-Stand: nur ein Bild als „image“
        _ereignis(1995, "Neue Fahne", image=plakat(1995)),
    ]
    html = text(client.get("/chronik/"))
    assert '<div class="zeitleiste-bilder mehrere">' in html
    assert "mehrere-bilder" in html
    stellen = [html.index(f'href="/medien/a/images/plakat{n}/"') for n in (2020, 2021, 2022)]
    assert stellen == sorted(stellen)
    assert html.count('href="/medien/a/images/plakat2020/"') == 1
    assert 'href="/medien/a/images/plakat1995/"' in html
    assert '<div class="zeitleiste-bilder">' in html
    # Blättern im Fenster
    assert "Nächstes Bild" in html and 'data-vorlage="Bild {n} von {m}"' in html


def test_chronik_bildposition(client, hubiplan):
    """Ralf 02.11.: Bildposition je Ereignis, Standard abwechselnd (beginnend rechts)."""

    def mit_bild(jahr, lage=None):
        bild = {"url": f"{fake.BASE}images/b{jahr}/", "small_url": f"{fake.BASE}images/b{jahr}/"}
        mehr = {"image_position": lage} if lage else {}
        return _ereignis(jahr, f"E{jahr}", images=[bild], **mehr)

    hubiplan.info["zeitleiste"] = [
        mit_bild(1920),
        _ereignis(1925, "Ohne Bild"),
        mit_bild(1930),
        mit_bild(1940, "below"),
        mit_bild(1950),
        mit_bild(1960, "left"),
    ]
    html = text(client.get("/chronik/"))
    lagen = re.findall(r'<div class="zeitleiste-karte( bild-\w+)?">', html)
    assert lagen == [
        " bild-rechts",
        "",
        " bild-links",
        " bild-unten",
        " bild-rechts",
        " bild-links",
    ]


def test_chronik_ohne_zeitleiste(client, hubiplan):
    html = text(client.get("/chronik/"))
    assert "zeitleiste" not in html


def test_chronik_kapitel(client, hubiplan):
    """Kapitel als Zwischenüberschriften; Ereignisse davor ohne Überschrift oben."""
    hubiplan.info["zeitleiste"] = [
        _ereignis(1899, "Vorgeschichte"),
        {**_ereignis(1900, "Gründerjahre", bis=1938), "kind": "chapter"},
        _ereignis(1900, "Gründung"),
        {**_ereignis(1939, "Krieg und Neubeginn", bis=1949), "kind": "chapter"},
        _ereignis(1949, "Neuanfang"),
    ]
    html = text(client.get("/chronik/"))
    # Reihenfolge in der Zeitleiste selbst (Sprungmarken stehen davor)
    leiste = html[html.index('<div class="zeitleiste">') :]
    assert leiste.index("Vorgeschichte") < leiste.index("Gründerjahre") < leiste.index("Gründung")
    assert '<section class="zeitleiste-abschnitt" id="kapitel-2"' in html
    assert '<span class="zeitleiste-zeitraum">1900–1938</span> Gründerjahre</h2>' in html
    # Sprungmarken zu den Kapiteln
    assert '<a href="#kapitel-2">Gründerjahre' in html
    assert '<a href="#kapitel-3">Krieg und Neubeginn' in html


def test_zeitleiste_jahrzehnte():
    from seite.zeitleiste import gliedern

    eintraege = [_ereignis(1920 + i * 3, f"E{i}") for i in range(15)]
    z = gliedern(eintraege)
    assert [m["label"] for m in z["sprungmarken"]][:3] == ["1920er", "1930er", "1940er"]
    assert z["abschnitte"][0]["ereignisse"][0]["anker"] == "jahrzehnt-1920"
    # Unter 15 Einträgen keine Sprungmarken
    assert gliedern(eintraege[:14])["sprungmarken"] == []
    # Ohne Jahr oder Überschrift fällt ein Eintrag weg
    assert gliedern([_ereignis(None, "x"), _ereignis(1950, "")])["abschnitte"] == []


def test_chronik_neueste_oben(client, hubiplan):
    """Wahlweise neueste Einträge oben: Kapitel, Ereignisse und Sprungmarken rückwärts."""
    hubiplan.info["zeitleiste_neueste_oben"] = True
    hubiplan.info["zeitleiste"] = [
        _ereignis(1899, "Vorgeschichte"),
        {**_ereignis(1900, "Gründerjahre", bis=1938), "kind": "chapter"},
        _ereignis(1900, "Gründung"),
        _ereignis(1925, "Erste Fahne"),
        {**_ereignis(2020, "Bis heute"), "kind": "chapter"},
        _ereignis(2021, "Jubiläum"),
        _ereignis(2025, "Neues Zelt"),
    ]
    html = text(client.get("/chronik/"))
    leiste = html[html.index('<div class="zeitleiste">') :]
    reihe = ["Bis heute", "Neues Zelt", "Jubiläum", "Gründerjahre", "Erste Fahne", "Gründung"]
    reihe.append("Vorgeschichte")
    stellen = [leiste.index(t) for t in reihe]
    assert stellen == sorted(stellen)
    # Kapitel behalten ihre Nummer; Sprungmarken rückwärts
    assert '<section class="zeitleiste-abschnitt" id="kapitel-3"' in html
    assert html.index('<a href="#kapitel-3">') < html.index('<a href="#kapitel-2">')
    # Kapitel ohne eigenes Ende zeigen den Zeitraum bis zum letzten Ereignis, mit eigenem Ende
    # bleibt es dabei
    assert '<span class="zeitleiste-zeitraum">2020–2025</span> Bis heute</h2>' in html
    assert '<span class="zeitleiste-zeitraum">1900–1938</span> Gründerjahre</h2>' in html
    assert '<a href="#kapitel-3">Bis heute <span class="klein">2020–2025</span>' in html


def test_zeitleiste_rueckwaerts():
    from seite.zeitleiste import gliedern

    eintraege = [
        {**_ereignis(2020, "Bis heute"), "kind": "chapter"},
        _ereignis(2021, "A"),
        _ereignis(2025, "B", bis=2026),
    ]
    vor = gliedern(eintraege)
    assert vor["abschnitte"][0]["ende"] == 2026
    # Alt nach neu bleibt das Kapitel beim Startjahr
    assert vor["abschnitte"][0]["kapitel"]["zeitraum"] == "2020"
    rueck = gliedern(eintraege, neueste_oben=True)
    assert [e["title"] for e in rueck["abschnitte"][0]["ereignisse"]] == ["B", "A"]
    # Jahrzehnte rückwärts, Anker am neuesten Ereignis des Jahrzehnts
    z = gliedern([_ereignis(1920 + i * 3, f"E{i}") for i in range(15)], neueste_oben=True)
    assert [m["label"] for m in z["sprungmarken"]][:2] == ["1960er", "1950er"]
    assert z["abschnitte"][0]["ereignisse"][0]["anker"] == "jahrzehnt-1960"
    assert z["abschnitte"][0]["ereignisse"][0]["year"] == 1962


def test_aemter(client, hubiplan):
    html = text(client.get("/aemter/"))
    assert "<h1>Ämter</h1>" in html
    assert "Alt Vorsitz" in html
    # Nur Jahre (Ralf 2026-10-31)
    assert "2000 bis 2019" in html
    assert "1.1.2000" not in html
    assert "2020 bis heute" in html
    # Gleiche Spaltenbreiten in allen Listen (Ralf 2026-10-31)
    assert '<table class="zeitliste">' in html
    # Ein Block je Amt (Ralf 2026-10-31)
    assert '<div class="karten aemter">' in html
    assert '<section class="karte">' in html
    assert "Seit 1900." not in html


def test_nur_aemter(client, hubiplan):
    """Ohne Chronik steht „Ämter“ direkt im Menü; /geschichte/ führt dorthin."""
    hubiplan.info["blocks"]["history"] = False
    hubiplan.info["blocks"]["offices"] = True
    html = text(client.get("/"))
    assert '<a href="/aemter/">Ämter</a>' in html
    assert "<summary>Geschichte</summary>" not in html
    assert client.get("/chronik/").status_code == 404
    assert client.get("/geschichte/")["Location"] == "/aemter/"


def test_aemter_ohne_inhalt(client, hubiplan):
    hubiplan.info["has_offices"] = False
    html = text(client.get("/"))
    assert '<a href="/chronik/">Chronik</a>' in html
    assert "<summary>Geschichte</summary>" not in html


def test_aemter_aus(client, hubiplan):
    hubiplan.info["blocks"]["offices"] = False
    assert client.get("/aemter/").status_code == 404
    assert "/aemter/" not in text(client.get("/"))


def test_geschichte_aus(client, hubiplan):
    """Schalter „Chronik“ und „Ämter“ aus: kein Menüpunkt, alte Adresse 404."""
    hubiplan.info["blocks"]["history"] = False
    hubiplan.info["blocks"]["offices"] = False
    html = text(client.get("/"))
    assert "Geschichte" not in html and "/chronik/" not in html
    assert client.get("/geschichte/").status_code == 404


def test_geschichte_ohne_schalter_wie_vorstand(client, hubiplan):
    """Ältere HUBIplan-Stände ohne Schalter „Geschichte“: wie bisher über „Vorstand“."""
    del hubiplan.info["blocks"]["history"]
    hubiplan.info["blocks"]["board"] = False
    assert "/chronik/" not in text(client.get("/"))
    assert client.get("/geschichte/").status_code == 404


def test_aemter_ohne_schalter_wie_geschichte(client, hubiplan):
    """Ältere HUBIplan-Stände ohne „offices“: Ämter folgen dem Schalter „Geschichte“."""
    assert "offices" not in hubiplan.info["blocks"]
    assert client.get("/aemter/").status_code == 200
    hubiplan.info["blocks"]["history"] = False
    cache.clear()
    assert client.get("/aemter/").status_code == 404


def test_textseite(client, hubiplan):
    assert "Mit dem Bus." in text(client.get("/seite/anfahrt/"))
    assert client.get("/seite/gibtsnicht/").status_code == 404


def test_kontakt(client, hubiplan):
    r = client.get("/kontakt/?an=" + "r1" * 10)
    html = text(r)
    assert r["Cache-Control"] == "private, no-store"
    assert f'data-ziel="https://hubiplan.example/api/public/site/v1/{KEY}/contact/"' in html
    assert 'data-salz="salz"' in html
    assert 'data-vorschau=""' in html
    # Feste Vorauswahl statt Auswahlfeld (Ralf 31.10.)
    assert "<select" not in html
    assert f'name="recipient" value="{"r1" * 10}"' in html
    assert '<strong id="k-an">1. Vorsitzender</strong>' in html


def test_kontakt_ohne_herkunft_an_den_verein(client, hubiplan):
    for url in ("/kontakt/", "/kontakt/?an=unbekannt"):
        html = text(client.get(url))
        assert "<select" not in html
        assert 'name="recipient" value="allgemein"' in html
        assert '<strong id="k-an">Verein</strong>' in html
        assert "an Verein;" in html


def test_impressum_und_datenschutz(client, hubiplan):
    html = text(client.get("/impressum/"))
    assert "VR 1234" in html
    assert "Max Muster (1. Vorsitzender)" in html
    # Adresszusatz steht über Straße und Hausnummer
    assert "c/o Vereinsheim Musterdorf<br>Dorfstraße 1<br>" in html
    html = text(client.get("/datenschutz/"))
    assert "<h2>Datenschutz</h2>" in html
    assert "Stand: 1.10.2026" not in html  # Stand steht schon im Text aus HUBIplan


def test_unbekannte_domain(client, hubiplan):
    r = client.get("/", HTTP_HOST="fremd.example")
    assert r.status_code == 404


def test_hubiplan_nicht_erreichbar(client, hubiplan, monkeypatch):
    from seite import api

    def kaputt(*args, **kwargs):
        raise api.Unavailable("weg")

    monkeypatch.setattr(api, "_request", kaputt)
    r = client.get("/")
    assert r.status_code == 503
    assert "Gerade nicht erreichbar" in text(r)


def test_zwischenspeicher(client, hubiplan):
    client.get("/vorstand/")
    n = len(hubiplan.calls)
    client.get("/vorstand/")
    assert len(hubiplan.calls) == n


def test_host_override(client, hubiplan, settings):
    settings.SITE_HOST_OVERRIDE = "www.musterdorf.test"
    assert client.get("/", HTTP_HOST="fremd.example").status_code == 200


def test_robots(client, hubiplan):
    assert "Allow: /" in text(client.get("/robots.txt"))
    hubiplan.info["allow_indexing"] = False
    from django.core.cache import cache

    cache.clear()
    assert "Disallow: /" in text(client.get("/robots.txt"))
    assert client.get("/").get("X-Robots-Tag") == "noindex"


@pytest.mark.parametrize(
    "path",
    [
        "/medien/a/images/festbild1/?size=small",
        f"/medien/a/photos/{'a' * 20}/",
        f"/medien/a/honors/photos/{'b' * 20}/",
        "/medien/m/logos/wappen.png",
    ],
)
def test_medien(client, hubiplan, path):
    r = client.get(path)
    assert r.status_code == 200
    assert r["Content-Type"] == "image/png"
    assert "sandbox" in r["Content-Security-Policy"]


@pytest.mark.parametrize(
    "path",
    [
        "/medien/a/board/",
        "/medien/a/contact/",
        "/medien/m/../settings.py",
        "/medien/m/geheim.txt",
        "/medien/x/images/abcd/",
    ],
)
def test_medien_nur_bilder(client, hubiplan, path):
    assert client.get(path).status_code == 404


def test_medien_ueber_caddy(client, hubiplan, settings):
    settings.HUBIPLAN_MEDIA_URL = "https://hubiplan.example"
    assert client.get("/medien/m/logos/wappen.png").status_code == 200
    assert hubiplan.bases[-1] == "https://hubiplan.example"
    client.get("/vorstand/")
    assert hubiplan.bases[-1] is None


def test_gesund(client, hubiplan):
    assert client.get("/gesund").content == b"ok\n"
    assert not hubiplan.calls


def test_vorschau_ohne_schraegstrich(client, hubiplan):
    r = client.get("/vorschau?schluessel=gut")
    assert r.status_code == 302
    assert r.cookies["vorschau"].value == hubiplan.preview_session


def test_unter_pfad(client, hubiplan, settings):
    """Testserver: Seite unter /webseite (Caddy entfernt den Pfad vor dem Weiterleiten)."""
    from django.urls import set_script_prefix

    settings.FORCE_SCRIPT_NAME = "/webseite"
    settings.BASE_PATH = "/webseite"
    # Der Testclient setzt das Präfix nicht selbst (anders als der WSGI-Handler)
    set_script_prefix("/webseite/")
    html = text(client.get("/"))
    assert 'href="/webseite/termine/"' in html
    assert "/webseite/medien/m/logos/wappen.png" in html
    r = client.get("/vorschau/?schluessel=gut")
    assert r["Location"] == "/webseite/"
    assert r.cookies["vorschau"]["path"] == "/webseite/"
    set_script_prefix("/")


def test_social_media_praesent(client, hubiplan):
    html = text(client.get("/"))
    assert "Folgt uns" not in html  # nur im Kopf, nicht auf der Startseite
    for kind in ("instagram", "facebook", "tiktok", "x"):
        assert f"sm-{kind}" in html
    # Kopf und Handy-Menü, nicht noch einmal im Fuß
    assert html.count('href="https://tiktok.example/@sv"') == 2
    assert 'aria-label="TikTok: @sv (öffnet in neuem Fenster)"' in html


def test_ohne_social_media_kein_block(client, hubiplan):
    hubiplan.info["social"] = []
    html = text(client.get("/"))
    assert "Folgt uns" not in html
    assert "sozial-symbole" not in html


def test_dokumente(client, hubiplan):
    assert client.get("/dokumente/").status_code == 404
    assert ">Dokumente</a>" not in text(client.get("/"))
    hubiplan.info["statute_url"] = "https://hubiplan.example/satzung/abc/"
    from django.core.cache import cache

    cache.clear()
    html = text(client.get("/dokumente/"))
    assert "Satzung" in html
    assert 'href="https://hubiplan.example/satzung/abc/"' in html
    assert ">Dokumente</a>" in html
    # Die Satzung steht nicht in der Chronik
    assert "satzung/abc" not in text(client.get("/chronik/"))


def test_dokumente_mit_vorschau(client, hubiplan):
    """Statt des Symbols die erste Seite der Satzung als Bild, über diese Seite geladen."""
    hubiplan.info["statute_url"] = "https://hubiplan.example/satzung/abc/"
    hubiplan.info["statute_preview_url"] = (
        f"https://hubiplan.example/api/public/site/v1/{KEY}/statute/preview/"
    )
    html = text(client.get("/dokumente/"))
    assert 'src="/medien/a/statute/preview/"' in html
    assert "dok-symbol" not in html
    r = client.get("/medien/a/statute/preview/")
    assert r.status_code == 200 and r["Content-Type"] == "image/png"


def test_dokumente_beitragsordnung(client, hubiplan):
    """Beitragsordnung (optional) neben der Satzung; allein reicht sie für „Dokumente“."""
    hubiplan.info["fee_rules_url"] = "https://hubiplan.example/beitragsordnung/xyz/"
    hubiplan.info["fee_rules_preview_url"] = (
        f"https://hubiplan.example/api/public/site/v1/{KEY}/fee-rules/preview/"
    )
    html = text(client.get("/dokumente/"))
    assert "Beitragsordnung" in html
    assert 'href="https://hubiplan.example/beitragsordnung/xyz/"' in html
    assert 'src="/medien/a/fee-rules/preview/"' in html
    assert ">Dokumente</a>" in html
    assert "Satzung" not in html
    r = client.get("/medien/a/fee-rules/preview/")
    assert r.status_code == 200 and r["Content-Type"] == "image/png"
    # Mit Satzung: beide, Satzung zuerst
    hubiplan.info["statute_url"] = "https://hubiplan.example/satzung/abc/"
    from django.core.cache import cache

    cache.clear()
    html = text(client.get("/dokumente/"))
    assert html.index("Satzung") < html.index("Beitragsordnung")


def test_dokumente_gruendungsurkunde(client, hubiplan):
    """Gründungsurkunde (optional): allein reicht sie für „Dokumente“, sonst als letzte."""
    hubiplan.info["founding_deed_url"] = "https://hubiplan.example/urkunde/xyz/"
    hubiplan.info["founding_deed_preview_url"] = (
        f"https://hubiplan.example/api/public/site/v1/{KEY}/founding-deed/preview/"
    )
    html = text(client.get("/dokumente/"))
    assert "Gründungsurkunde" in html
    assert 'href="https://hubiplan.example/urkunde/xyz/"' in html
    assert 'src="/medien/a/founding-deed/preview/"' in html
    assert ">Dokumente</a>" in html
    assert "Satzung" not in html and "Beitragsordnung" not in html
    r = client.get("/medien/a/founding-deed/preview/")
    assert r.status_code == 200 and r["Content-Type"] == "image/png"
    hubiplan.info["statute_url"] = "https://hubiplan.example/satzung/abc/"
    hubiplan.info["fee_rules_url"] = "https://hubiplan.example/beitragsordnung/abc/"
    from django.core.cache import cache

    cache.clear()
    html = text(client.get("/dokumente/"))
    assert html.index("Satzung") < html.index("Beitragsordnung") < html.index("Gründungsurkunde")


def test_startseite_ohne_doppelten_namen(client, hubiplan):
    """Der Name steht im Kopf; die Überschrift der Startseite ist nur für Screenreader."""
    hubiplan.info["greeting"] = None
    html = text(client.get("/"))
    assert '<h1 class="nur-vorlesen">' in html


def test_bilderkarussell(client, hubiplan):
    """Mit zwei oder mehr Bildern zeigt die Begrüßung ein Karussell statt eines Bildes."""
    bild = {
        "key": "festbild1",
        "url": f"https://hubiplan.example/api/public/site/v1/{KEY}/images/festbild1/",
        "small_url": "",
        "width": 800,
        "height": 400,
        "caption": "",
        "alt": "Festzug",
    }
    hubiplan.info["greeting"] = {
        "title": "Willkommen",
        "text": "Hallo",
        "image": None,
        "gallery": [bild, {**bild, "alt": "Zelt"}],
    }
    html = text(client.get("/"))
    assert 'aria-roledescription="Karussell"' in html
    assert html.count('src="/medien/a/images/festbild1/"') == 2
    assert 'alt="Zelt"' in html and 'aria-label="2 von 2"' in html
    assert "karussell.js" in html
    assert 'data-takt="7"' in html  # ältere HUBIplan-Fassung ohne Angabe: Standard


def test_bilderkarussell_wechselzeit(client, hubiplan):
    bild = {
        "key": "festbild1",
        "url": f"https://hubiplan.example/api/public/site/v1/{KEY}/images/festbild1/",
        "small_url": "",
        "width": 800,
        "height": 400,
        "caption": "",
        "alt": "Festzug",
    }
    hubiplan.info["greeting"] = {
        "title": "Willkommen",
        "text": "",
        "image": None,
        "gallery": [bild, bild],
        "gallery_interval": 12,
    }
    html = text(client.get("/"))
    assert 'data-takt="12"' in html and "data-zufall" not in html
    hubiplan.info["units"][0]["gallery"] = [bild, bild]
    hubiplan.info["units"][0]["gallery_interval"] = 4
    hubiplan.info["units"][0]["gallery_random"] = True
    cache.clear()
    html = text(client.get("/zuege/jaeger/"))
    assert 'data-takt="4"' in html and "data-zufall" in html


def test_ein_bild_ohne_karussell(client, hubiplan):
    html = text(client.get("/"))
    assert "Karussell" not in html and "karussell.js" not in html


def test_bilderkarussell_der_einheit(client, hubiplan):
    bild = {
        "key": "festbild1",
        "url": f"https://hubiplan.example/api/public/site/v1/{KEY}/images/festbild1/",
        "small_url": "",
        "width": 800,
        "height": 400,
        "caption": "",
        "alt": "Zugbild",
    }
    hubiplan.info["units"][0]["gallery"] = [bild, bild]
    html = text(client.get("/zuege/jaeger/"))
    assert 'aria-roledescription="Karussell"' in html
    assert "karussell.js" in html


def test_startseite_reihenfolge_aus_hubiplan(client, hubiplan):
    """Bausteine erscheinen in der Reihenfolge aus HUBIplan; ausgeschaltete fehlen."""
    hubiplan.info["home"] = ["units", "greeting", "instagram", "unbekannt"]
    html = text(client.get("/"))
    assert html.index('href="/zuege/jaeger/"') < html.index("<strong>Welt</strong>")
    assert "Schützenfest" not in html and "Karl Krone" not in html
    # Bild der Begrüßung gehört zum Baustein „Bilderkarussell“
    assert "titelbild" not in html
    haupt = html[html.index("<main") : html.index("</main>")]
    assert "<h1>Willkommen</h1>" in haupt and "nur-vorlesen" not in haupt


def test_startseite_ohne_willkommenstext_mit_karussell(client, hubiplan):
    bild = {
        "key": "festbild1",
        "url": f"https://hubiplan.example/api/public/site/v1/{KEY}/images/festbild1/",
        "small_url": "",
        "width": 800,
        "height": 400,
        "caption": "",
        "alt": "Festzug",
    }
    hubiplan.info["greeting"] = {
        "title": "Willkommen",
        "text": "Hallo",
        "image": None,
        "gallery": [bild, bild],
    }
    hubiplan.info["home"] = ["events", "carousel"]
    html = text(client.get("/"))
    assert 'aria-roledescription="Karussell"' in html and "karussell.js" in html
    assert html.index("Schützenfest") < html.index("Karussell")
    assert "<h1>Willkommen</h1>" not in html and '<h1 class="nur-vorlesen">' in html


def test_startseite_leer(client, hubiplan):
    hubiplan.info["home"] = []
    html = text(client.get("/"))
    assert "titelbild" not in html and "Schützenfest" not in html
    assert '<h1 class="nur-vorlesen">' in html


def _gruppiert(hubiplan, honorary=True):
    """Menü „Würdenträger“ (Ralf 2026-10-31): Unterpunkte je Würde und „Ehrungen“."""
    hubiplan.info["honors_menu"] = {
        "label": "Würdenträger",
        "dignities": [
            {"id": "d" * 20, "label": "Könige"},
            {"id": "b" * 20, "label": "Bundeskönig"},
        ],
        "honorary": honorary,
        "honorary_label": "Ehrenmitglied" if honorary else None,
    }


def test_menue_wuerdentraeger(client, hubiplan):
    _gruppiert(hubiplan)
    html = text(client.get("/"))
    assert '<details class="untermenue"><summary>Würdenträger</summary>' in html
    assert f'href="/majestaeten/{"d" * 20}/">Könige</a>' in html
    assert 'href="/ehrungen/">Ehrenmitglied</a>' in html
    assert ">Majestäten</a>" not in html
    # Handymenü: Gruppe mit eingerückten Unterpunkten
    assert '<span class="menue-gruppe">Würdenträger</span>' in html


def test_menue_wuerdentraeger_nur_ein_unterpunkt(client, hubiplan):
    hubiplan.info["honors_menu"] = {
        "label": "Würdenträger",
        "dignities": [{"id": "d" * 20, "label": "Könige"}],
        "honorary": False,
    }
    html = text(client.get("/"))
    assert "Würdenträger</summary>" not in html
    assert f'href="/majestaeten/{"d" * 20}/">Könige</a>' in html


def test_seite_einer_wuerde(client, hubiplan):
    _gruppiert(hubiplan)
    html = text(client.get(f"/majestaeten/{'d' * 20}/"))
    assert "Karl Krone" in html
    assert '<summary class="aktiv">Würdenträger</summary>' in html
    assert client.get(f"/majestaeten/{'e' * 20}/").status_code == 404


def test_ehrungen_eigene_seite(client, hubiplan):
    _gruppiert(hubiplan)
    html = text(client.get("/ehrungen/"))
    assert "<h1>Ehrenmitglied</h1>" in html
    assert "Erika Beispiel" in html
    # Auf der Vorstandsseite dann keine Ehrungen mehr
    assert "<h2>Ehrenmitglied</h2>" not in text(client.get("/vorstand/"))


def test_ehrungen_ohne_menue(client, hubiplan):
    assert client.get("/ehrungen/").status_code == 404


def test_weitergegebene_wuerde_mit_herkunft(client, hubiplan, monkeypatch):
    buerger = {**fake.HONORS["dignities"][0], "id": "b" * 20, "name": "Bundeskönig"}
    buerger["owner"] = "Bürgerverein Musterdorf"
    monkeypatch.setitem(fake.HONORS, "dignities", [*fake.HONORS["dignities"], buerger])
    html = text(client.get("/majestaeten/"))
    assert "Bundeskönig" in html
    # Kein Hinweis „Würde von …: unsere Träger“ (Ralf 31.10.)
    assert "unsere Träger" not in html


def test_menue_aus_hubiplan(client, hubiplan):
    """Ralf 2026-10-31: Reihenfolge und Unterpunkte legt HUBIplan fest (per Ziehen)."""
    hubiplan.info["nav"] = [
        {"key": "contact", "label": "Kontakt"},
        {
            "key": "events",
            "label": "Termine",
            "children": [
                {"key": "board", "label": "Vorstand"},
                {"key": "page", "label": "Anfahrt", "slug": "anfahrt"},
            ],
        },
        {
            "key": "group:history",
            "label": "Geschichte",
            "heading": True,
            "children": [{"key": "history", "label": "Chronik"}],
        },
        {"key": "unbekannt", "label": "Neu"},
    ]
    html = text(client.get("/"))
    kontakt = html.index('href="/kontakt/"')
    termine = html.index('<details class="untermenue"><summary>Termine</summary>')
    assert kontakt < termine
    # Termine selbst steht zuerst im Aufklappmenü, dann die Unterpunkte
    sub = html[termine : html.index("</details>", termine)]
    assert sub.index('href="/termine/"') < sub.index('href="/vorstand/"')
    assert 'href="/seite/anfahrt/"' in sub
    # Überschrift mit nur einem Unterpunkt: direkt im Menü
    assert '<a href="/chronik/">Chronik</a>' in html
    assert "<summary>Geschichte</summary>" not in html
    assert ">Neu<" not in html


def test_menue_link_nach_aussen_und_knopf(client, hubiplan):
    """Ralf 2026-11-10: Links nach außen im Menü (neuer Tab) und ein Punkt als Knopf."""
    hubiplan.info["nav"] = [
        {"key": "contact", "label": "Kontakt"},
        {
            "key": "link",
            "label": "Mitglied werden",
            "url": "https://www.example.org/beitritt",
            "button": True,
        },
        {
            "key": "events",
            "label": "Termine",
            "children": [
                {"key": "link", "label": "Dachverband", "url": "https://verband.example.org/"}
            ],
        },
        {"key": "link", "label": "Böse", "url": "javascript:alert(1)"},
        {"key": "link", "label": "Ohne Adresse"},
    ]
    html = text(client.get("/kontakt/"))
    assert (
        '<a href="https://www.example.org/beitritt" class="menue-knopf" target="_blank" '
        'rel="noopener noreferrer">Mitglied werden<span class="nur-vorlesen">'
    ) in html
    assert (
        '<a href="https://verband.example.org/" target="_blank" '
        'rel="noopener noreferrer">Dachverband' in html
    )
    # Nur vollständige http(s)-Adressen
    assert "javascript:" not in html
    assert ">Böse<" not in html and "Ohne Adresse" not in html
    # Der Knopf ist nie „aktiv“; Kontakt bleibt die aktuelle Seite
    assert '<a href="/kontakt/" aria-current="page">Kontakt</a>' in html
    assert html.count('class="menue-knopf"') == 2  # breites Menü und Handymenü


def test_eigene_namen_der_bausteine(client, hubiplan):
    """Ralf 2026-11-01: eigener Name eines Bausteins steht in Menü, Überschrift und Titel."""
    hubiplan.info["nav"] = [
        {"key": "events", "label": "Unsere Feste"},
        {"key": "board", "label": "Vorstand"},
    ]
    hubiplan.info["names"] = {"events": "Unsere Feste", "units": "Unsere Züge", "contact": " "}
    html = text(client.get("/termine/"))
    assert '<a href="/termine/" aria-current="page">Unsere Feste</a>' in html
    assert "<h1>Unsere Feste</h1>" in html
    assert "<title>Unsere Feste ·" in html
    assert "<h1>Unsere Züge</h1>" in text(client.get("/zuege/"))
    # Leer oder ohne Eintrag: Standardname
    assert "<h1>Vorstand</h1>" in text(client.get("/vorstand/"))
    assert "<h1>Kontakt</h1>" in text(client.get("/kontakt/"))


def test_homepage_der_einheit(client, hubiplan):
    """Eigene Homepage der Einheit: Link in neuem Tab, nur wenn HUBIplan sie liefert."""
    assert "Homepage" not in text(client.get("/zuege/jaeger/"))
    cache.clear()
    hubiplan.info["units"][0]["homepage"] = "https://www.jaegerzug.example/"
    html = text(client.get("/zuege/jaeger/"))
    # Eigene Karte im Abschnitt Kontakt neben den Ansprechpartnern, nicht im Kopf
    assert "<h2>Kontakt</h2>" in html
    assert '<section class="karte homepage">' in html
    assert ">www.jaegerzug.example<" in html
    assert (
        '<a class="knopf klein-knopf" href="https://www.jaegerzug.example/" target="_blank" '
        'rel="noopener noreferrer">Zur Homepage' in html
    )
    assert "öffnet in neuem Fenster" in html
    kopf, kontakt = html.index('class="einheit-kopf"'), html.index("<h2>Kontakt</h2>")
    assert kopf < kontakt < html.index("karte homepage")
    # Ohne Vorschaubild steht die Adresse in der Karte
    assert 'class="homepage-bild"' not in html
    # Mit Vorschaubild: Überschrift, Bild, Knopf – ohne Adresszeile
    cache.clear()
    hubiplan.info["units"][0]["homepage_image"] = (
        "https://hubiplan.example/media/homepages/5-20261031.jpg"
    )
    html = text(client.get("/zuege/jaeger/"))
    assert 'class="homepage-bild"' in html
    assert '<img src="/medien/m/homepages/5-20261031.jpg" alt=""' in html
    assert '<p class="klein">www.jaegerzug.example</p>' not in html
    assert "Zur Homepage" in html
    # Andere Schemata werden nie zum Link
    cache.clear()
    hubiplan.info["units"][0]["homepage"] = "javascript:alert(1)"
    html = text(client.get("/zuege/jaeger/"))
    assert "javascript:" not in html and "karte homepage" not in html


def test_aktuelles_foto_gross_nur_auf_eigener_seite(client, hubiplan):
    """Ralf 2026-10-31: nur der aktuelle Träger auf der Seite, also großes Foto."""
    assert '<section class="wuerde voll">' in text(client.get("/majestaeten/"))
    assert '<section class="wuerde voll">' in text(client.get(f"/majestaeten/{'d' * 20}/"))
    start = text(client.get("/"))
    assert '<section class="wuerde">' in start
    assert "wuerde voll" not in start
    css = (Path(__file__).parent.parent / "seite/static/seite/seite.css").read_text()
    assert ".wuerde.voll .majestaet img { width: min(28rem, 100%); }" in css


def test_quellcode_der_laufenden_fassung(tmp_path, monkeypatch):
    from seite.templatetags import seite as tags

    sha = "0123456789abcdef0123456789abcdef01234567"
    datei = tmp_path / ".fassung"
    datei.write_text(sha + "\n")
    monkeypatch.setattr(tags, "FASSUNG", datei)
    tags._fassung.cache_clear()
    try:
        assert tags.quellcode() == f"https://github.com/hubiplan/hubiplan-website/tree/{sha}"
        datei.write_text("kein commit")
        tags._fassung.cache_clear()
        assert tags.quellcode() == "https://github.com/hubiplan/hubiplan-website"
    finally:
        tags._fassung.cache_clear()


def test_chronik_bilder_neben_dem_text_groesser():
    """Ralf 2026-11-02: Bilder links oder rechts vom Text größer, aber höchstens 40 % der Karte."""
    css = (Path(__file__).parent.parent / "seite/static/seite/seite.css").read_text()
    spalte = "min(15rem, 40%)"
    assert f".bild-rechts {{ grid-template-columns: minmax(0, 1fr) {spalte}; }}" in css
    assert f".bild-links {{ grid-template-columns: {spalte} minmax(0, 1fr); }}" in css
    mehrere = "min(24rem, 50%)"
    assert f".mehrere-bilder {{ grid-template-columns: minmax(0, 1fr) {mehrere}; }}" in css


def test_bilderkarussell_kleine_fassung(client, hubiplan):
    """Große Bilder bieten dem Browser die kleine Fassung (800 px) an, etwa fürs Handy."""
    base = f"https://hubiplan.example/api/public/site/v1/{KEY}/images/festbild1-v2/"
    bild = {
        "key": "festbild1",
        "url": base,
        "small_url": base + "?size=small",
        "width": 2000,
        "height": 1000,
        "caption": "",
        "alt": "Festzug",
    }
    hubiplan.info["greeting"] = {
        "title": "Willkommen",
        "text": "Hallo",
        "image": None,
        "gallery": [bild, bild],
    }
    html = text(client.get("/"))
    assert (
        'srcset="/medien/a/images/festbild1-v2/?size=small 800w, '
        '/medien/a/images/festbild1-v2/ 2000w"'
    ) in html


def test_bilder_browser_zwischenspeicher(client, hubiplan):
    """Adressen, die sich bei jeder Änderung ändern, darf der Browser lange behalten."""
    r = client.get("/medien/m/logos/abteilungen/8-20261031200030.png")
    assert r["Cache-Control"] == "public, max-age=31536000, immutable"
    assert client.get("/medien/m/logos/wappen.png")["Cache-Control"] == "public, max-age=600"
    r = client.get("/medien/a/images/festbild1-v2/")
    assert r["Cache-Control"] == "public, max-age=86400"
    r = client.get("/medien/a/images/festbild1/")
    assert r["Cache-Control"] == "public, max-age=600"


def test_linkedin_eigenes_symbol(client, hubiplan):
    from seite.templatetags.seite import ICONS

    hubiplan.info["social"] = [
        {
            "kind": "linkedin",
            "label": "LinkedIn",
            "url": "https://linkedin.example/company/sv",
            "display": "linkedin.example/company/sv",
        }
    ]
    html = text(client.get("/"))
    assert "sm-linkedin" in html
    assert 'href="https://linkedin.example/company/sv"' in html
    # eigenes Symbol, nicht die Weltkugel für unbekannte Kanäle
    assert ICONS["linkedin"] in html
