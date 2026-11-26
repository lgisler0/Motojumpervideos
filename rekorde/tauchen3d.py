"""Tiefster Tauchgang mit konstantem Gewicht 136 m (Alexey Molchanov, Limassol 29.9.2023, GWR). Realistischer Stil.
python3 tauchen3d.py <ordner> [--nur t1,t2] [--start i] [--samples n]"""
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
D = 27.0
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


# ======================================================================  Taucher (zuerst)
import mensch_echt as ME
LOGO = ME.logo_bild(os.path.join(HIER, "_logo_norda.png"), "NORDA", farbe=(1, 1, 1))
AM = ME.mensch("molchanov", 61, 1.0, .4, .55, .25, haut="caucasian", haare="short02", braue="eyebrow001", haarfarbe="3a2a1c", schuhe=None)
ME.trikot(AM, "lang", "tights", "121417", "121417", brust=LOGO, brust_mass=(.15, .07), bein=LOGO)
for o in AM.huellen:
    if "versatz" in o.modifiers:
        o.modifiers["versatz"].strength = .017 if o.name.endswith("_hemd") else .010
    for md in o.modifiers:
        if md.type == "SUBSURF":
            md.render_levels = 2
hoehe = max(v.z for v in AM.EV); AM.SK = 1.84 / hoehe; AM.rig.scale = (AM.SK,) * 3
AM.PEL = AM.rig.data.bones["upperleg01.L"].head_local.copy(); AM.PEL.x = 0
print("ok mensch")

# ======================================================================  Materialien, Himmel, Sonne
SCHWARZ = mat("schwarzlack", "0d0d0f", .4, Coat_Weight=.3)
NEOPREN = mat("neopren", "111214", .78, Sheen_Weight=.5)
STAHL = pbr("stahl", "Metal012", 6, rau_mul=.6, rau_add=.15, metal=1.0)
sc.cycles.volume_step_rate = 4.0; sc.cycles.volume_max_steps = 256; sc.cycles.volume_bounces = 0
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; nt = w.node_tree
env = nt.nodes.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(os.path.join(ASSET, "tag.hdr"))
nt.links.new(env.outputs[0], nt.nodes["Background"].inputs[0]); nt.nodes["Background"].inputs[1].default_value = 1.0
bpy.ops.object.light_add(type="SUN", rotation=(math.radians(25), 0, math.radians(30))); sonne = bpy.context.object
sonne.data.energy = 4.5; sonne.data.angle = math.radians(1.0); sonne.data.color = (1, .96, .88)

# Wasserkoerper: Absorption + leuchtendes Blau, das mit der Tiefe abnimmt (billiges "Streulicht")
W_TIEF = -420.0
wm = bpy.data.materials.new("wasser_volumen"); wm.use_nodes = True; nw = wm.node_tree.nodes; lw = wm.node_tree.links
for nd in list(nw):
    if nd.type == "BSDF_PRINCIPLED":
        nw.remove(nd)
absn = nw.new("ShaderNodeVolumeAbsorption"); absn.inputs["Color"].default_value = (.2, .62, .78, 1); absn.inputs["Density"].default_value = .06
geo = nw.new("ShaderNodeNewGeometry"); sep = nw.new("ShaderNodeSeparateXYZ"); lw.new(geo.outputs["Position"], sep.inputs[0])
dv = nw.new("ShaderNodeMath"); dv.operation = "DIVIDE"; dv.inputs[1].default_value = 42; lw.new(sep.outputs["Z"], dv.inputs[0])
ex = nw.new("ShaderNodeMath"); ex.operation = "EXPONENT"; lw.new(dv.outputs[0], ex.inputs[0])
st = nw.new("ShaderNodeMath"); st.operation = "MULTIPLY"; st.inputs[1].default_value = .06 * 1.1; lw.new(ex.outputs[0], st.inputs[0])
em = nw.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (.06, .33, .55, 1); lw.new(st.outputs[0], em.inputs["Strength"])
add = nw.new("ShaderNodeAddShader"); lw.new(absn.outputs[0], add.inputs[0]); lw.new(em.outputs[0], add.inputs[1])
lw.new(add.outputs[0], nw["Material Output"].inputs["Volume"])
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, W_TIEF / 2 - .05)); vol = bpy.context.object; vol.name = "wasser"
vol.scale = (900, 900, -W_TIEF - .1); vol.data.materials.append(wm)
# Oberflaeche (Ocean) - von unten durchsichtig, von oben glaenzend
OBERF = mat("oberflaeche", "cfe8ec", .22, Transmission_Weight=1.0, IOR=1.33)
bpy.ops.mesh.primitive_grid_add(x_subdivisions=260, y_subdivisions=260, size=900, location=(0, 0, 0)); meer = bpy.context.object; meer.name = "meer"
meer.data.materials.append(OBERF)
for p in meer.data.polygons:
    p.use_smooth = True
