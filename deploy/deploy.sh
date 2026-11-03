#!/usr/bin/env bash
# Rollt die Vereinswebseite aus (neben HUBIplan, gleiches Docker-Netz).
#
#   deploy/deploy.sh               # Testserver, aktueller Commit (HEAD)
#   deploy/deploy.sh origin/main   # bestimmter Branch/Commit
#   deploy/deploy.sh v2026.11.0    # Release (Tag), siehe hubiplan/docs/releases.md
#
# Hosting hinter HestiaCP, siehe docs/betrieb.md:
#   DEPLOY_HOST=benutzer@server.example.org DEPLOY_SUDO=1 \
#   deploy/deploy.sh origin/main
# Beim ersten Mal zusätzlich (nur für die neue .env):
#   WEBSITE_HINTER_PROXY=1 SITE_DOMAINS=beispiel.de,www.beispiel.de HUBIPLAN_HOST=verein.beispiel.de
#
# Übertragen wird nur, was eingecheckt ist (git archive). Die .env auf dem Server
# bleibt erhalten; fehlt sie, entsteht sie aus .env.example mit einem zufälligen
# Schlüssel, der nur auf dem Server liegt.
#
# Ausgerollt wird nur ein Stand, der vorher lokal mit scripts/test.sh erfolgreich
# getestet wurde (gleicher Git-Tree). Tests laufen nie auf dem Server.
# Voraussetzung: HUBIplan läuft dort (Docker-Netz hubiplan_web).
set -euo pipefail

# SSH-Ziel des Testservers steht nur lokal (eine Zeile, z. B. root@test.example.org)
TESTSERVER_DATEI="${HUBIPLAN_TESTSERVER_FILE:-$HOME/.config/hubiplan/testserver}"
HOST="${DEPLOY_HOST:-$(head -n1 "$TESTSERVER_DATEI" 2>/dev/null || true)}"
if [ -z "$HOST" ]; then
    echo "Abbruch: Kein Ziel. DEPLOY_HOST=benutzer@server setzen oder das SSH-Ziel des" >&2
    echo "Testservers in $TESTSERVER_DATEI eintragen." >&2
    exit 1
fi
DIR="${DEPLOY_DIR:-/opt/hubiplan-website}"
SSH="${SSH:-ssh}"
if [ -n "${DEPLOY_KEY:-}" ]; then
    SSH_ARGS=(-i "$DEPLOY_KEY" -o IdentitiesOnly=yes)
else
    SSH_ARGS=()
fi
# Als normaler Benutzer anmelden und mit sudo arbeiten (DEPLOY_SUDO=1)
SUDO=""
[ -n "${DEPLOY_SUDO:-}" ] && SUDO="sudo "
# Angaben für eine neue .env (nur beim ersten Ausrollen genutzt)
SETUP_ENV=""
for v in WEBSITE_HINTER_PROXY WEB_PORT SITE_DOMAINS HUBIPLAN_HOST; do
    if [ -n "${!v:-}" ]; then
        case "${!v}" in
            *[!A-Za-z0-9.,-]*) echo "Abbruch: $v enthält unerlaubte Zeichen." >&2; exit 1 ;;
        esac
        SETUP_ENV="$SETUP_ENV $v=${!v}"
    fi
done
REF="${1:-HEAD}"
# Einmal auf den Commit festlegen: Geprüft, übertragen und vermerkt wird genau dieser
# Stand, auch wenn sich HEAD oder ein Branch inzwischen ändert (Gesamtaudit 31.10.b, INF-F05)
REF=$(git rev-parse --verify "$REF^{commit}")

TREE=$(git rev-parse "$REF^{tree}")
STATE="${HUBIPLAN_WEBSITE_TESTED_FILE:-$HOME/.local/state/hubiplan-website/tested-trees}"
if ! grep -q "^$TREE " "$STATE" 2>/dev/null; then
    echo "Abbruch: $(git rev-parse --short "$REF") ist nicht lokal getestet." >&2
    echo "Erst scripts/test.sh $REF ausführen (in WSL), dann ausrollen." >&2
    exit 1
fi

echo "Rolle $(git rev-parse --short "$REF") nach $HOST:$DIR aus …"
# Neue Fassung neben der laufenden entpacken (mit deren .env); server-setup.sh baut,
# tauscht die Ordner und geht bei einem Fehler automatisch zurück
NEU="$DIR.neu"
"$SSH" "${SSH_ARGS[@]}" "$HOST" "${SUDO}rm -rf '$NEU' && ${SUDO}mkdir -p '$NEU' && ${SUDO}chmod 755 '$NEU' && if [ -f '$DIR/.env' ]; then ${SUDO}cp -p '$DIR/.env' '$NEU/.env'; fi"
git archive --format=tar "$REF" | "$SSH" "${SSH_ARGS[@]}" "$HOST" "${SUDO}tar -x --no-same-owner -C '$NEU'"
git rev-parse "$REF" | "$SSH" "${SSH_ARGS[@]}" "$HOST" "${SUDO}tee '$NEU/.fassung' > /dev/null"
# Versionsnummer (hubiplan/docs/releases.md): Release-Tag „v2026.11.0“ → „2026.11.0“; Stand nach dem
# letzten Release → „2026.11.0+3.0a5d21e“ (3 Commits danach); ohne Release nur der Commit.
version_von() {
    local tag
    if tag=$(git describe --tags --exact-match --match 'v[0-9]*' "$1" 2> /dev/null); then
        echo "${tag#v}"
    elif tag=$(git describe --tags --abbrev=7 --match 'v[0-9]*' "$1" 2> /dev/null); then
        # v2026.11.0-3-g0a5d21e
        local rest="${tag%-g*}"
        echo "${rest%-*}+${rest##*-}.${tag##*-g}" | sed 's/^v//'
    else
        git rev-parse --short=7 "$1"
    fi
}
VERSION=$(version_von "$REF")
case "$VERSION" in
    *[!A-Za-z0-9.+]*) echo "Abbruch: unerwartete Versionsnummer „$VERSION“." >&2; exit 1 ;;
esac
echo "$VERSION" | "$SSH" "${SSH_ARGS[@]}" "$HOST" "${SUDO}tee '$NEU/.version' > /dev/null"
echo "Version $VERSION"

# Rollout-Protokoll neben dem Programmordner (bleibt beim Ordnertausch erhalten):
# eine Zeile je Lauf mit Zeit (UTC), Commit, Version und Ergebnis
protokoll() {
    local zeile
    zeile="$(date -u +%Y-%m-%dT%H:%M:%SZ) $(git rev-parse --short=7 "$REF") $VERSION $1"
    echo "$zeile" | "$SSH" "${SSH_ARGS[@]}" "$HOST" "${SUDO}tee -a '$DIR.protokoll' > /dev/null" || \
        echo "Warnung: Rollout-Protokoll $DIR.protokoll nicht geschrieben." >&2
}

if "$SSH" "${SSH_ARGS[@]}" "$HOST" "cd '$NEU' && ${SUDO}env$SETUP_ENV ZIEL='$DIR' sh deploy/server-setup.sh"; then
    protokoll ausgerollt
else
    rc=$?
    protokoll "fehlgeschlagen ($rc)"
    exit "$rc"
fi
