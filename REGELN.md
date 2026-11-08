# Regeln für Fakt-Posts

Gilt für jeden Eintrag in `facts.json`, egal ob von Hand oder automatisch aus dem Blog gezogen.

## Rein darf

- Eine Aussage pro Post, ohne Kontext verständlich
- Konkrete Zahl, Frist, Paragraph oder Rechenweg
- Zahlen und Aussagen, die im Blogartikel klar stehen (der Blog ist bereits faktengeprüft). Nennt der Artikel eine Primärquelle, kommt sie ins Feld `quelle`, sonst `Flippɘr-Blog`
- Marktzahlen (z. B. aus FlipperNews) nur mit Stand-Monat im Text und mit `ablauf` spätestens 6 Monate nach Stand
- Praxisregeln und allgemeine Tipps mit Mehrwert, `kategorie: praxis`, `quelle: Praxiserfahrung Flippɘr` oder `Flippɘr-Blog`
- Rechenbeispiele, deren Rechnung stimmt (vor dem Eintragen nachrechnen)

## Nicht rein

- Zahlen, die nicht im Artikel stehen oder hinzugedichtet sind
- Steuer- und Rechtstipps, deren Ergebnis vom Einzelfall abhängt
- Prognosen zu Zinsen, Preisen oder Märkten
- Kunden- und Objektnamen, Adressen, eigene Deal-Zahlen ohne Freigabe von Johannes
- Wettbewerber
- Werbung für Leverage oder andere eigene Produkte
- Politische Wertungen (Vergesellschaftung, Mietendeckel usw.). Erlaubt ist nur der nackte Fakt
- Die Wörter „Coaching“ und „Coach“
- Derselbe Fakt innerhalb von 12 Monaten ein zweites Mal

## Format

- Bildtext 300 bis 520 Zeichen: Zeile 1 die Kernaussage mit Zahl oder klarer Regel, danach 3 bis 4 Zeilen mit „• “, jede mit einem konkreten Detail (Zahl, Prüfschritt, Fehler, Kostenspanne, Paragraph)
- Höchstens drei `**Markierungen**` pro Text
- Beitragstext (`caption`) 700 bis 1300 Zeichen mit Details, die nicht auf dem Bild stehen
- Ein Thema pro Post, dafür in der Tiefe. Artikel über Personen, Events oder Produkte liefern keine Posts
- Gendergerecht formulieren, „wir“ statt „ich“, keine Floskeln, keine Punchlines, keine Gedankenstriche
- Deslop-Regeln: kein Anlauf vor der Aussage, keine „nicht X, sondern Y“-Formeln, keine selbst beantworteten Fragen, aktiv mit handelnder Person, keine Füllwörter, keine vagen Aussagen, keine erfundenen Quellen, keine Schluss-Zusammenfassungen

## Felder in facts.json

| Feld | Inhalt |
|---|---|
| `id` | fortlaufend, dreistellig (`003`, `004` …), wird Dateiname des Bildes |
| `text` | der Post-Text mit `**Akzent**` |
| `kategorie` | `recht`, `markt`, `praxis`, `rechnung` |
| `quelle` | Primärquelle oder `Praxiserfahrung Flippɘr` |
| `blog` | URL des Blogartikels, wird auf LinkedIn, Google und X verlinkt |
| `ablauf` | `JJJJ-MM-TT` oder leer; abgelaufene Fakten werden übersprungen |
| `status` | `offen` (wird gepostet), `gepostet`, `abgelaufen`, `gesperrt` |
| `gepostet_am` | trägt das Skript ein |