oc = meer.modifiers.new("ocean", "OCEAN"); oc.geometry_mode = "DISPLACE"; oc.spatial_size = 40; oc.resolution = 9
oc.wave_scale = .5; oc.choppiness = .9; oc.wind_velocity = 8; oc.use_normals = True
# Meeresgrund weit unten (Sand), damit es nicht im Nichts endet
SAND = pbr("sand", "Ground054", .2, tint="c8b898")
bpy.ops.mesh.primitive_plane_add(size=900, location=(0, 0, -300)); grund = bpy.context.object; grund.data.materials.append(SAND)
# Kueste von Limassol in der Ferne: Huegel + weisse Haeuser
def rau2(x, y):
    return math.sin(x * .004 + 1) * math.cos(y * .006) + .5 * math.sin(x * .011 - y * .007)


bm = bmesh.new(); vs = []
for j in range(41):
    y = 700 + 900 * j / 40; row = []
    for i in range(161):
        x = -2400 + 4800 * i / 160
        z = -5 + max(0, y - 760) * .22 + 60 * max(0, rau2(x, y)) * min(1, (y - 700) / 300)
        row.append(bm.verts.new((x, y, z)))
    vs.append(row)
for j in range(40):
    for i in range(160):
        bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
me_k = bpy.data.meshes.new("kueste"); bm.to_mesh(me_k); bm.free(); kueste = bpy.data.objects.new("kueste", me_k); sc.collection.objects.link(kueste)
me_k.materials.append(mat("huegel", "8a8a5a", .9))
for p in me_k.polygons:
    p.use_smooth = True
HAUS = mat("haus", "f1ede6", .7)
rh = random.Random(4)
for j in range(260):
    x = rh.uniform(-1800, 1800); y = rh.uniform(760, 980)
    z = -5 + max(0, y - 760) * .22 + 60 * max(0, rau2(x, y)) * min(1, (y - 700) / 300)
    h_ = rh.uniform(8, 40) if rh.random() < .2 else rh.uniform(6, 14)
    box("haus%03d" % j, (rh.uniform(10, 24), rh.uniform(10, 20), h_), (x, y, z + h_ / 2 - 1), HAUS, .2)

# ======================================================================  Wettkampf: Boje, Plattform, Boot, Seil mit Marken, Bodenplatte
ORANGE = mat("boje", "ff6a00", .4, Coat_Weight=.5)
GELB = mat("seil_gelb", "f2d21b", .6, Sheen_Weight=.5)
WEISS = mat("weiss", "f2f2f2", .35, Coat_Weight=.4)
bpy.ops.mesh.primitive_torus_add(major_radius=1.1, minor_radius=.32, location=(0, 0, .05)); boje = bpy.context.object; boje.data.materials.append(ORANGE)
box("plattform", (1.6, 1.6, .08), (0, 0, .25), WEISS, .02)
rohr("fahnenstange", (.7, .7, .25), (.7, .7, 2.4), .02, SCHWARZ)
box("fahne", (.02, .8, .5), (.7, 1.1, 2.1), mat("fahne", "d0141a", .7, Sheen_Weight=.5), 0)
zyl("seil", .012, 138.5, (0, 0, -68.6), GELB, v=12)
for d_ in range(10, 136, 10):                 # Tiefenmarken (Tape) alle 10 m
    zyl("marke", .016, .25, (0, 0, -d_), mat("marke_rot", "d0141a", .5) if not bpy.data.materials.get("marke_rot") else bpy.data.materials["marke_rot"], v=12)
