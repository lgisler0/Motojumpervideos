"""Schwerstes von einem Mann gezogenes Flugzeug: 188,83 t (Kevin Fast, Kanada 17.9.2009, GWR), 1:16 min, 8,8 m. Realistischer Stil.
python3 flugzeug3d.py <ordner> [--nur t1,t2] [--start i] [--samples n]"""
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
D = 27.6
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


# ======================================================================  Kraftsportler (zuerst)
import mensch_echt as ME
LOGO = ME.logo_bild(os.path.join(HIER, "_logo_norda.png"), "NORDA", farbe=(1, 1, 1))
KF = ME.mensch("fast", 19, 1.0, .55, .9, .7, haut="caucasian", haare="short03", braue="eyebrow001", haarfarbe="4a3a2a")
ME.trikot(KF, "tshirt", "tights", "c62828", "15171b", brust=LOGO, brust_mass=(.18, .09), bein=LOGO)
for o in KF.huellen:
    if "versatz" in o.modifiers:
        o.modifiers["versatz"].strength = .02 if o.name.endswith("_hemd") else .011
    for md in o.modifiers:
        if md.type == "SUBSURF":
            md.render_levels = 2
hoehe = max(v.z for v in KF.EV); KF.SK = 1.80 / hoehe; KF.rig.scale = (KF.SK,) * 3
KF.PEL = KF.rig.data.bones["upperleg01.L"].head_local.copy(); KF.PEL.x = 0
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
BLECH = pbr("blech", "Metal012", .5, tint="9aa0a6", rau_mul=.8, rau_add=.2, metal=.8)
BETON = pbr("beton", "Concrete034", .12, tint="b8b6b0")
GRAS = pbr("gras", "Grass004", .2, tint="9aa070")
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; nt = w.node_tree
env = nt.nodes.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(os.path.join(ASSET, "tag.hdr"))
nt.links.new(env.outputs[0], nt.nodes["Background"].inputs[0]); nt.nodes["Background"].inputs[1].default_value = 1.0
bpy.ops.object.light_add(type="SUN", rotation=(math.radians(50), 0, math.radians(-40))); sonne = bpy.context.object
sonne.data.energy = 4.2; sonne.data.angle = math.radians(1.2); sonne.data.color = (1, .96, .9)

# ======================================================================  Flugplatz: Vorfeld, Gras, Linien, Hallen
box("vorfeld", (420, 260, .2), (40, 0, -.1), BETON, 0)
box("gras", (3000, 3000, .1), (0, 0, -.25), GRAS, 0)
GELBLINIE = mat("gelblinie", "e8b81a", .6)
WEISSLINIE = mat("weisslinie", "eeeeea", .6)
box("mittellinie", (300, .3, .01), (40, -2.2, .005), GELBLINIE, 0)
for x in range(-140, 200, 12):
    box("fuge", (.03, 260, .006), (x, 0, .004), mat("fuge", "6a6a66", .9) if not bpy.data.materials.get("fuge") else bpy.data.materials["fuge"], 0)
START_X = 0.0; ZIEL_X = 8.8
box("startlinie", (.25, 14, .012), (START_X, 0, .006), WEISSLINIE, 0)
box("ziellinie", (.25, 14, .012), (ZIEL_X, 0, .006), mat("ziellinie", "d0141a", .6), 0)
for x, txt in ((START_X, "START"), (ZIEL_X, "8.8 m")):
    p_ = os.path.join(HIER, f"_fz_{txt.replace(' ', '').replace('.', '_')}.png")
    ME.logo_bild(p_, txt, farbe=(1, 1, 1), symbol=False, breite=512, hoehe=200)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(x + .9, 5.5, .02)); o = bpy.context.object; o.scale = (1.6, 4.0, 1); o.rotation_euler = (0, 0, -P / 2)
    m_ = bpy.data.materials.new("schrift_" + txt); m_.use_nodes = True; ti = m_.node_tree.nodes.new("ShaderNodeTexImage"); ti.image = bpy.data.images.load(p_)
    bsd = m_.node_tree.nodes["Principled BSDF"]; m_.node_tree.links.new(ti.outputs[0], bsd.inputs["Base Color"]); m_.node_tree.links.new(ti.outputs[1], bsd.inputs["Alpha"])
    o.data.materials.append(m_)


