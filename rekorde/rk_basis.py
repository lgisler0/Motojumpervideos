"""Weltrekord-Shorts: gemeinsame Engine (Kamera in Metern, Zeichen-Bausteine, Untertitel, Ton, Render)."""
import os, sys, json, math, subprocess, wave
import numpy as np, cairo
sys.path.insert(0, "/home/claude/fakten")
import fakten_studio as fs

W, H, FPS, SR = 1080, 1920, 60, 48000
HIER = os.path.dirname(os.path.abspath(__file__))
WORTE_ALLE = json.load(open(os.path.join(HIER, "stimme", "worte.json")))
SCHRIFT = fs.SCHRIFT


def rgb(h):
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


WEISS, GELB, ROT, CYAN, NACHT = (1, 1, 1), rgb("ffd23f"), rgb("ff5a4e"), rgb("5fd3ff"), rgb("0d1426")
TINTE = rgb("1b2238")


def ease(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


def ease_out(x):
    x = min(1.0, max(0.0, x)); return 1 - (1 - x) ** 3


def lerp(a, b, k):
    return a + (b - a) * k


def mischen(a, b, k):
    return tuple(lerp(x, y, k) for x, y in zip(a, b))


def fenster(t, a, b, rein=.3, raus=.3):
    """0..1 Sichtbarkeit zwischen a und b mit weichen Kanten"""
    if t < a or t > b:
        return 0.0
    return min(1.0, ease((t - a) / rein) if rein else 1, ease((b - t) / raus) if raus else 1)


# ---------------------------------------------------------------- Kamera
class Kamera:
    """keys: (t, cx, cy, s) - Weltpunkt (cx, cy) in Bildmitte, s = Pixel pro Meter. Interpolation logarithmisch im Zoom."""

    def __init__(self, keys, atmen=.012):
        self.keys = sorted(keys); self.atmen = atmen

    def at(self, t):
        ks = self.keys
        if t <= ks[0][0]:
            _, cx, cy, s = ks[0]
        elif t >= ks[-1][0]:
            _, cx, cy, s = ks[-1]
        else:
            for a, b in zip(ks, ks[1:]):
                if a[0] <= t <= b[0]:
                    k = ease((t - a[0]) / max(b[0] - a[0], 1e-6))
                    s = math.exp(lerp(math.log(a[3]), math.log(b[3]), k))
                    # Position so mischen, dass der Zoom ruhig wirkt
                    cx, cy = lerp(a[1], b[1], k), lerp(a[2], b[2], k)
                    break
        s *= 1 + self.atmen * math.sin(t * .9)
        return cx + .004 * math.sin(t * .6) * W / s, cy, s


class Welt:
    def __init__(self, ctx, cam, t):
        self.ctx, self.t = ctx, t
        self.cx, self.cy, self.s = cam.at(t)

    def ein(self):
        c = self.ctx; c.save(); c.translate(W / 2, H / 2); c.scale(self.s, -self.s); c.translate(-self.cx, -self.cy)

    def aus(self):
        self.ctx.restore()

    def px(self, n):
        return n / self.s

    def bild(self, x, y):
        return W / 2 + (x - self.cx) * self.s, H / 2 - (y - self.cy) * self.s


# ---------------------------------------------------------------- Grundformen (Weltkoordinaten, y nach oben)
def farbe(c, f, a=1.0):
    c.set_source_rgba(*f, a)


def rrect(c, x, y, b, h, r):
    r = min(r, b / 2, h / 2)
    c.new_sub_path(); c.arc(x + b - r, y + r, r, -math.pi / 2, 0); c.arc(x + b - r, y + h - r, r, 0, math.pi / 2)
    c.arc(x + r, y + h - r, r, math.pi / 2, math.pi); c.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2); c.close_path()


def linie(c, pts, breite, f, a=1.0, kappe=cairo.LINE_CAP_ROUND):
    c.move_to(*pts[0])
    for p in pts[1:]:
        c.line_to(*p)
    c.set_line_width(breite); c.set_line_cap(kappe); c.set_line_join(cairo.LINE_JOIN_ROUND); farbe(c, f, a); c.stroke()


