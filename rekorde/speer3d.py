"""Speerwurf-Weltrekord 98,48 m (Jan Zelezny, Jena, 25.5.1996). Realistischer Stil, natuerliche Arme.
python3 speer3d.py <ordner> [--nur t1,t2] [--start i] [--samples n]"""
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
D = 28.0
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
# ======================================================================  Werfer (zuerst)
import mensch_echt as ME
LOGO = ME.logo_bild(os.path.join(HIER, "_logo_norda.png"), "NORDA", farbe=(1, 1, 1))
BIB = ME.logo_bild(os.path.join(HIER, "_bib_sp.png"), "7", farbe=(.05, .05, .05), symbol=False, hintergrund=(.97, .97, .95), num=True, unterzeile="JENA 96")
PC = ME.mensch("zelezny", 31, 1.0, .5, .75, .25, haut="caucasian", haare="short02", braue="eyebrow001", haarfarbe="4a3426")
ME.trikot(PC, "singlet", "tights", "f2f2f2", "1f2a44", brust=BIB, brust_mass=(.16, .11), bein=LOGO)
for o in PC.huellen:
    if "versatz" in o.modifiers:
        o.modifiers["versatz"].strength = .017 if o.name.endswith("_hemd") else .010
    for md in o.modifiers:
        if md.type == "SUBSURF":
            md.render_levels = 2
hoehe = max(v.z for v in PC.EV); PC.SK = 1.85 / hoehe; PC.rig.scale = (PC.SK,) * 3
PC.PEL = PC.rig.data.bones["upperleg01.L"].head_local.copy(); PC.PEL.x = 0
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
# ======================================================================  Materialien, Himmel, Sonne
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; nt = w.node_tree
env = nt.nodes.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(os.path.join(ASSET, "tag.hdr"))
nt.links.new(env.outputs[0], nt.nodes["Background"].inputs[0]); nt.nodes["Background"].inputs[1].default_value = 1.0
bpy.ops.object.light_add(type="SUN", rotation=(math.radians(48), 0, math.radians(-140))); sonne = bpy.context.object
sonne.data.energy = 4.0; sonne.data.angle = math.radians(1.0); sonne.data.color = (1, .96, .9)
STAHL = pbr("stahl", "Metal012", 6, rau_mul=.6, rau_add=.15, metal=1.0)
BETON = pbr("beton", "Concrete034", .3, tint="b4afa6")
WEISS_M = mat("linie_weiss", "f4f4f2", .6)
TARTAN = mat("tartan", "a8402c", .8)
TARTAN_RW = mat("tartan_anlauf", "9a3826", .8)
RASEN = pbr("rasen", "Grass004", .35, tint="7fae5a")
# Maehstreifen im Rasen
nt_r = RASEN.node_tree
mxn = [n for n in nt_r.nodes if n.type == "MIX"][0]
tc_ = nt_r.nodes.new("ShaderNodeTexCoord"); sp_ = nt_r.nodes.new("ShaderNodeSeparateXYZ"); nt_r.links.new(tc_.outputs["Object"], sp_.inputs[0])
pp_ = nt_r.nodes.new("ShaderNodeMath"); pp_.operation = "PINGPONG"; pp_.inputs[1].default_value = 5.25; nt_r.links.new(sp_.outputs["X"], pp_.inputs[0])
lt_ = nt_r.nodes.new("ShaderNodeMath"); lt_.operation = "LESS_THAN"; lt_.inputs[1].default_value = 2.625; nt_r.links.new(pp_.outputs[0], lt_.inputs[0])
cm_ = nt_r.nodes.new("ShaderNodeMix"); cm_.data_type = "RGBA"; nt_r.links.new(lt_.outputs[0], cm_.inputs[0])
cm_.inputs[6].default_value = (*hexf("6f9f4c"), 1); cm_.inputs[7].default_value = (*hexf("8fbf66"), 1); nt_r.links.new(cm_.outputs[2], mxn.inputs[7])

# ======================================================================  Stadion: Rundbahn um STAD, Anlauf, Sektor
STAD = Vector((60.0, 0, 0)); GER = 84.39 / 2; R_IN = 36.5; BAHN = 9.76


def oval_pt(i, n_g, n_k, R):
    """Punkt i auf der Ovalbahn mit Radius R (vom Kurvenmittelpunkt)"""
    N = 2 * n_g + 2 * n_k
    i = i % N
    if i < n_g:
        return Vector((STAD.x - GER + 2 * GER * i / n_g, -R, 0))
    i -= n_g
    if i < n_k:
        a = -P / 2 + P * i / n_k; return Vector((STAD.x + GER + R * math.cos(a), R * math.sin(a), 0))
    i -= n_k
    if i < n_g:
        return Vector((STAD.x + GER - 2 * GER * i / n_g, R, 0))
    i -= n_g
    a = P / 2 + P * i / n_k; return Vector((STAD.x - GER + R * math.cos(a), R * math.sin(a), 0))


