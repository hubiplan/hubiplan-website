"""Letzte Fassung von Impressum und Datenschutzhinweisen (UX-Audit 31.10. S02/F15).

Bei allgemeiner Wartung oder wenn HUBIplan nicht antwortet, zeigt die Webseite die
zuletzt erfolgreich geladene Fassung mit ihrem Stand. Gespeichert wird je Hostname in
einer kleinen JSON-Datei (Container: /tmp, schreibbar; Inhalt ist ohnehin öffentlich).
Ohne gespeicherte Fassung bleibt es bei der Wartungs- bzw. Fehlerseite.
"""

from __future__ import annotations

import contextlib
import datetime
import hashlib
import json
import logging
import os
import uuid
from pathlib import Path

from django.conf import settings
from django.utils import timezone

log = logging.getLogger(__name__)


def _file(host: str) -> Path:
    name = hashlib.sha256(host.encode()).hexdigest()[:32]
    return Path(settings.LEGAL_ARCHIVE_DIR) / f"recht-{name}.json"


def save(host: str, key: str, info: dict, imprint: dict) -> None:
    path = _file(host)
    data = {
        "saved_at": timezone.now().isoformat(),
        "key": key,
        "info": info,
        "imprint": imprint,
    }
    # Eigener Name je Schreibvorgang: Prozesse und Threads überschreiben sich nicht (GA-F02)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(data), encoding="utf-8")
        os.replace(tmp, path)
    except OSError as exc:
        log.warning("Rechtstexte nicht gesichert: %s", exc)
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)


def load(host: str) -> dict | None:
    try:
        data = json.loads(_file(host).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    try:
        data["saved_at"] = datetime.datetime.fromisoformat(data["saved_at"])
    except (KeyError, TypeError, ValueError):
        return None
    return data
