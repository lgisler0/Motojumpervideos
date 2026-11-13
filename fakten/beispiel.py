"""Beispiel-Video im Stil 'eine verblueffende Frage, sofort gezeigt': Loch durch die Erde.
Aufruf: python3 beispiel.py [ordner]"""
import math, sys, os, cairo
import fakten_studio as fs
from fakten_studio import W, H, rgb, text, kreis, glut, verlauf, sterne, ease, lerp, zahl, pille, rund, WEISS, GELB, CYAN, PINK, DUNKEL

CX, CY, R = W / 2, 960, 470
SCHICHT = [(1.0, "7a4a2b"), (.985, "c2571a"), (.55, "f08a1d"), (.2, "ffd23f")]


def figur(ctx, x, y, s, rot=0.0, t=0.0, zappeln=1.0):
    """Kleiner Springer mit Helm. (x, y) = Koerpermitte, s = Groesse in Pixel."""
    ctx.save(); ctx.translate(x, y); ctx.rotate(rot); ctx.scale(s / 100, s / 100)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_width(13)
    w = math.sin(t * 14) * 22 * zappeln
    ctx.set_source_rgb(*rgb("ff7a1a"))
    for sx in (-1, 1):  # Arme und Beine
        ctx.move_to(sx * 20, -8); ctx.line_to(sx * (46 + w * .3 * sx), -44 - w * sx); ctx.stroke()
        ctx.move_to(sx * 12, 34); ctx.line_to(sx * (22 - w * .2 * sx), 74 + w * .4 * sx); ctx.stroke()
    rund(ctx, -26, -24, 52, 64, 20); ctx.set_source_rgb(*rgb("ff7a1a")); ctx.fill()
    ctx.arc(0, -46, 30, 0, 2 * math.pi); ctx.set_source_rgb(1, 1, 1); ctx.fill()
    rund(ctx, -20, -58, 40, 24, 11); ctx.set_source_rgb(*rgb("1b2a55")); ctx.fill()
    rund(ctx, -14, -54, 12, 6, 3); ctx.set_source_rgba(1, 1, 1, .7); ctx.fill()
    ctx.restore()


def erdschnitt(ctx, t, glueh=0.0):
    glut(ctx, CX, CY, R * 1.25, rgb("4aa3ff"), .3)
    for k, farbe in SCHICHT:
        ctx.arc(CX, CY, R * k, 0, 2 * math.pi); ctx.set_source_rgb(*rgb(farbe)); ctx.fill()
    ctx.arc(CX, CY, R, 0, 2 * math.pi); ctx.set_source_rgb(*rgb("3fae5a")); ctx.set_line_width(14); ctx.stroke()
    glut(ctx, CX, CY, R * (.34 + .03 * math.sin(t * 3)), rgb("fff6c0"), .75 + .25 * glueh)
    rund(ctx, CX - 50, CY - R - 4, 100, 2 * R + 8, 6); ctx.set_source_rgb(*rgb("0b1026")); ctx.fill()