def oval_band(name, r0, r1, z, m, n_g=24, n_k=64):
    bm = bmesh.new(); N = 2 * n_g + 2 * n_k
    a = [bm.verts.new(oval_pt(i, n_g, n_k, r0) + Vector((0, 0, z))) for i in range(N)]
    b = [bm.verts.new(oval_pt(i, n_g, n_k, r1) + Vector((0, 0, z))) for i in range(N)]
    for i in range(N):
        bm.faces.new((a[i], a[(i + 1) % N], b[(i + 1) % N], b[i]))
    me_ = bpy.data.meshes.new(name); bm.to_mesh(me_); bm.free(); me_.materials.append(m)
    o = bpy.data.objects.new(name, me_); sc.collection.objects.link(o); return o


box("umland", (900, 700, .2), STAD + Vector((0, 0, -.12)), mat("umland_gras", "5f7f45", .9), 0)
# Umgebung: Baeume, Haeuser, Parkplatz (Jena)
UM = Sammler(); ru = random.Random(21)
LAUB = [mat("laub%d" % i, f, .8) for i, f in enumerate(("3f6a2e", "4d7a34", "355c28"))]; STAMM = mat("stamm", "4a3a2a", .9)
DACH = [mat("dach%d" % i, f, .7) for i, f in enumerate(("8a3a2a", "5a5f66", "7a4a32"))]
WAND = [mat("hauswand%d" % i, f, .8) for i, f in enumerate(("e2dccd", "cfc6b4", "f0ece2", "bdb6a8"))]
for i in range(420):
    a = ru.uniform(0, 2 * P); r = ru.uniform(105, 260)
    p_ = STAD + Vector((r * math.cos(a) * 1.25, r * math.sin(a), 0))
    if abs(p_.y) < 70 and -60 < p_.x < 0:
        continue
    h = ru.uniform(7, 15)
    UM.zyl(.25, h * .4, p_ + Vector((0, 0, h * .2)), STAMM, v=6)
    lb = ru.choice(LAUB)
    for kk in range(3):
        UM.kugel(h * ru.uniform(.2, .28), p_ + Vector((ru.uniform(-.8, .8), ru.uniform(-.8, .8), h * (.55 + .15 * kk))), lb, skala=(1, 1, .85))
for i in range(90):
    a = ru.uniform(0, 2 * P); r = ru.uniform(230, 330)
    p_ = STAD + Vector((r * math.cos(a) * 1.2, r * math.sin(a), 0)); w_, l_, h = ru.uniform(10, 22), ru.uniform(12, 40), ru.uniform(8, 22)
    UM.box((w_, l_, h), p_ + Vector((0, 0, h / 2)), ru.choice(WAND), rot=(0, 0, a))
    UM.box((w_ + .6, l_ + .6, 1.2), p_ + Vector((0, 0, h + .6)), ru.choice(DACH), rot=(0, 0, a))
UM.box((60, 40, .05), STAD + Vector((0, -125, .02)), mat("parkplatz", "3a3b3e", .9))
AUTO = [mat("auto%d" % i, f, .3, Coat_Weight=.8) for i, f in enumerate(("c62828", "1565c0", "e6e6e6", "212121", "8a8f96"))]
for i in range(8):
    for j in range(14):
        if ru.random() < .3:
            continue
        p_ = STAD + Vector((-26 + j * 4.0, -140 + i * 4.5 + (1 if i % 2 else 0), 0))
        mm = ru.choice(AUTO); UM.box((1.8, 4.3, .8), p_ + Vector((0, 0, .55)), mm); UM.box((1.6, 2.4, .6), p_ + Vector((0, -.2, 1.2)), mm)
UM.fertig("umgebung", bevel=.04)
oval_band("innenraum", .01, R_IN, .0, RASEN, n_k=96)
oval_band("bahn", R_IN, R_IN + BAHN, .01, TARTAN, n_k=96)
oval_band("bahn_aussen", R_IN + BAHN, R_IN + BAHN + 4, .01, TARTAN, n_k=96)
for k in range(9):
    oval_band("bahnlinie%d" % k, R_IN + k * 1.22 - .025, R_IN + k * 1.22 + .025, .016, WEISS_M, n_k=96)
oval_band("bord", R_IN - .12, R_IN, .05, mat("bord", "e8e8e6", .5), n_k=96)
# Fussballfeld-Linien
SM = Sammler()
FW, FH = 105.0, 68.0
for (sx, sy, x, y) in ((FW, .12, 0, -FH / 2), (FW, .12, 0, FH / 2), (.12, FH, -FW / 2, 0), (.12, FH, FW / 2, 0), (.12, FH, 0, 0)):
    SM.box((sx, sy, .01), STAD + Vector((x, y, .012)), WEISS_M)
for sgn in (-1, 1):
    for (sx, sy, dx) in ((16.5, .12, 8.25), (.12, 40.3, 16.5)):
        if sy > 1:
            SM.box((sx, sy, .01), STAD + Vector((sgn * (FW / 2 - dx), 0, .012)), WEISS_M)
        else:
            for yy in (-20.15, 20.15):
                SM.box((sx, sy, .01), STAD + Vector((sgn * (FW / 2 - dx), yy, .012)), WEISS_M)
