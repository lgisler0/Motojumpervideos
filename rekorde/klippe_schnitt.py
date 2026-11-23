"""Schnitt Klippensprung (Laso Schaller): Blender-Bilder -> 1080x1920/60fps + Hoehenzaehler, Falluhr, Badges, Wasserfall/Wind/Platsch, Untertitel."""
import os, subprocess, math
import cairo
from rk_basis import *

HIER = os.path.dirname(os.path.abspath(__file__))
U = Untertitel("klippe"); D = 27.5
TS = 20.30
TF = TS + math.sqrt(2 * 58.8 / 9.81) * 1.02
RFPS = 15


def geraeusche(wav):
    import wave, numpy as np
    with wave.open(wav, "rb") as w:
        sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    n = len(x); t = np.arange(n) / sr; rng = np.random.default_rng(6)
    roh = rng.normal(0, 1, n)
    k = int(sr / 2500); rauschen = np.convolve(roh, np.ones(k) / k, "same")         # Wasserfall (gleichmaessig)
    x += rauschen * .10
    k2 = int(sr / 400); wind = np.convolve(rng.normal(0, 1, n), np.ones(k2) / k2, "same")   # Fallwind, schwillt an
    x += wind * 1.6 * np.clip((t - TS) / (TF - TS), 0, 1) ** 2 * (t < TF)
    i0 = int(TF * sr); L = int(1.4 * sr); tt = np.arange(L) / sr
    platsch = rng.normal(0, 1, L) * np.exp(-tt * 5) + np.sin(2 * np.pi * 55 * tt) * np.exp(-tt * 8) * 1.2
    x[i0:i0 + L] += platsch[:max(0, min(L, n - i0))] * .5
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
        fs.text(ctx, "JUMP INTO WATER", W / 2, 370, 88, GELB, .1, alpha=ha)
    badge(ctx, "HOW HIGH?", W / 2, 300, fenster(t, 3.4, 5.0), f=GELB, groesse=56)
    badge(ctx, "2015 \u00b7 MAGGIA, SWITZERLAND", W / 2, 300, fenster(t, 5.1, 9.5), f=WEISS, groesse=40)
    a_ = fenster(t, 9.65, 12.65, .2, .2)
    if a_ > 0:
        h = 58.8 * ease((t - 9.7) / 2.4); badge(ctx, f"{h:.1f} m", W / 2, 300, a_, f=GELB if h > 58.7 else WEISS, groesse=60)
    badge(ctx, "TOWER OF PISA: 56.7 m", W / 2, 300, fenster(t, 12.75, 15.3), f=WEISS, groesse=40)
    badge(ctx, "POOL: 8 m DEEP", W / 2, 300, fenster(t, 15.4, 19.9), f=WEISS, groesse=44)
    ua = fenster(t, TS - .05, 25.5, .05, .2)
    if ua > 0:
        z = min(TF - TS, max(0, t - TS)); badge(ctx, f"{z:.2f} s", W / 2, 300, ua, f=GELB if t >= TF else WEISS, groesse=72)
    badge(ctx, "> 100 KM/H", W / 2, 430, fenster(t, 23.3, 25.55), f=GELB, groesse=52)
    rekordlabel(ctx, fenster(t, 25.7, D - .45))
    U.zeichne(ctx, t)


def main():
    liste = os.path.join(HIER, "_kl_liste.txt"); n = int(round(D * RFPS))
    with open(liste, "w") as f:
        for i in range(n):
            f.write(f"file 'klframes/klippe_{i:04d}.png'\nduration {1 / RFPS}\n")
        f.write(f"file 'klframes/klippe_{n - 1:04d}.png'\n")
    basis = os.path.join(HIER, "_klbasis.mp4")
    if not os.path.exists(basis):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", liste,
                        "-vf", f"fps={RFPS},minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=fdiff:scd_threshold=6,scale=1080:1920:flags=lanczos,unsharp=5:5:0.5,noise=alls=5:allf=t",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", basis], check=True, cwd=HIER)
    wav = os.path.join(HIER, "_klippe.wav"); out = os.path.join(HIER, "videos", "rekord_klippe_3d.mp4")
    ton_spannung("klippe", D, [1.82, 3.36, 5.06, 6.08, 7.9, 9.6, 12.7, 15.34, 17.8, 19.96, 21.68, 23.2, 25.62, D - .9], wav)
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
