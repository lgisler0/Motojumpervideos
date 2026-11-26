"""Wingsuit-Rekord Sebastian Alvarez (22.3.2025, Whiteville TN): Absprung 12640 m, 550 km/h, 53,45 km, 11:01 (FAI/Red Bull). Realistischer Stil.
python3 wingsuit3d.py <ordner> [--nur t1,t2] [--start i] [--samples n]"""
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


# ======================================================================  Flieger (zuerst)
import mensch_echt as ME
LOGO = ME.logo_bild(os.path.join(HIER, "_logo_norda.png"), "NORDA", farbe=(1, 1, 1))
SA = ME.mensch("alvarez", 85, 1.0, .4, .6, .25, haut="caucasian", haare="short02", braue="eyebrow001", haarfarbe="1a120c")
ME.trikot(SA, "lang", "tights", "1b1f26", "1b1f26", brust=LOGO, brust_mass=(.16, .08), bein=LOGO)
for o in SA.huellen:
    if "versatz" in o.modifiers:
        o.modifiers["versatz"].strength = .02 if o.name.endswith("_hemd") else .012
    for md in o.modifiers:
        if md.type == "SUBSURF":
            md.render_levels = 2
hoehe = max(v.z for v in SA.EV); SA.SK = 1.78 / hoehe; SA.rig.scale = (SA.SK,) * 3
SA.PEL = SA.rig.data.bones["upperleg01.L"].head_local.copy(); SA.PEL.x = 0
print("ok mensch")

# ======================================================================  Materialien, Himmel, Sonne
SCHWARZ = mat("schwarzlack", "0d0d0f", .4, Coat_Weight=.3)
STAHL = pbr("stahl", "Metal012", 6, rau_mul=.6, rau_add=.15, metal=1.0)
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; nt = w.node_tree
env = nt.nodes.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(os.path.join(ASSET, "tag.hdr"))
nt.links.new(env.outputs[0], nt.nodes["Background"].inputs[0]); nt.nodes["Background"].inputs[1].default_value = 1.0
bpy.ops.object.light_add(type="SUN", rotation=(math.radians(40), 0, math.radians(-50))); sonne = bpy.context.object
sonne.data.energy = 4.6; sonne.data.angle = math.radians(.8); sonne.data.color = (1, .97, .92)
sc.render.film_transparent = False