def halle(name, cx, cy, laenge, radius):
    """Bogenhalle (halber Zylinder) mit Wellblech, offenes Tor zur Vorfeldseite"""
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=radius, depth=laenge, location=(cx, cy, 0), rotation=(P / 2, 0, 0))
    o = bpy.context.object; o.name = name
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y < -.01 * radius], context="VERTS"); bm.to_mesh(o.data); bm.free()
    o.data.materials.append(BLECH); so = o.modifiers.new("d", "SOLIDIFY"); so.thickness = .3
    for p in o.data.polygons:
        p.use_smooth = False
    box(name + "_rueckwand", (2 * radius, .4, radius), (cx, cy + laenge / 2, radius / 2), BLECH, 0)
    return o


for k, (cx, cy) in enumerate(((-40, 150), (40, 150), (120, 150))):
    halle("halle%d" % k, cx, cy, 60, 28)
box("tower", (8, 8, 26), (-120, 110, 13), mat("tower", "d8d4cc", .7), .1)
box("tower_kanzel", (11, 11, 5), (-120, 110, 28.5), mat("kanzel", "1c2a36", .05, Coat_Weight=1), .2)

# ======================================================================  Militaer-Transportflugzeug (grau, Hochdecker, T-Leitwerk, 4 Triebwerke)
def flugzeug_mat():
    m = bpy.data.materials.new("flugzeuggrau"); m.use_nodes = True; nt_ = m.node_tree; n = nt_.nodes; l = nt_.links; b = n["Principled BSDF"]
    tc = n.new("ShaderNodeTexCoord"); sp = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Object"], sp.inputs[0])
    def fuge(src, per, br):
        a = n.new("ShaderNodeMath"); a.operation = "PINGPONG"; a.inputs[1].default_value = per / 2; l.new(src, a.inputs[0])
        c = n.new("ShaderNodeMath"); c.operation = "LESS_THAN"; c.inputs[1].default_value = br; l.new(a.outputs[0], c.inputs[0]); return c
    f1 = fuge(sp.outputs["X"], 1.6, .005); f2 = fuge(sp.outputs["Z"], 1.1, .004); f3 = fuge(sp.outputs["Y"], 1.4, .004)
    mx_ = n.new("ShaderNodeMath"); mx_.operation = "MAXIMUM"; l.new(f1.outputs[0], mx_.inputs[0]); l.new(f2.outputs[0], mx_.inputs[1])
    mx2 = n.new("ShaderNodeMath"); mx2.operation = "MAXIMUM"; l.new(mx_.outputs[0], mx2.inputs[0]); l.new(f3.outputs[0], mx2.inputs[1])
    no = n.new("ShaderNodeTexNoise"); no.inputs["Scale"].default_value = .35; no.inputs["Detail"].default_value = 6; l.new(tc.outputs["Object"], no.inputs["Vector"])
    rp = n.new("ShaderNodeValToRGB"); l.new(no.outputs["Fac"], rp.inputs[0])
    rp.color_ramp.elements[0].color = (*hexf("6f757c"), 1); rp.color_ramp.elements[1].color = (*hexf("8a9097"), 1)
    mix = n.new("ShaderNodeMix"); mix.data_type = "RGBA"; l.new(mx2.outputs[0], mix.inputs[0]); l.new(rp.outputs[0], mix.inputs[6]); mix.inputs[7].default_value = (*hexf("5a6066"), 1)
    l.new(mix.outputs[2], b.inputs["Base Color"])
    rr = n.new("ShaderNodeMapRange"); rr.inputs[3].default_value = .42; rr.inputs[4].default_value = .62; l.new(no.outputs["Fac"], rr.inputs[0]); l.new(rr.outputs[0], b.inputs["Roughness"])
    bu = n.new("ShaderNodeBump"); bu.inputs["Strength"].default_value = .35; bu.inputs["Distance"].default_value = .004; bu.invert = True
    l.new(mx2.outputs[0], bu.inputs["Height"]); l.new(bu.outputs[0], b.inputs["Normal"])
    b.inputs["Coat Weight"].default_value = .15
    return m


GRAU = flugzeug_mat()
GRAU_D = mat("grau_dunkel", "50565c", .6)
FENSTER = mat("cockpit", "1a2430", .05, Coat_Weight=1)
PLANE = bpy.data.objects.new("transporter", None); sc.collection.objects.link(PLANE)


