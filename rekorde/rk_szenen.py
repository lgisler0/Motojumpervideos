"""Die 10 Weltrekord-Szenen. Aufruf: python3 rk_szenen.py <key> [--test t1,t2,...]"""
import sys, math, random
import cairo
from rk_basis import *
import fakten_studio as fs

SZENEN = {}


def szene(f):
    SZENEN[f.__name__] = f; return f


def tag_himmel(ctx, k=0.0):
    himmel(ctx, mischen(rgb("2c5fa8"), rgb("0f1d3a"), k), mischen(rgb("f2b77a"), rgb("2a3f6b"), k), mischen(rgb("6fa3d8"), rgb("1d2f55"), k))


def studio_hg(ctx, t, f1=rgb("1a2a4a"), f2=rgb("070b16")):
    g = cairo.RadialGradient(W / 2, H * .45, 100, W / 2, H * .5, 1300); g.add_color_stop_rgb(0, *f1); g.add_color_stop_rgb(1, *f2)
    ctx.set_source(g); ctx.paint()
    # leichte Lichtflecken
    for i in range(7):
        x = (i * 173 + t * 14 * (1 + i % 3)) % (W + 300) - 150; y = 300 + (i * 397) % 1300
        fs.glut(ctx, x, y, 160 + 40 * (i % 3), rgb("5fd3ff") if i % 2 else rgb("ffd23f"), .05)


def stadtsilhouette(w, x0, x1, hmax, f, seed=3, a=1.0):
    r = random.Random(seed); x = x0; c = w.ctx
    while x < x1:
        b = r.uniform(.04, .1) * hmax; h = r.uniform(.25, 1) * hmax
        c.rectangle(x, 0, b * .92, h); farbe(c, f, a); c.fill(); x += b


