"""Weltrekord-Szenen 3-10."""
import math, random
import cairo
from rk_basis import *
import fakten_studio as fs

S2 = {}


def szene(f):
    S2[f.__name__] = f; return f


def studio_hg(ctx, t, f1, f2):
    g = cairo.RadialGradient(W / 2, H * .45, 100, W / 2, H * .5, 1300); g.add_color_stop_rgb(0, *f1); g.add_color_stop_rgb(1, *f2)
    ctx.set_source(g); ctx.paint()


def kreuz_badge(ctx, s, x, y, a):
    badge(ctx, s + "  ✕", x, y, a, f=ROT, tf=WEISS, groesse=40)


# ======================================================================  EUSTACE
@szene
def eustace():
    U = Untertitel("eustace"); D = U.ende() + .25
    t_wo, t_ballon, t_oben, t_kurve, t_los, t_fall, t_flug, t_wolke, t_min, t_schirm, t_frage = 1.9, 4.3, 8.3, 11.2, 12.9, 14.8, 17.3, 18.5, 19.8, 22.1, 23.8
    TOP = 41422.0
    START = (0, 0, 33000, .028)
    cam = Kamera([START, (t_wo, 0, 36000, .04), (t_ballon - .1, 0, 37000, .04), (t_ballon + .3, 0, 2500, .09),
                  (t_oben - .4, 0, 38500, .05), (t_kurve, 0, 26000, .02), (t_los - .2, 0, 39000, .06), (t_los + .8, 0, 39500, .07),
                  (t_schirm + .4, 0, 4500, .07), (t_frage, 0, 6000, .05), (D - .9, *START[1:]), (D, *START[1:])], atmen=.02)

    def balloon_hoehe(t):
        if t_ballon <= t < t_oben - .3:
            return lerp(0, TOP, ease((t - t_ballon - .3) / (t_oben - t_ballon - .9)))
        if t_los <= t < D - .9:
            return TOP + (t - t_los) * 3000
        if t >= D - .9:
            return lerp(TOP + (D - .9 - t_los) * 3000, TOP, ease((t - D + .9) / .7))
        return TOP

    def mann_hoehe(t):
        if t < t_los:
            return balloon_hoehe(t) - 600
        if t < t_fall:
            return TOP - 600 - (t - t_los) * 400
        pts = [(t_fall, TOP - 1000), (t_flug + .3, 11000), (t_wolke + .4, 6000), (t_schirm, 3800), (t_frage, 2500)]
        for (a, ya), (b, yb) in zip(pts, pts[1:]):
            if a <= t <= b:
                return lerp(ya, yb, (t - a) / (b - a))
        if t < D - .9:
            return 2500
        return lerp(2500, TOP - 600, ease((t - D + .9) / .7))

    rng = random.Random(4)
    sterne = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(1, 2.6)) for _ in range(160)]
    wolken = [(rng.uniform(-30000, 30000), rng.uniform(1500, 6500), rng.uniform(900, 2200)) for _ in range(40)]

    def zeichne(ctx, t):
        w = Welt(ctx, cam, t)
        alt = w.cy; k = min(1, max(0, (alt - 6000) / 22000))
        himmel(ctx, mischen(rgb("3d7fd0"), rgb("02040b"), k ** .7), mischen(rgb("bfe0ff"), rgb("10294f"), k), mischen(rgb("78b4ec"), rgb("061226"), k))
        for x, y, r in sterne:
            ctx.arc(x, y, r, 0, 7); farbe(ctx, WEISS, .8 * max(0, k - .3)); ctx.fill()
        w.ein(); c = ctx
        # Erde mit sichtbarer Kruemmung (stilisiert)
        R = 260000.0
        c.arc(0, -R, R, 0, 2 * math.pi); c.set_source(verlauf_v(c, 0, 0, 0, -30000, [(0, rgb("3f7d5c")), (.4, rgb("2a5b80")), (1, rgb("10233a"))])); c.fill()
        # Atmosphaeren-Saum
        g = cairo.RadialGradient(0, -R, R, 0, -R, R + 9000); g.add_color_stop_rgba(0, .55, .8, 1, .55); g.add_color_stop_rgba(1, .55, .8, 1, 0)
        c.arc(0, -R, R + 9000, 0, 2 * math.pi); c.set_source(g); c.fill()
        # Everest
        poly(c, [(-22000, -200), (-11000, 3000), (-9000, 4500), (-6500, 8849), (-4000, 6200), (-1500, 4800), (6000, -200)], rgb("4d5a6e"))
        poly(c, [(-8300, 6600), (-6500, 8849), (-4800, 6900), (-5600, 7200), (-6500, 6600), (-7300, 7100)], rgb("eef3f8"))
        # Wolken
        for x, y, r in wolken:
            wolke(c, x + t * 60, y, r, .85)
        # Hoehenlinien
        for km in (10, 20, 30, 40):
            c.set_dash([w.px(10), w.px(14)]); linie(c, [(-80000, km * 1000), (80000, km * 1000)], w.px(2), WEISS, .25); c.set_dash([])
        w.aus()
        for km in (10, 20, 30, 40):
            bx, by = w.bild(0, km * 1000)
            if -50 < by < H + 50:
                fs.text(ctx, f"{km} km", 40, by - 22, 34, WEISS, .1, alpha=.6, anker="links")
        bx, by = w.bild(0, 11000)
        if -100 < by < H + 100:
            fs.text(ctx, "AIRLINERS ~11 km", W - 40, by - 22, 30, WEISS, .1, alpha=.55, anker="rechts")
        bx, by = w.bild(-6500, 8849)
        if -100 < by < H + 100:
            fs.text(ctx, "EVEREST", bx, by - 40, 34, WEISS, .12, alpha=.8)
        # Flugzeug (Bildschirm-Symbol)
        fa = fenster(t, t_flug - .9, t_wolke + .3, .3, .3)
        if fa:
            px_, py_ = w.bild(0, 11000); px_ = W + 200 - (t - t_flug + .9) * 700
            ctx.save(); ctx.translate(px_, py_); ctx.scale(1.4, 1.4)
            rrect(ctx, -90, -9, 180, 18, 9); farbe(ctx, WEISS, fa); ctx.fill()
            poly(ctx, [(-10, 0), (25, 0), (-25, 55), (-45, 55)], WEISS, fa); poly(ctx, [(60, -3), (90, -3), (95, -35), (80, -35)], WEISS, fa)
            ctx.restore()
        # Ballon
        bh = balloon_hoehe(t); bx, by = w.bild(0, bh)
        if -600 < by < H + 300:
            ctx.save(); ctx.translate(bx, by)
            g = cairo.LinearGradient(-110, 0, 110, 0); g.add_color_stop_rgb(0, .82, .86, .92); g.add_color_stop_rgb(.4, 1, 1, 1); g.add_color_stop_rgb(1, .7, .75, .82)
            ctx.move_to(0, 0); ctx.curve_to(-140, -60, -120, -330, 0, -340); ctx.curve_to(120, -330, 140, -60, 0, 0); ctx.set_source(g); ctx.fill()
            for xx in (-60, 0, 60):
                linie(ctx, [(0, 0), (xx * .9, -200), (xx * .5, -330)], 1.5, rgb("aab4c4"), .7)
            ctx.restore()
            if t < t_los:
                linie(ctx, [(bx, by), (bx, w.bild(0, mann_hoehe(t))[1] - 30)], 2, WEISS, .8)
        # Mann (Symbol)
        mh = mann_hoehe(t); mx, my = w.bild(0, mh)
        ctx.save(); ctx.translate(mx, my)
        if t_schirm <= t < D - .9:
            sk = ease((t - t_schirm) / .4)
            ctx.arc(0, -120, 110 * sk, math.pi, 2 * math.pi); farbe(ctx, ROT); ctx.fill()
            for xx in (-110, 0, 110):
                linie(ctx, [(xx * sk, -120), (0, -20)], 1.5, WEISS, .8)
        ang = 0 if (t < t_fall or t >= t_schirm) else .3 * math.sin(t * 9)
        ctx.rotate(ang)
        ctx.arc(0, -36, 12, 0, 7); farbe(ctx, WEISS); ctx.fill()
        rrect(ctx, -11, -24, 22, 34, 9); farbe(ctx, WEISS); ctx.fill()
        linie(ctx, [(-6, 8), (-9, 34)], 8, WEISS); linie(ctx, [(6, 8), (9, 34)], 8, WEISS)
        ctx.restore()
        # Anzeigen
        za = fenster(t, -1, t_wo + .3, 0, .4) + fenster(t, D - .45, 99, .25, 0)
        zahlkarte(ctx, "41 km", "HIGHEST SKYDIVE EVER", za, pop=1 - ease((t - D + .45) / .3) if t > D - .45 else 0)
        badge(ctx, "ALAN EUSTACE · 2014", W / 2, 300, fenster(t, t_wo + .3, t_ballon - .1), f=WEISS)
        if fenster(t, t_ballon, t_oben):
            minuten = int(lerp(0, 127, ease((t - t_ballon - .3) / (t_oben - t_ballon - .9))))
            badge(ctx, f"BALLOON CLIMB  {minuten // 60}h {minuten % 60:02d}min", W / 2, 300, fenster(t, t_ballon, t_oben - .2), f=WEISS)
        badge(ctx, "BLACK SKY · CURVE OF THE EARTH", W / 2, 300, fenster(t, t_oben, t_los - .2), f=WEISS)
        fa = fenster(t, t_fall, t_frage - .3, .3, .3)
        if fa:
            fs.text(ctx, f"{mann_hoehe(t) / 1000:.1f} km", W / 2, 290, 120, GELB, .1, alpha=fa)
            sek = int(lerp(0, 267, min(1, (t - t_fall) / (t_schirm - t_fall))))
            fs.text(ctx, f"FREE FALL  {sek // 60}:{sek % 60:02d}", W / 2, 390, 44, WEISS, .14, alpha=fa)
        badge(ctx, "FASTER THAN SOUND", W / 2, 490, fenster(t, U.zeit("faster") - .1, t_flug), f=ROT, tf=WEISS)
        badge(ctx, "PARACHUTE OPEN", W / 2, 490, fenster(t, t_schirm, t_frage - .2), f=GELB)
        U.zeichne(ctx, t)
    return D, zeichne, [t_ballon, t_los, t_fall, t_frage, D - .9]


