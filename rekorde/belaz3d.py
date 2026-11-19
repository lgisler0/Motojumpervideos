"""BelAZ 75710 in 3D (Blender/Cycles). Masse: Laenge 20.6 m, Breite 9.75 m, Hoehe 8.17 m, 8 Reifen (~4 m),
Leergewicht 360 t, Nutzlast 450 t (GWR: largest two-axle dump truck).
Aufbau: Oberdeck vorne ueber die ganze Breite, Kabine links auf dem Deck, Schaltschrank rechts, Kuehlergrill in der Mitte,
diagonale Treppe quer ueber die Front, Mulde mit Schutzdach ueber der Kabine, Zwillingsreifen an beiden Achsen, gelb.
python3 belaz3d.py <ordner> [--nur t1,t2] [--start i]"""
import bpy, bmesh, math, random, sys, os, argparse
from mathutils import Vector

ap = argparse.ArgumentParser()
ap.add_argument("ordner"); ap.add_argument("--nur", default=""); ap.add_argument("--skala", type=int, default=50)
ap.add_argument("--samples", type=int, default=14); ap.add_argument("--fps", type=int, default=15)
ap.add_argument("--start", type=int, default=0); ap.add_argument("--dauer", type=float, default=30.5)
ap.add_argument("--exp", type=float, default=-2.1)
A = ap.parse_args(sys.argv[1:])

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = A.samples; sc.cycles.use_denoising = True
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.transparent_max_bounces = 8
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1080, 1920, A.skala
sc.render.use_persistent_data = True
sc.view_settings.view_transform = os.environ.get("VT", "Standard")
if sc.view_settings.view_transform == "AgX":
    sc.view_settings.look = os.environ.get("LOOK", "AgX - Punchy")
sc.view_settings.exposure = A.exp
print("VT", sc.view_settings.view_transform, sc.view_settings.look, flush=True)
P = math.pi


def hexf(h):
    return tuple(((int(h[i:i + 2], 16) / 255) ** 2.2) for i in (0, 2, 4))


def mat(name, farbe, rau=.4, metall=0, leucht=0, lf=None, cc=0):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*farbe, 1); b.inputs["Roughness"].default_value = rau; b.inputs["Metallic"].default_value = metall
    if cc:
        b.inputs["Coat Weight"].default_value = cc; b.inputs["Coat Roughness"].default_value = .15
    if leucht:
        b.inputs["Emission Color"].default_value = (*(lf or farbe), 1); b.inputs["Emission Strength"].default_value = leucht
    return m, b


def obj_aus(bm, name, m, glatt=False):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o)
    if m:
        me.materials.append(m)
    if glatt:
        for p in me.polygons:
            p.use_smooth = True
    return o


lkw = bpy.data.objects.new("BelAZ", None); sc.collection.objects.link(lkw)


def kind(o, eltern=None):
    o.parent = eltern or lkw; return o


def box(x0, x1, y0, y1, z0, z1, m, bev=0.0, seg=2, eltern=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    o = kind(bpy.context.object, eltern); o.scale = (x1 - x0, y1 - y0, z1 - z0); o.data.materials.append(m)
    if bev:
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        bv = o.modifiers.new("b", "BEVEL"); bv.width = bev; bv.segments = seg
    return o


def zyl(p0, p1, r, m, v=24, eltern=None):
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d.length, vertices=v, location=(p0 + p1) / 2)
    o = kind(bpy.context.object, eltern); o.rotation_euler = d.to_track_quat("Z", "Y").to_euler(); o.data.materials.append(m)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


# ---------- Materialien: Lack mit leichtem Schmutz (Noise-Mix), Rahmen, Gummi, Glas
def lack_dreckig(name, farbe, dreck="6b5a44", menge=.5):
    m = bpy.data.materials.new(name); m.use_nodes = True; n = m.node_tree.nodes; l = m.node_tree.links; b = n["Principled BSDF"]
    tc = n.new("ShaderNodeTexCoord"); tc.object = lkw; nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = .9; nz.inputs["Detail"].default_value = 10
    l.new(tc.outputs["Object"], nz.inputs["Vector"])
    sp = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Object"], sp.inputs[0])
    # unten mehr Dreck
    h = n.new("ShaderNodeMapRange"); h.inputs["From Min"].default_value = 3.2; h.inputs["From Max"].default_value = 0.3
    l.new(sp.outputs["Z"], h.inputs["Value"])
    ad = n.new("ShaderNodeMath"); ad.operation = "MULTIPLY_ADD"; ad.inputs[1].default_value = menge
    l.new(nz.outputs["Fac"], ad.inputs[0]); l.new(h.outputs["Result"], ad.inputs[2])
    cr = n.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].position = .62; cr.color_ramp.elements[1].position = .98
    l.new(ad.outputs[0], cr.inputs["Fac"])
    mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.inputs[6].default_value = (*farbe, 1); mx.inputs[7].default_value = (*hexf(dreck), 1)
    l.new(cr.outputs[0], mx.inputs[0]); l.new(mx.outputs[2], b.inputs["Base Color"])
    rr = n.new("ShaderNodeMapRange"); rr.inputs["To Min"].default_value = .35; rr.inputs["To Max"].default_value = .85
    l.new(cr.outputs[0], rr.inputs["Value"]); l.new(rr.outputs["Result"], b.inputs["Roughness"])
    b.inputs["Coat Weight"].default_value = .15
    return m


