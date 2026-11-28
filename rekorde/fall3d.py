"""Wasserfall im Kajak 57,6 m (Tyler Bradt, Palouse Falls, 21.4.2009, GWR). Realistisch, natuerliche Paddelzuege.
python3 fall3d.py <ordner> [--nur t1,t2] [--start i] [--samples n]"""
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
D = 25.2
ASSET = os.path.join(os.path.dirname(HIER), "assets")
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = A.samples; sc.cycles.use_denoising = True
sc.cycles.max_bounces = 5; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 3; sc.cycles.transmission_bounces = 2
sc.cycles.transparent_max_bounces = 8; sc.cycles.adaptive_threshold = .03
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1080, 1920, A.skala
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"; sc.view_settings.exposure = -.05
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


_NR = [0]


def _nm(name):
    _NR[0] += 1; return "%s_%d" % (name, _NR[0])


def box(name, groesse, ort, m, bevel=.01, seg=3, rot=(0, 0, 0), eltern=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=ort, rotation=rot); o = bpy.context.object; o.name = _nm(name); o.scale = groesse
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
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=l, vertices=v, location=ort, rotation=rot); o = bpy.context.object; o.name = _nm(name)
    o.data.materials.append(m)
    bv = o.modifiers.new("b", "BEVEL"); bv.width = min(r, l) * .12; bv.segments = 2; bv.limit_method = "ANGLE"
    for p in o.data.polygons:
        p.use_smooth = True
    if eltern:
        o.parent = eltern
    return o


def rohr(name, a, b, r, m, eltern=None, v=10):
    a, b = Vector(a), Vector(b); d = b - a
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d.length, vertices=v, location=(a + b) / 2); o = bpy.context.object; o.name = _nm(name)
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


class Sammler:
    """viele Boxen/Zylinder pro Material in ein Mesh (schneller Aufbau)"""
    def __init__(self):
        self.bm = {}

    def _b(self, m, glatt):
        key = (m.name, glatt)
        if key not in self.bm:
            self.bm[key] = (bmesh.new(), m, glatt)
        return self.bm[key][0]

    def box(self, groesse, ort, m, rot=(0, 0, 0)):
        M = Matrix.Translation(Vector(ort)) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((*groesse, 1))
        bmesh.ops.create_cube(self._b(m, False), size=1, matrix=M)

    def zyl(self, r, l, ort, m, rot=(0, 0, 0), v=16):
        M = Matrix.Translation(Vector(ort)) @ Euler(rot).to_matrix().to_4x4()
        bmesh.ops.create_cone(self._b(m, True), cap_ends=True, segments=v, radius1=r, radius2=r, depth=l, matrix=M)

    def rohr(self, a, b, r, m, v=10):
        a, b = Vector(a), Vector(b); d = b - a
        M = Matrix.Translation((a + b) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
        bmesh.ops.create_cone(self._b(m, True), cap_ends=True, segments=v, radius1=r, radius2=r, depth=d.length, matrix=M)

    def kugel(self, r, ort, m, skala=(1, 1, 1), sub=2):
        M = Matrix.Translation(Vector(ort)) @ Matrix.Diagonal((*skala, 1))
        bmesh.ops.create_icosphere(self._b(m, True), subdivisions=sub, radius=r, matrix=M)

    def fertig(self, name, bevel=0.0):
        obs = []
        for i, (bm, m, glatt) in enumerate(self.bm.values()):
            me_ = bpy.data.meshes.new("%s_%d" % (name, i)); bm.to_mesh(me_); bm.free()
            if glatt:
                for p in me_.polygons:
                    p.use_smooth = True
            me_.materials.append(m)
            o = bpy.data.objects.new("%s_%d" % (name, i), me_); sc.collection.objects.link(o)
            if bevel and not glatt:
                bv = o.modifiers.new("b", "BEVEL"); bv.width = bevel; bv.segments = 2; bv.limit_method = "ANGLE"
            obs.append(o)
        self.bm = {}
        return obs
# ======================================================================  Kajakfahrer (zuerst): Drytop, Helm
import mensch_echt as ME
PC = ME.mensch("bradt", 44, 1.0, .3, .65, .2, haut="caucasian", haare="short02", braue="eyebrow001", haarfarbe="6b4a2e", schuhe=None)
for o in PC.stiefel:
    o.hide_render = True
ME.trikot(PC, "lang", "tights", "f2b705", "15171b")
for o in PC.huellen:
    if "versatz" in o.modifiers:
        o.modifiers["versatz"].strength = .014 if o.name.endswith("_hemd") else .010
    for md in o.modifiers:
        if md.type == "SUBSURF":
            md.render_levels = 2
hoehe = max(v.z for v in PC.EV); PC.SK = 1.80 / hoehe; PC.rig.scale = (PC.SK,) * 3
PC.PEL = PC.rig.data.bones["upperleg01.L"].head_local.copy(); PC.PEL.x = 0
bpy.context.view_layer.update()
kopf_b = PC.rig.data.bones["head"]
kh = PC.rig.matrix_world @ kopf_b.head_local; kt = PC.rig.matrix_world @ kopf_b.tail_local
kz = kh + (kt - kh) * .55
bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1, location=kz + Vector((0, .012, .03)))
helm = bpy.context.object; helm.name = "helm"; helm.scale = (.118, .132, .118); helm.data.materials.append(mat("helm", "c62828", .3, Coat_Weight=1.0))
bm = bmesh.new(); bm.from_mesh(helm.data)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -.05 and v.co.y < .2], context="VERTS"); bm.to_mesh(helm.data); bm.free()
helm.modifiers.new("d", "SOLIDIFY").thickness = .08
for p in helm.data.polygons:
    p.use_smooth = True