def poly(c, pts, f, a=1.0):
    c.move_to(*pts[0])
    for p in pts[1:]:
        c.line_to(*p)
    c.close_path(); farbe(c, f, a); c.fill()


def verlauf_v(c, x0, y0, x1, y1, stops):
    g = cairo.LinearGradient(x0, y0, x1, y1)
    for p, f, *a in stops:
        g.add_color_stop_rgba(p, *f, a[0] if a else 1)
    return g


def himmel(ctx, oben, unten, mitte=None):
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, *oben)
    if mitte:
        g.add_color_stop_rgb(.55, *mitte)
    g.add_color_stop_rgb(1, *unten)
    ctx.set_source(g); ctx.paint()


def boden(w, f_oben, f_unten, tiefe=None):
    """Boden unterhalb y=0, als grosse Flaeche"""
    c = w.ctx; x0 = w.cx - W / w.s; b = 2 * W / w.s; t = tiefe or 3 * H / w.s
    c.rectangle(x0, -t, b, t); c.set_source(verlauf_v(c, 0, 0, 0, -min(t, 2 * H / w.s), [(0, f_oben), (1, f_unten)])); c.fill()
    linie(c, [(x0, 0), (x0 + b, 0)], w.px(3), mischen(f_oben, WEISS, .25), .8)


def schatten(w, x, breite, a=.25):
    c = w.ctx; c.save(); c.translate(x, 0); c.scale(breite / 2, breite / 10)
    g = cairo.RadialGradient(0, 0, 0, 0, 0, 1); g.add_color_stop_rgba(0, 0, 0, 0, a); g.add_color_stop_rgba(1, 0, 0, 0, 0)
    c.set_source(g); c.arc(0, 0, 1, 0, 2 * math.pi); c.fill(); c.restore()


def mensch(w, x, h, f=rgb("e8ecf5"), f2=None, phase=None, kind=False, kleid=False, a=1.0, haare=None):
    """Piktogramm-Mensch, Fuesse bei (x,0), Hoehe h. phase: Laufzyklus (rad) oder None"""
    c = w.ctx; f2 = f2 or mischen(f, (0, 0, 0), .25)
    kopf = h * (.09 if not kind else .13); hk = h - kopf
    schulter, huefte = h * .80, h * .47
    sb = h * .105
    bein = h * .085; arm = h * .06
    if phase is None:
        sw, aw = 0, 0
    else:
        sw, aw = math.sin(phase), math.sin(phase + math.pi)
    lauf = phase is not None
    # hinteres Bein / Arm (dunkler)
    for s, tiefe in ((-1, True), (1, False)):
        ff = f2 if tiefe else f
        # Bein
        k = (sw if s > 0 else -sw) if lauf else 0
        knie = (x + s * h * .03 + k * h * .14, huefte * .5 + (abs(k) * h * .05 if lauf else 0))
        fuss = (x + s * h * .045 + k * h * .26, bein / 2 + (max(0, -k) * h * .08 if lauf else 0))
        linie(c, [(x + s * h * .04, huefte), knie, fuss], bein, ff, a)
    for s, tiefe in ((-1, True), (1, False)):
        ff = f2 if tiefe else f
        k = (aw if s > 0 else -aw) if lauf else 0
        ell = (x + s * sb * 1.05 + k * h * .12, h * .62)
        hand = (x + s * sb * 1.1 + k * h * .22, h * .46 + (abs(k) * h * .1 if lauf else 0))
        linie(c, [(x + s * sb * .9, schulter - arm * .4), ell, hand], arm, ff, a)
    # Rumpf
    if kleid:
        poly(c, [(x - sb, schulter), (x + sb, schulter), (x + sb * 1.5, huefte * .78), (x - sb * 1.5, huefte * .78)], f, a)
    rrect(c, x - sb, huefte, 2 * sb, schulter - huefte + arm * .4, sb * .7); farbe(c, f, a); c.fill()
    # Hals + Kopf
    linie(c, [(x, schulter), (x, hk - kopf * .6)], h * .05, f, a)
    c.arc(x, hk, kopf, 0, 2 * math.pi); farbe(c, f, a); c.fill()
    if haare:
        c.arc(x, hk + kopf * .15, kopf * 1.02, math.pi * .05, math.pi * .95); farbe(c, haare, a); c.fill()