PLATTE_Z = -136.0
box("bodenplatte", (.9, .9, .05), (0, 0, PLATTE_Z - .15), WEISS, .02)
zyl("gegengewicht", .18, .5, (0, 0, PLATTE_Z - 1.6), STAHL)
TAGS = []
for k, (dx, dy) in enumerate(((-.3, .25), (.3, .25), (0, -.3))):
    TAGS.append(box("tag%d" % k, (.12, .02, .2), (dx, dy, PLATTE_Z - .05), mat("tagm%d" % k, ("f2d21b", "ff6a00", "1565c0")[k], .5), .01))
for dx in (-.42, .42):                          # Lichter an der Platte
    zyl("plattenlicht", .05, .05, (dx, 0, PLATTE_Z - .1), emis("plattenlicht", "fff0d0", 30) if not bpy.data.materials.get("plattenlicht") else bpy.data.materials["plattenlicht"])
for dx in (-.42, .42):
    bpy.ops.object.light_add(type="POINT", location=(dx, 0, PLATTE_Z + .1)); L_ = bpy.context.object; L_.data.energy = 60; L_.data.shadow_soft_size = .05
    L_.data.color = (1, .94, .82)
# Boot (Rumpf + Kabine) neben der Boje
def boot_mesh():
    bm = bmesh.new(); r_ = []
    for i in range(21):
        x = -5 + 10 * i / 20; k = i / 20
        br = 1.4 * (1 - max(0, (k - .6) / .4) ** 1.6) + .05
        r_.append([bm.verts.new((x, y, z)) for y, z in ((-br * .3, -.7), (-br, .1), (-br, 1.0), (br, 1.0), (br, .1), (br * .3, -.7))])
    for a, b_ in zip(r_, r_[1:]):
        for k in range(6):
            bm.faces.new((a[k], a[(k + 1) % 6], b_[(k + 1) % 6], b_[k]))
    bm.faces.new(r_[0][::-1]); bm.faces.new(r_[-1])
    me = bpy.data.meshes.new("boot"); bm.to_mesh(me); bm.free(); me.materials.append(WEISS)
    return me


boot = bpy.data.objects.new("boot", boot_mesh()); sc.collection.objects.link(boot); boot.location = (14, 9, 0); boot.rotation_euler = (0, 0, .5)
box("kabine", (3, 2, 1.4), (-.5, 0, 1.7), WEISS, .1, eltern=boot)
box("kabinenfenster", (3.02, 2.02, .4), (-.5, 0, 2.0), mat("glas", "1c2a36", .03, Coat_Weight=1), .05, eltern=boot)
# Sicherheitstaucher an der Oberflaeche (einfache Koerper) + Kampfrichter auf der Plattform
koerper_me = []
for i, f in enumerate(["111214", "1565c0", "f2f2f2"]):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=7, radius=1, matrix=Matrix.Translation((0, 0, .55)) @ Matrix.Diagonal((.26, .19, .42, 1)))
    bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=7, radius=.11, matrix=Matrix.Translation((0, 0, 1.08)))
    me_p = bpy.data.meshes.new("pub%d" % i); bm.to_mesh(me_p); bm.free(); me_p.materials.append(mat("pubm%d" % i, f, .7))
    for p in me_p.polygons:
        p.use_smooth = True
    koerper_me.append(me_p)
for k, (x, y, z, r) in enumerate(((2.5, -1.5, -.9, .3), (-2.4, 3.6, -.9, 2.4), (15, 8.4, 1.0, 3.5))):
    o = bpy.data.objects.new("helfer%d" % k, koerper_me[k % 3]); sc.collection.objects.link(o); o.location = (x, y, z); o.rotation_euler = (0, 0, r)

print("ok szene")
# ======================================================================  Ausruestung: Monoflosse, Kopfhaube, Nackengewicht, Lanyard
FLOSSE_M = mat("flosse", "1b2a3a", .25, Coat_Weight=.8)


def flossen_mesh():
    bm = bmesh.new(); r_ = []
    for i in range(13):
        k = i / 12; l = .05 + .78 * k
        br = .16 + .26 * math.sin(min(1, k * 1.25) * P / 2) - .06 * max(0, k - .85) / .15
        r_.append([bm.verts.new((sy * br, -l, (.012 * (1 - k)) * sz)) for sy, sz in ((-1, -1), (-1, 1), (1, 1), (1, -1))])
    for a, b_ in zip(r_, r_[1:]):
        for k in range(4):
            bm.faces.new((a[k], a[(k + 1) % 4], b_[(k + 1) % 4], b_[k]))
    bm.faces.new(r_[0][::-1]); bm.faces.new(r_[-1])
    me = bpy.data.meshes.new("flosse"); bm.to_mesh(me); bm.free(); me.materials.append(FLOSSE_M)
    for p in me.polygons:
        p.use_smooth = True
    return me