# ======================================================================
@szene
def wadlow():
    U = Untertitel("wadlow"); D = U.ende() + .2
    t_zwei, t_tall, t_born, t_grow, t_17, t_245, t_22, t_80, t_end = 2.4, 5.4, 8.1, 11.6, 14.0, 15.7, 17.9, 20.3, D - .7
    START = (0, 0.0, 1.45, 300)
    cam = Kamera([START, (t_zwei, .1, 1.6, 350), (t_tall - .2, .2, 1.55, 340), (t_tall + .6, 1.1, 1.35, 300), (t_born - .1, 1.0, 1.3, 300),
                  (t_born + .5, .4, .55, 700), (t_grow, .4, .6, 650), (t_245, .1, 1.45, 340), (t_22 + 1, .05, 1.6, 320),
                  (t_80 + .4, .6, 1.4, 230), (t_end - .9, .6, 1.4, 230), (t_end, *START[1:]), (D, *START[1:])])
    leute = [(1.62, 3.2), (1.78, 4.1), (1.70, 5.0), (1.95, 5.9), (1.66, 6.8), (1.83, 7.7), (2.05, 8.6)]

    def hoehe(t):
        if t < t_born - .1 or t >= t_end:
            return 2.72
        if t < t_born + .45:
            return lerp(2.72, .52, ease((t - t_born + .1) / .55))
        if t < t_grow:
            return .52
        if t < t_245 + .7:
            return lerp(.52, 2.45, ease((t - t_grow) / (t_245 + .7 - t_grow)))
        if t < t_22:
            return 2.45
        return lerp(2.45, 2.72, ease((t - t_22) / 1.0))

    def alter(t):
        h = hoehe(t)
        if t < t_grow:
            return 0
        if h <= 2.45:
            return int(round(lerp(1, 17, (h - .52) / (2.45 - .52))))
        return int(round(lerp(17, 22, (h - 2.45) / .27)))

    def zeichne(ctx, t):
        tag_himmel(ctx, .55)
        w = Welt(ctx, cam, t); w.ein(); c = ctx
        # Hintergrund-Haeuser
        stadtsilhouette(w, -8, 12, 7, rgb("24365e"), a=.7)
        boden(w, rgb("3b4a6b"), rgb("141b2e"))
        h = hoehe(t)
        # Tuer zum Vergleich
        ta = fenster(t, t_tall - .1, t_born, .4, .3)
        if ta:
            c.rectangle(1.55, 0, .9, 2.03); farbe(c, rgb("7a5536"), ta); c.fill()
            c.rectangle(1.62, 0, .76, 1.96); farbe(c, rgb("4a3322"), ta); c.fill()
            c.arc(2.28, 1.0, .035, 0, 7); farbe(c, GELB, ta); c.fill()
        # Leute laufen durch (am Ende)
        la = fenster(t, t_80, t_end - .3, .5, .5)
        if la:
            for hh, x in leute:
                xx = x - (t - t_80) * 1.3
                schatten(w, xx, .5, .2 * la); mensch(w, xx, hh, f=rgb("9aa6c2"), phase=(t * 7 + x * 3), a=la)
            c.set_dash([w.px(18), w.px(12)]); linie(c, [(-4, 2.72), (10, 2.72)], w.px(5), GELB, la); c.set_dash([])
        schatten(w, -.9, .7); schatten(w, .6, .7 * h / 2.72 + .2)
        mensch(w, -.9, 1.75, f=rgb("b8c3dc"))
        mensch(w, .6, h, f=rgb("f2f4f8"), kind=h < .9, haare=rgb("3a2a20"))
        # Massband am Riesen
        ma = 1 - fenster(t, t_born - .2, t_end - .2, .2, .3) if True else 1
        if ma > 0:
            massband(w, 1.05, 0, 2.72, text="2.72 m", a=ma, k=1)
        else:
            pass
        mb = fenster(t, t_grow - .3, t_end - .2, .3, .3)
        if mb:
            massband(w, 1.05, 0, h, text=f"{h:.2f} m", a=mb)
        na = min(1, fenster(t, -1, t_born - .3, 0, .3) + fenster(t, t_end - .3, 99, .3, 0))
        if na:
            w.aus(); bx, by = w.bild(-.9, 1.75); fs.text(ctx, "1.75 m", bx, by - 40, 40, rgb("d6deef"), .14, alpha=na); w.ein()
        w.aus()
        # Alter ueber dem Kopf
        aa = fenster(t, t_grow - .2, t_80, .3, .3)
        if aa:
            bx, by = w.bild(.6, h + .25)
            badge(ctx, f"AGE {max(alter(t), 1)}", bx, by - 40, aa, f=WEISS, tf=NACHT, groesse=40)
        # Karten
        za = fenster(t, -1, t_zwei + .2, 0, .4) + fenster(t, t_end - .4, 99, .25, 0)
        zahlkarte(ctx, "2.72 m", "TALLEST HUMAN EVER", za, pop=1 - ease((t - (t_end - .4)) / .3) if t > t_end - .4 else 0)
        badge(ctx, "TALLEST HUMAN EVER", W / 2, 300, fenster(t, t_tall - .1, t_born - .2))
        badge(ctx, "ROBERT WADLOW · 1918–1940", W / 2, 300, fenster(t, t_zwei + .3, t_tall - .2), f=WEISS)
        badge(ctx, "80+ YEARS · STILL NO ONE TALLER", W / 2, 300, fenster(t, t_80 + .2, t_end - .45), f=WEISS)
        U.zeichne(ctx, t)
    return D, zeichne, [t_born, t_grow, t_80, t_end]


