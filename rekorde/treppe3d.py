"""Treppenlauf Empire State Building 9:33 (Paul Crake, 4.2.2003, GWR): 86 Stockwerke, 1576 Stufen. Realistischer Stil, viele Details.
python3 treppe3d.py <ordner> [--nur t1,t2] [--start i] [--samples n]"""
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
D = 26.6
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


# ======================================================================  Laeufer (zuerst)
import mensch_echt as ME
LOGO = ME.logo_bild(os.path.join(HIER, "_logo_norda.png"), "NORDA", farbe=(1, 1, 1))
BIB = ME.logo_bild(os.path.join(HIER, "_bib_tr.png"), "1", farbe=(.05, .05, .05), symbol=False, hintergrund=(.97, .97, .95), num=True, unterzeile="RUN-UP")
PC = ME.mensch("crake", 76, 1.0, .45, .65, .15, haut="caucasian", haare="short02", braue="eyebrow001", haarfarbe="6b4a2e")
ME.trikot(PC, "singlet", "shorts", "1565c0", "15171b", brust=BIB, brust_mass=(.16, .11), bein=LOGO)
for o in PC.huellen:
    if "versatz" in o.modifiers:
        o.modifiers["versatz"].strength = .017 if o.name.endswith("_hemd") else .010
    for md in o.modifiers:
        if md.type == "SUBSURF":
            md.render_levels = 2
hoehe = max(v.z for v in PC.EV); PC.SK = 1.76 / hoehe; PC.rig.scale = (PC.SK,) * 3
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
SCHWARZ = mat("schwarzlack", "0d0d0f", .4, Coat_Weight=.3)
STAHL = pbr("stahl", "Metal012", 6, rau_mul=.6, rau_add=.15, metal=1.0)
BETON = pbr("beton", "Concrete034", .6, tint="a8a49c")
PUTZ = pbr("putz", "PaintedPlaster017", .8, tint="d8d2c4")
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; nt = w.node_tree
env = nt.nodes.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(os.path.join(ASSET, "tag.hdr"))
nt.links.new(env.outputs[0], nt.nodes["Background"].inputs[0]); nt.nodes["Background"].inputs[1].default_value = 1.0


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
bpy.ops.object.light_add(type="SUN", rotation=(math.radians(52), 0, math.radians(-35))); sonne = bpy.context.object
sonne.data.energy = 4.2; sonne.data.angle = math.radians(1.0); sonne.data.color = (1, .95, .88)


def streifen_mat(name, grund, fenster, per_x, per_z, br_x, br_z, glanz=.3):
    """Fassade: Raster aus Fenstern (dunkel, spiegelnd) und Pfeilern; per = Rastermass, br = Pfeileranteil"""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt_ = m.node_tree; n = nt_.nodes; l = nt_.links; b = n["Principled BSDF"]
    tc = n.new("ShaderNodeTexCoord"); sp = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Object"], sp.inputs[0])
    hor = n.new("ShaderNodeMath"); hor.operation = "ADD"; l.new(sp.outputs["X"], hor.inputs[0]); l.new(sp.outputs["Y"], hor.inputs[1])
    def raster(src, per, br):
        a = n.new("ShaderNodeMath"); a.operation = "PINGPONG"; a.inputs[1].default_value = per / 2; l.new(src, a.inputs[0])
        c = n.new("ShaderNodeMath"); c.operation = "LESS_THAN"; c.inputs[1].default_value = per / 2 * br; l.new(a.outputs[0], c.inputs[0]); return c
    px = raster(hor.outputs[0], per_x, br_x); pz = raster(sp.outputs["Z"], per_z, br_z)
    mx = n.new("ShaderNodeMath"); mx.operation = "MAXIMUM"; l.new(px.outputs[0], mx.inputs[0]); l.new(pz.outputs[0], mx.inputs[1])
    no = n.new("ShaderNodeTexNoise"); no.inputs["Scale"].default_value = .4; l.new(tc.outputs["Object"], no.inputs["Vector"])
    rnd = n.new("ShaderNodeTexWhiteNoise"); rnd.noise_dimensions = "3D"
    fl = n.new("ShaderNodeVectorMath"); fl.operation = "SNAP"; fl.inputs[1].default_value = (per_x, per_x, per_z); l.new(tc.outputs["Object"], fl.inputs[0]); l.new(fl.outputs[0], rnd.inputs["Vector"])
    fcol = n.new("ShaderNodeMix"); fcol.data_type = "RGBA"; l.new(rnd.outputs["Value"], fcol.inputs[0])
    fcol.inputs[6].default_value = (*hexf(fenster), 1); fcol.inputs[7].default_value = (*[min(1, c * 2.2) for c in hexf(fenster)], 1)
    gcol = n.new("ShaderNodeMix"); gcol.data_type = "RGBA"; gcol.blend_type = "MULTIPLY"; gcol.inputs[0].default_value = .25
    gcol.inputs[6].default_value = (*hexf(grund), 1); l.new(no.outputs["Color"], gcol.inputs[7])
    mix = n.new("ShaderNodeMix"); mix.data_type = "RGBA"; l.new(mx.outputs[0], mix.inputs[0]); l.new(fcol.outputs[2], mix.inputs[6]); l.new(gcol.outputs[2], mix.inputs[7])
    l.new(mix.outputs[2], b.inputs["Base Color"])
    rr = n.new("ShaderNodeMapRange"); rr.inputs[3].default_value = .08; rr.inputs[4].default_value = .75; l.new(mx.outputs[0], rr.inputs[0]); l.new(rr.outputs[0], b.inputs["Roughness"])
    mt = n.new("ShaderNodeMapRange"); mt.inputs[3].default_value = glanz; mt.inputs[4].default_value = 0; l.new(mx.outputs[0], mt.inputs[0]); l.new(mt.outputs[0], b.inputs["Metallic"])
    bu = n.new("ShaderNodeBump"); bu.inputs["Strength"].default_value = .6; bu.inputs["Distance"].default_value = .05; l.new(mx.outputs[0], bu.inputs["Height"]); l.new(bu.outputs[0], b.inputs["Normal"])
    return m