def rumpf():
    bm = bmesh.new(); r_ = []
    n = 40
    for i in range(n + 1):
        k = i / n; x = -26 + 53 * k
        r = 3.4 * min(1, (1 - k) / .12) ** .55 if k > .88 else 3.4
        if k < .3:
            r = 3.4 * (.25 + .75 * (k / .3) ** .6)
        zc = 1.6 * max(0, (.3 - k) / .3) ** 1.5 + (-.3 * max(0, (k - .88) / .12))
        r_.append([bm.verts.new((x, r * math.cos(a), 3.4 + zc + r * .97 * math.sin(a))) for a in [2 * P * j / 20 for j in range(20)]])
    for a, b_ in zip(r_, r_[1:]):
        for j in range(20):
            bm.faces.new((a[j], a[(j + 1) % 20], b_[(j + 1) % 20], b_[j]))
    bm.faces.new(r_[0][::-1]); bm.faces.new(r_[-1])
    me = bpy.data.meshes.new("rumpf"); bm.to_mesh(me); bm.free(); me.materials.append(GRAU)
    for p in me.polygons:
        p.use_smooth = True
    o = bpy.data.objects.new("rumpf", me); sc.collection.objects.link(o); o.parent = PLANE
    s_ = o.modifiers.new("s", "SUBSURF"); s_.levels = 1; s_.render_levels = 2
    return o


rumpf()
# Fluegel (gepfeilt, auf dem Rumpf)
for sy in (-1, 1):
    bm = bmesh.new()
    pts = [(2.5, sy * 2.5), (-5.5, sy * 2.5), (-12.0, sy * 25.8), (-9.0, sy * 25.8)]
    vs_u = [bm.verts.new((x, y, 7.0)) for x, y in pts]; vs_o = [bm.verts.new((x, y, 7.9 - .25 * abs(y) / 25.8)) for x, y in pts]
    bm.faces.new(vs_u[::-1] if sy > 0 else vs_u); bm.faces.new(vs_o if sy > 0 else vs_o[::-1])
    for i in range(4):
        bm.faces.new((vs_u[i], vs_u[(i + 1) % 4], vs_o[(i + 1) % 4], vs_o[i]))
    me = bpy.data.meshes.new("fluegel"); bm.to_mesh(me); bm.free(); me.materials.append(GRAU)
    o = bpy.data.objects.new("fluegel", me); sc.collection.objects.link(o); o.parent = PLANE
    bv = o.modifiers.new("b", "BEVEL"); bv.width = .15; bv.segments = 2
    for k, yy in enumerate((9.5, 16.5)):                     # Triebwerke unter dem Fluegel
        x0 = -1.0 - (yy - 2.5) * .28
        zyl("triebwerk", 1.25, 5.8, (x0 + 1.5, sy * yy, 5.2), GRAU_D, rot=(0, P / 2, 0), eltern=PLANE)
        zyl("einlass", 1.05, .2, (x0 + 4.4, sy * yy, 5.2), mat("einlass", "1a1a1a", .6) if not bpy.data.materials.get("einlass") else bpy.data.materials["einlass"], rot=(0, P / 2, 0), eltern=PLANE)
        box("pylon", (3.0, .3, 1.4), (x0 + 1.0, sy * yy, 6.4), GRAU, .05, eltern=PLANE)
        zyl("duese", .9, .8, (x0 - 1.6, sy * yy, 5.2), mat("duese", "3a3530", .4, metal=.9), rot=(0, P / 2, 0), eltern=PLANE)
# T-Leitwerk
box("seitenleitwerk", (6.5, .6, 9.0), (-22.5, 0, 11.0), GRAU, .1, rot=(0, -.45, 0), eltern=PLANE)
box("hoehenleitwerk", (4.5, 19, .5), (-26.0, 0, 15.2), GRAU, .1, eltern=PLANE)
# Cockpit-Fenster, Fahrwerk
for sy in (-1, 1):
    box("fahrwerksverkleidung", (11, 1.6, 2.4), (-1, sy * 3.7, 1.6), GRAU, .4, eltern=PLANE)
RAEDER = []
REIFEN = mat("reifen", "151515", .85)
for sy in (-1, 1):
    for x in (-4.5, -1.0, 2.5):
        for dy in (-.45, .45):
            r_ = zyl("rad", .72, .45, (x, sy * 3.6 + dy, .72), REIFEN, rot=(P / 2, 0, 0), eltern=PLANE); RAEDER.append((r_, .72))
for dy in (-.35, .35):
    r_ = zyl("bugrad", .55, .35, (22.0, dy, .55), REIFEN, rot=(P / 2, 0, 0), eltern=PLANE); RAEDER.append((r_, .55))