bpy.context.view_layer.update()
PI = (PC.rig.matrix_world @ kopf_b.matrix_local @ Matrix.Translation((0, kopf_b.length, 0))).inverted()
helm.parent = PC.rig; helm.parent_type = "BONE"; helm.parent_bone = "head"; helm.matrix_parent_inverse = PI
print("ok mensch")
# ---- echte Zuschauer: einige MakeHuman-Menschen in Pose "backen" und als Instanzen verteilen
ZUSCH_ME = []
for i, (sd_, mn, haut, haar, fo, fu, oben) in enumerate((
        (101, 1.0, "caucasian", "short02", "1565c0", "2b2f36", "tshirt"), (102, 0.0, "caucasian", "ponytail01", "f2f2f2", "1f2a44", "lang"),
        (103, 1.0, "african", "short03", "2e7d32", "2b2f36", "tshirt"), (104, 0.0, "asian", "bob01", "c62828", "2b2f36", "lang"),
        (105, 1.0, "caucasian", "short04", "33507a", "4a3a2a", "lang"), (106, 1.0, "caucasian", "short02", "f9a825", "2b2f36", "tshirt"))):
    Z_ = ME.mensch("zus%d" % i, sd_, mn, .3 + .1 * (i % 3), .5, .3 + .1 * (i % 2), haut=haut, haare=haar, braue="eyebrow010", haarfarbe=("1a120c", "6b4a2e", "0b0908")[i % 3])
    ME.trikot(Z_, oben, "tights", fo, fu)
    hz = max(v.z for v in Z_.EV); Z_.rig.scale = ((1.62 + .12 * (i % 3)) / hz,) * 3
    Z_.dreh("upperarm01.L", z=-.72 + (1.0 if i == 2 else 0), x=.1); Z_.dreh("upperarm01.R", z=.72 - (1.4 if i == 4 else 0), x=.1)
    Z_.dreh("lowerarm01.L", x=-.3); Z_.dreh("lowerarm01.R", x=-.3)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    teile = []
    for o in [Z_.koerper] + list(Z_.huellen) + list(getattr(Z_, "proxies", [])):
        if o.type != "MESH" or o.hide_render:
            continue
        ev = o.evaluated_get(dg); me_ = bpy.data.meshes.new_from_object(ev, depsgraph=dg); me_.transform(o.matrix_world)
        t_ = bpy.data.objects.new("zt", me_); sc.collection.objects.link(t_); teile.append(t_)
    bpy.ops.object.select_all(action="DESELECT")
    for t_ in teile:
        t_.select_set(True)
    bpy.context.view_layer.objects.active = teile[0]; bpy.ops.object.join()
    j_ = bpy.context.object; j_.name = "zuschauer_typ%d" % i
    ZUSCH_ME.append(j_.data); bpy.data.objects.remove(j_)
    for o in list(Z_.objekte) + [Z_.rig]:
        try:
            bpy.data.objects.remove(o)
        except Exception:
            pass
print("zuschauer typen", len(ZUSCH_ME))
# ======================================================================  Himmel, Sonne
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; nt = w.node_tree
env = nt.nodes.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(os.path.join(ASSET, "tag.hdr"))
nt.links.new(env.outputs[0], nt.nodes["Background"].inputs[0]); nt.nodes["Background"].inputs[1].default_value = 1.0
bpy.ops.object.light_add(type="SUN", rotation=(math.radians(40), 0, math.radians(-60))); sonne = bpy.context.object
sonne.data.energy = 4.3; sonne.data.angle = math.radians(1.0); sonne.data.color = (1, .95, .88)
STAHL = pbr("stahl", "Metal012", 6, rau_mul=.6, rau_add=.15, metal=1.0)

H_FALL = 57.6                     # Fallhoehe (m)
C = Vector((34.0, 0, 0))          # Mitte des Kessels (Plunge Pool)
R_POOL = 30.0; Z_PLAT = 66.0


def sstep(a, b, x):
    t = min(1, max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t)


# ======================================================================  Gelaende (Hoehenfeld): Hochebene, Kessel, Oberlauf, Canyon
def gelaende(x, y):
    d = math.hypot(x - C.x, y - C.y)
    z = Z_PLAT + 1.5 * math.sin(x / 37) * math.sin(y / 29)
    # Kessel (steile Waende)
    k = sstep(R_POOL + 4.2, R_POOL + 3, d)
    z = z * (1 - k) + (-3) * k
    # Canyon flussabwaerts (+x)
    if x > C.x:
        bc = 26 + .08 * (x - C.x)
        kk = sstep(bc + 6, bc, abs(y))
        z = z * (1 - kk) + (-3) * kk
    # Oberlauf: Rinne bis zur Kante (x < 0)
    if x < 2:
        kk = sstep(14, 10, abs(y))
        bett = H_FALL - 1.0 + .015 * (-x)
        z = min(z, z * (1 - kk) + bett * kk)
    return z


def hoehenfeld(name, x0, x1, y0, y1, dx, fn, m):
    nx = int((x1 - x0) / dx) + 1; ny = int((y1 - y0) / dx) + 1
    bm = bmesh.new(); vs = []
    for j in range(ny):
        for i in range(nx):
            x = x0 + i * dx; y = y0 + j * dx
            vs.append(bm.verts.new((x, y, fn(x, y))))
    for j in range(ny - 1):
        for i in range(nx - 1):
            a = j * nx + i
            bm.faces.new((vs[a], vs[a + 1], vs[a + nx + 1], vs[a + nx]))
    me_ = bpy.data.meshes.new(name); bm.to_mesh(me_); bm.free(); me_.materials.append(m)
    for p in me_.polygons:
        p.use_smooth = True
    o = bpy.data.objects.new(name, me_); sc.collection.objects.link(o); return o


