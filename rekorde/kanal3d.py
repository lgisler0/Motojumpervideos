"""Aermelkanal-Schwimmen 6:45:25 (Andreas Waschburger, 8.9.2023, Dover -> Cap Gris-Nez, GWR). Realistisch, natuerliche Armzuege.
python3 kanal3d.py <ordner> [--nur t1,t2] [--start i] [--samples n]"""
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
# ======================================================================  Schwimmer (zuerst): Badehose, Kappe, Brille
import mensch_echt as ME
LOGO = ME.logo_bild(os.path.join(HIER, "_logo_norda.png"), "NORDA", farbe=(1, 1, 1))
PC = ME.mensch("waschburger", 58, 1.0, .45, .7, .2, haut="caucasian", haare=None, braue="eyebrow001", haarfarbe="3a2a1e", schuhe=None)
for o in PC.stiefel:
    o.hide_render = True
ME.trikot(PC, None, "shorts", "111111", "14181f", bein=LOGO)
for o in PC.huellen:
    if "versatz" in o.modifiers:
        o.modifiers["versatz"].strength = .008
    for md in o.modifiers:
        if md.type == "SUBSURF":
            md.render_levels = 2
hoehe = max(v.z for v in PC.EV); PC.SK = 1.86 / hoehe; PC.rig.scale = (PC.SK,) * 3
PC.PEL = PC.rig.data.bones["upperleg01.L"].head_local.copy(); PC.PEL.x = 0
# Kappe + Schwimmbrille am Kopf-Knochen
bpy.context.view_layer.update()
kopf_b = PC.rig.data.bones["head"]
kh = PC.rig.matrix_world @ kopf_b.head_local; kt = PC.rig.matrix_world @ kopf_b.tail_local
kz = kh + (kt - kh) * .55
bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1, location=kz + Vector((0, .015, .035)))
kappe = bpy.context.object; kappe.name = "kappe"; kappe.scale = (.103, .117, .104); kappe.data.materials.append(mat("kappe", "f5c400", .35, Coat_Weight=.6))
bm = bmesh.new(); bm.from_mesh(kappe.data)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -.25 or (v.co.z < .15 and v.co.y < -.55)], context="VERTS"); bm.to_mesh(kappe.data); bm.free()
for p in kappe.data.polygons:
    p.use_smooth = True
BR_M = mat("brillenglas", "1a3a6a", .05, metal=.9, Coat_Weight=1)
brille = []
for sx in (-1, 1):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=10, radius=1, location=kz + Vector((sx * .034, -.098, -.018)))
    g_ = bpy.context.object; g_.name = "brille"; g_.scale = (.019, .011, .013); g_.data.materials.append(BR_M)
    for p in g_.data.polygons:
        p.use_smooth = True
    brille.append(g_)
bpy.ops.mesh.primitive_torus_add(major_radius=.103, minor_radius=.004, location=kz + Vector((0, .0, -.018)))
band = bpy.context.object; band.name = "brillenband"; band.scale = (1, 1.1, 1); band.data.materials.append(mat("band", "111111", .7))
bpy.context.view_layer.update()
PI = (PC.rig.matrix_world @ kopf_b.matrix_local @ Matrix.Translation((0, kopf_b.length, 0))).inverted()
for o in [kappe, band] + brille:
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
bpy.ops.object.light_add(type="SUN", rotation=(math.radians(52), 0, math.radians(150))); sonne = bpy.context.object
sonne.data.energy = 4.2; sonne.data.angle = math.radians(.8); sonne.data.color = (1, .96, .9)
STAHL = pbr("stahl", "Metal012", 6, rau_mul=.6, rau_add=.15, metal=1.0)

A_ = Vector((0, 0, 0)); M_ = Vector((0, -6000, 0)); B_ = Vector((0, 6000, 0))