def massband(w, x, y0, y1, f=GELB, text=None, seite=1, k=1.0, a=1.0, groesse=56):
    """senkrechtes Mass von y0 bis y1 an Position x (Welt). Text in Bildkoordinaten."""
    c = w.ctx; y1k = lerp(y0, y1, k)
    linie(c, [(x, y0), (x, y1k)], w.px(6), f, a, cairo.LINE_CAP_BUTT)
    for yy in (y0, y1k):
        linie(c, [(x - w.px(22), yy), (x + w.px(22), yy)], w.px(6), f, a, cairo.LINE_CAP_BUTT)
    if text and a > 0:
        w.aus(); bx, by = w.bild(x, lerp(y0, y1k, .5))
        fs.text(c, text, bx + seite * 30, by, groesse, f, .16, alpha=a, anker="links" if seite > 0 else "rechts"); w.ein()


def massband_h(w, x0, x1, y, f=GELB, text=None, k=1.0, a=1.0, groesse=56, text_y=-70):
    c = w.ctx; x1k = lerp(x0, x1, k)
    linie(c, [(x0, y), (x1k, y)], w.px(6), f, a, cairo.LINE_CAP_BUTT)
    for xx in (x0, x1k):
        linie(c, [(xx, y - w.px(22)), (xx, y + w.px(22))], w.px(6), f, a, cairo.LINE_CAP_BUTT)
    if text and a > 0:
        w.aus(); bx, by = w.bild(lerp(x0, x1k, .5), y)
        fs.text(c, text, bx, by + text_y, groesse, f, .16, alpha=a, maxw=980); w.ein()


def wolke(c, x, y, r, a=.9, f=WEISS):
    for dx, dy, rr in ((0, 0, 1), (-.9, -.25, .7), (.9, -.2, .75), (-.4, .35, .65), (.45, .3, .7)):
        c.arc(x + dx * r, y + dy * r, rr * r, 0, 2 * math.pi); farbe(c, f, a); c.fill()


# ---------------------------------------------------------------- Bildschirm-Elemente
def zahlkarte(ctx, zahl, unter, a=1.0, y=300, pop=0.0, groesse=150):
    if a <= 0:
        return
    s = groesse * (1 + .12 * pop)
    fs.glut(ctx, W / 2, y, 330, GELB, .22 * a)
    fs.text(ctx, zahl, W / 2, y, s, GELB, .1, alpha=a, maxw=1000)
    if unter:
        fs.text(ctx, unter, W / 2, y + groesse * .62, 44, WEISS, .14, alpha=a, maxw=980)


def badge(ctx, s, x, y, a=1.0, f=GELB, tf=NACHT, groesse=42):
    if a <= 0:
        return
    ctx.select_font_face(SCHRIFT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); ctx.set_font_size(groesse)
    e = ctx.text_extents(s); b, h = e.x_advance + groesse * 1.1, groesse * 1.7
    rrect(ctx, x - b / 2, y - h / 2, b, h, h / 2); farbe(ctx, f, a); ctx.fill()
    fs.text(ctx, s, x, y, groesse, tf, 0, alpha=a)


def rekordlabel(ctx, a=1.0):
    badge(ctx, "WORLD RECORD", W / 2, 150, a, f=GELB, tf=NACHT, groesse=34)


KORREKTUR = {"Jodie": "JYOTI", "Straddle": "STRATO", "Launch": "LAUNCH", "Rock,": "ROC", "CY's": "SEAWISE", "great": "GREAT",
             "name": "DANE", "Dan": "DANYANG", "Yang": "", "dream,": "DREAM", "than.": "THAN", "stood.": "STOOD", "measured.": "MEASURED",
             "Exactly.": "EXACTLY", "at...": "AT", "measures...": "MEASURES"}


