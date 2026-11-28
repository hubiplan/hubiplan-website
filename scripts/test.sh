#!/usr/bin/env bash
# Testet einen Commit lokal in WSL (Docker), bevor er ausgerollt wird.
#
#   scripts/test.sh [Git-Referenz] [pytest-Argumente]
#
# Läuft nur, was eingecheckt ist (git archive): ruff und pytest im Container.
# Nach Erfolg wird der Stand (Git-Tree) als getestet vermerkt; deploy/deploy.sh
# rollt nur solche Stände aus.
#
# Regeln wie in hubiplan: Tests laufen nie auf dem Testserver. Höchstens zwei Testläufe
# gleichzeitig (alle Projekte), jeder höchstens 8 Kerne: das Skript holt sich einen Platz
# mit testplatz (aus hubiplan/scripts/testplatz.sh, in WSL nach ~/.local/bin installiert).
set -euo pipefail

# Release-Commit (hubiplan/docs/releases.md): Ändert ein Commit gegenüber seinem schon
# getesteten Vorgänger nur CHANGELOG.md/CHANGELOG.en.md, gilt er ohne neuen Lauf als getestet.
STATE="${HUBIPLAN_WEBSITE_TESTED_FILE:-$HOME/.local/state/hubiplan-website/tested-trees}"
nur_aenderungshinweise() {
    local c p dateien
    c=$(git rev-parse --verify --quiet "$1^{commit}" 2> /dev/null) || return 1
    p=$(git rev-parse --verify --quiet "$c^1^{commit}" 2> /dev/null) || return 1
    git rev-parse --verify --quiet "$c^2" > /dev/null 2>&1 && return 1
    grep -q "^$(git rev-parse "$p^{tree}") " "$STATE" 2> /dev/null || return 1
    dateien=$(git diff --name-only "$p" "$c")
    [ -n "$dateien" ] && ! grep -qvxE 'CHANGELOG(\.en)?\.md' <<< "$dateien"
}
if [ "$#" -le 1 ] && nur_aenderungshinweise "${1:-HEAD}"; then
    c=$(git rev-parse "${1:-HEAD}^{commit}")
    echo "$(git rev-parse "$c^{tree}") $(git rev-parse --short "$c") $(date -Iseconds) nur-aenderungshinweise" >> "$STATE"
    echo "Alles grün: $(git rev-parse --short "$c") ändert gegenüber dem getesteten Vorgänger nur die Änderungshinweise und ist als getestet vermerkt."
    exit 0
fi

if [ -z "${TESTPLATZ:-}" ]; then
    if ! command -v testplatz > /dev/null; then
        echo "Abbruch: testplatz fehlt (siehe hubiplan/docs/testserver.md, „Testplätze“)." >&2
        exit 2
    fi
    exec testplatz --kerne "${TEST_WORKERS:-4}" "$0" "$@"
fi

REF="${1:-HEAD}"
shift || true

RESULT_OK=0
WORK=""
on_exit() {
    local rc=$?
    [ -n "$WORK" ] && rm -rf "$WORK"
    if [ "$RESULT_OK" != 1 ]; then
        [ "$rc" -eq 0 ] && rc=1
        echo "FEHLGESCHLAGEN (Exit $rc): ${SHA:-$REF} ist nicht getestet." >&2
        exit "$rc"
    fi
}
trap on_exit EXIT

resolve() { git rev-parse --verify --quiet "$REF^{commit}" 2> /dev/null || true; }
COMMIT=$(resolve)
if [ -z "$COMMIT" ]; then
    echo "$REF fehlt im Klon, hole von allen Remotes …"
    git fetch --all --quiet || echo "Warnung: git fetch ist fehlgeschlagen." >&2
    COMMIT=$(resolve)
fi
if [ -z "$COMMIT" ]; then
    echo "Abbruch: $REF ist auch nach git fetch nicht im Klon $(pwd)." >&2
    exit 2