# ======================================================================  Wasser: Ocean-Modifier + ruhiges Fernmeer
WASSER = bpy.data.materials.new("wasser"); WASSER.use_nodes = True
n = WASSER.node_tree.nodes; l = WASSER.node_tree.links; b = n["Principled BSDF"]
b.inputs["Base Color"].default_value = (*hexf("0d3340"), 1); b.inputs["Roughness"].default_value = .06; b.inputs["IOR"].default_value = 1.333
b.inputs["Subsurface Weight"].default_value = .15; b.inputs["Subsurface Radius"].default_value = (.1, .4, .35)
at = n.new("ShaderNodeAttribute"); at.attribute_name = "schaum"
mr = n.new("ShaderNodeMapRange"); mr.inputs[1].default_value = .35; mr.inputs[2].default_value = 1.0; l.new(at.outputs["Fac"], mr.inputs[0])
mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; l.new(mr.outputs[0], mx.inputs[0])
mx.inputs[6].default_value = (*hexf("0d3340"), 1); mx.inputs[7].default_value = (.85, .9, .9, 1); l.new(mx.outputs[2], b.inputs["Base Color"])
rr = n.new("ShaderNodeMapRange"); rr.inputs[3].default_value = .06; rr.inputs[4].default_value = .6; l.new(mr.outputs[0], rr.inputs[0]); l.new(rr.outputs[0], b.inputs["Roughness"])
no = n.new("ShaderNodeTexNoise"); no.inputs["Scale"].default_value = 6.0; no.inputs["Detail"].default_value = 8
bu = n.new("ShaderNodeBump"); bu.inputs["Strength"].default_value = .08; l.new(no.outputs["Fac"], bu.inputs["Height"]); l.new(bu.outputs[0], b.inputs["Normal"])
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0)); OZEAN = bpy.context.object; OZEAN.name = "ozean"
om = OZEAN.modifiers.new("ocean", "OCEAN"); om.geometry_mode = "GENERATE"; om.resolution = 8; om.spatial_size = 120; om.size = 1.0
om.repeat_x = 4; om.repeat_y = 4; om.wave_scale = .22; om.choppiness = .9; om.wind_velocity = 6.0; om.wave_alignment = .3
om.use_normals = True; om.use_foam = True; om.foam_layer_name = "schaum"; om.foam_coverage = .25; om.random_seed = 4
OZEAN.data.materials.append(WASSER)
for p in OZEAN.data.polygons:
    p.use_smooth = True
OZEAN.modifiers.new("glatt", "SUBSURF").levels = 0
bpy.ops.mesh.primitive_plane_add(size=60000, location=(0, 0, -.12)); fern = bpy.context.object; fern.name = "fernmeer"; fern.data.materials.append(WASSER)
bpy.ops.mesh.primitive_plane_add(size=60000, location=(0, 0, -7)); grund = bpy.context.object; grund.name = "meeresgrund"; grund.data.materials.append(mat("meeresgrund", "0b2228", .9))

# ======================================================================  Gelaende-Gitter (Klippen, Strand) als Hoehenfeld
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