flosse = bpy.data.objects.new("flosse", flossen_mesh()); sc.collection.objects.link(flosse)
s_ = flosse.modifiers.new("s", "SUBSURF"); s_.levels = 1; s_.render_levels = 2
for dx in (-.07, .07):
    box("fussteil", (.1, .26, .1), (dx, .1, .02), NEOPREN, .04, seg=4, eltern=flosse)
bpy.context.view_layer.update()
kopf_b = AM.rig.data.bones["head"]
kh = AM.rig.matrix_world @ kopf_b.head_local; kt = AM.rig.matrix_world @ kopf_b.tail_local
kz = kh + (kt - kh) * .5
bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1, location=kz + Vector((0, .015, .015))); haube = bpy.context.object
haube.scale = (.102, .118, .122); haube.data.materials.append(NEOPREN)
bm = bmesh.new(); bm.from_mesh(haube.data)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y < -.55 and -.75 < v.co.z < .45], context="VERTS"); bm.to_mesh(haube.data); bm.free()
for p in haube.data.polygons:
    p.use_smooth = True
hals_b = AM.rig.data.bones["neck01"]; hh = AM.rig.matrix_world @ hals_b.head_local
bpy.ops.mesh.primitive_torus_add(major_radius=.072, minor_radius=.018, location=hh + Vector((0, 0, .03))); gew = bpy.context.object
gew.scale = (1, 1.15, 1); gew.data.materials.append(mat("blei", "2a2d31", .4, Metallic=.7))
bpy.context.view_layer.update()
PI = (AM.rig.matrix_world @ kopf_b.matrix_local @ Matrix.Translation((0, kopf_b.length, 0))).inverted()
haube.parent = AM.rig; haube.parent_type = "BONE"; haube.parent_bone = "head"; haube.matrix_parent_inverse = PI
PI2 = (AM.rig.matrix_world @ hals_b.matrix_local @ Matrix.Translation((0, hals_b.length, 0))).inverted()
gew.parent = AM.rig; gew.parent_type = "BONE"; gew.parent_bone = "neck01"; gew.matrix_parent_inverse = PI2
for o in AM.proxies:                                     # Haare unter der Haube
    if o.name.endswith("short02"):
        o.hide_render = True
lanyard = zyl("lanyard", .004, 1, (0, 0, 0), mat("lanyard", "f2f2f2", .6), v=6)
karab = box("karabiner", (.03, .05, .08), (0, 0, 0), STAHL, .01)

# ======================================================================  IK
AM.Z = {nm: leer("am_ik_" + nm) for nm in ("hand_L", "hand_R", "fuss_L", "fuss_R", "knie_L", "knie_R", "ell_L", "ell_R")}
AM.IK = {}
for bone, ziel, pol, pw in (("lowerarm02.L", "hand_L", "ell_L", 0), ("lowerarm02.R", "hand_R", "ell_R", 0),
                            ("lowerleg02.L", "fuss_L", "knie_L", -P / 2), ("lowerleg02.R", "fuss_R", "knie_R", -P / 2)):
    c = AM.rig.pose.bones[bone].constraints.new("IK"); c.target = AM.Z[ziel]; c.chain_count = 4
    c.pole_target = AM.Z[pol]; c.pole_angle = pw; AM.IK[ziel] = c


def rig_mat(H, Fc):
    Z = Vector(H).normalized(); Fc = Vector(Fc); Y = -(Fc - Z * Fc.dot(Z)).normalized(); X = Y.cross(Z)
    return Matrix((X, Y, Z)).transposed()


# ======================================================================  Ablauf (Story-Zeit ts)
T_ABT, T_LOS, T_FREI, T_UNTEN, T_WENDE, T_OBEN = 5.0, 6.5, 35.0, 130.0, 133.0, 262.0
Y_LINIE = .55


