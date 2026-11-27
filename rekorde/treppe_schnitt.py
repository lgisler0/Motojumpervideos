"""Schnitt Treppenlauf Empire State Building 9:33 (Paul Crake): Blender-Bilder -> 1080x1920/60fps + Badges, Untertitel. Ton: nur Stimme + Musik."""
import os, subprocess, math
import cairo
from rk_basis import *

HIER = os.path.dirname(os.path.abspath(__file__))
U = Untertitel("treppe"); D = 26.6
RFPS = 15
SCHNITTE = [1.4, 2.4, 3.7, 5.9, 7.5, 10.0, 13.1, 15.6, 16.5, 17.4, 18.4, 20.5, 22.4]


def overlay(ctx, t):
    lg = cairo.LinearGradient(0, H - 640, 0, H); lg.add_color_stop_rgba(0, 0, 0, 0, 0); lg.add_color_stop_rgba(1, 0, 0, 0, .5)
    ctx.set_source(lg); ctx.rectangle(0, H - 640, W, 640); ctx.fill()
    ha = fenster(t, -1, 1.4, 0, .2) + fenster(t, D - .4, 99, .25, 0)
    if ha:
        lg = cairo.LinearGradient(0, 0, 0, 560); lg.add_color_stop_rgba(0, 0, 0, 0, .55 * ha); lg.add_color_stop_rgba(1, 0, 0, 0, 0)
        ctx.set_source(lg); ctx.rectangle(0, 0, W, 560); ctx.fill()
        fs.text(ctx, "1 JOB:", W / 2, 260, 96, WEISS, .1, alpha=ha)
        fs.text(ctx, "RUN UP THE STAIRS", W / 2, 370, 76, GELB, .1, alpha=ha)
    badge(ctx, "WHICH STAIRS?", W / 2, 300, fenster(t, 2.55, 3.65), f=GELB, groesse=64)
    badge(ctx, "NEW YORK · 443 m", W / 2, 300, fenster(t, 3.8, 5.85), f=WEISS, groesse=52)
    badge(ctx, "86 FLOORS", W / 2, 300, fenster(t, 6.0, 7.45), f=GELB, groesse=72)
    badge(ctx, "1,576 STEPS", W / 2, 300, fenster(t, 7.6, 9.95), f=GELB, groesse=72)
    badge(ctx, "2 STEPS AT A TIME", W / 2, 300, fenster(t, 10.1, 13.0), f=WEISS, groesse=56)
    badge(ctx, "TOP: FLOOR 86", W / 2, 300, fenster(t, 18.5, 20.4), f=WEISS, groesse=56)
    badge(ctx, "9:33", W / 2, 300, fenster(t, 20.7, 22.35), f=GELB, groesse=96)
    badge(ctx, "FASTEST EMPIRE STATE RUN-UP", W / 2, 300, fenster(t, 22.5, D - .45), f=GELB, groesse=40)
    rekordlabel(ctx, fenster(t, 22.5, D - .45))
    U.zeichne(ctx, t)


def main():
    liste = os.path.join(HIER, "_tr_liste.txt"); n = int(round(D * RFPS))
    with open(liste, "w") as f:
        for i in range(n):
            f.write(f"file 'trframes/treppe_{i:04d}.png'\nduration {1 / RFPS}\n")
        f.write(f"file 'trframes/treppe_{n - 1:04d}.png'\n")
    basis = os.path.join(HIER, "_trbasis.mp4")
    if not os.path.exists(basis):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", liste,
                        "-vf", f"fps={RFPS},minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=fdiff:scd_threshold=6,scale=1080:1920:flags=lanczos,unsharp=5:5:0.4,noise=alls=4:allf=t",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", basis], check=True, cwd=HIER)
    wav = os.path.join(HIER, "_treppe.wav"); out = os.path.join(HIER, "videos", "rekord_treppe_3d.mp4")
    ton_spannung("treppe", D, SCHNITTE + [D - .9], wav)          # nur Stimme + Musik (keine Geraeusche)
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
