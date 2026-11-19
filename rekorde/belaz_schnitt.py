"""Schnitt BelAZ 75710: Blender-Bilder -> 1080x1920/60fps + Zahlen, Badges, Untertitel, Ton."""
import os, subprocess, math
import cairo
from rk_basis import *

HIER = os.path.dirname(os.path.abspath(__file__))
U = Untertitel("belaz"); D = 30.5
t_name, t_mass, t_reifen, t_leer, t_last, t_autos, t_gwr, t_ende = 3.2, 5.66, 9.6, 15.04, 18.82, 22.56, 24.94, 28.7
RFPS = 15


def gross(ctx, oben, unten, a, go=140):
    if a:
        fs.text(ctx, oben, W / 2, 290, go, GELB, .1, alpha=a)
        fs.text(ctx, unten, W / 2, 390, 40, WEISS, .14, alpha=a)


def overlay(ctx, t):
    lg = cairo.LinearGradient(0, H - 640, 0, H); lg.add_color_stop_rgba(0, 0, 0, 0, 0); lg.add_color_stop_rgba(1, 0, 0, 0, .5)
    ctx.set_source(lg); ctx.rectangle(0, H - 640, W, 640); ctx.fill()
    lg = cairo.LinearGradient(0, 0, 0, 560); lg.add_color_stop_rgba(0, 0, 0, 0, .45); lg.add_color_stop_rgba(1, 0, 0, 0, 0)
    ctx.set_source(lg); ctx.rectangle(0, 0, W, 560); ctx.fill()
    za = fenster(t, -1, t_name, 0, .3) + fenster(t, D - .45, 99, .25, 0)
    zahlkarte(ctx, "450 t", "BIGGEST DUMP TRUCK", za, pop=1 - ease((t - D + .45) / .3) if t > D - .45 else 0)
    badge(ctx, "BELAZ 75710 · BELARUS", W / 2, 300, fenster(t, t_name, t_mass - .1), f=GELB)
    gross(ctx, "20.6 m", "LONG · 8.17 m TALL · 9.75 m WIDE", fenster(t, t_mass, t_reifen - .1))
    gross(ctx, "4 m", "TALL TIRES · 8 OF THEM", fenster(t, t_reifen, t_leer - .1), 150)
    gross(ctx, "360 t", "EMPTY WEIGHT", fenster(t, t_leer, t_last - .1), 150)
    la = fenster(t, t_last, t_autos - .1)
    if la:
        n = int(round(450 * ease((t - t_last - .4) / 3.0)))
        gross(ctx, f"+{n} t", "LOADED IN ONE TRIP", la, 150)
    aa = fenster(t, t_autos, t_gwr - .1)
    if aa:
        n = int(round(300 * ease((t - t_autos - .1) / 1.4)))
        gross(ctx, f"= {n} CARS", "450 TONNES OF ROCK", aa, 120)
    ga = fenster(t, t_gwr, t_ende + .2)
    badge(ctx, "GUINNESS WORLD RECORDS", W / 2, 270, ga, f=WEISS, groesse=38)
    if ga:
        fs.text(ctx, "LARGEST TWO-AXLE", W / 2, 380, 72, GELB, .1, alpha=ga)
        fs.text(ctx, "DUMP TRUCK", W / 2, 460, 72, GELB, .1, alpha=ga)
    U.zeichne(ctx, t)


def main():
    liste = os.path.join(HIER, "_bzliste.txt"); n = int(round(D * RFPS))
    with open(liste, "w") as f:
        for i in range(n):
            f.write(f"file 'bzframes/belaz_{i:04d}.png'\nduration {1 / RFPS}\n")
        f.write(f"file 'bzframes/belaz_{n - 1:04d}.png'\n")
    basis = os.path.join(HIER, "_bzbasis.mp4")
    if not os.path.exists(basis):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", liste,
                        "-vf", f"fps={RFPS},minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,scale=1080:1920:flags=lanczos,unsharp=5:5:0.5,noise=alls=5:allf=t",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", basis], check=True, cwd=HIER)
    wav = os.path.join(HIER, "_bz.wav"); out = os.path.join(HIER, "videos", "rekord_belaz_3d.mp4")
    ton_spannung("belaz", D, [t_name, t_mass, t_reifen, t_leer, t_last, t_autos, t_gwr, D - .9], wav)
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
