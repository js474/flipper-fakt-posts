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
SLOP = re.compile(r"es geht nicht um|stell dir vor|kennst du das|klingt bekannt|ganz einfach:|das zeigt|denk mal|wirklich|eigentlich|letztlich|schlichtweg|sozusagen|ganzheitlich|mehrwert|navigieren|meistern|nahtlos|maßgeschneidert|unter die lupe|auf der sicheren seite|ins geld|in der heutigen zeit|mehr denn je|hand aufs herz|coach|—|–|kurz gesagt|unterm strich|am ende des tages|hier ist der|die wahrheit ist|was viele nicht wissen|nicht nur .{1,60} sondern|experten sagen|studien zeigen|\? [A-ZÄÖÜ][a-zäöü]+\.|entscheidend|essenziell|unerlässlich|maßgeblich|spannend|gamechanger|im blick behalten|nicht unterschätzen|a und o|schlüssel zum erfolg|praxisregel:|fazit:|!", re.I)
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


STIL = """SPRACHE. Das ist der wichtigste Teil. Jeder Text muss klingen, als hätte ein erfahrener Immobilienpraktiker ihn selbst getippt, nachdem er einem Kollegen auf der Baustelle etwas erklärt hat. Niemand darf beim Lesen den Verdacht bekommen, dass eine KI beteiligt war. Ein Text, der nach KI klingt, ist ein Fehler, auch wenn der Inhalt stimmt.

1. Grundton
- Deutsch, "du"-Ansprache, sachlich und direkt. Wenn Flippɘr als Absender spricht, dann "wir", nie "ich".
- Konkret vor allgemein: lieber "die Bank will die letzten drei BWAs sehen" als "Banken prüfen umfangreiche Unterlagen".
- Substantive, Zahlen und Verben tragen den Text, nicht Adjektive.

2. Rhythmus (hier verraten sich KI-Texte am schnellsten)
- Satzlängen mischen: kurz, dann länger mit Nebensatz, dann mittel. Nie drei gleich lange Sätze hintereinander.
- Keine Dreier-Aufzählungen aus Gewohnheit ("schnell, sicher und rentabel"). Zwei Dinge oder eins, drei nur, wenn es wirklich genau drei sind.
- Absätze enden unterschiedlich. Kein Absatz endet mit einem zusammenfassenden oder "starken" Schlusssatz.
- Keine Stakkato-Fragmente für Dramatik ("Kein Puffer. Kein Plan. Kein Gewinn.").
- Nicht jeder Absatz gleich gebaut (Behauptung, Erklärung, Fazit).

3. Verbotene Satzmuster
- Kontrast-Formeln: "nicht X, sondern Y", "Es geht nicht um X. Es geht um Y.", "Nicht A. Nicht B. Sondern C.", "nicht nur ... sondern auch". Y direkt sagen.
- Selbst beantwortete Fragen: "Das Ergebnis? Teuer.", "Warum? Ganz einfach:". Als Aussage schreiben.
- Rhetorische Fragen jeder Art ("Klingt bekannt?", "Kennst du das?").
- Anläufe vor der Aussage: "Hier ist der Punkt", "Die Wahrheit ist", "Was viele nicht wissen", "Stell dir vor", "Lass uns", "Kurz gesagt".
- Partizip-Anhängsel, die Bedeutung behaupten: "..., was zeigt, wie wichtig das ist", "..., wodurch du langfristig profitierst".
- Schlusssätze: "Unterm Strich", "Am Ende des Tages", "Das zeigt", "Und genau darum geht es", "Denk mal drüber nach".
- Aphorismen, Merksätze, Punchlines: "Wer X will, muss Y", "Zeit ist Geld", "Im Einkauf liegt der Gewinn".

4. Verbotene Wörter und Wendungen
- KI-Vokabular: entscheidend, essenziell, unerlässlich, maßgeblich, zentral, wesentlich, nachhaltig, ganzheitlich, spannend, wertvoll, kraftvoll, Mehrwert, Gamechanger, Schlüssel, Reise, Potenzial entfalten, auf das nächste Level, eintauchen, beleuchten, navigieren, meistern, optimal, nahtlos, maßgeschneidert, clever, smart, im Blick behalten, nicht unterschätzen, das A und O, Schlüssel zum Erfolg.
- Füllwörter: wirklich, einfach, eigentlich, letztlich, grundsätzlich, durchaus, schlichtweg, tatsächlich, quasi, sozusagen, ganz klar, absolut.
- Floskeln: "ganz unkompliziert", "gerne direkt", "das Wichtigste zum Schluss", "Ziel ist einfach", "in der heutigen Zeit", "mehr denn je", "Hand aufs Herz".
- Werbesprache: "entdecke", "sichere dir", "einzigartig", "revolutionär".
- Redewendungen und Idiome jeder Art ("unter die Lupe nehmen", "den Rotstift ansetzen", "auf der sicheren Seite", "ins Geld gehen", "Licht ins Dunkel").
- Vage Zuschreibungen: "Studien zeigen", "Experten sagen", "viele berichten". Nur Quellen, die im Artikel namentlich stehen.
- Die Wörter "Coaching" und "Coach".

5. Form
- Keine Gedankenstriche (– und —), keine Ausrufezeichen, keine Emojis.
- Nach einem Doppelpunkt immer groß weiterschreiben.
- Keine Einleitungen wie "Praxisregel:", "Beim Fix and Flip gilt", "Wichtig:", "Tipp:", "Fazit:", "Merke:".
- Aktiv mit handelnder Person ("du", "die Bank", "der Handwerksbetrieb", "wir"). Passiv nur, wenn niemand handelt.
- Gendergerecht über neutrale Formen ("wer verkauft", "die Verkäuferseite", "Maklerinnen und Makler"), nicht mit Doppelpunkt oder Sternchen.
- Erste Zeile und Text darunter sagen nie dasselbe zweimal. Bildtext und Beitragstext wiederholen sich nicht.

6. Vorher und nachher (nur für den Ton, Inhalte und Orte aus den Beispielen nie übernehmen)
- Falsch: "Ein Puffer ist nicht nur sinnvoll, sondern essenziell für deinen Erfolg."
  Richtig: "Wir rechnen auf jede Renovierung 15 bis 20 % Puffer. Bei der letzten Wohnung in Kempten kam hinter der Vorsatzschale ein feuchter Kamin zum Vorschein."
- Falsch: "Das Ergebnis? Mehr Marge, weniger Stress."
  Richtig: "Mit dem Puffer blieb die Marge bei 22 %, obwohl der Kamin 3.800 € gekostet hat."
- Falsch: "Am Ende des Tages zählt eine saubere Kalkulation."
  Richtig: Satz streichen, den Absatz mit dem letzten konkreten Punkt enden lassen.
"""


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