# ======================================================================
@szene
def amge():
    U = Untertitel("amge"); D = U.ende() + .3
    t1, t_alive, t_kueche, t_rek, t_heute, t_tv, t_frage, t_exakt = 2.7, 4.9, 7.1, 10.3, 13.7, 15.6, 18.8, 21.8
    START = (0, .25, .85, 400)
    cam = Kamera([START, (t1, .1, .55, 700), (t_alive + .8, .05, .45, 820), (t_kueche - .1, .1, .5, 760), (t_kueche + .7, .7, .6, 640),
                  (t_rek - .2, .7, .6, 620), (t_rek + .6, 0, .55, 760), (t_tv + .6, 0, .5, 820), (t_frage, 0, .55, 760),
                  (t_exakt - .3, *START[1:]), (D, *START[1:])])

    def zeichne(ctx, t):
        studio_hg(ctx, t, rgb("2a2140"), rgb("0b0a16"))
        w = Welt(ctx, cam, t); w.ein(); c = ctx
        boden(w, rgb("4a3a5c"), rgb("16121f"))
        # Kuechenkorpus
        c.rectangle(.75, 0, 1.4, .86); farbe(c, rgb("d9d2c4")); c.fill()
        c.rectangle(.7, .86, 1.5, .05); farbe(c, rgb("8b6b4a")); c.fill()
        for i in range(3):
            c.rectangle(.8 + i * .46, .1, .4, .66); farbe(c, rgb("c4bcae")); c.fill()
            linie(c, [(.95 + i * .46, .62), (1.05 + i * .46, .62)], w.px(6), rgb("6d665c"))
        # Spotlight fuer Schauspielerin
        sa = fenster(t, t_tv - .1, t_frage + .3, .3, .4)
        if sa:
            g = cairo.LinearGradient(0, 3, 0, 0); g.add_color_stop_rgba(0, 1, .95, .8, .0); g.add_color_stop_rgba(1, 1, .95, .8, .35 * sa)
            poly(c, [(-.12, 3), (.12, 3), (.55, 0), (-.55, 0)], (1, 1, 1), 0); c.move_to(-.12, 3); c.line_to(.12, 3); c.line_to(.55, 0); c.line_to(-.55, 0); c.close_path()
            c.set_source(g); c.fill()
        schatten(w, -.9, .6); schatten(w, 0, .35)
        mensch(w, -.9, 1.65, f=rgb("b8c3dc"), kleid=True, haare=rgb("2a1d17"))
        mensch(w, 0, .628, f=rgb("f6efe6"), kleid=True, haare=rgb("1a1210"))
        ka = fenster(t, t_kueche - .1, t_rek, .3, .3)
        if ka:
            c.set_dash([w.px(14), w.px(10)]); linie(c, [(-.3, .9), (2.3, .9)], w.px(4), CYAN, ka); c.set_dash([])
            massband(w, .42, .628, .91, f=CYAN, text="+27 cm", a=ka, groesse=46)
        ma = 1 - fenster(t, t_kueche - .2, t_frage + .2, .2, .3)
        massband(w, .3, 0, .628, text="62.8 cm", a=ma, groesse=50)
        w.aus()
        za = fenster(t, -1, t1 + .2, 0, .4) + fenster(t, t_exakt - .1, 99, .2, 0)
        zahlkarte(ctx, "62.8 cm", "SHORTEST WOMAN ALIVE", za, pop=1 - ease((t - t_exakt + .1) / .3) if t > t_exakt - .1 else 0)
        badge(ctx, "JYOTI AMGE · INDIA", W / 2, 300, fenster(t, t1 + .2, t_kueche - .2), f=WEISS)
        badge(ctx, "KITCHEN COUNTER ≈ 90 cm", W / 2, 300, fenster(t, t_kueche + .1, t_rek - .2), f=CYAN)
        ra = fenster(t, t_rek, t_tv - .2)
        if ra:
            jahr = int(round(lerp(2011, 2026, ease((t - t_heute) / 1.1)))) if t > t_heute else 2011
            fs.text(ctx, str(jahr), W / 2, 330, 150, GELB, .1, alpha=ra)
            fs.text(ctx, "RECORD HOLDER SINCE 2011" if t < t_heute else "STILL THE RECORD HOLDER", W / 2, 430, 44, WEISS, .14, alpha=ra)
        badge(ctx, "ACTRESS · FAMOUS TV SHOW", W / 2, 300, fenster(t, t_tv, t_frage - .1), f=GELB)
        U.zeichne(ctx, t)
    return D, zeichne, [t1, t_kueche, t_rek, t_tv, t_exakt]


if __name__ == "__main__":
    import rk_szenen2
    SZENEN.update(rk_szenen2.S2)
    key = sys.argv[1]
    D, z, wusch = SZENEN[key]()
    if "--test" in sys.argv:
        ts = [float(x) for x in sys.argv[sys.argv.index("--test") + 1].split(",")]
        rendern(key, D, z, wusch, os.path.join(HIER, "test"), nur=ts)
    else:
        print(rendern(key, D, z, wusch, os.path.join(HIER, "videos")))
