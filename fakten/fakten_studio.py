#!/usr/bin/env python3
"""
Fakten-Studio: "Wissen in 30 Sekunden" als Shorts (1080x1920, Englisch), komplett aus Code.
Jedes Video hat eigene Szenen, eine Erzaehlstimme, Untertitel, Musik und einen Fortschrittsbalken.

    python3 fakten_studio.py --liste
    python3 fakten_studio.py sun          # ein Video rendern
    python3 fakten_studio.py --alle

Braucht: pip install pycairo numpy kokoro-onnx ; ffmpeg ; Schrift "Poppins" ; Stimm-Modell in ./modelle
"""
import argparse, math, os, random, re, subprocess, wave
import cairo
import numpy as np

W, H, FPS, SR = 1080, 1920, 60, 48000
HIER = os.path.dirname(os.path.abspath(__file__))
MODELLE = os.path.join(HIER, "modelle")
STIMME, TEMPO = "am_michael", 1.02
SCHRIFT = "Poppins"


def rgb(h):
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


WEISS, GELB, CYAN, PINK, DUNKEL = (1, 1, 1), rgb("ffd23f"), rgb("4de1ff"), rgb("ff5d8f"), rgb("0b1026")


def mix(a, b, k):
    return tuple(x * (1 - k) + y * k for x, y in zip(a, b))


def ease(k):
    k = max(0.0, min(1.0, k))
    return k * k * (3 - 2 * k)


def lerp(a, b, k):
    return a + (b - a) * k


def zahl(n):
    return f"{int(round(n)):,}"


# ---------------- Zeichen-Helfer ----------------

def text(ctx, s, x, y, size, farbe=WEISS, rand=0.0, maxw=None, alpha=1.0, anker="mitte"):
    """Fetter Text, zentriert um (x, y). rand = dunkle Kontur (Anteil der Schriftgroesse)."""
    if size < 4 or alpha <= 0:
        return
    ctx.select_font_face(SCHRIFT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(size)
    e = ctx.text_extents(s)
    if maxw and e.x_advance > maxw:
        size *= maxw / e.x_advance; ctx.set_font_size(size); e = ctx.text_extents(s)
    x0 = x - e.x_advance / 2 if anker == "mitte" else (x if anker == "links" else x - e.x_advance)
    ctx.move_to(x0, y + size * .35); ctx.text_path(s)
    if rand:
        ctx.set_source_rgba(*DUNKEL, alpha); ctx.set_line_width(size * rand); ctx.set_line_join(cairo.LINE_JOIN_ROUND); ctx.stroke_preserve()
    ctx.set_source_rgba(*farbe, alpha); ctx.fill()


def kreis(ctx, x, y, r, farbe, alpha=1.0):
    if r <= 0:
        return
    ctx.arc(x, y, r, 0, 2 * math.pi); ctx.set_source_rgba(*farbe, alpha); ctx.fill()


def glut(ctx, x, y, r, farbe, staerke=.6):
    g = cairo.RadialGradient(x, y, 0, x, y, r)
    g.add_color_stop_rgba(0, *farbe, staerke); g.add_color_stop_rgba(1, *farbe, 0)
    ctx.set_source(g); ctx.arc(x, y, r, 0, 2 * math.pi); ctx.fill()


def verlauf(ctx, oben, unten):
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, *oben); g.add_color_stop_rgb(1, *unten)
    ctx.set_source(g); ctx.paint()


_STERNE = [(random.Random(i).uniform(0, W), random.Random(i * 7 + 1).uniform(0, H), random.Random(i * 3 + 2).uniform(.8, 2.6)) for i in range(140)]


def sterne(ctx, t, alpha=1.0):
    for i, (x, y, r) in enumerate(_STERNE):
        kreis(ctx, x, y, r, WEISS, alpha * (.35 + .35 * math.sin(t * 1.5 + i)))


def erde(ctx, x, y, r):
    if r < 1.2:
        kreis(ctx, x, y, max(r, 1.6), rgb("4aa3ff")); return
    glut(ctx, x, y, r * 1.35, rgb("4aa3ff"), .35)
    g = cairo.RadialGradient(x - r * .35, y - r * .35, r * .1, x, y, r)
    g.add_color_stop_rgb(0, *rgb("6cc4ff")); g.add_color_stop_rgb(1, *rgb("1b5fc4"))
    ctx.arc(x, y, r, 0, 2 * math.pi); ctx.set_source(g); ctx.fill()
    if r > 9:
        ctx.save(); ctx.arc(x, y, r, 0, 2 * math.pi); ctx.clip()
        for dx, dy, rx, ry in [(-.35, -.25, .38, .3), (.3, .15, .3, .42), (-.2, .55, .3, .2), (.55, -.5, .22, .16)]:
            ctx.save(); ctx.translate(x + dx * r, y + dy * r); ctx.scale(rx * r, ry * r); ctx.arc(0, 0, 1, 0, 2 * math.pi); ctx.restore()
            ctx.set_source_rgb(*rgb("48c774")); ctx.fill()
        ctx.restore()


def jupiter(ctx, x, y, r):
    if r < 1.5:
        kreis(ctx, x, y, max(r, 1.5), rgb("e0b98a")); return
    ctx.save(); ctx.arc(x, y, r, 0, 2 * math.pi); ctx.clip()
    for i, f in enumerate(["e8c9a0", "c98f5f", "f0dcc0", "b97a4a", "e8c9a0", "d6a878", "f0dcc0", "c98f5f", "e0b98a"]):
        ctx.rectangle(x - r, y - r + i * 2 * r / 9, 2 * r, 2 * r / 9 + 1); ctx.set_source_rgb(*rgb(f)); ctx.fill()
    ctx.save(); ctx.translate(x + r * .35, y + r * .28); ctx.scale(r * .2, r * .12); ctx.arc(0, 0, 1, 0, 2 * math.pi); ctx.restore()
    ctx.set_source_rgb(*rgb("c2553a")); ctx.fill()
    g = cairo.RadialGradient(x - r * .4, y - r * .4, r * .2, x, y, r)
    g.add_color_stop_rgba(0, 1, 1, 1, .12); g.add_color_stop_rgba(1, 0, 0, 0, .35)
    ctx.rectangle(x - r, y - r, 2 * r, 2 * r); ctx.set_source(g); ctx.fill(); ctx.restore()


