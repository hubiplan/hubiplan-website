"""Zeitleiste der Chronik: Einträge aus HUBIplan in Kapitel gliedern (Ralf 02.11.).

HUBIplan liefert die Einträge nach Jahren sortiert, Kapitel vor den Ereignissen ihres
Jahres. Ein Kapitel (``kind`` = ``chapter``) ist eine Zwischenüberschrift; darunter stehen
alle Ereignisse bis zum nächsten Kapitel. Ereignisse vor dem ersten Kapitel stehen ohne
Überschrift oben. Sprungmarken: zu den Kapiteln, ohne Kapitel ab 15 Ereignissen zu den
Jahrzehnten.
"""

from __future__ import annotations

from django.utils.translation import gettext as _

SPRUNG_AB = 15


def zeitraum(eintrag: dict) -> str:
    """„1939–1948“ oder „1920“."""
    jahr, bis = eintrag.get("year"), eintrag.get("until")
    return f"{jahr}–{bis}" if bis and bis != jahr else str(jahr)


def gliedern(eintraege: list | None) -> dict:
    """{"abschnitte": [{"kapitel", "id", "ereignisse"}], "sprungmarken": [{"id", "label"}]}"""
    abschnitte: list[dict] = []
    for e in eintraege or []:
        if not isinstance(e, dict) or not e.get("year") or not e.get("title"):
            continue
        e = {**e, "zeitraum": zeitraum(e), "anker": ""}
        if e.get("kind") == "chapter":
            abschnitte.append(
                {"kapitel": e, "id": f"kapitel-{len(abschnitte) + 1}", "ereignisse": []}
            )
            continue
        if not abschnitte:
            abschnitte.append({"kapitel": None, "id": "", "ereignisse": []})
        abschnitte[-1]["ereignisse"].append(e)

    marken = [
        {"id": a["id"], "label": a["kapitel"]["title"], "zeitraum": a["kapitel"]["zeitraum"]}
        for a in abschnitte
        if a["kapitel"]
    ]
    ereignisse = [e for a in abschnitte for e in a["ereignisse"]]
    if not marken and len(ereignisse) >= SPRUNG_AB:
        gesehen = set()
        for e in ereignisse:
            jahrzehnt = e["year"] // 10 * 10
            if jahrzehnt not in gesehen:
                gesehen.add(jahrzehnt)
                e["anker"] = f"jahrzehnt-{jahrzehnt}"
                # „1920er“: auf Englisch „1920s“
                marken.append({"id": e["anker"], "label": _("%(jahr)ser") % {"jahr": jahrzehnt}})
    return {"abschnitte": abschnitte, "sprungmarken": marken if len(marken) > 1 else []}