KALKSTEIN = streifen_mat("esb_fassade", "d6cdb8", "1c242c", 1.6, 3.8, .45, .3, .5)
STADT_MATS = [streifen_mat("haus_%d" % i, g, f, px, pz, bx, bz) for i, (g, f, px, pz, bx, bz) in enumerate((
    ("b9a58a", "202830", 2.2, 3.4, .5, .35), ("8a8f96", "18222c", 1.8, 3.6, .3, .25), ("c9c2b2", "26303a", 2.6, 3.2, .55, .4),
    ("6e5a4a", "1a1e22", 2.0, 3.4, .45, .35), ("a4acb4", "2a3a4a", 3.2, 3.8, .2, .15), ("d0c8b8", "222a34", 1.6, 3.0, .5, .3)))]

# ======================================================================  Manhattan (Stadt um das Empire State Building, Mittelpunkt bei STADT)
STADT = Vector((6000, 0, 0))
box("strassen", (4000, 4000, .2), STADT + Vector((0, 0, -.1)), mat("asphalt", "36373a", .9), 0)
rs = random.Random(11)
BLOCK_X, BLOCK_Y = 80.0, 260.0          # Manhattan-Raster (Strassen schmal, Avenues breit)
HOLZ_TANK = mat("holz_tank", "6a4a2a", .8)
SM = Sammler()
for i in range(-14, 15):
    for j in range(-6, 7):
        cx = STADT.x + i * BLOCK_X; cy = STADT.y + j * BLOCK_Y
        if abs(i) <= 1 and j == 0:
            continue
        d = math.hypot(i * BLOCK_X, j * BLOCK_Y)
        n_b = rs.randint(2, 4)
        for k in range(n_b):
            bx_ = BLOCK_X - 18; by_ = (BLOCK_Y - 30) / n_b; yk = cy - (BLOCK_Y - 30) / 2 + by_ * (k + .5)
            h = rs.choice((25, 40, 60, 90, 120, 160, 200)) * (1.25 if d < 700 else .8) * rs.uniform(.7, 1.2)
            mm = rs.choice(STADT_MATS)
            SM.box((bx_ - 2, by_ - 2, h), (cx, yk, h / 2), mm)
            if h > 120 and rs.random() < .4:                                 # Aufbau
                SM.box((bx_ * .5, by_ * .5, 8), (cx, yk, h + 4), mm)
            if rs.random() < .35:
                SM.zyl(2.2, 4, (cx + rs.uniform(-10, 10), yk, h + 2), HOLZ_TANK)
SM.fertig("stadt")
# Empire State Building (gestuft, Art-Deco-Krone, Mast)
E = STADT
ALUBAND = mat("aluband", "b8bcc0", .25, metal=1.0)
box("esb_sockel", (130, 57, 25), E + Vector((0, 0, 12.5)), KALKSTEIN, .3)
for (sx, sy, z0, z1) in ((95, 50, 25, 82), (75, 45, 82, 230), (62, 40, 230, 262), (50, 34, 262, 300), (40, 28, 300, 320)):
    box("esb_stufe", (sx, sy, z1 - z0), E + Vector((0, 0, (z0 + z1) / 2)), KALKSTEIN, .3)
    for sgn in (-1, 1):                                                       # vertikale Lisenen (Metallbaender)
        for k in range(-3, 4):
            SM.box((.6, .5, z1 - z0), E + Vector((k * sx / 8, sgn * (sy / 2 + .1), (z0 + z1) / 2)), ALUBAND)
SM.fertig("lisenen")
DECK_Z = 320.0
box("esb_krone", (25, 20, 28), E + Vector((0, 0, DECK_Z + 14)), KALKSTEIN, .3)
box("esb_krone2", (18, 14, 22), E + Vector((0, 0, DECK_Z + 39)), KALKSTEIN, .3)
zyl("esb_mast", 4, 60, E + Vector((0, 0, DECK_Z + 80)), mat("mast", "c8ccd0", .3, metal=.8))
zyl("esb_antenne", .8, 60, E + Vector((0, 0, DECK_Z + 140)), mat("antenne", "e6e6e6", .4, metal=.6))
# Aussichtsterrasse im 86. Stock: Boden, Bruestung, Gitter, Zielband, Zeittafel
DECK = E + Vector((0, 0, DECK_Z))
box("deck_boden", (40.2, 28.2, .3), DECK + Vector((0, 0, -.13)), pbr("deckplatten", "Concrete034", 1.2, tint="9a958c"), 0)
for (sx, sy, dx, dy) in ((40, .5, 0, -13.8), (40, .5, 0, 13.8), (.5, 28, -19.8, 0), (.5, 28, 19.8, 0)):
    box("bruestung", (sx, sy, 1.1), DECK + Vector((dx, dy, .55)), KALKSTEIN, .05)