# ======================================================================  BOLT
@szene
def bolt():
    U = Untertitel("bolt"); D = U.ende() + .27
    t_wer, t_berlin, t_speed, t_seit, t_fail, t_17, t_ende = 2.5, 5.9, 8.1, 12.6, 16.7, 18.4, D - .55
    R0, R1 = 2.6, 7.6

    def x_von(tau):
        return 12.25 * (tau - 1.35 * (1 - math.exp(-tau / 1.35)))

    def rennen(t, a, b):
        tau = min(9.58, max(0, (t - a) / (b - a) * 9.58))
        return tau, x_von(tau)

    def bolt_x(t):
        if t < R0:
            return 100.6 + t * .3
        if t < R1:
            return rennen(t, R0, R1)[1]
        if t < t_seit:
            return 100.6 + (t - R1) * .4 if t > t_speed + 3.2 else 100.6
        if t < t_fail + .4:
            return rennen(t, t_seit, t_fail)[1]
        return 100.6 + (t - t_fail) * .2

    START = (0, 100.5, 1.4, 260)
    cam = Kamera([START, (R0 - .1, 98, 1.4, 250), (R0 + .4, 4, 1.6, 150), (R1, 100, 1.6, 150), (t_speed - .1, 100.5, 1.3, 230),
                  (t_seit - .2, 100.5, 1.3, 230), (t_seit + .4, 6, 2.6, 85), (t_fail, 98, 2.6, 85), (t_17 + .3, 99, 2.2, 140), (t_ende, *START[1:]), (D, *START[1:])])
    geister = [(-3.4, .975), (-2.3, .985), (-1.15, .99), (1.15, .982), (2.3, .97)]
    rng = random.Random(9)
    menge = [(rng.uniform(-30, 140), rng.uniform(4, 9), rng.choice([rgb("ff5a4e"), rgb("ffd23f"), rgb("5fd3ff"), WEISS, rgb("7d8bb0")])) for _ in range(500)]

    def zeichne(ctx, t):
        himmel(ctx, rgb("0d1630"), rgb("2b3d6e"), rgb("1a2a50"))
        w = Welt(ctx, cam, t); w.ein(); c = ctx
        # Tribuene + Menge
        c.rectangle(-40, 3.5, 200, 7); farbe(c, rgb("1b2340")); c.fill()
        for x, y, f in menge:
            c.arc(x, y + .1 * math.sin(t * 6 + x), .18, 0, 7); farbe(c, f, .55); c.fill()
        # Flutlicht
        for x in (-10, 40, 90, 140):
            fs_x, fs_y = x, 12
            g = cairo.RadialGradient(fs_x, fs_y, 0, fs_x, fs_y, 9); g.add_color_stop_rgba(0, 1, 1, .9, .5); g.add_color_stop_rgba(1, 1, 1, .9, 0)
            c.arc(fs_x, fs_y, 9, 0, 7); c.set_source(g); c.fill()
        # Bahn
        c.rectangle(-40, -6, 200, 6); farbe(c, rgb("b5462f")); c.fill()
        c.rectangle(-40, 0, 200, .15); farbe(c, rgb("2f7d4a")); c.fill()
        for y in (-1.3, -2.6, -3.9, -5.2):
            linie(c, [(-40, y), (160, y)], w.px(3), WEISS, .6)
        for m in range(0, 101, 10):
            linie(c, [(m, -6), (m, 0)], w.px(4 if m in (0, 100) else 2), WEISS, .9 if m in (0, 100) else .35)
        w.aus()
        for m in range(10, 100, 10):
            bx, by = w.bild(m, -6.2)
            if -100 < bx < W + 100:
                fs.text(ctx, f"{m} m", bx, by + 30, 36, WEISS, .1, alpha=.55)
        bx, by = w.bild(100, 0)
        fs.text(ctx, "FINISH", bx, by + 260 * w.s / 260 * .0 + 40, 34, GELB, .1, alpha=.9)
        w.ein()
        # Geister
        ga = fenster(t, t_seit - .1, t_17, .3, .4)
        if ga:
            for dy, v in geister:
                tau = min(9.58, max(0, (t - t_seit) / (t_fail - t_seit) * 9.58))
                xg = x_von(tau) * v
                mensch(w, xg, 1.9, f=rgb("9fb3d9"), phase=tau * 9 + dy, a=ga * .55)
        # Bolt
        bxw = bolt_x(t); laeuft = (R0 <= t < R1) or (t_seit <= t < t_fail + .3) or (t_speed <= t < t_seit - .3)
        phase = t * 11 if laeuft else None
        schatten(w, bxw, .8)
        mensch(w, bxw, 1.95, f=GELB, f2=rgb("c99a10"), phase=phase)
        if t_speed <= t < t_seit - .3:
            for i in range(9):
                y = .3 + i * .2; xx = bxw - 1 - ((t * 9 + i * .37) % 1) * 4
                linie(c, [(xx, y), (xx - 1.5, y)], w.px(4), WEISS, .45)
        w.aus()
        # Uhr
        if R0 <= t < R1 + 1.0:
            tau = rennen(t, R0, R1)[0]; a = fenster(t, R0 - .2, R1 + 1.0, .2, .3)
            fs.text(ctx, f"{tau:.2f} s", W / 2, 290, 140, GELB, .1, alpha=a)
            fs.text(ctx, "BERLIN · 16 AUGUST 2009", W / 2, 390, 42, WEISS, .14, alpha=fenster(t, t_berlin - .1, R1 + 1.0))
        sa = fenster(t, t_speed, t_seit - .2)
        if sa:
            fs.text(ctx, "≈ 45 km/h", W / 2, 290, 140, GELB, .1, alpha=sa)
            fs.text(ctx, "TOP SPEED", W / 2, 390, 44, WEISS, .14, alpha=sa)
        badge(ctx, "THE FASTEST SPRINTERS TRIED", W / 2, 300, fenster(t, t_seit, t_fail - .1), f=WEISS)
        badge(ctx, "ALL OF THEM FAILED", W / 2, 300, fenster(t, t_fail, t_17 - .1), f=ROT, tf=WEISS)
        ja = fenster(t, t_17, t_ende - .1)
        if ja:
            jahr = int(round(lerp(2009, 2026, ease((t - t_17) / 1.2))))
            fs.text(ctx, str(jahr), W / 2, 290, 140, GELB, .1, alpha=ja)
            fs.text(ctx, "RECORD STILL STANDING", W / 2, 390, 44, WEISS, .14, alpha=ja)
        za = fenster(t, -1, t_wer + .1, 0, .3) + fenster(t, D - .4, 99, .25, 0)
        zahlkarte(ctx, "9.58 s", "100 m WORLD RECORD", za, pop=1 - ease((t - D + .4) / .3) if t > D - .4 else 0)
        badge(ctx, "USAIN BOLT", W / 2, 470, fenster(t, t_wer, R1), f=GELB)
        U.zeichne(ctx, t)
    return D, zeichne, [R0, t_speed, t_seit, t_17, t_ende]


