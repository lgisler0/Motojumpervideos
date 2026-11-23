"""Schnitt 100 m (Usain Bolt): Blender-Bilder -> 1080x1920/60fps + Rennuhr, Schrittzaehler, Badges, Startschuss + Publikum, Untertitel."""
import os, subprocess, math
import cairo
from rk_basis import *

HIER = os.path.dirname(os.path.abspath(__file__))
U = Untertitel("sprint"); D = 28.6
T0 = 12.38
RFPS = 15


def weg(t, vmax, tau=1.25, reakt=.15):
    t = max(0, t - reakt); return vmax * (t - tau * (1 - math.exp(-t / tau)))


VM = 12.0
for _ in range(40):
    VM *= 100 / weg(9.58, VM)


def geraeusche(wav):
    import wave, numpy as np
    with wave.open(wav, "rb") as w:
        sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    n = len(x); t = np.arange(n) / sr; rng = np.random.default_rng(4)
    # Startschuss: kurzer Knall (Rauschen mit schnellem Abklingen + tiefer Puls)
    i0 = int(T0 * sr); L = int(.6 * sr); tt = np.arange(L) / sr
    knall = rng.normal(0, 1, L) * np.exp(-tt * 28) + np.sin(2 * np.pi * 70 * tt) * np.exp(-tt * 12) * .8
    x[i0:i0 + L] += knall[:max(0, min(L, n - i0))] * .55
    # Publikum: gefiltertes Rauschen, schwillt im Rennen an, Jubel am Ziel
    roh = rng.normal(0, 1, n); k = int(sr / 900); menge = np.convolve(roh, np.ones(k) / k, "same")
    huell = .08 + .25 * np.clip((t - T0) / 4, 0, 1) * (t > T0) + .45 * np.clip((t - 21.9) / .6, 0, 1) * np.exp(-np.clip(t - 23.5, 0, None) / 2.5)
    huell *= np.where(t < T0, np.where(t > 10.4, .25, 1), 1)          # Stille bei "On your marks"
    x += menge * huell * .9
    x = x / np.abs(x).max() * .92
    with wave.open(wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((x * 32767).astype(np.int16).tobytes())


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
        fs.text(ctx, "RUN 100 m", W / 2, 370, 96, GELB, .1, alpha=ha)
    badge(ctx, "100 m", W / 2, 300, fenster(t, 2.15, 5.35), f=WEISS, groesse=52)
    badge(ctx, "BERLIN \u00b7 16 AUG 2009", W / 2, 300, fenster(t, 5.45, 8.65), f=WEISS, groesse=44)
    badge(ctx, "8 SPRINTERS", W / 2, 300, fenster(t, 8.75, 10.45), f=WEISS, groesse=46)
    ua = fenster(t, T0 - .05, 25.2, .05, .2)
    if ua > 0:
        z = min(9.58, max(0, t - T0)); badge(ctx, f"{z:.2f}", W / 2, 300, ua, f=GELB if t - T0 >= 9.58 else WEISS, groesse=80)
    if 13.5 <= t < 16.26:
        schr = min(41, int(weg(t - T0, VM) / 100 * 41) + 1); badge(ctx, f"STRIDE {schr}", W / 2, 430, fenster(t, 13.55, 16.2), f=WEISS, groesse=40)
    badge(ctx, "\u2248 45 KM/H", W / 2, 430, fenster(t, 18.15, 21.1), f=GELB, groesse=52)
    badge(ctx, "17 YEARS UNBEATEN", W / 2, 300, fenster(t, 25.35, D - .45), f=GELB, groesse=46)
    rekordlabel(ctx, fenster(t, 23.4, 25.25))
    U.zeichne(ctx, t)


def main():
    liste = os.path.join(HIER, "_spr_liste.txt"); n = int(round(D * RFPS))
    with open(liste, "w") as f:
        for i in range(n):
            f.write(f"file 'sprframes/sprint_{i:04d}.png'\nduration {1 / RFPS}\n")
        f.write(f"file 'sprframes/sprint_{n - 1:04d}.png'\n")
    basis = os.path.join(HIER, "_sprbasis.mp4")
    if not os.path.exists(basis):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", liste,
                        "-vf", f"fps={RFPS},minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=fdiff:scd_threshold=6,scale=1080:1920:flags=lanczos,unsharp=5:5:0.5,noise=alls=5:allf=t",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", basis], check=True, cwd=HIER)
    wav = os.path.join(HIER, "_sprint.wav"); out = os.path.join(HIER, "videos", "rekord_sprint_3d.mp4")
    ton_spannung("sprint", D, [2.08, 5.42, 8.7, 10.5, 11.56, 12.38, 13.5, 16.26, 18.12, 21.24, 23.38, 25.26, D - .9], wav)
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