rohr("bugbein", (22.0, 0, .55), (22.0, 0, 2.6), .14, STAHL, eltern=PLANE)
rohr("schlepp", (22.0, 0, .55), (23.6, 0, .5), .07, mat("gelbstange", "e8b81a", .5), eltern=PLANE)
ZUGPUNKT_LOKAL = Vector((23.7, 0, .5))
DUNKEL = mat("fugendunkel", "2a2d31", .7)
for k, (dy, rz) in enumerate(((-1.0, .25), (-.35, .08), (.35, -.08), (1.0, -.25))):      # Cockpit-Scheiben einzeln
    box("scheibe%d" % k, (.8, .55, .3), (23.0 - abs(dy) * .3, dy * 1.1, 5.45 - abs(dy) * .35), FENSTER, .05, rot=(0, .75, rz), eltern=PLANE)
for x in (16, 9, 2, -6, -13):                                                    # Bullaugen
    for sy in (-1, 1):
        zyl("bullauge", .16, .05, (x, sy * 3.36, 4.6), FENSTER, rot=(P / 2, 0, 0), eltern=PLANE)
for sy in (-1, 1):                                                               # Tueren (Umrisse)
    box("tuer", (1.1, .03, 1.9), (18.5, sy * 3.38, 3.4), DUNKEL, .02, eltern=PLANE)
    box("tuer_innen", (1.0, .035, 1.8), (18.5, sy * 3.38, 3.4), GRAU, .02, eltern=PLANE)
    box("klappe", (6.5, .05, .1), (-8.5 - 2, sy * 13, 7.3), DUNKEL, 0, rot=(0, 0, sy * -.28), eltern=PLANE)
box("heckrampe", (6.0, 5.2, .05), (-23.5, 0, 2.6), DUNKEL, .02, rot=(0, .32, 0), eltern=PLANE)
rohr("antenne1", (8, 0, 7.0), (8, 0, 7.8), .03, DUNKEL, eltern=PLANE)
rohr("antenne2", (-4, 0, 6.9), (-4.6, 0, 7.6), .03, DUNKEL, eltern=PLANE)
zyl("blitzlicht", .12, .12, (2, 0, 8.0), emis("beacon", "ff2010", 25), eltern=PLANE)
zyl("blitzlicht_u", .12, .12, (6, 0, -.05), bpy.data.materials["beacon"], eltern=PLANE)
for sy in (-1, 1):
    zyl("positionslicht", .1, .1, (-10.5, sy * 25.9, 7.6), emis("pos_" + ("rot" if sy > 0 else "gruen"), "ff2010" if sy > 0 else "20ff40", 18), eltern=PLANE)
for sy in (-1, 1):                                                               # Kennung am Leitwerk (Fantasie-Nummer)
    bpy.ops.object.text_add(location=(-22.2, sy * .32, 10.2), rotation=(P / 2, 0, 0 if sy < 0 else P)); t_ = bpy.context.object
    t_.data.body = "701"; t_.data.size = 1.4; t_.data.align_x = "CENTER"; t_.data.extrude = .005; t_.data.materials.append(mat("kennung", "2a2d31", .6)); t_.parent = PLANE
    bpy.ops.object.text_add(location=(10, sy * 3.42, 5.4), rotation=(P / 2, 0, 0 if sy < 0 else P)); t_ = bpy.context.object
    t_.data.body = "NORDA AIR"; t_.data.size = .9; t_.data.align_x = "CENTER"; t_.data.extrude = .005; t_.data.materials.append(bpy.data.materials["kennung"]); t_.parent = PLANE
# Bremskeile neben dem Rad (weggenommen) + Schlepper
box("bremskeil", (.4, .3, .25), (24.5, -3.0, .12), mat("keil", "e8b81a", .5), .03)
box("bremskeil", (.4, .3, .25), (24.5, -2.4, .12), bpy.data.materials["keil"], .03)

# Bodenfahrzeuge, Kegel, Flecken
def fahrzeug(name, x, y, rz, farbe, l_, b_, h_):
    e = leer(name, (x, y, 0)); e.rotation_euler = (0, 0, rz)
    m_ = mat(name + "_m", farbe, .35, Coat_Weight=.6)
    box(name + "_k", (l_, b_, h_), (0, 0, .5 + h_ / 2), m_, .12, eltern=e)
    box(name + "_kab", (l_ * .35, b_ * .95, h_ * .7), (l_ * .25, 0, .5 + h_ + h_ * .35), m_, .12, eltern=e)
    box(name + "_fen", (l_ * .36, b_ * .97, h_ * .35), (l_ * .25, 0, .5 + h_ + h_ * .45), FENSTER, .08, eltern=e)
    for dx in (-l_ * .32, l_ * .32):
        for dy in (-b_ / 2, b_ / 2):
            zyl(name + "_rad", .42, .3, (dx, dy, .42), REIFEN, rot=(P / 2, 0, 0), eltern=e)
    return e


