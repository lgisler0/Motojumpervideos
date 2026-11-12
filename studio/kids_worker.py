#!/usr/bin/env python3
"""
Kids-Worker: erzeugt automatisch englische, kinderfreundliche YouTube Shorts (1080x1920)
im modernen Kinderserien-Cartoon-Stil – mit Erzaehlstimme, Musik und Animation, alles aus Code.

Nutzung:
    python3 kids_worker.py                   # 1 zufaelliges Video
    python3 kids_worker.py --anzahl 5        # 5 Videos am Stueck
    python3 kids_worker.py --thema counting  # counting | colors | animals

Einmalig installieren:
    pip install pycairo numpy kokoro-onnx     (+ ffmpeg)
    Schrift "Lilita One" installieren (Google Fonts) – sonst wird eine Standardschrift benutzt.
    Die Stimm-Dateien (ca. 340 MB) werden beim ersten Start automatisch nach ./modelle geladen.
"""
import argparse, math, os, random, subprocess, urllib.request, wave
import cairo
import numpy as np

B, H, FPS, SR = 1080, 1920, 60, 48000
SCHRIFT = "Lilita One"
STIMME, TEMPO, TONHOEHE = "af_heart", 0.92, 1.06   # freundliche Stimme, etwas langsamer, etwas heller
HIER = os.path.dirname(os.path.abspath(__file__))
MODELL = os.path.join(HIER, "modelle", "kokoro-v1.0.onnx")
STIMMEN = os.path.join(HIER, "modelle", "voices-v1.0.bin")
MODELL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"


def rgb(h):
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


INK = rgb("3b2a5c")
WEISS = (1, 1, 1)
COLORS = {
    "red": rgb("ff4b55"), "blue": rgb("3d9bff"), "yellow": rgb("ffd633"), "green": rgb("3ed46a"),
    "orange": rgb("ff9a2e"), "purple": rgb("a970ff"), "pink": rgb("ff7ac8"),
}
REGENBOGEN = [COLORS[c] for c in ("red", "orange", "yellow", "green", "blue", "purple", "pink")]
ZAHLEN = ["zero", "one", "two", "three", "four", "five", "six"]
TIERE = {
    "bunny": dict(pl="bunnies", f=rgb("ffffff"), b=rgb("ffe3ee"), satz="The bunny goes hop, hop, hop!"),
    "bear": dict(pl="bears", f=rgb("c98b5e"), b=rgb("f3d5ae"), satz="The bear says, roar!"),
    "cat": dict(pl="cats", f=rgb("ffa94d"), b=rgb("ffe6c4"), satz="The cat says, meow!"),
    "dog": dict(pl="dogs", f=rgb("f3d6a8"), b=rgb("ffffff"), satz="The dog says, woof, woof!"),
    "frog": dict(pl="frogs", f=rgb("6ddc6d"), b=rgb("dcffc9"), satz="The frog says, ribbit, ribbit!"),
    "chick": dict(pl="chicks", f=rgb("ffdd4d"), b=rgb("fff3b0"), satz="The chick says, cheep, cheep!"),
}


def mix(c, d, k):
    return tuple(a * (1 - k) + b * k for a, b in zip(c, d))


def kontur(f):
    return mix(f, INK, 0.6)


# ---------------- Zeichen-Werkzeuge ----------------

def ellipse(ctx, x, y, rx, ry, rot=0):
    ctx.save(); ctx.translate(x, y); ctx.rotate(rot); ctx.scale(max(rx, .01), max(ry, .01))
    ctx.new_sub_path(); ctx.arc(0, 0, 1, 0, 2 * math.pi); ctx.restore()


def fuell(ctx, farbe, lw=0, kante=None, alpha=1):
    ctx.set_source_rgba(*farbe, alpha)
    if lw:
        ctx.fill_preserve(); ctx.set_source_rgb(*(kante or kontur(farbe))); ctx.set_line_width(lw); ctx.stroke()
    else:
        ctx.fill()


def stern_pfad(ctx, x, y, r, rot=0, innen=0.48):
    for i in range(10):
        rr = r if i % 2 == 0 else r * innen
        a = rot - math.pi / 2 + i * math.pi / 5
        (ctx.move_to if i == 0 else ctx.line_to)(x + rr * math.cos(a), y + rr * math.sin(a))
    ctx.close_path()


def augen(ctx, dx, y, r, t, seed=0):
    blink = (t * 0.55 + seed * 0.43) % 3.1 < 0.12
    for sx in (-1, 1):
        ex = sx * dx
        if blink:
            ctx.move_to(ex - r, y); ctx.curve_to(ex - r * .4, y + r * .6, ex + r * .4, y + r * .6, ex + r, y)
            ctx.set_source_rgb(*INK); ctx.set_line_width(r * .35); ctx.stroke()
        else:
            ellipse(ctx, ex, y, r, r * 1.18); fuell(ctx, INK)
            ellipse(ctx, ex - r * .3, y - r * .4, r * .36, r * .36); fuell(ctx, WEISS)
            ellipse(ctx, ex + r * .32, y + r * .35, r * .17, r * .17); fuell(ctx, WEISS)


