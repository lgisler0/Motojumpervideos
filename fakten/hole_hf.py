"""Loch durch die Erde, Higgsfield-Version: echte KI-Clips + ElevenLabs-Stimme + Wort-Untertitel, Zahlen, Zoom-Pulse.
Clips liegen als clips/c1.mp4 .. c9.mp4 (720x1280). Aufruf: python3 hole_hf.py"""
import math, os, subprocess
import numpy as np, cairo
import hole_v2 as v2, fakten_studio as fs
from fakten_studio import W, H, FPS, text, ease, zahl, WEISS, GELB, CYAN, rund

HIER = os.path.dirname(os.path.abspath(__file__))
CLIPS = os.path.join(HIER, "clips")
V = v2.VORLAUF
S = [s + V for s in v2.STARTS] + [v2.DAUER]
DAUER = v2.DAUER

# Schnittliste: (clip, startzeit im clip, dauer) - aneinandergereiht ab t=0
def _plan():
    p = []
    def seg(c, a, d):
        p.append((c, a, d))
    seg(1, 0.6, S[1])                      # Sprung ins Loch
    d = S[2] - S[1]; seg(2, 2.4, d * .55); seg(4, 0.3, d * .45)
    d = S[3] - S[2]; seg(3, 0.0, d * .45); seg(5, 0.0, d * .55)
    d = S[4] - S[3]; seg(5, 2.6, min(2.4, d * .45)); seg(6, 0.0, d - min(2.4, d * .45))
    d = S[5] - S[4]; seg(7, 0.2, d)
    d = S[6] - S[5]; seg(8, 0.0, min(d, 5.0))
    rest = S[6] - S[5] - min(S[6] - S[5], 5.0)
    if rest > 0:
        seg(3, 4.9 - rest, rest)
    d = DAUER - S[6]; seg(9, 0.0, min(d, 5.0))
    if d > 5.0:
        seg(3, 2.0, d - 5.0)
    return p


PLAN = _plan()
SCHNITTE = list(np.cumsum([d for _, _, d in PLAN])[:-1])


