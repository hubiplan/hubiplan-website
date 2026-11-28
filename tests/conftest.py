import pytest
from django.core.cache import cache, caches

from seite import api

from . import schnittstelle
from .fake import FakeHubiplan


@pytest.fixture
def hubiplan(monkeypatch):
    fake = FakeHubiplan()

    neu: list[str] = []

    def geprueft(method, path, **kwargs):
        antwort = fake(method, path, **kwargs)
        daten = None
        if antwort.content_type == "application/json" and antwort.status == 200:
            daten = antwort.json()
        neu.extend(schnittstelle.neue_abweichungen(method, path, antwort.status, daten))
        return antwort

    monkeypatch.setattr(api, "_request", geprueft)
    cache.clear()
    caches["bilder"].clear()
    caches["varianten"].clear()
    yield fake
    cache.clear()
    caches["bilder"].clear()
    caches["varianten"].clear()
    assert not neu, (
        "Die nachgebildete Schnittstelle weicht von HUBIplan ab (tests/schnittstelle.py): "
        + "; ".join(sorted(set(neu)))
    )


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
