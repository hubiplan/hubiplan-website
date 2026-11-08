# Vereinswebseite: kleiner Django-Dienst ohne Datenbank
# Gleiches Basisimage wie das Backend von HUBIplan, fest per Prüfsumme (reproduzierbarer Bau)
FROM python:3.13-slim@sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
ARG DEV=0
RUN pip install -r requirements.txt && if [ "$DEV" = "1" ]; then pip install -r requirements-dev.txt; fi

COPY . .
# Übersetzungen (hubiplan/konzepte/englisch.md, W1): .po → .mo beim Bauen. GNU gettext bleibt
# nur im Testabbild, im Betrieb wird es wieder entfernt.
RUN apt-get update -q && apt-get install -y -q --no-install-recommends gettext > /dev/null \
    && DJANGO_SECRET_KEY=nur-zum-bauen python manage.py compilemessages -v0 \
    && if [ "$DEV" != "1" ]; then \
           apt-get purge -y -q gettext > /dev/null && apt-get autoremove -y -q > /dev/null; fi \
    && rm -rf /var/lib/apt/lists/*
RUN DJANGO_SECRET_KEY=nur-zum-bauen python manage.py collectstatic --noinput -v0 \
    && useradd --system --uid 10001 --no-create-home seite \
    && mkdir /zwischenspeicher && chown seite /zwischenspeicher
USER seite

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:8000/gesund', timeout=4)" || exit 1
# Zugriffslog ohne Abfrage (?…) und ohne Referer: Der Vorschau-Schlüssel steht in der Adresse
# (/vorschau?schluessel=…) und darf in keinem Log landen (Gesamtaudit 30.10., I-S01)
# Ohne Steuer-Socket (gunicornc): Er läge im Home des Nutzers, das im schreibgeschützten
# Container fehlt, und wird nicht gebraucht
CMD ["gunicorn", "config.wsgi:application", "--no-control-socket", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "8", "--timeout", "30", "--access-logfile", "-", "--access-logformat", "%(h)s %(t)s \"%(m)s %(U)s %(H)s\" %(s)s %(b)s %(L)s"]