fahrzeug("schlepper", -34, -6.0, .4, "e8b81a", 4.0, 2.2, .9)
fahrzeug("feuerwehr", -14, 6.5, -.2, "c62828", 8.5, 2.6, 2.0)
fahrzeug("kamerawagen", 42, 6.0, 2.8, "f2f2f2", 5.5, 2.3, 1.6)
KEGEL = mat("kegel", "ff6a00", .5)
for x in range(-12, 40, 4):
    for sy in (-1, 1):
        bpy.ops.mesh.primitive_cone_add(radius1=.18, radius2=.02, depth=.7, location=(x, sy * 7.8, .35)); o = bpy.context.object; o.data.materials.append(KEGEL)
FLECK = mat("oelfleck", "5f5d58", .85)
rf = random.Random(2)
for i in range(40):
    bpy.ops.mesh.primitive_circle_add(vertices=16, radius=1, fill_type="NGON", location=(rf.uniform(-40, 60), rf.uniform(-20, 20), .003)); o = bpy.context.object
    s_ = rf.uniform(.3, 1.6); o.scale = (s_, s_ * rf.uniform(.5, 1), 1); o.data.materials.append(FLECK)

# ======================================================================  150 Autos auf dem Parkplatz (zum Vergleich)
AUTO_FARBEN = ["c62828", "1565c0", "f2f2f2", "212121", "9e9e9e", "2e7d32", "f9a825", "6d4c41", "37474f", "b0bec5"]
auto_me = []
GLAS_A = mat("autoglas", "1a2430", .05, Coat_Weight=1)
for i, f in enumerate(AUTO_FARBEN):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1, matrix=Matrix.Translation((0, 0, .62)) @ Matrix.Diagonal((4.4, 1.8, .62, 1)))
    bmesh.ops.create_cube(bm, size=1, matrix=Matrix.Translation((-.25, 0, 1.18)) @ Matrix.Diagonal((2.3, 1.62, .55, 1)))
    me = bpy.data.meshes.new("auto%d" % i); bm.to_mesh(me); bm.free(); me.materials.append(mat("auto%d" % i, f, .22, Coat_Weight=.9)); me.materials.append(GLAS_A)
    me.materials.append(REIFEN)
    bm = bmesh.new(); bm.from_mesh(me)
    for fc in bm.faces:
        if fc.calc_center_median().z > 1.0 and abs(fc.normal.z) < .5:
            fc.material_index = 1
    for dx in (-1.35, 1.35):
        for dy in (-.82, .82):
            g = bmesh.ops.create_cone(bm, cap_ends=True, segments=14, radius1=.34, radius2=.34, depth=.24,
                                      matrix=Matrix.Translation((dx, dy, .34)) @ Matrix.Rotation(P / 2, 4, "X"))
            for v in g["verts"]:
                for fc in v.link_faces:
                    fc.material_index = 2
    bm.to_mesh(me); bm.free()
    auto_me.append(me)
box("parkplatz", (90, 50, .05), (150, -100, .01), mat("asphalt", "3a3a3c", .9), 0)
ra = random.Random(5); n_auto = 0
for r in range(10):
    for c in range(15):
        o = bpy.data.objects.new("auto%03d" % n_auto, ra.choice(auto_me)); sc.collection.objects.link(o); n_auto += 1
        o.location = (110 + c * 5.5, -120 + r * 4.4 if r < 5 else -118 + r * 4.4, .03); o.rotation_euler = (0, 0, P / 2 + (P if r % 2 else 0))
        bv = o.modifiers.new("b", "BEVEL"); bv.width = .12; bv.segments = 2; bv.limit_method = "ANGLE"
print("autos", n_auto)

