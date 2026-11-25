"""Schnitt Speed-Klettern 5,99 s (Emma Hunt): Blender-Bilder -> 1080x1920/60fps + Badges, Publikum/Klirren/Aufprall, Untertitel."""
import os, subprocess, math
import cairo
from rk_basis import *

HIER = os.path.dirname(os.path.abspath(__file__))
U = Untertitel("kletter"); D = 24.7
RFPS = 15
SCHNITTE = [1.4, 3.6, 4.7, 7.2, 9.8, 11.0, 12.6, 14.2, 15.8, 17.4, 19.2, 20.5]


def geraeusche(wav):
    import wave, numpy as np
    with wave.open(wav, "rb") as w:
        sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    n = len(x); t = np.arange(n) / sr; rng = np.random.default_rng(21)
    k = int(sr / 1400); menge = np.convolve(rng.normal(0, 1, n), np.ones(k) / k, "same")
    pegel = .08 + .1 * ((t > 10.85) & (t < 16.84)) + .6 * np.exp(-np.clip(t - 16.84, 0, None) / 1.6) * (t >= 16.84) * (t < 17.4) \
        + .55 * np.exp(-np.clip(t - 19.2, 0, None) / 3.0) * (t >= 19.2)
    pegel[t < 1.4] = .2
    x += menge * pegel * 2.0
    def ton(t0, f0, dauer, st):
        i0 = int(t0 * sr); L = int(dauer * sr); tt = np.arange(L) / sr
        s_ = np.sin(2 * np.pi * f0 * tt) * np.minimum(1, (dauer - tt) * 30)
        x[i0:i0 + L] += s_[:max(0, min(L, n - i0))] * st
    def schlag(t0, st, f0=90, d=30, rausch=.6):
        i0 = int(t0 * sr); L = int(.3 * sr); tt = np.arange(L) / sr
        s_ = (np.sin(2 * np.pi * f0 * tt) + rng.normal(0, 1, L) * rausch) * np.exp(-tt * d)
        x[i0:i0 + L] += s_[:max(0, min(L, n - i0))] * st
    for k_, tt0 in enumerate((9.85, 10.35)):              # Startsignal: zwei kurze, ein langer Ton
        ton(tt0, 880, .12, .25)
    ton(10.85, 1320, .3, .3)
    tk = 10.95                                           # Griffe: dumpfe Klopfer, immer schneller
    while tk < 16.8:
        schlag(tk, .22, 140, 45, 1.0); tk += .19 + .05 * np.sin(tk * 3)
    ton(16.84, 1760, .45, .35)                           # Top-Taster
    schlag(16.84, .5, 300, 20, 1.5)
    x = x / np.abs(x).max() * .92
    with wave.open(wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((x * 32767).astype(np.int16).tobytes())


def overlay(ctx, t):
    lg = cairo.LinearGradient(0, H - 640, 0, H); lg.add_color_stop_rgba(0, 0, 0, 0, 0); lg.add_color_stop_rgba(1, 0, 0, 0, .5)
    ctx.set_source(lg); ctx.rectangle(0, H - 640, W, 640); ctx.fill()
    ha = fenster(t, -1, 1.4, 0, .2) + fenster(t, D - .4, 99, .25, 0)
    if ha:
        lg = cairo.LinearGradient(0, 0, 0, 560); lg.add_color_stop_rgba(0, 0, 0, 0, .55 * ha); lg.add_color_stop_rgba(1, 0, 0, 0, 0)
        ctx.set_source(lg); ctx.rectangle(0, 0, W, 560); ctx.fill()
        fs.text(ctx, "1 JOB:", W / 2, 260, 96, WEISS, .1, alpha=ha)
        fs.text(ctx, "CLIMB A 15 m WALL", W / 2, 370, 80, GELB, .1, alpha=ha)
    badge(ctx, "HOW FAST?", W / 2, 300, fenster(t, 3.6, 4.65), f=GELB, groesse=56)
    badge(ctx, "KRAK\u00d3W \u00b7 2026", W / 2, 300, fenster(t, 4.75, 7.15), f=WEISS, groesse=44)
    badge(ctx, "15 m \u2248 5 FLOORS", W / 2, 300, fenster(t, 7.3, 9.75), f=WEISS, groesse=48)
    a_ = fenster(t, 10.85, 17.35, .05, .15)
    if a_ > 0:
        z = min(5.99, max(0, t - 10.85)); badge(ctx, f"{z:.2f} s", W / 2, 300, a_, f=GELB if z >= 5.99 else WEISS, groesse=84)
    badge(ctx, "5.99 s", W / 2, 300, fenster(t, 17.45, 20.45), f=GELB, groesse=84)
    badge(ctx, "FIRST WOMAN UNDER 6 s", W / 2, 300, fenster(t, 20.6, D - .45), f=GELB, groesse=46)
    rekordlabel(ctx, fenster(t, 17.45, D - .45))
    U.zeichne(ctx, t)


def main():
    liste = os.path.join(HIER, "_kl_liste.txt"); n = int(round(D * RFPS))
    with open(liste, "w") as f:
        for i in range(n):
            f.write(f"file 'klframes/kletter_{i:04d}.png'\nduration {1 / RFPS}\n")
        f.write(f"file 'klframes/kletter_{n - 1:04d}.png'\n")
    basis = os.path.join(HIER, "_klbasis.mp4")
    if not os.path.exists(basis):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", liste,
                        "-vf", f"fps={RFPS},minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=fdiff:scd_threshold=6,scale=1080:1920:flags=lanczos,unsharp=5:5:0.4,noise=alls=4:allf=t",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", basis], check=True, cwd=HIER)
    wav = os.path.join(HIER, "_kletter.wav"); out = os.path.join(HIER, "videos", "rekord_kletter_3d.mp4")
    ton_spannung("kletter", D, SCHNITTE + [D - .9], wav)
    pass  # Loris 25.11.: keine Geraeusche-Effekte
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