def basis(pfad):
    """Alle Abschnitte zuschneiden, auf 1080x1920/60 fps bringen und aneinanderhaengen."""
    ein, filt = [], []
    for n, (c, a, d) in enumerate(PLAN):
        ein += ["-ss", f"{a:.3f}", "-t", f"{d + .05:.3f}", "-i", os.path.join(CLIPS, f"c{c}.mp4")]
        filt.append(f"[{n}:v]scale={W}:{H}:flags=lanczos,fps={FPS},trim=duration={d:.4f},setpts=PTS-STARTPTS,setsar=1[v{n}]")
    filt.append("".join(f"[v{n}]" for n in range(len(PLAN))) + f"concat=n={len(PLAN)}:v=1:a=0[out]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *ein, "-filter_complex", ";".join(filt), "-map", "[out]",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "12", "-pix_fmt", "yuv420p", pfad], check=True)


def tempo(t):
    """km/h-Anzeige waehrend des Falls (sin-Verlauf bis zur Mitte bei ~S[3])."""
    k = (t - S[1]) / (S[3] + .3 - S[1])
    return 28000 * math.sin(max(0, min(1, k)) * math.pi / 2) if t < S[3] + .3 else 28000 * math.cos(min(1, (t - S[3] - .3) / (S[4] - S[3] - .3)) * math.pi / 2)


def overlay(ctx, t):
    if t < S[1]:
        a = ease(t / .3)
        text(ctx, "A HOLE THROUGH", W / 2, 250, 104, WEISS, .14, maxw=980, alpha=a)
        text(ctx, "THE WHOLE EARTH?", W / 2, 385, 112, GELB, .14, maxw=980, alpha=a)
    elif t < S[4]:
        v = tempo(t)
        groß = S[2] + 1.8 < t < S[3] + .8
        text(ctx, f"{zahl(round(v, -2))} KM/H", W / 2, 260, 132 if groß else 116, GELB if groß else WEISS, .13, maxw=980)
        text(ctx, "THE CENTER OF THE EARTH" if groß else ("FALLING FASTER" if t < S[3] else "SLOWING DOWN"), W / 2, 380, 52, CYAN, .16)
    elif t < S[5]:
        text(ctx, "42 MINUTES", W / 2, 260, 132, GELB, .13)
        text(ctx, "THE OTHER SIDE OF THE PLANET", W / 2, 380, 52, CYAN, .16, maxw=980)
    elif t < S[6]:
        m = 42 + 84 * (t - S[5]) / (S[6] - S[5])
        text(ctx, f"{int(m)} MINUTES", W / 2, 260, 132, GELB, .13)
        text(ctx, "BACK AND FORTH, FOREVER", W / 2, 380, 52, CYAN, .16)
    else:
        a = ease((t - S[6] - .8) / .4)
        text(ctx, "5,500 °C", W / 2, 260, 140, GELB, .13, alpha=a)
        text(ctx, "AS HOT AS THE SUN'S SURFACE", W / 2, 385, 50, CYAN, .16, alpha=a, maxw=980)


def zeichne(ctx, bild, t):
    tt = t - V
    letzter = max([b for b in v2.BEATS if b <= tt] or [0])
    z = 1.0 + .035 * math.exp(-(tt - letzter) * 7) + .04 * ((t % 2.5) / 2.5)
    sw = max([s for s in SCHNITTE if s <= t] or [-9])
    wk = math.exp(-(t - sw) * 10) * 12 if sw > 0 else 0
    ctx.save()
    ctx.translate(W / 2 + math.sin(t * 61) * wk, H / 2 + math.cos(t * 47) * wk); ctx.scale(z, z); ctx.translate(-W / 2, -H / 2)
    ctx.set_source_surface(bild, 0, 0); ctx.paint()
    ctx.restore()
    # Abdunklung oben und unten fuer lesbare Schrift
    for y0, y1 in ((0, 520), (H - 520, H)):
        g = cairo.LinearGradient(0, y0, 0, y1)
        g.add_color_stop_rgba(0, 0, 0, 0, .55 if y0 == 0 else 0); g.add_color_stop_rgba(1, 0, 0, 0, 0 if y0 == 0 else .6)
        ctx.rectangle(0, y0, W, y1 - y0); ctx.set_source(g); ctx.fill()
    if sw > 0 and t - sw < .1:
        ctx.rectangle(0, 0, W, H); ctx.set_source_rgba(1, 1, 1, .5 * (1 - (t - sw) / .1)); ctx.fill()
    overlay(ctx, t)
    v2.untertitel(ctx, tt)
    rund(ctx, 0, 0, W * t / DAUER, 12, 0); ctx.set_source_rgb(*GELB); ctx.fill()


def ton(pfad):
    import wave
    roh = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", v2.STIMME, "-f", "s16le", "-ac", "1", "-ar", str(fs.SR), "-"], capture_output=True).stdout
    voc = np.frombuffer(roh, np.int16).astype(np.float64) / 32768
    n = int(DAUER * fs.SR); mix = np.zeros(n); s = int(V * fs.SR)
    mix[s:s + len(voc)] += voc[:n - s]
    mix += fs.musik(DAUER, 4242)[:n] * .10
    for st in SCHNITTE:
        mix += fs.wusch(n, st - .2) * .13
    mix = mix / np.abs(mix).max() * .92
    mix[-int(.4 * fs.SR):] *= np.linspace(1, 0, int(.4 * fs.SR))
    with wave.open(pfad, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(fs.SR); w.writeframes((mix * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    ordner = os.path.join(HIER, "beispiel"); os.makedirs(ordner, exist_ok=True)
    b, wav, out = os.path.join(ordner, "_basis.mp4"), os.path.join(ordner, "_hf.wav"), os.path.join(ordner, "fakten_hole_hf.mp4")
    basis(b); ton(wav)
    lesen = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", b, "-f", "rawvideo", "-pix_fmt", "bgra", "-"], stdout=subprocess.PIPE)
    schreiben = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
                                  "-c:v", "libx264", "-preset", "slow", "-crf", "15", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-shortest",
                                  "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    groesse = W * H * 4; surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); f = 0
    while True:
        roh = lesen.stdout.read(groesse)
        if len(roh) < groesse:
            break
        bild = cairo.ImageSurface.create_for_data(bytearray(roh), cairo.FORMAT_ARGB32, W, H)
        ctx = cairo.Context(surf); zeichne(ctx, bild, f / FPS); surf.flush(); schreiben.stdin.write(bytes(surf.get_data())); f += 1
    schreiben.stdin.close(); schreiben.wait(); os.remove(wav); os.remove(b)
    print("Fertig:", out, f, "Bilder")
