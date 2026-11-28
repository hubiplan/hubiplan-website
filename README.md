# HUBIplan-Website

**Öffentliche Vereinswebseiten, die sich aus den Daten von [HUBIplan](https://github.com/hubiplan/hubiplan) speisen.**

Termine, Vorstand, Untereinheiten, Würdenträger, Chronik und Satzung pflegt der Verein ohnehin
in HUBIplan. Die HUBIplan-Website macht daraus eine eigene Webseite unter der Domain des
Vereins, ohne zweites Redaktionssystem und ohne doppelte Pflege. Texte, Bilder, Abschnitte und
Gestaltung bearbeitet der Vorstand ebenfalls in HUBIplan, mit Entwurf, Vorschau und
Veröffentlichen.

> **English:** HUBIplan-Website renders public club websites from the public API of
> [HUBIplan](https://github.com/hubiplan/hubiplan), a free membership management system. It is
> a stateless Django app without a database. Each website can show its fixed texts in
> German or English; club content stays as entered in HUBIplan. The developer documentation
> is in German; issues and security reports in English are welcome.

## Inhalt

- [Funktionen](#funktionen)
- [Aufbau](#aufbau)
- [Technik](#technik)
- [Entwicklung](#entwicklung)
- [Selbst betreiben](#selbst-betreiben)
- [Mitwirken](#mitwirken)
- [Sicherheit](#sicherheit)
- [Lizenz](#lizenz)

## Funktionen

- **Startseite aus Bausteinen**, die HUBIplan ein- und ausschaltet, ordnet und auf Wunsch
  umbenennt (eigener Name in Menü, Überschrift und Seitentitel): Begrüßung,
  Bilderkarussell (Wechselzeit, Startbild oder zufälliges Titelbild, Knöpfe immer oder bei
  Mauszeiger) oder Titelfoto als Bühne, nächste Termine als Liste oder Karten, Geburtstage,
  aktuelle Würdenträger (auch als Band oder Podium), aktuelle Ergebnisse, Untereinheiten
- **Eigene Abschnitte** auf Startseite und Textseiten, mit Hintergrund und Breite: Text, Text
  mit Bild, Banner, Knopfleiste, Kacheln, hervorgehobener Termin mit Countdown, Album-Auszug,
  Zitat, Ansprechpartner, häufige Fragen, Partner und Sponsoren, Anfahrt mit Routenlink,
  Termine einer Art, Dokument, Video als Link (ohne Einbettung), Chronik-Auszug, Zahlen,
  Trenner und weitere; Bild neben, über oder unter dem Text; Kacheln und Knöpfe führen auch
  zu einer Untereinheit
- **Hinweisleiste** mit Zeitraum oben auf allen Seiten, in mehreren Stilen, mit Symbol, Knopf
  und Countdown; **Titelbild** je Textseite, Seitentitel auf Wunsch als Band über die ganze
  Breite, mehrere Kopfbilder im Wechsel, eigenes Kopfbild für schmale Bildschirme
- **Mitglied werden**: Einleitung, Mitgliedsarten mit Beitrag und Link zum
  Online-Mitgliedsantrag in HUBIplan (die Eingaben macht der Besucher dort, nicht auf der
  Webseite)
- **Aktuelles**: eigene Beiträge des Vereins (mit eigener Seite und Archiv) und Beiträge von Instagram und Facebook, nach Datum gemischt
- **Galerie** mit Albenübersicht, Unteralben und Bildern groß im Fenster mit Bildzähler;
  „Foto: …“ unter dem Bild und Bildnachweis im Impressum
- **Vorstand und Ansprechpartner** mit Funktionsadressen und Ehrungen, als Personenkarten oder
  Liste; Ehrungen auf Wunsch als eine Karte je Person
- **Untereinheiten** (z. B. Abteilungen oder Züge) mit eigenen Unterseiten aus Abschnitten und
  auf Wunsch eigenem Designpaket; der Pfad folgt der Bezeichnung in HUBIplan
- **Terminkalender** als Liste oder Monatskalender, Filter je Untereinheit, Kalender-Abo fürs
  Smartphone mit QR-Code; freigegebene Anhänge im Termin-Fenster
- **Veranstaltungen mit Anmeldung**: eigene Seite unter `/veranstaltung/<adresse>/` mit
  Eckdaten, Preisen, freien Plätzen und Knopf zum Anmeldeformular in HUBIplan, auf Wunsch mit
  Menüpunkt bis zum Ende der Veranstaltung
- **Würden** mit aktuellen Trägern und Chronik, **Ehrungen**, **Geschichte** mit Chronik als
  Zeitleiste (Epochen auch als flaches Band) und Ämtern, Satzung, Dokumente mit Vorschau und
  weitere Textseiten; lange Listen am Bildschirm zweispaltig
- **Belegung** von Räumen und Anlagen als Wochenansicht mit Kalender-Abo
- für Musikvereine und Kapellen: **Mitgliederlisten** je Mitgliedsart (nur mit Einwilligung)
  und **Repertoire** aus dem Notenarchiv
- **Suche** über alle öffentlichen Texte (Startseite, Abschnitte, Textseiten, Untereinheiten),
  Alben, Dokumente und Termine
- **Ergebnisse** der Wettbewerbe (wenn der Verein das Modul nutzt): Ranglisten, Reihen und
  Wanderpokale; laufende Wettbewerbe aktualisieren sich von selbst
- **Kontaktformular**: Der Browser schickt direkt an HUBIplan, Spamschutz ohne Fremddienst
- **Impressum, Datenschutzhinweise und Erklärung zur Barrierefreiheit**, auch im
  Wartungsmodus erreichbar
- **Wartungsmodus und Vorschau-Link** aus HUBIplan, Vorschau des Entwurfs auch im Rahmen in
  HUBIplan; ist HUBIplan kurz nicht erreichbar (etwa beim Ausrollen) oder drosselt es einen
  Besucher, zeigt die Seite den letzten guten Stand weiter
- **Sprache je Webseite**: Deutsch (Standard) oder Englisch für alle festen Texte, Menü,
  Datumsangaben und Meldungen; Vereinsdaten (Namen, Texte, Bezeichnungen) bleiben, wie sie in
  HUBIplan stehen. Impressum und Datenschutz zeigen auf Englisch einen Hinweis, dass die
  deutsche Fassung maßgeblich ist.
- **Menü** mit Links nach außen und einem hervorgehobenen Knopf (z. B. „Mitglied werden“)
- **Designpakete**: mehrere Standardlayouts (z. B. Klassisch, Festlich, Seitenleiste, Bühne,
  Zeitung), eigene Farben mit Verläufen, Kopfbild und CSS aus HUBIplan, exportier- und
  importierbar; **Feinabstimmung** mit festen Stufen statt CSS (Schrift, Breite, Abstände,
  Ecken, Kopf, Menü, Fuß, dunkle Darstellung, Kontrast, Wasserzeichen …), in HUBIplan nach
  Bereichen der Seite gegliedert; Farben und Wappen des Vereins, breite Logos scharf im Kopf,
  Favicon aus dem Wappen; **Schriften zur Auswahl** (Open Sans, Roboto, Source Sans 3, Crimson
  Pro, Oswald, Atkinson Hyperlegible, eine Fraktur und eine Schreibschrift), die auf der Seite
  selbst liegen (keine fremden Server); passt sich an Monitor, Tablet und Smartphone an
- **Kurze Ladezeiten**: Bilder in passender Größe als AVIF oder WebP, komprimierte Stile und
  Skripte (Brotli), Schriften werden vorgeladen, große Dokumente werden gestreamt
- **Barrierearm**: Farben gegen die jeweilige Fläche geprüft, Tastaturbedienung, markierter
  Menüpunkt der aktuellen Seite

Alle Seiten und Adressen: [docs/betrieb.md](docs/betrieb.md#seiten).

## Aufbau

Die Webseite ist reine **Darstellung**. Sie liest ausschließlich die öffentliche, versionierte
Schnittstelle von HUBIplan (`/api/public/site/v1/…`) und hat keinen Zugriff auf dessen
Datenbank. Welche Daten öffentlich sind (Einwilligungen, Widerspruch, Kennzeichen an Rollen),
entscheidet allein HUBIplan. So kann auch eine fehlerhafte Webseite keine geschützten
Mitgliederdaten zeigen.

```text
Browser ──HTTPS──> Webserver ──> Container website ──> HUBIplan (/api/public/site/v1/)
```

Ein Container bedient alle Vereine einer HUBIplan-Instanz; welche Webseite gemeint ist,
ergibt sich aus dem Hostnamen. Bilder und Logos liefert die Seite selbst aus (`/medien/…`),
damit der Browser keine zweite Adresse braucht. Konzept: [docs/konzept.md](docs/konzept.md).

## Technik

| Teil | Technik |
| --- | --- |
| Anwendung | Python 3.13, Django 5.2 LTS ohne Datenbank |
| Texte | markdown-it-py (Markdown aus HUBIplan) |
| QR-Codes | qrcode (Kalender-Abo) |
| Auslieferung | gunicorn, whitenoise, Docker (schreibgeschützt, ohne Zusatzrechte) |

```text
config/           Einstellungen (nur Umgebungsvariablen), URLs
seite/            Abruf der Schnittstelle, Ansichten, Vorlagen, CSS
locale/           englische Rahmentexte (django.po)
tests/            pytest mit nachgebildeter Schnittstelle (tests/fake.py)
deploy/           Ausrollen, Servereinrichtung, HestiaCP-Vorlagen
scripts/          test.sh (vollständiger Test), uebersetzung.sh (Texte sammeln),
                  schnittstelle.sh (Abgleich mit HUBIplan nachziehen)
docs/             Konzept, Betrieb und Lizenzen
```

## Entwicklung

Alle Einstellungen kommen aus Umgebungsvariablen (Vorlage [.env.example](.env.example),
Beschreibung in `config/settings.py`). Lokal gegen ein HUBIplan auf Port 8000 (siehe
[Ausprobieren mit Docker](https://github.com/hubiplan/hubiplan#ausprobieren-mit-docker), mit
Demodaten aus `seed_demoverein`):

```bash
python -m venv .venv && . .venv/bin/activate
pip install --require-hashes -r requirements.txt && pip install -r requirements-dev.txt
DJANGO_DEBUG=1 HUBIPLAN_API_URL=http://localhost:8000 \
  SITE_HOST_OVERRIDE=www.sv-musterstadt.test python manage.py runserver 8001
```

`SITE_HOST_OVERRIDE` ordnet alle Aufrufe der Demo-Webseite zu; ohne die Variable entscheidet
der Hostname. Die Demo-Webseite steht im Wartungsmodus; ansehen über „Vorschau öffnen“ in
HUBIplan unter Webseite › Einstellungen.

**Tests:**

```bash
ruff check . && ruff format --check .   # schnelle Prüfung
scripts/test.sh <commit>                # vollständiger Test in einem Wegwerf-Container
```

Die Tests nutzen eine nachgebildete Schnittstelle mit erfundenen Daten (`tests/fake.py`) und
brauchen kein laufendes HUBIplan. `scripts/test.sh` prüft nur den eingecheckten Stand und holt
sich dafür einen Testplatz mit `testplatz` (aus
[hubiplan/scripts/testplatz.sh](https://github.com/hubiplan/hubiplan/blob/main/scripts/testplatz.sh),
Installation steht im Kopf der Datei). Tests laufen nie auf einem Server.

**Abgleich mit HUBIplan:** Die Nachbildung wird bei jedem Testaufruf mit dem Server verglichen
(`tests/schnittstelle.py`): Jede Adresse muss es in HUBIplan geben, und die Antworten dürfen
nur Felder haben, die HUBIplan liefert. Die Vorlage dafür ist eine Kopie aus dem Server
(`tests/data/hubiplan_schnittstelle.json`). Der Server legt in seinen Tests einen Prüfverein an,
der jedes Feld belegt; Ausnahmen gibt es deshalb keine. Tests, die absichtlich falsche Daten
liefern, tragen den Merker `falsche_daten`. In der Gegenrichtung zeichnet
`tests/test_echte_antworten.py` jede Seite aus den echten Antworten des Servers
(`tests/data/hubiplan_antworten.json`: Demoverein, Prüfverein, dessen Vorschau, Demokapelle und
ein leerer Verein) und folgt dabei jedem Link. Nach Änderungen an der öffentlichen
Schnittstelle zieht `scripts/schnittstelle.sh` beide Dateien aus einem hubiplan-Klon im
Nachbarordner neu. `scripts/test.sh` holt dafür den aktuellen `main` von hubiplan (ist `origin`
des Nachbarklons selbst ein lokaler Klon, über dessen `origin`), vergleicht die Kopie damit und
schlägt fehl, wenn sie veraltet ist oder sich `main` nicht holen lässt.

**Aufbau des Programms:** `seite/api.py` ruft HUBIplan auf (mit Zwischenspeicher), `seite/site.py`
ordnet die Anfrage einer Webseite zu, `seite/views/` bereitet die Daten je Bereich für die
Vorlagen auf, `seite/hilfen/` enthält die Filter und Bausteine der Vorlagen und
`seite/farben.py` die Farbrechnung. Termine, Beiträge und Wettbewerbe gehen als feste
Datentypen in die Vorlagen (`seite/daten.py`): In Tests und Entwicklung ist das Lesen eines
Feldes, das es nicht gibt, ein Fehler (`STRENGE_DATEN`); im Betrieb bleibt es beim leeren Wert.
Programmdateien bleiben unter 800 Zeilen (`tests/test_dateigroesse.py`).

**Übersetzung:** Feste Texte stehen deutsch in Vorlagen (`{% translate %}`), Python (`_()`)
und für die Skripte in `JS_TEXTE` (`seite/hilfen/anzeige.py`). `scripts/uebersetzung.sh`
sammelt sie in `locale/en/LC_MESSAGES/django.po`; dort die englischen Texte eintragen.
`tests/test_sprache.py` schlägt fehl, solange ein Text fehlt. Die Sprache einer Webseite
kommt aus HUBIplan (Feld `language` der Grunddaten, unbekannt = Deutsch).

## Selbst betreiben

Voraussetzung ist eine laufende HUBIplan-Instanz auf demselben Server; die Webseite hängt
sich in deren Docker-Netz `hubiplan_web`. Ausgerollt wird per SSH, nur nach grünem Test:

```bash
scripts/test.sh <commit>
DEPLOY_HOST=root@server.example.org deploy/deploy.sh <commit>
```

- Beim ersten Ausrollen entsteht auf dem Server eine `.env` aus [.env.example](.env.example)
  mit zufälligem Schlüssel. Angaben für den Betrieb hinter einem vorhandenen Webserver
  (`WEBSITE_HINTER_PROXY=1`, `SITE_DOMAINS`, `HUBIPLAN_HOST`) stehen im Kopf von
  [deploy/deploy.sh](deploy/deploy.sh).
- Die neue Fassung wird neben der laufenden gebaut; wird sie nicht gesund, geht es
  automatisch zurück.
- In HUBIplan den Verein anlegen, das Modul Webseite einschalten und unter Webseite ›
  Internetadresse die Domain eintragen.

Einzelheiten, Wartungsschalter, Zwischenspeicher, Sicherheitsgrenzen der Designpakete und ein
Beispiel hinter HestiaCP: [docs/betrieb.md](docs/betrieb.md).

## Mitwirken

Fehlermeldungen, Ideen und Pull Requests sind willkommen: [CONTRIBUTING.md](CONTRIBUTING.md).
Bitte nur erfundene Daten in Code, Tests und Bildschirmfotos, nie echte Vereinsdaten wie
Namen, Königslisten oder Fotos. Datenschutzregeln (was öffentlich sein darf) gehören nach
[hubiplan](https://github.com/hubiplan/hubiplan), nicht hierher.

## Sicherheit

Sicherheitslücken bitte **nicht** als öffentliches Issue melden, sondern vertraulich über
[GitHub](https://github.com/hubiplan/hubiplan-website/security/advisories/new). Einzelheiten:
[SECURITY.md](SECURITY.md).

## Lizenz

Copyright © 2026 Ralf Philipsen (Philipsen EDV)

HUBIplan-Website ist freie Software: Sie dürfen sie unter den Bedingungen der **GNU Affero
General Public License**, wie von der Free Software Foundation veröffentlicht, weitergeben
und/oder ändern, entweder gemäß Version 3 der Lizenz oder (nach Ihrer Wahl) jeder späteren
Version (`AGPL-3.0-or-later`), wie HUBIplan selbst.

Die Software wird in der Hoffnung verbreitet, dass sie nützlich ist, aber **ohne jede
Gewährleistung**, sogar ohne die implizite Gewährleistung der Marktreife oder der Eignung für
einen bestimmten Zweck. Einzelheiten stehen in der Lizenz. Den vollständigen Lizenztext
(englisch, maßgeblich) enthält die Datei [LICENSE](LICENSE).

Wer eine veränderte Fassung der Webseite öffentlich betreibt, muss ihren Quellcode unter
derselben Lizenz zugänglich machen; die Fußzeile jeder Seite verlinkt dazu den Quellcode der
laufenden Fassung. Lizenzen der Abhängigkeiten und der HestiaCP-Vorlagen (GPL-3.0):
[docs/lizenzen.md](docs/lizenzen.md).