def klippen_mat(name, fels, fels2, gras):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt_ = m.node_tree; n = nt_.nodes; l = nt_.links; b = n["Principled BSDF"]
    geo = n.new("ShaderNodeNewGeometry"); sp = n.new("ShaderNodeSeparateXYZ"); l.new(geo.outputs["Normal"], sp.inputs[0])
    sp2 = n.new("ShaderNodeSeparateXYZ"); l.new(geo.outputs["Position"], sp2.inputs[0])
    gr = n.new("ShaderNodeMapRange"); gr.inputs[1].default_value = .72; gr.inputs[2].default_value = .85; l.new(sp.outputs["Z"], gr.inputs[0])
    hz = n.new("ShaderNodeMapRange"); hz.inputs[1].default_value = 6; hz.inputs[2].default_value = 12; l.new(sp2.outputs["Z"], hz.inputs[0])
    mu = n.new("ShaderNodeMath"); mu.operation = "MULTIPLY"; l.new(gr.outputs[0], mu.inputs[0]); l.new(hz.outputs[0], mu.inputs[1])
    no = n.new("ShaderNodeTexNoise"); no.inputs["Scale"].default_value = .15; no.inputs["Detail"].default_value = 10; l.new(geo.outputs["Position"], no.inputs["Vector"])
    st = n.new("ShaderNodeTexWave"); st.wave_type = "BANDS"; st.bands_direction = "Z"; st.inputs["Scale"].default_value = .12; st.inputs["Distortion"].default_value = 14; st.inputs["Detail"].default_value = 6
    l.new(geo.outputs["Position"], st.inputs["Vector"])
    fc = n.new("ShaderNodeMix"); fc.data_type = "RGBA"; l.new(st.outputs["Fac"], fc.inputs[0])
    fc.inputs[6].default_value = (*hexf(fels), 1); fc.inputs[7].default_value = (*hexf(fels2), 1)
    gc = n.new("ShaderNodeMix"); gc.data_type = "RGBA"; gc.blend_type = "MULTIPLY"; gc.inputs[0].default_value = .45
    l.new(fc.outputs[2], gc.inputs[6]); l.new(no.outputs["Color"], gc.inputs[7])
    mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; l.new(mu.outputs[0], mx.inputs[0]); l.new(gc.outputs[2], mx.inputs[6])
    mx.inputs[7].default_value = (*hexf(gras), 1); l.new(mx.outputs[2], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = .9
    bu = n.new("ShaderNodeBump"); bu.inputs["Strength"].default_value = 1.0; bu.inputs["Distance"].default_value = 1.2
    no2 = n.new("ShaderNodeTexNoise"); no2.inputs["Scale"].default_value = 1.2; no2.inputs["Detail"].default_value = 12; l.new(geo.outputs["Position"], no2.inputs["Vector"])
    l.new(no2.outputs["Fac"], bu.inputs["Height"]); l.new(bu.outputs[0], b.inputs["Normal"])
    return m


def sstep(a, b, x):
    t = min(1, max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t)


KIES = pbr("kies", "Ground054", .8, tint="a8a094")
# ---- Dover: Kiesstrand (x -70..30), weisse Kreideklippen bei x ~ -70
def dover(x, y):
    xc = -70 + 9 * math.sin(y / 41) + 4 * math.sin(y / 13 + 1)
    strand = -.1 * x if x > 0 else -.055 * x
    kl = 104 * sstep(xc + 2, xc - 5, x) + 7 * math.sin(y / 23) * sstep(xc, xc - 30, x) + 3 * math.sin(x / 9 + y / 17) * sstep(xc - 4, xc - 20, x)
    return max(strand, kl + (strand if kl < 1 else 0))


hoehenfeld("dover_klippen", -230, -50, -700, 700, 3.0, dover, klippen_mat("kreide", "ecebe4", "c9c5ba", "6d8a45"))
hoehenfeld("dover_strand", -60, 40, -300, 300, 1.0, lambda x, y: (-.1 * x if x > 0 else -.055 * x) + .04 * math.sin(x * 1.7 + y * .9), KIES)
# ---- Cap Gris-Nez: Felsstrand und niedrigere Klippen (x ~ +55), Leuchtturm
def gris(x, y):
    xc = 58 + 6 * math.sin((y - B_.y) / 31)
    strand = .09 * x
    kl = 44 * sstep(xc - 3, xc + 8, x) + 4 * math.sin((y - B_.y) / 19) * sstep(xc, xc + 25, x)
    return max(strand, kl)


hoehenfeld("gris_klippen", 45, 260, B_.y - 500, B_.y + 500, 3.0, gris, klippen_mat("sandstein", "c8b690", "a89878", "5f7e3e"))
hoehenfeld("gris_strand", -40, 60, B_.y - 250, B_.y + 250, 1.0, lambda x, y: .09 * x + .05 * math.sin(x * 1.3 + y * .7), KIES)
LT = B_ + Vector((105, 30, gris(105, B_.y + 30)))
zyl("leuchtturm", 3.2, 24, LT + Vector((0, 0, 12)), mat("turm", "f2f0ea", .5))
zyl("laterne", 2.2, 3.4, LT + Vector((0, 0, 25.7)), mat("laterne_glas", "202a30", .1, metal=.6))
zyl("laternendach", 2.6, .8, LT + Vector((0, 0, 27.8)), mat("turmdach", "1a1a1a", .5))
box("waerterhaus", (10, 7, 5), LT + Vector((9, 0, 2.5)), mat("haus_w", "e8e2d6", .7), .1)
box("haus_dach", (10.6, 7.6, .6), LT + Vector((9, 0, 5.3)), mat("haus_d", "3a3f46", .6), .05)
# Felsbrocken am Ufer (rund, keine Wuerfel)
FB = Sammler(); rf = random.Random(5)
FELS = [pbr("fels%d" % i, "Ground054", .5, tint=t) for i, t in enumerate(("6a6660", "5a564e", "7a746a"))]
for i in range(260):
    x = rf.uniform(-25, 40); y = rf.uniform(-60, 60)
    if abs(y) < 4 and -12 < x < 20:
        continue
    r = rf.uniform(.3, 1.6) * (1.6 if x < 0 else 1)
    FB.kugel(r, B_ + Vector((x, y, .09 * x - r * .3)), rf.choice(FELS), skala=(rf.uniform(.8, 1.4), rf.uniform(.8, 1.4), rf.uniform(.5, .8)), sub=2)
for i in range(120):
    x = rf.uniform(-55, -5); y = rf.uniform(-150, 150)
    r = rf.uniform(.4, 1.2)
    FB.kugel(r, A_ + Vector((x, y, -.055 * x - r * .5)), rf.choice(FELS), skala=(1.2, 1, .5), sub=2)
FB.fertig("felsen")
# Buhnen (Holzpfaehle) am Dover-Strand
HOLZ = mat("buhne", "5a4632", .85)
BU = Sammler()
for yb in (-110, 95):
    for k in range(30):
        x = -40 + k * 1.6
        BU.box((.35, .35, 1.6), A_ + Vector((x, yb, (-.1 * x if x > 0 else -.055 * x) + .4)), HOLZ)
BU.fertig("buhnen")

# ======================================================================  Containerschiff (fahrend, an SCHIFF gehaengt)
SCHIFF = leer("schiff")
SH = Sammler()
RUMPF = mat("schiffsrumpf", "2a3346", .45, Coat_Weight=.3); UNTER = mat("unterwasser", "7a2a22", .6); DECK_M = mat("deck", "8a8f96", .6)
WEISS_S = mat("aufbau", "eceae4", .5); FENSTER = mat("fenster", "1a2430", .1, metal=.6)
CONT = [mat("cont%d" % i, f, .55) for i, f in enumerate(("b33a2a", "2a5aa8", "e0a020", "3a7a46", "8a8f96", "d06a20", "f2f2f2"))]
SH.box((280, 44, 20), Vector((0, 0, 4)), RUMPF)
SH.box((281, 44.4, 6), Vector((0, 0, -3.2)), UNTER)
for k in range(8):                                       # spitzer Bug
    f = (k + 1) / 9
    SH.box((5, 44 * (1 - f * .9), 20 - k * .6), Vector((140 + 2.5 + k * 4.4, 0, 4 + k * .3)), RUMPF)
SH.box((280, 44, .6), Vector((0, 0, 14.3)), DECK_M)
rc = random.Random(9)
for bay in range(16):
    for row in range(14):
        h = rc.choice((4, 5, 6, 6, 7))
        for tier in range(h):
            SH.box((12.0, 2.4, 2.55), Vector((-80 + bay * 13.2, -15.6 + row * 2.45, 15.9 + tier * 2.6)), rc.choice(CONT))
SH.box((22, 40, 22), Vector((-120, 0, 25.5)), WEISS_S)
for z in range(5):
    SH.box((22.2, 36, 1.2), Vector((-120, 0, 19 + z * 4)), FENSTER)
SH.box((8, 46, 1.2), Vector((-112, 0, 36.8)), WEISS_S)
SH.box((7, 7, 12), Vector((-130, 0, 42)), mat("schornstein", "1a1a1a", .6))
for o in SH.fertig("containerschiff", bevel=.05):
    o.parent = SCHIFF

# ======================================================================  Begleitboot (mit Crew)
BOOT = leer("boot")
BS = Sammler()
BW = mat("boot_weiss", "f2f2ef", .3, Coat_Weight=.6); BB = mat("boot_blau", "1d3f78", .35, Coat_Weight=.6)
for k in range(10):
    f = k / 9
    BS.box((1.5, 4.2 * (1 - .75 * f ** 2), 1.8 - .3 * f), Vector((-6.5 + k * 1.45, 0, .5 + .15 * f)), BW)
BS.box((14.5, 4.25, .5), Vector((0, 0, -.2)), BB)
BS.box((4.5, 3.2, 2.3), Vector((-1.5, 0, 2.6)), BW)
BS.box((4.6, 3.3, .7), Vector((-1.5, 0, 3.3)), FENSTER)
BS.box((5, 3.6, .2), Vector((-1.5, 0, 3.85)), BB)
BS.rohr(Vector((-1.5, 0, 3.9)), Vector((-1.5, 0, 6.5)), .05, STAHL)
for sy in (-1, 1):
    BS.rohr(Vector((-6, sy * 2.0, 1.6)), Vector((5.5, sy * 1.2, 1.6)), .03, STAHL)
    for k in range(7):
        x = -6 + k * 1.8; BS.rohr(Vector((x, sy * (2.0 - .12 * k), 1.4)), Vector((x, sy * (2.0 - .12 * k), 2.3)), .025, STAHL)
for o in BS.fertig("begleitboot", bevel=.04):
    o.parent = BOOT
for i, (x, y) in enumerate(((2.5, -1.2), (4.2, -.8), (-4.5, -1.0))):
    o = bpy.data.objects.new("crew%d" % i, ZUSCH_ME[(i * 2 + 1) % len(ZUSCH_ME)]); sc.collection.objects.link(o)
    o.location = (x, y, 1.4); o.rotation_euler = (0, 0, P + .4 * (i - 1)); o.parent = BOOT
# Zuschauer am Strand (Dover-Start und Cap Gris-Nez)
rz = random.Random(13)
STRAND_LEUTE = []
for basis, xs, blick in ((A_, (-14, -4), -P / 2), (B_, (6, 16), P / 2)):
    for i in range(16):
        x = rz.uniform(*xs); y = rz.uniform(-9, 9)
        if abs(y) < 2.2:
            continue
        z = (-.055 * x if basis is A_ else .09 * x)
        o = bpy.data.objects.new("strand_%d" % len(STRAND_LEUTE), rz.choice(ZUSCH_ME)); sc.collection.objects.link(o)
        o.location = basis + Vector((x, y, z)); o.rotation_euler = (0, 0, blick + rz.uniform(-.6, .6))
        STRAND_LEUTE.append((o, z + basis.z, rz.uniform(0, 6)))
# Spritzwasser (kleine weisse Kugeln, werden bei den Armzuegen gesetzt)
SCHAUM_M = mat("gischt", "f4f8fa", .35, Transmission_Weight=.5)
GISCHT = []
for i in range(26):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, location=(0, 0, -50)); o = bpy.context.object; o.name = "gischt%d" % i
    o.data.materials.append(SCHAUM_M)
    for p in o.data.polygons:
        p.use_smooth = True
    GISCHT.append(o)