def wangen(ctx, dx, y, r):
    for sx in (-1, 1):
        ellipse(ctx, sx * dx, y, r, r * .65); fuell(ctx, rgb("ff8fa8"), alpha=.75)


def mund(ctx, x, y, w, offen=0.3):
    h = w * (0.35 + 0.95 * offen)

    def pfad():
        ctx.move_to(x - w, y); ctx.curve_to(x - w, y + h * 1.4, x + w, y + h * 1.4, x + w, y); ctx.close_path()
    pfad(); ctx.set_source_rgb(*rgb("7a1535")); ctx.fill()
    ctx.save(); pfad(); ctx.clip()
    ellipse(ctx, x, y + h * 1.05, w * .62, h * .5); fuell(ctx, rgb("ff7d95")); ctx.restore()
    pfad(); ctx.set_source_rgb(*INK); ctx.set_line_width(max(2.5, w * .2)); ctx.stroke()


# ---------------- Figuren (eigene Designs) ----------------

def _koerper(ctx, s, f, b, t, wink, lw, fuss=None):
    for sx in (-1, 1):
        ellipse(ctx, sx * .3 * s, 1.5 * s, .25 * s, .13 * s); fuell(ctx, fuss or f, lw)
    for sx in (-1, 1):
        rot, ay = sx * -0.5, .8 * s
        if wink and sx == 1:
            rot, ay = -2.3 + math.sin(t * 11) * .4, .68 * s
        ctx.save(); ctx.translate(sx * .48 * s, ay); ctx.rotate(rot); ellipse(ctx, 0, .24 * s, .14 * s, .32 * s); ctx.restore()
        fuell(ctx, f, lw)
    ellipse(ctx, 0, .98 * s, .56 * s, .5 * s); fuell(ctx, f, lw)
    ellipse(ctx, 0, 1.07 * s, .36 * s, .33 * s); fuell(ctx, b)