GITTER = mat("gitter", "3a3d42", .4, metal=.8)
for x in range(-19, 20):
    for sy in (-1, 1):
        SM.rohr(DECK + Vector((x, sy * 13.8, 1.1)), DECK + Vector((x + .0, sy * 13.8 - sy * .6, 3.0)), .02, GITTER)
for x in range(-19, 20, 3):
    for sy in (-1, 1):
        SM.rohr(DECK + Vector((x, sy * 13.6, 2.2)), DECK + Vector((x + 3, sy * 13.6, 2.2)), .015, GITTER)
SM.fertig("gitter")
TUER_POS = DECK + Vector((-12.6, -5, 0))
TUERM = mat("tuer", "7a2a1a", .5, Coat_Weight=.4)
box("tuerrahmen", (.3, 1.6, 2.4), TUER_POS + Vector((0, 0, 1.2)), TUERM, .03)
TUER_ANGEL = leer("tuer_angel", TUER_POS + Vector((-.17, -.6, 0)))
box("tuerblatt", (.05, 1.2, 2.2), TUER_POS + Vector((-.17, 0, 1.1)), TUERM, .01, eltern=TUER_ANGEL).location = (0, .6, 1.1)
box("tueroeffnung", (.32, 1.2, 2.2), TUER_POS + Vector((0, 0, 1.1)), mat("dunkel", "080808", .9), .01)
ZIEL_POS = TUER_POS + Vector((-4.0, 0, 0))
for sy in (-1, 1):
    rohr("zielpfosten", ZIEL_POS + Vector((0, sy * 1.4, 0)), ZIEL_POS + Vector((0, sy * 1.4, 1.3)), .03, STAHL)
ZBM = mat("zielband", "d0141a", .5)
ZIELBAND = box("zielband", (.02, 2.8, .06), ZIEL_POS + Vector((0, 0, 1.2)), ZBM, 0)
ZB_HALB = []
for sy in (-1, 1):
    e_ = leer("zb_angel", ZIEL_POS + Vector((0, sy * 1.4, 1.2)))
    h_ = box("zb_halb", (.02, 1.4, .06), ZIEL_POS, ZBM, 0, eltern=e_); h_.location = (0, -sy * .7, 0); h_.hide_render = True
    ZB_HALB.append((e_, h_, sy))
p_uhr = os.path.join(HIER, "_tr_uhr.png")
ME.logo_bild(p_uhr, "9:33", farbe=(1, .2, .15), symbol=False, hintergrund=(.02, .02, .03), unterzeile="RUN-UP", breite=640, hoehe=320)
bpy.ops.mesh.primitive_plane_add(size=1, location=TUER_POS + Vector((-.32, -2.4, 2.5))); uhr = bpy.context.object; uhr.scale = (2.0, 1.0, 1); uhr.rotation_euler = (P / 2, 0, -P / 2)
mu = bpy.data.materials.new("uhr"); mu.use_nodes = True; ti = mu.node_tree.nodes.new("ShaderNodeTexImage"); ti.image = bpy.data.images.load(p_uhr)
bu_ = mu.node_tree.nodes["Principled BSDF"]; mu.node_tree.links.new(ti.outputs[0], bu_.inputs["Emission Color"]); bu_.inputs["Emission Strength"].default_value = 2.5; UHR_EM = bu_.inputs["Emission Strength"]
bu_.inputs["Base Color"].default_value = (0, 0, 0, 1); uhr.data.materials.append(mu)
box("uhr_rahmen", (.2, 2.2, 1.2), TUER_POS + Vector((-.2, -2.4, 2.5)), SCHWARZ, .03)

# ======================================================================  Lobby (Start): Marmor, Art-Deco-Wand, Startlinie
LOB = Vector((-400, 0, 0))
GOLD = mat("gold", "c9a24a", .25, metal=1.0)
MARMOR = pbr("marmor", "PaintedPlaster017", .4, tint="e4e0d8", rau_mul=.3)
box("lobby_boden", (40, 16, .2), LOB + Vector((0, 0, -.1)), MARMOR, 0)
box("lobby_decke", (40, 16, .3), LOB + Vector((0, 0, 9)), mat("decke", "b08a4a", .4, metal=.5), 0)
for sy in (-1, 1):
    box("lobby_wand", (40, .4, 9), LOB + Vector((0, sy * 8, 4.5)), mat("marmorwand", "7a5a3a", .25, Coat_Weight=.6), 0)
    for k in range(-9, 10, 2):
        SM.box((.25, .05, 8.6), LOB + Vector((k * 2, sy * 7.78, 4.3)), GOLD)
