"""Geschwindigkeitsski 255,5 km/h (Simon Billy, Vars/Chabrieres, 22.3.2023, GWR). Realistisch, natuerliche Haltung.
python3 speed3d.py <ordner> [--nur t1,t2] [--start i] [--samples n]"""
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
# ======================================================================  Speedskifahrer (zuerst): Latexanzug, Aero-Helm
import mensch_echt as ME
LOGO = ME.logo_bild(os.path.join(HIER, "_logo_norda.png"), "NORDA", farbe=(1, 1, 1))
BIB = ME.logo_bild(os.path.join(HIER, "_bib_sk.png"), "3", farbe=(.05, .05, .05), symbol=False, hintergrund=(.97, .97, .95), num=True, unterzeile="VARS", breite=512, hoehe=256)
PC = ME.mensch("billy", 23, 1.0, .35, .7, .22, haut="caucasian", haare="short02", braue="eyebrow001", haarfarbe="3a2a1e", schuhe=None)
for o in PC.stiefel:
    o.hide_render = False          # Skischuhe (Stiefel-Huelle) bleiben sichtbar
ME.trikot(PC, "lang", "tights", "1d4fd8", "1d4fd8", brust=BIB, brust_mass=(.16, .11), bein=LOGO, rau=.18)
for o in PC.huellen:
    if "versatz" in o.modifiers:
        o.modifiers["versatz"].strength = .009
    for md in o.modifiers:
        if md.type == "SUBSURF":
            md.render_levels = 2
hoehe = max(v.z for v in PC.EV); PC.SK = 1.82 / hoehe; PC.rig.scale = (PC.SK,) * 3
PC.PEL = PC.rig.data.bones["upperleg01.L"].head_local.copy(); PC.PEL.x = 0
bpy.context.view_layer.update()
kopf_b = PC.rig.data.bones["head"]
kh = PC.rig.matrix_world @ kopf_b.head_local; kt = PC.rig.matrix_world @ kopf_b.tail_local
kz = kh + (kt - kh) * .55
# Aero-Helm: tropfenfoermig nach hinten verlaengert, dunkles Visier vorne
bm = bmesh.new()
bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=20, radius=1)
for v in bm.verts:
    y = v.co.y
    if y > 0:
        v.co.y = y * (1 + .75 * y)          # Schweif nach hinten
        v.co.z *= (1 - .3 * y * y)
me_h = bpy.data.meshes.new("aerohelm"); bm.to_mesh(me_h); bm.free()
helm = bpy.data.objects.new("aerohelm", me_h); sc.collection.objects.link(helm)
helm.location = kz + Vector((0, .02, .025)); helm.scale = (.122, .13, .128)
helm.data.materials.append(mat("helm", "d91e2a", .15, Coat_Weight=1.0))
for p in me_h.polygons:
    p.use_smooth = True
bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1, location=kz + Vector((0, -.07, -.005)))
visier = bpy.context.object; visier.name = "visier"; visier.scale = (.105, .07, .07); visier.data.materials.append(mat("visier", "15181e", .04, metal=.8, Coat_Weight=1))
for p in visier.data.polygons:
    p.use_smooth = True
bpy.context.view_layer.update()
PI = (PC.rig.matrix_world @ kopf_b.matrix_local @ Matrix.Translation((0, kopf_b.length, 0))).inverted()
for o in (helm, visier):
    o.parent = PC.rig; o.parent_type = "BONE"; o.parent_bone = "head"; o.matrix_parent_inverse = PI
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
bpy.ops.object.light_add(type="SUN", rotation=(math.radians(50), 0, math.radians(-120))); sonne = bpy.context.object
sonne.data.energy = 4.0; sonne.data.angle = math.radians(1.0); sonne.data.color = (1, .97, .92)
sc.view_settings.exposure = -.35
STAHL = pbr("stahl", "Metal012", 6, rau_mul=.6, rau_add=.15, metal=1.0)


def sstep(a, b, x):
    t = min(1, max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t)


