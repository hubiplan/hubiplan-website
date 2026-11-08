import pytest
from django.core.cache import cache, caches

from seite import api

from .fake import FakeHubiplan


@pytest.fixture
def hubiplan(monkeypatch):
    fake = FakeHubiplan()
    monkeypatch.setattr(api, "_request", fake)
    cache.clear()
    caches["bilder"].clear()
    yield fake
    cache.clear()
    caches["bilder"].clear()


@pytest.fixture(autouse=True)
def _ohne_manifest(settings):
    settings.STORAGES = {
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}
    }


@pytest.fixture(autouse=True)
def _rechtstexte_archiv(settings, tmp_path):
    settings.LEGAL_ARCHIVE_DIR = str(tmp_path / "rechtstexte")
