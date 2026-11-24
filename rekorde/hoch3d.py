"""Hochsprung 2,45 m (Javier Sotomayor, Salamanca 27.7.1993, World Athletics/GWR). Realistischer Stil (Vorlage heben3d.py).
Birmingham 5.9.2026; vorher 510 kg Bjoernsson 2025).
Realistischer Stil: Foto-Texturen (ambientCG, CC0), HDRI-Reflexionen (Poly Haven, CC0), runde/geglaettete Formen,
Stange biegt sich (Shape Key), Hantelscheiben als Drehkoerper, Fachwerk-Traversen, Moving Heads mit Lichtkegeln,
Publikum aus runden Figuren, LED-Wand, Anzeige "511 KG", Kreide-Schale.
python3 heben3d.py <ordner> [--nur t1,t2] [--start i] [--samples n]"""
import bpy, bmesh, math, random, sys, os, argparse
from mathutils import Vector, Matrix, Euler
HIER = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HIER)
import mensch_mh as MH

ap = argparse.ArgumentParser()
ap.add_argument("ordner"); ap.add_argument("--nur", default=""); ap.add_argument("--skala", type=int, default=50)
ap.add_argument("--samples", type=int, default=12); ap.add_argument("--fps", type=int, default=15)
ap.add_argument("--start", type=int, default=0)
A = ap.parse_args(sys.argv[1:])
P = math.pi
D = 23.8
ASSET = os.path.join(os.path.dirname(HIER), "assets")
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = A.samples; sc.cycles.use_denoising = True
sc.cycles.max_bounces = 5; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 3; sc.cycles.transmission_bounces = 2
sc.cycles.transparent_max_bounces = 8; sc.cycles.adaptive_threshold = .03
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1080, 1920, A.skala
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"; sc.view_settings.exposure = -.3
hexf = MH.hexf


def ease(x):
    x = min(1, max(0, x)); return x * x * (3 - 2 * x)


def lerpv(a, b, k):
    return Vector(a).lerp(Vector(b), k)


def mat(name, farbe, rau=.5, metal=0, **kw):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*hexf(farbe), 1); b.inputs["Roughness"].default_value = rau; b.inputs["Metallic"].default_value = metal
    for k, v in kw.items():
        b.inputs[k.replace("_", " ")].default_value = v
    return m


