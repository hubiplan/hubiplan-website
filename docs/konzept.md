# Vereinswebseite mit Daten aus HUBIplan – Architektur

Die öffentliche Vereinswebseite stellt freigegebene Inhalte aus HUBIplan dar. Die
Verwaltung der Inhalte und ihre Freigabe liegen in HUBIplan; dieses Repository enthält
die Darstellung und allgemeine Anleitungen. Die aktuellen Seiten und Einstellungen
beschreibt [betrieb.md](betrieb.md).

## Verantwortlichkeiten

| HUBIplan | Vereinswebseite |
| --- | --- |
| Vereinsdaten, Rollen, Würden, Einwilligungen und Widersprüche verwalten | Nur die freigegebene öffentliche Schnittstelle lesen |
| Inhalte, Domains, Menüs, Bausteine und Designs je Einheit verwalten | Seitenvorlagen und Designs darstellen |
| Vorschauzugänge ausstellen und prüfen | Vorschauzugang gegen ein geschütztes Cookie tauschen |
| Kontaktformular prüfen und Nachrichten über den Mail-Ausgang versenden | Kontaktformular und dessen Rückmeldungen anzeigen |

Die Webseite hat keine eigene Datenbank und keinen direkten Zugriff auf Mitgliederdaten.
Ein Container kann mehrere eingerichtete Webseiten bedienen; die Zuordnung ergibt sich
aus den in HUBIplan verwalteten Domains. Für lokale Beispiele lässt sich der Hostname
mit `SITE_HOST_OVERRIDE` festlegen.

## Inhalte und Bausteine

Eine Einheit richtet ihre Webseite ausdrücklich in HUBIplan ein. Welche Inhalte und
Untereinheiten erscheinen, wird dort je Webseite festgelegt. Die Darstellung umfasst:

- Startseite mit Begrüßung, nächsten Terminen und wählbaren Bausteinen.
- Vorstand, Ansprechpartner und Untereinheiten mit jeweils freigegebenen Kontaktwegen.
- Würdenträger, Ehrungen und Chronik aus den veröffentlichten Daten.
- Termine mit Kalenderansicht und Kalender-Abo sowie Wettbewerbsergebnisse.
- Textseiten, öffentliche Dokumente und reine Links zu Social-Media-Kanälen.
- Impressum, Datenschutzhinweise und Erklärung zur Barrierefreiheit.

Texte, Fotos und andere Vereinsinhalte werden in HUBIplan gepflegt und gesichert.
Echte Mitgliederlisten, historische Personenlisten, Fotos oder Vereinsdokumente gehören
nicht in dieses Repository. Beispiele und Bildschirmfotos verwenden erfundene Daten.

## Veröffentlichung und Vorschau

HUBIplan entscheidet, welche Daten öffentlich sein dürfen. Die Webseite übernimmt die
freigegebene Sicht, statt eigene Datenschutzentscheidungen aus Mitgliederdaten abzuleiten.
Personenbezogene Angaben und Fotos erscheinen nur entsprechend den Einstellungen,
Einwilligungen und Widersprüchen in HUBIplan.

| Zustand | Öffentlichkeit | Berechtigte |
| --- | --- | --- |
| Aus | Keine öffentliche Seite | Vorschau gemäß HUBIplan-Freigabe |
| Wartung | Wartungsseite mit erreichbarem Impressum und Datenschutz | Vorschau der vollständigen Seite |
| Öffentlich | Freigegebene Seite | Freigegebene Seite |

Ein Vorschau-Link wird in HUBIplan ausgestellt und auf der Webseite gegen ein zeitlich
begrenztes Cookie eingetauscht. Vorschauinhalte bleiben von öffentlich zwischengespeicherten
Antworten getrennt. Die Vorschau darf nicht von Suchmaschinen aufgenommen werden.
In der Vorschau zeigt HUBIplan den Entwurf der Gestaltung (Design, Farben, Stilregler, Kopfbild,
Startseite); Besucher sehen nur den veröffentlichten Stand. Nur Vorschau-Anfragen darf HUBIplan
selbst in einem Rahmen zeigen (`frame-ancestors` mit der Adresse aus `HUBIPLAN_PUBLIC_URL`),
alle anderen Seiten bleiben mit `frame-ancestors 'none'` unrahmbar.

## Darstellung und Anbindung

Die Seite wird serverseitig mit Django-Vorlagen gerendert. Antworten der öffentlichen
Schnittstelle werden kurz zwischengespeichert; die Vorschau hat einen getrennten,
kürzeren Zwischenspeicher. Medien und Designpakete kommen über die freigegebenen
Schnittstellen aus HUBIplan.

Stilregler (HUBIplan › Webseite › Gestaltung › Feinabstimmung) kommen als `style` in der
öffentlichen Schnittstelle, nur mit den verstellten Reglern. Die Seite nimmt davon nur bekannte
Regler und Stufen (`seite/stil.py`), schreibt sie als `data-st-…` an das `<html>`-Element und
lädt `stil.css` mit festen Regeln je Stufe. Ohne Regler bleibt jedes Design unverändert; was
ein Design selbst festlegt, sperrt `stil.LOCKS` (gleiche Liste in HUBIplan).

Die Gestaltung passt sich Smartphone, Tablet und großen Bildschirmen an. Feste
Rahmentexte stehen auf Deutsch und Englisch zur Verfügung. Inhalte werden in der
Sprache der jeweiligen Webseite gezeigt. Tastaturbedienung, Kontraste und Alternativtexte
gehören zur Darstellung; fremde Tracking-Dienste oder Webschriften werden nicht geladen.

Das Kontaktformular nutzt die Spam-Prüfung und Versandregeln in HUBIplan. Persönliche
Empfängeradressen müssen dafür nicht im Browser offengelegt werden. Versandgrenzen
werden in der jeweiligen Instanz passend zum Maildienst konfiguriert.

## Allgemeiner Betrieb

Die Webseite läuft als eigener Container neben HUBIplan. Ein vorgeschalteter Webserver
übernimmt HTTPS und leitet Anfragen zum lokalen Containerport weiter. Beispiele für
Docker, Unterpfade und HestiaCP stehen in [betrieb.md](betrieb.md) und `deploy/`.

Getestet wird ausschließlich auf dem lokalen Entwicklungsrechner. Ausrollskripte
übertragen nur eingecheckte und zuvor lokal geprüfte Stände. Tatsächliche Hostnamen,
SSH-Ziele, Zugangsdaten, kundenbezogene Migrationspläne und Freigabevermerke werden
außerhalb des öffentlichen Repositories verwaltet.