# Schaum/Kielwasser um den Schwimmer (Ebene mit Rauschen-Alpha)
SCH = bpy.data.materials.new("kielwasser"); SCH.use_nodes = True; SCH.blend_method = "HASHED" if hasattr(SCH, "blend_method") else None
n = SCH.node_tree.nodes; l = SCH.node_tree.links; out = n["Material Output"]; bs = n["Principled BSDF"]
bs.inputs["Base Color"].default_value = (.9, .94, .95, 1); bs.inputs["Roughness"].default_value = .45
tc = n.new("ShaderNodeTexCoord"); mp = n.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (2.0, 2.0, 1); l.new(tc.outputs["Object"], mp.inputs[0])
ln = n.new("ShaderNodeVectorMath"); ln.operation = "LENGTH"; l.new(mp.outputs[0], ln.inputs[0])
fall = n.new("ShaderNodeMapRange"); fall.inputs[1].default_value = .3; fall.inputs[2].default_value = .95; fall.inputs[3].default_value = 1.0; fall.inputs[4].default_value = 0.0; l.new(ln.outputs["Value"], fall.inputs[0])
nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 14; nz.inputs["Detail"].default_value = 8; l.new(tc.outputs["Object"], nz.inputs["Vector"])
th = n.new("ShaderNodeMapRange"); th.inputs[1].default_value = .56; th.inputs[2].default_value = .72; l.new(nz.outputs["Fac"], th.inputs[0])
mu = n.new("ShaderNodeMath"); mu.operation = "MULTIPLY"; l.new(th.outputs[0], mu.inputs[0]); l.new(fall.outputs[0], mu.inputs[1])
tr = n.new("ShaderNodeBsdfTransparent"); ms = n.new("ShaderNodeMixShader")
l.new(mu.outputs[0], ms.inputs[0]); l.new(tr.outputs[0], ms.inputs[1]); l.new(bs.outputs[0], ms.inputs[2]); l.new(ms.outputs[0], out.inputs["Surface"])
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -50)); KIEL = bpy.context.object; KIEL.name = "kielwasser"; KIEL.scale = (3.6, 1.5, 1)
KIEL.data.materials.append(SCH)
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


