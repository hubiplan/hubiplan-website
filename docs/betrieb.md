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
| `/chronik/` | Text „geschichte“ aus HUBIplan, darunter die Zeitleiste: Ereignisse mit Jahr oder Zeitraum, Kapitel als Zwischenüberschriften, Sprungmarken (Kapitel, sonst ab 15 Einträgen Jahrzehnte), Bild vergrößert im Fenster (`zeitleiste.js`); mit `timeline_newest_first` neueste Einträge oben; bis zu sechs Bilder je Ereignis (`images`), im Fenster zum Blättern; Bildposition `image_position` (automatisch abwechselnd, links, rechts, groß darunter) |
| `/aemter/` | frühere und heutige Inhaber der Ämter |
| `/mitglieder/<name>/` | Mitgliederliste einer Mitgliedsart (Name, Eintrittsjahr, auf Wunsch Instrument) |
| `/in-gedenken/` | verstorbene Mitglieder mit Todesjahr, Einleitung aus der Textseite „in-gedenken“ |
| `/repertoire/` | Stücke aus dem Notenarchiv mit „im Repertoire auf der Webseite“ |
| `/presse/` | Pressespiegel (PDF oder Bild mit Quelle und Datum) |
| `/suche/?q=…` | Suche in Textseiten, Alben, Dokumenten und Terminen (Lupe im Menü) |
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

Zwischenspeicher: Antworten von HUBIplan hält die Seite `CACHE_SECONDS` lang vor (Standard
120). In der Vorschau gilt `PREVIEW_CACHE_SECONDS` (Standard 5, je Vorschau getrennt,
`0` = aus), damit nicht jedes Bild die Grunddaten der Seite neu abruft.

## Testserver

Die Webseite läuft auf `test.example.org` in `/opt/hubiplan-website` als Container
`website` im Docker-Netz `hubiplan_web` von HUBIplan. Caddy (aus HUBIplan) leitet
`https://test.example.org/webseite/` dorthin weiter und entfernt dabei `/webseite`.

- `BASE_PATH=/webseite`: Adressen der Seite beginnen mit `/webseite/`.
- `SITE_HOST_OVERRIDE=www.sv-musterstadt.test`: Alle Aufrufe gehören zur
  Demo-Webseite aus `seed_demoverein` (statt Zuordnung über den Hostnamen). Ein
  Vorschau-Link mit `?seite=<hostname>` (HUBIplan hängt ihn auf dem Testserver an) zeigt
  für die Dauer dieser Vorschau eine andere eingerichtete Webseite derselben Instanz.
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
(bei eingeschränkten Benutzerrechten mit `sudo`).

Ansehen: In HUBIplan unter Webseite › Einstellungen „Vorschau öffnen“. Die Demo-Webseite
steht im Wartungsmodus; ohne Vorschau zeigt `/webseite/` nur die Wartungsseite.

## Releases und Rollout-Protokoll

Die Webseite hat eigene Releases (`JJJJ.MM.N`, Tag `v2026.11.0`) mit
[CHANGELOG.md](../CHANGELOG.md) und [CHANGELOG.en.md](../CHANGELOG.en.md). Angelegt werden sie
mit `~/hubiplan/scripts/release.sh entwurf|taggen` im Klon dieses Repos, Ablauf wie in
`docs/releases.md` von hubiplan. `deploy/deploy.sh` nimmt auch Tags, legt die Version als
`.version` ab und schreibt je Lauf eine Zeile nach `/opt/hubiplan-website.protokoll`.

## Betrieb hinter HestiaCP

Bei einem Hosting mit HestiaCP kann die Webseite unter einer Vereinsdomain laufen,
HUBIplan beispielsweise unter `verein.example.org` (siehe `docs/echtbetrieb.md` in
hubiplan). Die Container belegen weder Port 80 noch 443:

```
Browser ──HTTPS──> nginx (HestiaCP, Let's Encrypt, Vorlage webseite-8111)
                     └─HTTP──> 127.0.0.1:8111  Container website ──> backend:8000 (HUBIplan)
```

