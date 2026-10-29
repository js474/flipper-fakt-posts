"""Flippɘr Fakt-Post im Tweet-Format, 1080x1350 PNG.
Aufruf: python render.py facts.json  (rendert alle Einträge mit Feld "out")
Text-Markup: **...** wird in der Akzentfarbe gesetzt, \n erzwingt Absatz."""
import json, re, sys
from PIL import Image, ImageDraw, ImageFont

import os
A = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets") + "/"
F = A
W, H = 1080, 1350
PAD = 96
AVATAR = A + "avatar.png"
MINT, BLACK, WHITE = (155, 200, 205), (0, 0, 0), (255, 255, 255)

THEMES = {
    "weiss":   dict(bg=WHITE, text=BLACK, sub=(110, 110, 110), accent=(62, 123, 128), av_bg=BLACK, av_fg=WHITE, logo=BLACK, line=(225, 225, 225)),
    "schwarz": dict(bg=BLACK, text=WHITE, sub=(150, 150, 150), accent=MINT, av_bg=MINT, av_fg=BLACK, logo=WHITE, line=(45, 45, 45)),
    "mint":    dict(bg=MINT, text=BLACK, sub=(40, 70, 73), accent=WHITE, av_bg=BLACK, av_fg=MINT, logo=BLACK, line=(125, 170, 175)),
}

def tint(mask, color):
    out = Image.new("RGBA", mask.size, color + (0,))
    out.putalpha(mask.getchannel("A"))
    return out

def tokens(text):
    """-> list of paragraphs, each a list of (word, accent)"""
    paras = []
    for p in text.split("\n"):
        words, acc, prev_space = [], False, True
        for part in re.split(r"(\*\*)", p):
            if part == "**":
                acc = not acc; continue
            if not part:
                continue
            for i, w in enumerate(part.split()):
                glue = i == 0 and not part[0].isspace() and not prev_space and words
                if glue:  # Satzzeichen direkt hinter Akzent: ohne Leerzeichen anhängen
                    words.append((w, acc, True))
                else:
                    words.append((w, acc, False))
            prev_space = part[-1].isspace()
        paras.append(words)
    return paras

def layout(paras, font, maxw, d):
    lines = []
    for raw in paras:
        words = []  # jedes Wort = Liste von Segmenten (text, accent)
        for w, a, g in raw:
            if g and words:
                words[-1].append((w, a))
            else:
                words.append([(w, a)])
        cur, cw = [], 0
        sp = d.textlength(" ", font=font)
        for segs in words:
            w, a = segs, None
            ww = sum(d.textlength(s, font=font) for s, _ in segs)
            if cur and cw + sp + ww > maxw:
                lines.append(cur); cur, cw = [], 0
            cw += (sp if cur else 0) + ww
            cur.append(segs)
        lines.append(cur)
        lines.append(None)  # Absatz
    return lines[:-1]

def render(cfg, out):
    t = THEMES[cfg.get("theme", "weiss")]
    img = Image.new("RGB", (W, H), t["bg"])
    d = ImageDraw.Draw(img)
    logo = Image.open(A + "logo.png")

    # Text setzen, Größe so wählen, dass der Block passt
    maxw = W - 2 * PAD
    for size in range(60, 34, -2):
        font = ImageFont.truetype(F + "Montserrat-600.ttf", size)
        lh, gap = int(size * 1.38), int(size * 0.75)
        lines = layout(tokens(cfg["text"]), font, maxw, d)
        th = sum(gap if l is None else lh for l in lines)
        if th <= 760:
            break

    head_h, head_gap, foot_gap = 160, 60, 56
    meta_font = ImageFont.truetype(F + "Montserrat-500.ttf", 30)
    block = head_h + head_gap + th + foot_gap + 110
    y0 = (H - block) // 2 - 20

    # Avatar: Profilfoto im Kreis
    av = 160
    circ = Image.new("L", (av * 4, av * 4), 0)
    ImageDraw.Draw(circ).ellipse((0, 0, av * 4 - 1, av * 4 - 1), fill=255)
    circ = circ.resize((av, av), Image.LANCZOS)
    photo = Image.open(cfg.get("avatar", AVATAR)).convert("RGB").resize((av, av), Image.LANCZOS)
    img.paste(photo, (PAD, y0), circ)

    # Name (Wortmarke) + Haken + Handle
    nx = PAD + av + 30
    lh_name = 46
    wm = logo.resize((int(logo.width * lh_name / logo.height), lh_name), Image.LANCZOS)
    wm = tint(wm, t["logo"])
    img.paste(wm, (nx, y0 + 32), wm)
    bx, by, br = nx + wm.width + 16, y0 + 32 + 4, 17
    d.ellipse((bx, by, bx + 2 * br, by + 2 * br), fill=(29, 155, 240))
    d.line([(bx + 10, by + 18), (bx + 15, by + 23), (bx + 25, by + 12)], fill=WHITE, width=5, joint="curve")
    hf = ImageFont.truetype(F + "Montserrat-500.ttf", 34)
    d.text((nx, y0 + 94), cfg.get("handle", "@flipper.immo"), font=hf, fill=t["sub"])

    # Tweet-Text
    y = y0 + head_h + head_gap
    sp = d.textlength(" ", font=font)
    for l in lines:
        if l is None:
            y += gap; continue
        x = PAD
        for segs in l:
            for s, a in segs:
                d.text((x, y), s, font=font, fill=t["accent"] if a else t["text"])
                x += d.textlength(s, font=font)
            x += sp
        y += lh

    # Meta-Zeile wie beim Tweet
    y += 92 - (lh - int(size * 1.0))
    d.line([(PAD, y), (W - PAD, y)], fill=t["line"], width=2)
    cta_font = ImageFont.truetype(F + "Montserrat-600.ttf", 34)
    cta_bold = ImageFont.truetype(F + "Montserrat-800.ttf", 34)
    x, cy = PAD, y + 34
    for s_, b in [("Kommentiere", False), (" „Tools“", True), (cfg.get("cta", " für unseren Flip-Rechner."), False)]:
        f_ = cta_bold if b else cta_font
        for i, w in enumerate(s_.split(" ")):
            if not w:
                continue
            word = (" " if i > 0 else "") + w
            ww = d.textlength(word, font=f_)
            if x + ww > W - PAD:
                x, cy, word = PAD, cy + 48, w
                ww = d.textlength(word, font=f_)
            d.text((x, cy), word, font=f_, fill=t["accent"])
            x += ww
    d.text((PAD, cy + 62), cfg.get("meta", "Kaufen. Renovieren. Verkaufen."), font=meta_font, fill=t["accent"])
    img.save(out)
    print(out, "Schriftgröße", size)

if __name__ == "__main__":
    for c in json.load(open(sys.argv[1])):
        render(c, c["out"])