SM.fertig("gold")
box("lobby_vorne", (.4, 16, 9), LOB + Vector((-20, 0, 4.5)), bpy.data.materials["marmorwand"], 0)
box("lobby_rueck", (.4, 16, 9), LOB + Vector((20, 0, 4.5)), mat("marmorwand", "7a5a3a", .25) if not bpy.data.materials.get("marmorwand") else bpy.data.materials["marmorwand"], 0)
box("treppentuer", (.45, 2.0, 2.6), LOB + Vector((19.8, 0, 1.3)), mat("dunkel", "080808", .9) if not bpy.data.materials.get("dunkel") else bpy.data.materials["dunkel"], .02)
box("startlinie", (.3, 6, .02), LOB + Vector((10, 0, .01)), mat("startlinie", "f2f2f2", .5), 0)
for k in range(6):
    bpy.ops.object.light_add(type="AREA", location=LOB + Vector((-15 + k * 6, 0, 8.6))); L_ = bpy.context.object; L_.data.size = 3; L_.data.energy = 900; L_.data.color = (1, .95, .88)
    L_.rotation_euler = (P, 0, 0)

# ======================================================================  Treppenhaus (Module: 14 Geschosse uebereinander, wiederholt)
GH = 3.6; STUFE_H = .18; STUFE_T = .28; N_ST = 10; BREITE = 1.15; GAP = .22
_vor = set(bpy.data.objects)
LAUF_L = N_ST * STUFE_T
TR = Vector((0, 0, 0))
STUFEN_M = pbr("stufenbeton", "Concrete034", 1.6, tint="9c978e")
KANTE = mat("stufenkante", "e8c21a", .5)
WAND_M = mat("treppenwand", "d9d4c6", .85)
GELAENDER = mat("gelaender", "2a5a8a", .35, Coat_Weight=.5)
N_GESCH = 14
SCHILDER = []
SCHILD_T = mat("schild_text", "f2f2f2", .5); SCHILD_G = mat("schild_gruen", "1b6b3a", .4)
NOTL = emis("notlicht", "fff4e0", 8); LOESCH = mat("loescher", "c62828", .3, Coat_Weight=.7)
ROHR_M = [mat("rohr0", "c62828", .35, Coat_Weight=.5), mat("rohr1", "8a8f96", .35, Coat_Weight=.5)]
TUER_T = mat("treppentuer_m", "4a5a6a", .4, metal=.5)
ST = Sammler()
for g in range(N_GESCH):
    z0 = g * GH
    for lauf in (0, 1):                                       # Lauf A (+x, y<0) und Lauf B (-x, y>0)
        for s_ in range(N_ST):
            if lauf == 0:
                x = s_ * STUFE_T; y = -BREITE / 2 - GAP
            else:
                x = LAUF_L - (s_ + 1) * STUFE_T; y = BREITE / 2 + GAP
            zb = z0 + lauf * GH / 2; z = zb + (s_ + 1) * STUFE_H
            ST.box((STUFE_T, BREITE, z - zb + .15), TR + Vector((x + STUFE_T / 2, y, (z + zb - .15) / 2)), STUFEN_M)
            ST.box((.05, BREITE - .1, .012), TR + Vector((x + (STUFE_T - .03 if lauf == 1 else .03), y, z + .006)), KANTE)
    for (px_, pz_) in ((LAUF_L + .65, z0 + GH / 2), (-.65, z0 + GH)):
        ST.box((1.3, 2 * (BREITE + GAP), .25), TR + Vector((px_, 0, pz_ - .125)), STUFEN_M)
    for lauf, sy in ((0, -1), (1, 1)):                         # Gelaender innen mit Pfosten
        a = TR + Vector((0 if lauf == 0 else LAUF_L, sy * (GAP + .04), z0 + lauf * GH / 2 + .95))
        b_ = TR + Vector((LAUF_L if lauf == 0 else 0, sy * (GAP + .04), z0 + lauf * GH / 2 + GH / 2 + .95))
        ST.rohr(a, b_, .025, GELAENDER)
        ST.rohr(a - Vector((0, 0, .45)), b_ - Vector((0, 0, .45)), .012, GELAENDER)
        for k in range(0, 11, 2):
            p_ = a.lerp(b_, k / 10); ST.rohr(p_ - Vector((0, 0, .95 - .18 * (k % 2))), p_, .015, GELAENDER)
    ST.rohr(TR + Vector((LAUF_L, -GAP - .04, z0 + GH / 2 + .95)), TR + Vector((LAUF_L, GAP + .04, z0 + GH / 2 + .95)), .025, GELAENDER)
    ST.rohr(TR + Vector((0, GAP + .04, z0 + GH + .95)), TR + Vector((0, -GAP - .04, z0 + GH + .95)), .025, GELAENDER)
    # Schild, Tuer zum Stockwerk, Notlicht, Feuerloescher, Kabelkanal
    ST.box((.03, .8, .7), TR + Vector((-1.3, 0, z0 + GH + 1.86)), SCHILD_G)
    ST.box((.06, 1.0, 2.1), TR + Vector((-1.31, -.0 - 0, z0 + GH + 1.05)) + Vector((0, -BREITE - GAP + .62, 0)), TUER_T)
    ST.box((.04, .08, .03), TR + Vector((-1.27, -BREITE - GAP + .25, z0 + GH + 1.0)), STAHL)
    ST.box((.08, .3, .12), TR + Vector((LAUF_L + 1.28, .5, z0 + GH / 2 + 2.3)), NOTL)
    ST.box((.08, .3, .12), TR + Vector((-1.28, -.6, z0 + GH + 2.4)), NOTL)
    ST.zyl(.08, .5, TR + Vector((LAUF_L + 1.2, -.9, z0 + GH / 2 + .35)), LOESCH)
    ST.box((.05, .3, .12), TR + Vector((LAUF_L + 1.27, -.9, z0 + GH / 2 + .9)), LOESCH)
    bpy.ops.object.text_add(location=TR + Vector((-1.262, 0, z0 + GH + 1.7)), rotation=(P / 2, 0, P / 2)); t_ = bpy.context.object
    t_.data.body = "0"; t_.data.size = .55; t_.data.align_x = "CENTER"; t_.data.extrude = .01; t_.data.materials.append(SCHILD_T)
    SCHILDER.append((t_, g))
    for (lp, en) in (((LAUF_L + 1.0, .3, z0 + GH / 2 + 2.2), 90), ((-1.0, -.3, z0 + GH + 2.2), 70)):
        L_ = bpy.data.objects.new("licht_%d_%d" % (g, en), bpy.data.lights.new("licht_%d_%d" % (g, en), "POINT")); sc.collection.objects.link(L_)
        L_.location = TR + Vector(lp); L_.data.energy = en; L_.data.color = (1, .95, .85); L_.data.shadow_soft_size = .3
