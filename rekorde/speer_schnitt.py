"""Schnitt Speerwurf 98,48 m (Jan Zelezny): Blender-Bilder -> 1080x1920/60fps + Badges, Untertitel. Ton: nur Stimme + Musik."""
import os, subprocess, math
import cairo
from rk_basis import *

HIER = os.path.dirname(os.path.abspath(__file__))
U = Untertitel("speer"); D = 28.0
RFPS = 15
SCHNITTE = [1.5, 2.6, 3.55, 5.95, 8.0, 9.2, 10.9, 12.2, 14.3, 16.6, 18.0, 20.0, 21.6, 25.0]


def overlay(ctx, t):
    lg = cairo.LinearGradient(0, H - 640, 0, H); lg.add_color_stop_rgba(0, 0, 0, 0, 0); lg.add_color_stop_rgba(1, 0, 0, 0, .5)
    ctx.set_source(lg); ctx.rectangle(0, H - 640, W, 640); ctx.fill()
    ha = fenster(t, -1, 1.4, 0, .2) + fenster(t, D - .4, 99, .25, 0)
    if ha:
        lg = cairo.LinearGradient(0, 0, 0, 560); lg.add_color_stop_rgba(0, 0, 0, 0, .55 * ha); lg.add_color_stop_rgba(1, 0, 0, 0, 0)
        ctx.set_source(lg); ctx.rectangle(0, 0, W, 560); ctx.fill()
        fs.text(ctx, "1 JOB:", W / 2, 260, 96, WEISS, .1, alpha=ha)
        fs.text(ctx, "THROW A SPEAR", W / 2, 370, 80, GELB, .1, alpha=ha)
    badge(ctx, "HOW FAR?", W / 2, 300, fenster(t, 2.65, 3.5), f=GELB, groesse=68)
    badge(ctx, "JENA \u00b7 GERMANY \u00b7 1996", W / 2, 300, fenster(t, 3.6, 5.9), f=WEISS, groesse=48)
    badge(ctx, "800 g JAVELIN", W / 2, 300, fenster(t, 6.0, 7.95), f=WEISS, groesse=56)
    # Flugweite live (Bildschirmzeit -> Story-Zeit wie in speer3d.py)
    for (t0, t1, s0, s1) in ((12.2, 14.3, 5.6, 7.3), (14.3, 16.6, 7.3, 8.3), (16.6, 18.0, 8.55, 9.45)):
        if t0 <= t < t1:
            ts = s0 + (s1 - s0) * (t - t0) / (t1 - t0)
            dist = min(98.48, max(0.0, 98.48 * (ts - 5.22) / 3.9))
            badge(ctx, f"{dist:.0f} m" if dist < 98.4 else "98.48 m", W / 2, 300, fenster(t, t0 + .05, t1 - .05, .08, .08), f=GELB if dist >= 98.4 else WEISS, groesse=72)
    badge(ctx, "98.48 m", W / 2, 300, fenster(t, 18.05, 19.95), f=GELB, groesse=96)
    badge(ctx, "\u2248 A FOOTBALL PITCH", W / 2, 300, fenster(t, 20.05, 21.55), f=WEISS, groesse=56)
    badge(ctx, "LONGEST JAVELIN THROW", W / 2, 300, fenster(t, 21.7, D - .45), f=GELB, groesse=48)
    rekordlabel(ctx, fenster(t, 21.7, D - .45))
    U.zeichne(ctx, t)


def main():
    liste = os.path.join(HIER, "_jv_liste.txt"); n = int(round(D * RFPS))
    with open(liste, "w") as f:
        for i in range(n):
            f.write(f"file 'jvframes/speer_{i:04d}.png'\nduration {1 / RFPS}\n")
        f.write(f"file 'jvframes/speer_{n - 1:04d}.png'\n")
    basis = os.path.join(HIER, "_jvbasis.mp4")
    if not os.path.exists(basis):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", liste,
                        "-vf", f"fps={RFPS},minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=fdiff:scd_threshold=6,scale=1080:1920:flags=lanczos,unsharp=5:5:0.4,noise=alls=4:allf=t",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", basis], check=True, cwd=HIER)
    wav = os.path.join(HIER, "_speer.wav"); out = os.path.join(HIER, "videos", "rekord_speer_3d.mp4")
    ton_spannung("speer", D, SCHNITTE + [D - .9], wav)          # nur Stimme + Musik (keine Geraeusche)
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
