"""Umgebung für die Tests (wird vor Django geladen, siehe pyproject.toml)."""

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "nur-fuer-tests")
os.environ.setdefault("HUBIPLAN_API_URL", "http://backend:8000")
os.environ.setdefault("HUBIPLAN_PUBLIC_URL", "https://hubiplan.example")
os.environ.setdefault("MAINTENANCE_FILE", "/nicht/vorhanden/wartung")
os.environ.setdefault("PREVIEW_COOKIE_SECURE", "false")
# Im Betrieb ohne Angabe kein Rechnername (H-03); die Tests rufen erfundene Domains auf
os.environ.setdefault("ALLOWED_HOSTS", "*")
