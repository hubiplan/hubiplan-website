"""Real deployment script control flow, with local fake Hestia/Docker executables."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def executable(path, source):
    path.write_text("#!/bin/sh\nset -eu\n" + source)
    path.chmod(0o755)


def test_hestia_sicherungen_nach_benutzer_und_domain(tmp_path):
    binary = tmp_path / "bin"
    binary.mkdir()
    executable(binary / "v-list-web-domain", 'printf \'{"PROXY": "legacy-%s"}\\n\' "$2"\n')
    executable(
        binary / "v-change-web-domain-proxy-tpl", 'printf "%s %s %s\\n" "$1" "$2" "$3" >> "$LOG"\n'
    )
    executable(binary / "curl", "exit 0\n")
    executable(binary / "sleep", "exit 0\n")
    # Only filesystem roots and command lookup are redirected; production control
    # flow, naming, manifest verification and rollback selection remain unchanged.
    source = (ROOT / "deploy/hestia/umstellen.sh").read_text()
    source = source.replace("export PATH=", f"export PATH={binary}:")
    source = source.replace("SICHERUNG=/root/sicherung-webseite", f"SICHERUNG={tmp_path}/backups")
    source = source.replace(
        "/home/$HUSER/web/$DOMAIN/public_html", f"{tmp_path}/home/$HUSER/web/$DOMAIN/public_html"
    )
    source = source.replace("APP=/opt/hubiplan-website", f"APP={tmp_path}/app")
    source = source.replace(
        "TPL=/usr/local/hestia/data/templates/web/nginx", f"TPL={tmp_path}/templates"
    )
    script = tmp_path / "migration.sh"
    script.write_text(source)
    templates = tmp_path / "app/deploy/hestia"
    templates.mkdir(parents=True)
    (tmp_path / "templates").mkdir()
    for name in ("webseite-8111.tpl", "webseite-8111.stpl"):
        (templates / name).write_text("test")
    log = tmp_path / "changes"

    def run(user, domain, action):
        web = tmp_path / "home" / user / "web" / domain / "public_html"
        web.mkdir(parents=True, exist_ok=True)
        return subprocess.run(  # noqa: S603 - fixed local scripts and synthetic arguments
            ["/bin/bash", str(script)],
            env={**os.environ, "HUSER": user, "DOMAIN": domain, "AKTION": action, "LOG": str(log)},
            capture_output=True,
            text=True,
        )

    for user, domain in (("one", "one.example"), ("one", "two.example"), ("two", "one.example")):
        result = run(user, domain, "umstellen")
        assert result.returncode == 0, result.stderr + result.stdout
    # Repeated same-minute migration creates another unique directory.
    assert run("one", "one.example", "umstellen").returncode == 0
    assert len(list((tmp_path / "backups/one/one.example").iterdir())) == 2
    result = run("one", "one.example", "zurueck")
    # Hestia template names have no dots: our fixture deliberately tests fail-closed
    # validation, then supplies a valid recorded template for the actual rollback.
    assert result.returncode != 0
    backups = sorted((tmp_path / "backups/one/one.example").iterdir())
    (backups[-1] / "nginx-vorlage").write_text("legacy-one\n")
    assert run("one", "one.example", "zurueck").returncode == 0
    assert log.read_text().splitlines()[-1] == "one one.example legacy-one"
    (backups[-1] / "zuordnung").write_text("one\ntwo.example\n")
    before = log.read_text()
    assert run("one", "one.example", "zurueck").returncode != 0
    assert log.read_text() == before


@pytest.mark.parametrize(
    "image",
    ["own:latest", "registry.example:5000/team/own:latest", "registry.example:5000/team/own"],
)
def test_docker_raeumt_nur_eigenes_frueheres_image_auf(tmp_path, image):
    binary = tmp_path / "bin"
    binary.mkdir()
    rollback_name = image.rsplit(":", 1)[0] if ":" in image.rsplit("/", 1)[-1] else image
    executable(
        binary / "docker",
        """
printf '%s\n' "$*" >> "$LOG"
case "$*" in
  'compose -p own config --images') echo own:latest;;
  'image inspect -f {{.Id}} own:vorher') cat "$ROLLBACK";;
  'image inspect -f {{.Id}} own:latest') cat "$CURRENT";;
  'image inspect -f {{json .RepoTags}} sha256:former-own-rollback') echo "${TAGS:-[]}";;
  'image inspect -f {{json .RepoDigests}} sha256:former-own-rollback') echo '[]';;
  'tag own:latest own:vorher') cp "$CURRENT" "$ROLLBACK";;
  'compose -p own build') echo sha256:new > "$CURRENT";;
  'compose -p own ps -q website') echo website-container;;
  'inspect -f {{.State.Health.Status}} website-container') echo healthy;;
esac
""".replace("own:latest", image).replace("own:vorher", rollback_name + ":vorher"),
    )
    (tmp_path / ".env").write_text("COMPOSE_PROJECT_NAME=own\n")
    current, rollback, log = (tmp_path / n for n in ("current", "rollback", "commands"))
    current.write_text("sha256:current\n")
    rollback.write_text("sha256:former-own-rollback\n")
    result = subprocess.run(  # noqa: S603 - fixed local scripts and synthetic arguments
        ["/bin/sh", str(ROOT / "deploy/server-setup.sh")],
        cwd=tmp_path,
        env={
            **os.environ,
            "PATH": f"{binary}:{os.environ['PATH']}",
            "LOG": str(log),
            "CURRENT": str(current),
            "ROLLBACK": str(rollback),
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    calls = log.read_text().splitlines()
    assert "image rm sha256:former-own-rollback" in calls
    assert not any("prune" in call or "image rm -f" in call for call in calls)
    assert rollback.read_text() == "sha256:current\n"

    # A neighbour retaining even one tag prevents image-ID deletion.
    log.write_text("")
    current.write_text("sha256:current\n")
    rollback.write_text("sha256:former-own-rollback\n")
    result = subprocess.run(  # noqa: S603 - fixed local scripts and synthetic arguments
        ["/bin/sh", str(ROOT / "deploy/server-setup.sh")],
        cwd=tmp_path,
        env={
            **os.environ,
            "PATH": f"{binary}:{os.environ['PATH']}",
            "LOG": str(log),
            "CURRENT": str(current),
            "ROLLBACK": str(rollback),
            "TAGS": '["neighbour:stable"]',
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert not any(call.startswith("image rm ") for call in log.read_text().splitlines())