# ======================================================================  Pistenprofil: Winkel ueber x, Hoehe, Bogenlaenge
def winkel(x):
    if x < 40:
        a = 44
    elif x < 130:
        a = 44 - 11 * sstep(40, 130, x)
    elif x < 460:
        a = 33 - 6 * sstep(130, 460, x)
    elif x < 640:
        a = 27 - 7 * sstep(460, 640, x)
    elif x < 780:
        a = 20 - 20 * sstep(640, 780, x)
    else:
        a = -6 * sstep(780, 900, x)
    return math.radians(a)


DX = .5
XS = [i * DX for i in range(int(1100 / DX) + 1)]
ZS = [0.0]; SS = [0.0]
for i in range(1, len(XS)):
    a = winkel(XS[i] - DX / 2)
    ZS.append(ZS[-1] - math.tan(a) * DX); SS.append(SS[-1] + DX / math.cos(a))
Z0 = -min(ZS) + 0.0
ZS = [z + 0 for z in ZS]


def z_kurs(x):
    if x <= 0:
        return ZS[0] + math.tan(winkel(0)) * (-x) * .8
    i = min(len(XS) - 2, int(x / DX)); f = (x - XS[i]) / DX
    return ZS[i] * (1 - f) + ZS[i + 1] * f


def x_von_s(s):
    lo, hi = 0, len(SS) - 1
    while hi - lo > 1:
        m = (lo + hi) // 2
        if SS[m] < s:
            lo = m
        else:
            hi = m
    f = (s - SS[lo]) / max(1e-6, SS[hi] - SS[lo])
    return XS[lo] + f * DX


def kurs(s):
    """Punkt, Laufrichtung, Normale der Piste bei Bogenlaenge s"""
    x = x_von_s(max(0.0, s)) if s >= 0 else s * math.cos(winkel(0))
    p = Vector((x, 0, z_kurs(x)))
    a = winkel(max(0.0, x))
    fw = Vector((math.cos(a), 0, -math.sin(a))); nr = Vector((math.sin(a), 0, math.cos(a)))
    return p, fw, nr


S_FALLE = 575.0                   # Lichtschranke (Speed trap)

# ======================================================================  Gelaende: Couloir mit Graten, Berge rundherum
_rf = random.Random(77)
OKT = [(_rf.uniform(0, 6.3), math.cos(a_), math.sin(a_), 2.0 ** k) for k in range(7) for a_ in (_rf.uniform(0, 6.3),)]


def fbm(x, y, amp):
    z = 0.0
    for ph, cx, sy, fr in OKT:
        u = (x * cx + y * sy) * fr / 60.0 + ph
        z += amp / fr * (1 - abs(math.sin(u)))
    return z - amp * .9


def gelaende(x, y):
    zc = z_kurs(min(max(x, -150), 1100))
    ay = abs(y)
    breite = 30 + 15 * sstep(500, 800, x)
    grat = 55 * sstep(breite, breite + 45, ay) + 25 * sstep(breite + 45, breite + 140, ay)
    rau = fbm(x, y, 9.0) * sstep(breite - 4, breite + 25, ay) + .25 * fbm(x * 3, y * 3, 2.0)
    hinten = 60 * sstep(0, -120, x)
    return zc + grat + rau + hinten


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


def schnee_fels_mat(name, schnee_skala=.3):
    m = pbr(name, "Snow006", schnee_skala, tint="eef3fa", normal=.6)
    nt_ = m.node_tree; n = nt_.nodes; l = nt_.links; b = n["Principled BSDF"]
    basis = b.inputs["Base Color"].links[0].from_socket
    geo = n.new("ShaderNodeNewGeometry"); sp = n.new("ShaderNodeSeparateXYZ"); l.new(geo.outputs["Normal"], sp.inputs[0])
    st = n.new("ShaderNodeMapRange"); st.inputs[1].default_value = .55; st.inputs[2].default_value = .7; l.new(sp.outputs["Z"], st.inputs[0])
    no = n.new("ShaderNodeTexNoise"); no.inputs["Scale"].default_value = .08; no.inputs["Detail"].default_value = 10; l.new(geo.outputs["Position"], no.inputs["Vector"])
    fels = n.new("ShaderNodeMix"); fels.data_type = "RGBA"; l.new(no.outputs["Fac"], fels.inputs[0])
    fels.inputs[6].default_value = (*hexf("3a3632"), 1); fels.inputs[7].default_value = (*hexf("5f5a53"), 1)
    mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; l.new(st.outputs[0], mx.inputs[0]); l.new(fels.outputs[2], mx.inputs[6]); l.new(basis, mx.inputs[7])
    l.new(mx.outputs[2], b.inputs["Base Color"])
    b.inputs["Subsurface Weight"].default_value = .1
    return m


