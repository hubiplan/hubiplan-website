#!/bin/bash
# Geheimer Kopfwert zwischen HestiaCP-nginx und der Vereinswebseite (Gesamtaudit 13.11. S-05).
#
# Die Webseite lauscht auf 127.0.0.1:WEB_PORT. Auf einem geteilten Server erreicht diesen Port
# jeder Prozess, auch Nachbar-Websites; ohne Schutz könnten sie beliebige Besucheradressen
# vorgeben. Dieses Skript übernimmt den Kopfwert, den hubiplan/deploy/hestia/proxy-geheim.sh
# für HUBIplan angelegt hat (nginx schickt ihn schon mit), in die .env der Webseite. Danach
# glaubt die Webseite X-Forwarded-For nur noch mit diesem Wert oder vom Caddy von HUBIplan.
#
# Reihenfolge: erst die Vorlage webseite-8111 erneuern (sie bindet den Kopfwert ein,
# hubiplan/deploy/hestia/vorlagen-erneuern.sh), dann dieses Skript. Es bricht ab, wenn der
# nginx den Wert für die Webseite noch nicht mitschickt: Sonst zählten alle Besucher als einer.
#
# Aufruf vom lokalen Arbeitsrechner, läuft als root auf dem Server:
#   ssh deploy@server.example.org "sudo bash -s" < deploy/hestia/proxy-geheim.sh
# ZURUECK=1 nimmt die Einstellung wieder heraus. Gibt den Wert nie aus.
set -euo pipefail

APP=${APP:-/opt/hubiplan}
SEITE=${SEITE:-/opt/hubiplan-website}
ENV="$SEITE/.env"

echo "### Start $(TZ=Europe/Berlin date '+%d.%m.%Y %H:%M')"
[ -f "$ENV" ] || { echo "Abbruch: $ENV fehlt."; exit 1; }
grep -q '^WEBSITE_HINTER_PROXY=1' "$ENV" || { echo "Abbruch: WEBSITE_HINTER_PROXY=1 fehlt in $ENV."; exit 1; }

cp -p "$ENV" "$ENV.vor-proxy-geheim"
sed -i '/^HUBIPLAN_PROXY_GEHEIM=/d; /^WEBSITE_PROXY_HOSTS=/d' "$ENV"
if [ -z "${ZURUECK:-}" ]; then
    GEHEIM=$(sed -n 's/^HUBIPLAN_PROXY_GEHEIM=//p' "$APP/.env" | tail -1)
    case "$GEHEIM" in
        "") echo "Abbruch: In $APP/.env steht kein HUBIPLAN_PROXY_GEHEIM (erst dort proxy-geheim.sh)."; cp -p "$ENV.vor-proxy-geheim" "$ENV"; exit 1 ;;
        *[!0-9a-f]*) echo "Abbruch: HUBIPLAN_PROXY_GEHEIM ist kein Hexwert."; cp -p "$ENV.vor-proxy-geheim" "$ENV"; exit 1 ;;
    esac
    # Jede nginx-Konfiguration, die an den Port der Webseite weiterleitet, muss den Kopfwert
    # einbinden, und die Datei mit dem Wert muss da sein
    PORT=$(sed -n 's/^WEB_PORT=//p' "$ENV" | tail -1)
    KONF=$(grep -ls "127.0.0.1:${PORT:-8111}" /home/*/conf/web/*/nginx.ssl.conf || true)
    OHNE=$([ -n "$KONF" ] && grep -L "hubiplan/proxy-geheim" $KONF || true)
    if [ -z "$KONF" ] || [ -n "$OHNE" ] || ! ls /etc/nginx/hubiplan/proxy-geheim*.inc > /dev/null 2>&1; then
        echo "Abbruch: Der nginx schickt den Kopfwert für die Webseite noch nicht mit."
        echo "Erst die Vorlage webseite-8111 erneuern (hubiplan/deploy/hestia/vorlagen-erneuern.sh)."
        cp -p "$ENV.vor-proxy-geheim" "$ENV"
        exit 1
    fi
    {
        echo "HUBIPLAN_PROXY_GEHEIM=$GEHEIM"
        echo "WEBSITE_PROXY_HOSTS=web"
    } >> "$ENV"
    unset GEHEIM
    echo "Kopfwert eingetragen"
else
    echo "Kopfwert herausgenommen"
fi
chmod 600 "$ENV"

PROJEKT=$(sed -n 's/^COMPOSE_PROJECT_NAME=//p' "$ENV" | tail -1)
PROJEKT=${PROJEKT:-$(basename "$SEITE")}
cd "$SEITE"
docker compose -p "$PROJEKT" -f docker-compose.yml -f docker-compose.proxy.yml up -d > /dev/null
sleep 5
PORT=$(sed -n 's/^WEB_PORT=//p' "$ENV" | tail -1)
CODE=$(curl -sS -o /dev/null -w '%{http_code}' "http://127.0.0.1:${PORT:-8111}/gesund" || true)
case "$CODE" in
    200) echo "Webseite antwortet" ;;
    *) echo "WARNUNG: Webseite antwortet nicht wie erwartet (${CODE:-keine Antwort}); zurück mit ZURUECK=1" ;;
esac
echo "### Ende $(TZ=Europe/Berlin date '+%d.%m.%Y %H:%M')"
