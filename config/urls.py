from django.urls import path, re_path, register_converter

from seite import views


class UnitsPath:
    """„zuege“ oder „einheiten“ (je nach Bezeichnung der Untereinheiten)."""

    regex = "zuege|einheiten"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(UnitsPath, "einheiten")

urlpatterns = [
    path("", views.start, name="start"),
    path("aktuelles/", views.news, name="aktuelles"),
    path("vorstand/", views.board, name="vorstand"),
    path("termine/", views.events, name="termine"),
    path("<einheiten:pfad>/", views.units, name="einheiten"),
    path("<einheiten:pfad>/<slug:slug>/", views.unit, name="einheit"),
    path("majestaeten/", views.honors, name="majestaeten"),
    re_path(r"^majestaeten/(?P<kennung>[a-f0-9]{20})/$", views.dignity, name="wuerde"),
    path("ehrungen/", views.honorary, name="ehrungen"),
    path("ergebnisse/", views.results, name="ergebnisse"),
    re_path(r"^ergebnisse/reihe/(?P<kennung>[a-f0-9]{20})/$", views.result_series, name="reihe"),
    re_path(r"^ergebnisse/(?P<kennung>[a-f0-9]{20})/$", views.result, name="ergebnis"),
    re_path(
        r"^ergebnisse/(?P<kennung>[a-f0-9]{20})/tabelle/$",
        views.result_table,
        name="ergebnis_tabelle",
    ),
    re_path(
        r"^ergebnisse/(?P<kennung>[a-f0-9]{20})/stand/$",
        views.result_version,
        name="ergebnis_stand",
    ),
    path("chronik/", views.chronicle, name="chronik"),
    path("aemter/", views.offices, name="aemter"),
    path("geschichte/", views.history, name="geschichte"),
    path("dokumente/", views.documents, name="dokumente"),
    path("mitglieder/<slug:slug>/", views.members, name="mitglieder"),
    path("in-gedenken/", views.memorial, name="gedenken"),
    path("repertoire/", views.repertoire, name="repertoire"),
    path("belegung/", views.bookings, name="belegung"),
    path("presse/", views.press, name="presse"),
    path("suche/", views.search, name="suche"),
    path("galerie/", views.gallery, name="galerie"),
    path("galerie/<slug:slug>/", views.album, name="album"),
    path("seite/<slug:slug>/", views.page, name="seite"),
    path("kontakt/", views.contact, name="kontakt"),
    path("kontakt/pruefung/", views.contact_challenge, name="kontakt_pruefung"),
    path("impressum/", views.imprint, name="impressum"),
    path("datenschutz/", views.privacy, name="datenschutz"),
    path("barrierefreiheit/", views.accessibility, name="barrierefreiheit"),
    path("vorschau/", views.preview, name="vorschau"),
    # HUBIplan verlinkt ohne Schrägstrich am Ende
    path("vorschau", views.preview),
    path("vorschau/ende/", views.preview_end, name="vorschau_ende"),
    path("vorschau/design/", views.preview_design, name="vorschau_design"),
    # Designpakete (Ralf 2026-11-02): CSS eingespielter Designs, Export der Standarddesigns
    re_path(r"^design/(?P<key>[a-z][a-z0-9-]{1,30})\.css$", views.design_css, name="design_css"),
    re_path(
        r"^design-paket/(?P<key>[a-z][a-z0-9-]{1,30})\.zip$",
        views.design_export,
        name="design_export",
    ),
    re_path(r"^medien/(?P<kind>[am])/(?P<path>.+)$", views.media, name="medien"),
    path("robots.txt", views.robots, name="robots"),
    path("favicon.ico", views.favicon, name="favicon"),
    path("gesund", views.health, name="gesund"),
]
