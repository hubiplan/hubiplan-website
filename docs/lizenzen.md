# Lizenzen

Die Vereinswebseite steht unter der **AGPL-3.0-or-later** ([LICENSE](../LICENSE)), wie HUBIplan.
Dieses Dokument beschreibt fremde Bestandteile und ihre Lizenzen; es beruht auf den
Lizenzaudits vom 31.10.2026 und 10.11.2026 (Berichte im Projektordner unter `audit/`) und ist
keine anwaltliche Prüfung. Die ausführliche Beschreibung für das Gesamtsystem steht in
`hubiplan/docs/lizenzen.md`.

## Quellcode für Besucher (AGPL § 13)

Das Repository ist öffentlich (`https://github.com/hubiplan/hubiplan-website`). Jede Seite
verlinkt im Fuß „Quellcode“: `deploy/deploy.sh` legt beim Ausrollen den Commit als `.fassung`
ab, der Link zeigt dann auf `…/tree/<commit>`, also genau auf die laufende Fassung; ohne
diese Datei (Entwicklung) auf das Repository (`seite/templatetags/seite.py`, `quellcode`).
Eingespielte Designpakete bringen keine Vorlagen mit und können den Fuß nicht ersetzen. Ein
Design im Repo mit eigenem Fuß muss den Link behalten; `tests/test_designs.py` prüft das für
jedes Design. Wer eine veränderte Fassung betreibt, ändert `QUELLCODE` auf sein eigenes
öffentliches Repository.

## Was der Browser bekommt

Eigene Vorlagen, eigenes CSS und eigene Skripte; keine fremden Skripte oder Bilder, kein
Laden von fremden Servern. Einzige fremde Bestandteile sind die Schriften für Designpakete
(siehe unten). Logos, Wappen, Fotos und Texte
kommen zur Laufzeit aus HUBIplan; für ihre Rechte sorgen die Vereine (Hinweise in HUBIplan).

Symbole für Social-Media-Kanäle (`seite/templatetags/seite.py`): Die Pfade für Facebook,
TikTok und X entsprechen weitgehend [Simple Icons](https://simpleicons.org) (CC0 1.0, keine
Nennung nötig; das X-Symbol stammt wahrscheinlich aus Version 11.15.0). Die Zeichen sind
Marken der jeweiligen Unternehmen; CC0 gibt keine Markenrechte. Die Webseite nutzt sie nur als
Link auf den eigenen Kanal des Vereins (Lizenzaudit 10.11.2026, L11).

Beiträge aus Instagram und Facebook speichert HUBIplan mit Text und Bildern und gibt sie an
die Webseite weiter. Die Verbindung zu Meta gibt keine Rechte an fremden Bildern oder Musik;
Videos zeigt die Webseite nur als Vorschaubild mit Link.

## Schriften

Designpakete dürfen keine Schriften laden. Damit ein Paket trotzdem eine gängige Schrift
nutzen kann, liegen in `seite/static/seite/schriften/` **Open Sans** und **Roboto**
(Schnitte 400, 600, 700, Zeichensatz Latein) als WOFF2-Dateien, übernommen aus
[Fontsource](https://fontsource.org) 5.3.0. Beide stehen unter der **SIL Open Font License 1.1**
(Lizenztexte daneben als `OFL-open-sans.txt` und `OFL-roboto.txt`). Dazu kommt die
Schreibschrift **Great Vibes** (Schnitt 400, Latein, ebenfalls Fontsource 5.3.0, SIL OFL 1.1,
`OFL-great-vibes.txt`) für Begrüßungen. Der Browser lädt eine Schrift nur, wenn das gewählte
Design sie verwendet.

## Server

Die Python-Bibliotheken laufen nur im eigenen Container und werden nicht weitergegeben.

| Komponente | Lizenz |
|---|---|
| Django, asgiref, sqlparse, qrcode | BSD-3-Clause |
| markdown-it-py, mdurl, whitenoise, gunicorn | MIT |
| packaging | Apache-2.0 oder BSD-2-Clause |
| Hestia-Vorlagen `deploy/hestia/webseite-8111.*` | GPL-3.0 |

Die Hestia-Vorlagen sind nach den Standardvorlagen von HestiaCP 1.9.4 aufgebaut und als
solche gekennzeichnet; der GPL-Volltext liegt in `deploy/hestia/LICENSE-GPL-3.0.txt`. Sie
bleiben GPL-3.0; GPL-3.0 und AGPL-3.0 dürfen kombiniert werden (jeweils § 13). Der Kopf
jeder Vorlage nennt Herkunft und das Datum der letzten Änderung (GPL § 5a); bei jeder Änderung
das Datum anpassen.

## Offen

- **Images weitergeben:** vorher Stückliste und Lizenztexte aller Pakete im Image beilegen.