SCHNEE = schnee_fels_mat("schnee_fels")
hoehenfeld("couloir", -160, 1100, -260, 260, 3.0, gelaende, SCHNEE)


def berge(x, y):
    d = math.hypot((x - 450) / 1.3, y)
    base = z_kurs(min(max(x, -150), 1100)) if -150 < x < 1100 and abs(y) < 260 else -300
    h = 300 * sstep(600, 1800, d) + 380 * (math.sin(x / 310) * math.sin(y / 270) + 1) * sstep(800, 2200, d)
    if -150 < x < 1100 and abs(y) < 260:
        return base - 60
    return -350 + h + fbm(x / 6, y / 6, 160)


hoehenfeld("berge", -3200, 4000, -3600, 3600, 60.0, berge, schnee_fels_mat("berge_m", .05))
# Talboden weit unten
box("tal", (20000, 20000, .5), (450, 0, -420), mat("tal", "dfe6ee", .6), 0)
# Lärchen/Tannen im Tal und an den Hängen unten (rund)
BW = Sammler(); rb = random.Random(4)
NADEL = [mat("nadel%d" % i, f, .8) for i, f in enumerate(("2a3a26", "34472c", "223020"))]; STAMM = mat("stamm", "3a2a1e", .9)
for i in range(500):
    x = rb.uniform(600, 1100); y = rb.choice((-1, 1)) * rb.uniform(70, 260)
    z = gelaende(x, y)
    h = rb.uniform(6, 13)
    BW.zyl(.18, h * .3, (x, y, z + h * .15), STAMM, v=6)
    for k in range(3):
        BW.kugel(h * (.22 - .05 * k), (x, y, z + h * (.35 + .22 * k)), rb.choice(NADEL), skala=(1, 1, 1.5), sub=1)
BW.fertig("baeume")

# ======================================================================  Pistenausstattung: Markierungen, Netze, Lichtschranke, Anzeigetafel, Zuschauer
PM = Sammler()
BLAU = mat("farbspur", "1f4fbf", .9); ZWEIG = mat("tannenzweig", "2b4a2a", .9); NETZ = mat("netz", "ff6a00", .7)
s = 0.0
while s < 900:
    p, fw, nr = kurs(s)
    for sy in (-1, 1):
        q = p + Vector((0, sy * 17, 0)); q.z = gelaende(q.x, q.y) + .03
        PM.box((2.0, .35, .02), q, BLAU, rot=(0, math.atan2(-fw.z, fw.x), 0))
        if int(s) % 20 == 0:
            r = p + Vector((0, sy * 22, 0)); r.z = gelaende(r.x, r.y)
            PM.kugel(.35, r + Vector((0, 0, .3)), ZWEIG, skala=(1, 1, 1.4), sub=1)
    s += 2.0
# Querlinie an der Lichtschranke
pt, fwt, nrt = kurs(S_FALLE)
PM.box((.4, 34, .02), pt + Vector((0, 0, .03)), mat("rot_linie", "d01818", .8), rot=(0, math.atan2(fwt.z, fwt.x) * -1, 0))
# Fangnetze unten
for x in range(600, 900, 3):
    for sy in (-1, 1):
        y = sy * (28 + 15 * sstep(500, 800, x)); z = gelaende(x, y)
        PM.box((3.0, .04, 1.6), Vector((x + 1.5, y, z + .8)), NETZ)
        PM.zyl(.04, 1.9, Vector((x, y, z + .95)), STAHL, v=8)