def v_hole(ctx, i, tl, d, t, V):
    if i == 0:  # Einstieg: Figur springt sofort
        verlauf(ctx, rgb("3aa0ff"), rgb("bfe6ff"))
        for cx, cy, r in [(220, 520, 70), (300, 500, 90), (380, 530, 60), (820, 700, 60), (890, 680, 80)]:
            kreis(ctx, cx, cy, r, WEISS, .9)
        ctx.rectangle(0, 1180, W, H - 1180); ctx.set_source_rgb(*rgb("3fae5a")); ctx.fill()
        ctx.rectangle(0, 1330, W, H - 1330); ctx.set_source_rgb(*rgb("7a4a2b")); ctx.fill()
        ctx.save(); ctx.translate(W / 2 + 60, 1215); ctx.scale(250, 62); ctx.arc(0, 0, 1, 0, 2 * math.pi); ctx.restore()
        ctx.set_source_rgb(*rgb("0b1026")); ctx.fill()
        k = min(tl / max(d * .55, .1), 1); f = max((tl - d * .55) / max(d * .45 + .3, .1), 0)
        if f <= 0:
            x = lerp(250, 430, ease(k)); y = 1090 - abs(math.sin(k * math.pi * 3)) * 40
            figur(ctx, x, y, 210, 0, t, .15)
        else:
            x = lerp(430, W / 2 + 60, min(f * 2.2, 1)); y = 1090 - math.sin(min(f * 2.2, 1) * math.pi) * 260 + max(f - .45, 0) ** 2 * 2600
            ctx.save()
            if f > .45:
                ctx.rectangle(0, 0, W, 1215); ctx.clip()
            figur(ctx, x, y, 210, f * 2.5, t, 1); ctx.restore()
        text(ctx, "A HOLE THROUGH", W / 2, 250, 104, WEISS, .13, maxw=980); text(ctx, "THE WHOLE EARTH?", W / 2, 385, 112, GELB, .13, maxw=980)
        return
    verlauf(ctx, rgb("070a1c"), rgb("161d45")); sterne(ctx, t)
    P = math.pi
    k = min(tl / max(d, .1), 1)
    phase = {1: lerp(0, .46 * P, k * k), 2: lerp(.46 * P, .54 * P, k), 3: lerp(.54 * P, .97 * P, 1 - (1 - k) ** 2), 4: lerp(.97 * P, P, ease(tl / .6)),
             5: P + 2 * P * k, 6: 3 * P}[i]
    erdschnitt(ctx, t, 1 if i == 6 else 0)
    y = CY - R * math.cos(phase); tempo = 28000 * abs(math.sin(phase))
    if i < 6:
        for j in range(1, 7):  # Fahrtwind-Streifen
            a = (.5 - j * .07) * min(tempo / 12000, 1)
            ry = y - j * 26 * (1 if math.sin(phase) >= 0 else -1)
            ctx.move_to(CX - 22, ry - 30 * (1 if math.sin(phase) >= 0 else -1)); ctx.line_to(CX + 22, ry - 30 * (1 if math.sin(phase) >= 0 else -1)); ctx.set_source_rgba(1, 1, 1, max(a, 0)); ctx.set_line_width(5); ctx.stroke()
        raus = i == 4 and tl > .6
        figur(ctx, CX, y + (36 if raus else 0), 92, P if raus else phase * 1.3, t, 0 if raus else 1)
    else:
        figur(ctx, CX + 130, CY - R - 44, 92, 0, t, 0)
        glut(ctx, CX, CY, R * .5, rgb("ff5a1a"), .5 + .2 * math.sin(t * 5))
        a = ease((tl - .3) / .4)
        text(ctx, "5,500 °C", CX, CY, 120, WEISS, .12, alpha=a); text(ctx, "AS HOT AS THE SUN'S SURFACE", CX, CY + 110, 40, GELB, .16, alpha=a, maxw=820)
    # Anzeigen oben
    if i in (1, 2, 3):
        text(ctx, f"{zahl(round(tempo, -2))} KM/H", W / 2, 250, 120, GELB if i == 2 else WEISS, .12, maxw=980)
        text(ctx, "FALLING FASTER" if i == 1 else ("THE CENTER OF THE EARTH" if i == 2 else "SLOWING DOWN"), W / 2, 365, 50, CYAN, .15)
    if i in (4, 5):
        minuten = 42.2 * phase / P
        text(ctx, f"{int(minuten):02d}:{int(minuten % 1 * 60):02d}" if i == 5 else "42 MINUTES", W / 2, 250, 130, GELB, .12)
        text(ctx, "THE OTHER SIDE OF THE PLANET" if i == 4 else "BACK AND FORTH, FOREVER", W / 2, 365, 50, CYAN, .15, maxw=980)
    if i == 6:
        text(ctx, "MAYBE DON'T TRY IT", W / 2, 270, 100, GELB, .12, maxw=980)


fs.VIDEOS["hole"] = dict(
    zeichne=v_hole, titel="What If You Jumped Through the Earth? 🕳️ 42 Minutes to the Other Side #shorts",
    text="🕳️ Imagine a hole straight through the whole planet, and you jump in. How fast would you get? And where would you end up? 🌍 The answer takes 42 minutes.",
    hashtags="#whatif #physics #earth", tags=["hole through the earth", "what if", "gravity tunnel", "physics facts", "earth facts", "science facts"],
    szenen=[("What if you jumped into a hole, straight through the whole Earth?", .2),
            ("With no air to slow you down, you would fall faster, and faster.", .2),
            ("At the center, you would be flying at 28,000 kilometers per hour.", .3),
            ("But you would not stop there. Now gravity pulls you back, and you slow down.", .2),
            ("After 42 minutes, you would pop out on the other side of the planet.", .5),
            ("Miss the edge, and you fall all the way back. Again, and again.", .3),
            ("Sadly, the center is as hot as the surface of the Sun. So maybe don't try it. Follow for more.", .6)])

if __name__ == "__main__":
    print("Fertig:", fs.Video("hole").render(sys.argv[1] if len(sys.argv) > 1 else os.path.join(fs.HIER, "beispiel")))