def basalt_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt_ = m.node_tree; n = nt_.nodes; l = nt_.links; b = n["Principled BSDF"]
    geo = n.new("ShaderNodeNewGeometry"); sp = n.new("ShaderNodeSeparateXYZ"); l.new(geo.outputs["Normal"], sp.inputs[0])
    sp2 = n.new("ShaderNodeSeparateXYZ"); l.new(geo.outputs["Position"], sp2.inputs[0])
    gr = n.new("ShaderNodeMapRange"); gr.inputs[1].default_value = .7; gr.inputs[2].default_value = .85; l.new(sp.outputs["Z"], gr.inputs[0])
    hz = n.new("ShaderNodeMapRange"); hz.inputs[1].default_value = 60; hz.inputs[2].default_value = 63; l.new(sp2.outputs["Z"], hz.inputs[0])
    mu = n.new("ShaderNodeMath"); mu.operation = "MULTIPLY"; l.new(gr.outputs[0], mu.inputs[0]); l.new(hz.outputs[0], mu.inputs[1])
    vo = n.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = .5; vo.feature = "DISTANCE_TO_EDGE"
    mp = n.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1, 1, .08); l.new(geo.outputs["Position"], mp.inputs[0]); l.new(mp.outputs[0], vo.inputs["Vector"])
    kante = n.new("ShaderNodeMapRange"); kante.inputs[1].default_value = .0; kante.inputs[2].default_value = .06; l.new(vo.outputs["Distance"], kante.inputs[0])
    no = n.new("ShaderNodeTexNoise"); no.inputs["Scale"].default_value = .4; no.inputs["Detail"].default_value = 10; l.new(geo.outputs["Position"], no.inputs["Vector"])
    fc = n.new("ShaderNodeMix"); fc.data_type = "RGBA"; l.new(no.outputs["Fac"], fc.inputs[0])
    fc.inputs[6].default_value = (*hexf("2a221d"), 1); fc.inputs[7].default_value = (*hexf("4a3a2e"), 1)
    dk = n.new("ShaderNodeMix"); dk.data_type = "RGBA"; dk.blend_type = "MULTIPLY"; l.new(kante.outputs[0], dk.inputs[0])
    dk.inputs[0].default_value = 1; l.new(fc.outputs[2], dk.inputs[6])
    kc = n.new("ShaderNodeMapRange"); kc.inputs[3].default_value = .35; kc.inputs[4].default_value = 1.0; l.new(kante.outputs[0], kc.inputs[0])
    cc = n.new("ShaderNodeCombineColor"); l.new(kc.outputs[0], cc.inputs[0]); l.new(kc.outputs[0], cc.inputs[1]); l.new(kc.outputs[0], cc.inputs[2]); l.new(cc.outputs[0], dk.inputs[7])
    gras = n.new("ShaderNodeMix"); gras.data_type = "RGBA"; l.new(no.outputs["Fac"], gras.inputs[0])
    gras.inputs[6].default_value = (*hexf("5c6630"), 1); gras.inputs[7].default_value = (*hexf("857a44"), 1)
    mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; l.new(mu.outputs[0], mx.inputs[0]); l.new(dk.outputs[2], mx.inputs[6]); l.new(gras.outputs[2], mx.inputs[7])
    l.new(mx.outputs[2], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = .9
    bu = n.new("ShaderNodeBump"); bu.inputs["Strength"].default_value = .9; bu.inputs["Distance"].default_value = .8
    wand = n.new("ShaderNodeMath"); wand.operation = "SUBTRACT"; wand.inputs[0].default_value = 1.0; l.new(mu.outputs[0], wand.inputs[1])
    kw = n.new("ShaderNodeMath"); kw.operation = "MULTIPLY"; l.new(kante.outputs[0], kw.inputs[0]); l.new(wand.outputs[0], kw.inputs[1])
    ad = n.new("ShaderNodeMath"); ad.operation = "ADD"; l.new(kw.outputs[0], ad.inputs[0]); l.new(no.outputs["Fac"], ad.inputs[1])
    l.new(ad.outputs[0], bu.inputs["Height"]); l.new(bu.outputs[0], b.inputs["Normal"])
    return m


BASALT = basalt_mat("basalt")
hoehenfeld("gelaende", -260, 320, -260, 260, 2.0, gelaende, BASALT)
# Basaltsaeulen am Kesselrand (sechseckig, Hoehen variieren)
SA = Sammler(); rs = random.Random(3)
SAEULE = [mat("saeule%d" % i, f, .85) for i, f in enumerate(("3a2f28", "4a3c31", "5a4838"))]
for ring, (r0, z0, z1) in enumerate(((R_POOL + 3.5, -2, 30), (R_POOL + 5.5, 28, 58), (R_POOL + 7.5, 55, 64))):
    n_s = int(2 * P * r0 / 1.9)
    for k in range(n_s):
        a = 2 * P * k / n_s
        if abs(math.atan2(math.sin(a), math.cos(a))) < .55:          # offen flussabwaerts
            continue
        if abs(math.atan2(math.sin(a - P), math.cos(a - P))) < .28 and z1 > H_FALL - 4:   # Kerbe fuer den Fall
            continue
        h = (z1 - z0) * rs.uniform(.75, 1.0)
        p_ = C + Vector((r0 * math.cos(a) + rs.uniform(-.3, .3), r0 * math.sin(a) + rs.uniform(-.3, .3), z0 + h / 2))
        SA.zyl(rs.uniform(.9, 1.15), h, p_, rs.choice(SAEULE), rot=(0, 0, rs.uniform(0, 1)), v=6)
SA.fertig("basaltsaeulen", bevel=.06)
# Steppengras-Buesche auf der Hochebene (rund)
BG = Sammler(); BUSCH = [mat("busch%d" % i, f, .9) for i, f in enumerate(("8a7a44", "6e6a3a", "a39056"))]
for i in range(700):
    x = rs.uniform(-200, 260); y = rs.uniform(-220, 220)
    z = gelaende(x, y)
    if z < Z_PLAT - 3:
        continue
    BG.kugel(rs.uniform(.3, .8), (x, y, z + .2), rs.choice(BUSCH), skala=(1, 1, .6), sub=1)
BG.fertig("steppe")

# ======================================================================  Wasser: Oberlauf, Fallvorhang, Kessel, Gischt
ZEIT = []          # Mapping-Knoten, deren Versatz je Bild mit der Zeit laeuft


def fluss_mat(name, farbe, schaum, richtung, skala, schaumanteil):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt_ = m.node_tree; n = nt_.nodes; l = nt_.links; b = n["Principled BSDF"]
    tc = n.new("ShaderNodeTexCoord"); mp = n.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = skala; l.new(tc.outputs["Object"], mp.inputs[0])
    ZEIT.append((mp, richtung))
    no = n.new("ShaderNodeTexNoise"); no.inputs["Scale"].default_value = 2.0; no.inputs["Detail"].default_value = 12; no.inputs["Roughness"].default_value = .65
    l.new(mp.outputs[0], no.inputs["Vector"])
    mr = n.new("ShaderNodeMapRange"); mr.inputs[1].default_value = 1 - schaumanteil; mr.inputs[2].default_value = 1 - schaumanteil + .18; l.new(no.outputs["Fac"], mr.inputs[0])
    mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; l.new(mr.outputs[0], mx.inputs[0])
    mx.inputs[6].default_value = (*hexf(farbe), 1); mx.inputs[7].default_value = (*hexf(schaum), 1); l.new(mx.outputs[2], b.inputs["Base Color"])
    rr = n.new("ShaderNodeMapRange"); rr.inputs[3].default_value = .04; rr.inputs[4].default_value = .5; l.new(mr.outputs[0], rr.inputs[0]); l.new(rr.outputs[0], b.inputs["Roughness"])
    bu = n.new("ShaderNodeBump"); bu.inputs["Strength"].default_value = .35; l.new(no.outputs["Fac"], bu.inputs["Height"]); l.new(bu.outputs[0], b.inputs["Normal"])
    return m, mr


OBERLAUF_M, _ = fluss_mat("oberlauf", "2f5a46", "d8e4e0", (-1.0, 0, 0), (.25, .6, .25), .22)
POOL_M, pool_mr = fluss_mat("kessel", "21463c", "e4ecea", (0, 0, 0), (.3, .3, .3), .28)
# im Kessel: Schaum nahe dem Aufprall
nt_ = POOL_M.node_tree; n = nt_.nodes; l = nt_.links
geo = n.new("ShaderNodeNewGeometry"); vm = n.new("ShaderNodeVectorMath"); vm.operation = "DISTANCE"; vm.inputs[1].default_value = (14.0, 0, 0)
l.new(geo.outputs["Position"], vm.inputs[0])
nah = n.new("ShaderNodeMapRange"); nah.inputs[1].default_value = 22; nah.inputs[2].default_value = 6; l.new(vm.outputs["Value"], nah.inputs[0])
mxx = n.new("ShaderNodeMath"); mxx.operation = "MAXIMUM"; l.new(pool_mr.outputs[0], mxx.inputs[0])
mu2 = n.new("ShaderNodeMath"); mu2.operation = "MULTIPLY"; l.new(nah.outputs[0], mu2.inputs[0]); mu2.inputs[1].default_value = .85; l.new(mu2.outputs[0], mxx.inputs[1])
for lk in list(l):
    if lk.from_node == pool_mr and lk.to_node.type == "MIX":
        tgt = lk.to_socket; l.remove(lk); l.new(mxx.outputs[0], tgt)
# Oberlauf (Wasserflaeche in der Rinne), leicht geneigt
bpy.ops.mesh.primitive_grid_add(x_subdivisions=120, y_subdivisions=24, size=1, location=(-75, 0, 0)); OB = bpy.context.object; OB.name = "oberlauf"
OB.scale = (150, 26, 1); bpy.ops.object.transform_apply(scale=True)
for v in OB.data.vertices:
    v.co.z = H_FALL + .2 + .015 * (-(v.co.x - 75)) * 0 + .015 * -(v.co.x + -75 + 75) * 0
for v in OB.data.vertices:
    xw = v.co.x + OB.location.x
    v.co.z = H_FALL + .25 + .015 * max(0, -xw) - .35 * sstep(-6, 0, xw)
OB.data.materials.append(OBERLAUF_M)
for p in OB.data.polygons:
    p.use_smooth = True
# Fallvorhang: zwei Schichten, Parabel (v0 = 4 m/s)
FALL_M = bpy.data.materials.new("fallvorhang"); FALL_M.use_nodes = True
n = FALL_M.node_tree.nodes; l = FALL_M.node_tree.links; out = n["Material Output"]; bs = n["Principled BSDF"]
tc = n.new("ShaderNodeTexCoord"); mp = n.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (.9, 2.2, .12); l.new(tc.outputs["Object"], mp.inputs[0])
ZEIT.append((mp, (0, 0, 9.0)))
no = n.new("ShaderNodeTexNoise"); no.inputs["Scale"].default_value = 3.0; no.inputs["Detail"].default_value = 14; no.inputs["Roughness"].default_value = .7; l.new(mp.outputs[0], no.inputs["Vector"])
sp = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Object"], sp.inputs[0])
oben = n.new("ShaderNodeMapRange"); oben.inputs[1].default_value = H_FALL - 2; oben.inputs[2].default_value = H_FALL - 7; l.new(sp.outputs["Z"], oben.inputs[0])
cmx = n.new("ShaderNodeMix"); cmx.data_type = "RGBA"; l.new(oben.outputs[0], cmx.inputs[0])
cmx.inputs[6].default_value = (*hexf("3f7a5e"), 1); cmx.inputs[7].default_value = (.93, .95, .95, 1); l.new(cmx.outputs[2], bs.inputs["Base Color"])
bs.inputs["Roughness"].default_value = .35
al = n.new("ShaderNodeMapRange"); al.inputs[1].default_value = .35; al.inputs[2].default_value = .6; l.new(no.outputs["Fac"], al.inputs[0])
alm = n.new("ShaderNodeMath"); alm.operation = "MAXIMUM"; l.new(al.outputs[0], alm.inputs[0]); oben2 = n.new("ShaderNodeMath"); oben2.operation = "SUBTRACT"
oben2.inputs[0].default_value = 1.0; l.new(oben.outputs[0], oben2.inputs[1]); l.new(oben2.outputs[0], alm.inputs[1])
tr = n.new("ShaderNodeBsdfTransparent"); ms = n.new("ShaderNodeMixShader"); l.new(alm.outputs[0], ms.inputs[0]); l.new(tr.outputs[0], ms.inputs[1]); l.new(bs.outputs[0], ms.inputs[2])
l.new(ms.outputs[0], out.inputs["Surface"])
V0 = 4.0; G = 9.81
for schicht, (dx, breite) in enumerate(((0.0, 1.0), (.6, 1.12))):
    bm = bmesh.new(); rows = []
    NT = 40
    for i in range(NT + 1):
        t = 3.5 * i / NT
        x = V0 * t + dx * t / 3.5; z = H_FALL - .5 * G * t * t
        hw = (9.0 + 3.0 * t / 3.5) * breite
        rows.append([bm.verts.new((x, y, z)) for y in [-hw + 2 * hw * j / 24 for j in range(25)]])
    for a, b in zip(rows, rows[1:]):
        for j in range(24):
            bm.faces.new((a[j], a[j + 1], b[j + 1], b[j]))
    me_ = bpy.data.meshes.new("fall%d" % schicht); bm.to_mesh(me_); bm.free(); me_.materials.append(FALL_M)
    o = bpy.data.objects.new("fall%d" % schicht, me_); sc.collection.objects.link(o)
    for p in me_.polygons:
        p.use_smooth = True
# Kessel-Wasser
bpy.ops.mesh.primitive_plane_add(size=1, location=(C.x + 60, 0, 0)); POOL = bpy.context.object; POOL.name = "kessel"; POOL.scale = (260, 160, 1)
bpy.ops.object.transform_apply(scale=True)
pm = POOL.modifiers.new("wellen", "OCEAN"); pm.geometry_mode = "DISPLACE"
POOL.modifiers.remove(pm)
sub = POOL.modifiers.new("s", "SUBSURF"); sub.subdivision_type = "SIMPLE"; sub.levels = 0; sub.render_levels = 0
POOL.data.materials.append(POOL_M)
# Gischt / Nebel am Fuss des Falls (Volumen)
NEBEL = bpy.data.materials.new("nebel"); NEBEL.use_nodes = True
n = NEBEL.node_tree.nodes; l = NEBEL.node_tree.links; out = n["Material Output"]; n.remove(n["Principled BSDF"])
vol = n.new("ShaderNodeVolumePrincipled"); vol.inputs["Color"].default_value = (.95, .97, .98, 1); vol.inputs["Density"].default_value = .05
gr = n.new("ShaderNodeTexGradient"); gr.gradient_type = "SPHERICAL"; tcn = n.new("ShaderNodeTexCoord"); l.new(tcn.outputs["Object"], gr.inputs["Vector"])
mud = n.new("ShaderNodeMath"); mud.operation = "MULTIPLY"; mud.inputs[1].default_value = .008; l.new(gr.outputs["Fac"], mud.inputs[0]); l.new(mud.outputs[0], vol.inputs["Density"])
l.new(vol.outputs[0], out.inputs["Volume"])
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1, location=(15, 0, 3)); NB = bpy.context.object; NB.name = "nebel"; NB.scale = (14, 16, 9)
NB.data.materials.append(NEBEL)
# Aussichtspunkt mit Gelaender und Zuschauern (gegenueber, Suedrand)
AUS = C + Vector((10, -(R_POOL + 12), 0)); AUS.z = gelaende(AUS.x, AUS.y)
GL = Sammler()
for k in range(14):
    x0 = AUS.x - 14 + k * 2.0
    GL.rohr(Vector((x0, AUS.y + 2.5, AUS.z)), Vector((x0, AUS.y + 2.5, AUS.z + 1.05)), .03, STAHL)
