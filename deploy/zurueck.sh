#!/bin/sh
# Zurück zur vorigen Fassung der Webseite (Ordner ZIEL.vorher und Image „:vorher“).
# Läuft auf dem Server im Ordner der Webseite:
#   ssh administrator@dogado "cd /opt/hubiplan-website && sudo sh deploy/zurueck.sh"
# Ein zweiter Aufruf geht wieder vor (die Fassungen tauschen jeweils die Plätze).
set -eu

ZIEL="$(pwd)"
if [ ! -d "$ZIEL.vorher" ]; then
    echo "Keine vorige Fassung vorhanden ($ZIEL.vorher fehlt)." >&2
    exit 1
fi
PROJEKT=$(grep '^COMPOSE_PROJECT_NAME=' .env | cut -d= -f2 || true)
PROJEKT=${PROJEKT:-$(basename "$ZIEL")}
COMPOSE="docker compose -p $PROJEKT"
if grep -q '^WEBSITE_HINTER_PROXY=1' .env; then
    COMPOSE="$COMPOSE -f docker-compose.yml -f docker-compose.proxy.yml"
fi
IMG=$($COMPOSE config --images | head -n 1)
BASIS="${IMG%%:*}"

echo "Jetzt: $(cat .version 2>/dev/null || true) $(cat .fassung 2>/dev/null || echo unbekannt)"
echo "Zurück zu: $(cat "$ZIEL.vorher/.version" 2>/dev/null || true) $(cat "$ZIEL.vorher/.fassung" 2>/dev/null || echo unbekannt)"
if docker image inspect "$BASIS:vorher" > /dev/null 2>&1; then
    docker tag "$IMG" "$BASIS:tausch"
    docker tag "$BASIS:vorher" "$IMG"
    docker tag "$BASIS:tausch" "$BASIS:vorher"
    docker rmi "$BASIS:tausch" > /dev/null
fi
cp -p "$ZIEL/.env" "$ZIEL.vorher/.env"
mv "$ZIEL" "$ZIEL.tausch"
mv "$ZIEL.vorher" "$ZIEL"
mv "$ZIEL.tausch" "$ZIEL.vorher"
cd "$ZIEL"
$COMPOSE up -d --remove-orphans --force-recreate
$COMPOSE ps
echo "Läuft jetzt: $(cat .version 2>/dev/null || true) $(cat .fassung 2>/dev/null || echo unbekannt)"
# Rollout-Protokoll (deploy/deploy.sh): Rückweg vermerken
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $(cut -c1-7 .fassung 2>/dev/null || echo ?) $(cat .version 2>/dev/null || echo ?) zurueck" >> "$ZIEL.protokoll" || true
