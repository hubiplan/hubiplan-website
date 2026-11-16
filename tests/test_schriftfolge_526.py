"""Eigene Schriftfolge (hubiplan #526): nur Namen lokal installierter Schriften, streng geprüft,
weil sie im <style> stehen. Alle Daten erfunden."""

import re

import pytest
from django.core.cache import cache

from seite import stil


def seite(client) -> str:
    cache.clear()
    return client.get("/").content.decode()


def test_schriftfolge_mit_anfuehrungszeichen_und_ersatz():
    assert stil.font_stack("Lucida Sans, Lucida Grande, Segoe UI, Arial") == (
        '"Lucida Sans", "Lucida Grande", "Segoe UI", "Arial", sans-serif'
    )
    assert stil.font_stack("Source Sans 3, serif") == '"Source Sans 3", serif'


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "serif",
        'Arial"; } body { color: red',
        "Arial</style><script>",
        "a{b}",
        "A, B, C, D, E, F, G",
        ["Arial"],
    ],
)
def test_ungueltig_wird_ignoriert(value):
    assert stil.font_stack(value) is None


def test_ueberschriften_folgen_dem_text_ohne_eigene_wahl():
    assert stil.font_stacks({"font_family": "Lucida Sans"}) == {
        "text": '"Lucida Sans", sans-serif',
        "heading": '"Lucida Sans", sans-serif',
    }
    # eigene Schrift der Überschriften bleibt
    assert stil.font_stacks({"font_family": "Lucida Sans", "heading_font": "fraktur"}) == {
        "text": '"Lucida Sans", sans-serif'
    }
    assert stil.font_stacks({"heading_font_family": "Georgia, serif"}) == {
        "heading": '"Georgia", serif'
    }


def test_auf_der_seite(client, hubiplan):
    hubiplan.info["style"] = {"font": "clear", "font_family": "Lucida Sans, Segoe UI"}
    html = seite(client)
    tag = re.search(r"<html[^>]*>", html).group(0)
    assert 'data-st-font-own="on"' in tag and 'data-st-heading-font-own="on"' in tag
    assert ';--st-schrift:"Lucida Sans", "Segoe UI", sans-serif' in html
    assert "&quot;" not in re.search(r"<style>:root\{[^<]*</style>", html).group(0)
    # Ungültiges fällt still weg, die Seite bleibt wie das Design
    hubiplan.info["style"] = {"font_family": 'X"; } *{display:none'}
    html = seite(client)
    assert "--st-schrift" not in html and "data-st-font-own" not in html