GL.rohr(Vector((AUS.x - 14, AUS.y + 2.5, AUS.z + 1.05)), Vector((AUS.x + 12, AUS.y + 2.5, AUS.z + 1.05)), .03, STAHL)
GL.rohr(Vector((AUS.x - 14, AUS.y + 2.5, AUS.z + .55)), Vector((AUS.x + 12, AUS.y + 2.5, AUS.z + .55)), .02, STAHL)
GL.fertig("gelaender")
rz = random.Random(17); RAND_LEUTE = []
for i in range(12):
    x = AUS.x - 12 + i * 2.0 + rz.uniform(-.3, .3)
    o = bpy.data.objects.new("rand_%d" % i, rz.choice(ZUSCH_ME)); sc.collection.objects.link(o)
    o.location = (x, AUS.y + rz.uniform(.3, 1.6), AUS.z); o.rotation_euler = (0, 0, P + rz.uniform(-.4, .4))
    RAND_LEUTE.append((o, AUS.z, rz.uniform(0, 6)))

# ======================================================================  Kajak (rot) + Paddel
def kajak_mesh():
    """Rumpf: Querschnitte entlang x (Laenge 2,6 m), flacher Boden, gewoelbtes Deck"""
    bm = bmesh.new(); ringe = []; NX = 26; NU = 20
    for i in range(NX + 1):
        x = -1.3 + 2.6 * i / NX
        f = 1 - (abs(x) / 1.3) ** 2.2
        bw = .34 * max(f, .02) ** .6; hh = .28 * max(f, .05) ** .5
        ring = []
        for j in range(NU):
            a = 2 * P * j / NU
            y = bw * math.cos(a); z = (hh * math.sin(a) if math.sin(a) > 0 else .6 * hh * math.sin(a))
            ring.append(bm.verts.new((x, y, z + .02 * (x / 1.3) ** 2)))
        ringe.append(ring)
    for a, b in zip(ringe, ringe[1:]):
        for j in range(NU):
            bm.faces.new((a[j], a[(j + 1) % NU], b[(j + 1) % NU], b[j]))
    bmesh.ops.contextual_create(bm, geom=ringe[0]); bmesh.ops.contextual_create(bm, geom=ringe[-1])
    me_ = bpy.data.meshes.new("kajak"); bm.to_mesh(me_); bm.free()
    for p in me_.polygons:
        p.use_smooth = True
    return me_