def sonne(ctx, x, y, r, t=0):
    glut(ctx, x, y, r * 1.6, rgb("ffb300"), .55)
    g = cairo.RadialGradient(x, y, r * .1, x, y, r)
    g.add_color_stop_rgb(0, *rgb("fff3b0")); g.add_color_stop_rgb(.7, *rgb("ffc21a")); g.add_color_stop_rgb(1, *rgb("ff8a00"))
    ctx.arc(x, y, r, 0, 2 * math.pi); ctx.set_source(g); ctx.fill()


def mond(ctx, x, y, r):
    kreis(ctx, x, y, r, rgb("cfd3dc"))
    for dx, dy, q in [(-.3, -.2, .22), (.3, .3, .16), (.15, -.45, .12), (-.4, .4, .1)]:
        kreis(ctx, x + dx * r, y + dy * r, q * r, rgb("a9aebb"))


# ---------------- Videos: jede Szene = (Sprechtext, Pause) ; zeichne(ctx, i, tl, dauer, t, V) ----------------

def v_sun(ctx, i, tl, d, t, V):
    verlauf(ctx, rgb("070a1c"), rgb("161d45")); sterne(ctx, t)
    cams = [(0, 230), (0, 300), (10, 34), (100, 4.4), (132, 4.0), (151, .28)]
    c0 = cams[max(i - 1, 0)]; c1 = cams[i]
    k = ease(tl / 1.3) if i else 1
    cx = lerp(c0[0], c1[0], k); s = math.exp(lerp(math.log(c0[1]), math.log(c1[1]), k))
    X = lambda wx: W / 2 + (wx - cx) * s
    Y = 930
    sonne(ctx, X(151), Y, 109 * s, t)
    jupiter(ctx, X(16), Y, 11 * s)
    erde(ctx, X(0), Y, 1 * s)
    if i == 0:
        text(ctx, "HOW BIG IS", W / 2, 420, 120, WEISS, .12); text(ctx, "THE SUN?", W / 2, 560, 170, GELB, .12)
    else:
        text(ctx, "HOW BIG IS THE SUN?", W / 2, 190, 62, GELB, .15)
    if i == 1:
        text(ctx, "EARTH", W / 2, Y + 400, 90, CYAN, .12, alpha=ease(tl / .5))
    if i == 2:
        a = ease((tl - 1.0) / .5)
        text(ctx, "EARTH", X(0), Y + 110, 46, CYAN, .15, alpha=a); text(ctx, "JUPITER", X(16), Y + 11 * s + 90, 90, rgb("f0c890"), .12, alpha=a)
        text(ctx, "11x WIDER", W / 2, 420, 110, WEISS, .12, alpha=ease((tl - 1.6) / .4))
    if i in (3, 4):
        text(ctx, "JUPITER", X(16), Y + 11 * s + 50, 34, rgb("f0c890"), .18)
        text(ctx, "EARTH", X(0) + 10, Y - 60, 30, CYAN, .18, anker="links")
    if i == 3:
        n = int(109 * ease((tl - 1.2) / max(d - 2.0, .5)))
        for j in range(n):
            kreis(ctx, X(151 - 108 + j * 2), Y, max(1 * s * .82, 2), rgb("4aa3ff"))
        text(ctx, f"{n} EARTHS", W / 2, 400, 120, WEISS, .12, alpha=ease((tl - 1.0) / .4))
        text(ctx, "SIDE BY SIDE", W / 2, 520, 70, CYAN, .14, alpha=ease((tl - 1.0) / .4))
    if i == 4:
        kk = ease((tl - .3) / max(d - 1.2, .5))
        rnd = random.Random(9)
        for j in range(int(1800 * kk)):
            a, rr = rnd.uniform(0, 2 * math.pi), 105 * math.sqrt(rnd.random())
            kreis(ctx, X(151 + rr * math.cos(a)), Y + rr * math.sin(a) * s, 3, rgb("4aa3ff"), .9)
        text(ctx, zahl(1300000 * kk), W / 2, 400, 135, WEISS, .12)
        text(ctx, "EARTHS FIT INSIDE", W / 2, 525, 70, CYAN, .14)
    if i == 5:
        a = ease((tl - 1.0) / .6)
        text(ctx, "JUST AN", W / 2, 520, 90, WEISS, .12, alpha=a); text(ctx, "AVERAGE STAR", W / 2, 640, 110, GELB, .12, alpha=a)
        text(ctx, "THE SUN", X(151), Y + 100, 44, GELB, .15, alpha=a)


