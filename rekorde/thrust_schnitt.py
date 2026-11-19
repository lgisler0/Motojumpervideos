"""Schnitt ThrustSSC: Blender-Bilder -> 1080x1920/60fps + Zahlen, Badges, Untertitel, Ton."""
import os, subprocess, math
import cairo
from rk_basis import *

HIER = os.path.dirname(os.path.abspath(__file__))
U = Untertitel("thrust"); D = 30.2
t_name, t_1997, t_schall, t_eng, t_lang, t_30, t_rek = 3.88, 8.2, 12.2, 14.1, 19.96, 24.04, 26.98
RFPS = 15


def overlay(ctx, t):
    lg = cairo.LinearGradient(0, H - 640, 0, H); lg.add_color_stop_rgba(0, 0, 0, 0, 0); lg.add_color_stop_rgba(1, 0, 0, 0, .5)
    ctx.set_source(lg); ctx.rectangle(0, H - 640, W, 640); ctx.fill()
    lg = cairo.LinearGradient(0, 0, 0, 560); lg.add_color_stop_rgba(0, 0, 0, 0, .45); lg.add_color_stop_rgba(1, 0, 0, 0, 0)
    ctx.set_source(lg); ctx.rectangle(0, 0, W, 560); ctx.fill()
    za = fenster(t, -1, t_name, 0, .3) + fenster(t, D - .45, 99, .25, 0)
    zahlkarte(ctx, "1,228 km/h", "FASTEST CAR EVER", za, pop=1 - ease((t - D + .45) / .3) if t > D - .45 else 0)
    badge(ctx, "THRUST SSC · ANDY GREEN", W / 2, 300, fenster(t, t_name, t_1997 - .1), f=GELB)
    badge(ctx, "15 OCT 1997 · BLACK ROCK DESERT, NEVADA", W / 2, 300, fenster(t, t_1997, t_schall - .1), f=WEISS, groesse=34)
    # Schallmauer: Lichtblitz + Schockwellen-Ringe um das Auto (Schlieren-Effekt)
    for k in range(3):
        tt = t - (t_schall + .5) - k * .18
        if 0 <= tt <= 1.1:
            r = 40 + tt * 900; a = (1 - tt / 1.1) * .45
            ctx.set_line_width(10 * (1 - tt / 1.1) + 2); ctx.arc(W * .47, H * .515, r, 0, 2 * math.pi)
            ctx.set_source_rgba(1, 1, 1, a); ctx.stroke()
    fl = max(0, 1 - abs(t - (t_schall + .5)) / .15)
    if fl:
        ctx.set_source_rgba(1, 1, 1, .5 * fl); ctx.paint()
    ma = fenster(t, t_schall, t_eng - .1)
    if ma:
        fs.text(ctx, "MACH 1.02", W / 2, 290, 150, GELB, .1, alpha=ma)
        fs.text(ctx, "FIRST CAR TO BREAK THE SOUND BARRIER", W / 2, 390, 40, WEISS, .14, alpha=ma)
    ea = fenster(t, t_eng, t_lang - .1)
    if ea:
        fs.text(ctx, "100,000 HP", W / 2, 290, 140, GELB, .1, alpha=ea)
        fs.text(ctx, "2 JET ENGINES FROM A FIGHTER PLANE", W / 2, 390, 40, WEISS, .14, alpha=ea)
    la = fenster(t, t_lang, t_30 - .1)
    if la:
        fs.text(ctx, "16.5 m · 10.5 t", W / 2, 290, 120, GELB, .1, alpha=la)
        fs.text(ctx, "NEXT TO A PERSON AND A NORMAL CAR", W / 2, 390, 40, WEISS, .14, alpha=la)
    ja = fenster(t, t_30, t_rek + .6)
    if ja:
        jahr = int(round(lerp(1997, 2026, ease((t - t_30) / 1.4))))
        fs.text(ctx, str(jahr), W / 2, 290, 150, GELB, .1, alpha=ja)
        fs.text(ctx, "RECORD STILL UNBEATEN", W / 2, 390, 44, WEISS, .14, alpha=ja)
    U.zeichne(ctx, t)


def main():
    liste = os.path.join(HIER, "_thliste.txt"); n = int(round(D * RFPS))
    with open(liste, "w") as f:
        for i in range(n):
            f.write(f"file 'thframes/thrust_{i:04d}.png'\nduration {1 / RFPS}\n")
        f.write(f"file 'thframes/thrust_{n - 1:04d}.png'\n")
    basis = os.path.join(HIER, "_thbasis.mp4")
    if not os.path.exists(basis):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", liste,
                        "-vf", f"fps={RFPS},minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,scale=1080:1920:flags=lanczos,unsharp=5:5:0.5,noise=alls=5:allf=t",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", basis], check=True, cwd=HIER)
    wav = os.path.join(HIER, "_th.wav"); out = os.path.join(HIER, "videos", "rekord_thrust_3d.mp4")
    ton_spannung("thrust", D, [t_name, t_1997, t_schall, t_eng, t_lang, t_30, D - .9], wav)
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