def tiefe(ts):
    """Tiefe des Beckens (positiv nach unten)"""
    if ts < T_ABT:
        return .25
    if ts < T_LOS:
        return .25 + 1.3 * ease((ts - T_ABT) / (T_LOS - T_ABT))
    if ts < T_FREI:
        return 1.55 + (29.0 - 1.55) * (ts - T_LOS) / (T_FREI - T_LOS)
    if ts < T_UNTEN:
        return 29.0 + (134.9 - 29.0) * (ts - T_FREI) / (T_UNTEN - T_FREI)
    if ts < T_WENDE + 1:
        return 134.9
    if ts < T_OBEN:
        return 134.9 - (134.9 - .9) * ease((ts - (T_WENDE + 1)) / (T_OBEN - T_WENDE - 1)) ** 1 if False else 134.9 - (134.9 - .9) * (ts - (T_WENDE + 1)) / (T_OBEN - T_WENDE - 1)
    return .9


def figur(ts):
    AM.zuruecksetzen()
    for c in AM.IK.values():
        c.influence = 1.0
    d = tiefe(ts)
    unten = Vector((0, 0, -1)); oben = Vector((0, 0, 1)); vorne = Vector((1, 0, 0))
    if ts < T_ABT:                                    # an der Oberflaeche, Gesicht nach unten, atmet
        H = vorne; Fc = Vector((0, 0, -1)); atm = .03 * math.sin(ts * 2.2)
        pel = Vector((-.6, Y_LINIE + 1.6, -.25 + atm))
    elif ts < T_LOS:                                  # Abtauchen: Kopf nach unten drehen
        k = ease((ts - T_ABT) / (T_LOS - T_ABT))
        H = vorne.lerp(unten, k).normalized(); Fc = Vector((0, 0, -1)).lerp(Vector((-1, 0, 0)), k).normalized()
        pel = Vector((-.6 * (1 - k), Y_LINIE + 1.6 * (1 - k), -d))
    elif ts < T_WENDE:                                # runter
        H = unten; Fc = Vector((-1, 0, 0)); pel = Vector((0, Y_LINIE, -d))
    elif ts < T_WENDE + 1.0:                          # Wende an der Platte
        k = ease((ts - T_WENDE) / 1.0)
        H = Matrix.Rotation(P * k, 3, Vector((0, 1, 0))) @ unten; Fc = Matrix.Rotation(P * k, 3, Vector((0, 1, 0))) @ Vector((-1, 0, 0))
        pel = Vector((0, Y_LINIE, -d + .9 * k))
    elif ts < T_OBEN:
        H = oben; Fc = Vector((1, 0, 0)); pel = Vector((0, Y_LINIE, -d + .9))
    else:                                             # aufgetaucht: Kopf ueber Wasser
        H = oben; Fc = Vector((0, 1, 0)); pel = Vector((0, Y_LINIE + 1.6, -.5 + .04 * math.sin(ts * 2)))
    H = H.normalized(); Fc = (Fc - H * Fc.dot(H)).normalized(); S = H.cross(Fc).normalized()
    rq = rig_mat(H, Fc).to_quaternion()
    AM.rig.rotation_mode = "QUATERNION"; AM.rig.rotation_quaternion = rq
    AM.rig.location = pel - rq.to_matrix() @ (AM.PEL * AM.SK)
    # Beine: Delfinkick (ausser im freien Fall / an der Oberflaeche)
    kickt = (T_LOS <= ts < T_FREI) or (T_WENDE + 1 <= ts < T_OBEN - .5)
    kick = .2 * math.sin(2 * P * ts / 1.05) if kickt else 0.0
    if ts < T_ABT or ts >= T_OBEN:
        kick = .06 * math.sin(ts * 3)
    fuss_m = pel - H * .9 + Fc * kick
    for sd, s_ in (("L", 1), ("R", -1)):
        AM.Z["fuss_" + sd].location = fuss_m + S * (.07 * s_)
        AM.Z["knie_" + sd].location = pel - H * .45 + Fc * 1.5 + S * (.25 * s_)
        AM.Z["ell_" + sd].location = pel + H * .5 - Fc * .5 + S * (1.0 * s_)
    # Arme
    frei = T_FREI <= ts < T_UNTEN - .6
    jubel = ease((ts - (T_OBEN + .8)) / .6)
    for sd, s_ in (("L", 1), ("R", -1)):
        if frei or ts < T_ABT:
            h = pel + H * .05 + S * (.3 * s_) + Fc * .05
        else:
            h = pel + H * 1.28 + S * (.03 * s_) + Fc * .04
        AM.Z["hand_" + sd].location = h
    if T_UNTEN - .6 <= ts < T_WENDE + .3:                 # rechte Hand greift den Tag
        k = ease((ts - (T_UNTEN - .6)) / .8)
        ziel = TAGS[2].location + Vector((0, 0, .05))
        AM.Z["hand_R"].location = AM.Z["hand_R"].location.lerp(ziel, k)
    if ts >= T_OBEN:                                      # aufgetaucht: Tag hoch
        AM.Z["hand_R"].location = pel + H * (.9 + .5 * jubel) + S * -.35 + Fc * .25
        AM.Z["hand_L"].location = pel + H * .35 + S * .4 + Fc * .3
    # Tag in der Hand nach dem Greifen
    if ts >= T_WENDE:
        hb = AM.rig.matrix_world @ AM.rig.pose.bones["lowerarm02.R"].tail
        TAGS[2].location = hb
    else:
        TAGS[2].location = (0, -.3, PLATTE_Z - .05)
    AM.dreh("neck01", x=(-.55 if ts < T_ABT else (.2 if ts < T_OBEN else 0)))
    for sd in ("L", "R"):
        for ff in range(2, 6):
            for g in (1, 2, 3):
                AM.dreh(f"finger{ff}-{g}.{sd}", x=.2 if sd == "L" or ts < T_UNTEN - .6 else .9)
    bpy.context.view_layer.update()
    # Monoflosse an den Fuessen
    fl = (AM.rig.matrix_world @ AM.rig.pose.bones["foot.L"].head + AM.rig.matrix_world @ AM.rig.pose.bones["foot.R"].head) / 2
    richt = (-H + Fc * (kick * 1.8)).normalized()
    nrm = Fc.normalized(); sei = richt.cross(nrm).normalized(); nrm = sei.cross(richt)
    flosse.matrix_world = Matrix.Translation(fl) @ Matrix((sei, -richt, nrm)).transposed().to_4x4()
    # Lanyard vom linken Handgelenk zum Seil
    hw = AM.rig.matrix_world @ AM.rig.pose.bones["lowerarm02.L"].tail
    kpos = Vector((0, .03, hw.z - .2))
    karab.location = kpos
    dv_ = kpos - hw; lanyard.location = (hw + kpos) / 2; lanyard.scale = (1, 1, max(.01, dv_.length))
    lanyard.rotation_mode = "QUATERNION"; lanyard.rotation_quaternion = dv_.to_track_quat("Z", "Y")
    lanyard.hide_render = ts < T_LOS or ts >= T_OBEN; karab.hide_render = lanyard.hide_render
    oc.time = ts


