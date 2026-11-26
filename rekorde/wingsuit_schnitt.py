"""Schnitt Wingsuit 550 km/h (Sebastian Alvarez): Blender-Bilder -> 1080x1920/60fps + Badges, Untertitel. Ton: nur Stimme + Musik."""
import os, subprocess, math
import cairo
from rk_basis import *

HIER = os.path.dirname(os.path.abspath(__file__))
U = Untertitel("wingsuit"); D = 27.6
RFPS = 15
SCHNITTE = [1.5, 2.8, 3.8, 5.2, 8.2, 9.9, 11.9, 13.8, 16.5, 20.2, 23.1]


def overlay(ctx, t):
    lg = cairo.LinearGradient(0, H - 640, 0, H); lg.add_color_stop_rgba(0, 0, 0, 0, 0); lg.add_color_stop_rgba(1, 0, 0, 0, .5)
    ctx.set_source(lg); ctx.rectangle(0, H - 640, W, 640); ctx.fill()
    ha = fenster(t, -1, 1.4, 0, .2) + fenster(t, D - .4, 99, .25, 0)
    if ha:
        lg = cairo.LinearGradient(0, 0, 0, 560); lg.add_color_stop_rgba(0, 0, 0, 0, .55 * ha); lg.add_color_stop_rgba(1, 0, 0, 0, 0)
        ctx.set_source(lg); ctx.rectangle(0, 0, W, 560); ctx.fill()
        fs.text(ctx, "1 JOB:", W / 2, 260, 96, WEISS, .1, alpha=ha)
        fs.text(ctx, "FLY A WINGSUIT", W / 2, 370, 80, GELB, .1, alpha=ha)
    badge(ctx, "HOW FAST?", W / 2, 300, fenster(t, 2.85, 3.75), f=GELB, groesse=64)
    badge(ctx, "TENNESSEE \u00b7 USA", W / 2, 300, fenster(t, 3.85, 5.15), f=WEISS, groesse=46)
    badge(ctx, "12,640 m", W / 2, 300, fenster(t, 5.25, 9.85), f=WEISS, groesse=80)
    badge(ctx, "-50 \u00b0C", W / 2, 300, fenster(t, 9.95, 11.85), f=WEISS, groesse=80)
    badge(ctx, "JET STREAM", W / 2, 300, fenster(t, 13.85, 16.45), f=WEISS, groesse=64)
    a_ = fenster(t, 16.55, 20.15, .1, .15)
    if a_ > 0:
        ts = 22.0 + (t - 16.5) / 3.7 * 9.0
        v = 55 + (152.8 - 55) * (lambda x: x * x * (3 - 2 * x))(min(1, max(0, (ts - 1.0) / 30.0)))
        kmh = min(550, v * 3.6)
        badge(ctx, f"{kmh:.0f} km/h", W / 2, 300, a_, f=GELB if kmh >= 549 else WEISS, groesse=84)
    badge(ctx, "53.45 km \u00b7 11:01 min", W / 2, 300, fenster(t, 20.25, 23.05), f=GELB, groesse=52)
    badge(ctx, "FASTEST & FARTHEST WINGSUIT FLIGHT", W / 2, 300, fenster(t, 23.15, D - .45), f=GELB, groesse=36)
    rekordlabel(ctx, fenster(t, 16.55, D - .45))
    U.zeichne(ctx, t)


def main():
    liste = os.path.join(HIER, "_ws_liste.txt"); n = int(round(D * RFPS))
    with open(liste, "w") as f:
        for i in range(n):
            f.write(f"file 'wsframes/wingsuit_{i:04d}.png'\nduration {1 / RFPS}\n")
        f.write(f"file 'wsframes/wingsuit_{n - 1:04d}.png'\n")
    basis = os.path.join(HIER, "_wsbasis.mp4")
    if not os.path.exists(basis):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", liste,
                        "-vf", f"fps={RFPS},minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=fdiff:scd_threshold=6,scale=1080:1920:flags=lanczos,unsharp=5:5:0.4,noise=alls=4:allf=t",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", basis], check=True, cwd=HIER)
    wav = os.path.join(HIER, "_wingsuit.wav"); out = os.path.join(HIER, "videos", "rekord_wingsuit_3d.mp4")
    ton_spannung("wingsuit", D, SCHNITTE + [D - .9], wav)          # nur Stimme + Musik (keine Geraeusche)
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
