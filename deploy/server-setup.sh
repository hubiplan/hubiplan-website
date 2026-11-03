#!/bin/sh
# Läuft auf dem Server im Ordner der neuen Fassung (ZIEL.neu, aufgerufen von
# deploy/deploy.sh). Ablauf mit Rückweg: erst bauen (die laufende Webseite bleibt
# unberührt), dann Ordner tauschen (ZIEL -> ZIEL.vorher) und starten; wird der Container
# nicht gesund, automatisch zurück zur vorigen Fassung. Von Hand zurück: deploy/zurueck.sh.
set -eu

ZIEL="${ZIEL:-$(pwd)}"
NEU="$(pwd)"

if ! docker network inspect hubiplan_web > /dev/null 2>&1; then
    echo "Abbruch: Docker-Netz hubiplan_web fehlt (läuft HUBIplan?)." >&2
    exit 1
fi

key() { head -c 48 /dev/urandom | base64 | tr -d '/+=\n' | head -c 50; }

if [ ! -f .env ]; then
    umask 077
    if [ -n "${HUBIPLAN_HOST:-}" ]; then
        # Echtserver: eigene Domain(s), HUBIplan unter HUBIPLAN_HOST
        [ -n "${SITE_DOMAINS:-}" ] || { echo "Abbruch: SITE_DOMAINS fehlt." >&2; exit 1; }
        echo "Lege .env für $SITE_DOMAINS an (mit neuem Schlüssel) …"
        cat > .env << EOF
DJANGO_SECRET_KEY=$(key)
ALLOWED_HOSTS=$SITE_DOMAINS,website,127.0.0.1
HUBIPLAN_API_URL=http://backend:8000
HUBIPLAN_PUBLIC_URL=https://$HUBIPLAN_HOST
HUBIPLAN_HOST=$HUBIPLAN_HOST
HUBIPLAN_MEDIA_URL=https://$HUBIPLAN_HOST
${WEBSITE_HINTER_PROXY:+WEBSITE_HINTER_PROXY=$WEBSITE_HINTER_PROXY}
${WEB_PORT:+WEB_PORT=$WEB_PORT}
EOF
    else
        echo "Lege .env aus .env.example an (mit neuem Schlüssel) …"
        sed "s|^DJANGO_SECRET_KEY=.*|DJANGO_SECRET_KEY=$(key)|" .env.example > .env
    fi
    chmod 600 .env
fi

# Hinter einem vorhandenen Webserver (Echtserver mit HestiaCP): Container nur auf
# 127.0.0.1:WEB_PORT, HTTPS macht der vorgeschaltete Webserver.
PROJEKT=$(grep '^COMPOSE_PROJECT_NAME=' .env | cut -d= -f2 || true)
PROJEKT=${PROJEKT:-$(basename "$ZIEL")}
COMPOSE="docker compose -p $PROJEKT"
if grep -q '^WEBSITE_HINTER_PROXY=1' .env; then
    COMPOSE="$COMPOSE -f docker-compose.yml -f docker-compose.proxy.yml"
fi
IMG=$($COMPOSE config --images | head -n 1)

gesund() {
    # Warten, bis der Container gesund ist
    i=0
    state="?"
    while [ "$i" -lt 30 ]; do
        state=$(docker inspect -f '{{.State.Health.Status}}' "$($COMPOSE ps -q website)" 2> /dev/null || echo "?")
        [ "$state" = "healthy" ] && break
        i=$((i + 1))
        sleep 2
    done
    echo "Webseite: $state"
    [ "$state" = "healthy" ]
}

starten() {
    $COMPOSE up -d --remove-orphans || return 1
    gesund
}

# Only this project’s former rollback image is eligible for later cleanup.
case "${IMG##*/}" in
    *:*) ROLLBACK_IMG="${IMG%:*}:vorher" ;;
    *) ROLLBACK_IMG="$IMG:vorher" ;;
esac
ALT_ROLLBACK=$(docker image inspect -f '{{.Id}}' "$ROLLBACK_IMG" 2> /dev/null || true)

# 1. Bauen; die laufende Fassung bleibt als „:vorher“ erhalten
if docker image inspect "$IMG" > /dev/null 2>&1; then
    docker tag "$IMG" "$ROLLBACK_IMG"
fi
if ! $COMPOSE build; then
    echo "FEHLER: Bauen fehlgeschlagen. Die laufende Webseite bleibt unverändert." >&2
    docker tag "$ROLLBACK_IMG" "$IMG" 2> /dev/null || true
    exit 1
fi

# 2. Ordner tauschen
if [ "$NEU" != "$ZIEL" ]; then
    rm -rf "$ZIEL.vorher"
    if [ -d "$ZIEL" ]; then
        mv "$ZIEL" "$ZIEL.vorher"
    fi
    mv "$NEU" "$ZIEL"
    cd "$ZIEL"
fi

# 3. Starten; bei Fehler zurück
if ! starten; then
    echo "FEHLER: Die neue Fassung wird nicht gesund. Zurück zur vorigen Fassung …" >&2
    $COMPOSE logs --tail 40 website >&2 || true
    if [ -d "$ZIEL.vorher" ]; then
        rm -rf "$ZIEL.fehler"
        mv "$ZIEL" "$ZIEL.fehler"
        mv "$ZIEL.vorher" "$ZIEL"
        cp -p "$ZIEL.fehler/.env" "$ZIEL/.env"
        cd "$ZIEL"
        docker tag "$ROLLBACK_IMG" "$IMG" 2> /dev/null || true
        if starten; then
            echo "Vorige Fassung läuft wieder. Die fehlerhafte liegt in $ZIEL.fehler." >&2
        else
            echo "FEHLER: Auch die vorige Fassung wird nicht gesund – bitte von Hand prüfen." >&2
        fi
    fi
    exit 1
fi

# Never prune the shared Docker daemon. Remove only the captured former rollback
# image without force: active containers and remaining tags protect it.
AKTUELL=$(docker image inspect -f '{{.Id}}' "$IMG")
RUECKWEG=$(docker image inspect -f '{{.Id}}' "$ROLLBACK_IMG" 2> /dev/null || true)
if [ -n "$ALT_ROLLBACK" ] && [ "$ALT_ROLLBACK" != "$AKTUELL" ] && [ "$ALT_ROLLBACK" != "$RUECKWEG" ]; then
    MARKEN=$(docker image inspect -f '{{json .RepoTags}}' "$ALT_ROLLBACK" 2> /dev/null || echo unknown)
    DIGESTS=$(docker image inspect -f '{{json .RepoDigests}}' "$ALT_ROLLBACK" 2> /dev/null || echo unknown)
    case "$MARKEN/$DIGESTS" in
        '[]/[]'|'null/null'|'[]/null'|'null/[]')
            docker image rm "$ALT_ROLLBACK" > /dev/null 2>&1 || true ;;
    esac
fi
rm -rf "$ZIEL.fehler"
