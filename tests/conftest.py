import pytest
from django.core.cache import cache, caches

from seite import api

from . import schnittstelle
from .fake import FakeHubiplan


@pytest.fixture
def hubiplan(monkeypatch, request):
    fake = FakeHubiplan()
    # Tests mit dem Merker ``falsche_daten`` liefern absichtlich, was HUBIplan nie liefert
    # (kaputte oder böswillige Antworten): dort gilt der Abgleich nicht
    absichtlich = request.node.get_closest_marker("falsche_daten") is not None

    neu: list[str] = []

    def geprueft(method, path, **kwargs):
        antwort = fake(method, path, **kwargs)
        daten = None
        if antwort.content_type == "application/json" and antwort.status == 200:
            daten = antwort.json()
        neu.extend(schnittstelle.pruefe(method, path, antwort.status, daten))
        return antwort

    monkeypatch.setattr(api, "_request", geprueft)
    cache.clear()
    caches["bilder"].clear()
    caches["varianten"].clear()
    yield fake
    cache.clear()
    caches["bilder"].clear()
    caches["varianten"].clear()
    assert absichtlich or not neu, (
        "Die nachgebildete Schnittstelle weicht von HUBIplan ab (tests/schnittstelle.py): "
        + "; ".join(sorted(set(neu)))
    )
    assert neu or not absichtlich, "Merker falsche_daten ohne Abweichung: bitte streichen"


@pytest.fixture(autouse=True)
def _neu_holen_im_aufruf(settings):
    # Hintergrund-Auffrischung (seite/api.py) prüft test_ladezeiten.py eigens
    settings.REFRESH_IN_BACKGROUND = False


@pytest.fixture(autouse=True)
def _ohne_manifest(settings):
    settings.STORAGES = {
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}
    }


@pytest.fixture(autouse=True)
def _rechtstexte_archiv(settings, tmp_path):
    settings.LEGAL_ARCHIVE_DIR = str(tmp_path / "rechtstexte")