# ======================================================================  BURJ
def burj_form(c, x, h=828.0, f1=rgb("c7d3e6"), f2=rgb("8796b0"), a=1.0, bis=None):
    """gestufter, spitz zulaufender Turm"""
    stufen = [(0, 72), (150, 62), (300, 50), (420, 40), (520, 30), (600, 22), (660, 15), (700, 9), (740, 5), (828, 0.8)]
    bis = bis if bis is not None else h
    for (y0, b0), (y1, b1) in zip(stufen, stufen[1:]):
        if y0 >= bis:
            break
        y1c = min(y1, bis); bb = lerp(b0, b1, (y1c - y0) / (y1 - y0)) if y1 > y0 else b1
        poly(c, [(x - b0 / 2, y0), (x + b0 / 2, y0), (x + bb / 2, y1c), (x - bb / 2, y1c)], f1, a)
        poly(c, [(x, y0), (x + b0 / 2, y0), (x + bb / 2, y1c), (x, y1c)], f2, a * .7)
        for yy in range(int(y0) + 12, int(y1c), 24):
            bk = lerp(b0, b1, (yy - y0) / (y1 - y0))
            linie(c, [(x - bk / 2 + 2, yy), (x + bk / 2 - 2, yy)], .8, rgb("5c6b85"), a * .5)


def eiffel(c, x, a=1.0, f=rgb("9a6b43")):
    h = 330
    poly(c, [(x - 62, 0), (x - 40, 0), (x - 10, 180), (x - 3, 300), (x, 330), (x + 3, 300), (x + 10, 180), (x + 40, 0), (x + 62, 0), (x + 20, 120), (x - 20, 120)], f, a)
    c.arc(x, 0, 30, 0, math.pi); farbe(c, rgb("142038"), a); c.fill()
    for yy in (58, 116):
        linie(c, [(x - 52 + yy * .25, yy), (x + 52 - yy * .25, yy)], 5, f, a)


def empire(c, x, a=1.0, f=rgb("b8a88f")):
    stufen = [(0, 130, 60), (60, 90, 260), (260, 60, 340), (340, 36, 380), (380, 14, 400), (400, 3, 443)]
    for y0, b, y1 in stufen:
        c.rectangle(x - b / 2, y0, b, y1 - y0); farbe(c, f, a); c.fill()


@szene
def burj():
    U = Untertitel("burj"); D = U.ende() + .35
    t_name, t_seit, t_eiffel, t_saudi, t_jeddah, t_bis = 2.3, 4.6, 7.7, 10.8, 14.5, 19.0
    START = (0, 0, 470, 1.62)
    JX = 900
    cam = Kamera([START, (t_name, 0, 470, 1.6), (t_name + .5, 0, 80, 6), (t_seit + 1.2, 0, 720, 3.2), (t_eiffel - .1, 0, 470, 1.6),
                  (t_eiffel + .7, -150, 430, 1.55), (t_saudi - .1, -140, 430, 1.55), (t_saudi + .9, JX, 380, 1.5), (t_jeddah + .6, JX - 300, 560, .95),
                  (t_bis, JX - 350, 560, .92), (D - .8, *START[1:]), (D, *START[1:])])

    def zeichne(ctx, t):
        himmel(ctx, rgb("1d3b6e"), rgb("f0a868"), rgb("5f86b8"))
        fs.glut(ctx, W * .78, H * .62, 420, rgb("ffcf8a"), .35)
        w = Welt(ctx, cam, t); w.ein(); c = ctx
        r = random.Random(2); x = -1500
        while x < 2200:
            b = r.uniform(30, 70); h = r.uniform(40, 260)
            c.rectangle(x, 0, b * .9, h); farbe(c, rgb("2b3a5c"), .9); c.fill(); x += b
        boden(w, rgb("caa877"), rgb("6b5a40"))
        ea = fenster(t, t_eiffel - .1, D - .9, .5, .4)
        if ea:
            c.save(); c.translate(0, -330 * (1 - ease((t - t_eiffel + .1) / .6))); eiffel(c, -230, ea); c.restore()
        # Jeddah
        ja = fenster(t, t_saudi - .2, D - .8, .4, .4)
        if ja:
            gebaut = 470
            poly(c, [(JX - 45, 0), (JX + 45, 0), (JX + 22, gebaut), (JX - 22, gebaut)], rgb("aeb8c8"), ja)
            c.set_dash([6, 6]); linie(c, [(JX - 22, gebaut), (JX - 1, 1008), (JX + 1, 1008), (JX + 22, gebaut)], 3, GELB, ja * fenster(t, t_jeddah - .2, D, .4, .3)); c.set_dash([])
            linie(c, [(JX + 5, gebaut), (JX + 5, gebaut + 60), (JX + 70, gebaut + 60)], 3, GELB, ja)
            linie(c, [(JX + 60, gebaut + 60), (JX + 60, gebaut + 60 - 20 - 10 * math.sin(t * 2))], 1.5, WEISS, ja)
        burj_form(c, 0)
        fs_a = fenster(t, -1, t_name, 0, .3) + fenster(t, D - .9, 99, .4, 0)
        massband(w, 60, 0, 828, text="828 m", a=fs_a)
        massband(w, -300, 0, 330, f=rgb("e0b58a"), text="330 m", seite=-1, a=fenster(t, t_eiffel + .5, t_saudi, .3, .3), groesse=46)
        massband(w, JX - 90, 0, 1008, f=GELB, text="1,000+ m", seite=-1, a=fenster(t, t_jeddah + .2, t_bis + .5, .3, .3), groesse=50)
        w.aus()
        for nm, xw in (("BURJ KHALIFA", 0), ("EIFFEL TOWER", -230), ("JEDDAH TOWER", JX)):
            a = {0: fenster(t, t_name, t_eiffel + 2), -230: fenster(t, t_eiffel + .4, t_saudi), JX: fenster(t, t_saudi + .5, t_bis + .6)}[xw]
            if a:
                bx, by = w.bild(xw, 0)
                badge(ctx, nm, bx, by + 50, a, f=WEISS, groesse=32)
        za = fenster(t, -1, t_name, 0, .3) + fenster(t, D - .45, 99, .25, 0)
        zahlkarte(ctx, "828 m", "TALLEST BUILDING ON EARTH", za, pop=1 - ease((t - D + .45) / .3) if t > D - .45 else 0)
        badge(ctx, "DUBAI · TALLEST SINCE 2010", W / 2, 300, fenster(t, t_seit - .1, t_eiffel - .2), f=WEISS)
        badge(ctx, "MORE THAN 2× THE EIFFEL TOWER", W / 2, 300, fenster(t, t_eiffel + .3, t_saudi - .1), f=GELB)
        badge(ctx, "SAUDI ARABIA · UNDER CONSTRUCTION", W / 2, 300, fenster(t, t_saudi + .3, t_jeddah - .1), f=WEISS)
        badge(ctx, "PLANNED: OVER 1 km · 2028", W / 2, 300, fenster(t, t_jeddah, t_bis), f=GELB)
        U.zeichne(ctx, t)
    return D, zeichne, [t_name + .4, t_eiffel, t_saudi, D - .8]


