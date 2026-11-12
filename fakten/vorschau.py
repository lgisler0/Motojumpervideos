"""Standbilder ohne Ton: python3 vorschau.py <ziel.png> key:szene[:anteil] ..."""
import sys, cairo
import fakten_studio as fs
def bild(key, sz, ant=.9):
    v = fs.Video(key); t = .25; v.zeiten = []
    for txt, p in v.v["szenen"]:
        d = len(txt) * .065; v.zeiten.append((t, d, d + p, txt)); t += d + p
    v.dauer = t + .3; v.weg = [0] * 10
    st, d, _, _ = v.zeiten[sz]
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, fs.W, fs.H); c = cairo.Context(s)
    v.zeichne(c, int((st + d * ant) * fs.FPS)); return s
if __name__ == "__main__":
    args = sys.argv[2:]; n = len(args); k = .3
    out = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(fs.W * k * n), int(fs.H * k)); c = cairo.Context(out)
    for i, a in enumerate(args):
        p = a.split(":"); s = bild(p[0], int(p[1]), float(p[2]) if len(p) > 2 else .9)
        c.save(); c.translate(i * fs.W * k, 0); c.scale(k, k); c.set_source_surface(s); c.paint(); c.restore()
    out.write_to_png(sys.argv[1])