def v_light(ctx, i, tl, d, t, V):
    verlauf(ctx, rgb("05071a"), rgb("1a1040")); sterne(ctx, t)
    if i:
        text(ctx, "HOW FAST IS LIGHT?", W / 2, 190, 62, GELB, .15)
    if i == 0:
        text(ctx, "HOW FAST", W / 2, 440, 140, WEISS, .12); text(ctx, "IS LIGHT?", W / 2, 600, 160, GELB, .12)
        for j in range(5):
            x = ((t * 2600 + j * 420) % (W + 900)) - 450; y = 900 + j * 95
            g = cairo.LinearGradient(x - 420, 0, x, 0); g.add_color_stop_rgba(0, 1, 1, 1, 0); g.add_color_stop_rgba(1, *GELB, .9)
            ctx.set_source(g); ctx.rectangle(x - 420, y - 5, 420, 10); ctx.fill(); glut(ctx, x, y, 40, GELB, .9)
    if i == 1:
        k = ease(tl / max(d - 1.0, .5))
        text(ctx, zahl(300000 * k), W / 2, 760, 190, WEISS, .1, maxw=980)
        text(ctx, "KILOMETERS", W / 2, 930, 100, CYAN, .12); text(ctx, "EVERY SECOND", W / 2, 1050, 100, GELB, .12)
        for j in range(14):
            y = 1200 + (j * 37) % 260; x = ((t * (1800 + j * 130) + j * 300) % (W + 400)) - 200
            ctx.set_source_rgba(1, 1, 1, .25); ctx.rectangle(x - 160, y, 160, 4); ctx.fill()
    if i == 2:
        cx, cy, R = W / 2, 930, 235
        erde(ctx, cx, cy, R)
        k = min(1, tl / max(d - .8, 1))
        ang = k * 7.5 * 2 * math.pi - math.pi / 2
        ro = R + 70
        ctx.set_line_width(10); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        for j in range(24):
            a = ang - j * .09
            if a < -math.pi / 2:
                break
            ctx.set_source_rgba(*GELB, .9 * (1 - j / 24)); ctx.arc(cx, cy, ro, a - .1, a); ctx.stroke()
        glut(ctx, cx + ro * math.cos(ang), cy + ro * math.sin(ang), 46, GELB, 1)
        text(ctx, f"{k * 7.5:.1f}x", W / 2, 440, 170, WEISS, .1)
        text(ctx, "AROUND THE EARTH", W / 2, 1330, 72, CYAN, .14); text(ctx, "IN ONE SECOND", W / 2, 1420, 72, GELB, .14)
    if i == 3:
        ex, ey, mx, my = 230, 1180, 860, 620
        erde(ctx, ex, ey, 130); mond(ctx, mx, my, 44)
        k = max(0, min(1, (tl - .5) / 1.3))
        bx, by = lerp(ex, mx, k), lerp(ey, my, k)
        ctx.set_source_rgba(*GELB, .85); ctx.set_line_width(8); ctx.move_to(ex, ey); ctx.line_to(bx, by); ctx.stroke()
        glut(ctx, bx, by, 40, GELB, 1)
        text(ctx, f"{k * 1.3:.1f} s", W / 2, 420, 180, WEISS, .1)
        text(ctx, "EARTH", ex, ey + 190, 46, CYAN, .15); text(ctx, "MOON", mx, my - 90, 46, rgb("cfd3dc"), .15)
        text(ctx, "384,000 KM", 600, 1000, 60, GELB, .15, alpha=ease((tl - 1.8) / .4))
    if i == 4:
        sonne(ctx, W / 2, 520, 190, t); erde(ctx, W / 2, 1300, 62)
        k = ease(tl / max(d - .6, 1))
        y = lerp(710, 1238, k)
        ctx.set_source_rgba(*GELB, .5); ctx.set_line_width(6); ctx.set_dash([18, 14]); ctx.move_to(W / 2, 710); ctx.line_to(W / 2, 1238); ctx.stroke(); ctx.set_dash([])
        glut(ctx, W / 2, y, 44, WEISS, 1)
        sek = int(500 * k)
        text(ctx, f"{sek // 60}:{sek % 60:02d}", 820, 960, 130, WEISS, .1); text(ctx, "MINUTES", 820, 1060, 50, CYAN, .15)
        text(ctx, "150 MILLION KM", 250, 975, 44, GELB, .16)
    if i == 5:
        sonne(ctx, W / 2, 620, 210, t)
        a = ease(tl / .6)
        text(ctx, "THE SUNLIGHT YOU SEE", W / 2, 1010, 74, WEISS, .13, alpha=a, maxw=980); text(ctx, "IS 8 MINUTES OLD", W / 2, 1130, 100, GELB, .12, alpha=a, maxw=980)


TIEFEN = [0, 200, 1000, 3800, 8849, 10935, 10935]
_SCHNEE = [(random.Random(i).uniform(0, W), random.Random(i + 99).uniform(0, H), random.Random(i + 7).uniform(1.5, 4)) for i in range(70)]