# ======================================================================  Gurt + Seil
GURT_M = mat("gurt", "15171b", .7, Sheen_Weight=.3)
bpy.context.view_layer.update()
sp_b = KF.rig.data.bones["spine01"]; sp3 = KF.rig.data.bones["spine03"]
p1 = KF.rig.matrix_world @ sp_b.head_local; p3 = KF.rig.matrix_world @ sp3.head_local
bpy.ops.mesh.primitive_torus_add(major_radius=.19, minor_radius=.008, location=p1 + Vector((0, 0, .02))); gurt1 = bpy.context.object
gurt1.scale = (1.0, .78, 4.5); gurt1.data.materials.append(GURT_M)
bpy.ops.mesh.primitive_torus_add(major_radius=.2, minor_radius=.008, location=p3 + Vector((0, 0, .05))); gurt2 = bpy.context.object
gurt2.scale = (1.02, .8, 4.5); gurt2.data.materials.append(GURT_M)
ring = box("zugring", (.08, .05, .1), p1 + Vector((0, .2, 0)), STAHL, .02)
for sx in (-.12, .12):
    rohr("traeger", p1 + Vector((sx, .17, .02)), p3 + Vector((sx * 1.3, .18, .3)), .025, GURT_M)
bpy.context.view_layer.update()
for o, bone_ in ((gurt1, sp_b), (gurt2, sp3), (ring, sp_b), (bpy.data.objects["traeger"], sp_b), (bpy.data.objects["traeger.001"], sp_b)):
    PI = (KF.rig.matrix_world @ bone_.matrix_local @ Matrix.Translation((0, bone_.length, 0))).inverted()
    o.parent = KF.rig; o.parent_type = "BONE"; o.parent_bone = bone_.name; o.matrix_parent_inverse = PI
SEIL = zyl("zugseil", .022, 1, (0, 0, 0), mat("zugseil", "f2d21b", .6, Sheen_Weight=.4), v=10)
print("ok szene")
# ======================================================================  IK
KF.Z = {nm: leer("kf_ik_" + nm) for nm in ("hand_L", "hand_R", "fuss_L", "fuss_R", "knie_L", "knie_R", "ell_L", "ell_R")}
KF.IK = {}
for bone, ziel, pol, pw in (("lowerarm02.L", "hand_L", "ell_L", 0), ("lowerarm02.R", "hand_R", "ell_R", 0),
                            ("lowerleg02.L", "fuss_L", "knie_L", -P / 2), ("lowerleg02.R", "fuss_R", "knie_R", -P / 2)):
    c = KF.rig.pose.bones[bone].constraints.new("IK"); c.target = KF.Z[ziel]; c.chain_count = 4
    c.pole_target = KF.Z[pol]; c.pole_angle = pw; KF.IK[ziel] = c


def rig_mat(H, Fc):
    Z = Vector(H).normalized(); Fc = Vector(Fc); Y = -(Fc - Z * Fc.dot(Z)).normalized(); X = Y.cross(Z)
    return Matrix((X, Y, Z)).transposed()


# ======================================================================  Ablauf (Story-Zeit ts; Zug von 0 bis 76 s)
T_ZUG = 76.0
PLANE_X0 = START_X - 22.0
SEIL_L = 18.0


def weg(ts):
    if ts <= 0:
        return 0.0
    u = min(1.0, ts / T_ZUG)
    return ZIEL_X * (u ** 1.45)


def schritt(ts, versatz):
    LS, T = .34, 3.0
    s = max(0.0, ts) / T + versatz
    n = math.floor(s / 2); ph = s / 2 - n
    pos = 2 * LS * n + (2 * LS * ease((ph - .6) / .4) if ph > .6 else 0)
    hub = .07 * math.sin(max(0, (ph - .6) / .4) * P) if ph > .6 else 0
    return pos - LS * versatz, hub


