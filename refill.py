"""Fakt-Bank auffüllen: zieht Fakten aus noch nicht verarbeiteten Blogartikeln.

Läuft wöchentlich und zusätzlich im täglichen Job, sobald weniger als MIN_OPEN
offene Fakten da sind. Der Blog gilt als geprüfte Quelle, ein Claude-Aufruf pro Artikel ohne Websuche.
Die Regeln stehen in REGELN.md.

  python refill.py [ZIEL]   ZIEL = gewünschte Anzahl offener Fakten (Standard 14)

Umgebungsvariablen: ANTHROPIC_API_KEY (Secret), CLAUDE_MODEL (Standard claude-sonnet-5-5)
"""
import datetime as dt
import html
import json
import os
import re
import sys
import urllib.request
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.abspath(__file__))
FACTS = os.path.join(ROOT, "facts.json")
PROCESSED = os.path.join(ROOT, "processed.json")
SITEMAP = "https://www.flipperimmo.com/sitemap.xml"
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")
MAX_ARTICLES_PER_RUN = 20
SLOP = re.compile(r"entscheidend|essenziell|unerlässlich|maßgeblich|spannend|gamechanger|im blick behalten|nicht unterschätzen|a und o|schlüssel zum erfolg|praxisregel:|fazit:|!", re.I)
BANNED = re.compile(r"coaching|coach\b|leverage|—|–", re.I)
UA = {"User-Agent": "Mozilla/5.0 (fakt-bot; +https://www.flipperimmo.com)"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def dump(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


class Text(HTMLParser):
    """Holt den Artikeltext (h1-h3, p, li) und lässt Navigation und Footer weg."""

    def __init__(self):
        super().__init__()
        self.out, self.tag, self.skip = [], None, 0

    def handle_starttag(self, tag, attrs):
        if tag in ("nav", "footer", "script", "style", "form"):
            self.skip += 1
        if tag in ("h1", "h2", "h3", "p", "li"):
            self.tag = tag
            self.out.append("\n" + ("## " if tag in ("h2", "h3") else "# " if tag == "h1" else ""))

    def handle_endtag(self, tag):
        if tag in ("nav", "footer", "script", "style", "form") and self.skip:
            self.skip -= 1
        if tag == self.tag:
            self.tag = None

    def handle_data(self, data):
        if self.tag and not self.skip:
            self.out.append(data)


def article_text(url):
    p = Text()
    p.feed(get(url))
    txt = html.unescape("".join(p.out))
    txt = re.sub(r"\n\s*\n+", "\n", txt).strip()
    cut = txt.find("Bessere Deals")  # Footer-Block der Seite
    return txt[:cut] if cut > 0 else txt


def blog_urls():
    xml = get(SITEMAP)
    items = re.findall(r"<loc>(https://www\.flipperimmo\.com/blog/[^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>", xml)
    items.sort(key=lambda x: x[1], reverse=True)  # neueste zuerst
    return [u for u, _ in items]


PROMPT = """Du baust Wissens-Posts für Flippɘr (Fix & Flip, Immobilienhandel in Deutschland). Zielgruppe: Leute, die Immobilien kaufen, sanieren und verkaufen wollen oder es schon tun. Sie wollen Praxiswissen, das sie morgen anwenden können.

REGELN:
{rules}

Heutiges Datum: {today}

AUFGABE:
Lies den Blogartikel unten und baue daraus 0 bis {max_facts} Posts. Jeder Post behandelt EIN Thema und geht dabei in die Tiefe. Lieber 0 Posts als ein dünner.

Ein Post hat zwei Teile:

1. "text" (steht auf dem Bild, 300 bis 520 Zeichen ohne Markierungen):
   - Zeile 1: Die Kernaussage als harter Satz, mit Zahl, Frist, Kostenwert oder klarer Regel.
   - Danach 3 bis 4 Zeilen, jede beginnt mit "• " und bringt ein konkretes Detail: Zahl, Prüfschritt, typischer Fehler, Kostenspanne, Paragraph, Werkzeug, Reihenfolge. Jede Zeile muss allein etwas wert sein.
   - Zeilen mit \n trennen. Höchstens drei **Markierungen** für die wichtigsten Zahlen.
2. "caption" (Beitragstext, 700 bis 1300 Zeichen): vertieft das Thema mit weiteren Details aus dem Artikel, die nicht schon auf dem Bild stehen: Rechenbeispiel, Ablauf in Schritten, Ausnahmen, worauf man bei der Besichtigung oder beim Handwerker achtet. Absätze mit \n\n. Kein Hashtag, kein Link, kein CTA, das ergänzt das System.

INHALT:
- Nur, was im Artikel steht. Der Artikel ist geprüft und gilt als Quelle. Nichts erfinden, nicht umrunden. Rechenbeispiele rechnest du nach.
- Keine zwei Posts zum selben Thema. Nur Themen, die für den deutschen Markt gelten. Artikel über Einzelpersonen, Events, Teamvorstellungen oder Produkte geben 0 Posts.
- Marktzahlen bekommen den Stand-Monat in den Text und ein Ablaufdatum 6 Monate nach Stand.

SPRACHE (hart):
- Deutsch, "du", sachlich, wie ein erfahrener Praktiker, der einem Kollegen etwas erklärt. Konkrete Substantive und Zahlen statt Adjektive.
- Nach einem Doppelpunkt groß weiterschreiben.
- Verboten: Gedankenstriche, Floskeln, Punchlines, rhetorische Fragen, Ausrufezeichen, Einleitungen wie "Praxisregel:", "Beim Fix and Flip gilt", "Wichtig:", "Tipp:", "Fazit:". Verboten sind auch Wörter wie "entscheidend", "essenziell", "unerlässlich", "maßgeblich", "spannend", "Gamechanger", "clever", "smart", "nachhaltig", "im Blick behalten", "nicht unterschätzen", "A und O", "Schlüssel zum Erfolg".
- Gendergerecht über neutrale Formen ("wer verkauft", "die Verkäuferseite"), nicht mit Doppelpunkt oder Sternchen.

ANTWORT: nur ein JSON-Array, sonst nichts:
[{{"text": "...", "caption": "...", "kategorie": "recht|markt|praxis|rechnung", "quelle": "Primärquelle aus dem Artikel oder Flippɘr-Blog", "ablauf": "JJJJ-MM-TT oder leer"}}]

ARTIKEL ({url}):
{article}
"""


def claude(prompt):
    key = os.environ["ANTHROPIC_API_KEY"]
    body = {
        "model": MODEL,
        "max_tokens": 6000,
        "messages": [{"role": "user", "content": prompt}],
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(body).encode(),
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        res = json.loads(r.read().decode())
    text = "".join(b.get("text", "") for b in res.get("content", []) if b.get("type") == "text")
    m = re.search(r"\[\s*(\{.*\})?\s*\]", text, re.S)
    return json.loads(m.group(0)) if m else []


def norm(s):
    return re.sub(r"[^a-z0-9äöüß]", "", s.lower())


def valid(f, existing):
    t = f.get("text", "")
    plain = t.replace("**", "")
    cap = f.get("caption", "")
    if not t or not (250 <= len(plain) <= 560) or t.count("**") > 6 or t.count("**") % 2:
        return False
    if t.count("• ") < 2 or not (500 <= len(cap) <= 1600):
        return False
    if SLOP.search(t + " " + cap):
        return False
    if BANNED.search(t) or not f.get("quelle"):
        return False
    key = norm(plain)[:80]
    return all(norm(e["text"].replace("**", ""))[:80] != key for e in existing)


def main():
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    facts = load(FACTS, [])
    processed = set(load(PROCESSED, []))
    processed |= {f["blog"] for f in facts if f.get("blog") and f.get("status") == "gepostet"}
    open_ = lambda: sum(1 for f in facts if f.get("status") == "offen")
    if open_() >= target:
        print(f"{open_()} offene Fakten, nichts zu tun")
        return
    rules = open(os.path.join(ROOT, "REGELN.md"), encoding="utf-8").read()
    today = dt.date.today().isoformat()
    next_id = max([int(f["id"]) for f in facts] + [0]) + 1
    done = 0
    for url in blog_urls():
        if open_() >= target or done >= MAX_ARTICLES_PER_RUN:
            break
        if url in processed:
            continue
        news = re.search(r"flipper-news-(\d{2})-(\d{2})-(\d{4})", url)
        if news:
            d = dt.date(int(news.group(3)), int(news.group(2)), int(news.group(1)))
            if (dt.date.today() - d).days > 120:  # Marktzahlen veralten, alte Ausgaben nicht auswerten
                processed.add(url)
                continue
        done += 1
        try:
            art = article_text(url)
            new = claude(PROMPT.format(rules=rules, today=today, url=url, article=art[:30000],
                                       max_facts=1 if news else 2))
        except Exception as e:
            print("FEHLER", url, e)
            continue
        added = 0
        for f in new:
            if not valid(f, facts):
                continue
            facts.append({
                "id": f"{next_id:03d}", "text": f["text"].strip(), "kategorie": f.get("kategorie", ""),
                "caption": f.get("caption", "").strip(),
                "quelle": f["quelle"], "blog": url, "ablauf": f.get("ablauf") or "",
                "status": "offen", "gepostet_am": "",
            })
            next_id += 1
            added += 1
        processed.add(url)
        print(f"{url}: {added} Fakten")
        dump(FACTS, facts)
        dump(PROCESSED, sorted(processed))
    print(f"Offen: {open_()} (Ziel {target})")
    dump(PROCESSED, sorted(processed))
    if open_() < 7:
        sys.exit("Weniger als 7 offene Fakten (eine Woche). Blog liefert zu wenig, bitte prüfen.")


if __name__ == "__main__":
    main()
