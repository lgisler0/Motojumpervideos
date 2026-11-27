"""Schnitt Aermelkanal 6:45:25 (Andreas Waschburger): Blender-Bilder -> 1080x1920/60fps + Badges, Untertitel. Ton: nur Stimme + Musik."""
import os, subprocess, math
import cairo
from rk_basis import *

HIER = os.path.dirname(os.path.abspath(__file__))
U = Untertitel("kanal"); D = 27.4
RFPS = 15
SCHNITTE = [1.5, 2.5, 3.7, 4.6, 6.3, 9.1, 12.1, 14.3, 15.4, 17.9, 20.2, 23.6]


def overlay(ctx, t):
    lg = cairo.LinearGradient(0, H - 640, 0, H); lg.add_color_stop_rgba(0, 0, 0, 0, 0); lg.add_color_stop_rgba(1, 0, 0, 0, .5)
    ctx.set_source(lg); ctx.rectangle(0, H - 640, W, 640); ctx.fill()
    ha = fenster(t, -1, 1.4, 0, .2) + fenster(t, D - .4, 99, .25, 0)
    if ha:
        lg = cairo.LinearGradient(0, 0, 0, 560); lg.add_color_stop_rgba(0, 0, 0, 0, .55 * ha); lg.add_color_stop_rgba(1, 0, 0, 0, 0)
        ctx.set_source(lg); ctx.rectangle(0, 0, W, 560); ctx.fill()
        fs.text(ctx, "1 JOB:", W / 2, 260, 96, WEISS, .1, alpha=ha)
        fs.text(ctx, "SWIM TO FRANCE", W / 2, 370, 80, GELB, .1, alpha=ha)
    badge(ctx, "FROM WHERE?", W / 2, 300, fenster(t, 2.55, 3.65), f=GELB, groesse=64)
    badge(ctx, "DOVER \u00b7 ENGLAND", W / 2, 300, fenster(t, 3.75, 4.55), f=WEISS, groesse=56)
    badge(ctx, "8 SEPT 2023", W / 2, 300, fenster(t, 4.65, 6.25), f=WEISS, groesse=56)
    badge(ctx, "33 km", W / 2, 300, fenster(t, 9.2, 12.0), f=GELB, groesse=84)
    badge(ctx, "SHIPS UP TO 400 m", W / 2, 300, fenster(t, 12.2, 14.2), f=WEISS, groesse=50)
    a_ = fenster(t, 15.45, 17.85, .1, .1)
    if a_ > 0:
        h = 1 + 5 * (t - 15.45) / 2.4
        badge(ctx, f"HOUR {min(6, int(h))}", W / 2, 300, a_, f=WEISS, groesse=64)
    badge(ctx, "CAP GRIS-NEZ \u00b7 FRANCE", W / 2, 300, fenster(t, 18.0, 20.1), f=WEISS, groesse=48)
    badge(ctx, "6:45:25", W / 2, 300, fenster(t, 20.3, 23.5), f=GELB, groesse=96)
    badge(ctx, "FASTEST CHANNEL SWIM", W / 2, 300, fenster(t, 23.7, D - .45), f=GELB, groesse=48)
    rekordlabel(ctx, fenster(t, 23.7, D - .45))
    U.zeichne(ctx, t)


def main():
    liste = os.path.join(HIER, "_ka_liste.txt"); n = int(round(D * RFPS))
    with open(liste, "w") as f:
        for i in range(n):
            f.write(f"file 'kaframes/kanal_{i:04d}.png'\nduration {1 / RFPS}\n")
        f.write(f"file 'kaframes/kanal_{n - 1:04d}.png'\n")
    basis = os.path.join(HIER, "_kabasis.mp4")
    if not os.path.exists(basis):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", liste,
                        "-vf", f"fps={RFPS},minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=fdiff:scd_threshold=6,scale=1080:1920:flags=lanczos,unsharp=5:5:0.4,noise=alls=4:allf=t",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", basis], check=True, cwd=HIER)
    wav = os.path.join(HIER, "_kanal.wav"); out = os.path.join(HIER, "videos", "rekord_kanal_3d.mp4")
    ton_spannung("kanal", D, SCHNITTE + [D - .9], wav)          # nur Stimme + Musik (keine Geraeusche)
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
