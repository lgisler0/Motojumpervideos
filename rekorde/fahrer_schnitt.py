"""Schnitt Fahrer-Geschichte (BelAZ bremsen): Blender-Bilder -> 1080x1920/60fps + Zahlen, Badges, Untertitel, Ton."""
import os, subprocess, math
import cairo
from rk_basis import *

HIER = os.path.dirname(os.path.abspath(__file__))
U = Untertitel("fahrer"); D = 33.4
RFPS = 15


def gross(ctx, oben, unten, a, go=140):
    if a:
        fs.text(ctx, oben, W / 2, 290, go, GELB, .1, alpha=a)
        fs.text(ctx, unten, W / 2, 390, 40, WEISS, .14, alpha=a)


def overlay(ctx, t):
    lg = cairo.LinearGradient(0, H - 640, 0, H); lg.add_color_stop_rgba(0, 0, 0, 0, 0); lg.add_color_stop_rgba(1, 0, 0, 0, .5)
    ctx.set_source(lg); ctx.rectangle(0, H - 640, W, 640); ctx.fill()
    # Vignette fuer Kino-Look
    rg = cairo.RadialGradient(W / 2, H / 2, H * .35, W / 2, H / 2, H * .75)
    rg.add_color_stop_rgba(0, 0, 0, 0, 0); rg.add_color_stop_rgba(1, 0, 0, 0, .45); ctx.set_source(rg); ctx.paint()
    ha = fenster(t, -1, 2.0, 0, .25) + fenster(t, D - .4, 99, .25, 0)
    if ha:
        lg = cairo.LinearGradient(0, 0, 0, 560); lg.add_color_stop_rgba(0, 0, 0, 0, .55 * ha); lg.add_color_stop_rgba(1, 0, 0, 0, 0)
        ctx.set_source(lg); ctx.rectangle(0, 0, W, 560); ctx.fill()
        fs.text(ctx, "1 JOB:", W / 2, 260, 96, WEISS, .1, alpha=ha)
        fs.text(ctx, "STOP 800 TONNES", W / 2, 370, 96, GELB, .1, alpha=ha)
    badge(ctx, "RETARDER PEDAL", W / 2, 300, fenster(t, 17.0, 18.6), f=GELB, groesse=40)
    badge(ctx, "MOTORS BECOME GENERATORS", W / 2, 300, fenster(t, 20.3, 21.55), f=GELB, groesse=40)
    badge(ctx, "ELECTRICITY BECOMES HEAT", W / 2, 300, fenster(t, 23.6, 25.8), f=ROT, tf=WEISS, groesse=40)
    U.zeichne(ctx, t)


def main():
    liste = os.path.join(HIER, "_fzliste.txt"); n = int(round(D * RFPS))
    with open(liste, "w") as f:
        for i in range(n):
            f.write(f"file 'fzframes/fahrer_{i:04d}.png'\nduration {1 / RFPS}\n")
        f.write(f"file 'fzframes/fahrer_{n - 1:04d}.png'\n")
    basis = os.path.join(HIER, "_fzbasis.mp4")
    if not os.path.exists(basis):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", liste,
                        "-vf", f"fps={RFPS},minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,scale=1080:1920:flags=lanczos,unsharp=5:5:0.5,noise=alls=5:allf=t",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", basis], check=True, cwd=HIER)
    wav = os.path.join(HIER, "_fz.wav"); out = os.path.join(HIER, "videos", "rekord_fahrer_3d.mp4")
    ton_spannung("fahrer", D, [2.08, 3.6, 5.55, 8.95, 14.0, 16.5, 18.7, 21.6, 23.55, 25.85, 29.95, 31.0, D - .9], wav)
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
