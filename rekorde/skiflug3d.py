"""Skiflug 254,5 m (Domen Prevc, Planica 30.3.2025, GWR/FIS). Realistischer Stil, echte Figur (mensch_echt).
python3 skiflug3d.py <ordner> [--nur t1,t2] [--start i] [--samples n]"""
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
D = 27.4
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


# ======================================================================  Springer (echter Mensch) - zuerst, Materialien danach
import mensch_echt as ME
LOGO = ME.logo_bild(os.path.join(HIER, "_logo_norda.png"), "NORDA", farbe=(1, 1, 1))
BIB = ME.logo_bild(os.path.join(HIER, "_bib_sf.png"), "7", farbe=(.05, .05, .05), symbol=False, hintergrund=(.97, .97, .95), num=True, unterzeile="FLY")
S = ME.mensch("prevc", 41, 1.0, .3, .55, .2, haut="caucasian", haare="short02", braue="eyebrow001", haarfarbe="3a2a1c")
ME.trikot(S, "lang", "tights", "1d3f9a", "1d3f9a", brust=BIB, brust_mass=(.16, .11), bein=LOGO)
for o in S.huellen:
    if "versatz" in o.modifiers:
        o.modifiers["versatz"].strength = .017 if o.name.endswith("_hemd") else .010
    for md in o.modifiers:
        if md.type == "SUBSURF":
            md.render_levels = 2
hoehe = max(v.z for v in S.EV); S.SK = 1.80 / hoehe; S.rig.scale = (S.SK,) * 3
S.PEL = S.rig.data.bones["upperleg01.L"].head_local.copy(); S.PEL.x = 0
print("ok mensch")

# ======================================================================  Materialien
STAHL = pbr("stahl", "Metal012", 6, rau_mul=.6, rau_add=.15, metal=1.0)
BETON = pbr("beton", "Concrete034", .2, tint="8a8a8e")
HOLZ = pbr("holz", "WoodFloor041", .5)
FELS = pbr("fels", "Rock035", .05, tint="7a7570")
SCHWARZ = mat("schwarzlack", "0d0d0f", .4, Coat_Weight=.3)
WEISSLACK = mat("weisslack", "eef0f2", .35, Coat_Weight=.4)


