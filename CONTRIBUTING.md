# Mitwirken an HUBIplan-Website

Danke für dein Interesse! Fehlermeldungen, Verbesserungsvorschläge und Pull Requests sind
willkommen. Contributions in English are welcome as well.

## Bevor du loslegst

- **Fehler und Ideen** als [Issue](https://github.com/hubiplan/hubiplan-website/issues) melden. Für
  größere Änderungen bitte zuerst ein Issue eröffnen und den Weg absprechen, damit keine
  Arbeit umsonst ist.
- **Sicherheitslücken** nie öffentlich, sondern wie in [SECURITY.md](SECURITY.md) beschrieben.
- **Nur erfundene Daten**: in Code, Tests, Beispielen, Bildschirmfotos und Fehlerberichten
  nie echte Namen, Anschriften, Bankverbindungen oder Fotos von Vereinsmitgliedern.
- **Keine Geheimnisse**: keine Passwörter, Schlüssel oder `.env`-Dateien einchecken.
- **Keine privaten Betriebsdetails**: interne Chat-Links und Gesprächsverläufe, reale
  Hostnamen und SSH-Zuordnungen, persönliche Rechnerpfade sowie kundenbezogene Betriebs-
  oder Freigabevermerke gehören nicht in Dateien, Commit-Nachrichten, Issues oder PR-Texte.
  Beispiele verwenden reservierte Beispieldomains und erfundene Daten; tatsächliche
  Ausrollziele und Betriebsunterlagen bleiben in privater Konfiguration.

## Pull Requests

1. Repository forken, einen Branch anlegen, Änderung mit Tests umsetzen.
2. Prüfen:
   ```bash
   ruff check . && ruff format --check .
   scripts/test.sh HEAD     # vollständiger Test im Wegwerf-Container (Linux/WSL mit Docker)
   ```
3. Pull Request gegen `main` öffnen und kurz beschreiben, was sich ändert und warum.
   Den Abschnitt „Für die Änderungshinweise“ der Vorlage auf Deutsch und Englisch ausfüllen.

Hinweise zum Stil:

- Oberfläche, Dokumentation und Commit-Nachrichten sind **deutsch**, in einfacher Sprache.
- Die Webseite liest nur die öffentliche Schnittstelle von HUBIplan, nie dessen Datenbank.
  Was öffentlich sein darf, entscheidet HUBIplan; Änderungen daran gehören nach
  [hubiplan](https://github.com/hubiplan/hubiplan).
- Neue Funktionen allgemein halten: Die Seite soll für Vereine jeder Art passen.
  Besonderheiten gehören hinter Bausteine oder Einstellungen in HUBIplan.
- Neue feste Texte gleich auch auf Englisch (`{% translate %}`/`gettext`, Katalog
  `locale/en/LC_MESSAGES/django.po` über `scripts/uebersetzung.sh`); `tests/test_sprache.py`
  schlägt sonst fehl.
- Keine Inhalte von fremden Servern (Schriften, Skripte, Einbettungen) und keine echten
  Vereinsdaten in Vorlagen, Tests oder Beispielen.
- Links auf der Webseite werden nie unterstrichen (auch nicht beim Darüberfahren); sie sind
  an Farbe und Schriftstärke erkennbar.
- Neue Abhängigkeiten müssen mit der AGPL-3.0 verträglich sein (z. B. MIT, BSD, Apache-2.0,
  LGPL, MPL-2.0). Nicht möglich: GPL-2.0-only, SSPL, „nur nicht-kommerziell“, proprietär.
  Siehe [docs/lizenzen.md](docs/lizenzen.md).
- Es gibt keine automatische CI; vor dem Merge testet der Betreuer jeden Pull Request lokal
  mit `scripts/test.sh`.

## Beitragsbedingungen

HUBIplan-Website steht wie HUBIplan unter der AGPL-3.0-or-later. Damit das Projekt auch künftig auf veränderte
Anforderungen reagieren kann (z. B. Zusatzerlaubnisse nach AGPL § 7 wie für die
Google-Bibliotheken der Android-App, oder eine spätere Lizenzanpassung), gelten für jeden
Beitrag diese Bedingungen. Mit dem Einreichen eines Pull Requests stimmst du ihnen zu:

1. **Eigene Arbeit.** Der Beitrag stammt von dir, oder du bist berechtigt, ihn unter diesen
   Bedingungen einzureichen. Enthält er fremden Code, nennst du Herkunft und Lizenz. Gehört
   dein Beitrag rechtlich deinem Arbeitgeber oder Auftraggeber, hat dieser zugestimmt.
2. **Lizenz.** Du stellst den Beitrag unter die AGPL-3.0-or-later, wie das übrige Projekt.
3. **Zusätzliches Nutzungsrecht.** Du räumst Ralf Philipsen (Philipsen EDV) als Herausgeber
   zusätzlich ein einfaches, zeitlich und räumlich unbeschränktes, unentgeltliches und
   unwiderrufliches Recht ein, deinen Beitrag auch unter anderen Lizenzbedingungen zu nutzen,
   zu bearbeiten und weiterzugeben, einschließlich Zusatzerlaubnissen nach AGPL § 7. Dieses
   Recht darf er an Nachfolger in der Herausgeberschaft übertragen. Im Gegenzug sagt der
   Herausgeber zu, deinen Beitrag stets auch unter einer von der Free Software Foundation
   oder der Open Source Initiative anerkannten freien Lizenz zugänglich zu halten.
4. **Deine Rechte bleiben.** Du behältst dein Urheberrecht und darfst deinen Beitrag
   weiterhin beliebig selbst nutzen.
5. **Nennung.** Du wirst über die Git-Historie als Urheber genannt.
6. **Keine Gewährleistung.** Du gibst den Beitrag ohne Gewährleistung, soweit das Gesetz
   dies zulässt.

Die Pull-Request-Vorlage fragt die Zustimmung mit einem Häkchen ab.

> **English summary:** By submitting a pull request you confirm that you have the right to
> contribute it, you license it under AGPL-3.0-or-later, and you additionally grant Ralf
> Philipsen (Philipsen EDV) a non-exclusive, perpetual, irrevocable, royalty-free right to
> use and distribute your contribution under other license terms as well (including
> additional permissions under AGPL section 7); in return your contribution always stays
> available under a free software license. You keep your copyright. The German text above is
> binding.