def becken():
    nk = AM.rig.matrix_world @ AM.rig.pose.bones["neck01"].head
    return (AM.rig.matrix_world @ AM.PEL) * .55 + nk * .45


# ======================================================================  Kamera (+ Lampe des Kameramanns)
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam
cam.data.clip_start = .03; cam.data.clip_end = 6000; cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
cam.data.dof.use_dof = True
bpy.ops.object.light_add(type="SPOT", location=(0, 0, 0)); lampe = bpy.context.object; lampe.data.energy = 0; lampe.data.spot_size = 1.0
lampe.data.shadow_soft_size = .3; lampe.data.color = (.9, .95, 1)
PZ = PLATTE_Z
SZ = [
    (0.00, 1.50, 130.2, 130.8, "P", (1.6, -1.4, PZ + .6), (1.5, -1.5, PZ + .7), "B", "B", 26),                # Aufhaenger: Platte, greift den Tag
    (1.50, 4.00, 20.0, 23.0, "B+", (.6, -.8, -7), (.6, -.8, -7.5), "B", "B", 22),                             # von unten: Silhouette vor dem Licht
    (4.00, 5.00, 60.0, 60.0, "P", (.3, -.4, -20), (.3, -.4, -34), (0, 0, -140), (0, 0, -140), 22),             # am Seil runter ins Dunkle
    (5.00, 6.50, 1.0, 1.5, "P", (-25, -32, 4), (-22, -29, 4.5), (0, 40, 2), (0, 40, 2), 26),                  # Limassol: Boje, Boot, Kueste
    (6.50, 9.40, 3.0, 6.4, "P", (2.0, 5.6, 1.0), (1.8, 5.2, .8), "B", "B", 28),                               # letzter Atemzug, abtauchen
    (9.40, 12.00, 14.0, 16.6, "B+", (2.8, -1.2, .3), (2.8, -1.4, .3), "B", "B", 26),                         # Delfinkick mit Monoflosse
    (12.00, 15.30, 36.0, 39.3, "B+", (-2.5, -1.5, -.5), (-2.6, -1.4, -.5), "B", "B", 26),                    # freier Fall ab 30 m
    (15.30, 16.40, 80.0, 81.1, "B+", (.4, .5, 5), (.4, .5, 5.5), "B", "B", 24),                              # das Licht schwindet
    (16.40, 18.90, 110.0, 112.5, "B+", (-2.2, -1.8, -1.0), (-2.3, -1.9, -1.1), "B", "B", 30),                     # Druck von allen Seiten
    (18.90, 21.60, 129.2, 131.9, "P", (2.2, -1.8, PZ - .3), (2.0, -1.9, PZ - .2), "B", "B", 26),             # 136 m: Tag
    (21.60, 23.20, 230.0, 231.6, "B+", (.5, -.6, -6), (.5, -.6, -6.5), "B", "B", 22),                        # wieder hoch zum Licht
    (23.20, 27.00, 262.0, 265.8, "P", (1.6, 5.4, .4), (2.6, 7.2, 1.3), "B", "B", 28),                    # aufgetaucht, Tag hoch
]
SZ = [s if s[4] == "B+" else s[:4] + ("P",) + s[5:] for s in SZ]