def figur(ts):
    KF.zuruecksetzen()
    for c in KF.IK.values():
        c.influence = 1.0
    d = weg(ts)
    PLANE.location = (PLANE_X0 + d, 0, 0)
    for (r_, rad) in RAEDER:
        r_.rotation_euler = (P / 2, d / rad, 0)
    zug = PLANE.matrix_world @ ZUGPUNKT_LOKAL if False else Vector((PLANE_X0 + d, 0, 0)) + ZUGPUNKT_LOKAL
    mann_x = zug.x + SEIL_L
    lehn = ease((ts + 2.5) / 2.0) if ts < 77 else 1 - ease((ts - 77) / 1.2)
    th = math.radians(52) * lehn
    H = Vector((math.sin(th), 0, math.cos(th))); Fc = Vector((math.cos(th), 0, -math.sin(th)))
    pel = Vector((mann_x + .35 * lehn, 0, .98 - .18 * lehn))
    jubel = ease((ts - 78.0) / .7)
    rq = rig_mat(H, Fc).to_quaternion()
    KF.rig.rotation_mode = "QUATERNION"; KF.rig.rotation_quaternion = rq
    KF.rig.location = pel - rq.to_matrix() @ (KF.PEL * KF.SK)
    # Fuesse: im Zug vorne gebeugt / hinten gestreckt, langsame Schritte
    for sd, s_, vs in (("L", 1, 0.0), ("R", -1, 1.0)):
        if 0 < ts < T_ZUG:
            ph = (ts / 3.0 + vs) * P
            x = mann_x + (.3 if sd == "L" else -.5) * lehn + .14 * math.sin(ph) * lehn
            hb = .06 * max(0, math.cos(ph)) * lehn
            KF.Z["fuss_" + sd].location = (x, s_ * .17, .1 + hb)
        else:
            KF.Z["fuss_" + sd].location = (mann_x + (.2 if sd == "L" else -.45) * lehn, s_ * .16, .1)
        KF.Z["knie_" + sd].location = pel + Vector((2.0, s_ * .4, -.3))
        KF.Z["ell_" + sd].location = pel + Vector((-.6, s_ * 1.2, .2))
    # Haende: vor der Brust an den Traegern / nachher hoch
    for sd, s_ in (("L", 1), ("R", -1)):
        KF.Z["hand_" + sd].location = pel + H * .62 + Fc * .28 + Vector((0, s_ * .16, 0))
    if jubel > 0:
        KF.IK["hand_L"].influence = 1 - jubel; KF.IK["hand_R"].influence = 1 - jubel
        KF.dreh("upperarm01.L", z=-.72 + 3.0 * jubel, x=.2 * jubel); KF.dreh("upperarm01.R", z=.72 - 3.0 * jubel, x=.2 * jubel)
        KF.dreh("lowerarm01.L", x=-.4 * jubel); KF.dreh("lowerarm01.R", x=-.4 * jubel)
    KF.dreh("neck01", x=-.55 * lehn)
    for sd in ("L", "R"):
        for ff in range(2, 6):
            for g in (1, 2, 3):
                KF.dreh(f"finger{ff}-{g}.{sd}", x=1.3 * (1 - jubel) + .2)
    bpy.context.view_layer.update()
    # Seil vom Zugpunkt zum Ring (leicht durchhaengend nur vor dem Zug)
    r_w = ring.matrix_world.translation
    dv = r_w - zug; SEIL.location = (zug + r_w) / 2; SEIL.scale = (1, 1, max(.01, dv.length))
    SEIL.rotation_mode = "QUATERNION"; SEIL.rotation_quaternion = dv.to_track_quat("Z", "Y")
    # Publikum jubelt am Ende
    for o, z0, ph in PUBLIKUM:
        o.location.z = z0 + (.12 * max(0, math.sin(ts * 7 + ph)) if ts > 77.5 else .02 * math.sin(ts * 2 + ph))
    return pel, zug


def becken():
    nk = KF.rig.matrix_world @ KF.rig.pose.bones["neck01"].head
    return (KF.rig.matrix_world @ KF.PEL) * .55 + nk * .45


# ======================================================================  Absperrung + Publikum + Soldaten
BAR_M = mat("absperrung", "ff6a00", .5); BAR_W = mat("absperrung_w", "f2f2f2", .5)
for sy in (-1, 1):
    for k, x in enumerate(range(-30, 50, 2)):
        box("bar", (1.9, .1, .9), (x, sy * 9.0, .45), BAR_M if k % 2 else BAR_W, .02)
koerper_me = []
for i, f in enumerate(["c62828", "1565c0", "f2f2f2", "2e7d32", "212121", "f9a825", "33507a", "e65100", "4a5a3a"]):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=7, radius=1, matrix=Matrix.Translation((0, 0, .55)) @ Matrix.Diagonal((.26, .19, .42, 1)))
    bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=7, radius=.11, matrix=Matrix.Translation((0, 0, 1.08)))
    me_p = bpy.data.meshes.new("pub%d" % i); bm.to_mesh(me_p); bm.free(); me_p.materials.append(mat("pubm%d" % i, f, .8, Sheen_Weight=.5))
    for p in me_p.polygons:
        p.use_smooth = True
    koerper_me.append(me_p)
PUBLIKUM = []
rp = random.Random(4)
for sy in (-1, 1):
    for reihe in range(3):
        for j in range(60):
            if rp.random() < .25:
                continue
            x = -28 + j * 1.3 + rp.uniform(-.3, .3); y = sy * (10.0 + reihe * .9 + rp.uniform(-.2, .2))
            o = bpy.data.objects.new("pub%d_%d_%d" % (sy + 1, reihe, j), rp.choice(ZUSCH_ME)); sc.collection.objects.link(o)
            o.location = (x, y, .0); o.rotation_euler = (0, 0, (0 if sy > 0 else P) + rp.uniform(-.4, .4)); s_ = rp.uniform(.96, 1.04); o.scale = (s_, s_, s_)
            PUBLIKUM.append((o, .0, rp.uniform(0, 6)))