# ======================================================================  BRIDGE
@szene
def bridge():
    U = Untertitel("bridge"); D = U.ende() + .3
    t_name, t_long, t_zug, t_300, t_halb, t_mara, t_frage = 3.5, 7.0, 9.3, 13.2, 15.8, 18.9, 22.2
    L = 164.8
    # Karte (Einheit km), Bruecke laeuft von unten nach oben
    rng = random.Random(11)
    pfad = [(math.sin(y / 23) * 6 + math.sin(y / 9) * 1.5, y) for y in [i * L / 60 for i in range(61)]]

    def punkt(km):
        i = min(59, int(km / L * 60)); k = km / L * 60 - i
        return lerp(pfad[i][0], pfad[i + 1][0], k), lerp(pfad[i][1], pfad[i + 1][1], k)

    seen = [(rng.uniform(-60, 60), rng.uniform(0, 165), rng.uniform(2, 9)) for _ in range(40)]
    START = (0, 0, L / 2, 1920 * .72 / L)
    cam_k = Kamera([START, (t_name, 0, L / 2, 1920 * .72 / L), (t_name + .8, 0, 20, 24), (t_long - .2, 2, 60, 14), (t_long + .5, 0, L / 2, 1920 * .72 / L),
                    (t_zug, 0, L / 2, 1920 * .72 / L), (t_mara, 0, L / 2, 1920 * .72 / L), (t_mara + .5, 0, L / 2 + 2, 1920 * .66 / L),
                    (t_frage + .3, 0, L / 2 + 2, 1920 * .66 / L), (D - .8, *START[1:]), (D, *START[1:])])
    cam_s = Kamera([(t_zug, 0, 30, 14), (t_300, 60, 34, 9), (t_mara - .3, 300, 40, 7)])

    def karte(ctx, t):
        himmel(ctx, rgb("1c2b22"), rgb("0f1a14"))
        w = Welt(ctx, cam_k, t); w.ein(); c = ctx
        c.rectangle(-200, -50, 400, 300); farbe(c, rgb("2e4a35")); c.fill()
        for x, y, r in seen:
            c.arc(x, y, r, 0, 7); farbe(c, rgb("2a5d7a"), .9); c.fill()
        # Jangtse
        c.move_to(-200, 30)
        for i in range(41):
            x = -200 + i * 10; c.line_to(x, 30 + math.sin(i * .6) * 8 + i * 2.2)
        c.set_line_width(w.px(28)); farbe(c, rgb("2f6f96")); c.stroke()
        # Bruecke
        k = 1.0
        c.move_to(*pfad[0])
        for p in pfad[1:]:
            c.line_to(*p)
        c.set_line_width(w.px(16)); farbe(c, NACHT, .6); c.stroke()
        c.move_to(*pfad[0])
        for p in pfad[1:]:
            c.line_to(*p)
        c.set_line_width(w.px(9)); farbe(c, GELB); c.stroke()
        # Zug-Punkt
        zk = (t * 9) % L; zx, zy = punkt(zk)
        c.arc(zx, zy, w.px(16), 0, 7); farbe(c, WEISS); c.fill()
        # Marathons
        ma = fenster(t, t_mara, t_frage + .2, .3, .3)
        if ma:
            for i in range(4):
                a0, a1 = i * 42.195, min((i + 1) * 42.195, L + 4)
                kk = ease((t - t_mara - i * .45) / .45)
                if kk <= 0:
                    continue
                x0, y0 = punkt(min(a0, L)); x1, y1 = punkt(min(lerp(a0, a1, kk), L)) if lerp(a0, a1, kk) <= L else (punkt(L)[0], lerp(a0, a1, kk))
                linie(c, [(x0 + 9, y0), (x1 + 9, y1)], w.px(14), [CYAN, rgb("ff8ad8"), CYAN, rgb("ff8ad8")][i], ma)
        w.aus()
        for nm, km in (("DANYANG", 0), ("KUNSHAN", L)):
            bx, by = w.bild(*punkt(km))
            badge(ctx, nm, bx, by + (60 if km == 0 else -60), min(1, fenster(t, t_name - .2, t_zug + .1) + fenster(t, t_mara, t_frage + .3)), f=WEISS, groesse=32)
        if ma:
            for i in range(4):
                bx, by = w.bild(*punkt(min(i * 42.195 + 21, L)))
                if t > t_mara + i * .45 + .3:
                    badge(ctx, f"MARATHON {i + 1}", bx + 210, by, ma, f=[CYAN, rgb("ff8ad8"), CYAN, rgb("ff8ad8")][i], groesse=30)

    def seite(ctx, t):
        himmel(ctx, rgb("8fb8e0"), rgb("f3d6a8"), rgb("c4d8e8"))
        w = Welt(ctx, cam_s, t); w.ein(); c = ctx
        zug_x = 20 + (t - t_zug) * 83.3
        # Felder
        c.rectangle(w.cx - 2000, -400, 4000, 400); farbe(c, rgb("6f9a4a")); c.fill()
        for i in range(-40, 120):
            c.rectangle(i * 30, -3, 26, 3); farbe(c, rgb("5f8a3f") if i % 2 else rgb("88b05a")); c.fill()
        # Pfeiler + Fahrbahn
        for i in range(-10, 200):
            px_ = i * 32
            c.rectangle(px_ - 1.5, 0, 3, 28); farbe(c, rgb("c9c3b5")); c.fill()
        c.rectangle(w.cx - 2000, 28, 4000, 3.5); farbe(c, rgb("ddd7ca")); c.fill()
        # Zug
        for i in range(8):
            x0 = zug_x - i * 25.5
            rrect(c, x0 - 25, 31.5, 25, 3.8, 1.2 if i else .5); farbe(c, WEISS); c.fill()
            c.rectangle(x0 - 24, 33.4, 23, .9); farbe(c, rgb("2a3550")); c.fill()
        poly(c, [(zug_x, 31.5), (zug_x + 7, 31.8), (zug_x, 35.3)], WEISS)
        w.aus()
        sa = fenster(t, t_300 - .1, t_mara - .2)
        if sa:
            fs.text(ctx, "300 km/h", W / 2, 290, 130, GELB, .1, alpha=sa)
            minuten = int(lerp(0, 33, ease((t - t_halb) / 1.8))) if t > t_halb else 0
            fs.text(ctx, f"CROSSING TIME  0:{minuten:02d} h" if t > t_halb else "HIGH-SPEED TRAIN", W / 2, 390, 44, WEISS, .14, alpha=sa)
        badge(ctx, "BEIJING – SHANGHAI HIGH-SPEED LINE", W / 2, 300, fenster(t, t_zug + .1, t_300 - .2), f=WEISS, groesse=34)

    def zeichne(ctx, t):
        if t_zug <= t < t_mara - .2:
            seite(ctx, t)
        else:
            karte(ctx, t)
        # Blitz-Uebergang
        for tt in (t_zug, t_mara - .2):
            fa = max(0, 1 - abs(t - tt) / .12)
            if fa:
                ctx.set_source_rgba(1, 1, 1, .6 * fa); ctx.paint()
        za = fenster(t, -1, t_name, 0, .3) + fenster(t, D - .45, 99, .25, 0)
        zahlkarte(ctx, "164.8 km", "LONGEST BRIDGE IN THE WORLD", za, pop=1 - ease((t - D + .45) / .3) if t > D - .45 else 0)
        badge(ctx, "DANYANG–KUNSHAN GRAND BRIDGE · CHINA", W / 2, 300, fenster(t, t_name, t_zug - .1), f=GELB, groesse=32)
        badge(ctx, "≈ 4 MARATHONS", W / 2, 300, fenster(t, t_mara + .2, t_frage), f=CYAN)
        U.zeichne(ctx, t)
    return D, zeichne, [t_name + .5, t_zug, t_mara - .2, D - .8]