GELB = lack_dreckig("gelb", hexf("f5b000"))
GELB_M = lack_dreckig("gelb_mulde", hexf("e9a300"), menge=.6)
RAHMEN = lack_dreckig("rahmen", hexf("2a2a2c"), "4a3f33", .4)
GUMMI, gb = mat("gummi", hexf("141414"), .82)
STAHL, _ = mat("stahl", hexf("b8bcc2"), .25, 1)
CHROM, _ = mat("chrom", hexf("dfe3e8"), .1, 1)
GLAS, _ = mat("glas", hexf("10161e"), .03, .2)
GRILL_D, _ = mat("grilldunkel", hexf("0a0a0a"), .7)
LICHT, _ = mat("licht", hexf("ffffff"), .2, 0, 6, hexf("fff4dc"))
ORANGE, _ = mat("rundum", hexf("ff8a00"), .3, 0, 3, hexf("ff7a00"))
GRUEN_T, _ = mat("tritt", hexf("3a3a3a"), .6, .6)

# ---------- Rahmen und Antrieb
box(.6, 17.2, -1.35, -.75, 2.0, 3.3, RAHMEN, .05)
box(.6, 17.2, .75, 1.35, 2.0, 3.3, RAHMEN, .05)
for x in (2, 6.5, 10, 14, 16.8):
    box(x - .25, x + .25, -1.35, 1.35, 2.3, 3.0, RAHMEN)
# Hinterachsgehaeuse (gross, zwischen den Rad-Paaren) + Achsschenkel vorne
box(11.6, 13.6, -1.9, 1.9, 1.3, 2.7, RAHMEN, .25, 3)
zyl((12.6, -3.5, 2.0), (12.6, 3.5, 2.0), .75, RAHMEN, 32)
zyl((4.6, -3.4, 2.0), (4.6, 3.4, 2.0), .55, RAHMEN, 32)
# Federbeine (silberne Zylinder) vorne + hinten
for s in (-1, 1):
    zyl((4.1, s * 1.75, 2.4), (3.9, s * 1.75, 5.1), .32, CHROM); zyl((4.1, s * 1.75, 2.0), (4.1, s * 1.75, 3.2), .42, RAHMEN)
    zyl((13.6, s * 1.6, 2.5), (14.0, s * 1.6, 4.4), .3, CHROM)
    # Kippzylinder (Hydraulik) zwischen Rahmen und Mulde
    zyl((7.6, s * 1.6, 2.6), (8.6, s * 1.9, 4.5), .26, CHROM); zyl((7.4, s * 1.6, 2.2), (7.9, s * 1.7, 3.6), .36, RAHMEN)
# Motor-/Generatorblock unter dem Deck (zwei Diesel)
box(-.05, 7.4, -1.95, 1.95, 1.1, 5.25, GELB, .12, 3)
# Kuehlergrill vorne: dunkles Feld + waagrechte Lamellen
box(-.12, .0, -1.6, 1.6, 1.6, 5.0, GRILL_D)
for i in range(16):
    z = 1.75 + i * .21
    box(-.2, -.08, -1.62, 1.62, z, z + .06, RAHMEN)
box(-.22, -.06, -1.75, -1.6, 1.5, 5.1, GELB); box(-.22, -.06, 1.6, 1.75, 1.5, 5.1, GELB)
# Stossfaenger
box(-.75, .5, -2.6, 2.6, .85, 1.55, RAHMEN, .08)
for y in (-2.1, 2.1):
    box(-.8, -.7, y - .25, y + .25, 1.05, 1.3, LICHT)

# ---------- Oberdeck vorne (ueber die ganze Breite) mit Gelaender
box(-.25, 7.3, -4.85, 4.85, 5.2, 5.55, GELB, .05)
box(-.3, -.2, -4.85, 4.85, 4.85, 5.25, GELB)  # Stirnkante
for y in (-4.3, -3.6, 3.6, 4.3):
    box(-.34, -.28, y - .22, y + .22, 4.92, 5.18, LICHT)
# Kotfluegel ueber den Vorderraedern (Deck seitlich runtergezogen)
for s in (-1, 1):
    box(2.3, 7.0, s * 4.85 - .05, s * 4.85 + .05, 4.4, 5.2, GELB)
gel_y = [y / 2 for y in range(-9, 10)]
for y in gel_y[::2]:
    zyl((-.1, y, 5.55), (-.1, y, 6.6), .035, GELB, 10)
zyl((-.1, -4.6, 6.6), (-.1, 4.6, 6.6), .045, GELB, 10); zyl((-.1, -4.6, 6.1), (-.1, 4.6, 6.1), .035, GELB, 10)
for s in (-1, 1):
    zyl((-.1, s * 4.75, 6.6), (7.0, s * 4.75, 6.6), .045, GELB, 10)
    for x in (1.5, 3.5, 5.5, 7.0):
        zyl((x, s * 4.75, 5.55), (x, s * 4.75, 6.6), .035, GELB, 10)