X_ = Vector((1, 0, 0)); Y_ = Vector((0, 1, 0)); UP = Vector((0, 0, 1))
T_A = 1.5                      # Armzyklus (s)
V_SW = 1.45                    # Schwimmtempo (m/s)
T_B0 = 24300.0; T_STEH = 24312.0; T_ZIEL = 24325.0


def boden_A(x):
    return -.1 * x if x > 0 else -.055 * x


def boden_B(x):
    return .09 * x


def gebiet(ts):
    return "A" if ts < 100 else ("M" if ts < 24000 else "B")


def schwimm_pos(ts):
    g = gebiet(ts)
    if g == "A":
        return A_ + Vector((6.0 + V_SW * (ts - 3.0), 0, 0))
    if g == "M":
        return M_ + Vector((V_SW * (ts - 6000.0), 0, 0))
    return B_ + Vector((-6.0 - V_SW * (T_STEH - ts), 0, 0))


# Hand-Bahn beim Kraulen (vorwaerts, aussen, hoch) relativ zur Schulter
ARM_KEYS = [(0.00, (.55, .08, -.04)), (.12, (.64, .05, -.30)), (.30, (.15, -.10, -.52)), (.50, (-.40, .04, -.38)),
            (.58, (-.55, .10, -.06)), (.72, (-.30, .26, .22)), (.86, (.22, .22, .20))]


def arm_bahn(u):
    u = u % 1.0
    ks = ARM_KEYS + [(1.0, ARM_KEYS[0][1])]
    for i in range(len(ks) - 1):
        if ks[i][0] <= u < ks[i + 1][0]:
            break
    f = (u - ks[i][0]) / (ks[i + 1][0] - ks[i][0])
    p0 = Vector(ks[(i - 1) % len(ARM_KEYS)][1]); p1 = Vector(ks[i][1]); p2 = Vector(ks[(i + 1) % len(ARM_KEYS)][1]); p3 = Vector(ks[(i + 2) % len(ARM_KEYS)][1])
    f2 = f * f; f3 = f2 * f
    return .5 * (2 * p1 + (-p0 + p2) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f2 + (-p0 + 3 * p1 - 3 * p2 + p3) * f3)


def gischt(punkte):
    for i, o in enumerate(GISCHT):
        if i < len(punkte):
            p_, r = punkte[i]; o.location = p_; o.scale = (r, r, r * .45)
        else:
            o.location = (0, 0, -50)