# ======================================================================  ROC
def roc_form(c, a=1.0, hl=0.0, t=0):
    f, f2, f3 = rgb("f1f3f7"), rgb("c3cad8"), rgb("8d97aa")
    # Hoehenleitwerk verbindet beide Rumpfe
    rrect(c, -22, -47, 44, 5, 2); farbe(c, f2, a); c.fill()
    for sx in (-15, 15):
        c.move_to(sx - 2.8, -50); c.line_to(sx - 2.8, 16); c.curve_to(sx - 2.8, 21, sx - 1, 23, sx, 23.5)
        c.curve_to(sx + 1, 23, sx + 2.8, 21, sx + 2.8, 16); c.line_to(sx + 2.8, -50); c.close_path(); farbe(c, f, a); c.fill()
        c.rectangle(sx - .4, -50, .8, 66); farbe(c, f2, a * .6); c.fill()
        linie(c, [(sx, -40), (sx, -50)], 1.6, f3, a)
    if True:
        c.move_to(-15, 19.5); c.line_to(-15, 19.5)
        for sx in (15,):
            rrect(c, sx - 1.5, 17.5, 3, 2.2, 1); farbe(c, rgb("2a3550"), a); c.fill()
    poly(c, [(-58.7, 3), (58.7, 3), (57.5, -5), (-57.5, -5)], f, a)
    linie(c, [(-58, -1), (58, -1)], .5, f2, a)
    for sx in (-1, 1):
        for ex in (24, 33, 42):
            rrect(c, sx * ex - 1.3, -2, 2.6, 9, 1.2); farbe(c, mischen(f3, GELB, hl), a); c.fill()
            if hl:
                c.arc(sx * ex, 5, 4 + 1.5 * math.sin(t * 8), 0, 7); farbe(c, GELB, .25 * hl * a); c.fill()


def jumbo(c, x, y, a=1.0):
    f = rgb("dfe4ee")
    rrect(c, x - 3.2, y - 35, 6.4, 70.6, 3.2); farbe(c, f, a); c.fill()
    poly(c, [(x - 2, y + 8), (x - 32.2, y - 12), (x - 32.2, y - 16), (x - 2, y - 4)], f, a)
    poly(c, [(x + 2, y + 8), (x + 32.2, y - 12), (x + 32.2, y - 16), (x + 2, y - 4)], f, a)
    poly(c, [(x - 1, y - 27), (x - 11, y - 34), (x - 11, y - 36), (x - 1, y - 32)], f, a)
    poly(c, [(x + 1, y - 27), (x + 11, y - 34), (x + 11, y - 36), (x + 1, y - 32)], f, a)
    for ex in (-21, -12, 12, 21):
        rrect(c, x + ex - 1.2, y - 4 - abs(ex) * .6, 2.4, 6, 1); farbe(c, rgb("9aa4b6"), a); c.fill()


@szene
def roc():
    U = Untertitel("roc"); D = U.ende() + .3
    t_name, t_fluegel, t_feld, t_koerper, t_jumbo, t_frage = 2.5, 5.2, 8.5, 11.4, 15.8, 19.0
    START = (0, 0, -8, 8.1)
    cam = Kamera([START, (t_name, -50, -2, 16), (t_fluegel + .6, 50, -2, 16), (t_feld - .1, 0, -8, 8.1), (t_feld + .5, 0, -6, 7.4),
                  (t_koerper - .1, 0, -6, 7.4), (t_koerper + .6, 0, -12, 14), (t_jumbo - .2, 0, -12, 14), (t_jumbo + .6, 0, -55, 6.4),
                  (t_frage, 0, -50, 6.4), (D - .8, *START[1:]), (D, *START[1:])], atmen=.015)

    def zeichne(ctx, t):
        himmel(ctx, rgb("3c4250"), rgb("2a2f3a"))
        w = Welt(ctx, cam, t); w.ein(); c = ctx
        c.rectangle(-300, -300, 600, 600); farbe(c, rgb("4b505c")); c.fill()
        for i in range(-12, 13):
            c.rectangle(-2, i * 24, 4, 12); farbe(c, WEISS, .25); c.fill()
        fa = fenster(t, t_feld, t_koerper + .2, .4, .4)
        if fa:
            c.rectangle(-52.5, -40, 105, 68); farbe(c, rgb("3f8f4f"), fa * .9); c.fill()
            for i in range(0, 10):
                c.rectangle(-52.5 + i * 10.5, -40, 5.25, 68); farbe(c, rgb("4aa05b"), fa * .6); c.fill()
            c.set_line_width(.6); c.rectangle(-52.5, -40, 105, 68); farbe(c, WEISS, fa); c.stroke()
            linie(c, [(0, -40), (0, 28)], .6, WEISS, fa); c.arc(0, -6, 9.15, 0, 7); c.set_line_width(.6); c.stroke()
        # Schatten des Flugzeugs
        c.save(); c.translate(4, -4); roc_form(c, .25); c.restore()
        c.save(); c.set_operator(cairo.OPERATOR_OVER)
        roc_form(c, 1, hl=fenster(t, t_koerper + .4, t_jumbo - .2), t=t); c.restore()
        ja = fenster(t, t_jumbo - .2, t_frage + .4, .5, .4)
        if ja:
            jumbo(c, 0, -110 + 30 * (1 - ease((t - t_jumbo + .2) / .7)), ja)
        mk = fenster(t, -1, t_name + .1, 0, .3) + fenster(t, t_fluegel - .2, t_feld + .2, .3, .3) + fenster(t, D - .9, 99, .4, 0)
        massband_h(w, -58.7, 58.7, 14, text="117 m", a=min(1, mk), text_y=-60)
        if fa:
            massband_h(w, -52.5, 52.5, -48, f=rgb("8fe0a0"), text="FOOTBALL FIELD ≈ 105 m", a=fenster(t, t_feld + .3, t_koerper), text_y=60, groesse=40)
        if ja:
            massband_h(w, -32.2, 32.2, -154, f=CYAN, text="BOEING 747", a=ja, text_y=60, groesse=40)
        w.aus()
        za = fenster(t, -1, t_name, 0, .3) + fenster(t, D - .45, 99, .25, 0)
        zahlkarte(ctx, "117 m", "WIDEST WINGS EVER FLOWN", za, pop=1 - ease((t - D + .45) / .3) if t > D - .45 else 0)
        badge(ctx, "STRATOLAUNCH ROC", W / 2, 300, fenster(t, t_name, t_feld - .1), f=GELB)
        badge(ctx, "2 BODIES · 6 ENGINES FROM 747s", W / 2, 300, fenster(t, t_koerper + .2, t_jumbo - .1), f=WEISS)
        U.zeichne(ctx, t)
    return D, zeichne, [t_name, t_feld, t_koerper, t_jumbo, D - .8]


