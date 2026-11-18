"""Schnitt: Blender-Bilder (15fps, halbe Groesse) -> 1080x1920/60fps + Zahlen, Badges, Untertitel, Ton."""
import os, subprocess
import cairo
from rk_basis import *

HIER = os.path.dirname(os.path.abspath(__file__))
U = Untertitel("burj"); D = U.ende() + .35
t_name, t_seit, t_eiffel, t_saudi, t_jeddah, t_bis = 2.3, 4.6, 7.7, 10.8, 14.5, 19.0
RFPS = 15


def overlay(ctx, t):
    # leichte Vignette + Verlaeufe fuer Lesbarkeit
    lg = cairo.LinearGradient(0, H - 640, 0, H); lg.add_color_stop_rgba(0, 0, 0, 0, 0); lg.add_color_stop_rgba(1, 0, 0, 0, .55)
    ctx.set_source(lg); ctx.rectangle(0, H - 640, W, 640); ctx.fill()
    lg = cairo.LinearGradient(0, 0, 0, 560); lg.add_color_stop_rgba(0, 0, 0, 0, .5); lg.add_color_stop_rgba(1, 0, 0, 0, 0)
    ctx.set_source(lg); ctx.rectangle(0, 0, W, 560); ctx.fill()
    za = fenster(t, -1, t_name, 0, .3) + fenster(t, D - .45, 99, .25, 0)
    zahlkarte(ctx, "828 m", "TALLEST BUILDING ON EARTH", za, pop=1 - ease((t - D + .45) / .3) if t > D - .45 else 0)
    badge(ctx, "BURJ KHALIFA · DUBAI", W / 2, 300, fenster(t, t_name, t_seit - .1), f=GELB)
    badge(ctx, "TALLEST SINCE 2010", W / 2, 300, fenster(t, t_seit, t_eiffel - .2), f=WEISS)
    badge(ctx, "MORE THAN 2× THE EIFFEL TOWER", W / 2, 300, fenster(t, t_eiffel + .3, t_saudi - .1), f=GELB)
    badge(ctx, "EIFFEL TOWER · 330 m", W * .3, 1180, fenster(t, t_eiffel + .8, t_saudi - .2), f=WEISS, groesse=34)
    badge(ctx, "SAUDI ARABIA · JEDDAH TOWER", W / 2, 300, fenster(t, t_saudi + .3, t_jeddah - .1), f=WEISS)
    badge(ctx, "PLANNED: OVER 1 km · 2028", W / 2, 300, fenster(t, t_jeddah, t_bis), f=GELB)
    U.zeichne(ctx, t)


def main():
    liste = os.path.join(HIER, "_b3liste.txt"); n = int(round(D * RFPS))
    with open(liste, "w") as f:
        for i in range(n):
            f.write(f"file 'b3frames/burj_{i:04d}.png'\nduration {1 / RFPS}\n")
        f.write(f"file 'b3frames/burj_{n - 1:04d}.png'\n")
    basis = os.path.join(HIER, "_b3basis.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", liste,
                    "-vf", f"fps={RFPS},minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,scale=1080:1920:flags=lanczos,unsharp=5:5:0.5,noise=alls=5:allf=t",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", basis], check=True, cwd=HIER)
    wav = os.path.join(HIER, "_b3.wav"); out = os.path.join(HIER, "videos", "rekord_burj_3d.mp4")
    ton("burj", D, [t_name + .4, t_eiffel, t_saudi, D - .8], wav)
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