def tier(ctx, art, x, y, s, t, seed=0, wink=False, sprech=0.0):
    """Kleines Cartoon-Tier; (x, y) ist die Kopfmitte, s der Kopfradius."""
    if s < 4:
        return
    d = TIERE[art]; f, b = d["f"], d["b"]
    lw = max(3, s * .075)
    ctx.save(); ctx.translate(x, y); ctx.rotate(math.sin(t * 2.2 + seed * 1.7) * .05)
    _koerper(ctx, s, f, b, t, wink, lw, rgb("ff9a2e") if art == "chick" else None)
    wack = math.sin(t * 3 + seed) * .06
    if art == "bunny":
        for sx in (-1, 1):
            ellipse(ctx, sx * .4 * s, -1.2 * s, .22 * s, .62 * s, sx * .16 + wack); fuell(ctx, f, lw)
            ellipse(ctx, sx * .4 * s, -1.2 * s, .1 * s, .42 * s, sx * .16 + wack); fuell(ctx, rgb("ffb3cf"))
        ellipse(ctx, 0, 0, s, .9 * s); fuell(ctx, f, lw)
        augen(ctx, .4 * s, -.08 * s, .15 * s, t, seed); wangen(ctx, .64 * s, .22 * s, .15 * s)
        mund(ctx, 0, .3 * s, .16 * s, .25 + sprech * .8)
        ctx.rectangle(-.09 * s, .3 * s, .18 * s, .14 * s); fuell(ctx, WEISS, lw * .5, INK)
        ellipse(ctx, 0, .2 * s, .1 * s, .07 * s); fuell(ctx, rgb("ff7aa8"))
    elif art == "bear":
        for sx in (-1, 1):
            ellipse(ctx, sx * .72 * s, -.66 * s, .32 * s, .32 * s); fuell(ctx, f, lw)
            ellipse(ctx, sx * .72 * s, -.66 * s, .16 * s, .16 * s); fuell(ctx, b)
        ellipse(ctx, 0, 0, s, .92 * s); fuell(ctx, f, lw)
        ellipse(ctx, 0, .33 * s, .42 * s, .32 * s); fuell(ctx, b)
        augen(ctx, .42 * s, -.12 * s, .15 * s, t, seed); wangen(ctx, .68 * s, .2 * s, .14 * s)
        mund(ctx, 0, .36 * s, .15 * s, .3 + sprech * .8)
        ellipse(ctx, 0, .2 * s, .15 * s, .1 * s); fuell(ctx, INK)
    elif art == "cat":
        for sx in (-1, 1):
            ctx.move_to(sx * .95 * s, -.3 * s); ctx.line_to(sx * .8 * s, -1.2 * s); ctx.line_to(sx * .2 * s, -.8 * s)
            ctx.close_path(); fuell(ctx, f, lw)
            ctx.move_to(sx * .8 * s, -.55 * s); ctx.line_to(sx * .74 * s, -.98 * s); ctx.line_to(sx * .45 * s, -.78 * s)
            ctx.close_path(); fuell(ctx, rgb("ffb3cf"))
        ellipse(ctx, 0, 0, s, .9 * s); fuell(ctx, f, lw)
        ctx.set_source_rgb(*mix(f, rgb("d9541e"), .6)); ctx.set_line_width(s * .09); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        for k in (-1, 0, 1):
            ctx.move_to(k * .2 * s, -.82 * s); ctx.line_to(k * .17 * s, -.55 * s if k else -.48 * s)
        ctx.stroke()
        ellipse(ctx, 0, .32 * s, .38 * s, .27 * s); fuell(ctx, b)
        augen(ctx, .42 * s, -.1 * s, .15 * s, t, seed); wangen(ctx, .68 * s, .2 * s, .13 * s)
        ctx.set_source_rgb(*INK); ctx.set_line_width(s * .035)
        for sx in (-1, 1):
            for k in (-1, 1):
                ctx.move_to(sx * .5 * s, .3 * s + k * .05 * s); ctx.line_to(sx * 1.15 * s, .3 * s + k * .16 * s)
        ctx.stroke()
        mund(ctx, 0, .34 * s, .13 * s, .25 + sprech * .8)
        ellipse(ctx, 0, .22 * s, .09 * s, .065 * s); fuell(ctx, rgb("ff7aa8"))
    elif art == "dog":
        ellipse(ctx, 0, 0, s, .92 * s); fuell(ctx, f, lw)
        ohr = rgb("a8683d")
        for sx in (-1, 1):
            ellipse(ctx, sx * .92 * s, -.1 * s, .27 * s, .62 * s, sx * -.28 + wack); fuell(ctx, ohr, lw)
        ellipse(ctx, .42 * s, -.12 * s, .3 * s, .34 * s); fuell(ctx, mix(ohr, f, .35))
        ellipse(ctx, 0, .33 * s, .44 * s, .33 * s); fuell(ctx, WEISS)
        augen(ctx, .42 * s, -.12 * s, .15 * s, t, seed); wangen(ctx, .7 * s, .22 * s, .13 * s)
        mund(ctx, 0, .36 * s, .17 * s, .5 + sprech * .8)
        ellipse(ctx, 0, .2 * s, .16 * s, .11 * s); fuell(ctx, INK)
    elif art == "frog":
        for sx in (-1, 1):
            ellipse(ctx, sx * .5 * s, -.62 * s, .36 * s, .36 * s); fuell(ctx, f, lw)
        ellipse(ctx, 0, 0, 1.05 * s, .82 * s); fuell(ctx, f, lw)
        for sx in (-1, 1):
            ellipse(ctx, sx * .5 * s, -.64 * s, .25 * s, .25 * s); fuell(ctx, WEISS, lw * .6, INK)
        ctx.save(); ctx.translate(0, -.64 * s); augen(ctx, .5 * s, 0, .14 * s, t, seed); ctx.restore()
        wangen(ctx, .7 * s, .12 * s, .15 * s)
        mund(ctx, 0, .12 * s, .42 * s, .25 + sprech * .8)
        for sx in (-1, 1):
            ellipse(ctx, sx * .1 * s, -.1 * s, .03 * s, .03 * s); fuell(ctx, kontur(f))
    else:  # chick
        for k in (-1, 0, 1):
            ellipse(ctx, k * .16 * s, -.98 * s - (0 if k else .1 * s), .11 * s, .22 * s, k * .35); fuell(ctx, f, lw)
        ellipse(ctx, 0, 0, s, .95 * s); fuell(ctx, f, lw)
        augen(ctx, .42 * s, -.12 * s, .15 * s, t, seed); wangen(ctx, .66 * s, .2 * s, .14 * s)
        ctx.move_to(-.22 * s, .2 * s); ctx.line_to(0, .08 * s); ctx.line_to(.22 * s, .2 * s); ctx.line_to(0, .42 * s)
        ctx.close_path(); fuell(ctx, rgb("ff9a2e"), lw * .8)
        ctx.move_to(-.2 * s, .2 * s); ctx.line_to(.2 * s, .2 * s); ctx.set_source_rgb(*kontur(rgb("ff9a2e")))
        ctx.set_line_width(lw * .6); ctx.stroke()
    ctx.restore()


def schatten(ctx, x, y, s, zeichne):
    """Zeichnet eine Figur als dunkle Silhouette (fuer 'Who is this?')."""
    ctx.push_group(); zeichne(); p = ctx.pop_group()
    ctx.set_source_rgb(*rgb("4a3a80")); ctx.mask(p)