class Untertitel:
    def __init__(self, key):
        roh = WORTE_ALLE[key]
        self.W = [(w, a, b) for w, a, b in roh]
        self.anz = []
        for i, (w, a, b) in enumerate(self.W):
            if w in KORREKTUR:
                s = KORREKTUR[w]
            else:
                s = w.upper().strip(".?!").rstrip(",")
            if key == "roc" and w == "Launch":
                s = ""; self.anz[-1] = "STRATOLAUNCH"
            if key == "roc" and w.startswith("Rock"):
                s = "ROC"
            if w.startswith(".") and self.anz:
                self.anz[-1] += w.rstrip(".,"); s = ""
            if w.startswith(",") and self.anz:
                self.anz[-1] += w.rstrip(".,"); s = ""
            if w.startswith("-") and self.anz:
                self.anz[-1] += w.upper().rstrip(".,"); s = ""
            self.anz.append(s)
        self.gr, akt = [], []
        for i, (w, a, b) in enumerate(self.W):
            akt.append(i)
            nx = self.W[i + 1] if i + 1 < len(self.W) else None
            if nx and (nx[0].startswith(".") or nx[0].startswith(",") or nx[0].startswith("-")):
                continue
            n = len([k for k in akt if self.anz[k]])
            if n >= 3 or w[-1] in ".,?!" or (nx and nx[1] - b > .3) or not nx:
                self.gr.append(akt); akt = []

    def zeichne(self, ctx, t, y=1520):
        g = None
        for gg in self.gr:
            if self.W[gg[0]][1] - .05 <= t <= self.W[gg[-1]][2] + .2:
                g = gg
        if g is None:
            return
        ws = [n for n in g if self.anz[n]]
        size = 84
        ctx.select_font_face(SCHRIFT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); ctx.set_font_size(size)
        br = [ctx.text_extents(self.anz[n]).x_advance for n in ws]
        lu = size * .4; ges = sum(br) + lu * (len(ws) - 1); k = min(1.0, 940 / max(ges, 1))
        x = W / 2 - ges * k / 2
        for n, b in zip(ws, br):
            an = t >= self.W[n][1] - .03
            pop = ease((t - self.W[n][1] + .03) / .1) if an else 0
            f = GELB if an and t <= self.W[n][2] + .08 else WEISS
            fs.text(ctx, self.anz[n], x + b * k / 2, y, size * k * (1 + .1 * (1 - pop) * an), f, .2, alpha=1 if an else .4)
            x += (b + lu) * k

    def zeit(self, text, nr=0):
        """Startzeit des nr-ten Worts, das mit text beginnt"""
        hits = [a for w, a, b in self.W if w.lower().startswith(text.lower())]
        return hits[min(nr, len(hits) - 1)] if hits else 0.0

    def ende(self):
        return self.W[-1][2]


