#!/bin/bash
# Stellt eine Domain in HestiaCP auf die Vereinswebseite um (Hosting hinter einem Reverse-Proxy).
# Voraussetzung: deploy/deploy.sh ist mit WEBSITE_HINTER_PROXY=1 gelaufen, der Container
# lauscht also auf 127.0.0.1:8111.
#
# Aufruf vom lokalen Entwicklungsrechner (PowerShell), läuft als root auf dem Server:
#   nur prüfen:  Get-Content -Raw deploy\hestia\umstellen.sh | ssh benutzer@server.example.org "sudo env HUSER=hosting-user DOMAIN=example.org bash -s"
#   umstellen:   Get-Content -Raw deploy\hestia\umstellen.sh | ssh benutzer@server.example.org "sudo env HUSER=hosting-user DOMAIN=example.org AKTION=umstellen bash -s"
#   zurück:      Get-Content -Raw deploy\hestia\umstellen.sh | ssh benutzer@server.example.org "sudo env HUSER=hosting-user DOMAIN=example.org AKTION=zurueck bash -s"
#
# Umstellen sichert vorher die bisherige Seite (Dateien und, bei WordPress, die
# Datenbank) nach /root/sicherung-webseite/<Benutzer>/<Domain>/<Zeit.Zufall>/ und merkt sich die alte
# nginx-Vorlage. Gelöscht wird nichts: Dateien und Datenbank bleiben, wo sie sind.
# Hestia lädt nginx nur neu (reload), andere Websites und Mail laufen weiter.
set -euo pipefail
export PATH=/usr/local/hestia/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

HUSER=${HUSER:?HUSER fehlt, z. B. HUSER=hosting-user}
DOMAIN=${DOMAIN:?DOMAIN fehlt, z. B. DOMAIN=example.org}
[[ "$HUSER" =~ ^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$ ]] || { echo "Ungültiger HUSER"; exit 1; }
[[ "$DOMAIN" =~ ^[a-z0-9][a-z0-9.-]{0,251}[a-z0-9]$ && "$DOMAIN" != *..* ]] || { echo "Ungültige DOMAIN (ASCII/Punycode verwenden)"; exit 1; }
VORLAGE=webseite-8111
PORT=8111
APP=/opt/hubiplan-website
TPL=/usr/local/hestia/data/templates/web/nginx
SICHERUNG=/root/sicherung-webseite/$HUSER/$DOMAIN
AKTION=${AKTION:-pruefen}

echo "### Start $(TZ=Europe/Berlin date '+%d.%m.%Y %H:%M') ($AKTION)"
v-list-web-domain "$HUSER" "$DOMAIN" > /dev/null || { echo "Abbruch: Web-Domain $DOMAIN fehlt."; exit 1; }
feld() { v-list-web-domain "$HUSER" "$DOMAIN" json | sed -n "s/.*\"$1\": *\"\([^\"]*\)\".*/\1/p" | head -1; }
ALT=$(feld PROXY)
WEBROOT=/home/$HUSER/web/$DOMAIN/public_html

# wp-config.php gehört zur bisherigen Website: niemals als PHP/Shell ausführen.
# Nur eine einzelne, vollständige literale DB_NAME-Zeile ist automatisch eindeutig.
wordpress_datenbank() {
    local config=$1 inhalt anzahl name LC_ALL=C
    [ -f "$config" ] && [ -r "$config" ] || return 1
    # Sentinel erhält abschließende Zeilenumbrüche für die genaue Bytegrenze.
    inhalt=$(head -c 262145 -- "$config" && printf '.') || return 1
    inhalt=${inhalt%.}
    [ "${#inhalt}" -le 262144 ] || return 1
    anzahl=$(printf '%s\n' "$inhalt" | grep -c DB_NAME || true)
    [ "$anzahl" = 1 ] || return 1
    name=$(printf '%s\n' "$inhalt" |
        sed -e '/\/\*.*\*\//d' -e '/\/\*/,/\*\//d' |
        sed -nE "s/^[[:space:]]*define[[:space:]]*\([[:space:]]*(['\"])DB_NAME\1[[:space:]]*,[[:space:]]*(['\"])([^'\"]*)\2[[:space:]]*\)[[:space:]]*;[[:space:]]*((\/\/|#).*)?$/\3/p")
    [[ "$name" =~ ^[a-zA-Z0-9][a-zA-Z0-9_-]{0,62}$ ]] || return 1
    printf '%s\n' "$name"
}