PM.fertig("pistenausstattung")
# Lichtschranken-Portal + Anzeigetafel
for sy in (-1, 1):
    q = pt + Vector((0, sy * 18, 0)); q.z = gelaende(q.x, q.y)
    rohr("portal_pfosten", q, q + Vector((0, 0, 6.5)), .18, STAHL)
pp = pt + Vector((0, 0, 0)); pp.z = max(gelaende(pt.x, 18), gelaende(pt.x, -18)) + 6.5
p_ban = os.path.join(HIER, "_sk_banner.png")
ME.logo_bild(p_ban, "SPEED TRAP", farbe=(1, 1, 1), symbol=False, hintergrund=(.75, .06, .08), breite=1024, hoehe=160)
bpy.ops.mesh.primitive_plane_add(size=1, location=pp); ban = bpy.context.object; ban.scale = (36, 1.6, 1); ban.rotation_euler = (P / 2, 0, P / 2)
mb = bpy.data.materials.new("banner"); mb.use_nodes = True; ti = mb.node_tree.nodes.new("ShaderNodeTexImage"); ti.image = bpy.data.images.load(p_ban)
mb.node_tree.links.new(ti.outputs[0], mb.node_tree.nodes["Principled BSDF"].inputs["Base Color"]); ban.data.materials.append(mb)
ban.rotation_euler = (P / 2, 0, -P / 2)
TAF = pt + Vector((40, -34, 0)); TAF.z = gelaende(TAF.x, TAF.y)
p_a = os.path.join(HIER, "_sk_tafel_a.png"); p_b = os.path.join(HIER, "_sk_tafel_b.png")
ME.logo_bild(p_a, "- - -", farbe=(1, .85, .2), symbol=False, hintergrund=(.02, .02, .04), unterzeile="KM/H", breite=1024, hoehe=512)
ME.logo_bild(p_b, "255.50", farbe=(1, .85, .2), symbol=False, hintergrund=(.02, .02, .04), unterzeile="KM/H  -  WORLD RECORD", breite=1024, hoehe=512)
TAFELN = []
for p_img in (p_a, p_b):
    bpy.ops.mesh.primitive_plane_add(size=1, location=TAF + Vector((-.48 * .5, .88 * .5, 7))); t_ = bpy.context.object; t_.scale = (10, 5, 1); t_.rotation_euler = (P / 2, 0, P + .5)
    m_ = bpy.data.materials.new("tafel"); m_.use_nodes = True; ti = m_.node_tree.nodes.new("ShaderNodeTexImage"); ti.image = bpy.data.images.load(p_img)
    bsdf = m_.node_tree.nodes["Principled BSDF"]; m_.node_tree.links.new(ti.outputs[0], bsdf.inputs["Emission Color"]); bsdf.inputs["Emission Strength"].default_value = 3.0
    bsdf.inputs["Base Color"].default_value = (0, 0, 0, 1); t_.data.materials.append(m_); TAFELN.append(t_)
box("tafel_rahmen", (10.6, .5, 5.6), TAF + Vector((0, -.2, 7)), mat("tafelrahmen", "15161a", .5), .05, rot=(0, 0, .5))
for sx in (-1, 1):
    rohr("tafel_bein", TAF + Vector((sx * 3.5, .7, -1)), TAF + Vector((sx * 3.5, .7, 4.3)), .15, STAHL)
# Zuschauer im Auslauf (gebacken), hinter den Netzen
rz = random.Random(19); PUBLIKUM = []
for i in range(180):
    x = rz.uniform(650, 860); sy = rz.choice((-1, 1))
    y = sy * (31 + 15 * sstep(500, 800, x) + rz.uniform(.5, 6))
    z = gelaende(x, y)
    o = bpy.data.objects.new("zs_%d" % i, rz.choice(ZUSCH_ME)); sc.collection.objects.link(o)
    o.location = (x, y, z); o.rotation_euler = (0, 0, (P if sy < 0 else 0) + rz.uniform(-.5, .5))
    PUBLIKUM.append((o, z, rz.uniform(0, 6)))