def zustand(t):
    for s in SZ:
        if s[0] <= t < s[1]:
            break
    k = (t - s[0]) / (s[1] - s[0])
    ts = s[2] + (s[3] - s[2]) * k
    k = ease(k) * .7 + k * .3
    figur(ts)
    bk = becken()
    pos = bk + lerpv(s[5], s[6], k) if s[4] == "B+" else lerpv(s[5], s[6], k)
    ziel = bk if s[7] == "B" else lerpv(s[7], s[8], k)
    cam.location = pos; d = ziel - pos; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = s[9]; cam.data.dof.focus_distance = min(d.length, 60); cam.data.dof.aperture_fstop = 4 if d.length < 8 else 16
    zit = .008
    cam.location += Vector((zit * math.sin(t * 7.3), zit * math.cos(t * 5.1), zit * math.sin(t * 9.7)))
    # Lampe: nur unter Wasser, staerker in der Tiefe
    tief = max(0, -pos.z)
    lampe.location = pos + Vector((.2, 0, .3)); lampe.rotation_euler = cam.rotation_euler
    lampe.data.energy = 0 if pos.z > -1 else 8 + 1.2 * tief; lampe.data.shadow_soft_size = .8


# ======================================================================  Plankton zuletzt (viele Objekte)
# Schwebeteilchen (Plankton) entlang des Tauchwegs
SCHNEE_M = emis("plankton", "cfe8ff", .6)
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=.008, location=(0, -900, -50)); fl = bpy.context.object; fl.data.materials.append(SCHNEE_M)
rp = random.Random(6)
for i in range(5000):
    o = bpy.data.objects.new("p%04d" % i, fl.data); sc.collection.objects.link(o)
    o.location = (rp.uniform(-6, 6), rp.uniform(-6, 6), rp.uniform(-140, -1)); s_ = rp.uniform(.6, 1.8); o.scale = (s_, s_, s_)
os.makedirs(A.ordner, exist_ok=True)
N = int(round(D * A.fps))
liste = [int(round(float(x) * A.fps)) for x in A.nur.split(",")] if A.nur else list(range(A.start, N))
for f in liste:
    pfad = os.path.join(A.ordner, f"tauchen_{f:04d}.png")
    if os.path.exists(pfad) and not A.nur:
        continue
    zustand(f / A.fps); bpy.context.view_layer.update(); zustand(f / A.fps)
    sc.render.filepath = pfad
    bpy.ops.render.render(write_still=True); print("FERTIG", pfad, flush=True)