HW = N_GESCH * GH + 4
ST.box((LAUF_L + 3.2, .2, HW), TR + Vector((LAUF_L / 2, -BREITE - GAP - .2, HW / 2 - 2)), WAND_M)
ST.box((LAUF_L + 3.2, .2, HW), TR + Vector((LAUF_L / 2, BREITE + GAP + .2, HW / 2 - 2)), WAND_M)
ST.box((.2, 2 * (BREITE + GAP) + .5, HW), TR + Vector((LAUF_L + 1.4, 0, HW / 2 - 2)), WAND_M)
ST.box((.2, 2 * (BREITE + GAP) + .5, HW), TR + Vector((-1.4, 0, HW / 2 - 2)), WAND_M)
for k, yy in enumerate((-BREITE - GAP + .06, -BREITE - GAP + .2)):
    ST.zyl(.06 if k == 0 else .04, HW, TR + Vector((LAUF_L + 1.15, yy, HW / 2 - 2)), ROHR_M[k])
ST.box((.06, .1, HW), TR + Vector((-1.28, BREITE + GAP - .05, HW / 2 - 2)), mat("kabelkanal", "bdbab2", .6))
ST.fertig("treppe", bevel=.008)
STACK = leer("stack")
for o in set(bpy.data.objects) - _vor:
    if o.parent is None and o is not STACK:
        o.parent = STACK
print("ok szene")
# ======================================================================  IK
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


# ======================================================================  Zuschauer: Lobby und Terrasse
BAR_M = mat("absperrung", "1b1b1f", .4, metal=.6); BAND_M = mat("absperrband", "c9a24a", .4)
PUBLIKUM = []
rp = random.Random(4)


def absperrung(a, b):
    a, b = Vector(a), Vector(b); n = max(1, int((b - a).length / 1.6))
    for k in range(n + 1):
        p_ = a.lerp(b, k / n); zyl("pfosten_abs", .035, 1.0, p_ + Vector((0, 0, .5)), BAR_M, v=12)
        zyl("fuss_abs", .16, .03, p_ + Vector((0, 0, .015)), BAR_M, v=16)
        if k < n:
            q_ = a.lerp(b, (k + 1) / n); rohr("band_abs", p_ + Vector((0, 0, .92)), q_ + Vector((0, 0, .92)), .025, BAND_M)


def leute(x0, x1, y0, sy, reihen, z, blick, dichte=.8):
    for reihe in range(reihen):
        x = x0
        while x < x1:
            x += rp.uniform(.55, .8)
            if rp.random() > dichte:
                continue
            o = bpy.data.objects.new("pub_%d" % len(PUBLIKUM), rp.choice(ZUSCH_ME)); sc.collection.objects.link(o)
            o.location = (x, y0 + sy * (reihe * .7 + rp.uniform(-.15, .15)), z)
            o.rotation_euler = (0, 0, blick + rp.uniform(-.5, .5)); s_ = rp.uniform(.95, 1.05); o.scale = (s_, s_, s_)
            PUBLIKUM.append((o, z, rp.uniform(0, 6)))


for sy in (-1, 1):
    absperrung(LOB + Vector((-6, sy * 2.6, 0)), LOB + Vector((18.5, sy * 2.6, 0)))
    leute(LOB.x - 6, LOB.x + 18, LOB.y + sy * 3.2, sy, 3, 0, (0 if sy > 0 else P))
    absperrung(DECK + Vector((-19, sy * 1.9, 0)) + Vector((0, -5, 0)), DECK + Vector((-13.2, sy * 1.9, 0)) + Vector((0, -5, 0)))
    leute(DECK.x - 19.3, DECK.x - 13.4, DECK.y - 5 + sy * 2.5, sy, 2, DECK.z, (0 if sy > 0 else P), .85)
print("publikum", len(PUBLIKUM))

# ======================================================================  Gang: Fusspunkte (Stufen zwei auf einmal, Lobby und Terrasse flach)
LANE = GAP + .35
RAIL_Y = GAP + .04
T_STAIR_END = 571.0
LOBBY_SCHRITT = 1.1
LOBBY_ANZ = 9.8 / LOBBY_SCHRITT
N_FLOORS = 85
TP = T_STAIR_END / (N_FLOORS * 14 + LOBBY_ANZ)
T_ST = LOBBY_ANZ * TP
DECK_SCHRITT = .96
START = LOB + Vector((10.0, 0, 0))