# Starthaus oben
p0, fw0, nr0 = kurs(-4)
box("starthaus", (3, 4, 2.8), p0 + Vector((-3.5, 0, 1.0)), mat("starthaus", "c8ccd2", .5), .05)
box("startdach", (3.6, 4.6, .3), p0 + Vector((-3.5, 0, 2.5)), mat("startdach", "d01818", .5), .05)

# ======================================================================  Skier und Stoecke (bmesh, keine duennen Bevel-Boxen)
SKI_M = mat("ski", "e8e8e8", .25, Coat_Weight=.8); SKI_K = mat("ski_kante", "d01818", .3)
SKIS = []
for sd in ("L", "R"):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1, matrix=Matrix.Diagonal((2.4, .095, .02, 1)))
    for v in bm.verts:                          # Schaufel vorne hoch
        if v.co.x > 1.0:
            v.co.z += .12 * ((v.co.x - 1.0) / .2) ** 2
    me_ = bpy.data.meshes.new("ski_" + sd); bm.to_mesh(me_); bm.free(); me_.materials.append(SKI_M)
    o = bpy.data.objects.new("ski_" + sd, me_); sc.collection.objects.link(o); o.rotation_mode = "QUATERNION"
    SKIS.append(o)
STOECKE = []
for sd in ("L", "R"):
    bm = bmesh.new()
    pts = [Vector((0, 0, 0)), Vector((-.25, 0, -.12)), Vector((-.6, 0, -.2)), Vector((-1.1, 0, -.18))]     # gebogener Rennstock
    for a, b in zip(pts, pts[1:]):
        d = b - a
        bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=.012, radius2=.012, depth=d.length,
                              matrix=Matrix.Translation((a + b) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4())
    me_ = bpy.data.meshes.new("stock_" + sd); bm.to_mesh(me_); bm.free(); me_.materials.append(mat("stock", "222428", .3, metal=.5))
    o = bpy.data.objects.new("stock_" + sd, me_); sc.collection.objects.link(o); o.rotation_mode = "QUATERNION"
    STOECKE.append(o)
# Schneestaub hinter den Skiern
STAUB_M = mat("schneestaub", "f4f7fb", .9, Emission_Color=(1, 1, 1, 1), Emission_Strength=.15)
STAUB = []
for i in range(40):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, location=(0, 0, -900)); o = bpy.context.object; o.data.materials.append(STAUB_M)
    for p in o.data.polygons:
        p.use_smooth = True
    STAUB.append(o)
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


# ======================================================================  Fahrt: Geschwindigkeit und Weg
VMAX = 73.59; TAU = 3.3; T_BREMS = 12.0; A_BREMS = 6.2
S_BREMS = VMAX * (T_BREMS - TAU * (1 - math.exp(-T_BREMS / TAU)))
V_BREMS = VMAX * (1 - math.exp(-T_BREMS / TAU))
T_STOP = T_BREMS + V_BREMS / A_BREMS


def weg(t):
    if t <= 0:
        return 0.0
    if t < T_BREMS:
        return VMAX * (t - TAU * (1 - math.exp(-t / TAU)))
    tb = min(t, T_STOP) - T_BREMS
    return S_BREMS + V_BREMS * tb - .5 * A_BREMS * tb * tb


def tempo(t):
    if t <= 0:
        return 0.0
    if t < T_BREMS:
        return VMAX * (1 - math.exp(-t / TAU))
    return max(0.0, V_BREMS - A_BREMS * (t - T_BREMS))


T_FALLE = None
lo, hi = 0.0, 20.0
for _ in range(50):
    m = (lo + hi) / 2
    if weg(m) < S_FALLE:
        lo = m
    else:
        hi = m
