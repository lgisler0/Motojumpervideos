"""Schnitt Stratosphaeren-Sprung (Alan Eustace): Blender-Bilder -> 1080x1920/60fps + Hoehenzaehler, Badges, Untertitel, Ton."""
import os, subprocess, math
import cairo
from rk_basis import *

HIER = os.path.dirname(os.path.abspath(__file__))
U = Untertitel("sprung"); D = 30.5
RFPS = 15
ALTMAX = 41422.0


def hoehe(t):
    if 5.86 <= t < 7.8:
        return 30 * ease((t - 6.3) / 1.5) ** 1.3
    if 7.8 <= t < 9.74:
        k = (t - 7.8) / 1.94; return 30 + (ALTMAX - 30) * (k ** 1.6 * (3 - 2 * k))
    return None


def overlay(ctx, t):
    lg = cairo.LinearGradient(0, H - 640, 0, H); lg.add_color_stop_rgba(0, 0, 0, 0, 0); lg.add_color_stop_rgba(1, 0, 0, 0, .5)
    ctx.set_source(lg); ctx.rectangle(0, H - 640, W, 640); ctx.fill()
    rg = cairo.RadialGradient(W / 2, H / 2, H * .35, W / 2, H / 2, H * .75)
    rg.add_color_stop_rgba(0, 0, 0, 0, 0); rg.add_color_stop_rgba(1, 0, 0, 0, .4); ctx.set_source(rg); ctx.paint()
    ha = fenster(t, -1, 2.0, 0, .25) + fenster(t, D - .4, 99, .25, 0)
    if ha:
        lg = cairo.LinearGradient(0, 0, 0, 560); lg.add_color_stop_rgba(0, 0, 0, 0, .55 * ha); lg.add_color_stop_rgba(1, 0, 0, 0, 0)
        ctx.set_source(lg); ctx.rectangle(0, 0, W, 560); ctx.fill()
        fs.text(ctx, "1 JOB:", W / 2, 260, 96, WEISS, .1, alpha=ha)
        fs.text(ctx, "JUMP FROM SPACE", W / 2, 370, 92, GELB, .1, alpha=ha)
    badge(ctx, "2014", W / 2, 300, fenster(t, 4.05, 5.8), f=WEISS, groesse=44)
    h = hoehe(t)
    if h is not None:
        a = fenster(t, 6.0, 9.9, .25, .15)
        badge(ctx, f"{int(round(h / 10) * 10 if h < ALTMAX - 5 else ALTMAX):,} m".replace(",", ","), W / 2, 300, a, f=GELB, groesse=50)
    badge(ctx, "41,422 m", W / 2, 300, fenster(t, 12.0, 15.1), f=GELB, groesse=50)
    badge(ctx, "4 MIN 27 S FREEFALL", W / 2, 300, fenster(t, 16.35, 18.7), f=WEISS, groesse=44)
    badge(ctx, "≈ 1,300 KM/H", W / 2, 300, fenster(t, 18.85, 23.6), f=GELB, groesse=50)
    rekordlabel(ctx, fenster(t, 27.6, D - .45))
    U.zeichne(ctx, t)


def main():
    liste = os.path.join(HIER, "_spliste.txt"); n = int(round(D * RFPS))
    with open(liste, "w") as f:
        for i in range(n):
            f.write(f"file 'spframes/sprung_{i:04d}.png'\nduration {1 / RFPS}\n")
        f.write(f"file 'spframes/sprung_{n - 1:04d}.png'\n")
    basis = os.path.join(HIER, "_spbasis.mp4")
    if not os.path.exists(basis):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", liste,
                        "-vf", f"fps={RFPS},minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=fdiff:scd_threshold=6,scale=1080:1920:flags=lanczos,unsharp=5:5:0.5,noise=alls=5:allf=t",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", basis], check=True, cwd=HIER)
    wav = os.path.join(HIER, "_sprung.wav"); out = os.path.join(HIER, "videos", "rekord_sprung_3d.mp4")
    ton_spannung("sprung", D, [1.84, 4.0, 5.86, 7.8, 9.74, 10.86, 11.98, 13.6, 15.18, 16.22, 18.78, 21.62, 23.74, 25.58, 27.54, D - .9], wav)
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