# Kabine links, Schaltschrank rechts
kab = box(.35, 3.5, -4.55, -1.95, 5.55, 7.75, GELB, .14, 3)
box(.28, .36, -4.4, -2.1, 6.45, 7.6, GLAS)            # Frontscheibe
box(.6, 3.25, -4.6, -4.5, 6.45, 7.55, GLAS)           # Seitenfenster
box(.6, 3.25, -2.0, -1.9, 6.45, 7.55, GLAS)
box(1.2, 1.7, -4.6, -4.52, 5.7, 6.35, GLAS)           # Tuerfenster unten
box(.3, .42, -4.5, -2.0, 7.6, 7.72, RAHMEN)           # Sonnenblende
zyl((.3, -4.75, 7.2), (-.6, -5.1, 7.2), .04, RAHMEN, 8); box(-.75, -.6, -5.4, -5.0, 6.7, 7.3, GLAS)   # Spiegel
box(.6, 3.1, 1.95, 4.45, 5.55, 6.95, GELB, .08)       # Schaltschrank
for x in (.9, 1.6, 2.3):
    box(x, x + .5, 4.45, 4.5, 5.75, 6.75, RAHMEN)      # Lueftungsgitter
box(4.0, 7.0, -1.9, 1.9, 5.55, 6.6, GELB, .1)         # Motorhaube hinten auf dem Deck
for x in (4.4, 5.2, 6.0):
    zyl((x, 0, 6.6), (x, 0, 7.05), .16, RAHMEN, 16)    # Auspuff-Stutzen
zyl((2.0, -3.2, 7.75), (2.0, -3.2, 7.95), .12, ORANGE, 16)   # Rundumleuchte
# Diagonale Treppe quer ueber die Front (von unten rechts zum Deck links)
a0, a1 = Vector((-1.15, 3.3, .75)), Vector((-1.15, -1.3, 5.2))
for dy in (-.5, .5):  # zwei Wangen (in x-Richtung versetzt)
    zyl(a0 + Vector((dy * .9, 0, 0)), a1 + Vector((dy * .9, 0, 0)), .06, GELB, 10)
for i in range(15):
    k = (i + .5) / 15; p = a0.lerp(a1, k)
    box(p.x - .45, p.x + .45, p.y - .16, p.y + .16, p.z - .03, p.z + .03, GRUEN_T)
for k in (0, .33, .66, 1):
    p = a0.lerp(a1, k); zyl(p + Vector((-.45, 0, 0)), p + Vector((-.45, 0, 1.0)), .03, GELB, 8)
zyl(a0 + Vector((-.45, 0, 1.0)), a1 + Vector((-.45, 0, 1.0)), .04, GELB, 10)
box(-1.75, -.25, 3.0, 3.8, .7, .8, GRUEN_T)           # Podest unten
for i in range(3):
    box(-1.5, -.6, 3.15, 3.65, .2 + i * .2 - .02, .2 + i * .2 + .02, GRUEN_T)

# ---------- Mulde mit Schutzdach (Solidify), Rippen, Tropfkante
def flaeche(verts, name, m, dicke=.12):
    bm = bmesh.new(); vs = [bm.verts.new(v) for v in verts]; bm.faces.new(vs)
    o = kind(obj_aus(bm, name, m)); so = o.modifiers.new("s", "SOLIDIFY"); so.thickness = dicke
    bv = o.modifiers.new("b", "BEVEL"); bv.width = .03; bv.segments = 2
    return o


MY = 4.75
seite = [(7.4, 4.45), (15.8, 4.45), (20.6, 6.0), (20.45, 7.25), (19.6, 7.35), (7.4, 7.85)]
for s in (-1, 1):
    flaeche([(x, s * MY, z) for x, z in seite], f"seite{s}", GELB_M, .14)
    zyl((7.4, s * (MY + .05), 7.85), (19.6, s * (MY + .05), 7.35), .13, GELB_M, 12)     # Oberkante (Rohr)
    zyl((7.5, s * (MY + .05), 4.55), (15.8, s * (MY + .05), 4.55), .15, GELB_M, 12)
    zyl((15.8, s * (MY + .05), 4.55), (20.5, s * (MY + .05), 6.05), .15, GELB_M, 12)
    for x in (8.6, 10.2, 11.8, 13.4, 15.0, 16.6, 18.4):     # senkrechte Rippen aussen
        zu = 4.5 if x < 15.8 else 4.5 + (x - 15.8) / 4.8 * 1.55
        zo = 7.85 - (x - 7.4) / 12.2 * .5
        box(x - .14, x + .14, s * MY - (.16 if s < 0 else -.0), s * MY + (.0 if s < 0 else .16), zu, zo, GELB_M)
flaeche([(7.4, -MY, 4.45), (15.8, -MY, 4.45), (15.8, MY, 4.45), (7.4, MY, 4.45)], "boden", GELB_M, .16)
flaeche([(15.8, -MY, 4.45), (20.6, -MY, 6.0), (20.6, MY, 6.0), (15.8, MY, 4.45)], "heck", GELB_M, .16)
flaeche([(7.4, -MY, 4.45), (7.4, MY, 4.45), (7.4, MY, 7.95), (7.4, -MY, 7.95)], "stirn", GELB_M, .16)
flaeche([(7.5, -MY - .05, 7.95), (7.5, MY + .05, 7.95), (.1, MY + .05, 8.17), (.1, -MY - .05, 8.17)], "dach", GELB_M, .14)
zyl((.1, -MY - .05, 8.12), (.1, MY + .05, 8.12), .12, GELB_M, 12)
for y in (-3.6, -1.8, 0, 1.8, 3.6):   # Dachtraeger unten
    box(.2, 7.4, y - .12, y + .12, 7.65, 8.0, GELB_M)
for x in (5, 8, 11, 14):                # Laengstraeger unter der Mulde
    pass
