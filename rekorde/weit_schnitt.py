"""Schnitt Weitsprung 8,95 m (Mike Powell): Blender-Bilder -> 1080x1920/60fps + Badges, Publikum/Klirren/Aufprall, Untertitel."""
import os, subprocess, math
import cairo
from rk_basis import *

HIER = os.path.dirname(os.path.abspath(__file__))
U = Untertitel("weit"); D = 23.2
RFPS = 15
SCHNITTE = [1.3, 3.4, 4.5, 6.6, 7.7, 8.75, 10.2, 12.4, 14.3, 16.6, 18.0]


def geraeusche(wav):
    import wave, numpy as np
    with wave.open(wav, "rb") as w:
        sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    n = len(x); t = np.arange(n) / sr; rng = np.random.default_rng(21)
    k = int(sr / 1400); menge = np.convolve(rng.normal(0, 1, n), np.ones(k) / k, "same")
    pegel = .07 + .55 * np.exp(-np.clip(t - 9.52, 0, None) / 1.4) * (t >= 9.52) * (t < 10.2) \
        + .6 * np.exp(-np.clip(t - 12.4, 0, None) / 2.5) * (t >= 12.4)
    pegel[t < 1.3] = .18
    x += menge * pegel * 2.0
    def schlag(t0, st, f0=90, d=30, rausch=.6):
        i0 = int(t0 * sr); L = int(.35 * sr); tt = np.arange(L) / sr
        s_ = (np.sin(2 * np.pi * f0 * tt) + rng.normal(0, 1, L) * rausch) * np.exp(-tt * d)
        x[i0:i0 + L] += s_[:max(0, min(L, n - i0))] * st
    tk = 4.6; dt = .6                                   # Publikum klatscht im Rhythmus
    while tk < 8.5:
        schlag(tk, .16, 1200, 45, 2.0); tk += dt; dt = max(.28, dt * .92)
    tk = 5.8; dt = .42                                  # Schritte, immer schneller
    while tk < 8.55:
        schlag(tk, .22, 120, 40, .8); tk += dt; dt = max(.2, dt * .94)
    schlag(8.6, .5, 70, 16, .6)                         # Absprung vom Balken
    for tl in (9.52,):                                  # Landung im Sand: weiches Rauschen
        i0 = int(tl * sr); L = int(.6 * sr); tt = np.arange(L) / sr
        k2 = int(sr / 3000); sa = np.convolve(rng.normal(0, 1, L), np.ones(k2) / k2, "same") * np.exp(-tt * 7)
        x[i0:i0 + L] += sa * .9
        schlag(tl, .5, 55, 12, .3)
    x = x / np.abs(x).max() * .92
    with wave.open(wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((x * 32767).astype(np.int16).tobytes())


def overlay(ctx, t):
    lg = cairo.LinearGradient(0, H - 640, 0, H); lg.add_color_stop_rgba(0, 0, 0, 0, 0); lg.add_color_stop_rgba(1, 0, 0, 0, .5)
    ctx.set_source(lg); ctx.rectangle(0, H - 640, W, 640); ctx.fill()
    ha = fenster(t, -1, 1.3, 0, .2) + fenster(t, D - .4, 99, .25, 0)
    if ha:
        lg = cairo.LinearGradient(0, 0, 0, 560); lg.add_color_stop_rgba(0, 0, 0, 0, .55 * ha); lg.add_color_stop_rgba(1, 0, 0, 0, 0)
        ctx.set_source(lg); ctx.rectangle(0, 0, W, 560); ctx.fill()
        fs.text(ctx, "1 JOB:", W / 2, 260, 96, WEISS, .1, alpha=ha)
        fs.text(ctx, "JUMP INTO SAND", W / 2, 370, 88, GELB, .1, alpha=ha)
    badge(ctx, "HOW FAR?", W / 2, 300, fenster(t, 3.4, 4.45), f=GELB, groesse=56)
    badge(ctx, "TOKYO \u00b7 1991", W / 2, 300, fenster(t, 4.55, 6.55), f=WEISS, groesse=44)
    a_ = fenster(t, 10.2, 12.35, .1, .15)
    if a_ > 0:
        badge(ctx, f"{min(.92, (t - 10.2) / 2.2 * .92):.2f} s IN THE AIR", W / 2, 300, a_, f=WEISS, groesse=48)
    b_ = fenster(t, 12.45, 14.25, .1, .2)
    if b_ > 0:
        m = 8.95 * ease((t - 12.45) / .8); badge(ctx, f"{m:.2f} m", W / 2, 300, b_, f=GELB if m >= 8.949 else WEISS, groesse=84)
    badge(ctx, "\u2248 2 CARS LONG", W / 2, 300, fenster(t, 14.35, 16.55), f=WEISS, groesse=48)
    badge(ctx, "OLD RECORD: 8.90 m (1968)", W / 2, 300, fenster(t, 18.0, 20.6), f=WEISS, groesse=40)
    badge(ctx, "UNBEATEN SINCE 1991", W / 2, 300, fenster(t, 20.7, D - .45), f=GELB, groesse=50)
    rekordlabel(ctx, fenster(t, 18.0, D - .45))
    U.zeichne(ctx, t)


def main():
    liste = os.path.join(HIER, "_we_liste.txt"); n = int(round(D * RFPS))
    with open(liste, "w") as f:
        for i in range(n):
            f.write(f"file 'weframes/weit_{i:04d}.png'\nduration {1 / RFPS}\n")
        f.write(f"file 'weframes/weit_{n - 1:04d}.png'\n")
    basis = os.path.join(HIER, "_webasis.mp4")
    if not os.path.exists(basis):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", liste,
                        "-vf", f"fps={RFPS},minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=fdiff:scd_threshold=6,scale=1080:1920:flags=lanczos,unsharp=5:5:0.4,noise=alls=4:allf=t",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", basis], check=True, cwd=HIER)
    wav = os.path.join(HIER, "_weit.wav"); out = os.path.join(HIER, "videos", "rekord_weit_3d.mp4")
    ton_spannung("weit", D, SCHNITTE + [D - .9], wav)
    geraeusche(wav)
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