def ballon(ctx, x, y, s, farbe, t, seed=0):
    if s < 4:
        return
    lw = max(3, s * .06)
    ctx.save(); ctx.translate(x, y); ctx.rotate(math.sin(t * 2 + seed) * .07)
    ctx.move_to(0, 1.2 * s)
    for k in range(1, 9):
        ctx.line_to(math.sin(t * 3 + k * .9 + seed) * .08 * s, (1.2 + k * .16) * s)
    ctx.set_source_rgb(*INK); ctx.set_line_width(lw * .6); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.stroke()
    ctx.move_to(-.14 * s, 1.24 * s); ctx.line_to(0, 1.02 * s); ctx.line_to(.14 * s, 1.24 * s); ctx.close_path(); fuell(ctx, farbe, lw)
    ellipse(ctx, 0, 0, .9 * s, 1.08 * s); fuell(ctx, farbe, lw)
    ellipse(ctx, -.42 * s, -.5 * s, .14 * s, .28 * s, .5); fuell(ctx, WEISS, alpha=.75)
    augen(ctx, .32 * s, -.05 * s, .13 * s, t, seed); wangen(ctx, .55 * s, .2 * s, .13 * s)
    mund(ctx, 0, .22 * s, .17 * s, .45)
    ctx.restore()


def sonne(ctx, x, y, r, t, offen):
    """Die Erzaehlerin: eine Sonne, deren Mund sich zur Stimme bewegt."""
    r = r * (1 + .04 * offen)
    for i in range(12):
        a = t * .5 + i * math.pi / 6
        l = r * (1.42 + .08 * math.sin(t * 4 + i * 2))
        ctx.move_to(x + r * 1.05 * math.cos(a - .17), y + r * 1.05 * math.sin(a - .17))
        ctx.line_to(x + l * math.cos(a), y + l * math.sin(a))
        ctx.line_to(x + r * 1.05 * math.cos(a + .17), y + r * 1.05 * math.sin(a + .17)); ctx.close_path()
        fuell(ctx, rgb("ffb21f"), r * .07, rgb("e07b00"))
    ellipse(ctx, x, y, r, r); fuell(ctx, rgb("ffd93b"), r * .08, rgb("e07b00"))
    ctx.save(); ctx.translate(x, y)
    augen(ctx, .36 * r, -.15 * r, .14 * r, t, 5); wangen(ctx, .62 * r, .18 * r, .15 * r)
    mund(ctx, 0, .18 * r, .26 * r, .15 + .85 * offen)
    ctx.restore()


# ---------------- Welt ----------------

def wolke(ctx, x, y, s):
    for dx, dy, r in [(-.9, .1, .5), (-.35, -.25, .7), (.4, -.15, .6), (.95, .12, .45), (0, .2, .7)]:
        ellipse(ctx, x + dx * s, y + dy * s, r * s, r * s * .8)
    fuell(ctx, WEISS, alpha=.95)


def huegel(ctx, y0, amp, wl, ph, farbe, lw=10):
    ctx.move_to(-20, H + 20)
    for x in range(-20, B + 60, 40):
        ctx.line_to(x, y0 + math.sin(x / wl + ph) * amp)
    ctx.line_to(B + 20, H + 20); ctx.close_path(); fuell(ctx, farbe, lw)


def _statisch():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, B, H)
    c = cairo.Context(surf)
    g = cairo.LinearGradient(0, 0, 0, 1500)
    g.add_color_stop_rgb(0, *rgb("38b6ff")); g.add_color_stop_rgb(1, *rgb("c9f3ff"))
    c.set_source(g); c.paint()
    for i, col in enumerate(REGENBOGEN[:6]):
        c.arc(B / 2, 1520, 800 - i * 46, math.pi, 2 * math.pi)
        c.set_source_rgba(*col, .85); c.set_line_width(47); c.stroke()
    huegel(c, 1400, 45, 170, 1.0, rgb("9be88a"))
    huegel(c, 1500, 35, 230, 3.2, rgb("5fd65f"))
    rnd = random.Random(4)
    for _ in range(40):
        x, y = rnd.uniform(0, B), rnd.uniform(1570, H)
        c.move_to(x - 9, y); c.line_to(x, y - 22); c.line_to(x + 9, y)
        c.set_source_rgb(*rgb("3fb84a")); c.set_line_width(6); c.set_line_cap(cairo.LINE_CAP_ROUND); c.stroke()
    return surf


STATISCH = None
BLUMEN = [(70, 1640, 0), (230, 1760, 3), (400, 1650, 5), (560, 1790, 1), (700, 1660, 6), (860, 1770, 4), (1000, 1650, 2)]


def welt(ctx, t, offen):
    global STATISCH
    if STATISCH is None:
        STATISCH = _statisch()
    ctx.set_source_surface(STATISCH, 0, 0); ctx.paint()
    for i, (y, s, v) in enumerate([(470, 95, 22), (760, 70, 14), (1080, 85, 18)]):
        wolke(ctx, (i * 420 + t * v) % (B + 400) - 200, y, s)
    for x, y, ci in BLUMEN:
        k = math.sin(t * 2.2 + x) * 14
        ctx.move_to(x, y + 90); ctx.curve_to(x, y + 40, x + k, y + 30, x + k, y)
        ctx.set_source_rgb(*rgb("2f9e44")); ctx.set_line_width(9); ctx.stroke()
        for j in range(6):
            a = j * math.pi / 3 + t * .6
            ellipse(ctx, x + k + 24 * math.cos(a), y + 24 * math.sin(a), 17, 17); fuell(ctx, REGENBOGEN[ci], 4)
        ellipse(ctx, x + k, y, 15, 15); fuell(ctx, rgb("fff3a0"), 4, rgb("e07b00"))
    for i in range(2):  # Schmetterlinge
        bx = (t * 70 + i * 600) % (B + 200) - 100
        by = 1250 - i * 330 + math.sin(t * 2.5 + i * 2) * 60
        fl = abs(math.sin(t * 14 + i))
        for sx in (-1, 1):
            ellipse(ctx, bx + sx * 16 * fl, by - 6, 18 * fl + 3, 22); fuell(ctx, REGENBOGEN[6 - i * 2], 4)
        ellipse(ctx, bx, by, 4, 16); fuell(ctx, INK)
    sonne(ctx, 170, 215, 100, t, offen)