T_FALLE = lo
print("Lichtschranke bei t =", round(T_FALLE, 2), "v =", round(tempo(T_FALLE) * 3.6, 1), "km/h; Stopp bei", round(T_STOP, 1), "s, s =", round(weg(T_STOP)))


def figur(ts):
    KF.zuruecksetzen()
    for c in KF.IK.values():
        c.influence = 1.0
    s = weg(ts)
    p, fw, nr = kurs(s - (0 if ts > 0 else 0))
    if ts <= 0:
        p, fw, nr = kurs(0.0)
    le = nr.cross(fw).normalized()             # links (quer zur Piste)
    # Haltung: 0 = aufrecht, 1 = Ei (Hocke)
    hocke = ease(seg(ts, .6, 1.6)) * (1 - ease(seg(ts, T_BREMS + .2, T_BREMS + 1.6)))
    jubel = ease(seg(ts, T_STOP + .4, T_STOP + 1.2))
    schub = math.sin(P * seg(ts, -.2, .9)) if ts < .9 else 0.0      # Abstossen mit den Stoecken
    bremse = ease(seg(ts, T_BREMS + .8, T_BREMS + 1.8)) * (1 - jubel)
    lean = .15 + 1.15 * hocke + .25 * schub
    pel_h = .92 - .4 * hocke
    pel = p + nr * pel_h - fw * (.1 + .12 * hocke)
    H = nr * math.cos(lean) + fw * math.sin(lean); Fc = fw * math.cos(lean) - nr * math.sin(lean)
    rq = rig_mat(H, Fc).to_quaternion()
    KF.rig.rotation_mode = "QUATERNION"; KF.rig.rotation_quaternion = rq
    KF.rig.location = pel - rq.to_matrix() @ (KF.PEL * KF.SK)
    vib = .004 * math.sin(ts * 61) * seg(ts, 1, 3)
    for sd, sg in (("L", 1), ("R", -1)):
        fuss = p + le * (sg * .13) + nr * (.1 + vib) + fw * (.05 * hocke)
        KF.Z["fuss_" + sd].location = fuss
        KF.Z["knie_" + sd].location = pel + fw * 2.0 + le * (sg * .25) + nr * .2
        # Ski unter dem Fuss
        ski = SKIS[0 if sd == "L" else 1]
        ski.location = p + le * (sg * .13) + nr * .012 + fw * .15
        ski.rotation_quaternion = Matrix((fw, le, nr)).transposed().to_quaternion()
    sh_c = pel + H * .5
    # Arme: Ei -> Haende zusammen vor dem Gesicht; Start -> Stockschub; Bremsen -> Arme seitlich (Luftbremse)
    for sd, sg in (("L", 1), ("R", -1)):
        ei = sh_c + H * .08 + fw * .16 + le * (sg * .08) - nr * .14
        stand = sh_c - H * .4 + le * (sg * .28) + fw * (.12 - .45 * schub)
        breit = sh_c + le * (sg * .7) - H * .15 + fw * .05
        hand = stand.lerp(ei, hocke).lerp(breit, bremse)
        KF.Z["hand_" + sd].location = hand
        KF.Z["ell_" + sd].location = pel + le * (sg * .7) - nr * .6 + fw * .2 if hocke > .5 else pel - fw * 1.0 + le * (sg * .5) + nr * .3
        # Stock: Griff in der Hand, Spitze nach hinten (im Ei unter dem Arm)
        st = STOECKE[0 if sd == "L" else 1]
        richt = (-fw * .9 - nr * .3 + le * (sg * .15)).normalized() if hocke > .3 or bremse > .3 else (-nr * .85 - fw * .3 * (1 - schub) - fw * .6 * schub + le * (sg * .1)).normalized()
        st.location = hand
        q = richt.to_track_quat("-X", "Z")
        st.rotation_quaternion = q
    if jubel > 0:
        KF.IK["hand_L"].influence = 1 - jubel; KF.IK["hand_R"].influence = 1 - jubel
        KF.dreh("upperarm01.L", z=-.72 + 3.0 * jubel, x=.2 * jubel); KF.dreh("upperarm01.R", z=.72 - 3.0 * jubel, x=.2 * jubel)
        KF.dreh("lowerarm01.L", x=-.4 * jubel); KF.dreh("lowerarm01.R", x=-.4 * jubel)
        for sd, st in zip(("L", "R"), STOECKE):
            st.location = (0, 0, -900)
    KF.dreh("neck01", x=-.75 * hocke - .2 * lean * (1 - hocke)); KF.dreh("head", x=-.45 * hocke)
    for sd in ("L", "R"):
        for ff in range(2, 6):
            for g in (1, 2, 3):
                KF.dreh(f"finger{ff}-{g}.{sd}", x=(1.3 if jubel < .5 else .3))
        for g in (2, 3):
            KF.dreh(f"finger1-{g}.{sd}", x=.6)
    # Schneestaub hinter den Skiern ab ~150 km/h
    v = tempo(ts)
    st_ = 0.0
    for i, o in enumerate(STAUB):
        if st_ > 0 and ts < T_STOP:
            k = (i * .37 + ts * 3.1) % 1.0
            q_ = p - fw * (1.2 + 7 * k) + le * ((i % 5 - 2) * .12 * (1 + 2 * k)) + nr * (.03 + .5 * k * k)
            o.location = q_; r = (.03 + .16 * k) * st_; o.scale = (r * 2.2, r, r * .7)
        else:
            o.location = (0, 0, -900)
    # Anzeigetafel nach der Lichtschranke
    gemessen = ts > T_FALLE + .35
    TAFELN[0].hide_render = gemessen; TAFELN[1].hide_render = not gemessen
    for o, z0, ph_ in PUBLIKUM:
        o.location.z = z0 + (.09 * max(0, math.sin(ts * 7 + ph_)) if gemessen else 0.0)
    bpy.context.view_layer.update()
    return p, fw, nr