def schwimmen(ts):
    pel = schwimm_pos(ts)
    uR = (ts / T_A) % 1.0; uL = (uR + .5) % 1.0
    n = math.floor(ts / T_A)
    roll = .55 * math.sin(2 * P * (uR - .08))
    atem = 0.0
    if n % 2 == 0:
        atem = -.5 * math.sin(P * seg(uR, .52, .98))          # Kopf/Koerper zur rechten Seite drehen zum Atmen
    th = roll + atem
    H = Vector((math.cos(.06), 0, math.sin(.06)))
    Fc = Vector((0, math.sin(th), -math.cos(th)))
    pel = pel + Vector((0, 0, -.02 + .02 * math.sin(4 * P * ts / T_A)))
    rq = rig_mat(H, Fc).to_quaternion()
    KF.rig.rotation_mode = "QUATERNION"; KF.rig.rotation_quaternion = rq
    KF.rig.location = pel - rq.to_matrix() @ (KF.PEL * KF.SK)
    le = H.cross(Fc).normalized()
    spr = []
    for sd, s, u in (("L", 1, uL), ("R", -1, uR)):
        sh = pel + H * .5 + le * (.19 * s)
        k = arm_bahn(u)
        hand = sh + X_ * k.x + Y_ * (s * k.y) + UP * k.z
        KF.Z["hand_" + sd].location = hand
        KF.Z["ell_" + sd].location = sh + UP * 1.0 + Y_ * (s * .6) - X_ * .2
        if u < .14:
            e = 1 - u / .14
            for j in range(3):
                spr.append((Vector((hand.x + .1 * j - .1, hand.y + s * .06 * (j - 1), .03 + .1 * (1 - e) * (j + 1) / 3)), .02 + .03 * e))
        elif .54 < u < .64:
            spr.append((Vector((hand.x, hand.y, .08 + .2 * seg(u, .54, .64))), .018))
        # Beine: 6er-Beinschlag
        ph = 2 * P * 3 * ts / T_A + (0 if s > 0 else P)
        fz = -.24 + .12 * math.sin(ph)
        KF.Z["fuss_" + sd].location = pel - H * .9 + Y_ * (s * .1) + UP * fz
        KF.Z["knie_" + sd].location = pel - UP * 2.0 + X_ * .4 + Y_ * (s * .3)
        if fz > -.16:
            spr.append((Vector((pel.x - .95, pel.y + s * .1, .04)), .025 + .03 * seg(fz, -.16, -.12)))
    gischt(spr)
    KIEL.location = Vector((pel.x - .35, pel.y, .035)); KIEL.rotation_euler = (0, 0, 0)
    # Kopf leicht zur Atmung drehen
    KF.dreh("neck01", x=.35)
    for sd in ("L", "R"):
        for ff in range(2, 6):
            for g in (1, 2, 3):
                KF.dreh(f"finger{ff}-{g}.{sd}", x=.15 + .05 * g)       # Hand flach, Finger leicht geschlossen
        for g in (2, 3):
            KF.dreh(f"finger1-{g}.{sd}", x=.2)
    return pel, X_