for k in range(72):
    a = 2 * P * k / 72; a2 = 2 * P * (k + 1) / 72
    SM.rohr(STAD + Vector((9.15 * math.cos(a), 9.15 * math.sin(a), .012)), STAD + Vector((9.15 * math.cos(a2), 9.15 * math.sin(a2), .012)), .06, WEISS_M, v=4)
# Anlauf (x von -34 bis 0) mit Seitenlinien, Abwurfbogen, Sektor
box("anlauf", (34.0, 4.0, .03), Vector((-17.0, 0, .02)), TARTAN_RW, 0)
for sy in (-1, 1):
    SM.box((34.0, .05, .01), Vector((-17.0, sy * 2.0, .04)), WEISS_M)
C_ARC = Vector((-8.0, 0, 0))
for k in range(20):
    a = -.22 + .44 * k / 20; a2 = -.22 + .44 * (k + 1) / 20
    SM.box((.08, .1, .02), C_ARC + Vector((8 * math.cos(a), 8 * math.sin(a), .04)), WEISS_M, rot=(0, 0, a))
    SM.rohr(C_ARC + Vector((8 * math.cos(a), 8 * math.sin(a), .045)), C_ARC + Vector((8 * math.cos(a2), 8 * math.sin(a2), .045)), .035, WEISS_M, v=4)
SEKTOR = math.radians(28.96) / 2
for sgn in (-1, 1):
    d = Vector((math.cos(SEKTOR), sgn * math.sin(SEKTOR), 0))
    SM.rohr(C_ARC + d * 8 + Vector((0, 0, .02)), C_ARC + d * 110 + Vector((0, 0, .02)), .03, WEISS_M, v=4)
SCHILD_W = mat("distanzschild", "f6f6f4", .5)
for dist in range(50, 101, 10):
    r = dist + 8
    for k in range(30):
        a = -SEKTOR + 2 * SEKTOR * k / 30; a2 = -SEKTOR + 2 * SEKTOR * (k + 1) / 30
        SM.rohr(C_ARC + Vector((r * math.cos(a), r * math.sin(a), .02)), C_ARC + Vector((r * math.cos(a2), r * math.sin(a2), .02)), .025, WEISS_M, v=4)
SM.fertig("linien")
# Distanzschilder (aufgestellte Tafeln) an beiden Sektorrändern
for dist in range(50, 101, 10):
    r = dist + 8
    for sgn in (-1, 1):
        a = sgn * (SEKTOR + .015)
        p_ = C_ARC + Vector((r * math.cos(a), r * math.sin(a), 0))
        bpy.ops.object.text_add(location=p_ + Vector((0, 0, .45)), rotation=(P / 2, 0, -P / 2 + .5 * sgn * 0)); t_ = bpy.context.object
        t_.data.body = str(dist); t_.data.size = .5; t_.data.align_x = "CENTER"; t_.data.extrude = .01
        t_.data.materials.append(mat("schildzahl", "1a1a1a", .5) if not bpy.data.materials.get("schildzahl") else bpy.data.materials["schildzahl"])
        t_.location = p_ + Vector((-.06, 0, .35)); t_.rotation_euler = (P / 2, 0, -P / 2)
        box("distanztafel", (.06, .9, .7), p_ + Vector((0, 0, .5)), SCHILD_W, .01)
        rohr("tafelfuss", p_, p_ + Vector((0, 0, .15)), .02, STAHL)

