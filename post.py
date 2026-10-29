"""Täglicher Fakt-Post: nächsten offenen Fakt rendern und in Metricool einplanen.

Schritte (vom Workflow nacheinander aufgerufen):
  python post.py render    -> wählt Fakt, rendert out/<id>.png, schreibt NEXT_ID in $GITHUB_ENV
  (Workflow committet und pusht das Bild, damit die Raw-URL öffentlich erreichbar ist)
  python post.py schedule  -> plant den Fakt in Metricool ein und setzt Status "gepostet"

Umgebungsvariablen:
  METRICOOL_TOKEN   (Secret)  API-Token aus Metricool > Einstellungen > API
  METRICOOL_USER_ID           Standard 2209069
  METRICOOL_BLOG_ID           Standard 2740762 (Marke flipper.immo)
  POST_TIME                   Uhrzeit Europe/Berlin, Standard 11:47
  IMAGE_BASE_URL              Standard https://raw.githubusercontent.com/<repo>/main/out
  DRY_RUN=1                   nur anzeigen, nichts senden
"""
import datetime as dt
import json
import os
import re
import sys
import urllib.request
from zoneinfo import ZoneInfo

import render

ROOT = os.path.dirname(os.path.abspath(__file__))
FACTS = os.path.join(ROOT, "facts.json")
TZ = ZoneInfo("Europe/Berlin")
CTA_META = "Kommentiere „Tools“ für unseren Flip-Rechner."
HASHTAGS = "#fixandflip #immobilien #immobilieninvestment #flipper"


def load():
    with open(FACTS, encoding="utf-8") as f:
        return json.load(f)


def save(facts):
    with open(FACTS, "w", encoding="utf-8") as f:
        json.dump(facts, f, ensure_ascii=False, indent=2)
        f.write("\n")


def today():
    return dt.datetime.now(TZ).date()


def pick(facts):
    t = today().isoformat()
    for f in facts:
        if f.get("status") != "offen":
            continue
        if f.get("ablauf") and f["ablauf"] < t:
            f["status"] = "abgelaufen"
            continue
        return f
    return None


def plain(text):
    return re.sub(r"\*\*", "", text).strip()


def cmd_render():
    facts = load()
    fact = pick(facts)
    save(facts)  # abgelaufene Einträge markieren
    if not fact:
        sys.exit("Keine offenen Fakten mehr in facts.json. Neue Texte ergänzen.")
    posted = sum(1 for f in facts if f.get("status") == "gepostet")
    theme = "weiss" if posted % 2 == 0 else "schwarz"
    out = os.path.join(ROOT, "out", f"{fact['id']}.png")
    render.render({"text": fact["text"], "theme": theme}, out)
    print(f"Fakt {fact['id']} gerendert ({theme}): {out}")
    if os.environ.get("GITHUB_ENV"):
        with open(os.environ["GITHUB_ENV"], "a") as f:
            f.write(f"NEXT_ID={fact['id']}\n")


def publish_time():
    hh, mm = os.environ.get("POST_TIME", "11:47").split(":")
    now = dt.datetime.now(TZ)
    when = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
    if when < now + dt.timedelta(minutes=10):
        when = now + dt.timedelta(minutes=15)
    return when


def metricool(payload):
    token = os.environ.get("METRICOOL_TOKEN", "")
    user = os.environ.get("METRICOOL_USER_ID", "2209069")
    blog = os.environ.get("METRICOOL_BLOG_ID", "2740762")
    url = f"https://app.metricool.com/api/v2/scheduler/posts?blogId={blog}&userId={user}"
    if not token and os.environ.get("DRY_RUN") != "1":
        raise RuntimeError("METRICOOL_TOKEN fehlt (Secret im Repo anlegen)")
    if os.environ.get("DRY_RUN") == "1":
        print("DRY RUN", url, json.dumps(payload, ensure_ascii=False, indent=2))
        return {"dry_run": True}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"X-Mc-Auth": token, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read().decode()
    print("Metricool:", body[:500])
    return json.loads(body or "{}")


def base_post(text, image, when, networks):
    p = {
        "publicationDate": {"dateTime": when.strftime("%Y-%m-%dT%H:%M:%S"), "timezone": "Europe/Berlin"},
        "text": text,
        "providers": [{"network": n} for n in networks],
        "autoPublish": True,
        "draft": os.environ.get("DRAFT") == "1",
        "media": [image],
        "mediaAltText": [],
        "descendants": [],
        "firstCommentText": "",
        "shortener": False,
        "smartLinkData": {"ids": []},
        "hasNotReadNotes": False,
    }
    data = {
        "instagram": ("instagramData", {"type": "POST", "isAiGenerated": False}),
        "facebook": ("facebookData", {"type": "POST"}),
        "linkedin": ("linkedinData", {"type": "post", "previewIncluded": False}),
        "twitter": ("twitterData", {"tags": []}),
        "gmb": ("gmbData", {"type": "publication"}),
    }
    for n in networks:
        k, v = data[n]
        p[k] = v
    return p


def cmd_schedule():
    facts = load()
    fid = os.environ.get("NEXT_ID") or (pick(facts) or {}).get("id")
    fact = next((f for f in facts if f["id"] == fid), None)
    if not fact:
        sys.exit("Kein Fakt zum Einplanen gefunden.")
    repo = os.environ.get("GITHUB_REPOSITORY", "OWNER/flipper-fakt-posts")
    base = os.environ.get("IMAGE_BASE_URL", f"https://raw.githubusercontent.com/{repo}/{os.environ.get('GITHUB_REF_NAME', 'main')}/out")
    image = f"{base}/{fact['id']}.png"
    when = publish_time()
    txt = plain(fact["text"])
    link = fact.get("blog") or "https://www.flipperimmo.com/blog"

    posts = [
        # Meta: Kommentar-CTA (ManyChat), keine Links
        (f"{txt}\n\n{CTA_META}\n\n{HASHTAGS}", ["instagram", "facebook"]),
        # LinkedIn und Google: Link zum Artikel
        (f"{txt}\n\nMehr dazu im Flippɘr-Blog: {link}", ["linkedin", "gmb"]),
        # X: 280 Zeichen, Link nur wenn er passt (X zählt Links als 23 Zeichen)
    ]
    if len(txt) + 25 <= 280:
        posts.append((f"{txt}\n\n{link}", ["twitter"]))
    elif len(txt) <= 280:
        posts.append((txt, ["twitter"]))
    else:
        print(f"X übersprungen: Text hat {len(txt)} Zeichen (max. 280 ohne X Premium)")
    errors = []
    for text, nets in posts:
        try:
            metricool(base_post(text, image, when, nets))
        except Exception as e:  # ein Kanal darf die anderen nicht blockieren
            errors.append(f"{nets}: {e}")
            print("FEHLER", nets, e)
    if len(errors) == len(posts):
        sys.exit("Alle Metricool-Aufrufe fehlgeschlagen:\n" + "\n".join(errors))
    if os.environ.get("DRY_RUN") == "1":
        print("DRY RUN: Status bleibt offen")
        return
    fact["status"] = "gepostet"
    fact["gepostet_am"] = when.strftime("%Y-%m-%d %H:%M")
    save(facts)
    print(f"Fakt {fact['id']} eingeplant für {fact['gepostet_am']}")
    if errors:
        sys.exit("Teilweise fehlgeschlagen:\n" + "\n".join(errors))


if __name__ == "__main__":
    {"render": cmd_render, "schedule": cmd_schedule}[sys.argv[1]]()