def aufrecht(ts):
    """Stehen am Start, ins Wasser laufen, aus dem Wasser gehen, jubeln"""
    g = gebiet(ts)
    if g == "A":
        boden = boden_A; basis = A_
        if ts < 0:
            px = -1.0; T = 99; gehen = False
        else:
            px = -1.0 + 6.0 * ease(seg(ts, 0, 2.6)) ** .8; T = .36; gehen = True
    else:
        boden = boden_B; basis = B_
        px = -6.0 + 10.5 * seg(ts, T_STEH, T_ZIEL) if ts < T_ZIEL else 4.5 + .4 * ease(seg(ts, T_ZIEL, T_ZIEL + 1.0))
        T = .7; gehen = ts < T_ZIEL + 1.0
    jubel = ease(seg(ts, T_ZIEL + .4, T_ZIEL + 1.2)) if g == "B" else 0.0
    gischt([]); KIEL.location = (0, 0, -50)
    # Fuesse: Schrittfolge entlang x
    def fpos(k, seite):
        if not gehen:
            return Vector((px + (.05 if seite > 0 else -.05), seite * .12, 0))
        t0 = (0 if g == "A" else T_STEH)
        tk = t0 + k * T
        if g == "A":
            xk = -1.0 + 6.0 * ease(seg(tk, 0, 2.6)) ** .8
        else:
            xk = -6.0 + 10.5 * seg(tk, T_STEH, T_ZIEL) if tk < T_ZIEL else 4.5 + .4 * ease(seg(tk, T_ZIEL, T_ZIEL + 1.0))
        return Vector((xk + .25, seite * .12, 0))
    t0 = 0 if g == "A" else T_STEH
    q = (ts - t0) / T if gehen else 0.0
    k = math.floor(q); f = q - k
    for sd, s_ in (("L", 1), ("R", -1)):
        if not gehen or q < 0:
            p_ = fpos(0, s_)
            lift = 0.0
        else:
            mein = (k % 2 == 0) == (sd == "L")          # dieser Fuss steht
            if mein:
                p_ = fpos(k, s_); lift = 0.0
            else:
                a = fpos(k - 1, s_); b_ = fpos(k + 1, s_); e = ease(f)
                p_ = a.lerp(b_, e); lift = (.2 if g == "A" else .12) * math.sin(P * f)
        p_ = basis + p_ + Vector((0, 0, boden(p_.x) + .1 + lift))
        KF.Z["fuss_" + sd].location = p_
    pel = basis + Vector((px, 0, boden(px) + .95 + (.03 * math.sin(2 * P * q) if gehen else 0)))
    if jubel:
        pel.z += .08 * abs(math.sin((ts - T_ZIEL) * 5)) * jubel
    lean = (.18 if g == "A" and gehen else .06) * (1 - jubel)
    H = X_ * math.sin(lean) + UP * math.cos(lean); Fc = X_ * math.cos(lean) - UP * math.sin(lean)
    rq = rig_mat(H, Fc).to_quaternion()
    KF.rig.rotation_mode = "QUATERNION"; KF.rig.rotation_quaternion = rq
    KF.rig.location = pel - rq.to_matrix() @ (KF.PEL * KF.SK)
    le = Y_
    for sd, s_ in (("L", 1), ("R", -1)):
        KF.Z["knie_" + sd].location = pel + X_ * 2.0 + Y_ * (s_ * .35) - UP * .3
        KF.Z["ell_" + sd].location = pel - X_ * 1.2 + Y_ * (s_ * .45) + UP * .3
        sh = pel + H * .48 + le * (s_ * .19)
        if gehen:
            sp = (-math.cos(P * q) if sd == "L" else math.cos(P * q)) * (1.0 if g == "A" else .6)
            hand = sh + X_ * (.08 + .22 * sp) - H * (.38 - .14 * sp) + le * (s_ * .04)
            if g == "B":
                hand = hand + le * (s_ * .12) + UP * .06      # Arme leicht seitlich zum Balancieren auf den Steinen
        else:
            hand = sh - H * .56 + X_ * .06 + le * (s_ * .06)
        KF.Z["hand_" + sd].location = hand
    if jubel > 0:
        KF.IK["hand_L"].influence = 1 - jubel; KF.IK["hand_R"].influence = 1 - jubel
        KF.dreh("upperarm01.L", z=-.72 + 3.0 * jubel, x=.2 * jubel); KF.dreh("upperarm01.R", z=.72 - 3.0 * jubel, x=.2 * jubel)
        KF.dreh("lowerarm01.L", x=-.4 * jubel); KF.dreh("lowerarm01.R", x=-.4 * jubel)
    KF.dreh("neck01", x=-.3 * lean + .1 * jubel)
    for sd in ("L", "R"):
        for ff in range(2, 6):
            for gg in (1, 2, 3):
                KF.dreh(f"finger{ff}-{gg}.{sd}", x=(.5 + .12 * gg) * (1 - jubel) + .1)
        for gg in (2, 3):
            KF.dreh(f"finger1-{gg}.{sd}", x=.45 * (1 - jubel))
    return pel, X_


def figur(ts):
    KF.zuruecksetzen()
    for c in KF.IK.values():
        c.influence = 1.0
    g = gebiet(ts)
    schwimmt = (g == "A" and ts >= 3.0) or g == "M" or (g == "B" and ts < T_STEH)
    pel, fw = schwimmen(ts) if schwimmt else aufrecht(ts)
    # Meer, Boot, Schiff je Gebiet
    om.time = ts % 1000.0
    if g == "A":
        OZEAN.location = A_ + Vector((55, -180, 0)); BOOT.location = A_ + Vector((60, 25, 0)); BOOT.rotation_euler = (0, 0, .3)
        SCHIFF.location = A_ + Vector((2200, 600, 0)); SCHIFF.rotation_euler = (0, 0, P / 2)
    elif g == "M":
        OZEAN.location = M_ + Vector((-120, -180, 0))
        BOOT.location = schwimm_pos(ts) + Vector((-2.0, 12.0, 0)); BOOT.rotation_euler = (0, 0, 0)
        SCHIFF.location = M_ + Vector((112, 6.5 * (ts - 6045.0), 0)); SCHIFF.rotation_euler = (0, 0, P / 2)
    else:
        OZEAN.location = B_ + Vector((-415, -180, 0)); BOOT.location = B_ + Vector((-55, 18, 0)); BOOT.rotation_euler = (0, 0, .2)
        SCHIFF.location = B_ + Vector((-2600, -900, 0)); SCHIFF.rotation_euler = (0, 0, P / 2)
    # Boot schaukelt
    BOOT.location.z = .12 * math.sin(ts * 1.3); BOOT.rotation_euler.x = .03 * math.sin(ts * 1.1); BOOT.rotation_euler.y = .02 * math.sin(ts * .9)
    fertig = g == "B" and ts > T_ZIEL
    for o, z0, ph_ in STRAND_LEUTE:
        o.location.z = z0 + (.08 * max(0, math.sin(ts * 7 + ph_)) if fertig else 0.0)
    bpy.context.view_layer.update()
    return pel, fw