box(7.5, 16.5, -1.5, -1.0, 3.9, 4.35, GELB_M); box(7.5, 16.5, 1.0, 1.5, 3.9, 4.35, GELB_M)
zyl((16.2, -2.0, 3.6), (16.2, 2.0, 3.6), .3, RAHMEN, 20)   # Kipp-Gelenk
# Ladung (Huegel aus Gestein in der Mulde) als Hoehenfeld, Ursprung auf dem Muldenboden
ld_m = bpy.data.materials.new("gestein"); ld_m.use_nodes = True; n = ld_m.node_tree.nodes; l = ld_m.node_tree.links; b = n["Principled BSDF"]
tc = n.new("ShaderNodeTexCoord"); vo = n.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 3.5; l.new(tc.outputs["Object"], vo.inputs["Vector"])
nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 2; nz.inputs["Detail"].default_value = 8; l.new(tc.outputs["Object"], nz.inputs["Vector"])
cr = n.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (*hexf("4f4335"), 1); cr.color_ramp.elements[1].color = (*hexf("9a8a74"), 1)
l.new(nz.outputs["Fac"], cr.inputs["Fac"]); l.new(cr.outputs[0], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = .95
bp = n.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = .8; l.new(vo.outputs["Distance"], bp.inputs["Height"]); l.new(bp.outputs[0], b.inputs["Normal"])
bm = bmesh.new(); NX, NY = 64, 28; rr = random.Random(7); grid = {}
for i in range(NX + 1):
    for j in range(NY + 1):
        x = 7.6 + 8.2 * i / NX + (4.6 * (i / NX) ** 6); y = -MY + .1 + (2 * MY - .2) * j / NY
        u = (x - 12.6) / 6.6; v = y / 4.6
        h = 3.9 * max(0, 1 - u * u) ** .7 * max(0, 1 - v * v) ** .5 + .25
        if x > 15.8:
            h = max(h - (x - 15.8) * .33, .05)
        h += rr.uniform(-.12, .12)
        grid[i, j] = bm.verts.new((x, y, h))
for i in range(NX):
    for j in range(NY):
        bm.faces.new((grid[i, j], grid[i + 1, j], grid[i + 1, j + 1], grid[i, j + 1]))
ladung = kind(obj_aus(bm, "ladung", ld_m, True)); ladung.location = (0, 0, 4.5)
tx = bpy.data.textures.new("steine", "VORONOI"); tx.noise_scale = .55
dm = ladung.modifiers.new("d", "DISPLACE"); dm.texture = tx; dm.strength = .35; dm.texture_coords = "LOCAL"
# fallende Brocken (von einem Bagger ausserhalb des Bildes)
BROCKEN = []
for i in range(34):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=rr.uniform(.35, .8))
    o = kind(bpy.context.object); o.data.materials.append(ld_m); o.scale = (rr.uniform(.8, 1.3), rr.uniform(.8, 1.3), rr.uniform(.7, 1.1))
    o.rotation_euler = (rr.uniform(0, 6), rr.uniform(0, 6), rr.uniform(0, 6))
    BROCKEN.append((o, rr.uniform(9, 16), rr.uniform(-3.5, 3.5), rr.uniform(0, 1)))

# ---------- Reifen 59/80R63 (~4 m) mit Stollen, Felge
def reifen_mesh():
    bm = bmesh.new(); N = 96
    prof = [(.82, -.6), (1.05, -.7), (1.45, -.77), (1.8, -.76), (1.95, -.62), (1.97, -.3), (1.97, .3), (1.95, .62), (1.8, .76), (1.45, .77), (1.05, .7), (.82, .6)]
    ringe = [[bm.verts.new((r * math.cos(2 * P * k / N), r * math.sin(2 * P * k / N), w)) for k in range(N)] for r, w in prof]
    for r0, r1 in zip(ringe, ringe[1:]):
        for k in range(N):
            bm.faces.new((r0[k], r0[(k + 1) % N], r1[(k + 1) % N], r1[k]))
    for r0, r1 in ((ringe[-1], ringe[0]),):
        for k in range(N):
            bm.faces.new((r0[k], r0[(k + 1) % N], r1[(k + 1) % N], r1[k]))
    L = 42
    for k in range(L):
        for seite_, w0, w1 in ((0, -.68, -.06), (1, .06, .68)):
            a = 2 * P * (k + .5 * seite_) / L; da = 2 * P / L * .42; schief = .09 * (1 if seite_ else -1)
            vs = []
            for rr_ in (1.94, 2.04):
                for (aw, w) in ((a - da, w0), (a + da, w0), (a + da + schief, w1), (a - da + schief, w1)):
                    vs.append(bm.verts.new((rr_ * math.cos(aw), rr_ * math.sin(aw), w)))
            f = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
            for q in f:
                bm.faces.new([vs[i] for i in q])
    me = bpy.data.meshes.new("reifen"); bm.to_mesh(me); bm.free(); me.materials.append(GUMMI)
    for p in me.polygons:
        p.use_smooth = True
    return me


