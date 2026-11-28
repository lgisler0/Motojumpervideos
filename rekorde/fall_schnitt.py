"""Schnitt Wasserfall im Kajak 57,6 m (Tyler Bradt): Blender-Bilder -> 1080x1920/60fps + Badges, Untertitel. Ton: nur Stimme + Musik."""
import os, subprocess, math
import cairo
from rk_basis import *

HIER = os.path.dirname(os.path.abspath(__file__))
U = Untertitel("fall"); D = 25.2
RFPS = 15
SCHNITTE = [1.6, 3.0, 4.3, 6.9, 8.9, 11.5, 13.3, 15.3, 17.4, 19.3, 21.2]


def overlay(ctx, t):
    lg = cairo.LinearGradient(0, H - 640, 0, H); lg.add_color_stop_rgba(0, 0, 0, 0, 0); lg.add_color_stop_rgba(1, 0, 0, 0, .5)
    ctx.set_source(lg); ctx.rectangle(0, H - 640, W, 640); ctx.fill()
    ha = fenster(t, -1, 1.4, 0, .2) + fenster(t, D - .4, 99, .25, 0)
    if ha:
        lg = cairo.LinearGradient(0, 0, 0, 560); lg.add_color_stop_rgba(0, 0, 0, 0, .55 * ha); lg.add_color_stop_rgba(1, 0, 0, 0, 0)
        ctx.set_source(lg); ctx.rectangle(0, 0, W, 560); ctx.fill()
        fs.text(ctx, "1 JOB:", W / 2, 260, 96, WEISS, .1, alpha=ha)
        fs.text(ctx, "PADDLE OFF A WATERFALL", W / 2, 370, 66, GELB, .1, alpha=ha)
    badge(ctx, "HOW HIGH?", W / 2, 300, fenster(t, 3.05, 4.25), f=GELB, groesse=68)
    badge(ctx, "PALOUSE FALLS \u00b7 USA \u00b7 2009", W / 2, 300, fenster(t, 4.35, 6.85), f=WEISS, groesse=44)
    badge(ctx, "57.6 m", W / 2, 300, fenster(t, 9.0, 11.45), f=GELB, groesse=90)
    badge(ctx, "NIAGARA: 51 m", W / 2, 300, fenster(t, 11.55, 13.25), f=WEISS, groesse=56)
    a_ = fenster(t, 15.35, 17.35, .08, .1)
    if a_ > 0:
        ts = 10.6 + (13.2 - 10.6) * (t - 15.3) / 2.1
        ff = min(3.4, max(0.0, ts - 10.0))
        badge(ctx, f"FREE FALL {ff:.1f} s", W / 2, 300, a_, f=GELB if ff >= 3.4 else WEISS, groesse=60)
    badge(ctx, "TALLEST WATERFALL IN A KAYAK", W / 2, 300, fenster(t, 21.3, D - .45), f=GELB, groesse=40)
    rekordlabel(ctx, fenster(t, 21.3, D - .45))
    U.zeichne(ctx, t)


def main():
    liste = os.path.join(HIER, "_wf_liste.txt"); n = int(round(D * RFPS))
    with open(liste, "w") as f:
        for i in range(n):
            f.write(f"file 'wfframes/fall_{i:04d}.png'\nduration {1 / RFPS}\n")
        f.write(f"file 'wfframes/fall_{n - 1:04d}.png'\n")
    basis = os.path.join(HIER, "_wfbasis.mp4")
    if not os.path.exists(basis):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", liste,
                        "-vf", f"fps={RFPS},minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=fdiff:scd_threshold=6,scale=1080:1920:flags=lanczos,unsharp=5:5:0.4,noise=alls=4:allf=t",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", basis], check=True, cwd=HIER)
    wav = os.path.join(HIER, "_fall.wav"); out = os.path.join(HIER, "videos", "rekord_fall_3d.mp4")
    ton_spannung("fall", D, SCHNITTE + [D - .9], wav)          # nur Stimme + Musik (keine Geraeusche)
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