1. **In HUBIplan** den Verein anlegen, das Modul Webseite einschalten und unter
   Webseite › Internetadresse die Domain eintragen. Status: Wartung, bis die Inhalte stehen.
2. **Lokal testen** (`scripts/test.sh origin/main` in WSL).
3. **Ausrollen**, beim ersten Mal mit den Angaben für die `.env`:

   ```bash
   DEPLOY_HOST=benutzer@server.example.org DEPLOY_SUDO=1 \
   WEBSITE_HINTER_PROXY=1 SITE_DOMAINS=<domain>,www.<domain> HUBIPLAN_HOST=verein.<domain> \
   deploy/deploy.sh origin/main
   ```

   Später reicht die erste Zeile mit `deploy/deploy.sh origin/main`.
4. **Domain umstellen** mit `deploy/hestia/umstellen.sh`: `HUSER` muss explizit den
   Hestia-Benutzer angeben, beispielsweise `HUSER=hosting-user DOMAIN=example.org`.
   Erst nur prüfen, dann `AKTION=umstellen` setzen. Das Skript sichert die bisherige Seite
   (Dateien und WordPress-Datenbank) nach
   `/root/sicherung-webseite/<Benutzer>/<Domain>/<Zeit.Zufall>/`, merkt sich die alte
   nginx-Vorlage und löscht nichts. `AKTION=zurueck` stellt die alte Vorlage wieder her.

   Auch bestehende Aufrufe müssen `HUSER` ausdrücklich setzen. Ohne die Angabe bricht
   das Skript vor jeder Serveraktion ab. Die bisherige Vorlage kann weiterhin mit
   `HUSER=hosting-user DOMAIN=example.org AKTION=zurueck` wiederhergestellt werden.

   Bei WordPress muss `wp-config.php` lesbar und höchstens 256 KiB groß sein. Die
   Automatik akzeptiert genau eine vollständige literale `define('DB_NAME', '…');`-
   Zeile, einen ASCII-Namen mit höchstens 63 Zeichen (erster Buchstabe/Ziffer,
   danach auch `_` und `-`) sowie die erfolgreiche Zuordnung zu `HUSER` durch
   `v-list-database HUSER DB_NAME json`. Dessen Ausgabe wird vollständig verworfen;
   weder Verbindungsdaten noch Konfigurationsinhalte werden protokolliert. Der
   Dump erhält zusätzlich `--` vor dem Datenbankargument. Unklare/dynamische oder
   mehrfach vorkommende Angaben, nicht lesbare Dateien und nicht bestätigte
   Eigentümerschaft führen vor Sicherung und nginx-Umstellung zum Abbruch.

   **Manueller Weg:** Externe Datenbanken, abweichende Datenbankhosts und ungewöhnliche
   WordPress-Konfigurationen müssen vorab getrennt durch die Administration geprüft
   werden. Datenbankziel und Zugangsberechtigung aus vertrauenswürdiger
   Betriebsdokumentation ermitteln, mit auf diese Datenbank begrenzten Rechten sichern
   und die Wiederherstellbarkeit prüfen. Auch Dateien und bisherige nginx-Vorlage je
   Benutzer/Domain separat sichern; erst danach die Domain bewusst in Hestia umstellen.
   Die Konfiguration nicht löschen/umbenennen und Prüfungen nicht umgehen, um die
   Automatik zu erzwingen. Das Skript hat keinen Schalter zum Überspringen der Prüfung.
   Die Namens-/Eigentümerprüfung beweist keine PHP-Laufzeitkonfiguration und keine
   externe Datenbanktopologie. [English procedure](wordpress-umstellung.en.md).

Antwortet der Container nicht (z. B. beim Ausrollen), zeigt nginx statt „502 Bad Gateway“
die Seite „Die Webseite wird gerade aktualisiert“, die sich alle 5 Sekunden neu lädt.
Antworten des Containers selbst, auch die gewollte Wartungsseite (503), bleiben
unverändert. Eine geänderte Vorlage spielt `hubiplan/deploy/hestia/vorlagen-erneuern.sh`
nach dem Ausrollen ein (siehe `hubiplan/docs/echtbetrieb.md`).
