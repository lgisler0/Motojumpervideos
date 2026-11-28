"""Schnitt Speedski 255,5 km/h (Simon Billy) - Ende laeuft nahtlos in den Anfang (Loop): Blender-Bilder -> 1080x1920/60fps + Badges, Untertitel. Ton: nur Stimme + Musik."""
import os, subprocess, math
import cairo
from rk_basis import *

HIER = os.path.dirname(os.path.abspath(__file__))
U = Untertitel("speed"); D = 28.0
LOOP = 27.3
RFPS = 15
SCHNITTE = [1.5, 2.6, 3.7, 5.9, 8.2, 10.4, 12.4, 14.2, 15.4, 18.4, 20.4, 22.0, 24.4]


def overlay(ctx, t):
    lg = cairo.LinearGradient(0, H - 640, 0, H); lg.add_color_stop_rgba(0, 0, 0, 0, 0); lg.add_color_stop_rgba(1, 0, 0, 0, .5)
    ctx.set_source(lg); ctx.rectangle(0, H - 640, W, 640); ctx.fill()
    ha = fenster(t, -1, 1.4, 0, .2) + fenster(t, LOOP, 99, .0, 0)      # Titel am Anfang und im Loop-Ende gleich
    if ha:
        lg = cairo.LinearGradient(0, 0, 0, 560); lg.add_color_stop_rgba(0, 0, 0, 0, .55 * ha); lg.add_color_stop_rgba(1, 0, 0, 0, 0)
        ctx.set_source(lg); ctx.rectangle(0, 0, W, 560); ctx.fill()
        fs.text(ctx, "1 JOB:", W / 2, 260, 96, WEISS, .1, alpha=ha)
        fs.text(ctx, "SKI STRAIGHT DOWN", W / 2, 370, 76, GELB, .1, alpha=ha)
    badge(ctx, "HOW FAST?", W / 2, 300, fenster(t, 2.65, 3.65), f=GELB, groesse=68)
    badge(ctx, "VARS \u00b7 FRANCE \u00b7 2023", W / 2, 300, fenster(t, 3.75, 5.85), f=WEISS, groesse=48)
    badge(ctx, "98 % SLOPE \u2248 45\u00b0", W / 2, 300, fenster(t, 8.25, 10.35), f=GELB, groesse=60)
    badge(ctx, "SKIS: 2.40 m", W / 2, 300, fenster(t, 12.45, 14.15), f=WEISS, groesse=60)
    a_ = fenster(t, 15.45, 18.35, .08, .1)
    if a_ > 0:
        ts = 3.2 + 3.0 * (t - 15.4) / 3.0
        v = 73.59 * (1 - math.exp(-ts / 3.3)) * 3.6
        badge(ctx, f"{v:.0f} km/h", W / 2, 300, a_, f=GELB if v >= 200 else WEISS, groesse=76)
    badge(ctx, "255.5 km/h", W / 2, 300, fenster(t, 22.05, 24.35), f=GELB, groesse=90)
    badge(ctx, "FASTEST MAN ON SKIS", W / 2, 300, fenster(t, 24.45, LOOP - .05, .1, .05), f=GELB, groesse=50)
    rekordlabel(ctx, fenster(t, 24.45, LOOP - .05, .1, .05))
    U.zeichne(ctx, t)


def main():
    liste = os.path.join(HIER, "_sk_liste.txt"); n = int(round(D * RFPS))
    with open(liste, "w") as f:
        for i in range(n):
            f.write(f"file 'skframes/speed_{i:04d}.png'\nduration {1 / RFPS}\n")
        f.write(f"file 'skframes/speed_{n - 1:04d}.png'\n")
    basis = os.path.join(HIER, "_skbasis.mp4")
    if not os.path.exists(basis):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", liste,
                        "-vf", f"fps={RFPS},minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=fdiff:scd_threshold=6,scale=1080:1920:flags=lanczos,unsharp=5:5:0.4,noise=alls=4:allf=t",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", basis], check=True, cwd=HIER)
    wav = os.path.join(HIER, "_speed.wav"); out = os.path.join(HIER, "videos", "rekord_speed_3d.mp4")
    ton_spannung("speed", D, SCHNITTE + [LOOP], wav)          # nur Stimme + Musik (keine Geraeusche)
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
