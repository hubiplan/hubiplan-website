"""hubiplan #539: Eingabefelder heben sich von getönten Flächen ab (Farbrolle „Flächen“)."""

import re
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "seite" / "static" / "seite"


def test_felder_heben_sich_von_getoenten_flaechen_ab():
    """hubiplan #539: Such- und Formularfelder hängen nicht an der Farbrolle „Flächen“."""
    css = (STATIC / "seite.css").read_text()
    for selektor in (".suche input", ".fuss-suche input", ".formular input, .formular select"):
        treffer = re.search(re.escape(selektor) + r"[^{]*\{([^}]*)\}", css)
        assert treffer, selektor
        assert "background: #fff" in treffer.group(1), selektor
        assert "var(--flaeche)" not in treffer.group(1), selektor