# ======================================================================  ZEUS
def dogge(w, x, S=1.118, steh=0.0, f=rgb("3d4250"), f2=rgb("2a2e38"), t=0):
    """Deutsche Dogge, Seitenansicht (Schulter bei x+.28, Hoehe S). steh 0..1 = auf Hinterbeinen"""
    c = w.ctx
    hx, hy = x - .36, .62 + .12 * steh
    # Hinterbeine (bleiben am Boden)
    for dx, ff in ((-.02, f2), (.08, f)):
        c.move_to(hx + dx - .1, hy + .05); c.curve_to(hx + dx - .18, hy - .2, hx + dx - .02, .35, hx + dx - .05, .2)
        c.line_to(hx + dx, .04); c.line_to(hx + dx + .07, .04); c.line_to(hx + dx + .06, .22)
        c.curve_to(hx + dx + .05, .4, hx + dx + .14, hy - .15, hx + dx + .12, hy + .05); c.close_path(); farbe(c, ff); c.fill()
        rrect(c, hx + dx - .02, 0, .14, .06, .03); farbe(c, ff); c.fill()
    c.save(); c.translate(hx, hy); c.rotate(steh * math.radians(64)); c.translate(-hx, -hy)
    # Rumpf: Brust tief, Bauch hochgezogen
    c.move_to(x - .48, .98); c.curve_to(x - .3, 1.1, x + .1, 1.1, x + .3, 1.118)
    c.curve_to(x + .48, 1.1, x + .5, .78, x + .36, .6); c.curve_to(x + .2, .55, x + .05, .62, x - .1, .7)
    c.curve_to(x - .3, .72, x - .5, .62, x - .52, .8); c.close_path(); farbe(c, f); c.fill()
    # Vorderbeine
    for dx, ff in ((.0, f2), (.1, f)):
        rrect(c, x + .2 + dx, .05, .085, .7, .04); farbe(c, ff); c.fill()
        rrect(c, x + .18 + dx, 0, .14, .07, .03); farbe(c, ff); c.fill()
    # Hals
    c.move_to(x + .22, 1.05); c.line_to(x + .44, 1.42); c.line_to(x + .6, 1.36); c.line_to(x + .46, .95); c.close_path(); farbe(c, f); c.fill()
    # Kopf
    rrect(c, x + .44, 1.3, .24, .24, .08); farbe(c, f); c.fill()
    rrect(c, x + .6, 1.3, .26, .14, .05); farbe(c, f); c.fill()
    poly(c, [(x + .47, 1.5), (x + .5, 1.66), (x + .58, 1.52)], f2)
    c.arc(x + .64, 1.46, .022, 0, 7); farbe(c, WEISS, .9); c.fill()
    c.arc(x + .85, 1.41, .025, 0, 7); farbe(c, (0, 0, 0)); c.fill()
    # Schwanz
    linie(c, [(x - .5, .95), (x - .62, .75 + .04 * math.sin(t * 6)), (x - .6, .5)], .045, f)
    c.restore()


@szene
def zeus():
    U = Untertitel("zeus"); D = U.ende() + .3
    t_name, t_ever, t_schulter, t_auf, t_zwei, t_adult, t_sanft, t_mess = 1.8, 4.9, 7.4, 9.3, 11.0, 13.3, 15.0, 19.4
    START = (0, .25, .95, 540)

    def steh(t):
        return ease((t - t_auf) / 1.0) * (1 - ease((t - t_sanft) / .8))

    cam = Kamera([START, (t_name, .3, 1.0, 520), (t_schulter, .1, .85, 640), (t_auf - .1, .1, .85, 600), (t_auf + 1.0, .3, 1.25, 420),
                  (t_sanft, .3, 1.2, 430), (t_sanft + .9, .3, .95, 520), (t_mess, .2, .9, 600), (D - .8, *START[1:]), (D, *START[1:])])
    rng = random.Random(3)
    herzen = [(rng.uniform(-.4, .9), rng.uniform(0, 1), rng.uniform(.6, 1.2)) for _ in range(14)]

    def zeichne(ctx, t):
        studio_hg(ctx, t, rgb("2a3d5a"), rgb("0b1220"))
        w = Welt(ctx, cam, t); w.ein(); c = ctx
        boden(w, rgb("4a5a72"), rgb("151c29"))
        schatten(w, -.05, 1.3); schatten(w, 1.15, .6)
        st = steh(t)
        mensch(w, 1.15, 1.75, f=rgb("b8c3dc"))
        dogge(w, 0, steh=st, t=t)
        ha = fenster(t, t_sanft, t_mess, .4, .4)
        if ha:
            for x, y0, v in herzen:
                y = .8 + ((t - t_sanft) * .4 * v + y0) % 1.4
                c.save(); c.translate(x, y); c.scale(.06, .06)
                c.move_to(0, -.4); c.curve_to(0, .2, 1.2, .3, 1, 1); c.curve_to(.8, 1.6, 0, 1.3, 0, .9); c.curve_to(0, 1.3, -.8, 1.6, -1, 1); c.curve_to(-1.2, .3, 0, .2, 0, -.4)
                farbe(c, ROT, ha * .8); c.fill(); c.restore()
        sa = fenster(t, -1, t_auf, 0, .3) + fenster(t, t_sanft + .8, 99, .4, 0)
        massband(w, .75, 0, 1.118, text="1.12 m", a=min(1, sa), groesse=50) if False else massband(w, .78, 0, 1.118, text="1.12 m" if t < t_sanft else ("1.12 m"), a=min(1, sa) * (1 - fenster(t, t_auf - .2, t_sanft + .6, .2, .3)), groesse=50)
        aa = fenster(t, t_zwei - .2, t_sanft, .3, .3)
        if aa:
            massband(w, -.85, 0, 2.2, text="2+ m", seite=-1, a=aa, k=ease((t - t_zwei + .2) / .5))
            c.set_dash([w.px(12), w.px(8)]); linie(c, [(-1, 1.75), (1.8, 1.75)], w.px(3), WEISS, aa * fenster(t, t_adult - .2, t_sanft)); c.set_dash([])
        w.aus()
        za = fenster(t, -1, t_name, 0, .3) + fenster(t, D - .45, 99, .25, 0)
        zahlkarte(ctx, "1.12 m", "TALLEST DOG EVER", za, pop=1 - ease((t - D + .45) / .3) if t > D - .45 else 0)
        badge(ctx, "ZEUS · GREAT DANE · MICHIGAN", W / 2, 300, fenster(t, t_name, t_schulter - .1), f=WEISS)
        badge(ctx, "SHOULDER HEIGHT", W / 2, 300, fenster(t, t_schulter, t_auf), f=GELB)
        badge(ctx, "ON HIS BACK LEGS: OVER 2 m", W / 2, 300, fenster(t, t_zwei - .2, t_sanft - .1), f=GELB)
        badge(ctx, "GENTLE GIANT · THERAPY DOG", W / 2, 300, fenster(t, t_sanft, t_mess), f=WEISS)
        U.zeichne(ctx, t)
    return D, zeichne, [t_name, t_auf, t_sanft, D - .8]