def becken():
    nk = KF.rig.matrix_world @ KF.rig.pose.bones["neck01"].head
    return (KF.rig.matrix_world @ KF.PEL) * .55 + nk * .45


def kopf():
    return KF.rig.matrix_world @ KF.rig.pose.bones["head"].head + Vector((0, 0, .05))


def fuesse():
    return (KF.Z["fuss_L"].matrix_world.translation + KF.Z["fuss_R"].matrix_world.translation) / 2


# ======================================================================  Kamera
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam
cam.data.clip_start = .03; cam.data.clip_end = 12000; cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
cam.data.dof.use_dof = True
pt_f, fw_f, nr_f = kurs(S_FALLE)
SZ = [
    # t0, t1, ts0, ts1, modus, pos0, pos1, ziel0, ziel1, brennweite   (S+ = im Pistensystem: vor, links, Normale)
    (0.00, 1.50, 10.55, 10.85, "S+", (1.6, -2.4, .35), (1.2, -2.4, .35), "B", "B", 22),                          # Aufhaenger: volles Tempo
    (1.50, 2.60, 3.0, 4.1, "S+", (-6.5, -1.2, 3.0), (-6.0, -1.0, 2.8), (30, 0, -8), (30, 0, -8), 20),            # gerade runter
    (2.60, 3.70, 10.4, 10.95, "P", pt_f + Vector((14, 7, 1.0)), pt_f + Vector((14, 7, 1.0)), "B", "B", 40),       # wie schnell? frontal
    (3.70, 5.90, 0.0, 0.0, "P", Vector((1350, -950, 420)), Vector((1250, -880, 400)), Vector((250, 0, -120)), Vector((250, 0, -120)), 26),  # Vars aus der Luft
    (5.90, 8.20, -1.4, .9, "P", kurs(4)[0] + Vector((0, -5.5, 2.2)), kurs(4)[0] + Vector((0, -5.0, 2.2)), "B", "B", 26),   # Abstossen am Start
    (8.20, 10.40, .8, 3.2, "P", Vector((30, -26, z_kurs(30) + 6)), Vector((31, -26, z_kurs(31) + 6)), "B", "B", 60),  # 45 Grad von der Seite
    (10.40, 12.40, 4.0, 4.5, "S+", (1.3, -.6, .55), (1.25, -.55, .5), "KO", "KO", 34),                           # Anzug + Aero-Helm
    (12.40, 14.20, 4.5, 5.0, "S+", (.6, -2.4, .45), (.3, -2.4, .45), "FU", "FU", 18),                            # Skier 2,4 m
    (14.20, 15.40, 5.0, 5.45, "S+", (0, -2.6, .5), (0, -2.6, .5), "B", "B", 26),                                 # Ei
    (15.40, 18.40, 3.2, 6.2, "S+", (5.0, 1.4, 1.0), (7.0, 1.8, 1.4), "B", "B", 28),                              # 200 km/h in < 6 s
    (18.40, 20.40, 7.6, 8.6, "P", kurs(weg(8.1))[0] + Vector((0, -6, .6)), kurs(weg(8.1))[0] + Vector((0, -6, .6)), "B", "B", 24),  # rauscht vorbei
    (20.40, 22.00, 9.8, 10.7, "P", pt_f + Vector((-6, -12, 4)), pt_f + Vector((-6, -12, 4)), "B", "B", 55),    # Lichtschranke
    (22.00, 24.40, 10.75, 12.0, "P", TAF + Vector((20, 18, 3.0)), TAF + Vector((19, 17, 3.0)), TAF + Vector((0, 0, 6)), TAF + Vector((0, 0, 6)), 30),  # Tafel 255.50
    (24.40, 27.30, T_STOP - .6, T_STOP + 2.3, "S+", (5.5, -3.0, 2.6), (4.2, -4.3, 2.9), "B", "B", 26),           # Jubel im Auslauf
    (27.30, 28.00, 10.41, 10.55, "S+", (1.6, -2.4, .35), (1.6, -2.4, .35), "B", "B", 22),                        # Loop: fuehrt nahtlos in den Anfang
]


