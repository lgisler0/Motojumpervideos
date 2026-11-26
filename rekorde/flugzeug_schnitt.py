"""Schnitt Flugzeug ziehen 188,83 t (Kevin Fast): Blender-Bilder -> 1080x1920/60fps + Badges, Untertitel. Ton: nur Stimme + Musik."""
import os, subprocess, math
import cairo
from rk_basis import *

HIER = os.path.dirname(os.path.abspath(__file__))
U = Untertitel("flugzeug"); D = 27.6
RFPS = 15
SCHNITTE = [1.3, 2.5, 3.6, 5.3, 7.3, 9.2, 11.7, 15.0, 18.9, 23.2]


def overlay(ctx, t):
    lg = cairo.LinearGradient(0, H - 640, 0, H); lg.add_color_stop_rgba(0, 0, 0, 0, 0); lg.add_color_stop_rgba(1, 0, 0, 0, .5)
    ctx.set_source(lg); ctx.rectangle(0, H - 640, W, 640); ctx.fill()
    ha = fenster(t, -1, 1.4, 0, .2) + fenster(t, D - .4, 99, .25, 0)
    if ha:
        lg = cairo.LinearGradient(0, 0, 0, 560); lg.add_color_stop_rgba(0, 0, 0, 0, .55 * ha); lg.add_color_stop_rgba(1, 0, 0, 0, 0)
        ctx.set_source(lg); ctx.rectangle(0, 0, W, 560); ctx.fill()
        fs.text(ctx, "1 JOB:", W / 2, 260, 96, WEISS, .1, alpha=ha)
        fs.text(ctx, "PULL A PLANE", W / 2, 370, 84, GELB, .1, alpha=ha)
    badge(ctx, "HOW HEAVY?", W / 2, 300, fenster(t, 2.55, 3.55), f=GELB, groesse=64)
    badge(ctx, "CANADA \u00b7 2009", W / 2, 300, fenster(t, 3.65, 5.25), f=WEISS, groesse=48)
    badge(ctx, "188.83 TONNES", W / 2, 300, fenster(t, 7.35, 9.15), f=GELB, groesse=70)
    badge(ctx, "\u2248 150 CARS", W / 2, 300, fenster(t, 9.25, 11.65), f=WEISS, groesse=64)
    a_ = fenster(t, 18.95, 23.15, .1, .15)
    if a_ > 0:
        ts = 64.0 + (t - 18.9) / 4.3 * 13.0
        z = min(76, ts); m_ = 8.8 * (min(1, ts / 76) ** 1.45)
        badge(ctx, f"{int(z // 60)}:{int(z % 60):02d}  \u00b7  {m_:.1f} m", W / 2, 300, a_, f=GELB if z >= 76 else WEISS, groesse=60)
    badge(ctx, "HEAVIEST AIRCRAFT PULLED", W / 2, 300, fenster(t, 23.25, D - .45), f=GELB, groesse=44)
    rekordlabel(ctx, fenster(t, 23.25, D - .45))
    U.zeichne(ctx, t)


def main():
    liste = os.path.join(HIER, "_zug_liste.txt"); n = int(round(D * RFPS))
    with open(liste, "w") as f:
        for i in range(n):
            f.write(f"file 'zugframes/flugzeug_{i:04d}.png'\nduration {1 / RFPS}\n")
        f.write(f"file 'zugframes/flugzeug_{n - 1:04d}.png'\n")
    basis = os.path.join(HIER, "_zugbasis.mp4")
    if not os.path.exists(basis):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", liste,
                        "-vf", f"fps={RFPS},minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=fdiff:scd_threshold=6,scale=1080:1920:flags=lanczos,unsharp=5:5:0.4,noise=alls=4:allf=t",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", basis], check=True, cwd=HIER)
    wav = os.path.join(HIER, "_flugzeug.wav"); out = os.path.join(HIER, "videos", "rekord_flugzeug_3d.mp4")
    ton_spannung("flugzeug", D, SCHNITTE + [D - .9], wav)          # nur Stimme + Musik (keine Geraeusche)
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