KAJAK = bpy.data.objects.new("kajak", kajak_mesh()); sc.collection.objects.link(KAJAK)
KAJAK.data.materials.append(mat("kajak_rot", "c4161c", .3, Coat_Weight=.9))
KAJAK.modifiers.new("s", "SUBSURF").render_levels = 2
KAJAK.rotation_mode = "QUATERNION"
bpy.ops.mesh.primitive_torus_add(major_radius=.3, minor_radius=.025, location=(0, 0, .27)); sull = bpy.context.object; sull.name = "suelrand"; sull.scale = (1.25, .85, 1)
sull.data.materials.append(mat("schwarz", "121212", .5)); sull.parent = KAJAK
bpy.ops.mesh.primitive_cylinder_add(radius=.3, depth=.02, location=(0, 0, .272)); sk = bpy.context.object; sk.name = "spritzdecke"; sk.scale = (1.22, .82, 1)
sk.data.materials.append(mat("neopren", "1b1d22", .7)); sk.parent = KAJAK
# Paddel: Schaft entlang lokal y, Blaetter an beiden Enden
PADDEL = leer("paddel"); PADDEL.rotation_mode = "QUATERNION"
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=.016, radius2=.016, depth=2.0, matrix=Matrix.Rotation(P / 2, 4, "X"))
me_s = bpy.data.meshes.new("schaft"); bm.to_mesh(me_s); bm.free(); me_s.materials.append(mat("schaft", "1a1a1a", .3, metal=.3))
o_s = bpy.data.objects.new("schaft", me_s); sc.collection.objects.link(o_s); o_s.parent = PADDEL
bm = bmesh.new()
for sy in (-1, 1):
    bmesh.ops.create_cube(bm, size=1, matrix=Matrix.Translation((0, sy * 1.12, 0)) @ Matrix.Rotation(sy * .12, 4, "Z") @ Matrix.Diagonal((.014, .44, .18, 1)))