R_ME = reifen_mesh()
RAEDER = []
for x in (4.6, 12.6):
    for y, aussen in ((-4.05, -1), (-2.5, 0), (2.5, 0), (4.05, 1)):
        e = bpy.data.objects.new("rad", None); sc.collection.objects.link(e); e.parent = lkw; e.location = (x, y, 2.04)
        e.rotation_euler = (P / 2, 0, 0); RAEDER.append(e)
        o = bpy.data.objects.new("reifen", R_ME); sc.collection.objects.link(o); o.parent = e
        if aussen:
            # Felge aussen sichtbar: gelber Ring + Scheibe + Nabe + Bolzen
            sz = -aussen * .62  # lokale z-Richtung zeigt nach -y (rotation +90 um x)
            for r_, t_, zz, mm in ((.84, 1.2, 0, GELB), (.7, .08, .62, RAHMEN), (.66, .06, .66, GELB), (.32, .3, .7, RAHMEN)):
                bpy.ops.mesh.primitive_cylinder_add(radius=r_, depth=t_, vertices=48, location=(0, 0, -aussen * zz))
                c = bpy.context.object; c.parent = e; c.data.materials.append(mm)
            for b_ in range(18):
                aa = 2 * P * b_ / 18
                bpy.ops.mesh.primitive_cylinder_add(radius=.05, depth=.12, vertices=8, location=(.5 * math.cos(aa), .5 * math.sin(aa), -aussen * .7))
                c = bpy.context.object; c.parent = e; c.data.materials.append(STAHL)

# ---------- Staub hinter den Hinterraedern
st_m = bpy.data.materials.new("staub"); st_m.use_nodes = True; n = st_m.node_tree.nodes; l = st_m.node_tree.links
for k in list(n):
    n.remove(k)
out = n.new("ShaderNodeOutputMaterial"); df = n.new("ShaderNodeBsdfDiffuse"); tr = n.new("ShaderNodeBsdfTransparent"); mx = n.new("ShaderNodeMixShader")
df.inputs["Color"].default_value = (*hexf("b9a688"), 1)
tc = n.new("ShaderNodeTexCoord"); mp = n.new("ShaderNodeMapping"); nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = .5; nz.inputs["Detail"].default_value = 8
cr = n.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].position = .45; cr.color_ramp.elements[1].position = .8
gr = n.new("ShaderNodeSeparateXYZ"); fade = n.new("ShaderNodeMath"); fade.operation = "MULTIPLY"
l.new(tc.outputs["Object"], mp.inputs[0]); l.new(mp.outputs[0], nz.inputs["Vector"]); l.new(nz.outputs["Fac"], cr.inputs["Fac"])
l.new(tc.outputs["Generated"], gr.inputs[0])
inv = n.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0; l.new(gr.outputs["Z"], inv.inputs[1])
l.new(cr.outputs[0], fade.inputs[0]); l.new(inv.outputs[0], fade.inputs[1])
dichte = n.new("ShaderNodeMath"); dichte.operation = "MULTIPLY"; dichte.inputs[1].default_value = .55; l.new(fade.outputs[0], dichte.inputs[0])
l.new(dichte.outputs[0], mx.inputs["Fac"]); l.new(tr.outputs[0], mx.inputs[1]); l.new(df.outputs[0], mx.inputs[2]); l.new(mx.outputs[0], out.inputs["Surface"])
STAUB_MAP = mp
bpy.ops.mesh.primitive_cone_add(radius1=8, radius2=2.2, depth=40, vertices=48, location=(36, 0, 3.2), rotation=(0, -P / 2, 0))
staub = kind(bpy.context.object); staub.data.materials.append(st_m); staub.visible_shadow = False

# ---------- Messlatten (Laenge/Hoehe), nur in der Mass-Szene
MESS = []
ms_m, _ = mat("mess", hexf("ffd21a"), .3, 0, 4, hexf("ffd21a"))
MESS.append(box(0, 20.6, -6.4, -6.3, .05, .15, ms_m))
for x in (0, 20.6):
    MESS.append(box(x - .05, x + .05, -6.6, -6.1, .05, .9, ms_m))
MESS.append(box(21.3, 21.4, -6.4, -6.3, 0, 8.17, ms_m))
for z in (0, 8.17):
    MESS.append(box(20.9, 21.8, -6.4, -6.3, z - .05, z + .05, ms_m))

# ---------- Menschen (1.8 m) fuer den Reifen-Vergleich
mensch_m, _ = mat("mensch", hexf("e6e2da"), .7)
weste_m, _ = mat("weste", hexf("ff6a00"), .5, 0, .4, hexf("ff6a00"))
helm_m, _ = mat("helm", hexf("ffffff"), .3)
hose_m, _ = mat("hose", hexf("23324a"), .8)
MENSCHEN = []


def mensch(x, y, rot=0):
    obs = []
    bpy.ops.mesh.primitive_uv_sphere_add(radius=.12, location=(x, y, 1.66)); obs.append((bpy.context.object, mensch_m))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=.15, location=(x, y, 1.74)); o = bpy.context.object; o.scale = (1, 1, .55); obs.append((o, helm_m))
    bpy.ops.mesh.primitive_cylinder_add(radius=.2, depth=.62, location=(x, y, 1.22)); obs.append((bpy.context.object, weste_m))
    for dy in (-.1, .1):
        bpy.ops.mesh.primitive_cylinder_add(radius=.08, depth=.92, location=(x, y + dy, .46)); obs.append((bpy.context.object, hose_m))
        bpy.ops.mesh.primitive_cylinder_add(radius=.055, depth=.66, location=(x, y + dy * 2.5, 1.18)); obs.append((bpy.context.object, weste_m))
    for o, m in obs:
        o.data.materials.append(m); kind(o)
        for p in o.data.polygons:
            p.use_smooth = True
    return [o for o, _ in obs]


MENSCHEN += mensch(3.7, -5.75) + mensch(5.5, -5.9)

