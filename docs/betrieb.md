# Betrieb der Vereinswebseite

## Seiten

| Adresse | Inhalt |
| --- | --- |
| `/` | Begrüßung, nächste Termine, aktuelle Majestäten, Untereinheiten |
| `/termine/` | Termine nach Monaten, Filter je Untereinheit, Kalender-Abo mit QR-Code |
| `/vorstand/` | Vorstand, Ansprechpartner, Ehrungen |
| `/zuege/` bzw. `/einheiten/` | Untereinheiten (Pfad je nach Bezeichnung in HUBIplan); auf der Seite einer Untereinheit auf Wunsch ein Link zu ihrer eigenen Homepage (neuer Tab) |
| `/majestaeten/` | Würden mit aktuellen Trägern und Chronik |
| `/majestaeten/<kennung>/` | eine Würde (Unterpunkt des Menüs „Würdenträger“) |
| `/ergebnisse/` | Wettbewerbsergebnisse (Modul Wettbewerbe): laufende Wettbewerbe, Ergebnisse je Jahr, Reihen, Wanderpokale |
| `/ergebnisse/<kennung>/` | Rangliste eines Wettbewerbs; solange er läuft, fragt der Browser alle 15 s den Stand ab (`…/stand/`) und lädt nur bei einer Änderung die Rangliste neu (`…/tabelle/`) |
| `/ergebnisse/reihe/<kennung>/` | Archiv einer Wettbewerbsreihe: Titelträger und Sieger je Jahr |
| `/ehrungen/` | Ehrungen, wenn in HUBIplan „Würden und Ehrungen unter einem Menüpunkt“ an ist (dann nicht beim Vorstand) |
| `/chronik/` | Text „geschichte“ aus HUBIplan, darunter die Zeitleiste: Ereignisse mit Jahr oder Zeitraum, Kapitel als Zwischenüberschriften, Sprungmarken (Kapitel, sonst ab 15 Einträgen Jahrzehnte), Bild vergrößert im Fenster (`zeitleiste.js`) |
| `/aemter/` | frühere und heutige Inhaber der Ämter |
| `/geschichte/` | alte Adresse, leitet zu `/chronik/` bzw. `/aemter/` weiter |
| `/seite/<name>/` | weitere Textseiten aus HUBIplan |
| `/kontakt/` | Kontaktformular (der Browser schickt direkt an HUBIplan) |
| `/impressum/`, `/datenschutz/` | auch im Wartungsmodus erreichbar |
| `/vorschau/?schluessel=…` | Vorschau-Link aus HUBIplan einlösen (Cookie, max. 8 Stunden) |
| `/medien/…` | Bilder und Logos aus HUBIplan über diese Seite |
| `/gesund` | Healthcheck des Containers |

Welche Bereiche erscheinen, legt HUBIplan fest (Bausteine der Webseite). Im Wartungsmodus
zeigt die Seite nur die Wartungsseite, Impressum und Datenschutz, außer in der Vorschau.
Ein allgemeiner Wartungsschalter: `MAINTENANCE=true` oder die Datei `/tmp/wartung` im
Container.

## Testserver

Die Webseite läuft auf `test.example.org` in `/opt/hubiplan-website` als Container
`website` im Docker-Netz `hubiplan_web` von HUBIplan. Caddy (aus HUBIplan) leitet
`https://test.example.org/webseite/` dorthin weiter und entfernt dabei `/webseite`.

- `BASE_PATH=/webseite`: Adressen der Seite beginnen mit `/webseite/`.
- `SITE_HOST_OVERRIDE=www.hubertus-grimlinghausen.test`: Alle Aufrufe gehören zur
  Demo-Webseite aus `seed_testdata` (statt Zuordnung über den Hostnamen).
- Die Seite ruft HUBIplan intern unter `http://backend:8000` auf und setzt dabei den
  Hostnamen `test.example.org`. Logos und Bilder (`/media/…`) holt sie intern bei Caddy
  (`HUBIPLAN_MEDIA_URL=http://web:8081`, Port nur im Docker-Netz; über die eigene
  öffentliche Adresse erreicht der Container den Server nicht).

Ausrollen (nur lokal getestete Stände, Tests nie auf dem Server):

```bash
scripts/test.sh origin/main
deploy/deploy.sh origin/main
```

Beim ersten Ausrollen entsteht `/opt/hubiplan-website/.env` aus `.env.example` mit einem
zufälligen Schlüssel, der nur auf dem Server liegt.

Die neue Fassung wird in `/opt/hubiplan-website.neu` gebaut, während die alte läuft; erst
danach werden die Ordner getauscht. Wird der Container nicht gesund, geht es automatisch
zurück (die fehlerhafte Fassung bleibt in `….fehler`). Von Hand zurück (ein zweiter
Aufruf geht wieder vor): `cd /opt/hubiplan-website && sh deploy/zurueck.sh`
(auf Dogado mit `sudo`).

Ansehen: In HUBIplan unter Webseite › Einstellungen „Vorschau öffnen“. Die Demo-Webseite
steht im Wartungsmodus; ohne Vorschau zeigt `/webseite/` nur die Wartungsseite.

## Echtbetrieb (Dogado)

Auf Ralfs Dogado-Server (HestiaCP) läuft die Webseite unter der Hauptdomain des Vereins.
HUBIplan läuft dort unter `verein.…` (siehe `docs/echtbetrieb.md` in hubiplan). Wie
HUBIplan belegt die Webseite weder Port 80 noch 443:

```
Browser ──HTTPS──> nginx (HestiaCP, Let's Encrypt, Vorlage webseite-8111)
                     └─HTTP──> 127.0.0.1:8111  Container website ──> backend:8000 (HUBIplan)
```

1. **In HUBIplan** den Verein anlegen, das Modul Webseite einschalten und unter
   Webseite › Internetadresse die Domain eintragen. Status: Wartung, bis die Inhalte stehen.
2. **Lokal testen** (`scripts/test.sh origin/main` in WSL).
3. **Ausrollen**, beim ersten Mal mit den Angaben für die `.env`:

   ```bash
   SSH=/mnt/c/Windows/System32/OpenSSH/ssh.exe DEPLOY_HOST=administrator@dogado DEPLOY_SUDO=1 \
   WEBSITE_HINTER_PROXY=1 SITE_DOMAINS=<domain>,www.<domain> HUBIPLAN_HOST=verein.<domain> \
   deploy/deploy.sh origin/main
   ```

   Später reicht die erste Zeile mit `deploy/deploy.sh origin/main`.
4. **Domain umstellen** mit `deploy/hestia/umstellen.sh` (erst nur prüfen, dann
   `AKTION=umstellen`). Das Skript sichert die bisherige Seite (Dateien und
   WordPress-Datenbank) nach `/root/sicherung-webseite/<Datum>/`, merkt sich die alte
   nginx-Vorlage und löscht nichts. `AKTION=zurueck` stellt die alte Vorlage wieder her.

Antwortet der Container nicht (z. B. beim Ausrollen), zeigt nginx statt „502 Bad Gateway“
die Seite „Die Webseite wird gerade aktualisiert“, die sich alle 5 Sekunden neu lädt.
Antworten des Containers selbst, auch die gewollte Wartungsseite (503), bleiben
unverändert. Eine geänderte Vorlage spielt `hubiplan/deploy/hestia/vorlagen-erneuern.sh`
nach dem Ausrollen ein (siehe `hubiplan/docs/echtbetrieb.md`).
