"""Schnitt Everest (Kami Rita Sherpa): Blender-Bilder -> 1080x1920/60fps + Gipfelzaehler, Badges, Untertitel, Ton."""
import os, subprocess, math
import cairo
from rk_basis import *

HIER = os.path.dirname(os.path.abspath(__file__))
U = Untertitel("everest"); D = 31.6
RFPS = 15


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
        fs.text(ctx, "TOP OF THE WORLD", W / 2, 370, 88, GELB, .1, alpha=ha)
    badge(ctx, "8,849 m", W / 2, 300, fenster(t, 1.95, 4.2), f=WEISS, groesse=48)
    badge(ctx, "NEPAL", W / 2, 300, fenster(t, 4.35, 7.2), f=WEISS, groesse=48)
    badge(ctx, "1994", W / 2, 300, fenster(t, 7.35, 10.6), f=WEISS, groesse=48)
    a_ = fenster(t, 10.7, 14.85, .15, .2)
    if a_ > 0:
        n = 1 + int(30 * ease((t - 10.7) / 4.1)); badge(ctx, f"SUMMIT #{n}", W / 2, 300, a_, f=WEISS, groesse=52)
    badge(ctx, "LADDERS OVER CREVASSES", W / 2, 300, fenster(t, 14.95, 17.4), f=WEISS, groesse=40)
    badge(ctx, "ONLY 1/3 OF THE OXYGEN", W / 2, 300, fenster(t, 17.6, 20.9), f=WEISS, groesse=40)
    badge(ctx, "17 MAY 2026", W / 2, 300, fenster(t, 21.05, 23.3), f=WEISS, groesse=48)
    badge(ctx, "AGE 56", W / 2, 300, fenster(t, 23.4, 25.0), f=WEISS, groesse=48)
    badge(ctx, "SUMMIT #32", W / 2, 300, fenster(t, 26.1, 27.55), f=GELB, groesse=60)
    rekordlabel(ctx, fenster(t, 27.65, 30.0))
    U.zeichne(ctx, t)


def main():
    liste = os.path.join(HIER, "_evliste.txt"); n = int(round(D * RFPS))
    with open(liste, "w") as f:
        for i in range(n):
            f.write(f"file 'evframes/everest_{i:04d}.png'\nduration {1 / RFPS}\n")
        f.write(f"file 'evframes/everest_{n - 1:04d}.png'\n")
    basis = os.path.join(HIER, "_evbasis.mp4")
    if not os.path.exists(basis):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", liste,
                        "-vf", f"fps={RFPS},minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=fdiff:scd_threshold=6,scale=1080:1920:flags=lanczos,unsharp=5:5:0.5,noise=alls=5:allf=t",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", basis], check=True, cwd=HIER)
    wav = os.path.join(HIER, "_everest.wav"); out = os.path.join(HIER, "videos", "rekord_everest_3d.mp4")
    ton_spannung("everest", D, [1.88, 4.28, 7.26, 10.68, 11.48, 12.5, 13.56, 14.88, 17.5, 19.1, 21.0, 25.08, 27.62, 30.04, D - .9], wav)
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
