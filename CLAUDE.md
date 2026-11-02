# Hinweise für die Arbeit an hubiplan-website

Feste Regeln von Ralf (gelten wie im Hauptprojekt `hubiplan`):

- **Nie Tests auf dem Testserver ausführen**, auch keine Test-Container.
  Tests laufen lokal in WSL auf Ralfs Rechner, danach wird ausgerollt.
- **Höchstens zwei Testläufe gleichzeitig, jeder höchstens 8 Kerne**, projektübergreifend für
  alle Projekte auf Ralfs PC: `scripts/test.sh` holt sich einen Platz mit `testplatz`
  (aus `hubiplan/scripts/testplatz.sh`, siehe `hubiplan/docs/testserver.md`).
- Keine Passwörter oder Geheimnisse ins Repo oder in Chats.
- **Keine echten Vereinsdaten im Repository** (z. B. Königslisten, Namen, Fotos).
  Echte Daten kommen nur im Echtbetrieb über HUBIplan. Repo und Testserver: nur erfundene Daten.
- Die Webseite liest nur die öffentliche Schnittstelle von HUBIplan, nie die Datenbank.
  Datenschutzregeln gehören nach `hubiplan`, nicht hierher.
- **Jeder PR füllt „Für die Änderungshinweise“** der PR-Vorlage aus (Deutsch und Englisch).
  Releases nur auf Ralfs Wort, mit `~/hubiplan/scripts/release.sh` (siehe `hubiplan/docs/releases.md`).
- CI (GitHub Actions) nur von Hand (workflow_dispatch); keine automatischen Auslöser.
- Sprache in Oberfläche, Doku und Commits: Deutsch.
- **Neue Rahmentexte gleich auch auf Englisch** (`{% translate %}`/`gettext`, Katalog
  `locale/en/LC_MESSAGES/django.po` über `scripts/uebersetzung.sh`); `tests/test_sprache.py` prüft das.
- Links auf der Webseite nie unterstreichen (auch nicht beim Darüberfahren); Links sind an Farbe
  und Schriftstärke erkennbar.
