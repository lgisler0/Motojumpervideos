"""Schnitt Fahrer-Geschichte (BelAZ bremsen): Blender-Bilder -> 1080x1920/60fps + Zahlen, Badges, Untertitel, Ton."""
import os, subprocess, math
import cairo
from rk_basis import *

HIER = os.path.dirname(os.path.abspath(__file__))
U = Untertitel("putzer"); D = 29.6
RFPS = 15


def gross(ctx, oben, unten, a, go=140):
    if a:
        fs.text(ctx, oben, W / 2, 290, go, GELB, .1, alpha=a)
        fs.text(ctx, unten, W / 2, 390, 40, WEISS, .14, alpha=a)


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
        fs.text(ctx, "CLEAN 24,000 WINDOWS", W / 2, 370, 74, GELB, .1, alpha=ha)
    badge(ctx, "828 m", W / 2, 300, fenster(t, 5.0, 7.8), f=GELB, groesse=44)
    badge(ctx, "ABOUT 24,000 WINDOWS", W / 2, 300, fenster(t, 8.2, 10.7), f=WEISS, groesse=44)
    badge(ctx, "13-TONNE MACHINE", W / 2, 300, fenster(t, 13.2, 15.4), f=GELB, groesse=44)
    badge(ctx, "36 CLEANERS · 3 MONTHS", W / 2, 300, fenster(t, 20.7, 24.4), f=WEISS, groesse=44)
    U.zeichne(ctx, t)


def main():
    liste = os.path.join(HIER, "_putzerliste.txt"); n = int(round(D * RFPS))
    with open(liste, "w") as f:
        for i in range(n):
            f.write(f"file 'pzframes/putzer_{i:04d}.png'\nduration {1 / RFPS}\n")
        f.write(f"file 'pzframes/putzer_{n - 1:04d}.png'\n")
    basis = os.path.join(HIER, "_putzerbasis.mp4")
    if not os.path.exists(basis):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", liste,
                        "-vf", f"fps={RFPS},minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,scale=1080:1920:flags=lanczos,unsharp=5:5:0.5,noise=alls=5:allf=t",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", basis], check=True, cwd=HIER)
    wav = os.path.join(HIER, "_putzer.wav"); out = os.path.join(HIER, "videos", "rekord_putzer_3d.mp4")
    ton_spannung("putzer", D, [2.0, 4.6, 7.9, 10.8, 13.0, 15.45, 18.1, 20.5, 24.5, 26.4, 28.6, D - .9], wav)
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