def v_ocean(ctx, i, tl, d, t, V):
    k = ease(tl / max(d * .55, .8)) if i else 0
    tiefe = lerp(TIEFEN[max(i - 1, 0)], TIEFEN[i], k)
    stufen = [(0, "35b5f0"), (200, "136fb5"), (1000, "0a2a55"), (3800, "06142e"), (11000, "02060f")]
    for (d0, f0), (d1, f1) in zip(stufen, stufen[1:]):
        if tiefe <= d1:
            f = mix(rgb(f0), rgb(f1), (tiefe - d0) / (d1 - d0)); break
    verlauf(ctx, mix(f, WEISS, .08), mix(f, (0, 0, 0), .35))
    lauf = V["weg"](t)  # Summe der bisherigen Sinkbewegung -> Teilchen ziehen nach oben
    for x, y, r in _SCHNEE:
        kreis(ctx, x, (y - lauf * .9) % H, r, WEISS, .18)
    if i == 0:
        for j in range(3):
            ctx.move_to(0, 330 + j * 26)
            for x in range(0, W + 40, 40):
                ctx.line_to(x, 330 + j * 26 + math.sin(x / 90 + t * 2 + j) * 14)
            ctx.line_to(W, 0); ctx.line_to(0, 0); ctx.close_path(); ctx.set_source_rgba(1, 1, 1, .12 + j * .05); ctx.fill()
        text(ctx, "HOW DEEP IS", W / 2, 700, 120, WEISS, .12); text(ctx, "THE OCEAN?", W / 2, 850, 150, GELB, .12)
        return
    text(ctx, "HOW DEEP IS THE OCEAN?", W / 2, 190, 58, GELB, .15)
    text(ctx, f"{zahl(tiefe)} m", W / 2 + 40, 400, 150, WEISS, .1)
    # Tiefenmesser links
    y0, y1 = 560, 1300
    ctx.set_source_rgba(1, 1, 1, .35); ctx.set_line_width(6); ctx.move_to(80, y0); ctx.line_to(80, y1); ctx.stroke()
    for m in range(0, 11001, 2000):
        yy = lerp(y0, y1, m / 11000); ctx.move_to(66, yy); ctx.line_to(94, yy); ctx.stroke()
    kreis(ctx, 80, lerp(y0, y1, tiefe / 11000), 16, GELB)
    a = ease((tl - d * .5) / .5)
    if i == 1:
        for j in range(5):
            x = 250 + j * 160
            g = cairo.LinearGradient(0, 520, 0, 1250); g.add_color_stop_rgba(0, 1, 1, .8, .32); g.add_color_stop_rgba(1, 1, 1, .8, 0)
            ctx.move_to(x - 30, 520); ctx.line_to(x + 40, 520); ctx.line_to(x + 150 + math.sin(t + j) * 30, 1250); ctx.line_to(x - 60, 1250); ctx.close_path(); ctx.set_source(g); ctx.fill()
        text(ctx, "SUNLIGHT FADES", W / 2, 1000, 84, CYAN, .13, alpha=a)
    if i == 2:
        x = W / 2 + math.sin(t * .8) * 120
        glut(ctx, x, 900, 150, rgb("9dffcf"), .8); kreis(ctx, x, 900, 14, rgb("eafff5"))
        text(ctx, "TOTAL DARKNESS", W / 2, 1150, 84, CYAN, .13, alpha=a)
    if i == 3:
        ctx.rectangle(0, 1120, W, 800); ctx.set_source_rgb(*rgb("0d1d3a")); ctx.fill()
        ctx.save(); ctx.translate(W / 2 + 30, 1050); ctx.rotate(-.08)
        ctx.move_to(-330, -10); ctx.line_to(330, -10); ctx.line_to(270, 80); ctx.line_to(-270, 80); ctx.close_path(); ctx.set_source_rgb(*rgb("31486e")); ctx.fill()
        ctx.rectangle(-220, -55, 420, 46); ctx.fill()
        for j in range(4):
            ctx.rectangle(-170 + j * 105, -135, 42, 82)
        ctx.set_source_rgb(*rgb("3d5a8a")); ctx.fill(); ctx.restore()
        text(ctx, "THE TITANIC", W / 2, 780, 96, CYAN, .13, alpha=a)
    if i == 4:
        oben, unten = 600, 1290
        ctx.move_to(170, oben); ctx.line_to(W - 90, oben); ctx.line_to(W / 2 + 60, unten); ctx.close_path(); ctx.set_source_rgba(*rgb("123a78"), .9); ctx.fill()
        gipfel = lerp(unten, oben, 8849 / 10935)
        ctx.move_to(W / 2 + 60 - 230, unten + 2); ctx.line_to(W / 2 + 60, gipfel); ctx.line_to(W / 2 + 60 + 230, unten + 2); ctx.close_path(); ctx.set_source_rgb(*rgb("7d8aa3")); ctx.fill()
        ctx.move_to(W / 2 + 60 - 55, gipfel + 165); ctx.line_to(W / 2 + 60, gipfel); ctx.line_to(W / 2 + 60 + 55, gipfel + 165); ctx.close_path(); ctx.set_source_rgb(*WEISS); ctx.fill()
        ctx.set_source_rgba(*GELB, a); ctx.set_line_width(6); ctx.move_to(W / 2 + 60, oben + 6); ctx.line_to(W / 2 + 60, gipfel - 10); ctx.stroke()
        text(ctx, "2 KM OF WATER", W / 2 + 80, oben - 55, 60, GELB, .15, alpha=a)
        text(ctx, "MOUNT EVEREST", W / 2 + 60, unten + 80, 64, WEISS, .15, alpha=a)
    if i >= 5:
        ctx.move_to(0, 900); ctx.line_to(W / 2 - 60, 1330); ctx.line_to(W / 2 + 90, 1330); ctx.line_to(W, 860); ctx.line_to(W, H); ctx.line_to(0, H); ctx.close_path()
        ctx.set_source_rgb(*rgb("0a1326")); ctx.fill()
        sx, sy = W / 2 + 10 + math.sin(t) * 12, 1230
        glut(ctx, sx + 70, sy + 30, 160, rgb("fff3b0"), .35)
        ctx.save(); ctx.translate(sx, sy); ctx.scale(62, 36); ctx.arc(0, 0, 1, 0, 2 * math.pi); ctx.restore(); ctx.set_source_rgb(*GELB); ctx.fill()
        kreis(ctx, sx + 28, sy - 4, 13, rgb("9de8ff"))
        if i == 5:
            text(ctx, "CHALLENGER DEEP", W / 2, 720, 84, CYAN, .13, alpha=a, maxw=960)
        else:
            text(ctx, "ONLY A FEW DOZEN PEOPLE", W / 2, 690, 62, WEISS, .14, alpha=ease(tl / .5), maxw=980)
            text(ctx, "HAVE BEEN HERE", W / 2, 790, 90, GELB, .13, alpha=ease(tl / .5), maxw=980)


