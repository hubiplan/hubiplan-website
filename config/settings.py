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
# Ohne Angabe nimmt der Betrieb keinen Rechnernamen an (Gesamtaudit 13.11. H-03); nur in der
# Entwicklung gilt jeder. deploy/server-setup.sh trägt die Domains ein.
ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get("ALLOWED_HOSTS", "*" if DEBUG else "").split(",") if h.strip()
]

# --- Vorgeschalteter Proxy ---
# Der Dienst lauscht hinter HestiaCP auf einem lokalen Port, den auf einem geteilten Server
# jeder Prozess erreicht. Die Besucheradresse aus X-Forwarded-For gilt deshalb nur, wenn die
# Anfrage den geheimen Kopfwert des nginx trägt (derselbe wie für HUBIplan,
# hubiplan/deploy/hestia/proxy-geheim.sh) oder von einem vertrauten Container kommt (Caddy von
# HUBIplan, Dienst „web“). Ist beides leer (Entwicklung, Tests), gilt die Kopfzeile immer
# (Gesamtaudit 13.11. S-05; seite/besucher.py).
PROXY_GEHEIM = os.environ.get("HUBIPLAN_PROXY_GEHEIM", "").strip()
PROXY_HOSTS = [h.strip() for h in os.environ.get("WEBSITE_PROXY_HOSTS", "").split(",") if h.strip()]

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
# Ist HUBIplan nicht erreichbar (z. B. beim Ausrollen), zeigt die Seite höchstens so alte
# Stände weiter statt einer Fehlerseite (Ralf 08.11.: 24 h). Wartung und Widerruf wirken
# sofort, sobald HUBIplan wieder antwortet.
STALE_IF_ERROR_SECONDS = int(os.environ.get("STALE_IF_ERROR_SECONDS", "86400"))
# Bilder für diesen Fall bis zu dieser Größe zwischenspeichern (nur mit CACHE_DIR)
STALE_IMAGE_MAX_BYTES = int(os.environ.get("STALE_IMAGE_MAX_BYTES", str(2 * 1024 * 1024)))
# Vorschau wird bei jedem Aufruf autorisiert und niemals zwischen Anfragen gecacht.
# Die frühere Umgebungsvariable PREVIEW_CACHE_SECONDS hat keine Wirkung mehr.

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
    "seite.besucher.Besucher",
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
# Zwischenspeicher: auf dem Server auf der Platte (CACHE_DIR, eigenes Volume), damit er
# Neustarts übersteht und beide gunicorn-Prozesse ihn teilen; sonst im Prozess.
CACHE_DIR = os.environ.get("CACHE_DIR", "").strip()
if CACHE_DIR:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
            "LOCATION": os.path.join(CACHE_DIR, "daten"),
            "OPTIONS": {"MAX_ENTRIES": 3000},
        },
        "bilder": {
            "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
            "LOCATION": os.path.join(CACHE_DIR, "bilder"),
            "TIMEOUT": STALE_IF_ERROR_SECONDS,
            "OPTIONS": {"MAX_ENTRIES": int(os.environ.get("STALE_IMAGE_ENTRIES", "300"))},
        },
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "OPTIONS": {"MAX_ENTRIES": 2000},
        },
        "bilder": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "TIMEOUT": STALE_IF_ERROR_SECONDS,
            "OPTIONS": {"MAX_ENTRIES": 50},
        },
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