def zustand(t):
    for s in SZ:
        if s[0] <= t < s[1]:
            break
    k = (t - s[0]) / (s[1] - s[0])
    ts = s[2] + (s[3] - s[2]) * k
    k = ease(k) * .7 + k * .3
    p, fw, nr = figur(ts)
    le = nr.cross(fw).normalized()
    bk = becken()
    o = Vector(lerpv(s[5], s[6], k))
    if s[4] == "S+":
        pos = p + fw * o.x + le * o.y + nr * o.z
        ziel = {"B": bk, "KO": kopf(), "FU": fuesse()}.get(s[7]) if isinstance(s[7], str) else p + fw * lerpv(s[7], s[8], k)[0] + le * lerpv(s[7], s[8], k)[1] + nr * lerpv(s[7], s[8], k)[2]
    else:
        pos = o
        ziel = bk if s[7] == "B" else Vector(lerpv(s[7], s[8], k))
    cam.location = pos; d = ziel - pos; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = s[9]; cam.data.dof.focus_distance = d.length; cam.data.dof.aperture_fstop = 2.8 if d.length < 6 else 11
    zit = .006 + .02 * seg(tempo(ts), 40, 70) * (1 if s[4] == "S+" else 0)
    cam.location += Vector((zit * math.sin(t * 37.3), zit * math.cos(t * 41.1), zit * math.sin(t * 29.7)))


os.makedirs(A.ordner, exist_ok=True)
N = int(round(D * A.fps))
liste = [int(round(float(x) * A.fps)) for x in A.nur.split(",")] if A.nur else list(range(A.start, N))
for f in liste:
    pfad = os.path.join(A.ordner, f"speed_{f:04d}.png")
    if os.path.exists(pfad) and not A.nur:
        continue
    zustand(f / A.fps); bpy.context.view_layer.update(); zustand(f / A.fps)
    sc.render.filepath = pfad
    print("CAM", f, tuple(round(c, 1) for c in cam.location), flush=True)
    bpy.ops.render.render(write_still=True); print("FERTIG", pfad, flush=True)