# ---------- 300 Autos (20 x 15) neben dem Lkw, nur in der Auto-Szene
auto_m = bpy.data.materials.new("autolack"); auto_m.use_nodes = True; n = auto_m.node_tree.nodes; l = auto_m.node_tree.links; b = n["Principled BSDF"]
oi = n.new("ShaderNodeObjectInfo"); l.new(oi.outputs["Color"], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = .25
b.inputs["Metallic"].default_value = .5; b.inputs["Coat Weight"].default_value = .6
bm = bmesh.new()
for (x0, x1, y0, y1, z0, z1) in ((-2.25, 2.25, -.9, .9, .3, 1.0), (-1.2, .9, -.8, .8, 1.0, 1.48)):
    r_ = bmesh.ops.create_cube(bm, size=1)["verts"]
    for v in r_:
        v.co = Vector(((x0 + x1) / 2 + v.co.x * (x1 - x0), (y0 + y1) / 2 + v.co.y * (y1 - y0), (z0 + z1) / 2 + v.co.z * (z1 - z0)))
bmesh.ops.bevel(bm, geom=bm.edges[:], offset=.12, segments=2, affect="EDGES")
auto_me = bpy.data.meshes.new("auto"); bm.to_mesh(auto_me); bm.free(); auto_me.materials.append(auto_m)
FARBEN = ["d9dde2", "1c1d20", "8a9099", "f4f4f2", "9b1c1c", "1f3f7a", "5a5e63", "c9c3b4", "2d4a34", "ece9e2"]
AUTOS = []
rq = random.Random(3)
for i in range(20):
    for j in range(15):
        o = bpy.data.objects.new("pkw", auto_me); sc.collection.objects.link(o); kind(o)
        o.location = (-38 + i * 5.6, -10 - j * 2.7, 0); o.color = (*hexf(rq.choice(FARBEN)), 1); AUTOS.append(o)

# ======================================================================  Tagebau (Open Pit)
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; nt = w.node_tree
sky = nt.nodes.new("ShaderNodeTexSky")
try:
    sky.sky_type = "NISHITA"
except Exception:
    pass
sky.sun_elevation = math.radians(24); sky.sun_rotation = math.radians(205)
try:
    sky.air_density = 2.2; sky.dust_density = 3.0
except Exception:
    pass
nt.links.new(sky.outputs[0], nt.nodes["Background"].inputs[0]); nt.nodes["Background"].inputs[1].default_value = .32
bpy.ops.object.light_add(type="SUN"); sonne = bpy.context.object
sonne.rotation_euler = (math.radians(66), 0, math.radians(205 - 90)); sonne.data.energy = 4.2; sonne.data.color = (1, .9, .78); sonne.data.angle = .02

# Boden: verdichtete Erde, hellere Fahrspur mit Reifenspuren
bd = bpy.data.materials.new("boden"); bd.use_nodes = True; n = bd.node_tree.nodes; l = bd.node_tree.links; b = n["Principled BSDF"]
tc = n.new("ShaderNodeTexCoord"); sp = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Object"], sp.inputs[0])
nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = .08; nz.inputs["Detail"].default_value = 10; l.new(tc.outputs["Object"], nz.inputs["Vector"])
cr = n.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (*hexf("3f3429"), 1); cr.color_ramp.elements[1].color = (*hexf("7a6a56"), 1)
l.new(nz.outputs["Fac"], cr.inputs["Fac"])
ab = n.new("ShaderNodeMath"); ab.operation = "ABSOLUTE"; l.new(sp.outputs["Y"], ab.inputs[0])
spur = n.new("ShaderNodeMapRange"); spur.inputs["From Min"].default_value = 14; spur.inputs["From Max"].default_value = 22
spur.inputs["To Min"].default_value = 1; spur.inputs["To Max"].default_value = 0; l.new(ab.outputs[0], spur.inputs["Value"])
# Reifenspuren: Streifen bei |y| ~ 2.5..4.8 (wave entlang y)
wv = n.new("ShaderNodeTexWave"); wv.wave_type = "BANDS"; wv.bands_direction = "Y"; wv.inputs["Scale"].default_value = .7; wv.inputs["Distortion"].default_value = 6; wv.inputs["Detail"].default_value = 4
l.new(tc.outputs["Object"], wv.inputs["Vector"])
m1 = n.new("ShaderNodeMath"); m1.operation = "MULTIPLY"; m1.inputs[1].default_value = .14; l.new(wv.outputs["Fac"], m1.inputs[0])
m2 = n.new("ShaderNodeMath"); m2.operation = "MULTIPLY"; l.new(m1.outputs[0], m2.inputs[0]); l.new(spur.outputs["Result"], m2.inputs[1])
mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.inputs[7].default_value = (*hexf("8a7a64"), 1)
s3 = n.new("ShaderNodeMath"); s3.operation = "MULTIPLY"; s3.inputs[1].default_value = .55; l.new(spur.outputs["Result"], s3.inputs[0])
l.new(s3.outputs[0], mx.inputs[0]); l.new(cr.outputs[0], mx.inputs[6])
mx2 = n.new("ShaderNodeMix"); mx2.data_type = "RGBA"; mx2.inputs[7].default_value = (*hexf("4a3d30"), 1)
l.new(m2.outputs[0], mx2.inputs[0]); l.new(mx.outputs[2], mx2.inputs[6]); l.new(mx2.outputs[2], b.inputs["Base Color"])
b.inputs["Roughness"].default_value = .96
vo = n.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 6; l.new(tc.outputs["Object"], vo.inputs["Vector"])
bp = n.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = .55; l.new(vo.outputs["Distance"], bp.inputs["Height"]); l.new(bp.outputs[0], b.inputs["Normal"])
bpy.ops.mesh.primitive_plane_add(size=3000); boden = bpy.context.object; boden.data.materials.append(bd)

# Abbau-Terrassen ringsum (gestufte Wand), mit Gesteinsschichten
fels = bpy.data.materials.new("fels"); fels.use_nodes = True; n = fels.node_tree.nodes; l = fels.node_tree.links; b = n["Principled BSDF"]
tc = n.new("ShaderNodeTexCoord"); wv = n.new("ShaderNodeTexWave"); wv.wave_type = "BANDS"; wv.bands_direction = "Z"
wv.inputs["Scale"].default_value = .02; wv.inputs["Distortion"].default_value = 3; wv.inputs["Detail"].default_value = 6
l.new(tc.outputs["Object"], wv.inputs["Vector"])
cr = n.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (*hexf("4a3b2e"), 1); cr.color_ramp.elements[1].color = (*hexf("8c7860"), 1)
e2 = cr.color_ramp.elements.new(.5); e2.color = (*hexf("5c5650"), 1)
e3 = cr.color_ramp.elements.new(.75); e3.color = (*hexf("7a5a40"), 1)
l.new(wv.outputs["Fac"], cr.inputs["Fac"]); b.inputs["Roughness"].default_value = .95
geo = n.new("ShaderNodeNewGeometry"); gs = n.new("ShaderNodeSeparateXYZ"); l.new(geo.outputs["Normal"], gs.inputs[0])
gm = n.new("ShaderNodeMapRange"); gm.inputs["From Min"].default_value = .75; gm.inputs["From Max"].default_value = .95; l.new(gs.outputs["Z"], gm.inputs["Value"])
gmx = n.new("ShaderNodeMix"); gmx.data_type = "RGBA"; gmx.inputs[7].default_value = (*hexf("8d7a63"), 1)
dk = n.new("ShaderNodeMix"); dk.data_type = "RGBA"; dk.inputs[0].default_value = .35; dk.inputs[7].default_value = (*hexf("2e261f"), 1)
l.new(cr.outputs[0], dk.inputs[6]); l.new(dk.outputs[2], gmx.inputs[6]); l.new(gm.outputs["Result"], gmx.inputs[0]); l.new(gmx.outputs[2], b.inputs["Base Color"])
nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = .3; nz.inputs["Detail"].default_value = 12; l.new(tc.outputs["Object"], nz.inputs["Vector"])
bp = n.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 1.0; l.new(nz.outputs["Fac"], bp.inputs["Height"]); l.new(bp.outputs[0], b.inputs["Normal"])
bm = bmesh.new(); NA = 240; prof = []
r0 = 230.0; z0 = 0.0
for k in range(9):
    prof += [(r0, z0), (r0 + 2, z0 + 5), (r0 + 3.5, z0 + 10), (r0 + 4.5, z0 + 14), (r0 + 12, z0 + 14.3), (r0 + 22, z0 + 14.6)]
    r0 -= 4
    r0 += 26; z0 += 14.6
prof += [(r0 + 400, z0 + 10)]
ringe = []
for r, z in prof:
    ringe.append([bm.verts.new((r * math.cos(2 * P * a / NA), r * math.sin(2 * P * a / NA), z)) for a in range(NA)])
for ra, rb in zip(ringe, ringe[1:]):
    for a in range(NA):
        bm.faces.new((ra[a], ra[(a + 1) % NA], rb[(a + 1) % NA], rb[a]))
wand = obj_aus(bm, "terrassen", fels, True); wand.location = (-40, 0, 0)
tw = bpy.data.textures.new("wandtex", "CLOUDS"); tw.noise_scale = 6; tw.noise_depth = 4
dw = wand.modifiers.new("d", "DISPLACE"); dw.texture = tw; dw.strength = 3; dw.texture_coords = "GLOBAL"; dw.mid_level = .5
# Felsbrocken und Abraumhaufen am Rand der Fahrstrasse
rs = random.Random(11)
for i in range(60):
    x = rs.uniform(-260, 160); y = rs.choice((-1, 1)) * rs.uniform(26, 120)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1, location=(x, y, 0))
    o = bpy.context.object; s_ = rs.uniform(.6, 2.4); o.scale = (s_ * rs.uniform(1, 1.8), s_ * rs.uniform(1, 1.6), s_ * rs.uniform(.5, .9))
    o.rotation_euler = (0, 0, rs.uniform(0, 6)); o.data.materials.append(fels)
    dd = o.modifiers.new("d", "DISPLACE"); dd.texture = tw; dd.strength = .5