fi
SHA=$(git rev-parse --short "$COMMIT")
TREE=$(git rev-parse "$COMMIT^{tree}")

PYTEST_ARGS="${*:--q}"

WORK=$(mktemp -d)
echo "Teste $SHA ($(git log -1 --format=%s "$COMMIT")) lokal …"
git archive --format=tar "$COMMIT" | tar -x -C "$WORK"
start=$(date +%s)

# Abgleich mit HUBIplan: Der Container sieht den Nachbarordner nicht. Liegt dort ein
# hubiplan-Klon, gehen Adressen und Form der Schnittstelle aus dessen frisch geholtem main mit in den
# Lauf; tests/test_schnittstelle.py prüft die Kopie dagegen.
NACHBAR="$(dirname "$(git rev-parse --show-toplevel)")/hubiplan"
if git -C "$NACHBAR" rev-parse --git-dir > /dev/null 2>&1; then
    # Wie scripts/zug.sh in hubiplan: Ist origin des Nachbarklons selbst ein lokaler Klon, zählt
    # dessen origin. main wird frisch geholt, damit nicht gegen einen alten Stand verglichen wird.
    QUELLE="$NACHBAR"
    url=$(git -C "$NACHBAR" remote get-url origin 2> /dev/null || true)
    if [ -d "$url" ] && git -C "$url" remote get-url origin > /dev/null 2>&1; then
        QUELLE="$url"
    fi
    STAND=refs/webseite/hubiplan-main
    if ! git -C "$QUELLE" fetch --quiet origin "+refs/heads/main:$STAND" 2> /dev/null; then
        echo "FEHLER: main von hubiplan ließ sich nicht holen ($QUELLE)." >&2
        exit 1
    fi
    mkdir -p "$WORK/nachbar-config"
    for datei in api_routen.json webseite_schnittstelle.json; do
        if ! git -C "$QUELLE" show "$STAND:backend/config/$datei" > "$WORK/nachbar-config/$datei" 2> /dev/null; then
            echo "FEHLER: backend/config/$datei fehlt im main von hubiplan ($(git -C "$QUELLE" rev-parse --short "$STAND"))." >&2
            exit 1
        fi
    done
    echo "Abgleich mit hubiplan main $(git -C "$QUELLE" rev-parse --short "$STAND")"
else
    echo "Hinweis: kein hubiplan-Klon im Nachbarordner, die Kopie der Schnittstelle bleibt ungeprüft."
fi

# Eigener Image-Name je Lauf: zwei gleichzeitige Läufe dürfen sich nicht überschreiben
IMG="hubiplan-website-test:$(date +%s)-$$"
docker build -q --build-arg DEV=1 -t "$IMG" "$WORK" > /dev/null
rc=0
docker run --rm --cpuset-cpus="$TESTPLATZ_CPUS" --user 0 --entrypoint sh "$IMG" \
    -c "ruff check . && ruff format --check . > /dev/null && python -m pytest -p no:cacheprovider $PYTEST_ARGS" || rc=$?
docker image rm "$IMG" > /dev/null 2>&1 || true
[ "$rc" -eq 0 ] || exit "$rc"
echo "Webseite: ruff und Tests ok ($(($(date +%s) - start)) s)"

# nginx-Vorlage für HestiaCP (deploy/hestia/), aus dem geprüften Stand
if [ -x "$WORK/scripts/pruefe-proxy.sh" ]; then
    "$WORK/scripts/pruefe-proxy.sh" "$WORK" --cpuset-cpus="$TESTPLATZ_CPUS"
fi

if [ "$#" -gt 0 ]; then
    echo "Grün (Teil-Lauf, nicht als getestet vermerkt): $SHA"
    RESULT_OK=1
    exit 0
fi
mkdir -p "$(dirname "$STATE")"
echo "$TREE $SHA $(date -Iseconds)" >> "$STATE"
echo "Alles grün: $SHA ist als getestet vermerkt."
RESULT_OK=1