me_b = bpy.data.meshes.new("blaetter"); bm.to_mesh(me_b); bm.free(); me_b.materials.append(mat("blatt", "f2f2f2", .35, Coat_Weight=.6))
o_b = bpy.data.objects.new("blaetter", me_b); sc.collection.objects.link(o_b); o_b.parent = PADDEL
# Spritzer beim Aufprall
SPR_M = mat("spritzer", "f4f8fa", .8, Emission_Color=(1, 1, 1, 1), Emission_Strength=.25)
SPRITZER = []
rk = random.Random(8)
for i in range(60):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, location=(0, 0, -60)); o = bpy.context.object; o.name = "spritzer%d" % i
    o.data.materials.append(SPR_M)
    for p in o.data.polygons:
        p.use_smooth = True
    a = rk.uniform(0, 2 * P); v = rk.uniform(5, 14); h = rk.uniform(.3, 1.0)
    SPRITZER.append((o, Vector((math.cos(a) * v * .45, math.sin(a) * v * .45, v * h)), rk.uniform(.12, .3)))
print("ok szene")
# ======================================================================  IK (Arme pole -P/2)
from mathutils import Quaternion
KF = PC
KF.Z = {nm: leer("kf_ik_" + nm) for nm in ("hand_L", "hand_R", "fuss_L", "fuss_R", "knie_L", "knie_R", "ell_L", "ell_R")}
KF.IK = {}
for bone, ziel, pol, pw in (("lowerarm02.L", "hand_L", "ell_L", -P / 2), ("lowerarm02.R", "hand_R", "ell_R", -P / 2),
                            ("lowerleg02.L", "fuss_L", "knie_L", -P / 2), ("lowerleg02.R", "fuss_R", "knie_R", -P / 2)):
    c = KF.rig.pose.bones[bone].constraints.new("IK"); c.target = KF.Z[ziel]; c.chain_count = 4
    c.pole_target = KF.Z[pol]; c.pole_angle = pw; KF.IK[ziel] = c


def rig_mat(H, Fc):
    Z = Vector(H).normalized(); Fc = Vector(Fc); Y = -(Fc - Z * Fc.dot(Z)).normalized(); X = Y.cross(Z)
    return Matrix((X, Y, Z)).transposed()


def seg(t, a, b):
    return min(1.0, max(0.0, (t - a) / (b - a)))


UP = Vector((0, 0, 1))
T_LIP = 10.0; V_AN = 3.5; V_SPRUNG = 5.2; Y_ZUNGE = -9.0
T_FALL = math.sqrt(2 * (H_FALL - .2) / G)            # ~3.42 s
T_AUF = T_LIP + T_FALL; T_POP = T_AUF + 1.9
X_AUF = V_SPRUNG * T_FALL


