"""Schnitt Hochsprung 2,45 m (Javier Sotomayor): Blender-Bilder -> 1080x1920/60fps + Badges, Publikum/Klirren/Aufprall, Untertitel."""
import os, subprocess, math
import cairo
from rk_basis import *

HIER = os.path.dirname(os.path.abspath(__file__))
U = Untertitel("hoch"); D = 23.8
RFPS = 15
SCHNITTE = [1.3, 3.2, 4.6, 7.3, 8.4, 9.6, 10.8, 12.5, 16.1, 18.2, 20.1]


def geraeusche(wav):
    import wave, numpy as np
    with wave.open(wav, "rb") as w:
        sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    n = len(x); t = np.arange(n) / sr; rng = np.random.default_rng(21)
    k = int(sr / 1400); menge = np.convolve(rng.normal(0, 1, n), np.ones(k) / k, "same")
    pegel = .07 + .5 * np.exp(-np.clip(t - 10.75, 0, None) / 1.2) * (t >= 10.75) * (t < 12.5) \
        + .6 * np.exp(-np.clip(t - 16.25, 0, None) / 2.2) * (t >= 16.25)
    pegel[t < 1.3] = .18
    x += menge * pegel * 2.0
    def schlag(t0, st, f0=90, d=30, rausch=.6):
        i0 = int(t0 * sr); L = int(.35 * sr); tt = np.arange(L) / sr
        s_ = (np.sin(2 * np.pi * f0 * tt) + rng.normal(0, 1, L) * rausch) * np.exp(-tt * d)
        x[i0:i0 + L] += s_[:max(0, min(L, n - i0))] * st
    # Klatschen des Publikums im Anlauf-Rhythmus (wird schneller)
    tk = 5.2; dt = .62
    while tk < 9.5:
        schlag(tk, .16, 1200, 45, 2.0); tk += dt; dt = max(.3, dt * .93)
    # Schritte auf Tartan
    for i in range(8):
        schlag(7.35 + i * (2.25 / 8) * (1 - .04 * i), .25, 120, 40, .8)
    schlag(9.58, .45, 70, 18, .5)                      # Absprung
    for tl in (10.75, 16.25):                            # Matte
        schlag(tl, .8, 45, 7, 1.0)
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
        fs.text(ctx, "JUMP OVER A BAR", W / 2, 370, 84, GELB, .1, alpha=ha)
    badge(ctx, "HOW HIGH?", W / 2, 300, fenster(t, 3.2, 4.55), f=GELB, groesse=56)
    badge(ctx, "SALAMANCA, SPAIN \u00b7 1993", W / 2, 300, fenster(t, 4.65, 7.25), f=WEISS, groesse=42)
    badge(ctx, "BAR: 2.45 m", W / 2, 300, fenster(t, 13.1, 16.05), f=WEISS, groesse=48)
    badge(ctx, "HIM: 1.93 m", W / 2, 410, fenster(t, 13.9, 16.05), f=WEISS, groesse=48)
    badge(ctx, "+52 cm", W / 2, 530, fenster(t, 14.6, 16.05), f=GELB, groesse=64)
    badge(ctx, "2.45 m", W / 2, 300, fenster(t, 16.6, 18.15), f=GELB, groesse=84)
    badge(ctx, "UNBEATEN SINCE 1993", W / 2, 300, fenster(t, 20.9, D - .45), f=GELB, groesse=50)
    rekordlabel(ctx, fenster(t, 20.1, D - .45))
    U.zeichne(ctx, t)


def main():
    liste = os.path.join(HIER, "_ho_liste.txt"); n = int(round(D * RFPS))
    with open(liste, "w") as f:
        for i in range(n):
            f.write(f"file 'hoframes/hoch_{i:04d}.png'\nduration {1 / RFPS}\n")
        f.write(f"file 'hoframes/hoch_{n - 1:04d}.png'\n")
    basis = os.path.join(HIER, "_hobasis.mp4")
    if not os.path.exists(basis):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", liste,
                        "-vf", f"fps={RFPS},minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=fdiff:scd_threshold=6,scale=1080:1920:flags=lanczos,unsharp=5:5:0.4,noise=alls=4:allf=t",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", basis], check=True, cwd=HIER)
    wav = os.path.join(HIER, "_hoch.wav"); out = os.path.join(HIER, "videos", "rekord_hoch_3d.mp4")
    ton_spannung("hoch", D, SCHNITTE + [D - .9], wav)
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