VIDEOS = {
    "sun": dict(
        zeichne=v_sun, titel="How Big Is the Sun? ☀️ 1.3 Million Earths Fit Inside #shorts",
        text="The Sun is so big that 109 Earths fit side by side across it, and about 1.3 million Earths would fit inside. Here is the size of Earth, Jupiter and the Sun, to scale.",
        hashtags="#space #sun #astronomy", tags=["how big is the sun", "size comparison", "sun vs earth", "space facts", "astronomy", "science facts"],
        szenen=[("How big is the Sun, really?", .3), ("This is Earth. It feels huge to us.", .3), ("Jupiter is eleven times wider.", .5),
                ("But the Sun? You could line up one hundred and nine Earths, side by side.", .4), ("And inside, there is room for 1.3 million Earths.", .5),
                ("And the Sun is just an average star. Follow for more.", .6)]),
    "light": dict(
        zeichne=v_light, titel="How Fast Is Light? ⚡ 7.5 Times Around Earth in 1 Second #shorts",
        text="Light travels about 300,000 kilometers every second. That is seven and a half times around the Earth in one second, and still it needs more than eight minutes to reach us from the Sun.",
        hashtags="#speedoflight #physics #space", tags=["speed of light", "how fast is light", "physics facts", "light from the sun", "science facts", "space facts"],
        szenen=[("How fast is light? Faster than you can imagine.", .3), ("Light travels three hundred thousand kilometers, every second.", .4),
                ("In one second, it could circle the Earth seven and a half times.", .4), ("It reaches the Moon in just over one second.", .5),
                ("But even light needs more than eight minutes to get here from the Sun.", .4), ("So the sunlight you see is already eight minutes old. Follow for more.", .6)]),
    "ocean": dict(
        zeichne=v_ocean, titel="How Deep Is the Ocean? 🌊 Deeper Than Mount Everest #shorts",
        text="A dive to the deepest point of the ocean: sunlight fades at 200 meters, the Titanic rests at 3,800 meters, and Challenger Deep lies almost 11,000 meters down. Mount Everest would fit in with room to spare.",
        hashtags="#ocean #deepsea #marianatrench", tags=["how deep is the ocean", "challenger deep", "mariana trench", "deep sea facts", "titanic depth", "science facts"],
        szenen=[("How deep is the ocean? Let's dive.", .3), ("At two hundred meters, sunlight fades away.", .4), ("At one thousand meters, it is completely dark.", .4),
                ("The Titanic rests at three thousand eight hundred meters.", .4), ("Mount Everest would fit in here, with two kilometers of water above its peak.", .4),
                ("The deepest point is Challenger Deep, almost eleven thousand meters down.", .4), ("Only a few dozen people have ever been there. Follow for more.", .6)]),
}


# ---------------- Vorlagen-Videos aus fakten_daten.py ----------------
THEMEN = {  # oben, unten, zweite Farbe, Schild, Hashtags, Tags
    "space": ("070a1c", "1b1f52", "4de1ff", "SPACE", "#space #astronomy #universe", ["space facts", "astronomy", "universe"]),
    "animals": ("0b2418", "14532d", "7cffb2", "ANIMALS", "#animals #wildlife #animalfacts", ["animal facts", "wildlife", "amazing animals"]),
    "body": ("2a0a1c", "5a1233", "ff9fbd", "HUMAN BODY", "#humanbody #biology #anatomy", ["human body facts", "biology", "anatomy"]),
    "earth": ("1c1408", "4a3212", "ffb36b", "PLANET EARTH", "#earth #geography #nature", ["earth facts", "geography", "nature"]),
    "ocean": ("031a33", "0a4a7a", "4de1ff", "OCEAN", "#ocean #sea #nature", ["ocean facts", "sea", "nature"]),
    "tech": ("160a2e", "3a1670", "c9a0ff", "SCIENCE", "#physics #mindblown #learnsomethingnew", ["physics facts", "math facts", "mind blowing facts"]),
}
BALKENFARBEN = [CYAN, PINK, rgb("7cffb2"), rgb("ffb36b"), rgb("c9a0ff")]
_BOKEH = [(random.Random(i * 5).uniform(0, W), random.Random(i * 5 + 1).uniform(0, H), random.Random(i * 5 + 2).uniform(30, 120), random.Random(i * 5 + 3).uniform(12, 40)) for i in range(16)]
KLEIN = {"a", "an", "the", "of", "in", "on", "at", "to", "for", "and", "or", "by", "per"}
FEST = {"km/h": "km/h", "km": "km", "dna": "DNA", "m": "m", "cm": "cm", "mm": "mm", "kg": "kg", "km²": "km²", "t.": "T.", "usa": "USA", "iss": "ISS"}


def titelform(s):
    """'JUPITER IS|THE GIANT' -> 'Jupiter Is the Giant'"""
    w = s.replace("|", " ").split()
    out = []
    for i, x in enumerate(w):
        l = x.lower()
        kern = l.strip("?!:,.")
        if kern in FEST:
            out.append(l.replace(kern, FEST[kern]))
        elif i and kern in KLEIN and not w[i - 1].endswith(":"):
            out.append(l)
        else:
            out.append(l[:1].upper() + l[1:])
    return " ".join(out)


def pille(ctx, s, x, y, size, farbe, alpha=1.0, textfarbe=DUNKEL):
    ctx.select_font_face(SCHRIFT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); ctx.set_font_size(size)
    b = ctx.text_extents(s).x_advance + size * 1.4; h = size * 1.9
    rund(ctx, x - b / 2, y - h / 2, b, h, h / 2); ctx.set_source_rgba(*farbe, alpha); ctx.fill()
    text(ctx, s, x, y, size, textfarbe, alpha=alpha)