def kajak_zustand(ts):
    """Position und Ausrichtung (vorwaerts, Neigung) des Kajaks"""
    if ts < T_LIP:
        x = -V_AN * (T_LIP - ts)
        p = Vector((x, Y_ZUNGE + .4 * math.sin(ts * .7), H_FALL + .25 + .015 * max(0, -x) - .35 * sstep(-6, 0, x) + .05 * math.sin(ts * 3)))
        nick = -.12 * sstep(-6, 0, x); roll = .05 * math.sin(ts * 2.1)
    elif ts < T_AUF:
        t = ts - T_LIP
        p = Vector((V_SPRUNG * t, Y_ZUNGE, H_FALL + .2 - .5 * G * t * t))
        nick = -.12 - 1.05 * ease(seg(t, 0, 1.6)); roll = 0.0
    elif ts < T_POP:
        u = seg(ts, T_AUF, T_POP)
        p = Vector((X_AUF + 1.2 * u, Y_ZUNGE, -3.5 * math.sin(P * min(1, u * 1.3))))
        nick = -1.17 + .6 * u; roll = 0.0
    else:
        u = ts - T_POP
        p = Vector((X_AUF + 1.2 + .45 * u, Y_ZUNGE - .2 * u, .9 * math.exp(-u * 2.2) * math.cos(u * 4) + .05 * math.sin(ts * 2.5)))
        nick = -.57 * math.exp(-u * 2.5) + .06 * math.sin(u * 5) * math.exp(-u); roll = .08 * math.sin(u * 3) * math.exp(-u * .8)
    q = Quaternion((0, 0, 1), 0) @ Quaternion((0, 1, 0), -nick) @ Quaternion((1, 0, 0), roll)
    return p, q


def figur(ts):
    KF.zuruecksetzen()
    for c in KF.IK.values():
        c.influence = 1.0
    p, q = kajak_zustand(ts)
    KAJAK.location = p; KAJAK.rotation_quaternion = q
    M = q.to_matrix(); kf = M @ Vector((1, 0, 0)); kl = M @ Vector((0, 1, 0)); ku = M @ Vector((0, 0, 1))
    faellt = T_LIP < ts < T_AUF
    tuck = ease(seg(ts, T_LIP - .9, T_LIP + .2)) if ts < T_AUF else 0.0
    jubel = ease(seg(ts, T_POP + 1.8, T_POP + 2.6))
    lean = .1 + .75 * tuck - .05 * jubel
    pel = p + ku * .04 - kf * .05
    H = ku * math.cos(lean) + kf * math.sin(lean); Fc = kf * math.cos(lean) - ku * math.sin(lean)
    rq = rig_mat(H, Fc).to_quaternion()
    KF.rig.rotation_mode = "QUATERNION"; KF.rig.rotation_quaternion = rq
    KF.rig.location = pel - rq.to_matrix() @ (KF.PEL * KF.SK)
    # Beine im Boot: Fuesse vorne, Knie leicht hoch und aussen
    for sd, s in (("L", 1), ("R", -1)):
        KF.Z["fuss_" + sd].location = pel + kf * .95 + kl * (s * .1) + ku * .0
        KF.Z["knie_" + sd].location = pel + kf * .6 + kl * (s * 1.4) + ku * 1.0
    sh_c = pel + H * .48
    # Paddel: Mitte vor der Brust, Schaft quer, abwechselnd links/rechts eingetaucht
    TP = 1.3
    ph = 2 * P * ts / TP
    if ts < T_LIP - .9 or ts > T_POP + .6:
        paddeln = 1.0 if ts < T_LIP else (1 - jubel) * ease(seg(ts, T_POP + .6, T_POP + 1.0)) * .6
    else:
        paddeln = 0.0
    seite = math.sin(ph)                       # +1: links im Wasser, -1: rechts
    zug = math.cos(ph)                         # Blatt wandert von vorne nach hinten
    mitte = sh_c + kf * .36 - H * .14
    achse = (kl * math.cos(.75 * seite) + (-ku) * math.sin(.75 * seite) * 1.0)
    achse = Quaternion(ku, .45 * zug * paddeln).to_matrix() @ achse
    # ruhige Haltung beim Fallen: Paddel laengs neben dem Boot links, Haende an der linken Seite
    ruhe_achse = (kf * .9 + kl * .3 + ku * .1).normalized()
    ruhe_mitte = sh_c + kl * .3 + kf * .2 - H * .15
    a_eff = (achse * paddeln + kl * (1 - paddeln) * (1 - tuck) + ruhe_achse * tuck).normalized()
    m_eff = mitte * (1 - tuck) + ruhe_mitte * tuck
    if jubel > 0:     # Paddel hoch ueber den Kopf
        hoch = sh_c + H * .62 + kf * .05
        m_eff = m_eff.lerp(hoch, jubel); a_eff = (a_eff * (1 - jubel) + kl * jubel).normalized()
    PADDEL.location = m_eff
    PADDEL.rotation_quaternion = a_eff.to_track_quat("Y", "Z")
    KF.Z["hand_L"].location = m_eff + a_eff * .34
    KF.Z["hand_R"].location = m_eff - a_eff * .34
    KF.Z["ell_L"].location = sh_c - kf * .8 + kl * .9 - H * .3
    KF.Z["ell_R"].location = sh_c - kf * .8 - kl * .9 - H * .3
    KF.dreh("neck01", x=-.45 * lean + .15 * jubel)
    for sd in ("L", "R"):
        for ff in range(2, 6):
            for g in (1, 2, 3):
                KF.dreh(f"finger{ff}-{g}.{sd}", x=1.3)
        for g in (2, 3):
            KF.dreh(f"finger1-{g}.{sd}", x=.6)
    # unter Wasser: Fahrer versteckt sich mit dem Boot
    # Spritzer beim Aufprall
    dt = ts - T_AUF
    for o, v, r in SPRITZER:
        if 0 <= dt < 1.6:
            pp = Vector((X_AUF, Y_ZUNGE, 0)) + v * dt * .9 + Vector((0, 0, -4.9 * dt * dt))
            o.location = pp if pp.z > -.2 else Vector((0, 0, -60)); s_ = r * (1 + 1.5 * dt); o.scale = (s_ * (1 + .5 * v.x / 7), s_ * (1 - .3 * v.y / 7), s_ * .6)
        else:
            o.location = (0, 0, -60)
    # Wasser bewegt sich
    for mp, r in ZEIT:
        mp.inputs["Location"].default_value = (r[0] * ts * .3, r[1] * ts * .3, r[2] * ts * .3)
    jub = ts > T_POP + 1.5
    for o, z0, ph_ in RAND_LEUTE:
        o.location.z = z0 + (.08 * max(0, math.sin(ts * 7 + ph_)) if jub else 0.0)
    bpy.context.view_layer.update()
    return pel, kf


