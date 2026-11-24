"""Schnitt Kreuzheben 511 kg (Raul Flores): Blender-Bilder -> 1080x1920/60fps + Badges, Publikum/Klirren/Aufprall, Untertitel."""
import os, subprocess, math
import cairo
from rk_basis import *

HIER = os.path.dirname(os.path.abspath(__file__))
U = Untertitel("hebe"); D = 25.8
RFPS = 15
T_ZUG, T_LOS, T_OBEN, T_UNTEN = 10.7, 13.2, 15.6, 20.85
SCHNITTE = [1.4, 3.0, 4.5, 6.9, 7.85, 9.0, 10.6, 11.9, 13.4, 15.3, 17.2, 19.4, 20.7, 22.9]


def geraeusche(wav):
    import wave, numpy as np
    with wave.open(wav, "rb") as w:
        sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    n = len(x); t = np.arange(n) / sr; rng = np.random.default_rng(12)
    # Publikum: gefiltertes Rauschen, Pegel nach Ablauf
    k = int(sr / 1500); menge = np.convolve(rng.normal(0, 1, n), np.ones(k) / k, "same")
    pegel = .05 + .05 * np.clip((t - T_ZUG) / (T_OBEN - T_ZUG), 0, 1) + .55 * np.exp(-np.clip(t - T_OBEN, 0, None) / 1.6) * (t >= T_OBEN) \
        + .45 * np.exp(-np.clip(t - T_UNTEN, 0, None) / 2.5) * (t >= T_UNTEN)
    pegel[t < 1.4] = .2
    x += menge * pegel * 2.0
    # Klirren der Scheiben beim Abheben und Absetzen
    def klirr(t0, st):
        i0 = int(t0 * sr); L = int(.5 * sr); tt = np.arange(L) / sr
        s = sum(np.sin(2 * np.pi * f * tt) * np.exp(-tt * d) for f, d in ((1870, 9), (2730, 12), (3310, 15), (980, 7)))
        x[i0:i0 + L] += (s[:max(0, min(L, n - i0))]) * st
    klirr(T_LOS, .05); klirr(T_UNTEN + .02, .09)
    # Aufprall beim Absetzen
    i0 = int(T_UNTEN * sr); L = int(.9 * sr); tt = np.arange(L) / sr
    bum = np.sin(2 * np.pi * 48 * tt) * np.exp(-tt * 6) * 1.1 + rng.normal(0, 1, L) * np.exp(-tt * 25) * .4
    x[i0:i0 + L] += bum[:max(0, min(L, n - i0))]
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
        fs.text(ctx, "LIFT A BAR", W / 2, 370, 92, GELB, .1, alpha=ha)
    badge(ctx, "HOW HEAVY?", W / 2, 300, fenster(t, 3.05, 4.5), f=GELB, groesse=56)
    badge(ctx, "BIRMINGHAM · 2026", W / 2, 300, fenster(t, 4.6, 6.85), f=WEISS, groesse=44)
    a_ = fenster(t, 15.35, 17.15, .1, .2)
    if a_ > 0:
        kg = int(511 * ease((t - 15.35) / .7)); badge(ctx, f"{kg} KG", W / 2, 300, a_, f=GELB if kg >= 511 else WEISS, groesse=84)
    badge(ctx, "≈ A BIG POLAR BEAR", W / 2, 300, fenster(t, 17.25, 19.35), f=WEISS, groesse=46)
    badge(ctx, "OLD RECORD: 510 KG", W / 2, 300, fenster(t, 22.95, D - .45), f=WEISS, groesse=42)
    badge(ctx, "NEW: 511 KG", W / 2, 420, fenster(t, 23.9, D - .45), f=GELB, groesse=58)
    rekordlabel(ctx, fenster(t, 20.75, D - .45))
    U.zeichne(ctx, t)


def main():
    liste = os.path.join(HIER, "_he_liste.txt"); n = int(round(D * RFPS))
    with open(liste, "w") as f:
        for i in range(n):
            f.write(f"file 'heframes/heben_{i:04d}.png'\nduration {1 / RFPS}\n")
        f.write(f"file 'heframes/heben_{n - 1:04d}.png'\n")
    basis = os.path.join(HIER, "_hebasis.mp4")
    if not os.path.exists(basis):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", liste,
                        "-vf", f"fps={RFPS},minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=fdiff:scd_threshold=6,scale=1080:1920:flags=lanczos,unsharp=5:5:0.4,noise=alls=4:allf=t",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", basis], check=True, cwd=HIER)
    wav = os.path.join(HIER, "_hebe.wav"); out = os.path.join(HIER, "videos", "rekord_heben_3d.mp4")
    ton_spannung("hebe", D, SCHNITTE + [D - .9], wav)
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
