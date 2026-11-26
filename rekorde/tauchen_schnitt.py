"""Schnitt Tieftauchen 136 m (Alexey Molchanov): Blender-Bilder -> 1080x1920/60fps + Badges, Untertitel. Ton: nur Stimme + Musik."""
import os, subprocess, math
import cairo
from rk_basis import *

HIER = os.path.dirname(os.path.abspath(__file__))
U = Untertitel("tauchen"); D = 27.0
RFPS = 15
SCHNITTE = [1.5, 4.0, 5.0, 6.5, 9.4, 12.0, 15.3, 16.4, 18.9, 21.6, 23.2]


def overlay(ctx, t):
    lg = cairo.LinearGradient(0, H - 640, 0, H); lg.add_color_stop_rgba(0, 0, 0, 0, 0); lg.add_color_stop_rgba(1, 0, 0, 0, .5)
    ctx.set_source(lg); ctx.rectangle(0, H - 640, W, 640); ctx.fill()
    ha = fenster(t, -1, 1.4, 0, .2) + fenster(t, D - .4, 99, .25, 0)
    if ha:
        lg = cairo.LinearGradient(0, 0, 0, 560); lg.add_color_stop_rgba(0, 0, 0, 0, .55 * ha); lg.add_color_stop_rgba(1, 0, 0, 0, 0)
        ctx.set_source(lg); ctx.rectangle(0, 0, W, 560); ctx.fill()
        fs.text(ctx, "1 JOB:", W / 2, 260, 96, WEISS, .1, alpha=ha)
        fs.text(ctx, "DIVE DEEP", W / 2, 370, 84, GELB, .1, alpha=ha)
    badge(ctx, "ONE BREATH", W / 2, 300, fenster(t, 1.55, 3.95), f=WEISS, groesse=60)
    badge(ctx, "HOW DEEP?", W / 2, 300, fenster(t, 4.05, 4.95), f=GELB, groesse=64)
    badge(ctx, "LIMASSOL \u00b7 CYPRUS", W / 2, 300, fenster(t, 5.05, 6.45), f=WEISS, groesse=46)
    badge(ctx, "-30 m", W / 2, 300, fenster(t, 12.05, 15.25), f=WEISS, groesse=84)
    badge(ctx, "14.6 \u00d7 AIR PRESSURE", W / 2, 300, fenster(t, 16.45, 18.85), f=WEISS, groesse=52)
    badge(ctx, "-136 m", W / 2, 300, fenster(t, 18.95, 21.55), f=GELB, groesse=90)
    badge(ctx, "DEEPEST CONSTANT WEIGHT DIVE", W / 2, 300, fenster(t, 23.25, D - .45), f=GELB, groesse=40)
    rekordlabel(ctx, fenster(t, 18.95, D - .45))
    U.zeichne(ctx, t)


def main():
    liste = os.path.join(HIER, "_tc_liste.txt"); n = int(round(D * RFPS))
    with open(liste, "w") as f:
        for i in range(n):
            f.write(f"file 'tcframes/tauchen_{i:04d}.png'\nduration {1 / RFPS}\n")
        f.write(f"file 'tcframes/tauchen_{n - 1:04d}.png'\n")
    basis = os.path.join(HIER, "_tcbasis.mp4")
    if not os.path.exists(basis):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", liste,
                        "-vf", f"fps={RFPS},minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=fdiff:scd_threshold=6,scale=1080:1920:flags=lanczos,unsharp=5:5:0.4,noise=alls=4:allf=t",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", basis], check=True, cwd=HIER)
    wav = os.path.join(HIER, "_tauchen.wav"); out = os.path.join(HIER, "videos", "rekord_tauchen_3d.mp4")
    ton_spannung("tauchen", D, SCHNITTE + [D - .9], wav)          # nur Stimme + Musik (keine Geraeusche)
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
