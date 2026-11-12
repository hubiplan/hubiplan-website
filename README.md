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
  Bilderkarussell (Wechselzeit und Startbild aus HUBIplan), nächste Termine, Geburtstage,
  aktuelle Würdenträger, aktuelle Ergebnisse, Untereinheiten
- **Eigene Abschnitte** auf Startseite und Textseiten, mit Hintergrund und Breite: Text, Text
  mit Bild, Banner, Knopfleiste, Kacheln, hervorgehobener Termin mit Countdown, Album-Auszug,
  Zitat, Ansprechpartner, häufige Fragen, Partner und Sponsoren, Anfahrt mit Routenlink,
  Termine einer Art, Dokument, Video als Link (ohne Einbettung), Chronik-Auszug, Zahlen und
  Trenner
- **Hinweisleiste** mit Zeitraum oben auf allen Seiten, **Titelbild** je Textseite
- **Mitglied werden**: Einleitung, Mitgliedsarten mit Beitrag und Link zum
  Online-Mitgliedsantrag in HUBIplan (die Eingaben macht der Besucher dort, nicht auf der
  Webseite)
- **Aktuelles**: eigene Beiträge des Vereins von Instagram und Facebook
- **Galerie** mit Albenübersicht, Unteralben und Bildern groß im Fenster
- **Vorstand und Ansprechpartner** mit Funktionsadressen und Ehrungen, als Karten oder Liste
- **Untereinheiten** (z. B. Abteilungen oder Züge) mit eigenen Unterseiten; der Pfad folgt
  der Bezeichnung in HUBIplan
- **Terminkalender** als Liste oder Monatskalender, Filter je Untereinheit, Kalender-Abo fürs
  Smartphone mit QR-Code
- **Würden** mit aktuellen Trägern und Chronik, **Ehrungen**, **Geschichte** mit Chronik als
  Zeitleiste und Ämtern, Satzung, Dokumente und weitere Textseiten
- **Belegung** von Räumen und Anlagen als Wochenansicht mit Kalender-Abo
- für Musikvereine und Kapellen: **Mitgliederlisten** je Mitgliedsart (nur mit Einwilligung)
  und **Repertoire** aus dem Notenarchiv
- **Suche** über Textseiten, Alben, Dokumente und Termine
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
  Ecken, Kopf, Menü, Fuß …); Farben und Wappen des Vereins, Favicon aus dem Wappen; Schriften
  liegen auf der Seite selbst (keine fremden Server); passt sich an Monitor, Tablet und
  Smartphone an

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
scripts/          test.sh (vollständiger Test), uebersetzung.sh (Texte sammeln)
docs/             Konzept, Betrieb und Lizenzen
```

## Entwicklung

Alle Einstellungen kommen aus Umgebungsvariablen (Vorlage [.env.example](.env.example),
Beschreibung in `config/settings.py`). Lokal gegen ein HUBIplan auf Port 8000 (siehe
[Ausprobieren mit Docker](https://github.com/hubiplan/hubiplan#ausprobieren-mit-docker), mit
Demodaten aus `seed_demoverein`):

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
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

**Übersetzung:** Feste Texte stehen deutsch in Vorlagen (`{% translate %}`), Python (`_()`)
und für die Skripte in `JS_TEXTE` (`seite/templatetags/seite.py`). `scripts/uebersetzung.sh`
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