# ======================================================================  Tribuenen mit echten (gebackenen) Zuschauern
SITZ_M = [mat("sitz%d" % i, f, .4) for i, f in enumerate(("1565c0", "c62828", "f9a825", "e6e6e6"))]
ST = Sammler()
REIHEN = 16
PLAETZE = []          # (pos, blick)
for sgn in (-1, 1):
    y0 = sgn * (R_IN + BAHN + 6.0)
    for r in range(REIHEN):
        y = y0 + sgn * r * .85; z = 1.2 + r * .45
        ST.box((2 * GER + 12, .85, z), Vector((STAD.x, y, z / 2)), BETON)
        ST.box((2 * GER + 12, .45, .12), Vector((STAD.x, y + sgn * .15, z + .32)), SITZ_M[(r // 4) % 4])
        x = STAD.x - GER - 5
        while x < STAD.x + GER + 5:
            PLAETZE.append((Vector((x, y + sgn * .05, z)), P if sgn < 0 else 0.0))
            x += .62
    ST.box((2 * GER + 14, .3, 3.2), Vector((STAD.x, y0 + sgn * (REIHEN * .85 + .2), 1.2 + REIHEN * .45 + 1.6)), BETON)
    # Dach
    zt = 1.2 + REIHEN * .45 + 6.5
    ST.box((2 * GER + 16, REIHEN * .85 + 6, .4), Vector((STAD.x, y0 + sgn * (REIHEN * .85 / 2 + 1.0), zt)), mat("dach", "d8dade", .4, metal=.4))
    for k in range(8):
        ST.rohr(Vector((STAD.x - GER - 6 + k * (2 * GER + 12) / 7, y0 + sgn * (REIHEN * .85 + .2), 0)),
                Vector((STAD.x - GER - 6 + k * (2 * GER + 12) / 7, y0 + sgn * (REIHEN * .85 + .2), zt)), .25, STAHL)
# Kurventribuenen (West hinter dem Anlauf und Ost hinter der Anzeigetafel): nur Stufen + Publikum
for cx_, a0, a1 in ((STAD.x - GER, P / 2 + .25, 3 * P / 2 - .25), (STAD.x + GER, -P / 2 + .25, P / 2 - .25)):
    for r in range(10):
        R = R_IN + BAHN + 8 + r * .85; z = 1.2 + r * .45
        n = int((a1 - a0) * R / 1.2)
        for k in range(n):
            a = a0 + (a1 - a0) * (k + .5) / n
            ST.box((.85, 1.25, z), Vector((cx_ + R * math.cos(a), R * math.sin(a), z / 2)), BETON, rot=(0, 0, a))
            if (k + r) % 2 == 0:
                PLAETZE.append((Vector((cx_ + R * math.cos(a), R * math.sin(a), z)), a - P / 2))
ST.fertig("tribuenen")
rz = random.Random(7)
PUBLIKUM = []
for i, (p_, blick) in enumerate(PLAETZE):
    if rz.random() > .62:
        continue
    o = bpy.data.objects.new("zs_%d" % i, rz.choice(ZUSCH_ME)); sc.collection.objects.link(o)
    o.location = p_ + Vector((0, 0, -.45)); o.rotation_euler = (0, 0, blick + rz.uniform(-.3, .3)); s_ = rz.uniform(.95, 1.03); o.scale = (s_, s_, s_)
    PUBLIKUM.append((o, o.location.z, rz.uniform(0, 6)))
print("publikum", len(PUBLIKUM))
# Kampfrichter am Sektor (stehende Menschen, keine Tribuene)
for (x, y, b) in ((88, 9, P), (100, -11, P / 2 + .3), (-1.5, 4.0, -P / 2 - .4), (60, 14, P)):
    o = bpy.data.objects.new("richter", ZUSCH_ME[(int(x) + 3) % len(ZUSCH_ME)]); sc.collection.objects.link(o)
    o.location = (x, y, 0); o.rotation_euler = (0, 0, b)

# Flutlichtmasten
FL = emis("flutlicht", "fff6e0", 3.0)
for sx in (-1, 1):
    for sy in (-1, 1):
        p_ = Vector((STAD.x + sx * (GER + 30), sy * (R_IN + BAHN + 24), 0))
        rohr("mast", p_, p_ + Vector((0, 0, 46)), .7, STAHL)
        box("strahlerfeld", (1.0, 7, 4), p_ + Vector((0, 0, 47)), FL, .05, rot=(0, -.5 * sx * 0, 0))

# Anzeigetafel (Ost) - vor dem Wurf "JAVELIN", danach 98.48
TAF = Vector((STAD.x + GER + R_IN + BAHN + 10, 0, 0))
p_a = os.path.join(HIER, "_sp_tafel_a.png"); p_b = os.path.join(HIER, "_sp_tafel_b.png")
ME.logo_bild(p_a, "JAVELIN", farbe=(1, .85, .2), symbol=False, hintergrund=(.02, .02, .04), unterzeile="MEN  -  JENA 1996", breite=1024, hoehe=512)
ME.logo_bild(p_b, "98.48", farbe=(1, .85, .2), symbol=False, hintergrund=(.02, .02, .04), unterzeile="ZELEZNY (CZE)  WR", breite=1024, hoehe=512)
TAFELN = []
for p_img in (p_a, p_b):
    bpy.ops.mesh.primitive_plane_add(size=1, location=TAF + Vector((-.36, 0, 12))); t_ = bpy.context.object; t_.scale = (20, 10, 1); t_.rotation_euler = (P / 2, 0, -P / 2)
    m_ = bpy.data.materials.new("tafel"); m_.use_nodes = True; ti = m_.node_tree.nodes.new("ShaderNodeTexImage"); ti.image = bpy.data.images.load(p_img)
    bsdf = m_.node_tree.nodes["Principled BSDF"]; m_.node_tree.links.new(ti.outputs[0], bsdf.inputs["Emission Color"]); bsdf.inputs["Emission Strength"].default_value = 3.0
    bsdf.inputs["Base Color"].default_value = (0, 0, 0, 1); t_.data.materials.append(m_); TAFELN.append(t_)
box("tafel_rahmen", (.6, 21, 11), TAF + Vector((0, 0, 12)), mat("tafelrahmen", "15161a", .5), .05)
for sy in (-1, 1):
    rohr("tafel_bein", TAF + Vector((.2, sy * 7, 0)), TAF + Vector((.2, sy * 7, 7)), .45, STAHL)

# ======================================================================  Speer (2,6 m; Spitze vorne +y)
SPEER_M = mat("speer", "c8ccd2", .22, metal=1.0, Coat_Weight=.4)
SPEER = dreh_koerper("speer", [(-1.50, .0), (-1.49, .004), (-1.40, .008), (-.6, .013), (-.10, .0145), (.10, .0145), (.6, .012), (.98, .008), (1.02, .007), (1.10, .0)], SPEER_M, nv=24)
SPEER.rotation_mode = "QUATERNION"
GRIFF = dreh_koerper("speer_griff", [(-.09, .0155), (-.085, .0175), (.085, .0175), (.09, .0155)], mat("griff", "1d2a55", .8), nv=24)
GRIFF.parent = SPEER
SPITZE = dreh_koerper("speer_spitze", [(.98, .0085), (1.0, .0078), (1.10, .0)], mat("spitze", "2a2a2e", .35, metal=.8), nv=24)
SPITZE.parent = SPEER
# Rasenstuecke beim Einstich
KLUMPEN = []
rk = random.Random(3)
for i in range(7):
    o = box("klumpen", (.05, .04, .03), (0, 0, -5), mat("erde", "4a3a28", .9), .01)
    KLUMPEN.append((o, Vector((rk.uniform(-1.5, 1.5), rk.uniform(-1.2, 1.2), rk.uniform(1.5, 3.0)))))
print("ok szene")
# ======================================================================  IK (Arme mit pole -P/2: Ellbogen natuerlich)
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


# ======================================================================  Zeitplan (Story-Zeit ts in s)
T_KREUZ = 3.6          # Beginn Impulsschritte / Speer zurueck
T_BLOCK = 4.98         # Stemmschritt links
T_REL = 5.22           # Abwurf
X_ = Vector((1, 0, 0)); UP = Vector((0, 0, 1))


def pel_x(t):
    if t < 4.95:
        return -29.5 + 5.6 * max(t, 0.0)
    if t < 5.3:
        return -1.78 + .78 * ease(seg(t, 4.95, 5.3))
    return -1.0 + .45 * ease(seg(t, 5.3, 5.9))


# Fusspunkte: (Zeit, x, y, Fuss)
PLANTS = []
fuss = "R"
for k in range(12):
    t = .1 + .3 * k; PLANTS.append((t, pel_x(t) + .3, -.11 if fuss == "R" else .11, fuss)); fuss = "L" if fuss == "R" else "R"
for t in (3.68, 3.96, 4.24, 4.50, 4.74):
    PLANTS.append((t, pel_x(t) + .25, .02 if fuss == "R" else .2, fuss)); fuss = "L" if fuss == "R" else "R"
PLANTS.append((T_BLOCK, -.75, .15, "L"))
PLANTS.append((5.55, -.3, -.3, "R"))


def fuesse_setzen(t):
    """Stand- und Schwungfuss aus der Fusspunkt-Liste"""
    pos = {}
    if t <= PLANTS[0][0]:
        pos["R"] = Vector((pel_x(t) + .1, -.11, .1)); pos["L"] = Vector((pel_x(t) - .25, .11, .1)); return pos
    k = max(i for i, p in enumerate(PLANTS) if p[0] <= t)
    tk, xk, yk, fk = PLANTS[k]
    stand_lift = 0.0
    if k + 1 < len(PLANTS):
        tn = PLANTS[k + 1][0]; f = seg(t, tk, tn)
        stand_lift = .06 * ease((f - .55) / .45) if tn - tk < .5 else 0.0
        pos[fk] = Vector((xk, yk, .1 + stand_lift))
        # Schwungfuss: von seinem letzten Punkt (k-1) zum naechsten (k+1)
        _, xa, ya, _ = PLANTS[k - 1] if k >= 1 else (0, pel_x(0) - .3, -.11 if fk == "L" else .11, "")
        _, xb, yb, fb = PLANTS[k + 1]
        hub = (.22 if tk < T_KREUZ else .14) * math.sin(P * f)
        e = ease(f)
        pos[fb] = Vector((xa + (xb - xa) * e, ya + (yb - ya) * e, .1 + hub))
    else:
        pos[fk] = Vector((xk, yk, .1))
        _, xa, ya, fa = PLANTS[k - 1]; pos[fa] = Vector((xa, ya, .1))
    return pos


def gier(t):
    """Drehung des Oberkoerpers um z (0 = Laufrichtung +x; negativ = linke Schulter vorne)"""
    if t < T_KREUZ:
        return 0.0
    if t < T_BLOCK:
        return -1.2 * ease(seg(t, T_KREUZ, 4.05))
    if t < T_REL:
        return -1.2 + 1.45 * ease(seg(t, T_BLOCK, T_REL))
    return .25 * (1 - ease(seg(t, T_REL, 5.8)))


def lehne(t):
    if t < T_KREUZ:
        return .12
    if t < T_BLOCK:
        return .12 - .32 * ease(seg(t, T_KREUZ, 4.6))
    if t < 5.35:
        return -.2 + .65 * ease(seg(t, T_BLOCK, 5.35))
    return .45 - .4 * ease(seg(t, 5.35, 6.3))


def speer_richtung(t):
    a = (math.radians(8) if t < T_KREUZ else math.radians(8) + math.radians(26) * ease(seg(t, T_KREUZ, 4.05)))
    if t >= T_BLOCK:
        a = math.radians(34) + math.radians(2) * seg(t, T_BLOCK, T_REL)
    return Vector((math.cos(a), 0, math.sin(a)))


# Flug: Abwurf an der Hand, Landung mit der Spitze bei 98,48 m
G = 9.81
REL = {}


def flugbahn(dt):
    p0 = REL["p"]; vx, vz = REL["v"]
    return Vector((p0.x + vx * dt, p0.y, p0.z + vz * dt - .5 * G * dt * dt)), Vector((vx, 0, vz - G * dt))


def landung_berechnen(p0):
    REL["p"] = p0.copy(); vz = 18.6
    # Zeit, bis die Mitte auf .45 m sinkt (Spitze steckt dann im Boden)
    a = -.5 * G; b = vz; c = p0.z - .45
    dt = (-b - math.sqrt(b * b - 4 * a * c)) / (2 * a)
    d_end = Vector((1, 0, (vz - G * dt) / 1)).normalized()
    # Spitze (1,1 m vor der Mitte) soll bei x = 98,48 landen
    vx = (98.48 - 1.1 * d_end.x * .9 - p0.x) / dt
    for _ in range(3):
        d_end = Vector((vx, 0, vz - G * dt)).normalized(); vx = (98.48 - 1.1 * d_end.x - p0.x) / dt
    REL["v"] = (vx, vz); REL["dt"] = dt; REL["d_end"] = d_end
    REL["p_end"] = flugbahn(dt)[0]


T_LAND = None


def figur(ts):
    global T_LAND
    KF.zuruecksetzen()
    for c in KF.IK.values():
        c.influence = 1.0
    t = ts
    g_ = gier(t); fw = Vector((math.cos(g_), math.sin(g_), 0)); le = Vector((-fw.y, fw.x, 0))
    lean = lehne(t)
    jubel = ease(seg(t, 9.35, 9.9)) if t > 9.3 else 0.0
    # Becken
    bob = .035 * math.sin(2 * P * (t - .1) / .3 - P / 2) if t < T_KREUZ else .02 * math.sin(2 * P * t / .26)
    tief = -.05 * math.sin(P * seg(t, T_KREUZ, T_REL)) - .04 * ease(seg(t, T_BLOCK - .1, T_BLOCK + .1)) * (1 - seg(t, T_REL, 5.6))
    hopp = .14 * abs(math.sin((t - 9.6) * 5.5)) * jubel if t < 12.5 else 0.0
    pel = Vector((pel_x(t), .0 + .06 * seg(t, T_KREUZ, 4.1) - .06 * seg(t, T_REL, 5.8), .97 + (bob if t < 5.3 else 0) + tief + hopp))
    H = fw * math.sin(lean) + UP * math.cos(lean); Fc = fw * math.cos(lean) - UP * math.sin(lean)
    rq = rig_mat(H, Fc).to_quaternion()
    KF.rig.rotation_mode = "QUATERNION"; KF.rig.rotation_quaternion = rq
    KF.rig.location = pel - rq.to_matrix() @ (KF.PEL * KF.SK)
    # Fuesse
    fp = fuesse_setzen(t)
    for sd in ("L", "R"):
        p_ = fp[sd]
        if hopp:
            p_ = p_ + Vector((0, 0, hopp * .9))
        KF.Z["fuss_" + sd].location = p_
    for sd, s_ in (("L", 1), ("R", -1)):
        KF.Z["knie_" + sd].location = pel + X_ * 2.0 + Vector((0, s_ * .35, -.3))
    sh_R = pel + H * .48 - le * .19; sh_L = pel + H * .48 + le * .19
    # rechte Hand (Speer)
    ph = 2 * P * (t - .1) / .6
    trag = sh_R + UP * .14 + X_ * (.02 + .03 * math.sin(ph)) + Vector((0, -.03, 0))
    zurueck = sh_R - X_ * .64 + UP * .06
    if t < T_KREUZ:
        hR = trag
    elif t < T_BLOCK:
        hR = trag.lerp(zurueck, ease(seg(t, T_KREUZ, 4.15)))
    elif t < T_REL:
        s = seg(t, T_BLOCK, T_REL) ** 1.5
        P0 = zurueck; P1 = sh_R + UP * .34 - X_ * .05; P2 = sh_R + X_ * .6 + UP * .2
        hR = P0 * (1 - s) ** 2 + P1 * 2 * s * (1 - s) + P2 * s * s
    elif t < 5.65:
        s = ease(seg(t, T_REL, 5.65))
        P2 = sh_R + X_ * .6 + UP * .2; P3 = pel + X_ * .38 + Vector((0, .22, -.08))
        hR = P2.lerp(P3, s)
    else:
        P3 = pel + X_ * .38 + Vector((0, .22, -.08)); ruhe = pel + Vector((.05, -.27, -.05))
        hR = P3.lerp(ruhe, ease(seg(t, 5.65, 6.6)))
    # linke Hand
    sp = -math.cos(ph)
    lauf_L = sh_L + X_ * (.08 + .24 * sp) - H * (.36 - .16 * sp) + Vector((0, .03, 0))
    vorn_L = sh_L + X_ * .58 + UP * .02
    zieh_L = pel + UP * .28 + Vector((-.05, .3, 0))
    if t < T_KREUZ:
        hL = lauf_L
    elif t < T_BLOCK:
        hL = lauf_L.lerp(vorn_L, ease(seg(t, T_KREUZ, 4.1)))
    elif t < 5.4:
        hL = vorn_L.lerp(zieh_L, ease(seg(t, T_BLOCK, 5.3)))
    else:
        hL = zieh_L.lerp(pel + Vector((.05, .27, -.05)), ease(seg(t, 5.4, 6.4)))
    KF.Z["hand_R"].location = hR; KF.Z["hand_L"].location = hL
    # Ellbogen: beim Wurf hoch/aussen, sonst nach hinten
    hoch = math.sin(P * seg(t, T_BLOCK, T_REL + .05))
    KF.Z["ell_R"].location = pel - X_ * 1.2 - le * .45 + UP * (.3 + 1.2 * hoch)
    KF.Z["ell_L"].location = pel - X_ * 1.2 + le * .45 + UP * .3
    if jubel > 0:
        KF.IK["hand_L"].influence = 1 - jubel; KF.IK["hand_R"].influence = 1 - jubel
        KF.dreh("upperarm01.L", z=-.72 + 3.0 * jubel, x=.2 * jubel); KF.dreh("upperarm01.R", z=.72 - 3.0 * jubel, x=.2 * jubel)
        KF.dreh("lowerarm01.L", x=-.4 * jubel); KF.dreh("lowerarm01.R", x=-.4 * jubel)
    # Kopf: schaut dem Speer nach (oben), sonst geradeaus
    blick = 0.0
    if T_REL < t < 9.3:
        dtf = t - T_REL; blick = -.55 * math.sin(P * min(1, dtf / 3.9)) + .1
    KF.dreh("neck01", x=-.5 * lean + blick)
    KF.dreh("head", z=-.6 * min(0, g_) * .8)        # Blick bleibt nach vorne, auch wenn der Koerper seitlich steht
    halt = t < T_REL
    for sd in ("L", "R"):
        for ff in range(2, 6):
            for g in (1, 2, 3):
                fest = (sd == "R" and halt)
                KF.dreh(f"finger{ff}-{g}.{sd}", x=(1.35 if fest else .5 + .12 * g) * (1 - jubel) + .1)
        for g in (2, 3):
            KF.dreh(f"finger1-{g}.{sd}", x=.45 * (1 - jubel))
    bpy.context.view_layer.update()
    # Speer
    if t < T_REL:
        d = speer_richtung(t)
        SPEER.location = hR + Vector((0, -.02, .0)) + d * .02
        SPEER.rotation_quaternion = d.to_track_quat("Y", "Z")
    else:
        if not REL:
            figur(T_REL - 1e-4)          # Abwurfpunkt genau aus der Hand
            landung_berechnen(SPEER.location.copy())
            return figur(ts)
        dtf = t - T_REL
        if dtf < REL["dt"]:
            p_, v_ = flugbahn(dtf)
            d = v_.normalized()
            SPEER.location = p_; SPEER.rotation_quaternion = d.to_track_quat("Y", "Z")
        else:
            d = REL["d_end"]; we = dtf - REL["dt"]
            wackel = .05 * math.sin(we * 38) * math.exp(-we * 3.0)
            q = d.to_track_quat("Y", "Z") @ Quaternion((1, 0, 0), wackel)
            SPEER.location = REL["p_end"]; SPEER.rotation_quaternion = q
            spitze = REL["p_end"] + REL["d_end"] * 1.05
            for o, v in KLUMPEN:
                if we < .9:
                    o.location = Vector((spitze.x, spitze.y, .05)) + Vector((v.x * we, v.y * we, v.z * we - 4.9 * we * we)) * .6
                    if o.location.z < .02:
                        o.location.z = .02
                else:
                    o.location.z = .02
    # Anzeigetafel nach der Landung
    land = REL and (t - T_REL) >= REL["dt"] + .6
    TAFELN[0].hide_render = bool(land); TAFELN[1].hide_render = not land
    for o, z0, ph_ in PUBLIKUM:
        o.location.z = z0 + (.1 * max(0, math.sin(t * 7 + ph_)) if land else 0.0)
    return pel, fw


from mathutils import Quaternion


def becken():
    nk = KF.rig.matrix_world @ KF.rig.pose.bones["neck01"].head
    return (KF.rig.matrix_world @ KF.PEL) * .55 + nk * .45


def kopf():
    return KF.rig.matrix_world @ KF.rig.pose.bones["head"].head + Vector((0, 0, .1))


def fuesse():
    return (KF.Z["fuss_L"].matrix_world.translation + KF.Z["fuss_R"].matrix_world.translation) / 2 + Vector((0, 0, .15))


# ======================================================================  Kamera
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam
cam.data.clip_start = .03; cam.data.clip_end = 3000; cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
cam.data.dof.use_dof = True
SZ = [
    # t0, t1, ts0, ts1, modus, pos0, pos1, ziel0, ziel1, brennweite
    (0.00, 1.50, 4.98, 5.32, "P", (2.6, -2.7, .45), (2.5, -2.6, .5), "B", "B", 22),                    # Aufhaenger: Abwurf in Zeitlupe
    (1.50, 2.60, 6.6, 7.5, "P", (44, -1.6, .3), (46, -1.6, .3), "J", "J", 55),                          # Speer ueber der Kamera
    (2.60, 3.55, 4.1, 4.5, "P", (-52, -20, 26), (-50, -19, 25), (40, 0, 0), (42, 0, 0), 22),           # Stadion von hinten oben
    (3.55, 5.95, 0.0, 0.0, "P", (-95, -175, 95), (-60, -160, 80), (60, 0, 5), (60, 0, 5), 22),          # Stadion aus der Luft
    (5.95, 8.00, 1.0, 3.0, "T", (1.6, -4.6, 1.2), (1.3, -4.4, 1.2), "B", "B", 30),                     # Anlauf, seitlich mitfahrend
    (8.00, 9.20, 3.62, 4.4, "T", (1.0, -3.0, .4), (1.0, -2.9, .4), "FU", "FU", 18),                    # Kreuzschritte
    (9.20, 10.90, 4.3, 4.96, "T", (-2.0, -2.8, 1.7), (-1.6, -2.9, 1.6), "B", "B", 26),                 # Arm ganz zurueck
    (10.90, 12.20, 4.96, 5.42, "P", (3.2, -1.7, .7), (3.1, -1.8, .65), "B", "B", 20),                 # Peitschen nach vorn
    (12.20, 14.30, 5.6, 7.3, "J+", (-4.5, -8.5, -2.2), (-3.5, -8.5, -1.5), "J", "J", 32),             # steigt hoeher als ein Haus
    (14.30, 16.60, 7.3, 8.3, "P", (68, -6, 1.0), (69, -6, 1.0), "J", "J", 20),                         # fliegt und fliegt
    (16.60, 18.00, 8.55, 9.45, "P", (104, -6.5, .5), (104, -6.3, .5), (96, 0, .4), (97, 0, .5), 30),   # Landung hinter der 90-m-Linie
    (18.00, 20.00, 9.6, 11.6, "P", (94.6, -2.4, .75), (95.0, -2.2, .85), (154, 0, 9), (154, 0, 10), 38),  # Speer + Tafel 98.48
    (20.00, 21.60, 11.6, 13.0, "P", (52, -6, 150), (54, -6, 158), (52, 0, 0), (54, 0, 0), 24),         # von oben: fast ein Fussballfeld
    (21.60, 25.00, 9.5, 12.9, "B+", (2.0, -2.4, .1), (2.6, -1.0, .5), "B", "B", 24),                  # Jubel
    (25.00, 28.00, 13.0, 16.0, "P", (97.6, -3.6, .8), (100.6, -2.7, 1.3), (98.0, 0, .75), (98.1, 0, .8), 26),  # Speer steckt im Rasen
]


def zustand(t):
    for s in SZ:
        if s[0] <= t < s[1]:
            break
    k = (t - s[0]) / (s[1] - s[0])
    ts = s[2] + (s[3] - s[2]) * k
    k = ease(k) * .7 + k * .3
    pel, fw = figur(ts)
    bk = becken()
    o = Vector(lerpv(s[5], s[6], k))
    jp = SPEER.location.copy()
    if s[4] == "T":
        pos = Vector((pel.x, 0, 0)) + o
    elif s[4] == "B+":
        pos = bk + o
    elif s[4] == "J+":
        pos = jp + o
    else:
        pos = o
    if s[7] == "B":
        ziel = bk
    elif s[7] == "FU":
        ziel = fuesse()
    elif s[7] == "J":
        ziel = jp
    else:
        ziel = Vector(lerpv(s[7], s[8], k))
    cam.location = pos; d = ziel - pos; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = s[9]; cam.data.dof.focus_distance = d.length; cam.data.dof.aperture_fstop = 2.8 if d.length < 6 else 11
    zit = .004
    cam.location += Vector((zit * math.sin(t * 7.3), zit * math.cos(t * 5.1), zit * math.sin(t * 9.7)))


os.makedirs(A.ordner, exist_ok=True)
N = int(round(D * A.fps))
liste = [int(round(float(x) * A.fps)) for x in A.nur.split(",")] if A.nur else list(range(A.start, N))
for f in liste:
    pfad = os.path.join(A.ordner, f"speer_{f:04d}.png")
    if os.path.exists(pfad) and not A.nur:
        continue
    zustand(f / A.fps); bpy.context.view_layer.update(); zustand(f / A.fps)
    sc.render.filepath = pfad
    bpy.ops.render.render(write_still=True); print("FERTIG", pfad, flush=True)