def plan_lokal(j):
    """Fusspunkt-Mitte j (0..13) innerhalb eines Geschosses; z = Stufenoberflaeche"""
    if j <= 4:
        i = 2 * j + 1; return Vector(((i + .5) * STUFE_T, -LANE, (i + 1) * STUFE_H))
    if j == 5:
        return Vector((LAUF_L + .35, -GAP - .25, GH / 2))
    if j == 6:
        return Vector((LAUF_L + .4, GAP + .25, GH / 2))
    if j <= 11:
        i = 2 * (j - 7) + 1; return Vector((LAUF_L - (i + .5) * STUFE_T, LANE, GH / 2 + (i + 1) * STUFE_H))
    if j == 12:
        return Vector((-.35, GAP + .25, GH))
    return Vector((-.4, -GAP - .25, GH))


def c_treppe(k):
    F = k // 14; j = k % 14
    return plan_lokal(j) + Vector((0, 0, F * GH))


def c_lobby(k):
    return START + Vector((LOBBY_SCHRITT * k, 0, 0))


def c_deck(k):
    return TUER_POS + Vector((-.2 - DECK_SCHRITT * k, 0, 0))


DECK_STOP = 5.4


def phase(ts):
    """liefert (Mittelpunktfunktion, q, qmax)"""
    if ts < T_ST:
        return c_lobby, max(-.001, ts / TP), LOBBY_ANZ + 3
    if ts < T_STAIR_END:
        return c_treppe, (ts - T_ST) / TP, 1e9
    return c_deck, (ts - T_STAIR_END) / TP, DECK_STOP


def C(cf, x):
    k = math.floor(x); f = x - k
    return cf(k).lerp(cf(k + 1), f)


def links(fw):
    return Vector((-fw.y, fw.x, 0))


def fwd_at(cf, x):
    d = C(cf, x + .35) - C(cf, x - .35); d.z = 0
    return d.normalized() if d.length > 1e-4 else Vector((1, 0, 0))


def fusspunkt(cf, k):
    fw = fwd_at(cf, k); seite = .095 if k % 2 == 0 else -.095
    return cf(k) + links(fw) * seite + Vector((0, 0, .1))


