# Flippɘr Fakt-Posts

Postet jeden Tag einen Fakt im Tweet-Format auf Instagram, Facebook, LinkedIn, X und im Google Unternehmensprofil (über Metricool, Marke flipper.immo).

## So läuft es

1. GitHub Actions startet täglich um 08:17 UTC (`.github/workflows/daily.yml`).
2. `post.py render` nimmt den ersten Eintrag in `facts.json` mit `status: offen`, rendert `out/<id>.png` (abwechselnd weiß und schwarz) und pusht das Bild.
3. `post.py schedule` plant den Post in Metricool für 11:47 Uhr ein:
   - Instagram und Facebook: Text, CTA „Tools“, Hashtags, kein Link
   - LinkedIn und Google: Text und Link zum Blogartikel
   - X: Bild mit Text und Link; ist der Text zu lang, Bild mit Kurztext und Link
4. Der Eintrag bekommt `status: gepostet`.

## Fakt-Bank füllt sich selbst

- Jeden Sonntag zieht `refill.py` Fakten aus noch nicht verarbeiteten Blogartikeln (inkl. FlipperNews, neueste zuerst, laut Sitemap), bis 14 offene Fakten bereitliegen. Claude prüft jede Zahl per Websuche gegen eine Primärquelle, die Regeln stehen in `REGELN.md`.
- Fallen die offenen Fakten unter 3, füllt der tägliche Lauf vor dem Posten nach.
- Verarbeitete Artikel stehen in `processed.json` und werden nicht doppelt ausgewertet.
- Sofort auffüllen: `main` auf den Branch `refill-now` pushen.
- Von Hand ergänzen geht weiterhin über neue Einträge in `facts.json`.

## Einrichtung (einmalig)

1. Repo **öffentlich** anlegen und diesen Ordner pushen. Öffentlich ist nötig, weil Metricool das Bild über die Raw-URL von GitHub abholt. Für ein privates Repo muss `IMAGE_BASE_URL` auf einen anderen öffentlichen Speicher zeigen.
2. Unter Settings > Secrets and variables > Actions die Secrets `METRICOOL_TOKEN` (Metricool > Einstellungen > API) und `ANTHROPIC_API_KEY` (console.anthropic.com) anlegen.
3. Testlauf: `main` auf den Branch `test-run` pushen (oder Actions > Run workflow mit `draft = 1`). Der Post landet als Entwurf in Metricool und geht nicht live.

## Lokal testen

```bash
pip install pillow
python render.py beispiel.json     # rendert Einträge mit Feld "out"
DRY_RUN=1 python post.py render && DRY_RUN=1 python post.py schedule
```

## Anpassen

- Uhrzeit: `POST_TIME` in `daily.yml`
- CTA und Hashtags: `CTA_META` und `HASHTAGS` in `post.py`, CTA auf dem Bild über `cta` in `render.py`
- Avatar: `assets/avatar.png` ersetzen (quadratisch)
