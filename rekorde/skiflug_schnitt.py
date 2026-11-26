"""Schnitt Skiflug 254,5 m (Domen Prevc): Blender-Bilder -> 1080x1920/60fps + Badges, Untertitel. Ton: nur Stimme + Musik."""
import os, subprocess, math
import cairo
from rk_basis import *

HIER = os.path.dirname(os.path.abspath(__file__))
U = Untertitel("skiflug"); D = 27.4
RFPS = 15
SCHNITTE = [1.4, 3.8, 5.0, 6.5, 8.0, 9.6, 11.5, 12.9, 14.5, 15.4, 17.4, 19.4, 21.1, 23.5, 25.6]
A_ANL = 2 * 78.0 / 5.4 ** 2           # wie in skiflug3d.py (Anlauf 78 m in 5.4 s)


def overlay(ctx, t):
    lg = cairo.LinearGradient(0, H - 640, 0, H); lg.add_color_stop_rgba(0, 0, 0, 0, 0); lg.add_color_stop_rgba(1, 0, 0, 0, .5)
    ctx.set_source(lg); ctx.rectangle(0, H - 640, W, 640); ctx.fill()
    ha = fenster(t, -1, 1.4, 0, .2) + fenster(t, D - .4, 99, .25, 0)
    if ha:
        lg = cairo.LinearGradient(0, 0, 0, 560); lg.add_color_stop_rgba(0, 0, 0, 0, .55 * ha); lg.add_color_stop_rgba(1, 0, 0, 0, 0)
        ctx.set_source(lg); ctx.rectangle(0, 0, W, 560); ctx.fill()
        fs.text(ctx, "1 JOB:", W / 2, 260, 96, WEISS, .1, alpha=ha)
        fs.text(ctx, "FLY ON SKIS", W / 2, 370, 84, GELB, .1, alpha=ha)
    badge(ctx, "HOW FAR?", W / 2, 300, fenster(t, 3.85, 4.95), f=GELB, groesse=60)
    badge(ctx, "PLANICA · SLOVENIA", W / 2, 300, fenster(t, 5.05, 6.45), f=WEISS, groesse=44)
    a_ = fenster(t, 9.6, 11.45, .1, .15)             # Tempo im Anlauf (Story-Zeit 3.8 -> 5.7 s)
    if a_ > 0:
        ts = 3.8 + (t - 9.6) / 1.9 * 1.9
        kmh = min(104, A_ANL * max(0, ts - .6) * 3.6)
        badge(ctx, f"{kmh:.0f} km/h", W / 2, 300, a_, f=GELB if kmh > 95 else WEISS, groesse=80)
    a_ = fenster(t, 15.45, 17.35, .1, .15)            # Flugzeit (Story 8 -> 12 s, Absprung bei 6 s)
    if a_ > 0:
        badge(ctx, "\u2248 8 s IN THE AIR", W / 2, 300, a_, f=WEISS, groesse=60)
    badge(ctx, "254.5 m", W / 2, 300, fenster(t, 19.45, 21.05), f=GELB, groesse=90)
    badge(ctx, "> 2 FOOTBALL FIELDS", W / 2, 300, fenster(t, 21.15, 23.45), f=WEISS, groesse=52)
    badge(ctx, "LONGEST SKI JUMP EVER", W / 2, 300, fenster(t, 23.55, D - .45), f=GELB, groesse=48)
    rekordlabel(ctx, fenster(t, 19.45, D - .45))
    U.zeichne(ctx, t)


def main():
    liste = os.path.join(HIER, "_sf_liste.txt"); n = int(round(D * RFPS))
    with open(liste, "w") as f:
        for i in range(n):
            f.write(f"file 'sfframes/skiflug_{i:04d}.png'\nduration {1 / RFPS}\n")
        f.write(f"file 'sfframes/skiflug_{n - 1:04d}.png'\n")
    basis = os.path.join(HIER, "_sfbasis.mp4")
    if not os.path.exists(basis):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", liste,
                        "-vf", f"fps={RFPS},minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=fdiff:scd_threshold=6,scale=1080:1920:flags=lanczos,unsharp=5:5:0.4,noise=alls=4:allf=t",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", basis], check=True, cwd=HIER)
    wav = os.path.join(HIER, "_skiflug.wav"); out = os.path.join(HIER, "videos", "rekord_skiflug_3d.mp4")
    ton_spannung("skiflug", D, SCHNITTE + [D - .9], wav)          # nur Stimme + Musik (keine Geraeusche)
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