def rund(ctx, x, y, b, h, r):
    r = min(r, b / 2, h / 2)
    ctx.new_sub_path(); ctx.arc(x + b - r, y + r, r, -math.pi / 2, 0); ctx.arc(x + b - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi); ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi); ctx.close_path()


def hintergrund(ctx, thema, t):
    oben, unten, zweit = rgb(THEMEN[thema][0]), rgb(THEMEN[thema][1]), rgb(THEMEN[thema][2])
    verlauf(ctx, oben, unten)
    if thema == "space":
        sterne(ctx, t)
    else:
        for x, y, r, v in _BOKEH:
            glut(ctx, x + math.sin(t * .4 + r) * 30, (y - t * v) % (H + 240) - 120, r, zweit, .16)


def hoch(ctx, s, x, y, size, farbe=WEISS, rand=0.0, maxw=None, alpha=1.0):
    """Wie text(), zeichnet aber '10^80' mit hochgestelltem Exponenten."""
    m = re.match(r"^(.*?\d)\^(\d+)(.*)$", s)
    if not m:
        return text(ctx, s, x, y, size, farbe, rand, maxw, alpha)
    ctx.select_font_face(SCHRIFT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    def breite(sz):
        b = []
        for teil, f in zip(m.groups(), (1, .55, 1)):
            ctx.set_font_size(sz * f); b.append(ctx.text_extents(teil).x_advance)
        return b
    b = breite(size)
    if maxw and sum(b) > maxw:
        size *= maxw / sum(b); b = breite(size)
    x0 = x - sum(b) / 2
    text(ctx, m.group(1), x0, y, size, farbe, rand, None, alpha, "links")
    text(ctx, m.group(2), x0 + b[0], y - size * .3, size * .55, farbe, rand / .55 if rand else 0, None, alpha, "links")
    text(ctx, m.group(3), x0 + b[0] + b[1], y, size, farbe, rand, None, alpha, "links")


def wertform(v, k=1.0):
    if isinstance(v, int):
        return zahl(v * k)
    st = len(str(v).split(".")[1])
    return f"{v * k:.{st}f}"


def zaehl(s, k):
    """Zaehlt ganze Zahlen am Anfang hoch ('384,400 KM'), laesst alles andere stehen."""
    m = re.match(r"^(\d[\d,]*)((?:[ +%x].*)?)$", s)
    if not m or k >= 1:
        return s
    n = int(m.group(1).replace(",", ""))
    if n < 10 or ("," not in m.group(1) and 1500 <= n <= 2100 and not m.group(2).strip()):
        return s
    return (zahl(n * k) if "," in m.group(1) else str(int(round(n * k)))) + m.group(2)


def mache_vorlage(art, thema, frage, einheit, items, schluss, opt):
    zweit = rgb(THEMEN[thema][2]); f1, f2 = frage.upper().split("|"); s1, s2 = schluss.split("|")
    n = len(items)
    if art == "b":
        werte = [it[1] for it in items]; vmax = max(werte)
        if opt.get("log"):
            lo = math.log(min(werte)) - .7; anteil = [(math.log(v) - lo) / (math.log(vmax) - lo) for v in werte]
        else:
            anteil = [v / vmax for v in werte]
        sieger = werte.index(vmax)

    def kopf(ctx):
        text(ctx, f"{f1} {f2}", W / 2, 190, 58, GELB, .15, maxw=980)

    def anfang(ctx, tl, t):
        pille(ctx, THEMEN[thema][3], W / 2, 400, 40, zweit, ease(tl / .4))
        k = ease(tl / .35)
        text(ctx, f1, W / 2, 640, 112 * (.9 + .1 * k), WEISS, .12, maxw=980); text(ctx, f2, W / 2, 800, 140 * (.9 + .1 * k), GELB, .12, maxw=980)
        if art == "b":
            for j in range(4):
                b = (300 + 170 * j) * (.75 + .25 * math.sin(t * 2.2 + j * 1.3)) * ease((tl - .15 * j) / .5)
                rund(ctx, 110, 1010 + j * 82, b, 52, 26); ctx.set_source_rgba(*BALKENFARBEN[j], .55); ctx.fill()
        else:
            for j in range(3):
                r = 110 + j * 70 + 12 * math.sin(t * 2 + j)
                ctx.arc(W / 2, 1160, r, 0, 2 * math.pi); ctx.set_source_rgba(*zweit, .5 - j * .14); ctx.set_line_width(10); ctx.stroke()
            text(ctx, "?", W / 2, 1160, 170, GELB, .1)

    def ende(ctx, tl, t):
        a = ease(tl / .5)
        for j in range(3):
            r = 330 + j * 90 + 14 * math.sin(t * 1.6 + j)
            ctx.arc(W / 2, 760, r, 0, 2 * math.pi); ctx.set_source_rgba(*zweit, (.22 - j * .06) * a); ctx.set_line_width(8); ctx.stroke()
        text(ctx, s1, W / 2, 680, 104, WEISS, .12, maxw=960, alpha=a); text(ctx, s2, W / 2, 830, 124, GELB, .12, maxw=960, alpha=a)
        if art == "b":
            lab, v, _ = items[sieger]
            pille(ctx, f"{lab}: {wertform(v)} {einheit}", W / 2, 1050, 40, zweit, ease((tl - .4) / .4))
        pille(ctx, "FOLLOW FOR MORE", W / 2, 1290, 46 * (1 + .04 * math.sin(t * 5)), GELB, ease((tl - .8) / .4))

    def balken(ctx, i, tl, d, t):
        kopf(ctx)
        zh = min(215, 960 / n); y0 = 330 + (960 - zh * n) / 2
        for j in range(min(i, n)):
            akt = j == i - 1
            k = ease(tl / 1.1) if akt else 1
            a = 1 if akt else .78
            lab, v, _ = items[j]; farbe = GELB if j == sieger else BALKENFARBEN[j % 5]
            y = y0 + j * zh
            ws = f"{wertform(v, k)} {einheit}"
            ctx.select_font_face(SCHRIFT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); ctx.set_font_size(56)
            wb = min(ctx.text_extents(f"{wertform(v)} {einheit}").x_advance, 560)
            text(ctx, ws, 1010, y + 30, 56, farbe, .14, maxw=560, alpha=a, anker="rechts")
            text(ctx, lab, 70, y + 30, 50, WEISS, .14, maxw=940 - wb - 40, alpha=a, anker="links")
            rund(ctx, 70, y + 78, 940, 60, 30); ctx.set_source_rgba(1, 1, 1, .08); ctx.fill()
            b = max(60, 940 * anteil[j]) * max(k, .001)
            if akt:
                glut(ctx, 70 + b, y + 108, 90, farbe, .5 * k)
            rund(ctx, 70, y + 78, max(b, 2), 60, 30); ctx.set_source_rgba(*farbe, a); ctx.fill()

    def zahlen(ctx, i, tl, d, t):
        kopf(ctx)
        j = min(i, n) - 1
        for q in range(j):
            gross, lab, _ = items[q]
            hoch(ctx, f"{gross}  ·  {lab}", W / 2, 330 + q * 92, 42, mix(WEISS, zweit, .35), .14, maxw=960, alpha=.8)
        gross, lab, _ = items[j]
        k = ease(tl / .45); kz = ease(tl / 1.0)
        cy = 930
        glut(ctx, W / 2, cy, 520, zweit, .22 * k)
        for q in range(2):
            ctx.arc(W / 2, cy + 40, 400 + q * 60 + 10 * math.sin(t * 2 + q), 0, 2 * math.pi); ctx.set_source_rgba(*zweit, (.16 - q * .07) * k); ctx.set_line_width(6); ctx.stroke()
        hoch(ctx, zaehl(gross, kz), W / 2, cy, 190 * (.8 + .2 * k), GELB, .09, maxw=960, alpha=k)
        text(ctx, lab, W / 2, cy + 175, 60, WEISS, .14, maxw=960, alpha=ease((tl - .25) / .4))
        for q in range(n):
            kreis(ctx, W / 2 + (q - (n - 1) / 2) * 44, 1300, 11 if q == j else 8, GELB if q <= j else WEISS, 1 if q <= j else .3)

    def zeichne(ctx, i, tl, d, t, V):
        hintergrund(ctx, thema, t)
        if i == 0:
            anfang(ctx, tl, t)
        elif i > n:
            ende(ctx, tl, t)
        else:
            (balken if art == "b" else zahlen)(ctx, i, tl, d, t)
    return zeichne


TEASER = ["Watch to the end for the full answer! 👀", "The last one surprised us! 🤯", "Did you know all of them? 🤔", "Can you guess the last one? 👇", "Save it for your next quiz night! 🧠"]


def lade_daten():
    try:
        from fakten_daten import DATEN
    except ImportError:
        return
    for nr, e in enumerate(DATEN):
        key, art, thema, frage, einheit, items, schluss, satz, emoji = e[:9]
        opt = e[9] if len(e) > 9 else {}
        fr = frage.replace("|", " ")
        th = THEMEN[thema]
        VIDEOS[key] = dict(
            zeichne=mache_vorlage(art, thema, frage, einheit, items, schluss, opt),
            titel=f"{titelform(frage)} {emoji} {titelform(schluss)} #shorts",
            text=f"{emoji} {fr} {satz} {TEASER[nr % len(TEASER)]}",
            hashtags=th[4], tags=[fr.lower().rstrip("?"), *th[5], "science facts", "did you know", "facts in 30 seconds"],
            szenen=[(fr, .3)] + [(it[2], .4) for it in items] + [(satz + " Follow for more.", .6)])


lade_daten()


# ---------------- Ton ----------------
_K, _CACHE = None, {}


def stimme(txt):
    global _K
    if txt in _CACHE:
        return _CACHE[txt]
    if _K is None:
        from kokoro_onnx import Kokoro
        _K = Kokoro(os.path.join(MODELLE, "kokoro-v1.0.onnx"), os.path.join(MODELLE, "voices-v1.0.bin"))
    a, sr = _K.create(txt, voice=STIMME, speed=TEMPO, lang="en-us")
    a = np.asarray(a, dtype=np.float64).flatten()
    laut = np.where(np.abs(a) > .015 * np.abs(a).max())[0]
    a = a[max(0, laut[0] - int(.03 * sr)):laut[-1] + int(.1 * sr)]
    a = np.interp(np.linspace(0, len(a) - 1, int(len(a) * SR / sr)), np.arange(len(a)), a)
    _CACHE[txt] = a / np.abs(a).max() * .9
    return _CACHE[txt]


def musik(dauer, seed):
    """Ruhiger Klangteppich mit sanftem Puls."""
    n = int(dauer * SR); t = np.arange(n) / SR; a = np.zeros(n)
    akk = [[110.0, 164.81, 220.0, 261.63], [87.31, 130.81, 174.61, 220.0], [130.81, 196.0, 261.63, 329.63], [98.0, 146.83, 196.0, 246.94]]
    takt = 3.2
    for b in range(int(dauer / takt) + 1):
        s, e = int(b * takt * SR), min(n, int((b + 1) * takt * SR))
        if s >= n:
            break
        tt = t[s:e] - b * takt
        hue = np.minimum(1, tt / .6) * np.minimum(1, (takt - tt) / .6)
        for f in akk[(b + seed) % 4]:
            a[s:e] += .16 * (np.sin(2 * np.pi * f * tt) + .4 * np.sin(2 * np.pi * f * 2.003 * tt)) * hue
    puls = 60 / 100
    for b in range(int(dauer / puls)):
        s = int(b * puls * SR); tt = np.arange(min(int(.25 * SR), n - s)) / SR
        a[s:s + len(tt)] += .5 * np.sin(2 * np.pi * (55 + 40 * np.exp(-30 * tt)) * tt) * np.exp(-14 * tt)
        if b % 2:
            rs = np.random.default_rng(b).standard_normal(len(tt)); a[s:s + len(tt)] += .05 * rs * np.exp(-40 * tt)
    return a / np.abs(a).max()


def wusch(n_ges, start):
    a = np.zeros(n_ges); s = int(start * SR); n = min(int(.5 * SR), n_ges - s)
    if n <= 0:
        return a
    rs = np.random.default_rng(int(start * 100)).standard_normal(n)
    glatt = np.convolve(rs, np.ones(60) / 60, "same")
    tt = np.arange(n) / SR
    a[s:s + n] = glatt * np.sin(np.pi * tt / .5) ** 2 * 3
    return a


class Video:
    def __init__(self, key):
        self.key, self.v = key, VIDEOS[key]

    def vertonen(self, pfad):
        t, self.zeiten, teile = .25, [], []
        for txt, pause in self.v["szenen"]:
            a = stimme(txt); d = len(a) / SR
            self.zeiten.append((t, d, d + pause, txt)); teile.append((t, a)); t += d + pause
        self.dauer = t + .3
        n = int(self.dauer * SR); voc = np.zeros(n)
        for st, a in teile:
            s = int(st * SR); voc[s:s + len(a)] += a[:n - s]
        mix_ = voc + musik(self.dauer, sum(map(ord, self.key)))[:n] * .13
        for st, *_ in self.zeiten[1:]:
            mix_ += wusch(n, st - .2) * .12
        mix_ = mix_ / np.abs(mix_).max() * .92
        mix_[-int(.3 * SR):] *= np.linspace(1, 0, int(.3 * SR))
        with wave.open(pfad, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix_ * 32767).astype(np.int16).tobytes())
        # fuer das Ozean-Video: zurueckgelegter "Sinkweg" als Funktion der Zeit
        tiefe_t = []
        for f in range(int(self.dauer * FPS) + 2):
            tt = f / FPS; i, tl, d = self.szene(tt)
            k = ease(tl / max(d * .55, .8)) if i else 0
            tiefe_t.append(lerp(TIEFEN[max(i - 1, 0)], TIEFEN[min(i, 6)], k) if self.key == "ocean" else 0)
        self.weg = [math.log1p(x) * 420 for x in tiefe_t]

    def szene(self, t):
        for i, (st, d, ges, _) in enumerate(self.zeiten):
            if t < st + ges or i == len(self.zeiten) - 1:
                return i, max(0, t - st), d
        return 0, 0, 1

    def untertitel(self, ctx, i, tl, d):
        worte = self.zeiten[i][3].split()
        gruppen, akt = [], []
        for w_ in worte:
            akt.append(w_)
            if len(akt) >= 4 or re.search(r"[.,?!]$", w_):
                gruppen.append(" ".join(akt)); akt = []
        if akt:
            gruppen.append(" ".join(akt))
        laengen = [len(g) + 2 for g in gruppen]; ges = sum(laengen); pos = 0
        for g, l in zip(gruppen, laengen):
            if tl <= d * (pos + l) / ges or g is gruppen[-1]:
                k = min(1, (tl - d * pos / ges) / .12)
                text(ctx, g.upper().rstrip(".,"), W / 2, 1530, 66 * (.85 + .15 * k), WEISS, .2, maxw=960)
                break
            pos += l

    def zeichne(self, ctx, f):
        t = f / FPS; i, tl, d = self.szene(t)
        self.v["zeichne"](ctx, i, tl, d, t, {"weg": lambda tt: self.weg[min(int(tt * FPS), len(self.weg) - 1)]})
        self.untertitel(ctx, i, tl, d)
        ctx.rectangle(0, 0, W * t / self.dauer, 10); ctx.set_source_rgb(*GELB); ctx.fill()

    def render(self, ordner):
        os.makedirs(ordner, exist_ok=True)
        wav, out = os.path.join(ordner, f"_{self.key}.wav"), os.path.join(ordner, f"fakten_{self.key}.mp4")
        self.vertonen(wav)
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
               "-c:v", "libx264", "-preset", "slow", "-crf", "15", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", out]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
        for f in range(int(self.dauer * FPS)):
            ctx = cairo.Context(surf); self.zeichne(ctx, f); surf.flush(); p.stdin.write(bytes(surf.get_data()))
        p.stdin.close(); p.wait(); os.remove(wav)
        v = self.v
        with open(out.replace(".mp4", ".txt"), "w") as fh:
            fh.write(f"TITEL:\n{v['titel']}\n\nBESCHREIBUNG:\n{v['text']}\n\n⏱️ Big questions, answered in 30 seconds. Follow for more! 🚀\n\n#shorts {v['hashtags']} #sciencefacts #didyouknow #facts #science\n\nTAGS:\n{', '.join(v['tags'])}\n\nSPRECHTEXT:\n" + "\n".join(s[0] for s in v["szenen"]) + "\n")
        return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("video", nargs="?"); ap.add_argument("--alle", action="store_true"); ap.add_argument("--liste", action="store_true")
    ap.add_argument("--ordner", default=os.path.join(HIER, "videos"))
    a = ap.parse_args()
    if a.liste or not (a.video or a.alle):
        for k, v in VIDEOS.items():
            print(f"{k:8s} {v['titel']}")
    else:
        for k in (VIDEOS if a.alle else [a.video]):
            print("Fertig:", Video(k).render(a.ordner))