def floor_von(ts):
    if ts < T_ST:
        return 0
    if ts >= T_STAIR_END:
        return N_FLOORS
    return int(((ts - T_ST) / TP) // 14)


def tsp(F, j):
    return T_ST + (F * 14 + j) * TP


def figur(ts):
    KF.zuruecksetzen()
    for c in KF.IK.values():
        c.influence = 1.0
    cf, q, qmax = phase(ts)
    steht = q < 0 or q >= qmax
    qq = min(max(q, 0.0), qmax)
    k = math.floor(qq); f = qq - k
    treppe = cf is c_treppe
    if steht:
        fw = fwd_at(cf, qq)
        lf = cf(math.floor(qq)) if q >= qmax else cf(0)
        for sd, s_ in (("L", 1), ("R", -1)):
            KF.Z["fuss_" + sd].location = lf + links(fw) * (s_ * .12) + Vector((0, 0, .1)) + fw * (.12 if (sd == "L") == (q < 0) else 0) * (-1 if q < 0 else 1)
        pel = lf + Vector((0, 0, .95 if q >= qmax else .9))
        lean = 0.0 if q >= qmax else .15
    else:
        stand = fusspunkt(cf, k)
        sw0 = fusspunkt(cf, k - 1); sw1 = fusspunkt(cf, k + 1)
        if k == 0:
            sw0 = cf(0) + links(fwd_at(cf, 0)) * (.095 if k % 2 else -.095) + Vector((0, 0, .1)) - fwd_at(cf, 0) * .3
        e = ease(f)
        swing = sw0.lerp(sw1, e) + Vector((0, 0, (.26 if treppe else .18) * math.sin(P * f)))
        # Ferse loest sich am Ende der Stuetzphase
        stand = stand + Vector((0, 0, .05 * ease((f - .6) / .4)))
        st_sd, sw_sd = ("L", "R") if k % 2 == 0 else ("R", "L")
        KF.Z["fuss_" + st_sd].location = stand; KF.Z["fuss_" + sw_sd].location = swing
        fw = fwd_at(cf, qq)
        pel = C(cf, qq - .5) + Vector((0, 0, (.83 if treppe else .9) + .035 * math.sin(2 * P * f - P / 2)))
        pel -= fw * (.02 if treppe else 0)
        lean = .38 if treppe else .2
        if cf is c_deck:
            lean *= 1 - ease((q - (DECK_STOP - 1.2)) / 1.2)
    up = Vector((0, 0, 1)); le = links(fw)
    H = (fw * math.sin(lean) + up * math.cos(lean)); Fc = (fw * math.cos(lean) - up * math.sin(lean))
    rq = rig_mat(H, Fc).to_quaternion()
    KF.rig.rotation_mode = "QUATERNION"; KF.rig.rotation_quaternion = rq
    KF.rig.location = pel - rq.to_matrix() @ (KF.PEL * KF.SK)
    for sd, s_ in (("L", 1), ("R", -1)):
        KF.Z["knie_" + sd].location = pel + fw * 2.0 + le * (s_ * .35) - up * .3
        KF.Z["ell_" + sd].location = pel - fw * 1.2 + le * (s_ * .45) + up * .3     # Ellbogen zeigen nach hinten
    # Arme: links am Gelaender (Treppe), rechts pumpt; flach: beide pumpen
    ph = 2 * P * (qq / 2.0)
    schulter = pel + H * .5
    jubel = ease((ts - (T_STAIR_END + DECK_STOP * TP + .25)) / .8) if cf is c_deck else 0.0
    if treppe:
        xr = qq - .5 + .25
        rail = C(cf, xr) + le * (LANE - RAIL_Y) * .8
        rail.z = C(cf, xr).z + .95 + .04
        KF.Z["hand_L"].location = rail
        sp = math.cos(ph)                               # rechter Arm schwingt gegengleich zum rechten Bein
        KF.Z["hand_R"].location = schulter - le * (.19 - .04 * sp) + fw * (.06 + .2 * sp) - H * (.36 - .14 * sp)
    elif steht and q < 0:
        for sd, s_ in (("L", 1), ("R", -1)):
            KF.Z["hand_" + sd].location = schulter + le * (s_ * .26) - H * .42 + fw * (.15 if sd == "R" else -.05)
    else:
        amp = 0 if steht else 1
        for sd, s_ in (("L", 1), ("R", -1)):
            sp = (-math.cos(ph) if sd == "L" else math.cos(ph)) * amp      # Arm gegengleich zum Bein, Ellbogen ~90 Grad
            KF.Z["hand_" + sd].location = schulter + le * (s_ * (.2 - .05 * max(0, sp))) + fw * (.08 + .24 * sp) - H * (.36 - .16 * sp)
    if jubel > 0:
        KF.IK["hand_L"].influence = 1 - jubel; KF.IK["hand_R"].influence = 1 - jubel
        KF.dreh("upperarm01.L", z=-.72 + 3.0 * jubel, x=.2 * jubel); KF.dreh("upperarm01.R", z=.72 - 3.0 * jubel, x=.2 * jubel)
        KF.dreh("lowerarm01.L", x=-.4 * jubel); KF.dreh("lowerarm01.R", x=-.4 * jubel)
    KF.dreh("neck01", x=-.6 * lean + .15 * jubel)
    for sd in ("L", "R"):
        for ff in range(2, 6):
            for g in (1, 2, 3):
                KF.dreh(f"finger{ff}-{g}.{sd}", x=(1.2 if (treppe and sd == "L") else .55 + .12 * g) * (1 - jubel) + .12)
        for g in (2, 3):
            KF.dreh(f"finger1-{g}.{sd}", x=.45 * (1 - jubel))                    # Daumen locker angelegt
    # Treppenhaus mitfuehren (identische Geschosse), Stockwerk-Schilder
    Fi = floor_von(ts)
    STACK.location = (0, 0, GH * (Fi - 6))
    for t_, g in SCHILDER:
        Fa = Fi - 6 + g
        txt = str(Fa + 2) if Fa >= 0 else ""
        if t_.data.body != txt:
            t_.data.body = txt
    # Tuer und Zielband
    UHR_EM.default_value = 2.5 if ts >= 573.0 else 0.0
    TUER_ANGEL.rotation_euler = (0, 0, 1.75 * ease((ts - (T_STAIR_END - .5)) / .5))
    zx = KF.rig.location.x
    gerissen = cf is c_deck and C(cf, qq).x < ZIEL_POS.x + .15
    ZIELBAND.hide_render = gerissen
    for e_, h_, sy in ZB_HALB:
        h_.hide_render = not gerissen
        if gerissen:
            dt = ts - 573.0
            e_.rotation_euler = (sy * -1.3 * ease(dt / .6) + sy * .1 * math.sin(dt * 9) * math.exp(-dt * 2), 0, -.5 * sy * ease(dt / .4))
    for o, z0, ph_ in PUBLIKUM:
        o.location.z = z0 + (.1 * max(0, math.sin(ts * 7 + ph_)) if ts > 572.8 else .015 * math.sin(ts * 2 + ph_))
    bpy.context.view_layer.update()
    return pel, fw


def becken():
    nk = KF.rig.matrix_world @ KF.rig.pose.bones["neck01"].head
    return (KF.rig.matrix_world @ KF.PEL) * .55 + nk * .45


def kopf():
    return KF.rig.matrix_world @ KF.rig.pose.bones["head"].head + Vector((0, 0, .1))


def fuesse():
    return (KF.Z["fuss_L"].matrix_world.translation + KF.Z["fuss_R"].matrix_world.translation) / 2 + Vector((0, 0, .15))


# ======================================================================  Kamera
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam
cam.data.clip_start = .03; cam.data.clip_end = 9000; cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
cam.data.dof.use_dof = True
Fh = 40; Ff = 20; Fz = 30; Fg = 60
SZ = [
    # t0, t1, ts0, ts1, modus, pos0, pos1, ziel0, ziel1, brennweite, extra
    (0.00, 1.40, tsp(Fh, 2.3), tsp(Fh, 3.2), "R+", (-1.5, .05, -.45), (-1.35, .1, -.4), "KO", "KO", 16, {}),       # Aufhaenger: von unten hinten, Zeitlupe
    (1.40, 2.40, tsp(Ff, 1.0), tsp(Ff, 3.0), "R+", (.75, -.55, -.25), (.8, -.55, -.25), "FU", "FU", 20, {}),          # Fuesse, zwei Stufen
    (2.40, 3.70, tsp(10, 3), tsp(10, 5.5), "S", (1.4, 0, .5), (1.4, 0, .5), (1.4, .02, 40), (1.5, .3, 40), 14, {"dF": -2}),  # Blick hoch ins Treppenauge
    (3.70, 5.90, 300, 300, "P", E + Vector((-420, -620, 260)), E + Vector((-380, -560, 280)), E + Vector((0, 0, 190)), E + Vector((0, 0, 205)), 24, {}),   # Empire State Building
    (5.90, 7.50, 300, 300, "P", E + Vector((-55, -75, 3)), E + Vector((-55, -75, 8)), E + Vector((-10, -10, 120)), E + Vector((0, 0, 330)), 14, {}),  # Fassade hoch
    (7.50, 10.00, -1.2, 1.6, "P", LOB + Vector((12.8, -1.9, 1.0)), LOB + Vector((13.6, -1.8, 1.15)), "B", "B", 22, {}),  # Lobby-Start
    (10.00, 13.10, tsp(Fz, -.1), tsp(Fz, 4.3), "R+", (-1.35, -.38, .45), (-1.2, -.36, .5), "B", "B", 20, {}),        # zwei Stufen + Gelaender
    (13.10, 15.60, tsp(Fg, -.1), tsp(Fg, 4.1), "R+", (.95, -.12, .45), (.85, -.1, .42), "KO", "KO", 42, {}),          # Gesicht
    (15.60, 16.50, tsp(55, 11.3), tsp(55, 13.4), "S", (1.3, -.75, GH + 1.3), (1.3, -.75, GH + 1.35), (-1.28, 0, GH + 1.2), (-1.28, 0, GH + 1.2), 18, {"dF": 0}),
    (16.50, 17.40, tsp(66, 11.3), tsp(66, 13.4), "S", (1.3, -.75, GH + 1.3), (1.3, -.75, GH + 1.35), (-1.28, 0, GH + 1.2), (-1.28, 0, GH + 1.2), 18, {"dF": 0}),
    (17.40, 18.40, tsp(77, 11.3), tsp(77, 13.4), "S", (1.3, -.75, GH + 1.3), (1.3, -.75, GH + 1.35), (-1.28, 0, GH + 1.2), (-1.28, 0, GH + 1.2), 18, {"dF": 0}),
    (18.40, 20.50, 569.9, 572.0, "P", TUER_POS + Vector((-6.5, -1.5, 1.3)), TUER_POS + Vector((-6.3, -1.4, 1.3)), TUER_POS + Vector((-.5, 0, 1.2)), TUER_POS + Vector((-1.8, 0, 1.2)), 24, {}),  # Tuer geht auf
    (20.50, 22.40, 572.15, 573.45, "P", ZIEL_POS + Vector((-2.5, 1.5, 1.0)), ZIEL_POS + Vector((-2.4, 1.4, 1.05)), "B", "B", 26, {}),       # Ziel 9:33
    (22.40, 26.60, 573.6, 577.8, "B+", Vector((-1.6, 1.2, -.2)), Vector((-1.3, 2.4, .5)), "B", "B", 22, {}),        # Jubel mit Skyline
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
    o = lerpv(s[5], s[6], k)
    if s[4] == "R+":
        pos = bk + fw * o[0] + links(fw) * o[1] + Vector((0, 0, o[2]))
    elif s[4] == "B+":
        pos = bk + Vector(o)
    elif s[4] == "S":
        base = Vector((0, 0, GH * (floor_von(s[2]) + s[10].get("dF", 0))))
        pos = base + Vector(o)
    else:
        pos = Vector(o)
    if s[7] == "B":
        ziel = bk
    elif s[7] == "KO":
        ziel = kopf()
    elif s[7] == "FU":
        ziel = fuesse()
    elif s[4] == "S":
        ziel = base + Vector(lerpv(s[7], s[8], k))
    else:
        ziel = lerpv(s[7], s[8], k)
    cam.location = pos; d = ziel - pos; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = s[9]; cam.data.dof.focus_distance = d.length; cam.data.dof.aperture_fstop = 2.8 if d.length < 6 else 11
    zit = .004
    cam.location += Vector((zit * math.sin(t * 7.3), zit * math.cos(t * 5.1), zit * math.sin(t * 9.7)))


os.makedirs(A.ordner, exist_ok=True)
N = int(round(D * A.fps))
liste = [int(round(float(x) * A.fps)) for x in A.nur.split(",")] if A.nur else list(range(A.start, N))
for f in liste:
    pfad = os.path.join(A.ordner, f"treppe_{f:04d}.png")
    if os.path.exists(pfad) and not A.nur:
        continue
    zustand(f / A.fps); bpy.context.view_layer.update(); zustand(f / A.fps)
    sc.render.filepath = pfad
    print("CAM", f, tuple(round(c, 2) for c in cam.location), tuple(round(c, 2) for c in becken()), flush=True)
    bpy.ops.render.render(write_still=True); print("FERTIG", pfad, flush=True)