# ======================================================================  Boden (Felder in Tennessee) und Wolken
def felder_mat():
    m = bpy.data.materials.new("felder"); m.use_nodes = True; nt_ = m.node_tree; n = nt_.nodes; l = nt_.links; b = n["Principled BSDF"]
    tc = n.new("ShaderNodeTexCoord")
    vo = n.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = .0025; vo.voronoi_dimensions = "2D"; l.new(tc.outputs["Object"], vo.inputs["Vector"])
    rp = n.new("ShaderNodeValToRGB"); l.new(vo.outputs["Color"], rp.inputs[0])
    els = rp.color_ramp.elements
    els[0].color = (*hexf("4e6b2a"), 1); els[1].color = (*hexf("8a7a4a"), 1)
    for pos, c in ((.25, "6f8a3a"), (.45, "a08b5a"), (.62, "3f5a26"), (.8, "c2b080")):
        e = els.new(pos); e.color = (*hexf(c), 1)
    rp.color_ramp.interpolation = "CONSTANT"
    vo2 = n.new("ShaderNodeTexVoronoi"); vo2.inputs["Scale"].default_value = .0025; vo2.feature = "DISTANCE_TO_EDGE"; l.new(tc.outputs["Object"], vo2.inputs["Vector"])
    rand = n.new("ShaderNodeMath"); rand.operation = "LESS_THAN"; rand.inputs[1].default_value = .012; l.new(vo2.outputs["Distance"], rand.inputs[0])
    mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; l.new(rand.outputs[0], mx.inputs[0]); l.new(rp.outputs[0], mx.inputs[6]); mx.inputs[7].default_value = (*hexf("2c3a1c"), 1)
    no = n.new("ShaderNodeTexNoise"); no.inputs["Scale"].default_value = .0004; l.new(tc.outputs["Object"], no.inputs["Vector"])
    mx2 = n.new("ShaderNodeMix"); mx2.data_type = "RGBA"; mx2.blend_type = "MULTIPLY"; mx2.inputs[0].default_value = .5
    l.new(mx.outputs[2], mx2.inputs[6]); l.new(no.outputs["Color"], mx2.inputs[7])
    l.new(mx2.outputs[2], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = .95
    return m


bpy.ops.mesh.primitive_plane_add(size=400000, location=(60000, 0, 0)); boden = bpy.context.object; boden.data.materials.append(felder_mat())
# Fluss (Mississippi-artig, weit weg)
bpy.ops.mesh.primitive_plane_add(size=1, location=(-15000, 22000, 2)); fl = bpy.context.object; fl.scale = (900, 120000, 1); fl.rotation_euler = (0, 0, .4)
fl.data.materials.append(mat("fluss", "3a4a52", .08, Coat_Weight=1))


def wolken_mat(name, skala, schwelle, dicht=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; nn_ = m.node_tree.nodes; ln_ = m.node_tree.links
    noi = nn_.new("ShaderNodeTexNoise"); noi.inputs["Scale"].default_value = skala; noi.inputs["Detail"].default_value = 8; noi.inputs["Roughness"].default_value = .62
    tcn = nn_.new("ShaderNodeTexCoord"); ln_.new(tcn.outputs["Object"], noi.inputs["Vector"])
    rrn = nn_.new("ShaderNodeMapRange"); rrn.inputs[1].default_value = schwelle; rrn.inputs[2].default_value = schwelle + .14; rrn.inputs[4].default_value = dicht
    ln_.new(noi.outputs["Fac"], rrn.inputs[0])
    trn = nn_.new("ShaderNodeBsdfTransparent"); mxn = nn_.new("ShaderNodeMixShader"); ln_.new(rrn.outputs[0], mxn.inputs[0])
    bn = nn_["Principled BSDF"]; bn.inputs["Base Color"].default_value = (1, 1, 1, 1); bn.inputs["Roughness"].default_value = 1
    bn.inputs["Subsurface Weight"].default_value = .7; bn.inputs["Subsurface Radius"].default_value = (1, 1, 1)
    ln_.new(trn.outputs[0], mxn.inputs[1]); ln_.new(bn.outputs[0], mxn.inputs[2]); ln_.new(mxn.outputs[0], nn_["Material Output"].inputs["Surface"])
    return m


WOLKE1 = wolken_mat("cumulus", .00012, .5)
WOLKE2 = wolken_mat("cirrus", .00004, .55, .55)
for z, m_, rz in ((2400, WOLKE1, 0), (2700, WOLKE1, 1.3), (8200, WOLKE2, .7)):
    bpy.ops.mesh.primitive_plane_add(size=300000, location=(60000, 0, z)); o = bpy.context.object; o.data.materials.append(m_); o.rotation_euler = (0, 0, rz)
# einzelne Wolkenbaenke nahe der Flugbahn (fuer Geschwindigkeitsgefuehl)
PUFF_M = wolken_mat("puff", .004, .45)
rw = random.Random(8); PUFFS = []
for i in range(40):
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0)); o = bpy.context.object; o.name = "puff%02d" % i
    o.data.materials.append(PUFF_M); s_ = rw.uniform(300, 900); o.scale = (s_, s_ * .6, 1); o.rotation_euler = (rw.uniform(-.2, .2), rw.uniform(-.2, .2), rw.uniform(0, 3))
    PUFFS.append((o, rw.uniform(0, 1), rw.uniform(-1, 1), rw.uniform(-1, 1)))

# ======================================================================  Flugzeug (zweimotorige Turboprop, Tuer offen)
WEISS = mat("rumpf", "eef0f2", .3, Coat_Weight=.6)
BLAU = mat("streifen", "1d3f9a", .35, Coat_Weight=.5)


def rumpf_mesh():
    bm = bmesh.new(); r_ = []
    n = 30
    for i in range(n + 1):
        k = i / n; x = -6 + 12 * k
        r = .85 * min(1, (k / .14) ** .5) * (1 - max(0, (k - .62) / .38) ** 1.3 * .82) + .05
        zc = .35 * max(0, (k - .62) / .38) ** 2
        r_.append([bm.verts.new((x, r * math.cos(a), zc + r * .95 * math.sin(a))) for a in [2 * P * j / 16 for j in range(16)]])
    for a, b_ in zip(r_, r_[1:]):
        for j in range(16):
            bm.faces.new((a[j], a[(j + 1) % 16], b_[(j + 1) % 16], b_[j]))
    bm.faces.new(r_[0][::-1]); bm.faces.new(r_[-1])
    me = bpy.data.meshes.new("rumpf"); bm.to_mesh(me); bm.free(); me.materials.append(WEISS)
    for p in me.polygons:
        p.use_smooth = True
    return me