# ======================================================================  LIMO (Draufsicht, faehrt nach oben)
def limo_oben(w, x, y0, t, merk=(0, 0, 0)):
    c = w.ctx; L, B = 30.54, 2.3
    rrect(c, x - B / 2, y0, B, L, .8); farbe(c, rgb("f4f4f2")); c.fill()
    for e in (y0 + .6, y0 + L - 2.0):
        rrect(c, x - B / 2 + .2, e, B - .4, 1.4, .4); farbe(c, rgb("2a3550")); c.fill()
    for i in range(13):
        yy = y0 + 1.2 + i * (L - 2.4) / 12
        for sx in (-1, 1):
            c.rectangle(x + sx * (B / 2) - (.18 if sx > 0 else -.0), yy - .35, .18, .7); farbe(c, rgb("181818")); c.fill()
    # Fenster-Streifen
    for i in range(10):
        c.rectangle(x - B / 2 + .15, y0 + 3 + i * 2.6, .25, 1.8); farbe(c, rgb("3a4664"), .8); c.fill()
        c.rectangle(x + B / 2 - .4, y0 + 3 + i * 2.6, .25, 1.8); farbe(c, rgb("3a4664"), .8); c.fill()
    pa, ga, ha = merk
    if pa:
        rrect(c, x - .8, y0 + 11, 1.6, 4.2, .3); farbe(c, rgb("2fa8e0"), pa); c.fill()
        for i in range(4):
            yy = y0 + 11.6 + i * .9 + .2 * math.sin(t * 3 + i)
            linie(c, [(x - .6, yy), (x + .6, yy + .1)], w.px(3), WEISS, .5 * pa)
        c.rectangle(x - .15, y0 + 15.2, .3, 1.2); farbe(c, rgb("c79a5a"), pa); c.fill()
    if ga:
        rrect(c, x - .9, y0 + 17.5, 1.8, 3.2, .4); farbe(c, rgb("4caf50"), ga); c.fill()
        c.arc(x + .3, y0 + 20, .12, 0, 7); farbe(c, NACHT, ga); c.fill()
        linie(c, [(x + .3, y0 + 20), (x + .3, y0 + 20.9)], w.px(3), WEISS, ga)
        poly(c, [(x + .3, y0 + 20.9), (x + .8, y0 + 20.7), (x + .3, y0 + 20.5)], ROT, ga)
    if ha:
        c.arc(x, y0 + 24.5, 1.05, 0, 7); farbe(c, rgb("3c4048"), ha); c.fill()
        c.arc(x, y0 + 24.5, .95, 0, 7); c.set_line_width(w.px(3)); farbe(c, GELB, ha); c.stroke()
        for xx in (-.35, .35):
            linie(c, [(x + xx, y0 + 24.0), (x + xx, y0 + 25.0)], .14, WEISS, ha, cairo.LINE_CAP_BUTT)
        linie(c, [(x - .35, y0 + 24.5), (x + .35, y0 + 24.5)], .14, WEISS, ha, cairo.LINE_CAP_BUTT)


def auto_oben(c, x, y0, f):
    rrect(c, x - .9, y0 + .1, 1.8, 4.3, .5); farbe(c, f); c.fill()
    rrect(c, x - .75, y0 + 1.2, 1.5, 2.0, .3); farbe(c, mischen(f, (0, 0, 0), .35)); c.fill()


@szene
def limo():
    U = Untertitel("limo"); D = U.ende() + .45
    t_name, t_rad, t_pool, t_golf, t_heli, t_autos, t_beide, t_mess = 2.0, 6.1, 8.7, 11.8, 13.0, 14.6, 17.6, 19.4
    START = (0, 1.2, 15.6, 41)
    cam = Kamera([START, (t_name, 1.2, 15.6, 40), (t_rad - .1, 1.2, 15.6, 40), (t_rad + .5, 0, 5, 120), (t_pool - .2, 0, 8, 110),
                  (t_pool + .6, 0, 14, 110), (t_golf + .4, 0, 19, 110), (t_heli + .4, 0, 24, 110), (t_autos - .1, 0, 22, 100),
                  (t_autos + .7, 2.6, 15.3, 39), (t_beide + .3, 2.6, 15.3, 39), (t_mess, 1.2, 15.6, 41), (D - .5, *START[1:]), (D, *START[1:])])
    farben = [rgb("e25c4b"), rgb("4b8ee2"), rgb("e2c14b"), rgb("5bbf7a"), rgb("9b6be0"), rgb("e28e4b")]

    def zeichne(ctx, t):
        himmel(ctx, rgb("33363d"), rgb("26282e"))
        w = Welt(ctx, cam, t); w.ein(); c = ctx
        c.rectangle(-8, -200, 16, 400); farbe(c, rgb("3d4048")); c.fill()
        for x in (-2.0, 4.6):
            linie(c, [(x, -200), (x, 200)], w.px(4), WEISS, .7)
        off = (t * 6) % 6
        for i in range(-30, 40):
            c.rectangle(1.3 - .08, i * 6 - off, .16, 3); farbe(c, WEISS, .6); c.fill()
        # Baeume am Rand
        for i in range(-20, 30):
            yy = i * 5 - off * .99
            for x in (-4.5, 7.5):
                c.arc(x + (i % 3) * .3, yy, 1.4, 0, 7); farbe(c, rgb("2f5a3a")); c.fill()
                c.arc(x + (i % 3) * .3 - .3, yy + .3, .9, 0, 7); farbe(c, rgb("3e7049")); c.fill()
        merk = (fenster(t, t_pool, 99, .4, 0), fenster(t, t_golf, 99, .4, 0), fenster(t, t_heli, 99, .4, 0))
        if t > D - .5:
            merk = (1, 1, 1)
        if t < t_pool:
            merk = (1, 1, 1) if t < t_name + .3 else (0, 0, 0)
        aa = fenster(t, t_autos - .2, t_mess + .3, .4, .4)
        if aa:
            c.save(); c.translate(0, -6 * (1 - ease((t - t_autos + .2) / .7)))
            for i in range(6):
                auto_oben(c, 2.6, i * 4.5, farben[i])
            c.restore()
            massband(w, 4.1, 0, 27, f=CYAN, text="6 CARS ≈ 27 m", a=aa, groesse=40)
        limo_oben(w, 0, 0, t, merk)
        ba = fenster(t, t_beide, t_mess, .3, .3)
        if ba:
            for y, d in ((-.4, -1), (30.94, 1)):
                poly(c, [(-.6, y), (.6, y), (0, y + d * 1.2)], GELB, ba)
        ra = fenster(t, t_rad, t_pool - .1, .3, .3)
        if ra:
            for i in range(13):
                yy = 1.2 + i * (30.54 - 2.4) / 12
                for sx in (-1, 1):
                    c.arc(sx * 1.25, yy, .45, 0, 7); c.set_line_width(w.px(4)); farbe(c, GELB, ra); c.stroke()
        ma = fenster(t, -1, t_name, 0, .3) + fenster(t, t_mess - .2, 99, .4, 0)
        massband(w, -1.8, 0, 30.54, text="30.5 m", seite=-1, a=min(1, ma), groesse=50)
        w.aus()
        za = fenster(t, -1, t_name, 0, .3) + fenster(t, D - .45, 99, .25, 0)
        zahlkarte(ctx, "30.5 m", "LONGEST CAR IN THE WORLD", za, y=230, pop=1 - ease((t - D + .45) / .3) if t > D - .45 else 0)
        badge(ctx, "THE AMERICAN DREAM", W / 2, 230, fenster(t, t_name, t_rad - .1), f=GELB)
        badge(ctx, "26 WHEELS", W / 2, 230, fenster(t, t_rad, t_pool - .1), f=GELB)
        badge(ctx, "SWIMMING POOL + DIVING BOARD", W / 2, 230, fenster(t, t_pool, t_golf - .1), f=CYAN)
        badge(ctx, "MINI GOLF", W / 2, 230, fenster(t, t_golf, t_heli - .1), f=rgb("8fe0a0"))
        badge(ctx, "HELIPAD", W / 2, 230, fenster(t, t_heli, t_autos - .1), f=GELB)
        badge(ctx, "DRIVES FROM BOTH ENDS", W / 2, 230, fenster(t, t_beide, t_mess), f=WEISS)
        U.zeichne(ctx, t)
    return D, zeichne, [t_rad, t_autos, D - .5]


