"""Einstellungen der Vereinswebseite. Keine Datenbank: alle Daten kommen aus der
öffentlichen Schnittstelle von HUBIplan. Alles Wichtige kommt aus Umgebungsvariablen."""

import os
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "ja")


DEBUG = env_bool("DJANGO_DEBUG", False)
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "nur-fuer-die-entwicklung" if DEBUG else "")
if not SECRET_KEY:
    raise RuntimeError("DJANGO_SECRET_KEY fehlt.")
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "*").split(",") if h.strip()]

# --- HUBIplan ---
# Adresse, unter der dieser Container HUBIplan erreicht (z. B. intern http://backend:8000)
HUBIPLAN_API_URL = os.environ.get("HUBIPLAN_API_URL", "http://localhost:8000").rstrip("/")
# Öffentliche Adresse von HUBIplan (für Browser: Kontaktformular, Kalender-Abo)
HUBIPLAN_PUBLIC_URL = os.environ.get("HUBIPLAN_PUBLIC_URL", HUBIPLAN_API_URL).rstrip("/")
# Bei internem Aufruf: Hostname, den HUBIplan erwartet (sonst der aus HUBIPLAN_API_URL)
# Woher Logos und andere hochgeladene Dateien (/media/…) kommen (Server: über Caddy)
HUBIPLAN_MEDIA_URL = os.environ.get("HUBIPLAN_MEDIA_URL", HUBIPLAN_API_URL).rstrip("/")
HUBIPLAN_HOST = os.environ.get("HUBIPLAN_HOST", urlparse(HUBIPLAN_PUBLIC_URL).hostname or "")
API_TIMEOUT = float(os.environ.get("API_TIMEOUT", "10"))
# Antworten der Schnittstelle so lange zwischenspeichern
CACHE_SECONDS = int(os.environ.get("CACHE_SECONDS", "120"))
# In der Vorschau nur kurz (je Vorschau getrennt), damit Änderungen gleich sichtbar sind;
# 0 = gar nicht
PREVIEW_CACHE_SECONDS = int(os.environ.get("PREVIEW_CACHE_SECONDS", "5"))

# Feste Einheit statt Hostname (Testserver: alle Aufrufe unter /webseite/ gehören zu
# dieser Domain aus HUBIplan)
SITE_HOST_OVERRIDE = os.environ.get("SITE_HOST_OVERRIDE", "").strip().lower()
# Pfad, unter dem die Seite läuft (Testserver: /webseite), sonst leer
BASE_PATH = os.environ.get("BASE_PATH", "").rstrip("/")
FORCE_SCRIPT_NAME = BASE_PATH or None
# Allgemeiner Wartungsschalter (z. B. beim Ausrollen): Umgebungsvariable oder Datei
MAINTENANCE = env_bool("MAINTENANCE", False)
MAINTENANCE_FILE = os.environ.get("MAINTENANCE_FILE", "/tmp/wartung")  # noqa: S108
# Letzte Fassung von Impressum/Datenschutz für Wartung und Ausfälle (seite/archiv.py)
LEGAL_ARCHIVE_DIR = os.environ.get("LEGAL_ARCHIVE_DIR", "/tmp/rechtstexte")  # noqa: S108

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "seite",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "seite.middleware.SecurityHeaders",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": ["django.template.context_processors.request"]},
    }
]

DATABASES: dict = {}
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "OPTIONS": {"MAX_ENTRIES": 2000},
    }
}

LANGUAGE_CODE = "de"
LANGUAGES = [("de", "Deutsch"), ("en", "English")]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True

STATIC_URL = f"{BASE_PATH}/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        if not DEBUG
        else "django.contrib.staticfiles.storage.StaticFilesStorage"
    }
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"
# Vorschau-Cookie: nur über HTTPS (außer in der Entwicklung)
PREVIEW_COOKIE_SECURE = env_bool("PREVIEW_COOKIE_SECURE", not DEBUG)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
}