def schrift(ctx, size):
    ctx.select_font_face(SCHRIFT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(size)


def titel(ctx, txt, cx, cy, size, farbe, t, welle=1.0, maxw=None):
    """Sticker-Schrift: bunte, huepfende Buchstaben mit weissem Rand. farbe = eine Farbe oder Liste."""
    if size < 6:
        return
    schrift(ctx, size)
    w = ctx.text_extents(txt).x_advance + size * (.05 * len(txt) + .15 * txt.count(' '))
    if maxw and w > maxw:
        size *= maxw / w; schrift(ctx, size)
    adv = [ctx.text_extents(ch).x_advance + size * (.2 if ch == ' ' else .05) for ch in txt]
    x0, base = cx - sum(adv) / 2, cy + size * .36
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    for p in range(3):
        x, ci = x0, 0
        for i, ch in enumerate(txt):
            dy = math.sin(t * 5 - i * .7) * size * .055 * welle
            ctx.move_to(x, base + dy + (size * .05 if p == 0 else 0)); ctx.text_path(ch)
            if p == 2:
                ctx.set_source_rgb(*(farbe[ci % len(farbe)] if isinstance(farbe, list) else farbe)); ctx.fill()
                ci += ch != " "
            x += adv[i]
        if p == 0:
            ctx.set_source_rgb(*INK); ctx.set_line_width(size * .32); ctx.stroke()
        elif p == 1:
            ctx.set_source_rgb(*WEISS); ctx.set_line_width(size * .18); ctx.stroke()


# ---------------- Animation ----------------

def hopsen(t, start):
    if t < start:
        return 0
    dt = t - start
    if dt < 0.14:
        return dt / 0.14 * 1.22
    return 1 + math.exp(-5.5 * dt) * math.sin(13 * dt) * .28 if dt < 1.3 else 1


def weg(t, start, dauer=.3):
    """1 -> 0: Figur schrumpft weg."""
    return 1 if t < start else max(0, 1 - (t - start) / dauer)


def funkeln(ctx, cx, cy, t, start, seed, R=330, n=14):
    dt = t - start
    if not 0 <= dt < .9:
        return
    rnd = random.Random(seed)
    for i in range(n):
        a = i * 2 * math.pi / n + rnd.uniform(-.2, .2)
        d = (R * .35 + rnd.uniform(0, R)) * (1 - math.exp(-5 * dt))
        stern_pfad(ctx, cx + d * math.cos(a), cy + d * math.sin(a), (22 + rnd.uniform(0, 26)) * (1 - dt / .9) + 1, dt * 5 + i)
        fuell(ctx, REGENBOGEN[i % 7], 4)


def konfetti(ctx, t, start, seed, n=90):
    dt = t - start
    if dt < 0:
        return
    rnd = random.Random(seed)
    for i in range(n):
        x = rnd.uniform(0, B) + math.sin(dt * 3 + i) * 40
        y = -60 - rnd.uniform(0, 900) + dt * rnd.uniform(420, 720)
        if -40 < y < H:
            ctx.save(); ctx.translate(x, y); ctx.rotate(dt * rnd.uniform(3, 8) + i)
            ctx.rectangle(-14, -8, 28, 16); ctx.restore(); fuell(ctx, REGENBOGEN[i % 7])


def huepf(t, i=0, v=9):
    return -abs(math.sin(t * v + i * .9)) * 55


# ---------------- Szenen ----------------
# Jede Szene liefert: Sprechzeilen [(key, text, pause)], eine Zeichen-Funktion und Sound-Zeitpunkte.

def szene_counting(seed):
    rnd = random.Random(seed)
    n, art = rnd.randint(3, 6), rnd.choice(list(TIERE))
    pl, farbe = TIERE[art]["pl"], rnd.choice(REGENBOGEN)
    zeilen = [("intro", f"Hi friends! Let's count the {pl}!", .35)]
    zeilen += [(f"n{i}", f"{ZAHLEN[i].capitalize()}!", .4) for i in range(1, n + 1)]
    zeilen += [("total", f"{ZAHLEN[n].capitalize()} {pl}! Great job!", .3), ("bye", "Bye bye! See you next time!", .5)]
    spalten = 3 if n > 4 or n == 3 else 2
    reihen = math.ceil(n / spalten)
    plaetze = []
    for i in range(n):
        r_, s_ = divmod(i, spalten)
        anz = min(spalten, n - r_ * spalten)
        plaetze.append((B / 2 + (s_ - (anz - 1) / 2) * 310, 760 + (r_ - (reihen - 1) / 2) * 350 - 40))

    def zeichne(ctx, t, c, offen):
        welt(ctx, t, offen)
        titel(ctx, "LET'S COUNT!", 660, 215, 125, REGENBOGEN, t, maxw=690)
        s0 = hopsen(t, c["intro"][0] + .2) * weg(t, c["n1"][0] - .35)
        tier(ctx, art, B / 2, 720, 190 * s0, t, 9, wink=True)
        for i, (x, y) in enumerate(plaetze):
            st = c[f"n{i + 1}"][0] - .1
            dy = huepf(t, i) if t >= c["total"][0] else math.sin(t * 2.4 + i) * 8
            tier(ctx, art, x, y + dy, 92 * hopsen(t, st), t, i, wink=t >= c["bye"][0])
            funkeln(ctx, x, y, t, st, seed + i, R=170, n=8)
        if c["n1"][0] - .1 <= t < c["total"][0]:
            k = max(i for i in range(1, n + 1) if t >= c[f"n{i}"][0] - .1)
            titel(ctx, str(k), B / 2, 1290, 250 * hopsen(t, c[f"n{k}"][0] - .1), farbe, t, 0)
        _finale(ctx, t, c, seed, f"{n} {pl.upper()}!", farbe)

    pops = [c for c in [f"n{i}" for i in range(1, n + 1)]]
    return zeilen, zeichne, pops, f"counting_{n}_{pl}"


def _finale(ctx, t, c, seed, text, farbe):
    if t >= c["total"][0]:
        konfetti(ctx, t, c["total"][0], seed)
        if t < c["bye"][0]:
            s = hopsen(t, c["total"][0])
            titel(ctx, text, B / 2, 1230, 130 * s, farbe, t, maxw=960)
            titel(ctx, "GREAT JOB!", B / 2, 1380, 120 * s, REGENBOGEN, t, maxw=960)
        else:
            titel(ctx, "BYE BYE!", B / 2, 1290, 170 * hopsen(t, c["bye"][0]), REGENBOGEN, t)
        funkeln(ctx, B / 2, 1290, t, c["total"][0], seed + 50, R=480, n=18)


def szene_colors(seed):
    rnd = random.Random(seed)
    namen = rnd.sample(list(COLORS), 4)
    zeilen = [("intro", "Hi friends! Let's learn colors!", .35)]
    for i, nm in enumerate(namen):
        art = "an" if nm[0] in "aeiou" else "a"
        zeilen += [(f"q{i}", "What color is this?", .75), (f"a{i}", f"{nm.capitalize()}! {art.capitalize()} {nm} balloon!", .6)]
    zeilen += [("total", "Yay! You know your colors! Great job!", .3), ("bye", "Bye bye! See you next time!", .5)]

    def zeichne(ctx, t, c, offen):
        welt(ctx, t, offen)
        titel(ctx, "COLORS!", 660, 215, 150, REGENBOGEN, t, maxw=690)
        if t < c["q0"][0]:
            for i in range(4):
                ballon(ctx, 180 + i * 240, 800 + math.sin(t * 3 + i) * 30, 85 * hopsen(t, .3 + i * .15) * weg(t, c["q0"][0] - .3),
                       REGENBOGEN[(i * 2 + seed) % 7], t, i)
        for i, nm in enumerate(namen):
            q, a = c[f"q{i}"][0], c[f"a{i}"]
            raus = a[1] + .1
            if q <= t < raus + .5:
                k = min(1, (t - q) / .8); k = 1 - (1 - k) ** 3
                y = 2300 + (740 - 2300) * k + math.sin(t * 2.5) * 16
                if t > raus:
                    y -= ((t - raus) / .5) ** 2 * 1500
                ballon(ctx, B / 2, y, 215, COLORS[nm], t, i)
                if t < a[0]:
                    titel(ctx, "?", B / 2 + math.sin(t * 6) * 14, 1290, 230 * hopsen(t, q + .3), COLORS["yellow"], t, 0)
                elif t < raus:
                    titel(ctx, nm.upper(), B / 2, 1290, 210 * hopsen(t, a[0]), COLORS[nm], t, maxw=960)
                funkeln(ctx, B / 2, 740, t, a[0], seed + i)
        if t >= c["total"][0]:
            for i, nm in enumerate(namen):
                ballon(ctx, 180 + i * 240, 780 + huepf(t, i, 5), 88 * hopsen(t, c["total"][0] + i * .1), COLORS[nm], t, i)
        _finale(ctx, t, c, seed, "YOU DID IT!", COLORS[namen[0]])

    return zeilen, zeichne, [f"a{i}" for i in range(4)], "colors_" + "_".join(namen)


def szene_animals(seed):
    rnd = random.Random(seed)
    arten = rnd.sample(list(TIERE), 3)
    zeilen = [("intro", "Hi friends! Who is hiding today?", .35)]
    for i, a in enumerate(arten):
        zeilen += [(f"q{i}", "Who is this?", .8), (f"a{i}", f"It's a {a}! {TIERE[a]['satz']}", .6)]
    zeilen += [("total", "You found them all! Great job!", .3), ("bye", "Bye bye! See you next time!", .5)]
    farben = rnd.sample(REGENBOGEN, 3)

    def zeichne(ctx, t, c, offen):
        welt(ctx, t, offen)
        titel(ctx, "WHO IS THIS?", 660, 215, 120, REGENBOGEN, t, maxw=690)
        if t < c["q0"][0]:
            titel(ctx, "?", B / 2, 760, 420 * hopsen(t, .3) * weg(t, c["q0"][0] - .3), REGENBOGEN[seed % 7], t, 0)
        for i, art in enumerate(arten):
            q, a = c[f"q{i}"][0], c[f"a{i}"]
            raus = a[1] + .15
            if q <= t < raus + .3:
                s = 200 * hopsen(t, q) * weg(t, raus)
                if t < a[0]:
                    wob = math.sin(t * 7) * 12
                    schatten(ctx, B / 2, 700, s, lambda: tier(ctx, art, B / 2 + wob, 700, s, 0, i))
                    titel(ctx, "?", B / 2 + math.sin(t * 6) * 14, 1290, 230 * hopsen(t, q + .3), COLORS["yellow"], t, 0)
                else:
                    s *= 1 + .18 * math.exp(-6 * (t - a[0])) * math.sin(14 * (t - a[0]))
                    spricht = t > a[0] + (a[1] - a[0]) * .42
                    tier(ctx, art, B / 2, 700 + (huepf(t, 0, 10) if spricht else 0), s, t, i, wink=not spricht)
                    if t < raus:
                        titel(ctx, art.upper(), B / 2, 1290, 230 * hopsen(t, a[0]), farben[i], t, maxw=960)
                funkeln(ctx, B / 2, 760, t, a[0], seed + i, R=420, n=18)
        if t >= c["total"][0]:
            for i, art in enumerate(arten):
                tier(ctx, art, 200 + i * 340, 760 + huepf(t, i), 115 * hopsen(t, c["total"][0] + i * .1), t, i, wink=True)
        _finale(ctx, t, c, seed, "YOU FOUND THEM!", farben[0])

    return zeilen, zeichne, [f"a{i}" for i in range(3)], "animals_" + "_".join(arten)


SZENEN = {"counting": szene_counting, "colors": szene_colors, "animals": szene_animals}


# ---------------- Stimme, Musik, Ton ----------------

_K, _CACHE = None, {}


def stimme(text):
    """Text -> gesprochene Stimme (numpy, 44.1 kHz)."""
    global _K
    if text in _CACHE:
        return _CACHE[text]
    if _K is None:
        from kokoro_onnx import Kokoro
        for pfad in (MODELL, STIMMEN):
            if not os.path.exists(pfad):
                os.makedirs(os.path.dirname(pfad), exist_ok=True)
                print("Lade Stimm-Datei:", os.path.basename(pfad))
                urllib.request.urlretrieve(MODELL_URL + os.path.basename(pfad), pfad)
        _K = Kokoro(MODELL, STIMMEN)
    a, sr = _K.create(text, voice=STIMME, speed=TEMPO, lang="en-us")
    a = np.asarray(a, dtype=np.float64).flatten()
    laut = np.where(np.abs(a) > 0.015 * np.abs(a).max())[0]
    a = a[max(0, laut[0] - int(.03 * sr)):laut[-1] + int(.1 * sr)]
    n = int(len(a) * SR / sr / TONHOEHE)
    a = np.interp(np.linspace(0, len(a) - 1, n), np.arange(len(a)), a)
    a = a / max(np.abs(a).max(), 1e-9) * .9
    _CACHE[text] = a
    return a


def _ton(audio, start, f, dauer, amp, abkling, art="glocke"):
    s = int(start * SR)
    if s >= len(audio):
        return
    tt = np.arange(min(int(dauer * SR), len(audio) - s)) / SR
    if art == "glocke":
        w = np.sin(2 * np.pi * f * tt) + .35 * np.sin(2 * np.pi * 3 * f * tt) * np.exp(-8 * tt)
    elif art == "zupf":
        w = np.sin(2 * np.pi * f * tt) + .45 * np.sin(4 * np.pi * f * tt) + .2 * np.sin(6 * np.pi * f * tt)
    else:
        w = np.sin(2 * np.pi * f * tt)
    audio[s:s + len(tt)] += amp * w * np.exp(-abkling * tt) * np.minimum(1, tt * 400)


def musik(dauer, seed):
    """Froehliche Hintergrundmusik: Bass, gezupfte Akkorde und Glockenspiel."""
    a = np.zeros(int(dauer * SR))
    rnd = random.Random(seed)
    C, D, E, F, G, A, Hh = 261.63, 293.66, 329.63, 349.23, 392.0, 440.0, 493.88
    akkorde = [(C, [C, E, G]), (G, [Hh / 2, D, G]), (A, [C, E, A]), (F, [C, F, A])]
    penta = [C * 2, D * 2, E * 2, G * 2, A * 2, C * 4]
    achtel = 60 / 118 / 2
    i, letzte = 0, 2
    while i * achtel < dauer:
        grund, ak = akkorde[(i // 8) % 4]
        t0 = i * achtel
        if i % 4 == 0:
            _ton(a, t0, grund / 2, achtel * 3.5, .5, 3, "bass")
        _ton(a, t0, ak[[0, 1, 2, 1][i % 4]], achtel * 2, .28, 6, "zupf")
        if i % 2 == 0 and rnd.random() < .75:
            letzte = max(0, min(5, letzte + rnd.choice([-1, -1, 0, 1, 1, 2])))
            _ton(a, t0, penta[letzte], achtel * 3, .22, 5, "glocke")
        if i % 4 == 2:  # leiser Shaker
            n = int(.04 * SR); s = int(t0 * SR)
            if s + n < len(a):
                a[s:s + n] += .06 * np.random.default_rng(i).standard_normal(n) * np.exp(-np.arange(n) / SR * 90)
        i += 1
    return a / max(np.abs(a).max(), 1e-9)


def effekte(dauer, pops, tada):
    a = np.zeros(int(dauer * SR))
    for k, tp in enumerate(pops):  # "Pop!"
        s = int(tp * SR); tt = np.arange(int(.25 * SR)) / SR
        if s + len(tt) < len(a):
            f = 380 + 1000 * (1 - np.exp(-22 * tt)) + 50 * k
            a[s:s + len(tt)] += .6 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-12 * tt)
        for j, f in enumerate([1568, 2093, 2637]):  # Glitzern
            _ton(a, tp + .08 + j * .06, f, .4, .16, 9)
    for j, f in enumerate([523.25, 659.25, 783.99, 1046.5, 1318.5]):  # "Tadaa!"
        _ton(a, tada + j * .09, f, 1.0, .4, 3.5)
    return a


def vertonen(zeilen, pop_keys, seed, pfad):
    t, cues, teile = .5, {}, []
    for key, text, pause in zeilen:
        a = stimme(text)
        cues[key] = (t, t + len(a) / SR)
        teile.append((t, a))
        t += len(a) / SR + pause
    dauer = t + .4
    voc = np.zeros(int(dauer * SR))
    for st, a in teile:
        s = int(st * SR); voc[s:s + len(a)] += a[:len(voc) - s]
    # Lautstaerke-Kurve der Stimme -> Mundbewegung + Musik leiser, wenn gesprochen wird
    hop = SR // FPS
    env = np.array([np.sqrt(np.mean(voc[i:i + hop] ** 2)) for i in range(0, len(voc), hop)])
    env = np.clip(env / (np.percentile(env[env > 0], 90) + 1e-9), 0, 1)
    env = np.convolve(env, [.25, .5, .25], "same")
    duck = np.repeat(np.convolve(env > .05, np.ones(12) / 12, "same"), hop)[:len(voc)]
    mix_ = voc + musik(dauer, seed) * (.24 - .12 * duck) + effekte(dauer, [cues[k][0] - .1 for k in pop_keys], cues["total"][0]) * .45
    mix_ = mix_ / max(np.abs(mix_).max(), 1e-9) * .92
    n_aus = int(.4 * SR); mix_[-n_aus:] *= np.linspace(1, 0, n_aus)
    with wave.open(pfad, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix_ * 32767).astype(np.int16).tobytes())
    return cues, env, dauer


# ---------------- Rendern ----------------

def render(thema, seed, ordner):
    zeilen, zeichne, pop_keys, name = SZENEN[thema](seed)
    os.makedirs(ordner, exist_ok=True)
    wav = os.path.join(ordner, f"_{seed}.wav")
    out = os.path.join(ordner, f"kids_{name}_{seed}.mp4")
    cues, env, dauer = vertonen(zeilen, pop_keys, seed, wav)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
           "-s", f"{B}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, B, H)
    for i in range(int(dauer * FPS)):
        ctx = cairo.Context(surf)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        zeichne(ctx, i / FPS, cues, float(env[min(i, len(env) - 1)]))
        surf.flush()
        p.stdin.write(bytes(surf.get_data()))
    p.stdin.close(); p.wait()
    os.remove(wav)
    with open(out.replace(".mp4", ".txt"), "w") as f:  # Sprechtext, praktisch fuer die Videobeschreibung
        f.write("\n".join(z[1] for z in zeilen) + "\n")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--anzahl", type=int, default=1)
    ap.add_argument("--thema", choices=list(SZENEN))
    ap.add_argument("--ordner", default="shorts")
    ap.add_argument("--seed", type=int)
    a = ap.parse_args()
    for _ in range(a.anzahl):
        seed = a.seed or random.randint(1000, 99999)
        thema = a.thema or random.choice(list(SZENEN))
        print("Fertig:", render(thema, seed, a.ordner))