def schnee_mat(name, skala=.35, linien=False):
    """Schnee: Foto-Textur (ambientCG Snow006) + leichtes Glitzern; optional blaue Weitenlinien alle 10 m (entlang Bogenlaenge)."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; n = nt.nodes; l = nt.links; b = n["Principled BSDF"]
    pfad = os.path.join(ASSET, "Snow006", "Snow006_1K-JPG", "Snow006_1K-JPG")
    tc = n.new("ShaderNodeTexCoord"); mp = n.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (skala,) * 3
    l.new(tc.outputs["Object"], mp.inputs[0])
    c = n.new("ShaderNodeTexImage"); c.image = bpy.data.images.load(pfad + "_Color.jpg", check_existing=True); c.projection = "BOX"; c.projection_blend = .3
    l.new(mp.outputs[0], c.inputs[0])
    nm = n.new("ShaderNodeTexImage"); nm.image = bpy.data.images.load(pfad + "_NormalGL.jpg", check_existing=True); nm.image.colorspace_settings.name = "Non-Color"
    nm.projection = "BOX"; l.new(mp.outputs[0], nm.inputs[0])
    nmap = n.new("ShaderNodeNormalMap"); nmap.inputs["Strength"].default_value = .5; l.new(nm.outputs[0], nmap.inputs["Color"])
    hell = n.new("ShaderNodeMix"); hell.data_type = "RGBA"; hell.blend_type = "MULTIPLY"; hell.inputs[0].default_value = 1
    l.new(c.outputs[0], hell.inputs[6]); hell.inputs[7].default_value = (1.05, 1.07, 1.12, 1)
    farbe = hell.outputs[2]
    if linien:   # Attribut "bogen" (Bogenlaenge ab Schanzentisch) -> blaue Linien alle 10 m ab 120 m
        at = n.new("ShaderNodeAttribute"); at.attribute_name = "bogen"
        pp = n.new("ShaderNodeMath"); pp.operation = "PINGPONG"; pp.inputs[1].default_value = 5.0; l.new(at.outputs["Fac"], pp.inputs[0])
        lt = n.new("ShaderNodeMath"); lt.operation = "LESS_THAN"; lt.inputs[1].default_value = .09; l.new(pp.outputs[0], lt.inputs[0])
        gt = n.new("ShaderNodeMath"); gt.operation = "GREATER_THAN"; gt.inputs[1].default_value = 118; l.new(at.outputs["Fac"], gt.inputs[0])
        kl = n.new("ShaderNodeMath"); kl.operation = "LESS_THAN"; kl.inputs[1].default_value = 262; l.new(at.outputs["Fac"], kl.inputs[0])
        m1 = n.new("ShaderNodeMath"); m1.operation = "MULTIPLY"; l.new(lt.outputs[0], m1.inputs[0]); l.new(gt.outputs[0], m1.inputs[1])
        m2 = n.new("ShaderNodeMath"); m2.operation = "MULTIPLY"; l.new(m1.outputs[0], m2.inputs[0]); l.new(kl.outputs[0], m2.inputs[1])
        # Laengsrand: Linie nur bis |y| < 21
        ay = n.new("ShaderNodeAttribute"); ay.attribute_name = "quer"
        ql = n.new("ShaderNodeMath"); ql.operation = "LESS_THAN"; ql.inputs[1].default_value = 21; l.new(ay.outputs["Fac"], ql.inputs[0])
        m3 = n.new("ShaderNodeMath"); m3.operation = "MULTIPLY"; l.new(m2.outputs[0], m3.inputs[0]); l.new(ql.outputs[0], m3.inputs[1])
        mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; l.new(m3.outputs[0], mx.inputs[0]); l.new(farbe, mx.inputs[6])
        mx.inputs[7].default_value = (*hexf("1f5fd0"), 1); farbe = mx.outputs[2]
    l.new(farbe, b.inputs["Base Color"]); l.new(nmap.outputs[0], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = .55; b.inputs["Specular IOR Level"].default_value = .6
    b.inputs["Subsurface Weight"].default_value = .15; b.inputs["Subsurface Radius"].default_value = (.4, .5, .7)
    return m


SCHNEE = schnee_mat("schnee", .3, linien=True)
SCHNEE_W = schnee_mat("schnee_weit", .06)
EIS = mat("eisspur", "dfe8f2", .08, Coat_Weight=.6)

w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; nt = w.node_tree
env = nt.nodes.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(os.path.join(ASSET, "schnee.hdr"))
nt.links.new(env.outputs[0], nt.nodes["Background"].inputs[0]); nt.nodes["Background"].inputs[1].default_value = 1.25
bpy.ops.object.light_add(type="SUN", rotation=(math.radians(52), 0, math.radians(-35))); sonne = bpy.context.object
sonne.data.energy = 4.0; sonne.data.angle = math.radians(1.2); sonne.data.color = (1, .96, .9)

# ======================================================================  Schanzenprofil (x = horizontal talwaerts, z = Hoehe; Schanzentisch-Kante bei 0,0,0)
TISCH_H = 3.0


def winkel_land(x):
    """Neigung des Aufsprunghangs in Grad"""
    if x < 0:
        return 8.0
    if x < 40:
        return 8 + 28 * ease(x / 40)
    if x < 165:
        return 36.0
    if x < 290:
        return 36 * (1 - ease((x - 165) / 125))
    if x < 400:
        return 0.0
    return -6 * ease((x - 400) / 40)        # Gegenhang am Ende


PROF_X, PROF_Z, PROF_S = [], [], []
_z, _s = -TISCH_H, 0.0
for i in range(0, 4601):
    x = i * .1
    PROF_X.append(x); PROF_Z.append(_z); PROF_S.append(_s)
    a = math.radians(winkel_land(x + .05)); _z -= math.tan(a) * .1; _s += .1 / math.cos(a)


def hang_z(x):
    if x <= 0:
        return -TISCH_H
    i = min(len(PROF_X) - 2, int(x / .1)); k = (x - PROF_X[i]) / .1
    return PROF_Z[i] * (1 - k) + PROF_Z[i + 1] * k


def hang_s(x):
    if x <= 0:
        return x
    i = min(len(PROF_X) - 2, int(x / .1)); k = (x - PROF_X[i]) / .1
    return PROF_S[i] * (1 - k) + PROF_S[i + 1] * k


def x_aus_s(s):
    lo, hi = 0, len(PROF_S) - 1
    while hi - lo > 1:
        mi = (lo + hi) // 2
        if PROF_S[mi] < s:
            lo = mi
        else:
            hi = mi
    k = (s - PROF_S[lo]) / max(1e-6, PROF_S[hi] - PROF_S[lo]); return PROF_X[lo] + .1 * k


def hang_pkt(s):
    x = x_aus_s(s); a = math.radians(winkel_land(x))
    p = Vector((x, 0, hang_z(x))); t = Vector((math.cos(a), 0, -math.sin(a))); nn = Vector((math.sin(a), 0, math.cos(a)))
    return p, t, nn


# Anlauf: von der Tischkante bergauf; Tisch 6 m mit 11 Grad, Radius bis 35 Grad, dann gerade
ANL_L = 92.0


def winkel_anl(s):
    """s = Strecke vor der Kante (0 an der Kante)"""
    if s < 6:
        return 11.0
    if s < 36:
        return 11 + 24 * ease((s - 6) / 30)
    return 35.0


ANL = []          # (s, Punkt, Tangente talwaerts)
_p = Vector((0, 0, 0))
for i in range(0, int(ANL_L * 10) + 41):
    s = i * .1; a = math.radians(winkel_anl(s))
    ANL.append((s, _p.copy(), Vector((math.cos(a), 0, -math.sin(a)))))
    _p = _p - Vector((math.cos(a), 0, -math.sin(a))) * .1


def anl_pkt(s):
    """Punkt auf der Anlaufspur, s Meter vor der Kante"""
    s = max(0, min(ANL_L + 3.9, s)); i = int(s * 10); k = s * 10 - i
    a, b_ = ANL[i], ANL[min(i + 1, len(ANL) - 1)]
    return a[1].lerp(b_[1], k), a[2].lerp(b_[2], k).normalized()


# ======================================================================  Gelaende (ein Gitter: Hang, Seitenwaelle, Tal, Berge)
def rausch(x, y, f, seed):
    return (math.sin(x * f + seed) * math.cos(y * f * 1.3 + seed * 2) + .5 * math.sin(x * f * 2.1 - y * f * 1.7 + seed * 3)
            + .25 * math.sin(x * f * 4.3 + y * f * 3.9 + seed))


def mitte_z(x):
    if x >= 0:
        return hang_z(x)
    # unter dem Anlauf: Hang etwas unter der Spur
    p, _ = anl_pkt(-x / math.cos(math.radians(30)) if x > -80 else -x * 1.2)
    k = ease(-x / 25)
    return p.z - TISCH_H * (1 - k) - (8 + .06 * -x) * k


def gelaende_z(x, y):
    zc = mitte_z(min(max(x, -110), 445))
    if x > 445:
        zc += (x - 445) * .25
    if x < -110:
        zc += (-110 - x) * .5
    ay = abs(y)
    breite = 24 + .06 * max(0, x - 100)
    wall = 0.0
    if ay > breite:
        d = ay - breite
        wall = 1.8 * (1 - math.exp(-d / 3)) + d * .32 + d * d * .0016
    z = zc + wall
    # Berge in der Ferne
    r = max(0, ay - 260) + max(0, -x - 260) * .8 + max(0, x - 700) * .6
    if r > 0:
        z += r * .9 + 60 * max(0, rausch(x, y, .006, 1.7)) * min(1, r / 120) + 18 * rausch(x, y, .02, 4.1) * min(1, r / 200)
    return z


def gitter(name, x0, x1, y0, y1, nx, ny, fz, material, attr=False):
    bm = bmesh.new(); vs = []
    for j in range(ny + 1):
        row = []
        y = y0 + (y1 - y0) * j / ny
        for i in range(nx + 1):
            x = x0 + (x1 - x0) * i / nx
            row.append(bm.verts.new((x, y, fz(x, y))))
        vs.append(row)
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if attr:
        ab = me.attributes.new("bogen", "FLOAT", "POINT"); aq = me.attributes.new("quer", "FLOAT", "POINT")
        ab.data.foreach_set("value", [hang_s(v.co.x) for v in me.vertices]); aq.data.foreach_set("value", [abs(v.co.y) for v in me.vertices])
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o); me.materials.append(material)
    for p in me.polygons:
        p.use_smooth = True
    return o


# Hang fein (dort fliegt die Kamera nah), Umgebung grob
hang = gitter("hang", -6, 450, -60, 60, 456, 60, gelaende_z, SCHNEE, attr=True)
# einfacher: zwei Material-Slots nach Steilheit (Fels / Schnee)
def berg_mat():
    m = bpy.data.materials.new("berg"); m.use_nodes = True; nt_ = m.node_tree; n_ = nt_.nodes; l_ = nt_.links; b_ = n_["Principled BSDF"]
    tc_ = n_.new("ShaderNodeTexCoord"); mp_ = n_.new("ShaderNodeMapping"); mp_.inputs["Scale"].default_value = (.05,) * 3; l_.new(tc_.outputs["Object"], mp_.inputs[0])
    def bild(pfad):
        t_ = n_.new("ShaderNodeTexImage"); t_.image = bpy.data.images.load(pfad, check_existing=True); t_.projection = "BOX"; t_.projection_blend = .3
        l_.new(mp_.outputs[0], t_.inputs[0]); return t_
    sn = bild(os.path.join(ASSET, "Snow006", "Snow006_1K-JPG", "Snow006_1K-JPG_Color.jpg"))
    fe = bild(os.path.join(ASSET, "Rock035", "Rock035_1K-JPG", "Rock035_1K-JPG_Color.jpg"))
    geo_ = n_.new("ShaderNodeNewGeometry"); sp_ = n_.new("ShaderNodeSeparateXYZ"); l_.new(geo_.outputs["Normal"], sp_.inputs[0])
    no_ = n_.new("ShaderNodeTexNoise"); no_.inputs["Scale"].default_value = .02; l_.new(tc_.outputs["Object"], no_.inputs[0])
    ad_ = n_.new("ShaderNodeMath"); ad_.operation = "MULTIPLY_ADD"; ad_.inputs[1].default_value = .25; l_.new(no_.outputs[0], ad_.inputs[0]); l_.new(sp_.outputs["Z"], ad_.inputs[2])
    rm_ = n_.new("ShaderNodeMapRange"); rm_.inputs[1].default_value = .68; rm_.inputs[2].default_value = .78; l_.new(ad_.outputs[0], rm_.inputs[0])
    mx_ = n_.new("ShaderNodeMix"); mx_.data_type = "RGBA"; l_.new(rm_.outputs[0], mx_.inputs[0]); l_.new(fe.outputs[0], mx_.inputs[6]); l_.new(sn.outputs[0], mx_.inputs[7])
    l_.new(mx_.outputs[2], b_.inputs["Base Color"]); b_.inputs["Roughness"].default_value = .7
    return m


weit = gitter("umgebung", -900, 1300, -1100, 1100, 300, 300, gelaende_z, berg_mat())
weit.location.z = -.35            # unter dem feinen Hang
# Loch fuer den feinen Hang nicht noetig (liegt darunter)

# ======================================================================  Anlauf-Turm, Spur, Tisch
spur_pkte = [anl_pkt(s) for s in [i * .5 for i in range(0, int((ANL_L + 3) * 2))]]
bm = bmesh.new(); ringe = []
for (p, t) in spur_pkte:
    nn = Vector((t.z * -1, 0, t.x)) if False else Vector((-t.z, 0, t.x)) * -1
    nn = Vector((math.copysign(1, 1) * -t.z, 0, t.x)) if t.x > 0 else nn
    up = Vector((-(-t.z), 0, t.x)).normalized()
    up = Vector((t.z * -1, 0, t.x)).normalized()
    if up.z < 0:
        up = -up
    q_ = []
    for (yy, zz) in ((-1.9, -.9), (-1.9, .05), (1.9, .05), (1.9, -.9)):
        q_.append(bm.verts.new(p + Vector((0, yy, 0)) + up * zz))
    ringe.append(q_)
for a, b_ in zip(ringe, ringe[1:]):
    for k in range(4):
        bm.faces.new((a[k], a[(k + 1) % 4], b_[(k + 1) % 4], b_[k]))
bm.faces.new(ringe[0][::-1]); bm.faces.new(ringe[-1])
me = bpy.data.meshes.new("anlauf"); bm.to_mesh(me); bm.free(); anl_o = bpy.data.objects.new("anlauf", me); sc.collection.objects.link(anl_o)
me.materials.append(SCHNEE_W)
for p in me.polygons:
    p.use_smooth = False
# Eisspur mit zwei Rillen + Seitenbanden (Holz, weiss gestrichen)
for yy in (-.11, .11):
    bm = bmesh.new(); r_ = []
    for (p, t) in spur_pkte:
        up = Vector((-t.z, 0, t.x)).normalized()
        if up.z < 0:
            up = -up
        r_.append([bm.verts.new(p + Vector((0, yy + d, 0)) + up * (.055 + h)) for d, h in ((-.075, 0), (-.06, -.025), (.06, -.025), (.075, 0))])
    for a, b_ in zip(r_, r_[1:]):
        for k in range(3):
            bm.faces.new((a[k], a[k + 1], b_[k + 1], b_[k]))
    me = bpy.data.meshes.new("rille"); bm.to_mesh(me); bm.free(); o = bpy.data.objects.new("rille", me); sc.collection.objects.link(o); me.materials.append(EIS)
box("eisflaeche", (1, 1, 1), (0, 0, -100), EIS, 0)   # Platzhalter (unsichtbar)
bpy.data.objects["eisflaeche"].hide_render = True
for sy in (-1, 1):
    bm = bmesh.new(); r_ = []
    for (p, t) in spur_pkte:
        up = Vector((-t.z, 0, t.x)).normalized()
        if up.z < 0:
            up = -up
        r_.append([bm.verts.new(p + Vector((0, sy * yy_, 0)) + up * zz) for yy_, zz in ((1.75, .05), (1.75, .95), (1.9, .95), (1.9, .05))])
    for a, b_ in zip(r_, r_[1:]):
        for k in range(3):
            bm.faces.new((a[k], a[k + 1], b_[k + 1], b_[k]))
    me = bpy.data.meshes.new("bande"); bm.to_mesh(me); bm.free(); o = bpy.data.objects.new("bande", me); sc.collection.objects.link(o); me.materials.append(WEISSLACK)
# Netz-/Werbebanden am Anlauf: Fantasiemarke
BAND_M = bpy.data.materials.new("bande_logo"); BAND_M.use_nodes = True; nb = BAND_M.node_tree.nodes; lb = BAND_M.node_tree.links
ti = nb.new("ShaderNodeTexImage"); ti.image = bpy.data.images.load(LOGO); ti.extension = "REPEAT"
mpb = nb.new("ShaderNodeMapping"); mpb.inputs["Scale"].default_value = (6, 1, 1); tcb = nb.new("ShaderNodeTexCoord")
lb.new(tcb.outputs["UV"], mpb.inputs[0]); lb.new(mpb.outputs[0], ti.inputs[0])
mxb = nb.new("ShaderNodeMix"); mxb.data_type = "RGBA"; mxb.inputs[6].default_value = (*hexf("1d3f9a"), 1); lb.new(ti.outputs[1], mxb.inputs[0])
lb.new(ti.outputs[0], mxb.inputs[7]); lb.new(mxb.outputs[2], nb["Principled BSDF"].inputs["Base Color"]); nb["Principled BSDF"].inputs["Roughness"].default_value = .5
# Stuetzen unter dem Anlauf (Stahlfachwerk)
for s in range(10, int(ANL_L), 8):
    p, t = anl_pkt(s)
    boden = mitte_z(p.x)
    if p.z - boden > 1.5:
        for yy in (-1.6, 1.6):
            rohr("stuetze", (p.x, yy, boden - 1), (p.x, yy, p.z - .8), .22 if s % 16 == 2 else .16, STAHL)
        rohr("quer", (p.x, -1.6, (p.z + boden) / 2), (p.x, 1.6, (p.z + boden) / 2), .08, STAHL)
        rohr("diag", (p.x, -1.6, boden), (p.x, 1.6, p.z - .8), .07, STAHL)
# Startturm mit Dach, Startbalken, Trainerturm
p_top, t_top = anl_pkt(ANL_L)
box("startturm", (7, 6, 7), (p_top.x - 3.5, 0, p_top.z + 1.6), BETON, .05)
box("turmdach", (8.4, 7.4, .35), (p_top.x - 3.0, 0, p_top.z + 5.4), SCHWARZ, .05, rot=(0, -.08, 0))
for yy in (-3.0, 3.0):
    box("turmglas", (5, .05, 2.2), (p_top.x - 3.5, yy, p_top.z + 3.2), mat("glas", "2a3a48", .05, Coat_Weight=1, Metallic=.3), .01)
GATE = []
for k, sg in enumerate((ANL_L - 1.0, ANL_L - 3.0, ANL_L - 5.0)):
    p, t = anl_pkt(sg)
    GATE.append(box("startbalken", (.12, 3.6, .08), (p.x, 0, p.z + .55), mat("balken", "d0d4d8", .4, Metallic=.6), .02))
# Schanzentisch-Kante: rote Markierung, Fotozellen
box("tischkante", (.08, 3.8, .06), (0, 0, .03), mat("rotlack", "d0141a", .35, Coat_Weight=.4), .01)
for yy in (-2.3, 2.3):
    box("fotozelle", (.15, .15, .7), (-.3, yy, .35), SCHWARZ, .02)

# ======================================================================  Weitentafeln, Linien, Zaeune, Kampfrichterturm
def zahl_mat(txt, farbe="ffffff", hg="1d3f9a"):
    pfad = os.path.join(HIER, f"_sf_tafel_{txt.replace('.', '_')}.png")
    ME.logo_bild(pfad, txt, farbe=tuple(c for c in hexf(farbe)), symbol=False, hintergrund=hexf(hg), num=True)
    m = bpy.data.materials.new("tafel_" + txt); m.use_nodes = True; nt_ = m.node_tree; ti_ = nt_.nodes.new("ShaderNodeTexImage")
    ti_.image = bpy.data.images.load(pfad); nt_.links.new(ti_.outputs[0], nt_.nodes["Principled BSDF"].inputs["Base Color"])
    nt_.nodes["Principled BSDF"].inputs["Roughness"].default_value = .45; return m


TAFELN = {}
for meter in range(120, 270, 10):
    x = x_aus_s(meter); z = hang_z(x)
    for sy in (-1, 1):
        bpy.ops.mesh.primitive_plane_add(size=1, location=(x, sy * 23.0, z + 1.1), rotation=(P / 2, 0, -sy * P / 2 + P / 2 * (1 + sy) * 0))
        o = bpy.context.object; o.scale = (2.2, 1.1, 1); o.rotation_euler = (P / 2, 0, P / 2 if sy < 0 else -P / 2)
        uv = o.data.uv_layers.active
        o.data.materials.append(zahl_mat(str(meter), hg="d0141a" if meter in (240, 250, 260) else "1d3f9a"))
        o.rotation_euler = (P / 2, 0, P if sy < 0 else 0)   # Gesicht zur Hangmitte
        rohr("tafelpfosten", (x, sy * 23.0, z), (x, sy * 23.0, z + .6), .04, STAHL)
# Zaun entlang des Hangs (Pfosten + Netz)
NETZ = mat("netz", "1d3f9a", .7)
for sy in (-1, 1):
    for x in range(0, 440, 6):
        z = hang_z(x)
        rohr("zaunpfosten", (x, sy * 24.2, z - .3), (x, sy * 24.2, z + 1.2), .035, STAHL)
    bm = bmesh.new(); r_ = []
    for x in range(0, 441, 3):
        z = hang_z(x); r_.append((bm.verts.new((x, sy * 24.2, z + .2)), bm.verts.new((x, sy * 24.2, z + 1.15))))
    for a, b_ in zip(r_, r_[1:]):
        bm.faces.new((a[0], b_[0], b_[1], a[1]))
    me = bpy.data.meshes.new("netz"); bm.to_mesh(me); bm.free(); o = bpy.data.objects.new("netz", me); sc.collection.objects.link(o); me.materials.append(NETZ)
# Kampfrichterturm (rechts, Hoehe ~ K-Punkt)
xk = x_aus_s(200); zk = hang_z(xk)
box("richterturm", (16, 8, 22), (xk - 40, -46, zk + 25), BETON, .1)
for i in range(5):
    box("richterfenster", (2.4, .08, 1.6), (xk - 48 + i * 3.6, -41.9, zk + 33), mat("glas2", "1c2a36", .03, Coat_Weight=1), .01)
box("richterdach", (17, 9, .5), (xk - 40, -46, zk + 36.3), SCHWARZ, .05)

# ======================================================================  Ski, Schuhe, Helm, Brille
SKI_M = bpy.data.materials.new("ski"); SKI_M.use_nodes = True; ns = SKI_M.node_tree.nodes; ls_ = SKI_M.node_tree.links
tis = ns.new("ShaderNodeTexImage"); tis.image = bpy.data.images.load(LOGO); tcs = ns.new("ShaderNodeTexCoord")
mps = ns.new("ShaderNodeMapping"); mps.inputs["Scale"].default_value = (1.6, 3.2, 1); mps.inputs["Location"].default_value = (-.3, -1.1, 0)
ls_.new(tcs.outputs["Generated"], mps.inputs[0]); ls_.new(mps.outputs[0], tis.inputs[0]); tis.extension = "CLIP"
mxs = ns.new("ShaderNodeMix"); mxs.data_type = "RGBA"; mxs.inputs[6].default_value = (*hexf("d0141a"), 1); ls_.new(tis.outputs[1], mxs.inputs[0])
ls_.new(tis.outputs[0], mxs.inputs[7]); ls_.new(mxs.outputs[2], ns["Principled BSDF"].inputs["Base Color"])
ns["Principled BSDF"].inputs["Roughness"].default_value = .22; ns["Principled BSDF"].inputs["Coat Weight"].default_value = .8
SKI_VOR, SKI_HINT = 1.62, 1.0


def ski_mesh():
    bm = bmesh.new(); r_ = []
    n = 60
    for i in range(n + 1):
        x = -SKI_HINT + (SKI_VOR + SKI_HINT) * i / n
        tip = max(0, x - (SKI_VOR - .32)) / .32
        z = .16 * tip ** 2; br = .058 * (1 - .35 * tip ** 3)
        dick = .012 + .01 * (1 - abs(x) / 1.6)
        r_.append([bm.verts.new((x, sy * br, z + dz)) for sy, dz in ((-1, 0), (1, 0), (1, dick), (-1, dick))])
    for a, b_ in zip(r_, r_[1:]):
        for k in range(4):
            bm.faces.new((a[k], a[(k + 1) % 4], b_[(k + 1) % 4], b_[k]))
    bm.faces.new(r_[0][::-1]); bm.faces.new(r_[-1])
    me = bpy.data.meshes.new("ski"); bm.to_mesh(me); bm.free(); me.materials.append(SKI_M)
    return me


SKI_ME = ski_mesh()
SCHUH_M = mat("schuh", "16181c", .35, Coat_Weight=.5)
SKIS = {}
for sd in ("L", "R"):
    o = bpy.data.objects.new("ski_" + sd, SKI_ME); sc.collection.objects.link(o)
    bv = o.modifiers.new("b", "BEVEL"); bv.width = .004; bv.segments = 2
    sch = box("schuh_" + sd, (.30, .115, .13), (.02, 0, .085), SCHUH_M, .035, seg=4, eltern=o)
    box("schaft_" + sd, (.15, .11, .16), (-.04, 0, .2), SCHUH_M, .04, seg=4, eltern=o)
    box("bindung_" + sd, (.36, .07, .02), (.0, 0, .026), STAHL, .005, eltern=o)
    SKIS[sd] = o
# Helm + Brille am Kopf-Knochen
bpy.context.view_layer.update()
kopf_b = S.rig.data.bones["head"]
kh = S.rig.matrix_world @ kopf_b.head_local; kt = S.rig.matrix_world @ kopf_b.tail_local
kz = kh + (kt - kh) * .55
HELM_M = mat("helm", "f2f2f2", .25, Coat_Weight=1.0)
bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1, location=kz + Vector((0, .012, .03)))
helm = bpy.context.object; helm.name = "helm"; helm.scale = (.118, .132, .118); helm.data.materials.append(HELM_M)
bm = bmesh.new(); bm.from_mesh(helm.data)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -.05 and v.co.y < .2], context="VERTS"); bm.to_mesh(helm.data); bm.free()
helm.modifiers.new("d", "SOLIDIFY").thickness = .1
for p in helm.data.polygons:
    p.use_smooth = True
bpy.ops.mesh.primitive_torus_add(major_radius=.112, minor_radius=.012, location=kz + Vector((0, 0, -.025)))
band = bpy.context.object; band.name = "brillenband"; band.scale = (1, 1.12, .9); band.data.materials.append(mat("band", "111111", .7))
bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=1, location=kz + Vector((0, -.112, -.022)))
glas = bpy.context.object; glas.name = "brille"; glas.scale = (.085, .03, .036)
glas.data.materials.append(mat("brillenglas", "c2731a", .05, metal=1.0, Coat_Weight=1))
for p in glas.data.polygons:
    p.use_smooth = True
bpy.context.view_layer.update()
PI = (S.rig.matrix_world @ kopf_b.matrix_local @ Matrix.Translation((0, kopf_b.length, 0))).inverted()
for o in (helm, band, glas):
    o.parent = S.rig; o.parent_type = "BONE"; o.parent_bone = "head"; o.matrix_parent_inverse = PI
print("ok ausruestung")

# ======================================================================  IK
S.Z = {nm: leer("ik_" + nm) for nm in ("hand_L", "hand_R", "fuss_L", "fuss_R", "knie_L", "knie_R", "ell_L", "ell_R")}
S.IK = {}
for bone, ziel, pol, pw in (("lowerarm02.L", "hand_L", "ell_L", 0), ("lowerarm02.R", "hand_R", "ell_R", 0),
                            ("lowerleg02.L", "fuss_L", "knie_L", -P / 2), ("lowerleg02.R", "fuss_R", "knie_R", -P / 2)):
    c = S.rig.pose.bones[bone].constraints.new("IK"); c.target = S.Z[ziel]; c.chain_count = 4
    c.pole_target = S.Z[pol]; c.pole_angle = pw; S.IK[ziel] = c

# ======================================================================  Ablauf (Story-Zeit ts)
S0 = 78.0                    # Startbalken (Meter vor der Kante)
T_LOS, T_KANTE, T_LAND = .6, 6.0, 13.8
A_ANL = 2 * S0 / (T_KANTE - T_LOS) ** 2
V_KANTE = A_ANL * (T_KANTE - T_LOS)
S_LAND = 254.5
V_LAND = 31.0
T_STOPP = T_LAND + 2 * 88 / V_LAND
for k, sg in enumerate((S0 + .6, S0 + 2.6, S0 + 4.6)):
    p, t = anl_pkt(sg); GATE[k].location = (p.x, 0, p.z + .55)
print("Absprung km/h", round(V_KANTE * 3.6, 1))


def flug_s(u):
    return S_LAND * (.85 * u + .15 * u * u)


def flug_h(u):
    return TISCH_H * (1 - u) ** 2 * (1 - u) + 6.5 * math.sin(P * u) * (1 - u) ** .5


def flug_pkt(u):
    p, t, nn = hang_pkt(flug_s(u)); return p + nn * flug_h(u)


def rahmen_aus(p, f, up):
    f = f.normalized(); l = up.cross(f).normalized(); up = f.cross(l).normalized()
    return p, Matrix((f, l, up)).transposed()


def rahmen(ts):
    """Position (Skiunterseite unter der Bindung) + Orientierung (Spalten: vorne, links, oben), Phase"""
    if ts < T_KANTE:
        s = S0 if ts < T_LOS else S0 - .5 * A_ANL * (ts - T_LOS) ** 2
        p, t = anl_pkt(s); up = Vector((-t.z, 0, t.x))
        return rahmen_aus(p + up * .055, t, up) + ("anlauf",)
    if ts < T_LAND:
        u = (ts - T_KANTE) / (T_LAND - T_KANTE)
        p = flug_pkt(u); d = (flug_pkt(min(1, u + .003)) - flug_pkt(max(0, u - .003))).normalized()
        aoa = math.radians(8 + 26 * ease(u / .08) - 24 * ease((u - .9) / .1))
        f = Matrix.Rotation(aoa, 3, Vector((0, -1, 0))) @ d       # Spitzen nach oben drehen
        up = Vector((0, 1, 0)).cross(f) * -1
        up = Vector((-f.z, 0, f.x))
        return rahmen_aus(p, f, up) + ("flug",)
    tl = ts - T_LAND; tt = min(tl, T_STOPP - T_LAND)
    s = S_LAND + V_LAND * tt - .5 * (V_LAND / (T_STOPP - T_LAND)) * tt * tt
    p, t, nn = hang_pkt(s)
    return rahmen_aus(p + nn * .02, t, nn) + ("auslauf",)


def pose_lokal(name):
    """(Becken lokal, Rumpf-Neigung in Grad, Haende L/R, Ski L/R (x, y, gier, nick), Nacken, Knie-Pol, Ellbogen-Pol)"""
    if name == "start":
        return dict(pel=(-.28, 0, .66), e=48, hand=((-.05, .32, .62), (-.05, -.32, .62)), ski=((0, .11, 0, 0), (0, -.11, 0, 0)), nacken=-.3,
                    knie=(2.0, .25, 1.0), ell=(-.5, 1.4, 1.2))
    if name == "hocke":
        return dict(pel=(-.16, 0, .56), e=12, hand=((-.42, .2, .4), (-.42, -.2, .4)), ski=((0, .11, 0, 0), (0, -.11, 0, 0)), nacken=-.75,
                    knie=(2.0, .25, 1.0), ell=(-1.0, 1.2, 1.6))
    if name == "flug":
        e = 15
        return dict(pel=(.86, 0, .36), e=e, hand=((.55, .36, .22), (.55, -.36, .22)), ski=((0, .2, .21, .0), (0, -.2, -.21, .0)), nacken=-.85,
                    knie=(1.0, .5, -2.0), ell=(.0, 1.5, 1.6))
    if name == "landung":
        return dict(pel=(.04, 0, .74), e=70, hand=((.15, .78, 1.05), (.15, -.78, 1.05)), ski=((.34, .11, 0, 0), (-.34, -.11, 0, 0)), nacken=-.15,
                    knie=(2.0, .3, .8), ell=(-.2, 1.6, 1.4))
    if name == "fahren":
        return dict(pel=(-.08, 0, .82), e=72, hand=((.25, .45, .82), (.25, -.45, .82)), ski=((0, .12, 0, 0), (0, -.12, 0, 0)), nacken=-.1,
                    knie=(2.0, .3, .8), ell=(-.2, 1.6, 1.4))
    if name == "stehen":
        return dict(pel=(0, 0, .95), e=90, hand=((.05, .3, .8), (.05, -.3, .8)), ski=((0, .13, 0, 0), (0, -.13, 0, 0)), nacken=0,
                    knie=(2.0, .3, .8), ell=(-.3, 1.4, 1.2))


def mix_pose(a, b, k):
    if k <= 0:
        return a
    if k >= 1:
        return b
    out = {}
    for key in a:
        va, vb = a[key], b[key]
        if isinstance(va, (int, float)):
            out[key] = va + (vb - va) * k
        elif isinstance(va[0], (int, float)):
            out[key] = tuple(x + (y - x) * k for x, y in zip(va, vb))
        else:
            out[key] = tuple(tuple(x + (y - x) * k for x, y in zip(pa, pb)) for pa, pb in zip(va, vb))
    return out


def pose_bei(ts):
    if ts < T_LOS:
        return pose_lokal("start")
    if ts < T_KANTE - .3:
        return mix_pose(pose_lokal("start"), pose_lokal("hocke"), ease((ts - T_LOS) / .7))
    if ts < T_LAND - .5:
        return mix_pose(pose_lokal("hocke"), pose_lokal("flug"), ease((ts - (T_KANTE - .3)) / .55))
    if ts < T_LAND + .5:
        return mix_pose(pose_lokal("flug"), pose_lokal("landung"), ease((ts - (T_LAND - .5)) / .5))
    if ts < T_STOPP - .6:
        return mix_pose(pose_lokal("landung"), pose_lokal("fahren"), ease((ts - (T_LAND + .5)) / .8))
    return mix_pose(pose_lokal("fahren"), pose_lokal("stehen"), ease((ts - (T_STOPP - .6)) / .7))


def rig_matrix(e_grad):
    e = math.radians(e_grad)
    H = Vector((math.cos(e), 0, math.sin(e))); Fc = Vector((math.sin(e), 0, -math.cos(e)))
    Y = -Fc; Z = H; X = Y.cross(Z)
    return Matrix((X, Y, Z)).transposed()


def figur(ts):
    S.zuruecksetzen()
    pos, M, phase = rahmen(ts)
    po = pose_bei(ts)
    Mw = M @ rig_matrix(po["e"])
    rq = Mw.to_quaternion()
    pel_w = pos + M @ Vector(po["pel"])
    S.rig.rotation_mode = "QUATERNION"; S.rig.rotation_quaternion = rq
    S.rig.location = pel_w - rq.to_matrix() @ (S.PEL * S.SK)
    for c in S.IK.values():
        c.influence = 1.0
    jubel = ease((ts - (T_STOPP + .2)) / .6)
    for sd, (sx, sy, gier, nick) in zip(("L", "R"), po["ski"]):
        o = SKIS[sd]
        lok = Matrix.Translation((sx, sy, 0)) @ Matrix.Rotation(gier, 4, "Z") @ Matrix.Rotation(nick, 4, "Y")
        o.matrix_world = Matrix.Translation(pos) @ M.to_4x4() @ lok
        S.Z["fuss_" + sd].location = pos + M @ Vector((sx + .03, sy, .15))
        s_ = 1 if sd == "L" else -1
        S.Z["knie_" + sd].location = pel_w + M @ Vector((po["knie"][0], s_ * po["knie"][1], po["knie"][2]))
        S.Z["ell_" + sd].location = pel_w + M @ Vector((po["ell"][0], s_ * po["ell"][1], po["ell"][2]))
    for sd, h in zip(("L", "R"), po["hand"]):
        S.Z["hand_" + sd].location = pos + M @ Vector(h)
    if jubel > 0:
        S.IK["hand_L"].influence = 1 - jubel; S.IK["hand_R"].influence = 1 - jubel
        S.dreh("upperarm01.L", z=-.72 + 3.0 * jubel, x=.2 * jubel); S.dreh("upperarm01.R", z=.72 - 3.0 * jubel, x=.2 * jubel)
        S.dreh("lowerarm01.L", x=-.4 * jubel); S.dreh("lowerarm01.R", x=-.4 * jubel)
    S.dreh("neck01", x=po["nacken"] - .2 * jubel)
    for sd in ("L", "R"):
        for ff in range(2, 6):
            for g in (1, 2, 3):
                S.dreh(f"finger{ff}-{g}.{sd}", x=.5 + .6 * jubel)
    # Fuesse parallel zum Ski ausrichten (nach dem IK)
    bpy.context.view_layer.update()
    for sd in ("L", "R"):
        pb = S.rig.pose.bones["foot." + sd]
        Mb = S.rig.matrix_world @ pb.matrix
        ist = (Mb.to_3x3() @ Vector((0, 1, 0))).normalized()
        soll = (SKIS[sd].matrix_world.to_3x3() @ Vector((1, 0, -.35))).normalized()
        dq = ist.rotation_difference(soll)
        neu = Matrix.Translation(Mb.translation) @ (dq.to_matrix() @ Mb.to_3x3()).to_4x4()
        pb.matrix = S.rig.matrix_world.inverted() @ neu
    bpy.context.view_layer.update()
    # Anzeige
    ANZ_TEX.image = ANZ_BILD[1] if ts > T_LAND + .8 else ANZ_BILD[0]
    return pel_w


def becken():
    nk = S.rig.matrix_world @ S.rig.pose.bones["neck01"].head
    return (S.rig.matrix_world @ (S.PEL)) * .55 + nk * .45


# ======================================================================  Kamera
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam
cam.data.clip_start = .05; cam.data.clip_end = 6000; cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
cam.data.dof.use_dof = True
X_LAND = x_aus_s(S_LAND); Z_LAND = hang_z(X_LAND)
X_STOPP = x_aus_s(S_LAND + 88); Z_STOPP = hang_z(X_STOPP)
TAFEL_Z = hang_z(440) + 12
print("Landung x", round(X_LAND, 1), "z", round(Z_LAND, 1), "Stopp x", round(X_STOPP, 1))
SZ = [
    (0.00, 1.40, 8.60, 8.85, "B+", (3.0, 2.5, 1.2), (3.0, 2.3, 1.1), "B", "B", 32),                       # Aufhaenger: Zeitlupe im Flug
    (1.40, 3.80, 6.40, 9.00, (75, -19, hang_z(75) + 1.6), (78, -19, hang_z(78) + 1.6), "B", "B", 28),          # von der Seite: fliegt vorbei
    (3.80, 5.00, 1.0, 1.0, (330, 8, hang_z(330) + 2), (322, 7, hang_z(322) + 2.4), (60, 0, hang_z(60) + 10), (50, 0, hang_z(50) + 14), 30),  # Hang von unten
    (5.00, 6.50, 0.0, 0.2, (430, 230, 40), (415, 215, 42), (0, 0, -15), (0, 0, -12), 24),                # Luftbild Planica
    (6.50, 8.00, -.6, .9, "B+", (-2.4, .7, 1.4), (-2.6, .7, 1.5), (120, 0, -90), (120, 0, -90), 24),         # vom Start runter
    (8.00, 9.60, 2.2, 3.8, "B+", (4.5, 1.0, -2.0), (4.5, 1.0, -2.0), "B", "B", 30),                          # Anlauf von vorne
    (9.60, 11.50, 3.8, 5.7, "B+", (.6, 2.6, .3), (.6, 2.6, .3), "B", "B", 28),                                # Anlauf seitlich
    (11.50, 12.90, 5.75, 6.30, (2.5, 5.5, .6), (2.5, 5.5, .6), "B", "B", 26),                                 # Absprung Zeitlupe
    (12.90, 14.50, 6.8, 7.5, "B+", (1.0, .4, 4.5), (1.2, .4, 4.5), "B", "B", 30),                             # V von oben
    (14.50, 15.40, 7.5, 7.9, "B+", (-.2, 3.0, .4), (-.2, 3.0, .4), "B", "B", 30),                             # Arme hinten, flach
    (15.40, 17.40, 8.0, 12.0, "B+", (-8, -25, 6), (-8, -25, 6), "B", "B", 55),                                # lange Fahrt seitlich
    (17.40, 19.40, 12.7, 14.05, (X_LAND + 12, 18, Z_LAND + 1.2), (X_LAND + 12, 18, Z_LAND + 1.2), "B", "B", 30),  # Landung kommt
    (19.40, 21.10, 13.7, 14.15, "B+", (3.5, -2.2, .2), (3.5, -2.2, .2), "B", "B", 32),                        # Landung Zeitlupe
    (21.10, 23.50, 15.0, 17.0, (380, -90, hang_z(380) + 45), (372, -86, hang_z(372) + 43), (120, 0, hang_z(120)), (115, 0, hang_z(115)), 24),          # ganzer Hang
    (23.50, 25.60, 18.5, 20.6, "B+", (3.2, 1.2, .6), (3.0, 1.4, .7), "B", "B", 32),                          # Jubel
    (25.60, 27.40, 20.6, 22.4, (X_STOPP - 4.5, -.7, Z_STOPP + 1.5), (X_STOPP - 10, -.9, Z_STOPP + 2.6), (452, 0, TAFEL_Z - 6), (452, 0, TAFEL_Z - 5), 24),  # Tafel
]


SZ = [s if s[4] == "B+" else s[:4] + ("P",) + s[4:] for s in SZ]


def zustand(t):
    for s in SZ:
        if s[0] <= t < s[1]:
            break
    k = (t - s[0]) / (s[1] - s[0])
    ts = s[2] + (s[3] - s[2]) * k
    k = ease(k) * .7 + k * .3
    figur(ts)
    bk = becken()
    if s[4] == "B+":
        pos = bk + lerpv(s[5], s[6], k)
    else:
        pos = lerpv(s[5], s[6], k)
    ziel = bk if s[7] == "B" else lerpv(s[7], s[8], k)
    cam.location = pos; d = ziel - pos; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = s[9]; cam.data.dof.focus_distance = d.length; cam.data.dof.aperture_fstop = 2.8 if d.length < 6 else 8
    zit = .004
    cam.location += Vector((zit * math.sin(t * 7.3), zit * math.cos(t * 5.1), zit * math.sin(t * 9.7)))


# ======================================================================  Auslauf: Zuschauer, Fahnen, Anzeigetafel
koerper_me = []
for i, f in enumerate(["c62828", "1565c0", "f2f2f2", "2e7d32", "212121", "f9a825", "6a1b9a", "1b8a4a", "e65100"]):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=7, radius=1, matrix=Matrix.Translation((0, 0, .55)) @ Matrix.Diagonal((.28, .2, .42, 1)))
    bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=7, radius=.11, matrix=Matrix.Translation((0, 0, 1.08)))
    bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=.11, radius2=.02, depth=.16, matrix=Matrix.Translation((0, 0, 1.2)))
    me = bpy.data.meshes.new("pub%d" % i); bm.to_mesh(me); bm.free(); me.materials.append(mat("pubm%d" % i, f, .8, Sheen_Weight=.5))
    for p in me.polygons:
        p.use_smooth = True
    koerper_me.append(me)
FAHNEN = []
rp = random.Random(3)
for sy in (-1, 1):
    for reihe in range(14):
        for j in range(70):
            if rp.random() < .12:
                continue
            x = 300 + j * 1.6 + rp.uniform(-.3, .3)
            breite = 24 + .06 * max(0, x - 100)
            y = sy * (breite + 6 + reihe * 1.1 + rp.uniform(-.2, .2))
            o = bpy.data.objects.new("pub%d_%d_%d" % (sy + 1, reihe, j), rp.choice(koerper_me)); sc.collection.objects.link(o)
            o.location = (x, y, gelaende_z(x, y) + .02); o.rotation_euler = (0, 0, (-P / 2 if sy > 0 else P / 2) + rp.uniform(-.5, .5))
            if rp.random() < .05:
                f_ = box("fahne", (.02, 1.2, .8), (x, y, o.location.z + 2.3), mat("fahne%d" % len(FAHNEN), rp.choice(["c62828", "f2f2f2", "1565c0", "2e7d32", "f9a825"]), .7, Sheen_Weight=.6), 0)
                rohr("fahnenstock", (x, y, o.location.z + 1.0), (x, y, o.location.z + 2.8), .015, SCHWARZ); FAHNEN.append(f_)
    # Werbebanden am Auslauf
    box("bande", (140, .15, 1.0), (370, sy * 31.5, hang_z(370) + .5), BAND_M, .02)
bpy.ops.mesh.primitive_plane_add(size=1); tafel = bpy.context.object; tafel.name = "anzeige"
tafel.scale = (18, 9, 1); tafel.rotation_euler = (P / 2, 0, -P / 2); tafel.location = (452, 0, hang_z(440) + 12)
box("anzeige_rahmen", (.6, 19, 10), (452.4, 0, hang_z(440) + 12), SCHWARZ, .05)
for yy in (-6, 6):
    rohr("anzeige_bein", (452.4, yy, hang_z(440) - 1), (452.4, yy, hang_z(440) + 7), .3, STAHL)
ANZ_M = bpy.data.materials.new("anzeige"); ANZ_M.use_nodes = True; na = ANZ_M.node_tree.nodes
ANZ_TEX = na.new("ShaderNodeTexImage"); ANZ_M.node_tree.links.new(ANZ_TEX.outputs[0], na["Principled BSDF"].inputs["Emission Color"])
na["Principled BSDF"].inputs["Emission Strength"].default_value = 2.5; na["Principled BSDF"].inputs["Base Color"].default_value = (0, 0, 0, 1)
tafel.data.materials.append(ANZ_M)
p1 = os.path.join(HIER, "_sf_anz1.png"); p2 = os.path.join(HIER, "_sf_anz2.png")
ME.logo_bild(p1, "PREVC", farbe=(1, .75, .1), symbol=False, hintergrund=(.02, .02, .03), unterzeile="SLO", breite=1024, hoehe=512)
ME.logo_bild(p2, "254.5 m", farbe=(1, .75, .1), symbol=False, hintergrund=(.02, .02, .03), unterzeile="WORLD RECORD", breite=1024, hoehe=512)
ANZ_BILD = (bpy.data.images.load(p1), bpy.data.images.load(p2)); ANZ_TEX.image = ANZ_BILD[0]
print("ok szene")

# ======================================================================  Wald (Fichten mit Schnee) als Instanzen
def fichte_mesh(name, h):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=7, radius1=.18 * h / 12, radius2=.12 * h / 12, depth=h * .25,
                          matrix=Matrix.Translation((0, 0, h * .12)))
    for k, (z0, r0, d) in enumerate(((.18, .26, .38), (.36, .21, .32), (.55, .16, .28), (.72, .11, .24))):
        bmesh.ops.create_cone(bm, cap_ends=True, segments=9, radius1=r0 * h, radius2=.01, depth=d * h, matrix=Matrix.Translation((0, 0, z0 * h + d * h / 2)))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.materials.append(FICHTE)
    for p in me.polygons:
        p.use_smooth = True
    return me


FICHTE = bpy.data.materials.new("fichte"); FICHTE.use_nodes = True; nf = FICHTE.node_tree.nodes; lf = FICHTE.node_tree.links; bf_ = nf["Principled BSDF"]
geo_f = nf.new("ShaderNodeNewGeometry"); sepf = nf.new("ShaderNodeSeparateXYZ"); lf.new(geo_f.outputs["Normal"], sepf.inputs[0])
noi = nf.new("ShaderNodeTexNoise"); noi.inputs["Scale"].default_value = 6
adf = nf.new("ShaderNodeMath"); adf.operation = "ADD"; lf.new(sepf.outputs["Z"], adf.inputs[0])
nm2 = nf.new("ShaderNodeMath"); nm2.operation = "MULTIPLY"; nm2.inputs[1].default_value = .5; lf.new(noi.outputs[0], nm2.inputs[0]); lf.new(nm2.outputs[0], adf.inputs[1])
rf = nf.new("ShaderNodeMapRange"); rf.inputs[1].default_value = .55; rf.inputs[2].default_value = .8; lf.new(adf.outputs[0], rf.inputs[0])
mxf = nf.new("ShaderNodeMix"); mxf.data_type = "RGBA"; mxf.inputs[6].default_value = (*hexf("2f5236"), 1); mxf.inputs[7].default_value = (.92, .94, .97, 1)
lf.new(rf.outputs[0], mxf.inputs[0]); lf.new(mxf.outputs[2], bf_.inputs["Base Color"]); bf_.inputs["Roughness"].default_value = .8
FICHTEN = [fichte_mesh("fichte%d" % i, h) for i, h in enumerate((9, 12, 15, 18))]
rw = random.Random(7)
anz = 0
for _ in range(9000):
    x = rw.uniform(-140, 520); y = rw.uniform(-330, 330)
    breite = 24 + .06 * max(0, x - 100)
    if abs(y) < breite + 9:
        continue
    if x > 300 and abs(y) < breite + 40:        # Auslauf/Zuschauer frei
        continue
    if x < 5 and abs(y) < 16:                   # Anlauf frei
        continue
    if -60 < x - (xk - 40) < 60 and -70 < y < -30:
        continue
    o = bpy.data.objects.new("fichte%05d" % anz, rw.choice(FICHTEN)); sc.collection.objects.link(o)
    o.location = (x, y, gelaende_z(x, y) - .4); o.rotation_euler = (0, 0, rw.uniform(0, 2 * P)); s_ = rw.uniform(.8, 1.25); o.scale = (s_, s_, s_ * rw.uniform(.9, 1.15))
    anz += 1
print("fichten", anz)


os.makedirs(A.ordner, exist_ok=True)
N = int(round(D * A.fps))
liste = [int(round(float(x) * A.fps)) for x in A.nur.split(",")] if A.nur else list(range(A.start, N))
for f in liste:
    pfad = os.path.join(A.ordner, f"skiflug_{f:04d}.png")
    if os.path.exists(pfad) and not A.nur:
        continue
    zustand(f / A.fps); bpy.context.view_layer.update(); zustand(f / A.fps)
    sc.render.filepath = pfad
    bpy.ops.render.render(write_still=True); print("FERTIG", pfad, flush=True)