for i in range(7):
    x = rs.uniform(-200, 140); y = rs.choice((-1, 1)) * rs.uniform(60, 150)
    bpy.ops.mesh.primitive_cone_add(radius1=rs.uniform(18, 30), radius2=1, depth=rs.uniform(9, 16), vertices=48, location=(x, y, 4))
    o = bpy.context.object; o.data.materials.append(fels)
    bpy.ops.object.modifier_add(type="SUBSURF"); o.modifiers[-1].levels = 2; o.modifiers[-1].render_levels = 2
    dd = o.modifiers.new("d", "DISPLACE"); dd.texture = tw; dd.strength = 2.5
# Strommasten / Lichtmasten entlang der Strasse
for i in range(8):
    x = -250 + i * 55
    zyl((x, 30, 0), (x, 30, 14), .18, RAHMEN, 10, eltern=boden)
    box(x - .9, x + .9, 29.8, 30.2, 13.6, 14.2, RAHMEN, eltern=boden)

# ======================================================================  Kamera + Ablauf
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam; cam.data.lens = 30; cam.data.clip_end = 5000; cam.data.sensor_fit = "VERTICAL"
cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = 8


def ease(x):
    x = min(1, max(0, x)); return x * x * (3 - 2 * x)


def lerpv(a, b, k):
    return tuple(x + (y - x) * k for x, y in zip(a, b))


