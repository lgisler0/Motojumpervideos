"""Schnitt Luftanhalten (Vitomir Maričić): Blender-Bilder -> 1080x1920/60fps + Stoppuhr, EKG, Vergleichsbalken, Badges, Untertitel, Ton."""
import os, subprocess, math
import cairo
from rk_basis import *

HIER = os.path.dirname(os.path.abspath(__file__))
U = Untertitel("atem"); D = 34.0
RFPS = 15
UHR = [(14.6, 0), (15.8, 60), (17.0, 300), (17.84, 600), (18.78, 1200), (24.3, 1680), (25.84, 1743)]


def sekunden(t):
    if t < UHR[0][0]:
        return 0
    for (a, x), (b, y) in zip(UHR, UHR[1:]):
        if t < b:
            return x + (y - x) * (t - a) / (b - a)
    return UHR[-1][1]


def ekg(ctx, t, a):
    if a <= 0:
        return
    x0, y0, bw, hh = 140, 520, 800, 120
    rrect(ctx, x0 - 30, y0 - hh, bw + 60, hh * 2, 30); ctx.set_source_rgba(0, 0, 0, .45 * a); ctx.fill()
    ctx.set_line_width(7); ctx.set_source_rgba(1, .35, .3, a)
    per = .55 + 1.1 * min(1, max(0, (t - 19.84) / 2.0))       # Herzschlag wird langsamer
    for i in range(0, 401):
        x = x0 + bw * i / 400; tt = t - (400 - i) / 400 * 2.2
        ph = (tt % per) / per; y = 0
        if .30 < ph < .34: y = -15
        elif .36 < ph < .40: y = -90 * math.sin((ph - .36) / .04 * math.pi)
        elif .40 < ph < .43: y = 30
        elif .55 < ph < .65: y = -18 * math.sin((ph - .55) / .1 * math.pi)
        ctx.line_to(x, y0 + y) if i else ctx.move_to(x, y0 + y)
    ctx.stroke()
    hx, hy, r = x0 + 18, y0 - 78, 14
    ctx.arc(hx - r * .7, hy, r, math.pi, 2 * math.pi); ctx.arc(hx + r * .7, hy, r, math.pi, 2 * math.pi)
    ctx.line_to(hx, hy + r * 2.2); ctx.close_path(); ctx.set_source_rgba(1, .35, .3, a); ctx.fill()
    fs.text(ctx, "HEART RATE", x0 + 150, hy, 30, WEISS, .1, alpha=a)


def balken(ctx, t, a):
    if a <= 0:
        return
    k = ease((t - 29.9) / .9)
    for i, (lab, wert, f) in enumerate((("YOU", 60, WEISS), ("HIM", 1743, GELB))):
        y = 480 + i * 130; laenge = 640 * wert / 1743 * k
        rrect(ctx, 150, y - 40, max(laenge, 30), 80, 40); farbe(ctx, f, a); ctx.fill()
        fs.text(ctx, lab, 95, y, 40, WEISS, .1, alpha=a)
        zeit = "\u2248 1 MIN" if i == 0 else "29:03"
        fs.text(ctx, zeit, min(150 + max(laenge, 30) + 110, 930), y, 44, f, .1, alpha=a)


def overlay(ctx, t):
    lg = cairo.LinearGradient(0, H - 640, 0, H); lg.add_color_stop_rgba(0, 0, 0, 0, 0); lg.add_color_stop_rgba(1, 0, 0, 0, .5)
    ctx.set_source(lg); ctx.rectangle(0, H - 640, W, 640); ctx.fill()
    rg = cairo.RadialGradient(W / 2, H / 2, H * .35, W / 2, H / 2, H * .75)
    rg.add_color_stop_rgba(0, 0, 0, 0, 0); rg.add_color_stop_rgba(1, 0, 0, 0, .4); ctx.set_source(rg); ctx.paint()
    ha = fenster(t, -1, 2.0, 0, .25) + fenster(t, D - .4, 99, .25, 0)
    if ha:
        lg = cairo.LinearGradient(0, 0, 0, 560); lg.add_color_stop_rgba(0, 0, 0, 0, .55 * ha); lg.add_color_stop_rgba(1, 0, 0, 0, 0)
        ctx.set_source(lg); ctx.rectangle(0, 0, W, 560); ctx.fill()
        fs.text(ctx, "1 JOB:", W / 2, 260, 96, WEISS, .1, alpha=ha)
        fs.text(ctx, "DON'T BREATHE", W / 2, 370, 96, GELB, .1, alpha=ha)
    badge(ctx, "2025", W / 2, 300, fenster(t, 3.45, 5.85), f=WEISS, groesse=44)
    badge(ctx, "3 m DEEP", W / 2, 300, fenster(t, 6.0, 8.85), f=WEISS, groesse=44)
    badge(ctx, "100% OXYGEN", W / 2, 300, fenster(t, 10.0, 12.45), f=WEISS, groesse=44)
    ua = fenster(t, 14.6, 28.85, .2, .2)
    if ua > 0:
        s_ = int(sekunden(t)); badge(ctx, f"{s_ // 60:02d}:{s_ % 60:02d}", W / 2, 300, ua, f=GELB if t > 25.84 else WEISS, groesse=72)
    ekg(ctx, t, fenster(t, 19.9, 22.05))
    balken(ctx, t, fenster(t, 29.9, 32.35))
    badge(ctx, "DON'T TRY THIS AT HOME", W / 2, 300, fenster(t, 32.5, D - .45), f=ROT, tf=WEISS, groesse=40)
    rekordlabel(ctx, fenster(t, 27.9, 29.0))
    U.zeichne(ctx, t)


def main():
    liste = os.path.join(HIER, "_atliste.txt"); n = int(round(D * RFPS))
    with open(liste, "w") as f:
        for i in range(n):
            f.write(f"file 'atframes/atem_{i:04d}.png'\nduration {1 / RFPS}\n")
        f.write(f"file 'atframes/atem_{n - 1:04d}.png'\n")
    basis = os.path.join(HIER, "_atbasis.mp4")
    if not os.path.exists(basis):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", liste,
                        "-vf", f"fps={RFPS},minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=fdiff:scd_threshold=6,scale=1080:1920:flags=lanczos,unsharp=5:5:0.5,noise=alls=5:allf=t",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", basis], check=True, cwd=HIER)
    wav = os.path.join(HIER, "_atem.wav"); out = os.path.join(HIER, "videos", "rekord_atem_3d.mp4")
    ton_spannung("atem", D, [2.1, 3.4, 5.9, 8.9, 12.5, 15.8, 17.0, 17.84, 18.78, 19.84, 22.1, 24.3, 27.4, 28.9, 32.4, D - .9], wav)
    lese = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", basis, "-f", "rawvideo", "-pix_fmt", "bgra", "-"], stdout=subprocess.PIPE)
    sch = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
                            "-c:v", "libx264", "-preset", "slow", "-crf", "15", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-t", f"{D:.3f}",
                            "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    gr = W * H * 4; f = 0
    while True:
        roh = lese.stdout.read(gr)
        if len(roh) < gr:
            break
        arr = bytearray(roh); s = cairo.ImageSurface.create_for_data(arr, cairo.FORMAT_ARGB32, W, H)
        ctx = cairo.Context(s); overlay(ctx, f / FPS); s.flush(); sch.stdin.write(bytes(arr)); f += 1
    sch.stdin.close(); sch.wait(); os.remove(wav)
    print("Fertig:", out, f)


if __name__ == "__main__":
    main()
