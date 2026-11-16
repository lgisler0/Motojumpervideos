"""Loch durch die Erde, Version 2: ElevenLabs-Stimme, Wort-fuer-Wort-Untertitel, Zoom-Schnitte, Blitze, Whooshes.
Aufruf: python3 hole_v2.py"""
import json, math, os, subprocess, wave
import numpy as np, cairo
import beispiel, fakten_studio as fs
from fakten_studio import W, H, FPS, SR, text, ease, WEISS, GELB, rund

HIER = os.path.dirname(os.path.abspath(__file__))
STIMME = os.path.join(HIER, "stimme", "hole.mp3")
WORTE = [(w, float(a), float(b)) for w, a, b in json.load(open(os.path.join(HIER, "stimme", "hole_worte.json")))]
STARTS = [0.0, 4.08, 8.58, 13.22, 18.8, 22.84, 27.56]
VORLAUF = 0.15
DAUER = WORTE[-1][2] + VORLAUF + 0.7


def szene(t):
    tt = t - VORLAUF
    i = max(k for k, s in enumerate(STARTS) if tt >= s) if tt >= 0 else 0
    ende = STARTS[i + 1] if i + 1 < len(STARTS) else WORTE[-1][2]
    return i, max(tt - STARTS[i], 0), max(ende - STARTS[i] - .35, 1.0)


# Untertitel-Gruppen: max 3 Woerter, neue Gruppe nach Satzzeichen oder Pause
GRUPPEN, akt = [], []
for n, (w, a, b) in enumerate(WORTE):
    akt.append(n)
    naechst = WORTE[n + 1][1] if n + 1 < len(WORTE) else 1e9
    if len(akt) == 3 or w[-1] in ".,?!" or naechst - b > .25:
        GRUPPEN.append(akt); akt = []
if akt:
    GRUPPEN.append(akt)
# Zahlen zusammenfassen ("28" ",000" -> "28,000")
ANZEIGE = [w.upper().strip(".,?!") for w, _, _ in WORTE]
for n, (w, _, _) in enumerate(WORTE):
    if w.startswith(","):
        ANZEIGE[n - 1] += w; ANZEIGE[n] = ""
BEATS = [WORTE[g[0]][1] for g in GRUPPEN]


def untertitel(ctx, tt):
    g = None
    for gg in GRUPPEN:
        if WORTE[gg[0]][1] - .05 <= tt <= WORTE[gg[-1]][2] + .25:
            g = gg
    if g is None:
        return
    worte = [n for n in g if ANZEIGE[n]]
    size = 92
    ctx.select_font_face(fs.SCHRIFT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); ctx.set_font_size(size)
    breiten = [ctx.text_extents(ANZEIGE[n]).x_advance for n in worte]
    luecke = size * .42; ges = sum(breiten) + luecke * (len(worte) - 1)
    k = min(1.0, 980 / ges)
    x = W / 2 - ges * k / 2; y = 1640
    for n, b in zip(worte, breiten):
        an = tt >= WORTE[n][1] - .03
        pop = ease((tt - WORTE[n][1] + .03) / .1) if an else 0
        s = size * k * (1 + .1 * (1 - pop) * an)
        farbe = GELB if an and tt <= WORTE[n][2] + .08 else WEISS
        text(ctx, ANZEIGE[n], x + b * k / 2, y, s, farbe, .2, alpha=1 if an else .45)
        x += (b + luecke) * k


def kamera(t):
    """Zoom-Puls bei jeder Untertitel-Gruppe, Wackler beim Szenenwechsel."""
    tt = t - VORLAUF
    letzter = max([b for b in BEATS if b <= tt] or [0])
    z = 1.0 + .045 * math.exp(-(tt - letzter) * 7) + .02 * (tt / DAUER)
    sw = max([s for s in STARTS if s <= tt] or [0])
    wackel = math.exp(-(tt - sw) * 9) * 14
    return z, math.sin(t * 61) * wackel, math.cos(t * 47) * wackel, math.sin(t * 53) * .01 * wackel / 14


def zeichne(ctx, f):
    t = f / FPS; tt = t - VORLAUF
    i, tl, d = szene(t)
    z, dx, dy, rot = kamera(t)
    ctx.save()
    ctx.translate(W / 2 + dx, H / 2 + dy); ctx.rotate(rot); ctx.scale(z, z); ctx.translate(-W / 2, -H / 2)
    beispiel.v_hole(ctx, i, tl, d, t, {})
    ctx.restore()
    sw = max([s for s in STARTS if s <= tt] or [-9])
    if 0 < sw and tt - sw < .12:  # weisser Blitz beim Schnitt
        ctx.rectangle(0, 0, W, H); ctx.set_source_rgba(1, 1, 1, .55 * (1 - (tt - sw) / .12)); ctx.fill()
    untertitel(ctx, tt)
    rund(ctx, 0, 0, W * t / DAUER, 12, 0); ctx.set_source_rgb(*GELB); ctx.fill()


def ton(pfad):
    roh = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", STIMME, "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True).stdout
    voc = np.frombuffer(roh, np.int16).astype(np.float64) / 32768
    n = int(DAUER * SR); mix = np.zeros(n)
    s = int(VORLAUF * SR); mix[s:s + len(voc)] += voc[:n - s] * 1.0
    mix += fs.musik(DAUER, 4242)[:n] * .10
    for st in STARTS[1:]:
        mix += fs.wusch(n, st + VORLAUF - .2) * .16
    mix = mix / np.abs(mix).max() * .92
    mix[-int(.4 * SR):] *= np.linspace(1, 0, int(.4 * SR))
    with wave.open(pfad, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    ordner = os.path.join(HIER, "beispiel"); os.makedirs(ordner, exist_ok=True)
    wav, out = os.path.join(ordner, "_hole_v2.wav"), os.path.join(ordner, "fakten_hole_v2.mp4")
    ton(wav)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
           "-c:v", "libx264", "-preset", "slow", "-crf", "15", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    for f in range(int(DAUER * FPS)):
        ctx = cairo.Context(surf); ctx.set_source_rgb(0, 0, 0); ctx.paint(); zeichne(ctx, f); surf.flush(); p.stdin.write(bytes(surf.get_data()))
    p.stdin.close(); p.wait(); os.remove(wav)
    print("Fertig:", out)