flug = bpy.data.objects.new("flugzeug", rumpf_mesh()); sc.collection.objects.link(flug)
s_ = flug.modifiers.new("s", "SUBSURF"); s_.levels = 1; s_.render_levels = 2
box("fluegel", (2.0, 13.0, .22), (.8, 0, -.35), WEISS, .08, eltern=flug)
box("hoehenleitwerk", (1.2, 4.6, .12), (-5.3, 0, .55), WEISS, .05, eltern=flug)
box("seitenleitwerk", (1.8, .14, 1.8), (-5.2, 0, 1.3), BLAU, .05, rot=(0, -.35, 0), eltern=flug)
box("streifen_l", (9, .02, .14), (.5, .86, .05), BLAU, 0, eltern=flug)
box("streifen_r", (9, .02, .14), (.5, -.86, .05), BLAU, 0, eltern=flug)
for yy in (-2.6, 2.6):
    zyl("gondel", .42, 2.6, (1.3, yy, -.25), WEISS, rot=(0, P / 2, 0), eltern=flug)
    zyl("prop", 1.15, .02, (2.65, yy, -.25), mat("propeller", "222222", .5, Alpha=.25), rot=(0, P / 2, 0), eltern=flug)
for k in range(5):
    box("fenster", (.28, .02, .22), (2.6 - k * .75, -.84 * (1 if k % 2 else 1), .25), mat("fenster", "1c2a36", .05, Coat_Weight=1) if not bpy.data.materials.get("fenster") else bpy.data.materials["fenster"], .03, eltern=flug)
box("tuer_offen", (1.0, .05, 1.15), (-2.1, .86, -.05), mat("innen", "15171b", .8), .02, eltern=flug)
box("cockpitfenster", (.6, 1.2, .3), (4.9, 0, .45), mat("fenster", "1c2a36", .05) if not bpy.data.materials.get("fenster") else bpy.data.materials["fenster"], .1, rot=(0, .5, 0), eltern=flug)

# Verkehrsflugzeug weit unten (in Reisehoehe)
JET = bpy.data.objects.new("jet", rumpf_mesh()); sc.collection.objects.link(JET); JET.scale = (3.4, 2.4, 2.4)
box("jet_fluegel", (1.4, 11, .12), (0, 0, -.4), WEISS, .05, rot=(0, 0, .35), eltern=JET)
SPUR_M = wolken_mat("kondensstreifen", .02, .3)
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0)); spur = bpy.context.object; spur.scale = (1800, 18, 1); spur.data.materials.append(SPUR_M)

# ======================================================================  Jetstream: lange, schnelle Windstreifen
STREIF_M = bpy.data.materials.new("windstreifen"); STREIF_M.use_nodes = True; ns_ = STREIF_M.node_tree.nodes; ls_ = STREIF_M.node_tree.links
tcs = ns_.new("ShaderNodeTexCoord"); grs = ns_.new("ShaderNodeTexGradient"); grs.gradient_type = "QUADRATIC_SPHERE"
mps = ns_.new("ShaderNodeMapping"); mps.inputs["Scale"].default_value = (1.0, 2.0, 1); mps.inputs["Location"].default_value = (0, 0, 0)
ls_.new(tcs.outputs["Generated"], mps.inputs[0])
sep_ = ns_.new("ShaderNodeSeparateXYZ"); ls_.new(tcs.outputs["Generated"], sep_.inputs[0])
pp = ns_.new("ShaderNodeMath"); pp.operation = "PINGPONG"; pp.inputs[1].default_value = .5; ls_.new(sep_.outputs["Y"], pp.inputs[0])
px_ = ns_.new("ShaderNodeMath"); px_.operation = "PINGPONG"; px_.inputs[1].default_value = .5; ls_.new(sep_.outputs["X"], px_.inputs[0])
mm = ns_.new("ShaderNodeMath"); mm.operation = "MULTIPLY"; ls_.new(pp.outputs[0], mm.inputs[0]); ls_.new(px_.outputs[0], mm.inputs[1])
mm2 = ns_.new("ShaderNodeMath"); mm2.operation = "MULTIPLY"; mm2.inputs[1].default_value = 1.6; ls_.new(mm.outputs[0], mm2.inputs[0])
ems = ns_.new("ShaderNodeEmission"); ems.inputs["Color"].default_value = (.85, .93, 1, 1); ems.inputs["Strength"].default_value = 1.2
trs = ns_.new("ShaderNodeBsdfTransparent"); mxs = ns_.new("ShaderNodeMixShader"); ls_.new(mm2.outputs[0], mxs.inputs[0])
ls_.new(trs.outputs[0], mxs.inputs[1]); ls_.new(ems.outputs[0], mxs.inputs[2]); ls_.new(mxs.outputs[0], ns_["Material Output"].inputs["Surface"])
STREIFEN = []
rs = random.Random(12)
for i in range(70):
    bpy.ops.mesh.primitive_plane_add(size=1); o = bpy.context.object; o.name = "streif%02d" % i
    o.scale = (rs.uniform(25, 60), rs.uniform(.15, .45), 1); o.data.materials.append(STREIF_M)
    STREIFEN.append((o, rs.uniform(0, 1), rs.uniform(-1, 1), rs.uniform(-1, 1), rs.uniform(.6, 1.4)))