# ---------------------------------------------------------------- Film-Look
_rng = np.random.default_rng(5)
_KOERNER = []
for _ in range(4):
    n = (_rng.standard_normal((H // 2, W // 2)) * 18 + 128).clip(0, 255).astype(np.uint8)
    arr = np.zeros((H // 2, W // 2, 4), np.uint8); arr[..., 0] = arr[..., 1] = arr[..., 2] = n; arr[..., 3] = 255
    s = cairo.ImageSurface.create_for_data(memoryview(arr).cast("B"), cairo.FORMAT_ARGB32, W // 2, H // 2)
    _KOERNER.append((s, arr))


def filmlook(ctx, f):
    g = cairo.RadialGradient(W / 2, H * .48, 450, W / 2, H / 2, 1250); g.add_color_stop_rgba(0, 0, 0, 0, 0); g.add_color_stop_rgba(1, 0, 0, 0, .5)
    ctx.set_source(g); ctx.paint()
    lg = cairo.LinearGradient(0, H - 640, 0, H); lg.add_color_stop_rgba(0, 0, 0, 0, 0); lg.add_color_stop_rgba(1, 0, 0, 0, .55)
    ctx.set_source(lg); ctx.rectangle(0, H - 640, W, 640); ctx.fill()
    lg = cairo.LinearGradient(0, 0, 0, 520); lg.add_color_stop_rgba(0, 0, 0, 0, .55); lg.add_color_stop_rgba(1, 0, 0, 0, 0)
    ctx.set_source(lg); ctx.rectangle(0, 0, W, 520); ctx.fill()
    s, _ = _KOERNER[f % 4]
    ctx.save(); ctx.scale(2, 2); ctx.set_source_surface(s, 0, 0); ctx.get_source().set_filter(cairo.FILTER_FAST)
    ctx.set_operator(cairo.OPERATOR_OVERLAY); ctx.paint_with_alpha(.18); ctx.restore()


# ---------------------------------------------------------------- Ton + Render
def ton(key, dauer, wusch, pfad):
    roh = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", os.path.join(HIER, "stimme", f"{key}.mp3"), "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True).stdout
    voc = np.frombuffer(roh, np.int16).astype(np.float64) / 32768
    n = int(dauer * SR); mix = np.zeros(n); m = min(n, len(voc)); mix[:m] += voc[:m]
    mu = fs.musik(dauer + 1, abs(hash(key)) % 9999)[:n + SR]
    # Musik nahtlos: Ende in Anfang ueberblenden
    L = int(.5 * SR); kopf = mu[:n].copy(); kopf[:L] = kopf[:L] * np.linspace(0, 1, L) + mu[n:n + L] * np.linspace(1, 0, L)
    mix += kopf * .09
    for st in wusch:
        mix += fs.wusch(n, st - .2) * .14
    mix = mix / np.abs(mix).max() * .92
    with wave.open(pfad, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype(np.int16).tobytes())


def rendern(key, dauer, zeichne, wusch, ordner, nur=None):
    os.makedirs(ordner, exist_ok=True)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    if nur is not None:
        for t in nur:
            ctx = cairo.Context(surf); zeichne(ctx, t); filmlook(ctx, int(t * FPS)); surf.write_to_png(os.path.join(ordner, f"{key}_{t:05.2f}.png"))
        return
    wav = os.path.join(ordner, f"_{key}.wav"); out = os.path.join(ordner, f"rekord_{key}.mp4")
    ton(key, dauer, wusch, wav)
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
                          "-c:v", "libx264", "-preset", "slow", "-crf", "15", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-shortest",
                          "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for f in range(int(round(dauer * FPS))):
        ctx = cairo.Context(surf); ctx.set_source_rgb(0, 0, 0); ctx.paint()
        zeichne(ctx, f / FPS); filmlook(ctx, f); surf.flush(); p.stdin.write(bytes(surf.get_data()))
    p.stdin.close(); p.wait(); os.remove(wav)
    return out


# ---------------------------------------------------------------- spannende Hintergrundmusik (leise, treibend)
def _tp(x, k):
    """einfacher Tiefpass (exponentiell), k 0..1"""
    y = np.empty_like(x); a = 0.0
    for i in range(len(x)):
        a += k * (x[i] - a); y[i] = a
    return y


OHNE_RAUSCHEN = True          # Loris 25.11.: kein Rauschen im Hintergrund


def musik_spannung(dauer, schnitte=(), seed=1, bpm=120):
    rng = np.random.default_rng(seed)
    n = int(dauer * SR); t = np.arange(n) / SR; out = np.zeros(n)
    beat = 60 / bpm; achtel = beat / 2
    # Akkordfolge a-Moll: Am F C G (je 2 Takte), Grundtoene im Bass
    akk = [(55.0, [220.0, 261.63, 329.63]), (43.65, [174.61, 220.0, 261.63]), (65.41, [196.0, 261.63, 329.63]), (49.0, [196.0, 246.94, 293.66])]
    takt = 4 * beat
    # Bass: pulsierende Achtel, saegezahnartig, gefiltert
    for i in range(int(dauer / achtel) + 1):
        st = i * achtel; s0 = int(st * SR); L = int(achtel * SR * .9)
        if s0 >= n:
            break
        grund = akk[int(st / (2 * takt)) % 4][0]
        f = grund * (2 if i % 8 == 7 else 1)
        tt = np.arange(min(L, n - s0)) / SR
        ton_ = sum(np.sin(2 * np.pi * f * h * tt) / h for h in range(1, 6))
        env = np.exp(-tt * 9) * (1 - np.exp(-tt * 400))
        out[s0:s0 + len(tt)] += ton_ * env * (.55 if i % 2 == 0 else .4)
    # Pad: weiche, leicht verstimmte Akkorde
    pad = np.zeros(n)
    for i in range(int(dauer / (2 * takt)) + 1):
        st = i * 2 * takt; s0 = int(st * SR); L = int(2 * takt * SR)
        tt = np.arange(min(L, n - s0)) / SR
        if len(tt) == 0:
            break
        env = np.minimum(1, tt / 1.2) * np.minimum(1, (L / SR - tt) / .8)
        for f in akk[i % 4][1]:
            pad[s0:s0 + len(tt)] += (np.sin(2 * np.pi * f * tt) + .6 * np.sin(2 * np.pi * f * 1.004 * tt)) * env * .12
    out += pad
    # Ticken (Hi-Hat) auf Sechzehnteln, sehr leise, + weicher Kick auf 1 und 3
    for i in range(int(dauer / (beat / 4)) + 1):
        s0 = int(i * beat / 4 * SR); L = int(.04 * SR)
        if s0 + L >= n:
            break
        if not OHNE_RAUSCHEN:
            nz = rng.standard_normal(L); nz = nz - _tp(nz, .3)
            out[s0:s0 + L] += nz * np.exp(-np.arange(L) / SR * 90) * (.09 if i % 4 == 2 else .045)
    for i in range(int(dauer / (2 * beat)) + 1):
        s0 = int(i * 2 * beat * SR); L = int(.35 * SR)
        if s0 + L >= n:
            break
        tt = np.arange(L) / SR; f = 50 + 70 * np.exp(-tt * 30)
        out[s0:s0 + L] += np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 9) * .8
    # Spannungsbogen vor jedem Schnitt + tiefer Schlag beim Schnitt
    for sc_ in schnitte:
        a = int(max(0, sc_ - 1.6) * SR); b = int(sc_ * SR)
        if b - a > 10 and b <= n and OHNE_RAUSCHEN:
            L = b - a; tt = np.arange(L) / SR                     # tonaler Anstieg statt Rauschen
            f = 110 * 2 ** (np.linspace(0, 1, L) * 1.0)
            out[a:b] += np.sin(2 * np.pi * np.cumsum(f) / SR) * np.linspace(0, 1, L) ** 2 * .25
        elif b - a > 10 and b <= n:
            L = b - a; nz = rng.standard_normal(L); k = np.linspace(.02, .35, L)
            y = np.empty(L); acc = 0.0
            for j in range(L):
                acc += k[j] * (nz[j] - acc); y[j] = acc
            out[a:b] += y * np.linspace(0, 1, L) ** 2 * 1.4
        L = int(1.2 * SR)
        if b + L < n:
            tt = np.arange(L) / SR
            out[b:b + L] += np.sin(2 * np.pi * (42 + 30 * np.exp(-tt * 8)) * tt) * np.exp(-tt * 3.5) * 1.3
    # langsamer Aufbau ueber das ganze Video
    out *= .75 + .25 * (t / dauer)
    return out / (np.abs(out).max() + 1e-9)


def ton_spannung(key, dauer, schnitte, pfad, musik_laut=.16):
    roh = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", os.path.join(HIER, "stimme", f"{key}.mp3"), "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True).stdout
    voc = np.frombuffer(roh, np.int16).astype(np.float64) / 32768
    n = int(dauer * SR); v = np.zeros(n); m = min(n, len(voc)); v[:m] = voc[:m]
    mu_l = musik_spannung(dauer + .6, schnitte, abs(hash(key)) % 999)
    L = int(.5 * SR); mu = mu_l[:n].copy(); mu[:L] = mu[:L] * np.linspace(0, 1, L) + mu_l[n:n + L] * np.linspace(1, 0, L)  # Loop-Naht
    # Ducking: Musik leiser, wenn gesprochen wird
    hull = np.convolve(np.abs(v), np.ones(int(.15 * SR)) / int(.15 * SR), "same")
    duck = 1 - .45 * np.clip(hull / (hull.max() * .25 + 1e-9), 0, 1)
    mix = v + mu * musik_laut * duck
    if not OHNE_RAUSCHEN:
        for st in schnitte:
            mix += fs.wusch(n, st - .2) * .1
    mix = mix / np.abs(mix).max() * .92
    with wave.open(pfad, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype(np.int16).tobytes())