# ======================================================================  SEAWISE
def schiff(c, x, y, L=458.45, a=1.0, t=0):
    """Seitenansicht, Heck bei x, Wasserlinie bei y"""
    poly(c, [(x, y - 24.6), (x + L - 30, y - 24.6), (x + L, y + 8), (x + L, y + 12), (x - 2, y + 12), (x - 6, y - 4)], rgb("3a4152"), a)
    c.rectangle(x - 2, y + 10.5, L, 1.5); farbe(c, rgb("d8dbe2"), a); c.fill()
    poly(c, [(x, y - 24.6), (x + L - 30, y - 24.6), (x + L - 6, y - 2), (x - 6, y - 4)], rgb("8a2b25"), a)
    c.rectangle(x + 6, y + 12, 44, 30); farbe(c, rgb("f2f2ee"), a); c.fill()
    c.rectangle(x + 10, y + 42, 36, 14); farbe(c, rgb("f2f2ee"), a); c.fill()
    for i in range(4):
        c.rectangle(x + 11 + i * 9, y + 46, 6, 4); farbe(c, rgb("2a3550"), a); c.fill()
    c.rectangle(x + 22, y + 56, 10, 16); farbe(c, rgb("c43b2f"), a); c.fill()
    for i in range(16):
        c.rectangle(x + 70 + i * 23, y + 12, 14, 2.5); farbe(c, rgb("4a4f5c"), a); c.fill()


@szene
def seawise():
    U = Untertitel("seawise"); D = U.ende() + .4
    t_name, t_stell, t_kanal, t_india, t_mess = 2.3, 6.6, 10.9, 17.4, 20.3

    def winkel(t):
        if t < t_name:
            return 90
        if t < t_name + 1.0:
            return lerp(90, 0, ease((t - t_name) / 1.0))
        if t < t_stell:
            return 0
        if t < t_stell + 1.0:
            return lerp(0, 90, ease((t - t_stell) / 1.0))
        if t < t_kanal:
            return 90
        if t < t_kanal + 1.0:
            return lerp(90, 0, ease((t - t_kanal) / 1.0))
        if t < t_mess + .3:
            return 0
        return lerp(0, 90, ease((t - t_mess - .3) / 1.2))

    START = (0, 20, 250, 2.75)
    cam = Kamera([START, (t_name, 60, 250, 2.75), (t_name + 1.0, 60, 28, 6.5), (t_stell - .2, 380, 18, 5.5), (t_stell + 1.0, 0, 250, 2.75),
                  (t_kanal - .1, 0, 250, 2.75), (t_kanal + 1.0, 400, 15, 6.0), (t_india, 260, 20, 4.0), (t_mess + .3, 230, 40, 2.6),
                  (D - .2, *START[1:]), (D, *START[1:])])

    def zeichne(ctx, t):
        himmel(ctx, rgb("27406a"), rgb("e9b98a"), rgb("6f8fbf"))
        fs.glut(ctx, W * .2, H * .58, 380, rgb("ffd9a0"), .3)
        w = Welt(ctx, cam, t); w.ein(); c = ctx
        ea = fenster(t, t_stell, t_kanal + .3, .4, .4) + fenster(t, -1, t_name + .4, 0, .3) + fenster(t, t_mess + .3, 99, .4, 0)
        ea = min(1, ea)
        if ea:
            empire(c, -120, ea)
        c.save(); c.translate(0, 0); c.rotate(math.radians(winkel(t)))
        schiff(c, 0, 0, t=t)
        c.restore()
        # Meer
        c.rectangle(w.cx - 3000, -300, 6000, 300); c.set_source(verlauf_v(c, 0, 0, 0, -120, [(0, rgb("1f5a86")), (1, rgb("0b2440"))])); c.fill()
        for i in range(-60, 120):
            xx = i * 18 + (t * 9) % 18
            linie(c, [(xx, .6 * math.sin(t * 2 + i)), (xx + 9, .6 * math.sin(t * 2 + i + 1))], w.px(3), WEISS, .35)
        if ea:
            massband(w, -175, 0, 443, f=rgb("e0c9a0"), text="443 m", seite=-1, a=ea, groesse=44)
        sa = min(1, fenster(t, -1, t_name, 0, .3) + fenster(t, t_stell + .9, t_kanal, .3, .3) + fenster(t, t_mess + 1.4, 99, .3, 0))
        if sa:
            massband(w, 40, 0, 458.45, text="458 m", a=sa)
        w.aus()
        bx, by = w.bild(-120, 0)
        if ea:
            badge(ctx, "EMPIRE STATE", max(bx, 170), by + 60, ea, f=WEISS, groesse=30)
        za = fenster(t, -1, t_name, 0, .3) + fenster(t, D - .45, 99, .25, 0)
        zahlkarte(ctx, "458 m", "LONGEST SHIP EVER BUILT", za, pop=1 - ease((t - D + .45) / .3) if t > D - .45 else 0)
        badge(ctx, "SEAWISE GIANT · OIL TANKER", W / 2, 300, fenster(t, t_name, t_stell - .1), f=WEISS)
        badge(ctx, "TALLER THAN THE EMPIRE STATE", W / 2, 300, fenster(t, t_stell + .5, t_kanal - .1), f=GELB)
        for i, (nm, tt) in enumerate((("SUEZ CANAL", U.zeit("Suez")), ("PANAMA CANAL", U.zeit("Panama")), ("ENGLISH CHANNEL", U.zeit("English")))):
            kreuz_badge(ctx, nm, W / 2, 280 + i * 100, fenster(t, tt - .1, t_india - .1))
        badge(ctx, "TAKEN APART · INDIA · 2010", W / 2, 300, fenster(t, t_india, t_mess), f=WEISS)
        U.zeichne(ctx, t)
    return D, zeichne, [t_name, t_stell, t_kanal, t_mess + .3]