def becken():
    nk = KF.rig.matrix_world @ KF.rig.pose.bones["neck01"].head
    return (KF.rig.matrix_world @ KF.PEL) * .55 + nk * .45


# ======================================================================  Kamera
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam
cam.data.clip_start = .03; cam.data.clip_end = 20000; cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
cam.data.dof.use_dof = True
SZ = [
    # t0, t1, ts0, ts1, modus, pos0, pos1, ziel0, ziel1, brennweite   (R = relativ zum Becken, Ziel "B" oder relativer Punkt "R:")
    (0.00, 1.50, 6043.6, 6044.3, "R", (-1.1, -1.8, .5), (-.9, -1.75, .52), (.5, 0, .05), (.6, 0, .05), 24),        # Aufhaenger: Wasserhoehe, Schiff dahinter
    (1.50, 2.50, 6010.0, 6011.0, "R", (-3.0, -2.0, 6.0), (-2.6, -2.0, 6.0), (2, 0, 0), (2.4, 0, 0), 28),           # Drohne ueber dem Schwimmer
    (2.50, 3.70, 6020.0, 6021.2, "R", (-170, -230, 200), (-160, -225, 190), (0, 0, 0), (0, 0, 0), 40),            # winzig im offenen Meer
    (3.70, 4.60, -1.0, -0.8, "P", A_ + Vector((260, -140, 14)), A_ + Vector((250, -132, 14)), A_ + Vector((-80, 0, 45)), A_ + Vector((-80, 0, 45)), 26),   # Kreideklippen Dover
    (4.60, 6.30, -2.0, -0.3, "P", A_ + Vector((6.5, -3.0, 1.1)), A_ + Vector((6.0, -2.7, 1.15)), "B", "B", 26),   # am Strand
    (6.30, 9.10, 0.0, 2.3, "P", A_ + Vector((10.0, -5.2, 1.0)), A_ + Vector((10.2, -4.6, 1.0)), "B", "B", 28),   # laeuft ins Wasser
    (9.10, 12.10, 6000.0, 6003.0, "R", (-9, -12, 5), (-30, -46, 26), (0, 0, 0), (0, 0, 0), 26),                    # offenes Meer, Boot
    (12.10, 14.30, 6040.5, 6046.0, "R", (-6.5, -4.0, 1.0), (-5.8, -3.6, 1.1), (6, 1.0, 4.0), (6, 1.5, 4.6), 18),         # Schiff kreuzt
    (14.30, 15.40, 6020.0, 6021.3, "R", (.35, -1.6, .5), (.4, -1.55, .5), (.25, 0, .1), (.3, 0, .1), 26),        # Arm ueber Arm
    (15.40, 17.90, 6012.0, 6015.0, "R", (-4.0, -1.6, 2.2), (-3.6, -1.3, 2.2), (1.5, 0, 0), (1.5, 0, 0), 28),                # Stunde um Stunde (von oben)
    (17.90, 20.20, 24302.0, 24304.3, "R", (-1.4, -.6, .55), (-1.3, -.55, .58), (60, 0, 18), (60, 0, 18), 26),      # Klippen Frankreichs
    (20.20, 23.60, 24320.4, 24325.8, "P", B_ + Vector((9.5, -3.6, 1.7)), B_ + Vector((9.0, -3.1, 1.6)), "B", "B", 26),   # aus dem Wasser
    (23.60, 27.40, 24325.8, 24329.6, "R", (-3.0, -1.8, 1.1), (-2.6, -2.8, 1.5), "B", "B", 24),         # Jubel vor den Klippen
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
    if s[4] == "R":
        anker = Vector((pel.x, pel.y, 0)) if gebiet(ts) != "B" or ts < T_STEH else Vector((bk.x, bk.y, boden_B(bk.x - B_.x)))
        pos = anker + o
        pos.z = max(pos.z, .45)
        ziel = bk if s[7] == "B" else anker + Vector(lerpv(s[7], s[8], k))
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
    pfad = os.path.join(A.ordner, f"kanal_{f:04d}.png")
    if os.path.exists(pfad) and not A.nur:
        continue
    zustand(f / A.fps); bpy.context.view_layer.update(); zustand(f / A.fps)
    sc.render.filepath = pfad
    bpy.ops.render.render(write_still=True); print("FERTIG", pfad, flush=True)