print("ok szene")
# ======================================================================  Ausruestung: Helm, Maske, Sauerstoff, Container, Hoehenmesser
bpy.context.view_layer.update()
kopf_b = SA.rig.data.bones["head"]; sp_b = SA.rig.data.bones["spine03"]
kh = SA.rig.matrix_world @ kopf_b.head_local; kt = SA.rig.matrix_world @ kopf_b.tail_local; kz = kh + (kt - kh) * .5
HELM = mat("helm", "e8e8ea", .2, Coat_Weight=1.0)
bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1, location=kz + Vector((0, .01, .01))); helm = bpy.context.object
helm.scale = (.13, .145, .145); helm.data.materials.append(HELM)
for p in helm.data.polygons:
    p.use_smooth = True
bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1, location=kz + Vector((0, -.06, .0))); visier = bpy.context.object
visier.scale = (.115, .1, .07); visier.data.materials.append(mat("visier", "d07a1a", .03, metal=1.0, Coat_Weight=1))
maske = box("maske", (.09, .06, .07), kz + Vector((0, -.12, -.09)), mat("maske", "2a2d31", .5), .025, seg=3)
SCHLAUCH = mat("schlauch", "1565c0", .5)
sp_h = SA.rig.matrix_world @ sp_b.head_local
flasche = zyl("sauerstoff", .05, .32, sp_h + Vector((-.1, -.2, .05)), mat("flasche", "c8ccd0", .3, metal=.8), rot=(0, 0, 0))
container = box("container", (.36, .16, .5), sp_h + Vector((0, .2, 0)), mat("container", "1b1f26", .6, Sheen_Weight=.3), .05, seg=4)
rohr("schlauch", kz + Vector((0, -.14, -.12)), sp_h + Vector((-.1, -.2, .2)), .012, SCHLAUCH)
for o, bone_ in ((helm, kopf_b), (visier, kopf_b), (maske, kopf_b), (flasche, sp_b), (container, sp_b)):
    pass
bpy.context.view_layer.update()
for o, bone_ in ((helm, kopf_b), (visier, kopf_b), (maske, kopf_b), (flasche, sp_b), (container, sp_b), (bpy.data.objects["schlauch"], sp_b)):
    PI = (SA.rig.matrix_world @ bone_.matrix_local @ Matrix.Translation((0, bone_.length, 0))).inverted()
    o.parent = SA.rig; o.parent_type = "BONE"; o.parent_bone = bone_.name; o.matrix_parent_inverse = PI
for o in SA.proxies:
    if o.name.endswith("short02"):
        o.hide_render = True

# Wingsuit-Flaechen (werden jedes Bild neu aus den Knochen gebaut)
ANZUG = bpy.data.materials.new("anzug"); ANZUG.use_nodes = True; na_ = ANZUG.node_tree.nodes; la_ = ANZUG.node_tree.links
tca = na_.new("ShaderNodeTexCoord"); sepa = na_.new("ShaderNodeSeparateXYZ"); la_.new(tca.outputs["UV"], sepa.inputs[0])
ppa = na_.new("ShaderNodeMath"); ppa.operation = "PINGPONG"; ppa.inputs[1].default_value = .17; la_.new(sepa.outputs["X"], ppa.inputs[0])
lta = na_.new("ShaderNodeMath"); lta.operation = "LESS_THAN"; lta.inputs[1].default_value = .02; la_.new(ppa.outputs[0], lta.inputs[0])
mxa = na_.new("ShaderNodeMix"); mxa.data_type = "RGBA"; mxa.inputs[6].default_value = (*hexf("1b1f26"), 1); mxa.inputs[7].default_value = (*hexf("c6ff1a"), 1)
la_.new(lta.outputs[0], mxa.inputs[0]); la_.new(mxa.outputs[2], na_["Principled BSDF"].inputs["Base Color"])
na_["Principled BSDF"].inputs["Roughness"].default_value = .55; na_["Principled BSDF"].inputs["Sheen Weight"].default_value = .5
NU, NV = 10, 6