def pbr(name, tex, skala=1.0, tint=None, rau_mul=1.0, rau_add=0.0, metal=0.0, normal=1.0, coat=0.0):
    """Foto-Textur (ambientCG) mit Box-Projektion auf Objektkoordinaten."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; n = nt.nodes; l = nt.links; b = n["Principled BSDF"]
    pfad = os.path.join(ASSET, tex, f"{tex}_1K-JPG")
    tc = n.new("ShaderNodeTexCoord"); mp = n.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (skala, skala, skala)
    l.new(tc.outputs["Object"], mp.inputs[0])

    def bild(suffix, farbe=True):
        if not os.path.exists(pfad + suffix):
            return None
        t = n.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(pfad + suffix, check_existing=True)
        if not farbe:
            t.image.colorspace_settings.name = "Non-Color"
        t.projection = "BOX"; t.projection_blend = .25; l.new(mp.outputs[0], t.inputs[0]); return t
    c = bild("_Color.jpg")
    if c:
        if tint:
            mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"; mx.inputs[0].default_value = 1
            l.new(c.outputs[0], mx.inputs[6]); mx.inputs[7].default_value = (*hexf(tint), 1); l.new(mx.outputs[2], b.inputs["Base Color"])
        else:
            l.new(c.outputs[0], b.inputs["Base Color"])
    r = bild("_Roughness.jpg", False)
    if r:
        ma = n.new("ShaderNodeMath"); ma.operation = "MULTIPLY_ADD"; ma.inputs[1].default_value = rau_mul; ma.inputs[2].default_value = rau_add
        l.new(r.outputs[0], ma.inputs[0]); l.new(ma.outputs[0], b.inputs["Roughness"])
    nm = bild("_NormalGL.jpg", False)
    if nm:
        nmap = n.new("ShaderNodeNormalMap"); nmap.inputs["Strength"].default_value = normal; l.new(nm.outputs[0], nmap.inputs["Color"])
        l.new(nmap.outputs[0], b.inputs["Normal"])
    b.inputs["Metallic"].default_value = metal
    if coat:
        b.inputs["Coat Weight"].default_value = coat; b.inputs["Coat Roughness"].default_value = .12
    return m


def emis(name, farbe, st):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0, 0, 0, 1); b.inputs["Emission Color"].default_value = (*hexf(farbe), 1)
    b.inputs["Emission Strength"].default_value = st; return m


def glatt(o, sub=1, bevel=0.0, seg=3):
    if bevel:
        bv = o.modifiers.new("b", "BEVEL"); bv.width = bevel; bv.segments = seg; bv.limit_method = "ANGLE"
    if sub:
        s = o.modifiers.new("s", "SUBSURF"); s.levels = sub; s.render_levels = sub
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def box(name, groesse, ort, m, bevel=.01, seg=3, rot=(0, 0, 0), eltern=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=ort, rotation=rot); o = bpy.context.object; o.name = name; o.scale = groesse
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        bv = o.modifiers.new("b", "BEVEL"); bv.width = bevel; bv.segments = seg
        for p in o.data.polygons:
            p.use_smooth = True
        o.data.shade_auto_smooth() if hasattr(o.data, "shade_auto_smooth") else None
    o.data.materials.append(m)
    if eltern:
        o.parent = eltern
    return o


def zyl(name, r, l, ort, m, rot=(0, 0, 0), eltern=None, v=32):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=l, vertices=v, location=ort, rotation=rot); o = bpy.context.object; o.name = name
    o.data.materials.append(m)
    bv = o.modifiers.new("b", "BEVEL"); bv.width = min(r, l) * .12; bv.segments = 2; bv.limit_method = "ANGLE"
    for p in o.data.polygons:
        p.use_smooth = True
    if eltern:
        o.parent = eltern
    return o


def rohr(name, a, b, r, m, eltern=None, v=10):
    a, b = Vector(a), Vector(b); d = b - a
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d.length, vertices=v, location=(a + b) / 2); o = bpy.context.object; o.name = name
    o.rotation_mode = "QUATERNION"; o.rotation_quaternion = d.to_track_quat("Z", "Y"); o.data.materials.append(m)
    for p in o.data.polygons:
        p.use_smooth = True
    if eltern:
        o.parent = eltern
    return o


def leer(name, ort=(0, 0, 0), eltern=None):
    o = bpy.data.objects.new(name, None); sc.collection.objects.link(o); o.location = ort
    if eltern:
        o.parent = eltern
    return o


def dreh_koerper(name, profil, m, nv=64):
    """profil: [(y, r)] - Drehkoerper um die y-Achse"""
    bm = bmesh.new(); ringe = []
    for y, r in profil:
        ringe.append([bm.verts.new((r * math.cos(2 * P * k / nv), y, r * math.sin(2 * P * k / nv))) for k in range(nv)])
    for a, b in zip(ringe, ringe[1:]):
        for k in range(nv):
            bm.faces.new((a[k], a[(k + 1) % nv], b[(k + 1) % nv], b[k]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o); me.materials.append(m)
    for p in me.polygons:
        p.use_smooth = True
    return o


def trimmen(o, gruppen, z_min=None, z_max=None):
    idx = {g.index: g.name for g in o.vertex_groups}
    me = o.data; rz = me.attributes.get("rest_z")
    zv = [0.0] * len(me.vertices)
    if rz:
        rz.data.foreach_get("value", zv)
    bm = bmesh.new(); bm.from_mesh(me); dl = bm.verts.layers.deform.active; bm.verts.ensure_lookup_table()
    weg = []
    for v in bm.verts:
        w = sum(val for gi, val in v[dl].items() if idx.get(gi, "").startswith(gruppen)) if dl else 0
        z = zv[v.index]
        if w > .4 or (z_min is not None and z < z_min) or (z_max is not None and z > z_max):
            weg.append(v)
    bmesh.ops.delete(bm, geom=weg, context="VERTS"); bm.to_mesh(me); bm.free()


# ======================================================================  Springer (MPFB) - zuerst, Materialien danach
import mensch_echt as ME
H = ME.mensch("springer", 31, 1.0, .35, .8, .15, haut="african", haare="short04", braue="eyebrow002")
BIB = ME.logo_bild(os.path.join(HIER, "_bib_hoch.png"), "142", farbe=(.05, .05, .05), symbol=False, hintergrund=(.97, .97, .95), num=True, unterzeile="SALAMANCA 93")
LOGO = ME.logo_bild(os.path.join(HIER, "_logo_norda.png"), "NORDA", farbe=(1, 1, 1))
ME.trikot(H, "singlet", "shorts", "8c0d14", "0d2a6b", brust=BIB, brust_mass=(.19, .13), bein=LOGO)
for o in H.huellen:
    if "versatz" in o.modifiers:
        o.modifiers["versatz"].strength = .011 if o.name.endswith("_hemd") else .004
BN = H.rig.data.bones
PEL = BN["upperleg01.L"].head_local.copy(); PEL.x = 0
KOERPER_H = max(v.z for v in H.EV)
SK = 1.93 / KOERPER_H; H.rig.scale = (SK, SK, SK)
print("GROESSE", KOERPER_H, SK)

# ======================================================================  Materialien
WEISSLACK = mat("weisslack", "f2f2f0", .25, Coat_Weight=.5)
STAHL = pbr("stahl", "Metal012", 6, rau_mul=.6, rau_add=.15, metal=1.0)
TARTAN = pbr("tartan", "Rubber004", 1.6, tint="c0472f", rau_mul=1.0, normal=1.4)
RASEN = pbr("rasen", "Grass004", .35, normal=.8)
MATTE = pbr("matte", "Fabric048", 1.2, tint="2457c9", normal=1.2, rau_mul=.9)
MATTE_S = pbr("matte_seite", "Fabric030", 3, tint="183d94")
SCHUH = mat("schuh", "1a1a1a", .4)

LINIE = mat("linie", "f4f4f0", .6)
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; nt = w.node_tree
env = nt.nodes.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(os.path.join(ASSET, "tag.hdr"))
mpw = nt.nodes.new("ShaderNodeMapping"); tcw = nt.nodes.new("ShaderNodeTexCoord"); nt.links.new(tcw.outputs["Generated"], mpw.inputs[0])
mpw.inputs["Rotation"].default_value = (0, 0, math.radians(200)); nt.links.new(mpw.outputs[0], env.inputs[0])
nt.links.new(env.outputs[0], nt.nodes["Background"].inputs[0]); nt.nodes["Background"].inputs[1].default_value = .7

# ======================================================================  Anlage: Rasen, Tartan-Halbrund, Laufbahn, Linien
box("rasen", (400, 400, .02), (0, 0, -.012), RASEN, 0)
bm = bmesh.new(); mitte = bm.verts.new((0, 2, 0)); rand = []
for k in range(65):
    a = P + P * k / 64
    rand.append(bm.verts.new((26 * math.cos(a), 2 + 20 * math.sin(a), 0)))
for a, b in zip(rand, rand[1:]):
    bm.faces.new((mitte, a, b))
me = bpy.data.meshes.new("anlauf"); bm.to_mesh(me); bm.free()
anl = bpy.data.objects.new("anlauf", me); sc.collection.objects.link(anl); me.materials.append(TARTAN); anl.location.z = .003
box("anlauf_vorne", (52, 6, .006), (0, 4.5, .003), TARTAN, 0)
for k in range(9):                                     # Laufbahn hinter der Matte
    box("bahn", (220, 1.22, .006), (0, 9 + k * 1.22, .003), TARTAN, 0)
    box("bahnlinie", (220, .05, .004), (0, 9 - .61 + k * 1.22, .008), LINIE, 0)
# Anlauf-Markierungen (Klebeband) und Absprung-Zone
for (x_, y_) in ((7.4, -11.0), (3.6, -4.6), (1.4, -1.9)):
    box("marke", (.25, .05, .003), (x_, y_, .008), mat("band", "f2d21a", .5) if not bpy.data.materials.get("band") else bpy.data.materials["band"], 0)

# ======================================================================  Hochsprunganlage
LATTE_Z = 2.45
for s in (-1, 1):
    x_ = s * 2.01
    zyl("staender_fuss", .28, .05, (x_, 0, .025), WEISSLACK)
    zyl("staender", .035, 2.9, (x_, 0, 1.47), WEISSLACK)
    box("staender_skala", (.012, .07, 2.6), (x_ - s * .04, -.03, 1.35), mat("skala", "1a1a1a", .5) if not bpy.data.materials.get("skala") else bpy.data.materials["skala"], .004)
    box("schlitten", (.09, .11, .12), (x_ - s * .02, 0, LATTE_Z - .06), STAHL, .01)
    rohr("auflage", (x_ - s * .05, 0, LATTE_Z - .03), (x_ - s * .11, 0, LATTE_Z - .03), .012, STAHL)
# Latte mit Ringelfarben
latte_m = bpy.data.materials.new("latte"); latte_m.use_nodes = True; n = latte_m.node_tree.nodes; l = latte_m.node_tree.links; b = n["Principled BSDF"]
tc = n.new("ShaderNodeTexCoord"); sp = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Object"], sp.inputs[0])
mo = n.new("ShaderNodeMath"); mo.operation = "PINGPONG"; mo.inputs[1].default_value = .2; l.new(sp.outputs["Z"], mo.inputs[0])
gt = n.new("ShaderNodeMath"); gt.operation = "GREATER_THAN"; gt.inputs[1].default_value = .1; l.new(mo.outputs[0], gt.inputs[0])
mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.inputs[6].default_value = (*hexf("f5f5f2"), 1); mx.inputs[7].default_value = (*hexf("d01a1a"), 1)
l.new(gt.outputs[0], mx.inputs[0]); l.new(mx.outputs[2], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = .3
b.inputs["Coat Weight"].default_value = .5
LATTE = zyl("latte", .016, 4.0, (0, 0, LATTE_Z), latte_m, rot=(0, P / 2, 0), v=24)
# Landematte (gesteppt), Vorderteil und Unterbau
matte = box("matte", (6.0, 4.0, .62), (0, 2.45, .41), MATTE, .09, seg=4)
box("matte_sockel", (6.1, 4.1, .12), (0, 2.45, .06), MATTE_S, .03)
box("matte_vorne_l", (1.6, .55, .55), (-2.2, .2, .345), MATTE, .08, seg=4)
box("matte_vorne_r", (1.6, .55, .55), (2.2, .2, .345), MATTE, .08, seg=4)
box("matte_abdeckung", (6.2, .05, .9), (0, .5 - .03, .45), MATTE_S, .02)
MATTE_Z = .72
# Hoehenanzeige (LED-Tafel) neben dem Staender
box("tafel", (.9, .08, .55), (3.4, -.6, 1.1), mat("tafelgeh", "151515", .4), .02)
zyl("tafelfuss", .03, .85, (3.4, -.6, .43), STAHL)
bpy.ops.object.text_add(location=(3.4, -.65, 1.02), rotation=(P / 2, 0, 0)); TAF = bpy.context.object
TAF.data.body = "2.45"; TAF.data.align_x = "CENTER"; TAF.data.size = .32; TAF.data.extrude = .005
TAF.data.materials.append(emis("tafeltext", "ffb020", 18))
# Kampfrichter-Stuehle + Windsack
for i, (x_, y_) in enumerate(((4.6, -1.2), (5.3, -1.0))):
    box("stuhl", (.45, .45, .45), (x_, y_, .45), mat("stuhl%d" % i, "e6e6e6", .5), .03)
zyl("windmast", .025, 3.2, (-6, -3, 1.6), STAHL)
bpy.ops.mesh.primitive_cone_add(radius1=.15, radius2=.07, depth=.8, location=(-6.38, -3, 3.05), rotation=(0, P / 2, 0))
bpy.context.object.data.materials.append(mat("windsack", "ff6a00", .6, Sheen_Weight=.5))

# ======================================================================  Stadion: Tribuenen-Oval, Dach, Flutlicht-Masten, Publikum
MITTE = Vector((-10, 40, 0)); RA, RB = 105, 78
trib_m = pbr("tribuene", "Concrete034", .2, tint="8a8a8a")
sitz_m = mat("sitze", "1e5bb0", .45)
bm = bmesh.new(); NRG = 180; STUF = 30; ringe = []
for s_ in range(STUF + 1):
    rr = 1 + s_ * .01; hz = .8 + s_ * .9
    ringe.append([bm.verts.new((MITTE.x + RA * rr * math.cos(2 * P * j / NRG), MITTE.y + RB * rr * math.sin(2 * P * j / NRG), hz)) for j in range(NRG)])
for a, b_ in zip(ringe, ringe[1:]):
    for j in range(NRG):
        bm.faces.new((a[j], a[(j + 1) % NRG], b_[(j + 1) % NRG], b_[j]))
me = bpy.data.meshes.new("tribuene"); bm.to_mesh(me); bm.free()
trib = bpy.data.objects.new("tribuene", me); sc.collection.objects.link(trib); me.materials.append(sitz_m)
dach_m = mat("dach", "d0d4d9", .35, .6)
bm = bmesh.new(); ri, ra_ = [], []
for j in range(NRG):
    a = 2 * P * j / NRG
    ri.append(bm.verts.new((MITTE.x + RA * 1.2 * math.cos(a), MITTE.y + RB * 1.2 * math.sin(a), 34)))
    ra_.append(bm.verts.new((MITTE.x + RA * 1.5 * math.cos(a), MITTE.y + RB * 1.5 * math.sin(a), 37)))
for j in range(NRG):
    bm.faces.new((ri[j], ri[(j + 1) % NRG], ra_[(j + 1) % NRG], ra_[j]))
me = bpy.data.meshes.new("dach"); bm.to_mesh(me); bm.free(); dach = bpy.data.objects.new("dach", me); sc.collection.objects.link(dach)
me.materials.append(dach_m); dach.modifiers.new("d", "SOLIDIFY").thickness = .6
fl_m = emis("flutlicht", "fff4e2", 25)
for j in range(0, NRG, 6):
    a = 2 * P * j / NRG
    box("fluter", (2.0, 2.0, .2), (MITTE.x + RA * 1.21 * math.cos(a), MITTE.y + RB * 1.21 * math.sin(a), 33.6), fl_m, 0)
r = random.Random(4)
koerper_me = []
for i, f in enumerate(["c62828", "1565c0", "f2f2f2", "2e7d32", "212121", "f9a825", "6a1b9a", "455a64", "ef6c00"]):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=7, radius=1, matrix=Matrix.Translation((0, 0, .45)) @ Matrix.Diagonal((.24, .17, .34, 1)))
    bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=7, radius=.1, matrix=Matrix.Translation((0, 0, .93)))
    me = bpy.data.meshes.new("pub%d" % i); bm.to_mesh(me); bm.free(); me.materials.append(mat("pubm%d" % i, f, .8, Sheen_Weight=.4))
    for p in me.polygons:
        p.use_smooth = True
    koerper_me.append(me)
for s_ in range(0, STUF, 1):
    rr = 1 + (s_ + .5) * .01; hz = .8 + (s_ + .5) * .9
    for j in range(560):
        if r.random() < .15:
            continue
        a = 2 * P * (j + r.random() * .5) / 560
        o = bpy.data.objects.new("pub", r.choice(koerper_me)); sc.collection.objects.link(o)
        o.location = (MITTE.x + RA * rr * math.cos(a), MITTE.y + RB * rr * math.sin(a), hz - .05); o.rotation_euler = (0, 0, a + P / 2 + P / 2)
# Sonne passend zum HDRI + Flutlicht als Flaechenlichter
bpy.ops.object.light_add(type="SUN"); sonne = bpy.context.object; sonne.data.energy = 3.0; sonne.data.angle = .02
sonne.rotation_euler = Euler((math.radians(50), 0, math.radians(150))); sonne.data.color = (1, .9, .78)
for (x_, y_) in ((-40, -20), (30, -25), (-40, 80), (30, 85)):
    bpy.ops.object.light_add(type="AREA", location=(x_, y_, 36)); L = bpy.context.object; L.data.size = 12; L.data.energy = 90000
    L.rotation_euler = (Vector((0, 0, 0)) - L.location).to_track_quat("-Z", "Y").to_euler(); L.data.color = (1, .96, .9)

# ======================================================================  Ablauf
T_LOS, T_ABS = 7.3, 9.6                 # Anlauf, Absprung
FLUG = 1.215
T_LAND = T_ABS + FLUG
P0 = Vector((7.4, -11.0, 0)); P1 = Vector((3.6, -4.6, 0)); P2 = Vector((1.5, -1.95, 0)); PT = Vector((.6, -.95, 0))


def bez(k):
    a = P0.lerp(P1, k); b_ = P1.lerp(P2, k); c = P2.lerp(PT, k)
    return a.lerp(b_, k).lerp(b_.lerp(c, k), k)


BEZ = [bez(i / 400) for i in range(401)]
LANG = [0.0]
for a, b_ in zip(BEZ, BEZ[1:]):
    LANG.append(LANG[-1] + (b_ - a).length)
L_GES = LANG[-1]


def anlauf(t):
    """Weg (0..L_GES) mit Beschleunigung, Richtung"""
    k = max(0, min(1, (t - T_LOS) / (T_ABS - T_LOS)))
    s_ = L_GES * (.55 * k * k + .45 * k)
    i = max(1, min(400, next((j for j, v in enumerate(LANG) if v >= s_), 400)))
    p = BEZ[i]; d = (BEZ[i] - BEZ[i - 1]).normalized()
    return p, d, s_


def yaw_von(d):
    return math.atan2(d.x, -d.y)


def q(rx=0, ry=0, rz=0):
    return Euler((rx, ry, rz)).to_quaternion()


_, D_END, _ = anlauf(T_ABS)
YAW_END = yaw_von(D_END)
Q_TAKE = q(rz=YAW_END) @ q(rx=-.18)
Q_UP = q(rx=-.35)
Q_PEAK = q(rx=-P / 2 - .05)
Q_LAND = q(rx=-P / 2 - .6)
PT3 = Vector((.6, -.95, 1.05)); PL3 = Vector((-.35, 1.5, MATTE_Z + .11))
VZ = math.sqrt(2 * 9.81 * (2.76 - 1.05))


def flug_pos(tf):
    u = tf / FLUG
    xy = PT3.lerp(PL3, u)
    z = 1.05 + VZ * tf - 4.905 * tf * tf
    return Vector((xy.x, xy.y, max(z, MATTE_Z + .11)))


def setze(rot_q, pel):
    H.rig.rotation_mode = "QUATERNION"; H.rig.rotation_quaternion = rot_q
    H.rig.location = pel - rot_q.to_matrix() @ (PEL * SK)


def figuren(t):
    H.zuruecksetzen()
    LATTE.location.z = LATTE_Z + (.012 * math.exp(-(t - 10.05) * 4) * math.sin((t - 10.05) * 45) if t > 10.05 else 0)
    if t < T_LOS:                                   # Vorbereitung am Anlaufstart: wippen, konzentrieren
        wipp = math.sin(t * 2.4)
        setze(q(rz=yaw_von((P1 - P0).normalized())) @ q(rx=.05 + .04 * wipp), P0 + Vector((0, 0, PEL.z * SK - .02 + .015 * wipp)))
        H.dreh("upperarm01.L", z=-.62 + .06 * wipp); H.dreh("upperarm01.R", z=.62 - .06 * wipp)
        H.dreh("lowerarm01.L", x=-.3); H.dreh("lowerarm01.R", x=-.3); H.dreh("upperleg01.L", x=-.15 * max(0, wipp))
        H.dreh("lowerleg01.L", x=.3 * max(0, wipp)); H.dreh("neck01", x=.12)
    elif t < T_ABS - .12:                          # Anlauf (J-Kurve), Kurvenlage nach innen
        p, d, s_ = anlauf(t)
        kurv = max(0, (s_ - LANG[150]) / (L_GES - LANG[150]))
        kraft = min(1, .6 + (t - T_LOS) * .4)
        ph = s_ / 2.1 * P
        setze(q(rz=yaw_von(d)) @ q(ry=-.22 * kurv) @ q(rx=.18 - .1 * kurv), p + Vector((0, 0, PEL.z * SK - .05 + .05 * abs(math.sin(ph)))))
        s, c = math.sin(ph), math.cos(ph)
        H.dreh("upperleg01.L", x=-.95 * s * kraft - .35); H.dreh("upperleg01.R", x=.95 * s * kraft - .35)
        H.dreh("lowerleg01.L", x=.4 + 1.1 * max(0, c) * kraft); H.dreh("lowerleg01.R", x=.4 + 1.1 * max(0, -c) * kraft)
        H.dreh("upperarm01.L", z=-.65, x=1.0 * s * kraft + .2); H.dreh("upperarm01.R", z=.65, x=-1.0 * s * kraft + .2)
        H.dreh("lowerarm01.L", x=-1.4); H.dreh("lowerarm01.R", x=-1.4); H.dreh("neck01", x=-.05)
    elif t < T_ABS:                                # Stemmschritt: Ruecklage, Schwungknie hoch
        k = ease((t - (T_ABS - .12)) / .12)
        setze(q(rz=YAW_END) @ q(rx=-.18 * k), PT + Vector((0, 0, PEL.z * SK - .05)))
        H.dreh("upperleg01.R", x=-1.5 * k); H.dreh("lowerleg01.R", x=1.7 * k); H.dreh("upperleg01.L", x=.1)
        H.dreh("upperarm01.L", z=-.4, x=1.6 * k); H.dreh("upperarm01.R", z=.4, x=1.6 * k)
    elif t < T_LAND:                               # Flop
        tf = t - T_ABS; u = tf / FLUG
        if u < .2:
            rq = Q_TAKE.slerp(Q_UP, ease(u / .2))
        elif u < .4:
            rq = Q_UP.slerp(Q_PEAK, ease((u - .2) / .2))
        else:
            rq = Q_PEAK.slerp(Q_LAND, ease((u - .45) / .55))
        setze(rq, flug_pos(tf))
        kn = max(0, 1 - u / .3)                                    # Schwungknie loest sich
        bog = math.sin(min(1, max(0, (u - .2) / .45)) * P / 2) * (1 - ease((u - .62) / .2))   # Bruecke ueber der Latte
        kick = ease((u - .58) / .25)                                # Beine hoch, Kinn zur Brust
        for sd in ("L", "R"):
            H.dreh("upperleg01." + sd, x=(-1.5 * kn if sd == "R" else 0) + .35 * bog - 1.4 * kick)
            H.dreh("lowerleg01." + sd, x=(1.7 * kn if sd == "R" else .1) + 1.5 * bog * (1 - kick) + .2 * kick)
        for b_ in ("spine01", "spine02", "spine03"):
            H.dreh(b_, x=-.28 * bog + .18 * kick)
        H.dreh("neck01", x=-.55 * bog + .6 * kick); H.dreh("neck02", x=-.2 * bog)
        H.dreh("upperarm01.L", z=-.62 * (1 - kn) - .4 * kn, x=1.6 * kn); H.dreh("upperarm01.R", z=.62 * (1 - kn) + .4 * kn, x=1.6 * kn)
    else:                                          # Landung, liegen, aufsitzen, jubeln
        tl = t - T_LAND
        if tl < 1.0:
            setze(Q_LAND.slerp(q(rx=-P / 2 - .15), ease(tl / .6)), PL3 + Vector((0, 0, -.06 * math.exp(-tl * 5) * math.sin(tl * 18))))
            H.dreh("upperleg01.L", x=-1.4 * (1 - ease(tl / .8))); H.dreh("upperleg01.R", x=-1.4 * (1 - ease(tl / .8)))
            H.dreh("upperarm01.L", z=-.3); H.dreh("upperarm01.R", z=.3)
        else:
            k = ease((tl - 1.0) / .8)
            rq = q(rx=-P / 2 - .15).slerp(q(rx=0), k)
            setze(rq, PL3 + Vector((0, 0, .0)))
            H.dreh("upperleg01.L", x=-1.45 * k); H.dreh("upperleg01.R", x=-1.45 * k)
            H.dreh("lowerleg01.L", x=.5 * k); H.dreh("lowerleg01.R", x=.5 * k)
            j = ease((tl - 1.8) / .5)
            H.dreh("upperarm01.L", z=-.72 + 3.3 * j, x=.2 * j); H.dreh("upperarm01.R", z=.72 - 3.3 * j, x=.2 * j)
            H.dreh("lowerarm01.L", x=-.4 * j); H.dreh("lowerarm01.R", x=-.4 * j); H.dreh("neck01", x=-.3 * j)
            for f in range(1, 6):
                for g in (1, 2, 3):
                    H.dreh(f"finger{f}-{g}.L", x=1.1 * j); H.dreh(f"finger{f}-{g}.R", x=1.1 * j)
    bpy.context.view_layer.update()


def becken():
    return H.rig.matrix_world @ PEL


# ======================================================================  Kamera
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam
cam.data.clip_start = .03; cam.data.clip_end = 3000; cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
cam.data.dof.use_dof = True
# (von, bis, ts0, ts1, pos0, pos1, ziel0, ziel1, linse); ziel "B" = Becken, pos mit "B+" = relativ zum Becken
SZ = [
    (0.00, 1.30, 10.00, 10.39, (1.9, -3.3, 1.9), (1.8, -3.1, 1.95), (0, .05, 2.35), (0, .05, 2.35), 30),     # Aufhaenger
    (1.30, 3.20, 1.30, 3.20, (13, -18, 3.2), (12, -17, 3.0), (2, -3, 1.6), (2, -3, 1.6), 26),
    (3.20, 4.60, 3.20, 4.60, (.9, 2.3, .95), (.8, 2.2, .95), (0, 0, 2.45), (0, 0, 2.45), 20),        # Latte gegen Himmel
    (4.60, 7.30, 4.60, 7.30, (-30, 45, 24), (-24, 38, 21), (0, 0, 0), (0, 0, 0), 28),
    (7.30, 8.40, 7.30, 8.40, "B+", (3.0, -1.6, .2), "B", "B", 32),                                 # Anlauf mitfahrend
    (8.40, 9.60, 8.40, 9.60, "B+", (1.3, -1.6, -.85), "F", "F", 30),                                   # Fuesse mitfahrend
    (9.60, 10.80, 9.60, 10.80, (2.8, -4.8, 1.7), (2.6, -4.6, 1.8), (0, 0, 1.9), (0, 0, 2.0), 28),    # Absprung + Flug
    (10.80, 12.50, 9.55, 10.40, (6.8, .1, 2.2), (6.6, .1, 2.25), (0, .1, 2.15), (0, .1, 2.2), 40),   # Zeitlupe seitlich
    (12.50, 16.10, 9.92, 10.30, (-1.4, 2.8, 2.75), (-1.1, 2.6, 2.7), (0, 0, 2.45), (0, 0, 2.45), 32),  # Super-Zeitlupe
    (16.10, 18.20, 10.60, 12.70, (4.2, 3.8, 1.7), (4.0, 3.6, 1.6), (-.3, 1.3, 1.1), (-.3, 1.4, 1.2), 28),
    (18.20, 20.10, 12.70, 14.60, (1.3, -.2, 1.5), (1.2, -.3, 1.55), (-.35, 1.5, 1.25), (-.35, 1.5, 1.3), 40),
    (20.10, 23.80, 14.60, 18.30, (3.5, -3.5, 3.0), (16, -21, 14), (0, .5, 1.5), (0, .5, 1.5), 26),
]


def zustand(t):
    for s in SZ:
        if s[0] <= t < s[1]:
            break
    k = (t - s[0]) / (s[1] - s[0])
    ts = s[2] + (s[3] - s[2]) * k
    k = ease(k) * .7 + k * .3
    figuren(ts)
    bk = becken()
    if s[4] == "B+":
        pos = bk + Vector(s[5]) + Vector((0, 0, -bk.z + 1.1))
    else:
        pos = lerpv(s[4], s[5], k)
    ziel = bk if s[6] == "B" else (Vector((bk.x, bk.y, .45)) if s[6] == "F" else lerpv(s[6], s[7], k))
    cam.location = pos; d = ziel - pos; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = s[8]; cam.data.dof.focus_distance = d.length; cam.data.dof.aperture_fstop = 2.2 if d.length < 4 else 5.6
    zit = .003
    cam.location += Vector((zit * math.sin(t * 7.3), zit * math.cos(t * 5.1), zit * math.sin(t * 9.7)))


os.makedirs(A.ordner, exist_ok=True)
N = int(round(D * A.fps))
liste = [int(round(float(x) * A.fps)) for x in A.nur.split(",")] if A.nur else list(range(A.start, N))
for f in liste:
    pfad = os.path.join(A.ordner, f"hoch_{f:04d}.png")
    if os.path.exists(pfad) and not A.nur:
        continue
    zustand(f / A.fps); bpy.context.view_layer.update(); zustand(f / A.fps)
    sc.render.filepath = pfad
    bpy.ops.render.render(write_still=True); print("FERTIG", pfad, flush=True)