echo "--- Stand"
echo "nginx-Vorlage: $ALT · Aliase: $(feld ALIAS) · SSL: $(feld SSL)"
if [ -f "$WEBROOT/wp-config.php" ]; then echo "WordPress in $WEBROOT"; else echo "Kein WordPress in $WEBROOT"; fi
du -sh "$WEBROOT" 2> /dev/null || true
if curl -fsS -o /dev/null "http://127.0.0.1:$PORT/gesund"; then echo "Webseite antwortet auf 127.0.0.1:$PORT"; else echo "Webseite antwortet NICHT auf 127.0.0.1:$PORT"; fi
ls -1 "$SICHERUNG" 2> /dev/null | sed 's/^/vorhandene Sicherung: /' || true

case "$AKTION" in
pruefen)
    ;;
umstellen)
    [ "$ALT" = "$VORLAGE" ] && { echo "Ist schon umgestellt."; exit 0; }
    [ -n "$ALT" ] || { echo "Abbruch: bisherige nginx-Vorlage unbekannt."; exit 1; }
    curl -fsS -o /dev/null "http://127.0.0.1:$PORT/gesund" || { echo "Abbruch: erst die Webseite ausrollen."; exit 1; }
    DB=''
    if [ -e "$WEBROOT/wp-config.php" ] || [ -L "$WEBROOT/wp-config.php" ]; then
        DB=$(wordpress_datenbank "$WEBROOT/wp-config.php") || {
            echo "Abbruch: DB_NAME ist nicht eindeutig als sicherer literaler Hestia-Datenbankname lesbar. Manuelle Sicherung und Umstellung erforderlich."
            exit 1
        }
        # Nur Exitstatus: die Hestia-Ausgabe kann vertrauliche Verbindungsdaten enthalten.
        v-list-database "$HUSER" "$DB" json > /dev/null 2>&1 || {
            echo "Abbruch: Datenbank ist diesem Hestia-Benutzer nicht bestätigt zugeordnet. Manuelle Sicherung und Umstellung erforderlich."
            exit 1
        }
    fi
    umask 077
    mkdir -p "$SICHERUNG"
    ZIEL=$(mktemp -d "$SICHERUNG/$(date +%Y-%m-%d_%H%M%S.%N).XXXXXX")
    printf '%s\n%s\n' "$HUSER" "$DOMAIN" > "$ZIEL/zuordnung"
    echo "--- 1) Sicherung nach $ZIEL"
    echo "$ALT" > "$ZIEL/nginx-vorlage"
    tar -czf "$ZIEL/public_html.tar.gz" -C "$(dirname "$WEBROOT")" public_html
    if [ -n "$DB" ]; then
        mysqldump --single-transaction --routines -- "$DB" | gzip > "$ZIEL/datenbank-$DB.sql.gz"
        echo "Datenbank $DB gesichert"
    fi
    ls -lh "$ZIEL"
    echo "--- 2) nginx-Vorlage $VORLAGE"
    install -m 644 -o root -g root "$APP/deploy/hestia/$VORLAGE.tpl" "$APP/deploy/hestia/$VORLAGE.stpl" "$TPL/"
    v-change-web-domain-proxy-tpl "$HUSER" "$DOMAIN" "$VORLAGE" '' yes
    ;;
zurueck)
    LETZTE=$(find "$SICHERUNG" -mindepth 1 -maxdepth 1 -type d 2> /dev/null | sort | tail -1)
    [ -n "$LETZTE" ] || { echo "Abbruch: keine Sicherung gefunden."; exit 1; }
    [[ "$(cat "$LETZTE/zuordnung")" = "$(printf '%s\n%s' "$HUSER" "$DOMAIN")" ]] || { echo "Abbruch: Sicherung gehört nicht zu dieser Domain/diesem Benutzer."; exit 1; }
    VORHER=$(cat "$LETZTE/nginx-vorlage")
    [[ "$VORHER" =~ ^[a-zA-Z0-9_-]+$ ]] || { echo "Abbruch: ungültige gesicherte Vorlage."; exit 1; }
    echo "--- Zurück auf nginx-Vorlage $VORHER (aus $LETZTE)"
    v-change-web-domain-proxy-tpl "$HUSER" "$DOMAIN" "$VORHER" '' yes
    ;;
*)
    echo "Unbekannte AKTION: $AKTION (pruefen, umstellen, zurueck)"
    exit 1
    ;;
esac

if [ "$AKTION" != pruefen ]; then
    echo "--- Prüfung von außen"
    sleep 2
    for u in "http://$DOMAIN/" "https://$DOMAIN/" "https://www.$DOMAIN/" "https://$DOMAIN/impressum/"; do
        curl -sS -o /dev/null -w "$u -> %{http_code} %{redirect_url}\n" "$u" || true
    done
fi
echo "### Ende $(TZ=Europe/Berlin date '+%d.%m.%Y %H:%M')"
