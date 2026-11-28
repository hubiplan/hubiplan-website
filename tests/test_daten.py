"""Feste Datentypen (seite/daten.py): Felder aus HUBIplan und strenges Lesen."""

from dataclasses import fields

import pytest
from django.template import Context, Template

from seite.daten import Beitrag, Termin, UnbekanntesFeld, Wettbewerb

from . import schnittstelle


def test_unbekanntes_feld_ist_in_tests_ein_fehler():
    termin = Termin.aus({"title": "Sommerfest", "neu_im_server": 1})
    assert termin.title == "Sommerfest"
    with pytest.raises(UnbekanntesFeld, match="Termin hat kein Feld „titel“"):
        termin.titel  # noqa: B018
    # … auch aus einer Vorlage heraus, in Ausgabe und Bedingung
    for vorlage in ("{{ e.titel }}", "{% if e.titel %}x{% endif %}"):
        with pytest.raises(UnbekanntesFeld):
            Template(vorlage).render(Context({"e": termin}))
    assert Template("{{ e.title }}").render(Context({"e": termin})) == "Sommerfest"


def test_im_betrieb_bleibt_ein_unbekanntes_feld_leer(settings):
    settings.STRENGE_DATEN = False
    termin = Termin.aus({"title": "Sommerfest"})
    assert Template("[{{ e.titel }}]").render(Context({"e": termin})) == "[]"
    assert not hasattr(termin, "titel")


def test_kopieren_und_vergleichen_gehen_wie_bei_jedem_objekt():
    import copy

    a = Termin.aus({"title": "Sommerfest", "attachments": [{"name": "Plan"}]})
    b = copy.deepcopy(a)
    assert a == b and a is not b and b.attachments == [{"name": "Plan"}]


@pytest.mark.parametrize(
    ("typ", "antwort", "liste"),
    [
        (Termin, "events/", "events"),
        (Beitrag, "posts/", "posts"),
        (Wettbewerb, "results/", "competitions"),
    ],
)
def test_typ_kennt_jedes_feld_des_servers(typ, antwort, liste):
    """Liefert HUBIplan ein neues Feld, fällt es hier auf, statt still wegzufallen."""
    server = schnittstelle.ANTWORTEN[antwort][liste][0]
    assert set(server) <= {f.name for f in fields(typ)}