{stil}

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


LEKTORAT = """Du bist Lektor für die Social-Media-Posts von Flippɘr (Fix & Flip, Immobilienhandel). Unten stehen Posts als JSON. Überarbeite "text" und "caption" streng nach diesen Regeln:

{stil}

VORGEHEN
1. Durchgang: Geh jeden Satz gegen die Abschnitte 2 bis 5 durch. Jeden Treffer schreibst du um, statt nur ein Wort zu tauschen.
2. Durchgang: Lies jeden Text, als würdest du ihn laut vorlesen. Würde ein erfahrener Praktiker das genau so zu einem Kollegen sagen? Wenn nein, umschreiben.
3. Bewerte jeden Text von 1 bis 10 bei "klingt nach einem echten Menschen". Unter 9: neu schreiben.

HARTE GRENZEN
- Fakten, Zahlen, Paragraphen, Fristen und Rechenwege bleiben exakt gleich. Nichts hinzuerfinden, nichts weglassen, was eine Zahl trägt.
- Format bleibt: "text" beginnt mit der Kernaussage, danach 3 bis 4 Zeilen mit "• ", getrennt durch \\n, 300 bis 520 Zeichen ohne Markierungen, höchstens drei **Markierungen**. "caption" 700 bis 1300 Zeichen, Absätze mit \\n\\n.
- Alle anderen Felder unverändert zurückgeben.

ANTWORT: nur das JSON-Array in derselben Reihenfolge, sonst nichts.

POSTS:
{posts}
"""


def lektorat(posts):
    """Zweiter Durchgang: Sprache menschlich machen, Inhalt bleibt."""
    if not posts:
        return posts
    try:
        out = claude(LEKTORAT.format(stil=STIL, posts=json.dumps(posts, ensure_ascii=False, indent=1)))
    except Exception as e:
        print("Lektorat fehlgeschlagen, Original bleibt:", e)
        return posts
    if len(out) != len(posts):
        print("Lektorat lieferte andere Anzahl, Original bleibt")
        return posts
    return out


def caps(s):
    """Nach Doppelpunkt immer groß weiterschreiben."""
    return re.sub(r":(\s+)(\*\*)?([a-zäöü])", lambda m: ":" + m.group(1) + (m.group(2) or "") + m.group(3).upper(), s)


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
    todo = [f for f in facts if f.get("status") == "offen" and not f.get("lektoriert")]
    for i in range(0, len(todo), 4):
        chunk = todo[i:i + 4]
        res = lektorat([{"text": f["text"], "caption": f.get("caption", "")} for f in chunk])
        for f, n in zip(chunk, res):
            if valid({**f, **n, "text": n.get("text", ""), "quelle": f.get("quelle", "x")}, [x for x in facts if x is not f]):
                f["text"], f["caption"] = caps(n["text"].strip()), caps(n.get("caption", "").strip())
            f["lektoriert"] = True
        dump(FACTS, facts)
    if todo:
        print(f"{len(todo)} offene Fakten nachlektoriert")
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
            new = claude(PROMPT.format(stil=STIL, rules=rules, today=today, url=url, article=art[:30000],
                                       max_facts=1 if news else 2))
        except Exception as e:
            print("FEHLER", url, e)
            continue
        new = lektorat([f for f in new if f.get("text")])
        added = 0
        for f in new:
            if not valid(f, facts):
                continue
            facts.append({
                "id": f"{next_id:03d}", "text": caps(f["text"].strip()), "kategorie": f.get("kategorie", ""),
                "caption": caps(f.get("caption", "").strip()),
                "quelle": f["quelle"], "blog": url, "ablauf": f.get("ablauf") or "",
                "status": "offen", "gepostet_am": "", "lektoriert": True,
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
