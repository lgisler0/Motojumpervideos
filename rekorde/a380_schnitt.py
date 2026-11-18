"""Schnitt A380: Blender-Bilder -> 1080x1920/60fps + Zahlen, Badges, Untertitel, Ton."""
import os, subprocess
import cairo
from rk_basis import *

HIER = os.path.dirname(os.path.abspath(__file__))
U = Untertitel("a380"); D = U.ende() + .25
t_name, t_deck, t_pax, t_start, t_built, t_ende = 2.14, 7.68, 11.0, 15.0, 19.26, 24.36
RFPS = 15


def overlay(ctx, t):
    lg = cairo.LinearGradient(0, H - 640, 0, H); lg.add_color_stop_rgba(0, 0, 0, 0, 0); lg.add_color_stop_rgba(1, 0, 0, 0, .5)
    ctx.set_source(lg); ctx.rectangle(0, H - 640, W, 640); ctx.fill()
    lg = cairo.LinearGradient(0, 0, 0, 560); lg.add_color_stop_rgba(0, 0, 0, 0, .45); lg.add_color_stop_rgba(1, 0, 0, 0, 0)
    ctx.set_source(lg); ctx.rectangle(0, 0, W, 560); ctx.fill()
    za = fenster(t, -1, t_name, 0, .3) + fenster(t, D - .45, 99, .25, 0)
    zahlkarte(ctx, "79.75 m", "WINGSPAN · BIGGEST PASSENGER PLANE", za, pop=1 - ease((t - D + .45) / .3) if t > D - .45 else 0)
    badge(ctx, "AIRBUS A380", W / 2, 300, fenster(t, t_name, t_deck - .1), f=GELB)
    badge(ctx, "2 FULL DECKS · NOSE TO TAIL", W / 2, 300, fenster(t, t_deck, t_pax - .1), f=WEISS)
    pa = fenster(t, t_pax, t_start - .1)
    if pa:
        n = int(round(853 * ease((t - U.zeit("853")) / 1.2))) if t > U.zeit("853") else 0
        fs.text(ctx, f"{n}", W / 2, 290, 150, GELB, .1, alpha=pa)
        fs.text(ctx, "PASSENGERS (CERTIFIED MAX)", W / 2, 390, 44, WEISS, .14, alpha=pa)
    sa = fenster(t, t_start, t_built - .1)
    if sa:
        fs.text(ctx, "575 t", W / 2, 290, 150, GELB, .1, alpha=sa)
        fs.text(ctx, "MAX TAKEOFF WEIGHT", W / 2, 390, 44, WEISS, .14, alpha=sa)
    ba = fenster(t, t_built, t_ende - .1)
    if ba:
        fs.text(ctx, "251", W / 2, 290, 150, GELB, .1, alpha=ba)
        fs.text(ctx, "BUILT · PRODUCTION ENDED 2021" if t > U.zeit("production") - .1 else "EVER BUILT", W / 2, 390, 44, WEISS, .14, alpha=ba)
    U.zeichne(ctx, t)


def main():
    liste = os.path.join(HIER, "_a3liste.txt"); n = int(round(D * RFPS))
    with open(liste, "w") as f:
        for i in range(n):
            f.write(f"file 'a3frames/a380_{i:04d}.png'\nduration {1 / RFPS}\n")
        f.write(f"file 'a3frames/a380_{n - 1:04d}.png'\n")
    basis = os.path.join(HIER, "_a3basis.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", liste,
                    "-vf", f"fps={RFPS},minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,scale=1080:1920:flags=lanczos,unsharp=5:5:0.5,noise=alls=5:allf=t",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", basis], check=True, cwd=HIER)
    wav = os.path.join(HIER, "_a3.wav"); out = os.path.join(HIER, "videos", "rekord_a380_3d.mp4")
    ton("a380", D, [t_deck, t_pax, t_start, t_built, D - .8], wav)
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