D = A.dauer
t_name, t_mass, t_reifen, t_leer, t_last, t_autos, t_gwr, t_ende = 3.2, 5.66, 9.6, 15.04, 18.82, 22.56, 24.94, 28.7
STOP = (t_reifen - .05, t_gwr - .05)
V = 5.0
START = ((-22, -13, 1.4), (6, 0, 4.6))
KEYS = [(0, *START), (t_name - .1, (-18.5, -11.5, 1.6), (6, 0, 4.6)),
        (t_name, (1, -31, 2.4), (9, 0, 4.2)), (t_mass - .1, (7, -29.5, 2.8), (10, 0, 4.2)),
        (t_mass, (10.0, -60, 4.4), (10.0, 0, 4.4)), (t_reifen - .1, (10.0, -56, 4.6), (10.0, 0, 4.4)),
        (t_reifen, (-3, -15.5, 1.3), (4.6, -4.6, 2.3)), (t_leer - .1, (-.6, -13.6, 1.6), (4.6, -4.6, 2.4)),
        (t_leer, (-9, -16, 25), (10.5, 0, 5)), (t_last - .1, (-6.5, -18.5, 24), (10.5, 0, 5)),
        (t_last, (-5, -19.5, 22), (10.5, 0, 5.5)), (t_autos - .1, (1, -22, 20.5), (10.5, 0, 5.5)),
        (t_autos, (18, -118, 78), (14, -27, 0)), (t_gwr - .1, (16, -110, 72), (14, -27, 0)),
        (t_gwr, (34, -15, 1.8), (10, 0, 4.5)), (t_ende, (17, -24, 8.5), (8, 0, 4.5)),
        (D - .9, *START), (D, *START)]


def weg(t):
    if t < STOP[0]:
        return V * t
    if t < STOP[1]:
        return V * STOP[0]
    return V * (STOP[0] + t - STOP[1])


def zustand(t):
    faehrt = not (STOP[0] <= t < STOP[1])
    x = weg(t)
    lkw.location = (-x, 0, (.025 * math.sin(t * 9) + .015 * math.sin(t * 23)) if faehrt else 0)
    lkw.rotation_euler = (.003 * math.sin(t * 5.3) if faehrt else 0, 0, 0)
    for r in RAEDER:
        r.rotation_euler = (P / 2, -x / 2.04, 0)
    STAUB_MAP.inputs["Location"].default_value = (x * .05, 0, t * .25)
    staub.hide_render = not faehrt
    for o in MESS:
        o.hide_render = not (t_mass <= t < t_reifen)
    for o in MENSCHEN:
        o.hide_render = not (t_reifen <= t < t_leer)
    for o in AUTOS:
        o.hide_render = not (t_autos <= t < t_gwr)
    # Ladung: leer ab t_leer, waechst waehrend t_last..t_autos
    if t_leer <= t < t_last:
        lad = 0.0
    elif t_last <= t < t_autos:
        lad = ease((t - t_last - .4) / 3.0)
    else:
        lad = 1.0
    ladung.hide_render = lad < .02; ladung.scale = (1, 1, max(lad, .02))
    for o, bx, by, phase in BROCKEN:
        t0 = t_last + .1 + phase * 2.9; tt = t - t0
        z_land = 4.5 + 3.6 * lad * .9 + .3
        z = 26 - 9.81 * .5 * tt * tt * 1.4
        sichtbar = t_last <= t < t_autos and tt >= 0 and z > z_land
        o.hide_render = not sichtbar
        if sichtbar:
            o.location = (bx, by, z); o.rotation_euler[0] += 0
    for a, b in zip(KEYS, KEYS[1:]):
        if a[0] <= t <= b[0]:
            k = ease((t - a[0]) / max(b[0] - a[0], 1e-6)); pos = lerpv(a[1], b[1], k); ziel = lerpv(a[2], b[2], k); break
    else:
        pos, ziel = KEYS[-1][1], KEYS[-1][2]
    wackel = .03 if faehrt else 0
    if t_last + .6 <= t < t_autos:
        wackel = .05   # Brocken schlagen ein
    pos = (pos[0] - x, pos[1] + wackel * math.sin(t * 27), pos[2] + wackel * math.sin(t * 31))
    ziel = (ziel[0] - x, ziel[1], ziel[2])
    cam.location = Vector(pos); d = Vector(ziel) - Vector(pos); cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.dof.focus_distance = d.length


os.makedirs(A.ordner, exist_ok=True)
N = int(round(D * A.fps))
liste = [int(round(float(x) * A.fps)) for x in A.nur.split(",")] if A.nur else list(range(A.start, N))
for f in liste:
    pfad = os.path.join(A.ordner, f"belaz_{f:04d}.png")
    if os.path.exists(pfad) and not A.nur:
        continue
    zustand(f / A.fps); sc.render.filepath = pfad
    bpy.ops.render.render(write_still=True); print("FERTIG", pfad, flush=True)
