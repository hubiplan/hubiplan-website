"""Gesamtaudit 03.11.2026, GA-F02: Rechtstext-Archiv mit eigener Zwischendatei je Schreibvorgang."""

import threading
from pathlib import Path

from django.conf import settings

from seite import archiv


def test_gleichzeitiges_speichern_bleibt_lesbar(caplog):
    def schreiben(n):
        for _ in range(20):
            archiv.save("verein.example.org", f"k{n}", {"n": n}, {"text": "x" * 5000})

    threads = [threading.Thread(target=schreiben, args=(n,)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    # save() meldet Schreibfehler nur im Protokoll
    assert "nicht gesichert" not in caplog.text
    data = archiv.load("verein.example.org")
    assert data is not None and data["imprint"]["text"] == "x" * 5000
    # Keine Zwischendateien bleiben liegen
    assert [p.name for p in Path(settings.LEGAL_ARCHIVE_DIR).iterdir() if p.suffix == ".tmp"] == []