def becken():
    nk = KF.rig.matrix_world @ KF.rig.pose.bones["neck01"].head
    return (KF.rig.matrix_world @ KF.PEL) * .55 + nk * .45


# ======================================================================  Kamera
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam
cam.data.clip_start = .03; cam.data.clip_end = 5000; cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
cam.data.dof.use_dof = True
SZ = [
    # t0, t1, ts0, ts1, modus, pos0, pos1, ziel0, ziel1, brennweite   (K+ = relativ zum Kajak in Weltachsen)
    (0.00, 1.60, 11.25, 11.7, "K+", (3.0, -6.5, .8), (3.0, -6.5, 1.0), "B", "B", 24),                                 # Aufhaenger: freier Fall
    (1.60, 3.00, 7.4, 8.9, "K+", (-6.0, -2.4, 2.8), (-5.5, -2.2, 2.9), (8, 2, -5), (8, 2, -6), 22),                   # zur Kante
    (3.00, 4.30, 8.0, 8.6, "P", (70, -10, 2.5), (69, -9.5, 2.6), (6, -4, 34), (6, -4, 36), 20),                        # wie hoch? von unten
    (4.30, 6.90, 8.0, 8.0, "P", (175, -70, 100), (150, -58, 88), (12, 0, 28), (12, 0, 28), 24),                   # Palouse Falls von oben
    (6.90, 8.90, 3.0, 5.0, "K+", (3.4, -2.0, .9), (3.1, -1.7, .95), "B", "B", 26),                                   # paddelt zur Kante
    (8.90, 11.50, 8.4, 9.7, "P", (6.5, -5.5, 61.2), (6.8, -5.8, 61.0), "B", "B", 20),               # 57 m nichts
    (11.50, 13.30, 9.0, 9.8, "P", (42, -40, 75), (40, -39, 75), (4, -6, 30), (4, -6, 30), 24),                        # hoeher als Niagara
    (13.30, 15.30, 9.3, 10.6, "K+", (2.3, -2.6, .9), (2.6, -2.8, -.6), "B", "B", 24),                                # lehnt sich vor, kippt
    (15.30, 17.40, 10.6, 13.2, "K+", (3.6, -6.0, -2.2), (3.6, -6.0, -2.6), "B", "B", 22),                            # freier Fall
    (17.40, 19.30, 12.9, 14.4, "P", (30, -20, 1.6), (29, -19.5, 1.6), (14, -9, 1.5), (14, -9, 1.0), 22),             # Aufprall
    (19.30, 21.20, 14.6, 16.2, "P", (24, -16, 1.2), (23.5, -15.6, 1.2), (16.5, -9, .3), (16.5, -9, .4), 26),          # weg ... wieder da
    (21.20, 25.20, 16.2, 20.2, "P", (25.5, -14.0, 1.6), (24.0, -16.0, 2.4), "B", "B", 24),                            # Jubel vor dem Fall
]


def zustand(t):
    for s in SZ:
        if s[0] <= t < s[1]:
            break
    k = (t - s[0]) / (s[1] - s[0])
    ts = s[2] + (s[3] - s[2]) * k
    k = ease(k) * .7 + k * .3
    pel, kf = figur(ts)
    bk = becken()
    o = Vector(lerpv(s[5], s[6], k))
    if s[4] == "K+":
        pos = KAJAK.location + o
        ziel = bk if s[7] == "B" else KAJAK.location + Vector(lerpv(s[7], s[8], k))
    else:
        pos = o
        ziel = bk if s[7] == "B" else Vector(lerpv(s[7], s[8], k))
    cam.location = pos; d = ziel - pos; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = s[9]; cam.data.dof.focus_distance = d.length; cam.data.dof.aperture_fstop = 2.8 if d.length < 6 else 11
    zit = .006
    cam.location += Vector((zit * math.sin(t * 7.3), zit * math.cos(t * 5.1), zit * math.sin(t * 9.7)))


os.makedirs(A.ordner, exist_ok=True)
N = int(round(D * A.fps))
liste = [int(round(float(x) * A.fps)) for x in A.nur.split(",")] if A.nur else list(range(A.start, N))
for f in liste:
    pfad = os.path.join(A.ordner, f"fall_{f:04d}.png")
    if os.path.exists(pfad) and not A.nur:
        continue
    zustand(f / A.fps); bpy.context.view_layer.update(); zustand(f / A.fps)
    sc.render.filepath = pfad
    bpy.ops.render.render(write_still=True); print("FERTIG", pfad, flush=True)
