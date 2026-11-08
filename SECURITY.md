# Sicherheit

Die HUBIplan-Website zeigt öffentliche Daten aus HUBIplan, einer Vereinsverwaltung mit
personenbezogenen Daten. Hinweise auf Sicherheitslücken nehmen wir deshalb sehr ernst und sind
für jede Meldung dankbar.

*Reports in English are welcome; see the [English summary](#english-summary) at the end.*

## Lücke melden

Bitte **kein öffentliches Issue**, sondern vertraulich über GitHub:
[Report a vulnerability](https://github.com/hubiplan/hubiplan-website/security/advisories/new)
(im Repository unter **Security › Report a vulnerability**).

Hilfreich sind:

- betroffene Fassung (Commit) und betroffener Teil (z. B. Seite, Vorlage, Einstellung),
- Schritte zum Nachvollziehen, am besten mit den Demodaten von HUBIplan (`seed_testdata`)
  oder der nachgebildeten Schnittstelle der Tests,
- eingeschätzte Auswirkung: Was kann ein Besucher sehen oder auslösen, was er nicht dürfte?

## Was dann passiert

- Wir bestätigen den Eingang in der Regel innerhalb von 7 Tagen.
- Wir prüfen die Meldung, halten dich auf dem Laufenden und stimmen eine Korrektur mit dir ab.
- Die Korrektur erscheint zuerst; Einzelheiten veröffentlichen wir danach als
  Sicherheitshinweis (GitHub Security Advisory), auf Wunsch mit Nennung deines Namens.
- Bitte gib uns bis zur Korrektur, höchstens 90 Tage ab Meldung, Zeit, bevor du Einzelheiten
  veröffentlichst.

## Unterstützte Fassungen

Die Webseite wird fortlaufend aus `main` entwickelt und zusammen mit HUBIplan in Releases
(`JJJJ.MM.N`, siehe [CHANGELOG.md](CHANGELOG.md)) veröffentlicht; es gibt keine
Release-Zweige. Korrekturen gibt es für das neueste Release und den aktuellen Stand von `main`.

## Umfang

Gemeint ist der Code in diesem Repository: Darstellung, Vorlagen, Abruf der Schnittstelle,
Medien-Weiterleitung, Kontaktformular, Ergebnisseiten, Vorschau und Wartungsmodus sowie die
Skripte und Vorlagen fürs Ausrollen. Besonders interessant sind:

- Cross-Site-Scripting oder eingeschleuste Inhalte über Texte und Daten aus HUBIplan,
- Zugriff auf Seiten im Wartungsmodus oder auf Vorschauen ohne gültigen Vorschau-Link,
- Abrufe über `/medien/…`, die mehr als Bilder und Logos aus HUBIplan erreichen,
- Daten eines anderen Vereins auf einer Webseite (Zuordnung über den Hostnamen),
- Umgehung des Spamschutzes im Kontaktformular oder Missbrauch des Formulars zum Versand an
  beliebige Empfänger,
- Inhalte, die nur in der Vorschau oder im Wartungsmodus sichtbar sein dürften, in Caches
  oder über die Live-Abfrage der Ergebnisseiten,
- widerrufene oder gelöschte Inhalte, die der Zwischenspeicher für den Ausfall von HUBIplan
  weiter ausliefert, obwohl HUBIplan wieder antwortet,
- Designpakete, die fremde Inhalte nachladen oder eigenen Vorlagen- oder Skriptcode ausführen,
- Suche, Galerie oder Belegung, die mehr zeigen als die öffentliche Schnittstelle freigibt.

Zeigt die Webseite Daten, die HUBIplan gar nicht hätte herausgeben dürfen, liegt der Fehler
meist in HUBIplan; dann bitte [dort melden](https://github.com/hubiplan/hubiplan/security/advisories/new).

Nicht gemeint sind Lücken in Fremdsoftware (bitte dort melden), reine Last- oder
Überlastungsangriffe, Social Engineering sowie Befunde ohne Auswirkung (z. B. fehlende
Header ohne Angriffsweg).

## Regeln fürs Prüfen

- Prüfe **nur gegen eine eigene Installation** mit erfundenen Daten, z. B. mit
  HUBIplan per `docker compose up` und `seed_testdata`.
- Keine Angriffe auf fremde Vereinswebseiten, HUBIplan-Instanzen oder echte Vereinsdaten, keine
  Überlastungsangriffe.
- Stößt du doch auf echte personenbezogene Daten, greife nicht weiter darauf zu, speichere
  nichts und melde es uns.

Wer sich an diese Regeln hält und in gutem Glauben handelt, hat von uns keine rechtlichen
Schritte zu erwarten.

## English summary

Please do **not** open a public issue. Report vulnerabilities privately via
[GitHub private vulnerability reporting](https://github.com/hubiplan/hubiplan-website/security/advisories/new).
If the website shows data that HUBIplan should never have published, the bug is most likely
in [HUBIplan](https://github.com/hubiplan/hubiplan/security/advisories/new). We usually
acknowledge reports within 7 days and ask you to keep details private until a fix is
available, for at most 90 days. Fixes go into `main` and the latest release; there are no release branches.
Test only against your own installation with made-up data, never against other clubs'
websites or real data. Good-faith research that follows these rules will not face legal
action from us.
