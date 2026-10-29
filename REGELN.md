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

- Höchstens 280 Zeichen Klartext (ohne `**`), sonst entfällt X automatisch
- Höchstens zwei `**Markierungen**` pro Text
- `\n` setzt einen Absatz, höchstens ein Absatz pro Text
- Gendergerecht formulieren, „wir“ statt „ich“, keine Floskeln, keine Punchlines, keine Gedankenstriche

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
