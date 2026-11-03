"""Lokale Shell-Stubs: keine Hestia-Installation, keine echte Datenbank/kein nginx."""

import gzip
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def migration(tmp_path):
    binary = tmp_path / "bin"
    binary.mkdir()

    def executable(name, source):
        path = binary / name
        path.write_text("#!/bin/sh\nset -eu\n" + source)
        path.chmod(0o755)

    executable("v-list-web-domain", "printf '%s\\n' '{\"PROXY\":\"legacy\"}'\n")
    executable("curl", "exit 0\n")
    executable("sleep", "exit 0\n")
    executable(
        "head",
        """
if [ "${UNREADABLE_CONFIG:-0}" = 1 ] && [ "$1" = -c ]; then exit 1; fi
exec /usr/bin/head "$@"
""",
    )
    executable(
        "v-list-database",
        """
printf 'owner-check\\t%s\\t%s\\t%s\\n' "$1" "$2" "$3" >> "$LOG"
printf '%s\\n' 'synthetic-private-connection-output'
printf '%s\\n' 'synthetic-private-error-output' >&2
[ "$1" = own ] && [ "$2" = "$OWN_DATABASE" ]
""",
    )
    executable(
        "mysqldump",
        """
printf 'dump' >> "$LOG"
for arg; do printf '\\t%s' "$arg" >> "$LOG"; done
printf '\\n' >> "$LOG"
printf '%s\\n' 'synthetic SQL only'
exit "${DUMP_STATUS:-0}"
""",
    )
    executable("v-change-web-domain-proxy-tpl", 'printf \'nginx-change\\t%s\\n\' "$*" >> "$LOG"\n')
    source = (ROOT / "deploy/hestia/umstellen.sh").read_text()
    # Redirect only paths/command lookup; execute the real parser and control flow.
    source = source.replace("export PATH=", f"export PATH={binary}:")
    source = source.replace("SICHERUNG=/root/sicherung-webseite", f"SICHERUNG={tmp_path}/backups")
    source = source.replace("/home/$HUSER/web/$DOMAIN/public_html", str(tmp_path / "public_html"))
    source = source.replace("APP=/opt/hubiplan-website", f"APP={tmp_path}/app")
    source = source.replace(
        "TPL=/usr/local/hestia/data/templates/web/nginx", f"TPL={tmp_path}/templates"
    )
    script = tmp_path / "migration.sh"
    script.write_text(source)
    (tmp_path / "public_html").mkdir()
    templates = tmp_path / "app/deploy/hestia"
    templates.mkdir(parents=True)
    (tmp_path / "templates").mkdir()
    for name in ("webseite-8111.tpl", "webseite-8111.stpl"):
        (templates / name).write_text("synthetic template")
    log = tmp_path / "calls"

    def run(config, **extra):
        wp = tmp_path / "public_html/wp-config.php"
        wp.write_text(config)
        result = subprocess.run(  # noqa: S603 - fixed local Bash/script, synthetic fixture data
            ["/bin/bash", str(script)],
            env={
                **os.environ,
                "HUSER": "own",
                "DOMAIN": "club.example",
                "AKTION": "umstellen",
                "LOG": str(log),
                "OWN_DATABASE": "own_wp",
                **extra,
            },
            capture_output=True,
            text=True,
            timeout=10,
        )
        calls = log.read_text().splitlines() if log.exists() else []
        assert "synthetic-private-connection-output" not in result.stdout + result.stderr
        assert "synthetic-private-error-output" not in result.stdout + result.stderr
        return result, calls, tmp_path / "backups"

    return run


@pytest.mark.parametrize(
    "definition",
    [
        "define('DB_NAME', '--all-databases');",
        "define('DB_NAME', '--tab=/tmp/unwanted');",
        "define('DB_NAME', '../foreign');",
        "define('DB_NAME', 'own_wp;whoami');",
        "define('DB_NAME', getenv('DATABASE'));",
        "define('DB_NAME', 'own_' . 'wp');",
        "define('DB_NAME', 'own_wp');\ndefine('DB_NAME', 'own_wp');",
        "// define('DB_NAME', 'own_wp');",
        "/*\ndefine('DB_NAME', 'own_wp');\n*/",
        "define('DB_NAME', '');",
        "define('DB_NAME', '" + "x" * 64 + "');",
        "/* no database configured */",
    ],
)
def test_option_oder_unklarer_name_bricht_vor_dump_und_umstellung_ab(migration, definition):
    result, calls, backups = migration("<?php\n" + definition + "\n")
    assert result.returncode != 0
    assert "DB_NAME" in result.stdout
    assert calls == []  # Not even Hestia's database query receives an unsafe argument.
    assert not backups.exists()


def test_fremde_datenbank_wird_nicht_gesichert_oder_umgestellt(migration):
    result, calls, backups = migration("<?php\ndefine('DB_NAME', 'other_wp');\n")
    assert result.returncode != 0
    assert calls == ["owner-check\town\tother_wp\tjson"]
    assert not backups.exists()


def test_nicht_lesbare_konfiguration_bricht_kontrolliert_ab(migration):
    result, calls, backups = migration(
        "<?php\ndefine('DB_NAME', 'own_wp');\n", UNREADABLE_CONFIG="1"
    )
    assert result.returncode != 0
    assert "DB_NAME" in result.stdout
    assert calls == []
    assert not backups.exists()


def test_zu_grosse_konfiguration_wird_auch_mit_zeilenumbruch_an_der_grenze_abgewiesen(migration):
    prefix = "<?php\ndefine('DB_NAME', 'own_wp');\n"
    config = prefix + " " * (262144 - len(prefix)) + "\ndefine('DB_NAME', 'other_wp');\n"
    result, calls, backups = migration(config)
    assert result.returncode != 0
    assert calls == []
    assert not backups.exists()


def test_eigener_name_mit_bindestrich_ist_sicher_als_datenbankargument(migration):
    result, calls, _ = migration(
        "<?php\ndefine('DB_NAME', 'own-site_wp');\n", OWN_DATABASE="own-site_wp"
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert calls[1] == "dump\t--single-transaction\t--routines\t--\town-site_wp"


@pytest.mark.parametrize(
    "definition",
    [
        "define('DB_NAME', 'own_wp');",
        'define ( "DB_NAME" , "own_wp" ); // local database',
        "/** WordPress configuration */\ndefine('DB_NAME', 'own_wp');",
    ],
)
def test_eigene_literale_datenbank_hat_argumentende_und_wird_gesichert(migration, definition):
    result, calls, backups = migration("<?php\n" + definition + "\n")
    assert result.returncode == 0, result.stdout + result.stderr
    assert calls[0] == "owner-check\town\town_wp\tjson"
    assert calls[1] == "dump\t--single-transaction\t--routines\t--\town_wp"
    assert calls[2].startswith("nginx-change\t")
    (dump,) = backups.rglob("datenbank-own_wp.sql.gz")
    assert gzip.decompress(dump.read_bytes()) == b"synthetic SQL only\n"


def test_fehlerhafter_dump_verhindert_nginx_umstellung(migration):
    result, calls, _ = migration("<?php\ndefine('DB_NAME', 'own_wp');\n", DUMP_STATUS="1")
    assert result.returncode != 0
    assert not any(call.startswith("nginx-change") for call in calls)
