"""Entferntes verschwindet nach höchstens 15 Minuten (Fachfrage 10 zum Gesamtaudit 10.11.)."""

from django.conf import settings

from seite import api


def test_zwischenspeicher_hoechstens_15_minuten():
    # Frisch höchstens CACHE_SECONDS, danach noch STALE_SECONDS während des Neuladens
    assert settings.CACHE_SECONDS + api.STALE_SECONDS <= 15 * 60