def flaeche(name):
    bm = bmesh.new(); vs = [[bm.verts.new((0, 0, 0)) for _ in range(NU + 1)] for _ in range(NV + 1)]
    for j in range(NV):
        for i in range(NU):
            bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(ANZUG)
    uv = me.uv_layers.new()
    for p in me.polygons:
        p.use_smooth = True
        for li in p.loop_indices:
            vi = me.loops[li].vertex_index; uv.data[li].uv = ((vi % (NU + 1)) / NU, (vi // (NU + 1)) / NV)
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o)
    so = o.modifiers.new("d", "SOLIDIFY"); so.thickness = .012
    return o


FL_L, FL_R, FL_B = flaeche("fluegel_l"), flaeche("fluegel_r"), flaeche("beinfluegel")


def patch(o, a0, a1, b0, b1, wolbung, n_w, t):
    """bilineare Flaeche zwischen Kante a0->a1 und b0->b1, gewoelbt entlang n_w (Luftdruck), leichtes Flattern"""
    co = []
    for j in range(NV + 1):
        v = j / NV
        for i in range(NU + 1):
            u = i / NU
            pa = a0.lerp(a1, u); pb = b0.lerp(b1, u)
            p = pa.lerp(pb, v) + n_w * (wolbung * math.sin(v * P) * math.sin(min(1, u * 1.2) * P / 2 + .3)
                                         + .008 * math.sin(t * 40 + u * 9 + v * 5) * v)
            co += [p.x, p.y, p.z]
    o.data.vertices.foreach_set("co", co); o.data.update()


# ======================================================================  IK
SA.Z = {nm: leer("sa_ik_" + nm) for nm in ("hand_L", "hand_R", "fuss_L", "fuss_R", "knie_L", "knie_R", "ell_L", "ell_R")}
SA.IK = {}
for bone, ziel, pol, pw in (("lowerarm02.L", "hand_L", "ell_L", 0), ("lowerarm02.R", "hand_R", "ell_R", 0),
                            ("lowerleg02.L", "fuss_L", "knie_L", -P / 2), ("lowerleg02.R", "fuss_R", "knie_R", -P / 2)):
    c = SA.rig.pose.bones[bone].constraints.new("IK"); c.target = SA.Z[ziel]; c.chain_count = 4
    c.pole_target = SA.Z[pol]; c.pole_angle = pw; SA.IK[ziel] = c


def rig_mat(H, Fc):
    Z = Vector(H).normalized(); Fc = Vector(Fc); Y = -(Fc - Z * Fc.dot(Z)).normalized(); X = Y.cross(Z)
    return Matrix((X, Y, Z)).transposed()


# ======================================================================  Flugbahn (Story-Zeit ts, 0.1 s Schritte vorausberechnet)
T_EXIT, T_TOP, T_AUF = 1.0, 31.0, 661.3
Z0 = 12640.0; V_FLUGZEUG = 75.0


def v_horiz(ts):
    if ts < T_EXIT:
        return V_FLUGZEUG
    if ts < T_TOP:
        return 55 + (152.8 - 55) * ease((ts - T_EXIT) / (T_TOP - T_EXIT))
    return 152.8 - 86 * ease((ts - T_TOP) / 380)


def v_sink(ts):
    if ts < T_EXIT:
        return 0.0
    return 14 + 34 * math.exp(-((ts - 9) / 6) ** 2) + 6 * (1 - ease((ts - 40) / 200))


BAHN = []
x, z = 0.0, Z0
for i in range(0, 7000):
    ts = i * .1
    BAHN.append((x, z)); x += v_horiz(ts) * .1; z -= v_sink(ts) * .1
k_s = (Z0 - 900) / (Z0 - BAHN[int(T_AUF * 10)][1])          # Sinkrate so skalieren, dass er bei 900 m die Kappe oeffnet
k_x = 53448.5 / BAHN[int(T_AUF * 10)][0]
BAHN = [(bx * k_x, Z0 - (Z0 - bz) * k_s) for (bx, bz) in BAHN]
print("Distanz bis Oeffnung km", round(BAHN[int(T_AUF * 10)][0] / 1000, 2))


def bahn(ts):
    i = max(0, min(len(BAHN) - 2, int(ts * 10))); k = ts * 10 - i
    a, b_ = BAHN[i], BAHN[i + 1]
    return Vector((a[0] + (b_[0] - a[0]) * k, 0, a[1] + (b_[1] - a[1]) * k))


def flugzeug_pos(ts):
    return Vector((V_FLUGZEUG * ts, 0, Z0 + 1.2 + .5 * max(0, ts - T_EXIT) ** 1.5))


# Fallschirm (Flaechenschirm) - erscheint bei T_AUF
KAPPE = bpy.data.objects.new("kappe", None); sc.collection.objects.link(KAPPE)
KM = mat("kappe", "d0141a", .5, Sheen_Weight=.4); KM2 = mat("kappe2", "f2f2f2", .5, Sheen_Weight=.4)
for i in range(9):
    yy = -4.0 + i
    a = (i - 4) / 4
    box("zelle%d" % i, (2.6, .98, .45), (0, yy * .98, 7.2 - 1.2 * a * a), KM if i % 2 else KM2, .12, seg=3, rot=(-.25 * a, 0, 0), eltern=KAPPE)
LEINEN = []
for i in range(8):
    LEINEN.append(zyl("leine%d" % i, .004, 1, (0, 0, 0), mat("leine", "dddddd", .6) if not bpy.data.materials.get("leine") else bpy.data.materials["leine"], v=6))


def figur(ts):
    SA.zuruecksetzen()
    for c in SA.IK.values():
        c.influence = 1.0
    t_ = ts
    if ts < T_EXIT:                                            # in der Tuer kauern
        fp = flugzeug_pos(ts); pel = fp + Vector((-2.1, .55, -.15)); H = Vector((.25, .3, 1)); Fc = Vector((0, 1, 0))
        flieg = 0.0
    else:
        pel = bahn(ts)
        if ts < T_EXIT + 1.0:                                  # Abflug aus der Tuer
            k = ease((ts - T_EXIT) / 1.0)
            fp = flugzeug_pos(T_EXIT); start = fp + Vector((-2.1, .55, -.15))
            pel = start.lerp(pel, k) + Vector((0, 1.5 * k, 0))
            flieg = k
        else:
            flieg = 1.0
        vel = (bahn(ts + .1) - bahn(ts - .1)).normalized()
        if ts > T_AUF:                                        # unter dem Schirm: aufrecht, Blick nach vorn
            k = ease((ts - T_AUF) / 1.5)
            H = vel.lerp(Vector((0, 0, 1)), k).normalized(); Fc = Vector((0, 0, -1)).lerp(Vector((1, 0, 0)), k).normalized()
            flieg = 1 - k
        else:
            pitch = Matrix.Rotation(math.radians(-8), 3, Vector((0, 1, 0)))
            H = (pitch @ vel).normalized(); Fc = Vector((0, 0, -1))
            if ts < T_EXIT + 1.0:
                H = Vector((.25, .3, 1)).lerp(H, flieg).normalized(); Fc = Vector((0, 1, 0)).lerp(Fc, flieg).normalized()
            # leichtes Rollen
            roll = .12 * math.sin(ts * .9)
            Fc = Matrix.Rotation(roll, 3, H) @ Fc
    H = H.normalized(); Fc = (Fc - H * Fc.dot(H)).normalized(); S = H.cross(Fc).normalized()
    rq = rig_mat(H, Fc).to_quaternion()
    SA.rig.rotation_mode = "QUATERNION"; SA.rig.rotation_quaternion = rq
    SA.rig.location = pel - rq.to_matrix() @ (SA.PEL * SA.SK)
    # Glieder: kauern -> Flugpose (Arme seitlich/hinten, Beine gespreizt)
    kauer = {"hand_L": pel + H * .5 + Fc * .35 + S * .3, "hand_R": pel + H * .5 + Fc * .35 - S * .3,
             "fuss_L": pel - H * .5 + Fc * .25 + S * .15, "fuss_R": pel - H * .5 + Fc * .25 - S * .15}
    fliegen = {"hand_L": pel + H * .32 + S * .8 - Fc * .05, "hand_R": pel + H * .32 - S * .8 - Fc * .05,
               "fuss_L": pel - H * .94 + S * .28, "fuss_R": pel - H * .94 - S * .28}
    schirm = {"hand_L": pel + H * 1.2 + S * .35, "hand_R": pel + H * 1.2 - S * .35, "fuss_L": pel - H * .92 + S * .1, "fuss_R": pel - H * .92 - S * .1}
    for nm in kauer:
        p = kauer[nm].lerp(fliegen[nm], flieg) if ts <= T_AUF else schirm[nm].lerp(fliegen[nm], flieg)
        SA.Z[nm].location = p + Fc * (.015 * math.sin(ts * 23 + len(nm)))
    for sd, s_ in (("L", 1), ("R", -1)):
        SA.Z["knie_" + sd].location = pel - H * .45 + Fc * 1.5 + S * (.3 * s_)
        SA.Z["ell_" + sd].location = pel + H * .2 - Fc * 1.2 + S * (.9 * s_)
    SA.dreh("neck01", x=-.6 * flieg)
    for sd in ("L", "R"):
        for ff in range(2, 6):
            for g in (1, 2, 3):
                SA.dreh(f"finger{ff}-{g}.{sd}", x=.15)
    bpy.context.view_layer.update()
    # Flaechen aus den Knochen
    def bw(nm, kopf=True):
        pb = SA.rig.pose.bones[nm]; return SA.rig.matrix_world @ (pb.head if kopf else pb.tail)
    sicht = flieg > .3
    for o in (FL_L, FL_R, FL_B):
        o.hide_render = not sicht
    if sicht:
        w_ = .06 * flieg
        for o, sd in ((FL_L, "L"), (FL_R, "R")):
            schulter = bw("upperarm01." + sd); hand = bw("lowerarm02." + sd, False)
            huefte = bw("upperleg01." + sd); knie = bw("lowerleg01." + sd)
            patch(o, schulter, hand, huefte.lerp(knie, .1), huefte.lerp(knie, .75), w_, -Fc, ts)
        mitte = (bw("upperleg01.L") + bw("upperleg01.R")) / 2
        patch(FL_B, mitte, bw("lowerleg02.L", False), mitte, bw("lowerleg02.R", False), w_ * .8, -Fc, ts)
        # Beinflaeche: bilineare Kanten von Becken zu beiden Knoecheln - als Faecher
        co = []
        aL = bw("lowerleg02.L", False); aR = bw("lowerleg02.R", False)
        for j in range(NV + 1):
            v = j / NV
            for i in range(NU + 1):
                u = i / NU
                p = mitte.lerp(aL.lerp(aR, v), u) + (-Fc) * (w_ * .8 * math.sin(v * P) * u)
                co += [p.x, p.y, p.z]
        FL_B.data.vertices.foreach_set("co", co); FL_B.data.update()
    # Schirm
    if ts > T_AUF:
        k = ease((ts - T_AUF) / 1.2)
        KAPPE.hide_viewport = False
        KAPPE.location = pel + Vector((0, 0, -.2)); KAPPE.rotation_euler = (0, 0, 0); KAPPE.scale = (.3 + .7 * k, .2 + .8 * k, .3 + .7 * k)
        for ch in KAPPE.children:
            ch.hide_render = False
        for i, L_ in enumerate(LEINEN):
            L_.hide_render = False
            a = (pel + H * .55 + S * (.18 if i % 2 else -.18)); b_ = KAPPE.matrix_world @ Vector((.9 * (1 if i < 4 else -1), -3.5 + i, 6.8))
            d_ = b_ - a; L_.location = (a + b_) / 2; L_.scale = (1, 1, max(.01, d_.length)); L_.rotation_mode = "QUATERNION"; L_.rotation_quaternion = d_.to_track_quat("Z", "Y")
    else:
        for ch in KAPPE.children:
            ch.hide_render = True
        for L_ in LEINEN:
            L_.hide_render = True
    # Flugzeug
    flug.location = flugzeug_pos(ts); flug.rotation_euler = (0, -.03 * max(0, ts - T_EXIT) ** .5 * 0, 0)
    flug.hide_render = ts > 25
    # Verkehrsflugzeug ~2 km tiefer, kreuzt die Bahn
    bp = bahn(min(ts, 600))
    JET.location = Vector((bp.x - 1500 + 220 * (ts - 6), -2600 + 190 * (ts - 6), 10600)); JET.rotation_euler = (0, 0, .7)
    spur.location = JET.location - Vector((1000 * math.cos(.7), 1000 * math.sin(.7), 0)) + Vector((0, 0, 0)); spur.rotation_euler = (0, 0, .7)
    # Windstreifen um den Flieger (schneller als er), nur im Jetstream
    js = max(0, min(1, (ts - 12) / 4)) * (1 - max(0, min(1, (ts - 120) / 30)))
    for (o, a, b_, c, g) in STREIFEN:
        o.hide_render = js <= 0.01
        if js > .01:
            vel = (bahn(ts + .1) - bahn(ts - .1)) / .2
            lauf = ((ts * 45 * g + a * 200) % 200) - 100
            o.location = pel + Vector((lauf, b_ * 14, c * 9)); o.rotation_euler = (0, -math.atan2(vel.z, vel.x) * .3, 0)
    # Wolkenfetzen entlang der Bahn
    for (o, a, b_, c) in PUFFS:
        x_ = pel.x + ((a * 30000 - pel.x * .0) % 30000) - 8000
        o.location = (x_, b_ * 6000, pel.z - 600 - abs(c) * 3500)
    return pel


def becken():
    nk = SA.rig.matrix_world @ SA.rig.pose.bones["neck01"].head
    return (SA.rig.matrix_world @ SA.PEL) * .55 + nk * .45


# ======================================================================  Kamera
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam
cam.data.clip_start = .05; cam.data.clip_end = 300000; cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
cam.data.dof.use_dof = True
SZ = [
    (0.00, 1.50, 35.0, 35.4, "B+", (5.0, 2.2, -.4), (5.2, 2.0, -.5), "B", "B", 26),                     # Aufhaenger: Zeitlupe im Jetstream
    (1.50, 2.80, 50.0, 52.0, "B+", (-1.5, -9.0, 2.5), (1.5, -9.0, 2.5), "B", "B", 28),                  # seitlich: Fluegelform
    (2.80, 3.80, 60.0, 61.0, "B+", (90, 8, -2), (-70, 8, -1), "B", "B", 30),                             # rast an der Kamera vorbei
    (3.80, 5.20, 0.0, 0.0, "P", (-6000, -9000, 2200), (-5600, -8800, 2150), (4000, 8000, 0), (4000, 8000, 0), 30),   # Tennessee von oben
    (5.20, 8.20, -.4, 2.1, "F+", (-6.5, 9.0, 1.2), (-6.0, 9.5, 1.0), "B", "B", 22),                       # Absprung aus der Tuer
    (8.20, 9.90, 6.0, 7.7, "B+", (-6, 3, 7), (-5, 3, 7), "J", "J", 75),                                  # tief unten ein Verkehrsflugzeug
    (9.90, 11.90, 10.0, 12.0, "B+", (1.4, -.9, .5), (1.4, -.8, .5), "K", "K", 34),                       # Helm, Kaelte
    (11.90, 13.80, 12.0, 13.9, "B+", (1.2, .6, -.7), (1.2, .5, -.7), "K", "K", 34),                      # Sauerstoffmaske
    (13.80, 16.50, 16.0, 21.0, "B+", (-25, -14, 7), (-20, -12, 5), "B", "B", 24),                        # in den Jetstream
    (16.50, 20.20, 22.0, 31.0, "B+", (3.2, -2.0, 1.0), (3.4, -2.2, 1.1), "B", "B", 24),                  # Tempo 550 km/h
    (20.20, 23.10, 300.0, 310.0, "B+", (-120, -240, 140), (-80, -260, 150), "B", "B", 40),               # weit: 53 km
    (23.10, 27.60, 662.2, 667.0, "B+", (10, -7, 5), (13, -10, 6), "C", "C", 26),                          # Schirm offen
]


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
    elif s[4] == "F+":
        pos = flugzeug_pos(ts) + lerpv(s[5], s[6], k)
    else:
        pos = lerpv(s[5], s[6], k)
    if s[7] == "B":
        ziel = bk
    elif s[7] == "J":
        ziel = JET.location.copy()
    elif s[7] == "C":
        ziel = bk + Vector((0, 0, 3.2))
    elif s[7] == "K":
        ziel = SA.rig.matrix_world @ SA.rig.pose.bones["head"].head
    else:
        ziel = lerpv(s[7], s[8], k)
    cam.location = pos; d = ziel - pos; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = s[9]; cam.data.dof.focus_distance = min(d.length, 5000); cam.data.dof.aperture_fstop = 4 if d.length < 8 else 22
    zit = .02
    cam.location += Vector((zit * math.sin(t * 17.3), zit * math.cos(t * 13.1), zit * math.sin(t * 19.7)))


os.makedirs(A.ordner, exist_ok=True)
N = int(round(D * A.fps))
liste = [int(round(float(x) * A.fps)) for x in A.nur.split(",")] if A.nur else list(range(A.start, N))
for f in liste:
    pfad = os.path.join(A.ordner, f"wingsuit_{f:04d}.png")
    if os.path.exists(pfad) and not A.nur:
        continue
    zustand(f / A.fps); bpy.context.view_layer.update(); zustand(f / A.fps)
    sc.render.filepath = pfad
    bpy.ops.render.render(write_still=True); print("FERTIG", pfad, flush=True)