# ======================================================================  Kamera
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam
cam.data.clip_start = .03; cam.data.clip_end = 8000; cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
cam.data.dof.use_dof = True
NASE = Vector((22.0, 0, .6))
SZ = [
    (0.00, 1.30, 50.0, 50.4, "B+", (3.0, -1.3, -.5), (3.1, -1.4, -.5), "B", "B", 24),                        # Aufhaenger: von vorne unten
    (1.30, 2.50, 30.0, 31.2, "P", (35, -6.2, 1.7), (35.6, -6.3, 1.8), "M", "M", 22),                             # Mann, Seil, Flugzeug
    (2.50, 3.60, 10.0, 11.0, "PL+", (26.5, -5.5, .8), (26.2, -5.6, .9), "NR", "NR", 24),                    # Bugrad
    (3.60, 5.30, 0.0, 0.0, "P", (62, -92, 46), (56, -86, 43), (0, 20, 2), (0, 20, 2), 26),                     # Flugplatz von oben
    (5.30, 7.30, 0.0, 0.0, "P", (-24, -12, 2.2), (6, -12, 2.4), (-8, 0, 6), (18, 0, 5), 20),                  # unter dem Fluegel entlang
    (7.30, 9.20, 5.0, 6.9, "P", (30, -3.5, .7), (30.5, -3.6, .7), (4, 0, 9), (4, 0, 9.5), 18),                # Flugzeug ragt hinter ihm auf
    (9.20, 11.70, 5.0, 5.0, "P", (178, -138, 20), (172, -133, 22), (20, 0, 6), (15, 0, 6), 26),                # zum Parkplatz mit 150 Autos
    (11.70, 15.00, -6.0, .5, "B+", (1.4, -1.5, .3), (1.9, -1.9, .4), "B", "B", 28),                           # Gurt, lehnt sich rein
    (15.00, 18.90, 2.0, 12.0, "PL+", (25.0, -3.6, 1.2), (25.0, -3.6, 1.2), "NR", "NR", 26),                    # Bugrad dreht sich langsam
    (18.90, 23.20, 64.0, 77.0, "P", (42, -4.5, 2.4), (43, -4.8, 2.6), (9, 0, 2.0), (10, 0, 2.0), 24),            # weit: Ziellinie 8,8 m
    (23.20, 27.60, 78.0, 82.4, "B+", (4, -3, .6), (6.5, -5.5, 1.6), "B", "B", 24),                           # Jubel
]


def zustand(t):
    for s in SZ:
        if s[0] <= t < s[1]:
            break
    k = (t - s[0]) / (s[1] - s[0])
    ts = s[2] + (s[3] - s[2]) * k
    k = ease(k) * .7 + k * .3
    pel, zug = figur(ts)
    bk = becken()
    if s[4] == "B+":
        pos = bk + lerpv(s[5], s[6], k)
    elif s[4] == "PL+":
        pos = PLANE.location + lerpv(s[5], s[6], k)
    else:
        pos = lerpv(s[5], s[6], k)
    if s[7] == "B":
        ziel = bk
    elif s[7] == "M":
        ziel = (bk + zug) / 2 + Vector((0, 0, 1.5))
    elif s[7] == "NR":
        ziel = PLANE.location + NASE
    else:
        ziel = lerpv(s[7], s[8], k)
    cam.location = pos; d = ziel - pos; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = s[9]; cam.data.dof.focus_distance = d.length; cam.data.dof.aperture_fstop = 2.8 if d.length < 6 else 11
    zit = .005
    cam.location += Vector((zit * math.sin(t * 7.3), zit * math.cos(t * 5.1), zit * math.sin(t * 9.7)))


os.makedirs(A.ordner, exist_ok=True)
N = int(round(D * A.fps))
liste = [int(round(float(x) * A.fps)) for x in A.nur.split(",")] if A.nur else list(range(A.start, N))
for f in liste:
    pfad = os.path.join(A.ordner, f"flugzeug_{f:04d}.png")
    if os.path.exists(pfad) and not A.nur:
        continue
    zustand(f / A.fps); bpy.context.view_layer.update(); zustand(f / A.fps)
    sc.render.filepath = pfad
    bpy.ops.render.render(write_still=True); print("FERTIG", pfad, flush=True)
