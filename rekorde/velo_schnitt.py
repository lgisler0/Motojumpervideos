"""Schnitt Velo-Rekord (Denise Mueller-Korenek): Blender-Bilder -> 1080x1920/60fps + Tempoanzeige, Badges, Motor/Wind/Klack, Untertitel."""
import os, subprocess, math
import cairo
from rk_basis import *

HIER = os.path.dirname(os.path.abspath(__file__))
U = Untertitel("velo"); D = 26.6
TREL = 11.1
RFPS = 15
SCHNITTE = [1.3, 2.7, 4.0, 5.4, 6.9, 8.3, 10.0, 11.7, 13.0, 14.6, 16.9, 18.3, 20.6, 21.9, 23.6]


def v_rad(t):
    if t < TREL:
        return 18 + 2.4 * max(t, 0)
    if t < 19.0:
        k = (t - TREL) / (19.0 - TREL); return 44.64 + (82.22 - 44.64) * (1 - (1 - k) ** 2)
    if t < 24.0:
        return 82.22
    return max(20, 82.22 - 7 * (t - 24))


def geraeusche(wav):
    import wave, numpy as np
    with wave.open(wav, "rb") as w:
        sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    n = len(x); t = np.arange(n) / sr; rng = np.random.default_rng(9)
    ts = np.where(t < 1.3, 19.6 + t * .35, t)
    v = np.array([v_rad(a) for a in ts[::200]]); v = np.repeat(v, 200)[:n]
    # Fahrtwind: tiefpassgefiltertes Rauschen, lauter mit Tempo
    k = int(sr / 900); wind = np.convolve(rng.normal(0, 1, n), np.ones(k) / k, "same")
    x += wind * 1.4 * (v / 82) ** 2
    # Motor: Grundton steigt mit Tempo (bis zum Abkoppeln hart, danach leiser, weil vorne)
    f = 38 + v * .9; ph = np.cumsum(2 * np.pi * f / sr)
    motor = (np.sign(np.sin(ph)) * .5 + np.sin(2 * ph) * .3) * (.06 + .03 * np.sin(t * 31))
    k2 = int(sr / 1200); motor = np.convolve(motor, np.ones(k2) / k2, "same")
    x += motor * np.where(t < TREL, 1.0, .55)
    # Klack beim Abkoppeln
    i0 = int(TREL * sr); L = int(.25 * sr); tt = np.arange(L) / sr
    klack = (rng.normal(0, 1, L) * np.exp(-tt * 60) + np.sin(2 * np.pi * 1800 * tt) * np.exp(-tt * 40)) * .6
    x[i0:i0 + L] += klack[:max(0, min(L, n - i0))]
    # Zischen am Bildschnitt in der Zeitlupe (Anfang)
    x[:int(1.3 * sr)] += np.convolve(rng.normal(0, 1, int(1.3 * sr)), np.ones(6) / 6, "same") * .04
    x = x / np.abs(x).max() * .92
    with wave.open(wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((x * 32767).astype(np.int16).tobytes())


def overlay(ctx, t):
    lg = cairo.LinearGradient(0, H - 640, 0, H); lg.add_color_stop_rgba(0, 0, 0, 0, 0); lg.add_color_stop_rgba(1, 0, 0, 0, .5)
    ctx.set_source(lg); ctx.rectangle(0, H - 640, W, 640); ctx.fill()
    rg = cairo.RadialGradient(W / 2, H / 2, H * .35, W / 2, H / 2, H * .75)
    rg.add_color_stop_rgba(0, 0, 0, 0, 0); rg.add_color_stop_rgba(1, 0, 0, 0, .35); ctx.set_source(rg); ctx.paint()
    ha = fenster(t, -1, 1.3, 0, .2) + fenster(t, D - .4, 99, .25, 0)
    if ha:
        lg = cairo.LinearGradient(0, 0, 0, 560); lg.add_color_stop_rgba(0, 0, 0, 0, .55 * ha); lg.add_color_stop_rgba(1, 0, 0, 0, 0)
        ctx.set_source(lg); ctx.rectangle(0, 0, W, 560); ctx.fill()
        fs.text(ctx, "1 JOB:", W / 2, 260, 96, WEISS, .1, alpha=ha)
        fs.text(ctx, "RIDE A BIKE", W / 2, 370, 92, GELB, .1, alpha=ha)
    badge(ctx, "HOW FAST?", W / 2, 300, fenster(t, 2.75, 4.0), f=GELB, groesse=56)
    badge(ctx, "2018 · BONNEVILLE, UTAH", W / 2, 300, fenster(t, 4.05, 6.85), f=WEISS, groesse=42)
    badge(ctx, "TOWED BY A DRAGSTER", W / 2, 300, fenster(t, 6.95, 10.9), f=WEISS, groesse=40)
    badge(ctx, "RELEASE!", W / 2, 300, fenster(t, TREL, 12.4, .05, .2), f=GELB, groesse=60)
    a_ = fenster(t, 16.9, 20.55, .15, .1)
    if a_ > 0:
        kmh = min(296, int(v_rad(t) * 3.6 + .5)); badge(ctx, f"{kmh} KM/H", W / 2, 300, a_, f=GELB if kmh >= 296 else WEISS, groesse=78)
    b_ = fenster(t, 20.6, 21.85, .1, .2)
    if b_ > 0:
        badge(ctx, "296 KM/H", W / 2, 300, b_, f=GELB, groesse=78)
        badge(ctx, "TOUR DE FRANCE PROS: ~45 KM/H", W / 2, 440, b_, f=WEISS, groesse=36)
    rekordlabel(ctx, fenster(t, 23.65, D - .45))
    U.zeichne(ctx, t)


def main():
    liste = os.path.join(HIER, "_ve_liste.txt"); n = int(round(D * RFPS))
    with open(liste, "w") as f:
        for i in range(n):
            f.write(f"file 'veframes/velo_{i:04d}.png'\nduration {1 / RFPS}\n")
        f.write(f"file 'veframes/velo_{n - 1:04d}.png'\n")
    basis = os.path.join(HIER, "_vebasis.mp4")
    if not os.path.exists(basis):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", liste,
                        "-vf", f"fps={RFPS},minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=fdiff:scd_threshold=6,scale=1080:1920:flags=lanczos,unsharp=5:5:0.5,noise=alls=5:allf=t",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", basis], check=True, cwd=HIER)
    wav = os.path.join(HIER, "_velo.wav"); out = os.path.join(HIER, "videos", "rekord_velo_3d.mp4")
    ton_spannung("velo", D, SCHNITTE + [D - .9], wav)
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
