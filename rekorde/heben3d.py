"""Geschichte: Ein Mann hat einen Job: eine Stange heben - 511 kg Kreuzheben (Raul Flores, World Deadlift Championships,
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
D = 25.8
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


# ======================================================================  Heber (MPFB) - zuerst, Materialien danach
H = MH.Arbeiter(name="heber", seed=5, maenn=1.0, alter=.4, muskel=1.0, gewicht=1.0, haut="caucasian", weste=False)
TON = (.46, .29, .19)
for sl in H.koerper.material_slots:
    g = sl.material.node_tree.nodes.get("colorgroup") if sl.material and sl.material.node_tree else None
    if g:
        g.inputs["SkinColor"].default_value = (*TON, 1); g.inputs["SkinOverride"].default_value = 1.0
knie = H.gm("joint-l-knee").z
for o in H.huellen:
    if o.name.endswith("_hemd"):
        for nd in o.active_material.node_tree.nodes:
            if nd.type == "MIX" and nd.data_type == "RGBA":
                nd.inputs[6].default_value = (*hexf("1a1a1c"), 1); nd.inputs[7].default_value = (*hexf("222226"), 1)
        o.modifiers["versatz"].strength = .005
        o.active_material.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = .55
    elif o.name.endswith("_hose"):
        for nd in o.active_material.node_tree.nodes:
            if nd.type == "MIX" and nd.data_type == "RGBA":
                nd.inputs[6].default_value = (*hexf("0f1c3a"), 1); nd.inputs[7].default_value = (*hexf("13244a"), 1)
        o.modifiers["versatz"].strength = .016
    elif o.name.endswith(("_hand", "_gesicht")):
        o.hide_render = True
for o in H.helm:
    o.hide_render = True
for o in H.stiefel:
    if "schaft" in o.name:
        o.scale.z *= .35
H.objekte = [o for o in H.objekte if o not in H.helm and not o.name.endswith(("_hand", "_gesicht"))]
BN = H.rig.data.bones
PEL = BN["upperleg01.L"].head_local.copy(); PEL.x = 0
SCH = {s: BN["upperarm01." + s].head_local.copy() for s in "LR"}
ARM = sum(BN[b + ".L"].length for b in ("upperarm01", "upperarm02", "lowerarm01", "lowerarm02"))
BEIN_Z = BN["upperleg01.L"].head_local.z
KNOECHEL = {s: BN["foot." + s].head_local.copy() for s in "LR"}

# ======================================================================  Materialien (ab hier)
STAHL = pbr("stahl", "Metal012", 6, rau_mul=.6, rau_add=.12, metal=1.0)
GUMMI = pbr("gummi", "Rubber004", 1.2, rau_mul=1.0)
HOLZ = pbr("holz", "WoodFloor041", .7, rau_mul=.9)
BETON = pbr("beton", "Concrete034", .25, tint="5a5a5e")
LEDER = pbr("leder", "Leather037", 6, tint="3a2a20", normal=.8)
STOFF_SITZ = pbr("sitzstoff", "Fabric030", 3, tint="1d2233")
SCHWARZLACK = mat("schwarzlack", "0b0b0d", .35, Coat_Weight=.4)
ALU = mat("alu_trav", "b9bec6", .3, 1)
SCHUH = mat("schuh", "101012", .5, Sheen_Weight=.3)
for o in H.stiefel:
    o.active_material = SCHUH
    o.scale.y *= .9

# HDRI fuer Reflexionen (sehr schwach, Arena ist dunkel)
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; nt = w.node_tree
env = nt.nodes.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(os.path.join(ASSET, "warehouse.hdr"))
nt.links.new(env.outputs[0], nt.nodes["Background"].inputs[0]); nt.nodes["Background"].inputs[1].default_value = .06
lp_ = nt.nodes.new("ShaderNodeLightPath"); mxw = nt.nodes.new("ShaderNodeMixShader"); dunkel = nt.nodes.new("ShaderNodeBackground")
dunkel.inputs[0].default_value = (.004, .005, .008, 1); bgo = nt.nodes["Background"]; outw = nt.nodes["World Output"]
nt.links.new(lp_.outputs["Is Camera Ray"], mxw.inputs[0]); nt.links.new(bgo.outputs[0], mxw.inputs[1]); nt.links.new(dunkel.outputs[0], mxw.inputs[2])
nt.links.new(mxw.outputs[0], outw.inputs[0])

# ======================================================================  Buehne + Plattform
box("buehne", (14, 12, .6), (0, 0, -.3), GUMMI, .02)
box("buehnenkante", (.05, 12, .05), (7.0, 0, -.03), emis("kantenlicht", "ff7a1a", 6), 0)
box("plattform_holz", (2.4, 1.3, .05), (-.15, 0, .025), HOLZ, .006)
for dy in (-1.1, 1.1):
    box("plattform_gummi", (2.4, .9, .05), (-.15, dy, .025), GUMMI, .006)
box("plattform_rahmen", (2.5, 3.2, .045), (-.15, 0, .02), STAHL, .01)
BODEN_Z = .05
box("hallenboden", (120, 120, .1), (0, 0, -.65), BETON, 0)

# ======================================================================  Stange + Scheiben
R_SCH = .225                          # Scheibenradius (45 cm)
STANGE = None


def radius_stange(y):
    a = abs(y)
    if a < .64:
        return .0135
    if a < .69:
        return .038 if .655 < a < .685 else .024
    if a < 1.12:
        return .025
    return .02


bm = bmesh.new(); ringe = []; NV = 24
ys = [-1.13 + i * .02 for i in range(int(2.26 / .02) + 1)]
for y in ys:
    r = radius_stange(y)
    ringe.append([bm.verts.new((r * math.cos(2 * P * k / NV), y, r * math.sin(2 * P * k / NV))) for k in range(NV)])
for a, b in zip(ringe, ringe[1:]):
    for k in range(NV):
        bm.faces.new((a[k], a[(k + 1) % NV], b[(k + 1) % NV], b[k]))
bm.faces.new(ringe[0][::-1]); bm.faces.new(ringe[-1])
me = bpy.data.meshes.new("stange"); bm.to_mesh(me); bm.free()
STANGE = bpy.data.objects.new("stange", me); sc.collection.objects.link(STANGE); me.materials.append(STAHL)
for p in me.polygons:
    p.use_smooth = True
STANGE.shape_key_add(name="basis")
sk = STANGE.shape_key_add(name="biegen")


def biegeprofil(y):
    return (max(0, abs(y) - .25) / .85) ** 2


for i, v in enumerate(me.vertices):
    sk.data[i].co = v.co + Vector((0, 0, -biegeprofil(v.co.y)))
# Riffelung (Raendelung) als Bump in der Mitte
nt = STAHL.node_tree; b = nt.nodes["Principled BSDF"]
wv = nt.nodes.new("ShaderNodeTexWave"); wv.inputs["Scale"].default_value = 400; wv.wave_type = "BANDS"
tc = nt.nodes.new("ShaderNodeTexCoord"); nt.links.new(tc.outputs["Object"], wv.inputs["Vector"])
bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = .25; bp.inputs["Distance"].default_value = .0008
nt.links.new(wv.outputs["Fac"], bp.inputs["Height"])
nmap = [nd for nd in nt.nodes if nd.type == "NORMAL_MAP"]
if nmap:
    nt.links.new(nmap[0].outputs[0], bp.inputs["Normal"])
nt.links.new(bp.outputs[0], b.inputs["Normal"])

# Scheiben (kalibrierte Stahlscheiben, lackiert): 8x rot 25, blau 20, gelb 15, gruen 10, Verschluss
FARBEN = [("rot", "c8161d", .225, .027)] * 8 + [("blau", "1946b8", .225, .026), ("gelb", "f2c200", .2, .022), ("gruen", "1f8a3a", .163, .02)]
lack = {}
for nm, f, r, d in FARBEN:
    if nm not in lack:
        m = mat("lack_" + nm, f, .3, Coat_Weight=.6)
        nt = m.node_tree; nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 80; nz.inputs["Detail"].default_value = 6
        mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = .22; mr.inputs["To Max"].default_value = .5
        nt.links.new(nz.outputs["Fac"], mr.inputs["Value"]); nt.links.new(mr.outputs[0], nt.nodes["Principled BSDF"].inputs["Roughness"])
        lack[nm] = m
SCHEIBEN_ME = {}


def scheibe(nm, r, d):
    key = (nm, r, d)
    if key not in SCHEIBEN_ME:
        prof = [(-d / 2, .026), (-d / 2, .07), (-d / 2 + .004, .085), (-d / 2 + .004, r - .02), (-d / 2, r - .012), (-d / 2 + .002, r - .003),
                (-d / 2 + .006, r), (d / 2 - .006, r), (d / 2 - .002, r - .003), (d / 2, r - .012), (d / 2 - .004, r - .02), (d / 2 - .004, .085),
                (d / 2, .07), (d / 2, .026), (-d / 2, .026)]
        o = dreh_koerper("scheibe_" + nm, prof, lack[nm])
        o.data.materials.append(STAHL)
        for p in o.data.polygons:                       # Nabe innen: Stahl
            if all(math.hypot(o.data.vertices[i].co.x, o.data.vertices[i].co.z) < .09 for i in p.vertices):
                p.material_index = 1
        SCHEIBEN_ME[key] = o.data
        bpy.data.objects.remove(o)
    o = bpy.data.objects.new("scheibe", SCHEIBEN_ME[key]); sc.collection.objects.link(o); return o


ENDE = {}
for s in (-1, 1):
    e = leer("ende%d" % s); ENDE[s] = e
    y = .705
    for nm, f, r, d in FARBEN:
        o = scheibe(nm, r, d); o.parent = e; o.location = (0, s * (y + d / 2 - .9), 0); y += d + .001
    v = zyl("verschluss", .045, .05, (0, s * (y + .025 - .9), 0), STAHL, rot=(P / 2, 0, 0), eltern=e)
    zyl("verschluss_hebel", .006, .09, (0, s * (y + .025 - .9), .06), SCHWARZLACK, eltern=e)

# Zughilfen (Straps) und Kreide
STRAP_M = mat("strap", "1b1b1b", .8, Sheen_Weight=.6)
STRAPS = []
for s in (-1, 1):
    bpy.ops.mesh.primitive_torus_add(major_radius=.018, minor_radius=.003, location=(0, s * .30, 0), rotation=(P / 2, 0, 0))
    t = bpy.context.object; t.scale = (1, 1, 1); t.data.materials.append(STRAP_M); t.parent = STANGE; STRAPS.append(t)
    for p in t.data.polygons:
        p.use_smooth = True
kreide_m = mat("kreide", "f4f4f0", .9)
zyl("kreideschale_fuss", .035, .9, (-1.4, 2.4, .5), STAHL)
schale = dreh_koerper("kreideschale", [(-.08, .02), (-.08, .2), (.02, .26), (.03, .265), (.03, .255), (-.06, .19), (-.06, 0)], STAHL)
schale.rotation_euler = (P / 2, 0, 0); schale.location = (-1.4, 2.4, .98)
zyl("kreide", .23, .02, (-1.4, 2.4, .99), kreide_m)

# ======================================================================  Arena: LED-Wand, Traversen, Moving Heads, Publikum
led = bpy.data.materials.new("led"); led.use_nodes = True; n = led.node_tree.nodes; l = led.node_tree.links
for k in list(n):
    n.remove(k)
out = n.new("ShaderNodeOutputMaterial"); em = n.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = 1.4
tc = n.new("ShaderNodeTexCoord"); nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.2; nz.inputs["Detail"].default_value = 3
l.new(tc.outputs["Object"], nz.inputs["Vector"]); LED_W = nz.inputs["W"] if "W" in nz.inputs else None
nz.noise_dimensions = "4D"; LED_W = nz.inputs["W"]
cr = n.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (*hexf("050a1c"), 1); cr.color_ramp.elements[1].color = (*hexf("d8460a"), 1)
cr.color_ramp.elements[0].position = .45; cr.color_ramp.elements[1].position = .9
# Pixelraster
vo = n.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 90; vo.feature = "DISTANCE_TO_EDGE"; l.new(tc.outputs["Object"], vo.inputs["Vector"])
mr = n.new("ShaderNodeMapRange"); mr.inputs["From Max"].default_value = .12; l.new(vo.outputs["Distance"], mr.inputs["Value"])
mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"; mx.inputs[0].default_value = 1
l.new(nz.outputs["Fac"], cr.inputs["Fac"]); l.new(cr.outputs[0], mx.inputs[6]); l.new(mr.outputs[0], mx.inputs[7])
l.new(mx.outputs[2], em.inputs["Color"]); l.new(em.outputs[0], out.inputs["Surface"])
box("ledwand", (.15, 16, 7), (-6.8, 0, 4.2), led, .01)
box("ledrahmen", (.3, 16.4, 7.4), (-6.95, 0, 4.2), SCHWARZLACK, .02)
# Anzeige mit Gewicht (Text-Objekt, leuchtend)
bpy.ops.object.text_add(location=(-6.65, 0, 5.9), rotation=(P / 2, 0, P / 2)); ANZ = bpy.context.object
ANZ.data.body = "511 KG"; ANZ.data.align_x = "CENTER"; ANZ.data.size = 1.5; ANZ.data.extrude = .02
ANZ.data.materials.append(emis("anzeige", "ffffff", 9))
# Fachwerk-Traverse (Segment einmal bauen, dann verknuepfte Kopien)


def traverse(name, laenge, b=.29):
    teile = []
    for dy in (-b / 2, b / 2):
        for dz in (-b / 2, b / 2):
            teile.append(rohr(name + "_gurt", (0, dy, dz), (laenge, dy, dz), .024, ALU))
    n_ = int(laenge / b)
    for i in range(n_):
        x0, x1 = i * b, (i + 1) * b
        for dy, dz, dy2, dz2 in ((-b / 2, -b / 2, -b / 2, b / 2), (b / 2, -b / 2, b / 2, b / 2), (-b / 2, -b / 2, b / 2, -b / 2), (-b / 2, b / 2, b / 2, b / 2)):
            teile.append(rohr(name + "_diag", (x0, dy, dz), (x1, dy2, dz2), .009, ALU))
    for o in teile:
        o.select_set(True)
    bpy.context.view_layer.objects.active = teile[0]; bpy.ops.object.join(); o = bpy.context.object; o.name = name
    bpy.ops.object.select_all(action="DESELECT")
    return o


tv = traverse("traverse_h", 18)
tv.location = (-4.5, -9, 8.5); tv.rotation_euler = (0, 0, P / 2)
for (x_, y_) in ((-4.5, -9.0), (-4.5, 9.0), (4.5, -9.0), (4.5, 9.0)):
    o = bpy.data.objects.new("traverse_v", tv.data); sc.collection.objects.link(o); o.location = (x_, y_, 0); o.rotation_euler = (0, -P / 2, 0)
    o.scale = (8.5 / 18, 1, 1)
o = bpy.data.objects.new("traverse_h2", tv.data); sc.collection.objects.link(o); o.location = (4.5, -9, 8.5); o.rotation_euler = (0, 0, P / 2)
# Moving Heads mit Lichtkegeln
KEGEL_M = bpy.data.materials.new("kegel"); KEGEL_M.use_nodes = True; n = KEGEL_M.node_tree.nodes; l = KEGEL_M.node_tree.links
for k in list(n):
    n.remove(k)
out = n.new("ShaderNodeOutputMaterial"); ad = n.new("ShaderNodeAddShader"); tr = n.new("ShaderNodeBsdfTransparent")
em = n.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (1, .86, .7, 1)
tc = n.new("ShaderNodeTexCoord"); sp = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Generated"], sp.inputs[0])
mr = n.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 0; mr.inputs["From Max"].default_value = 1
mr.inputs["To Min"].default_value = .0; mr.inputs["To Max"].default_value = .05; l.new(sp.outputs["Z"], mr.inputs["Value"])
lp = n.new("ShaderNodeLightPath"); mu = n.new("ShaderNodeMath"); mu.operation = "MULTIPLY"
l.new(mr.outputs[0], mu.inputs[0]); l.new(lp.outputs["Is Camera Ray"], mu.inputs[1]); l.new(mu.outputs[0], em.inputs["Strength"])
l.new(tr.outputs[0], ad.inputs[0]); l.new(em.outputs[0], ad.inputs[1]); l.new(ad.outputs[0], out.inputs["Surface"])
KOPF_M = mat("movinghead", "121214", .35, Coat_Weight=.3)
LINSE = emis("linse", "fff1dd", 60)
HEADS = []
for i, y_ in enumerate((-7, -4.5, -2, 2, 4.5, 7)):
    for x_ in (-4.5, 4.5):
        root = leer("mh", (x_, y_, 8.2))
        bg = box("mh_buegel", (.06, .42, .3), (0, 0, .15), KOPF_M, .02, eltern=root)
        kopf = leer("mh_kopf", (0, 0, 0), root)
        k_ = zyl("mh_gehaeuse", .16, .38, (0, 0, -.05), KOPF_M, eltern=kopf)
        zyl("mh_linse", .12, .01, (0, 0, -.245), LINSE, eltern=kopf)
        bpy.ops.mesh.primitive_cone_add(radius1=.12, radius2=1.0, depth=9, vertices=32, location=(0, 0, -4.75), rotation=(P, 0, 0))
        kg = bpy.context.object; kg.data.materials.append(KEGEL_M); kg.parent = kopf; kg.visible_shadow = False
        kg.visible_diffuse = False; kg.visible_glossy = False
        root["ph"] = i * .7 + (x_ > 0) * 1.3; root["kopf"] = kopf.name; HEADS.append((root, kopf))
# echte Spots auf den Heber
for (x_, y_, z_, e) in ((4.5, -3, 8, 2600), (4.5, 3, 8, 2600), (-4, 0, 8, 1800), (2, -6, 6, 1500), (0.5, 0, 9, 1200)):
    bpy.ops.object.light_add(type="SPOT", location=(x_, y_, z_)); L = bpy.context.object; L.data.energy = e * 4; L.data.spot_size = .55
    L.data.spot_blend = .5; L.data.shadow_soft_size = .3; L.data.color = (1, .93, .85)
    L.rotation_euler = (Vector((0, 0, .9)) - L.location).to_track_quat("-Z", "Y").to_euler()
bpy.ops.object.light_add(type="AREA", location=(-5, 0, 3)); L = bpy.context.object; L.data.size = 8; L.data.energy = 900; L.data.color = (1, .55, .25)
L.rotation_euler = (Vector((0, 0, 1)) - L.location).to_track_quat("-Z", "Y").to_euler()
# Publikum: Tribuene vorne (+x) und seitlich, runde Figuren
trib_m = mat("tribuene", "16171b", .8)
r = random.Random(3)
koerper_me = []
farben_pub = ["c62828", "1565c0", "f2f2f2", "2e7d32", "212121", "f9a825", "6a1b9a", "455a64"]
for i, f in enumerate(farben_pub):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=1, matrix=Matrix.Translation((0, 0, .5)) @ Matrix.Diagonal((.24, .17, .36, 1)))
    me = bpy.data.meshes.new("pubk%d" % i); bm.to_mesh(me); bm.free(); me.materials.append(mat("pub%d" % i, f, .8, Sheen_Weight=.4))
    for p in me.polygons:
        p.use_smooth = True
    koerper_me.append(me)
haut_ms = [mat("pubhaut%d" % i, c, .55) for i, c in enumerate(["8d5524", "c68642", "e0ac69", "f1c27d", "ffdbac"])]
kopf_me = []
for i, hm in enumerate(haut_ms):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=.105, matrix=Matrix.Translation((0, 0, .98)))
    me = bpy.data.meshes.new("pubh%d" % i); bm.to_mesh(me); bm.free(); me.materials.append(hm)
    for p in me.polygons:
        p.use_smooth = True
    kopf_me.append(me)
PUB = []; HANDY = []
handy_m = emis("handy", "ffffff", 25)
for reihe in range(22):
    rr = 9.5 + reihe * .85; hz = -.3 + reihe * .42
    box("stufe", (.85, 2 * rr * 1.1, .42), (rr + .2, 0, hz - .21), trib_m, 0, rot=(0, 0, 0))
    for j in range(int(2 * rr * 1.1 / .55)):
        y_ = -rr * 1.1 + .3 + j * .55 + r.uniform(-.06, .06)
        if r.random() < .08:
            continue
        p = Vector((rr + .25 + r.uniform(-.05, .05), y_, hz))
        for me_ in (r.choice(koerper_me), r.choice(kopf_me)):
            o = bpy.data.objects.new("pub", me_); sc.collection.objects.link(o); o.location = p; o.rotation_euler = (0, 0, P / 2 + r.uniform(-.3, .3))
            PUB.append(o)
        if r.random() < .05:
            h_ = box("handy", (.01, .05, .09), p + Vector((-.25, 0, 1.25)), handy_m, 0); h_["ph"] = r.random(); HANDY.append(h_)
for s in (-1, 1):
    for reihe in range(14):
        rr = 9.5 + reihe * .85; hz = -.3 + reihe * .42
        box("stufe_s", (16, .85, .42), (-1, s * (rr + .2), hz - .21), trib_m, 0)
        for j in range(26):
            x_ = -8.5 + j * .6 + r.uniform(-.06, .06)
            if r.random() < .1:
                continue
            p = Vector((x_, s * (rr + .25), hz))
            for me_ in (r.choice(koerper_me), r.choice(kopf_me)):
                o = bpy.data.objects.new("pub", me_); sc.collection.objects.link(o); o.location = p; o.rotation_euler = (0, 0, -s * P / 2 + r.uniform(-.3, .3))
# Kampfrichter-Tisch vorne + Kameramann-Stativ
box("tisch", (.8, 2.4, .75), (5.2, 0, .375), SCHWARZLACK, .02)
box("tischdecke", (.82, 2.42, .05), (5.2, 0, .77), mat("decke", "101010", .9, Sheen_Weight=.5), .01)

# ======================================================================  Hebe-Ablauf
T_SETUP0, T_SETUP1 = 8.7, 9.3          # in Position gehen
T_ZUG = 10.7                           # Zug beginnt
T_LOS = 13.2                           # Scheiben verlassen den Boden
T_OBEN = 15.6                          # Lockout
T_AB, T_UNTEN = 20.4, 20.85            # Absetzen
OFFMAX = .075
HAND_STEH = 0.0                        # wird unten berechnet

for bone, ziel, pol in (("lowerleg02.L", "fuss_L", "knie_L"), ("lowerleg02.R", "fuss_R", "knie_R"),
                        ("lowerarm02.L", "hand_L", "ell_L"), ("lowerarm02.R", "hand_R", "ell_R")):
    pass
ZIELE = {nm: leer("ik_" + nm) for nm in ("fuss_L", "fuss_R", "hand_L", "hand_R", "knie_L", "knie_R", "ell_L", "ell_R")}
IKC = {}
for bone, ziel, pol, pw in (("lowerleg02.L", "fuss_L", "knie_L", -P / 2), ("lowerleg02.R", "fuss_R", "knie_R", -P / 2),
                            ("lowerarm02.L", "hand_L", "ell_L", 0), ("lowerarm02.R", "hand_R", "ell_R", 0)):
    c = H.rig.pose.bones[bone].constraints.new("IK"); c.target = ZIELE[ziel]; c.chain_count = 4
    c.pole_target = ZIELE[pol]; c.pole_angle = pw; IKC[ziel] = c
FUSS_X = -.12
for s, nm in ((1, "L"), (-1, "R")):
    ZIELE["fuss_" + nm].location = (FUSS_X, s * .2, BODEN_Z + KNOECHEL[nm].z)
    ZIELE["knie_" + nm].location = (1.5, s * .5, .7)
    ZIELE["ell_" + nm].location = (-1.0, s * 1.0, 1.0)
GRIFF_Y = .30


def stange_hoehe(t):
    """Anhebung der Stangenmitte (m) und Biegung an den Enden (m)"""
    if t < T_ZUG:
        h = 0.0
    elif t < T_LOS:
        h = OFFMAX * ease((t - T_ZUG) / (T_LOS - T_ZUG)) ** .8
    elif t < T_OBEN:
        k = (t - T_LOS) / (T_OBEN - T_LOS); k = k - .06 * math.sin(2 * P * k)      # Haenger in der Mitte
        h = OFFMAX + (HUB - OFFMAX) * ease(k)
    elif t < T_AB:
        h = HUB
    elif t < T_UNTEN:
        h = HUB * (1 - ((t - T_AB) / (T_UNTEN - T_AB)) ** 2)
    else:
        h = 0.0
    if t < T_LOS:
        off = h
    elif t < T_AB:
        off = OFFMAX - (OFFMAX - .045) * ease((t - T_LOS) / .7)
    elif t < T_UNTEN:
        off = .045
    else:
        off = .045 * math.exp(-(t - T_UNTEN) * 9) * math.cos((t - T_UNTEN) * 40)
    return h, off


def koerper_pose(t, zb):
    """Becken-Position und Vorneigung so, dass die Arme gestreckt zur Stange reichen."""
    if t < T_SETUP0 or t >= T_UNTEN:
        return None
    if t < T_SETUP1:
        p = 0.0; k0 = ease((t - T_SETUP0) / (T_SETUP1 - T_SETUP0))
    else:
        k0 = 1.0
        p = max(0.0, min(1.0, (zb - (R_SCH + BODEN_Z)) / HUB))
    lean = (1.02 - 1.12 * ease((p - .15) / .85)) * k0
    px = -.34 + .2 * ease(p)
    R_ = Euler((lean, 0, P / 2)).to_matrix()
    sh = R_ @ (SCH["L"] - PEL)
    grip = Vector((0, GRIFF_Y, zb + .03))
    dy = abs(grip.y) - abs(sh.y); dx = grip.x - (px + sh.x)
    rest = max(.0, (ARM * .985) ** 2 - dx * dx - dy * dy)
    pz = zb + .03 + math.sqrt(rest) - sh.z
    pz = min(pz, BODEN_Z + BEIN_Z - .004)
    if k0 < 1:
        pz = (1 - k0) * (BODEN_Z + BEIN_Z) + k0 * pz; px = (1 - k0) * (-.34) + k0 * px
    return lean, Vector((px, 0, pz))


def figuren(t):
    h, off = stange_hoehe(t)
    zb = BODEN_Z + R_SCH + h
    STANGE.location = (0, 0, zb); STANGE.data.shape_keys.key_blocks["biegen"].value = off / biegeprofil(.9)
    for s, e in ENDE.items():
        b9 = biegeprofil(.9) * STANGE.data.shape_keys.key_blocks["biegen"].value
        steig = 2 * (.9 - .25) / .85 ** 2 * STANGE.data.shape_keys.key_blocks["biegen"].value
        e.location = (0, s * .9, zb - b9); e.rotation_euler = (s * math.atan(steig), 0, 0)
    H.zuruecksetzen()
    pose = koerper_pose(t, zb)
    for c in IKC.values():
        c.influence = 1.0
    if pose is None:
        # stehen (vor dem Zug: Kreide/Konzentration; nach dem Absetzen: Jubel)
        H.rig.rotation_euler = (0, 0, P / 2); H.rig.location = (-.45, 0, BODEN_Z)
        IKC["hand_L"].influence = 0; IKC["hand_R"].influence = 0
        if t >= T_UNTEN:
            k = ease((t - T_UNTEN - .2) / .6)
            H.dreh("upperarm01.L", z=-.72 + 3.3 * k, x=.25 * k); H.dreh("upperarm01.R", z=.72 - 3.3 * k, x=.25 * k)
            H.dreh("lowerarm01.L", x=-.5 * k); H.dreh("lowerarm01.R", x=-.5 * k); H.dreh("neck01", x=-.35 * k)
            for f in range(1, 6):
                for g in (1, 2, 3):
                    H.dreh(f"finger{f}-{g}.L", x=.9 * k); H.dreh(f"finger{f}-{g}.R", x=.9 * k)
        else:
            atm = math.sin(t * 1.6) * .03
            H.dreh("upperarm01.L", z=-.66 + atm); H.dreh("upperarm01.R", z=.66 - atm)
            H.dreh("lowerarm01.L", x=-.25); H.dreh("lowerarm01.R", x=-.25); H.dreh("neck01", x=.15 + .05 * math.sin(t * .7))
    else:
        lean, pel = pose
        R_ = Euler((lean, 0, P / 2)).to_matrix()
        H.rig.rotation_euler = (lean, 0, P / 2); H.rig.location = pel - R_ @ PEL
        for s, nm in ((1, "L"), (-1, "R")):
            ZIELE["hand_" + nm].location = (-.015, s * GRIFF_Y, zb + .045)
        H.dreh("neck01", x=-.45 * min(1, lean)); H.dreh("neck02", x=-.2 * min(1, lean)); H.dreh("head", x=-.1)
        for f in range(1, 6):
            for g in (1, 2, 3):
                H.dreh(f"finger{f}-{g}.L", x=1.25 if f > 1 else .5); H.dreh(f"finger{f}-{g}.R", x=1.25 if f > 1 else .5)
    bpy.context.view_layer.update()


# Hub = Stangenhoehe bei aufrechtem Stand (Handgelenk bei haengenden Armen) - Startlage
H.zuruecksetzen(); H.rig.rotation_euler = (0, 0, P / 2); H.rig.location = (0, 0, BODEN_Z)
H.dreh("upperarm01.L", z=-.72); H.dreh("upperarm01.R", z=.72); bpy.context.view_layer.update()
pb = H.rig.pose.bones["wrist.L"]; HAND_STEH = (H.rig.matrix_world @ pb.head).z
HUB = HAND_STEH - .03 - (BODEN_Z + R_SCH) - .02
print("HUB", HUB, "ARM", ARM)

# Gurt (Leder, Schnalle) am Rumpf
H.zuruecksetzen(); H.rig.location = (0, 0, 0); H.rig.rotation_euler = (0, 0, 0); bpy.context.view_layer.update()
gz = BN["spine05"].tail_local.z + .03
bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=False, segments=48, radius1=.2, radius2=.2, depth=.12)
me = bpy.data.meshes.new("gurt"); bm.to_mesh(me); bm.free()
gurt = bpy.data.objects.new("gurt", me); sc.collection.objects.link(gurt); me.materials.append(LEDER)
# Gurt-Form an Rumpfquerschnitt anpassen (Ellipse aus Koerper-Vertices auf Gurthoehe)
vs = [v for v in H.EV if abs(v.z - gz) < .02 and abs(v.x) < .24]
if vs:
    xs = [v.x for v in vs]; ys_ = [v.y for v in vs]
    gurt.scale = ((max(xs) - min(xs)) / 2 / .2 + .03, (max(ys_) - min(ys_)) / 2 / .2 + .04, 1)
    gurt.location = (0, (max(ys_) + min(ys_)) / 2, gz)
so = gurt.modifiers.new("s", "SOLIDIFY"); so.thickness = .012; glatt(gurt, 1)
schnalle = box("schnalle", (.09, .02, .08), (0, gurt.location.y - gurt.scale.y * .2 - .012, gz), STAHL, .006)
bpy.context.view_layer.update()
for o in (gurt, schnalle):
    bn = H.rig.data.bones["spine04"]
    o.parent = H.rig; o.parent_type = "BONE"; o.parent_bone = "spine04"
    o.matrix_parent_inverse = (H.rig.matrix_world @ bn.matrix_local @ Matrix.Translation((0, bn.length, 0))).inverted()

# ======================================================================  Kamera
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam
cam.data.clip_start = .03; cam.data.clip_end = 500; cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
cam.data.dof.use_dof = True
SZ = [
    (0.00, 1.40, (1.6, -1.3, .35), (1.5, -1.2, .38), (0, -.2, .95), (0, -.2, .95), 26),          # Aufhaenger (Zeitlupe, Stange gebogen)
    (1.40, 3.00, (.45, -1.65, .33), (.3, -1.55, .31), (0, -.85, .24), (0, -.9, .24), 35),          # Scheiben nah
    (3.00, 4.50, (6, -3, 3.2), (5.4, -2.6, 2.9), (0, 0, .8), (0, 0, .8), 30),                      # hoch vorne
    (4.50, 6.90, (24, -10, 9), (21, -6, 8.4), (0, 0, 2.0), (0, 0, 2.0), 22),                       # Arena weit
    (6.90, 7.85, (.9, -1.0, 1.4), (.85, -.9, 1.35), (-.45, 0, 1.25), (-.45, 0, 1.25), 40),        # Anzug
    (7.85, 9.00, (.45, -.75, 1.05), (.4, -.7, 1.02), (-.45, 0, .98), (-.45, 0, .98), 45),         # Gurt
    (9.00, 10.60, (.65, -.8, .5), (.6, -.75, .45), (0, -.3, .3), (0, -.3, .3), 35),               # Griff + Straps
    (10.60, 11.90, (1.8, .15, .45), (1.7, .12, .5), (0, 0, .95), (0, 0, 1.0), 30),                # Zug von vorne
    (11.90, 13.40, (.4, -1.95, .26), (.38, -1.9, .27), (0, -.85, .27), (0, -.85, .29), 40),       # Biegung, Scheiben noch am Boden
    (13.40, 15.30, (.3, -4.3, .9), (.4, -4.1, 1.0), (-.1, 0, .85), (-.1, 0, .9), 30),             # seitlich weit
    (15.30, 17.20, (1.4, -1.0, .22), (1.3, -.85, .28), (-.3, 0, 1.3), (-.3, 0, 1.3), 22),         # Held von unten
    (17.20, 19.40, (-2.2, -.7, 1.7), (-2.0, -.4, 1.6), (2, 0, 1.1), (2, 0, 1.1), 26),             # hinten, Richtung Publikum
    (19.40, 20.70, (1.3, -1.0, 1.7), (1.25, -.95, 1.68), (-.12, 0, 1.5), (-.12, 0, 1.5), 45),     # Kopf nah
    (20.70, 22.90, (5, 1.6, 1.6), (4.5, 1.3, 1.5), (0, 0, .9), (0, 0, 1.0), 28),                  # Absetzen weit
    (22.90, 25.80, (2.6, -2.1, 1.2), (9, -7.5, 4.2), (-.4, 0, 1.3), (-.4, 0, 1.6), 26),           # Jubel, Rueckfahrt
]


def zustand(t):
    for s in SZ:
        if s[0] <= t < s[1]:
            break
    k = (t - s[0]) / (s[1] - s[0]); k = ease(k) * .7 + k * .3
    ts = 13.9 + t * .45 if t < 1.4 else t
    figuren(ts)
    pos = lerpv(s[2], s[3], k); ziel = lerpv(s[4], s[5], k)
    cam.location = pos; d = ziel - pos; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = s[6]; cam.data.dof.focus_distance = d.length; cam.data.dof.aperture_fstop = 2.0 if d.length < 3 else 4.5
    zit = .0025
    cam.location += Vector((zit * math.sin(t * 7.3), zit * math.cos(t * 5.1), zit * math.sin(t * 9.7)))
    LED_W.default_value = t * .15
    ANZ.hide_render = ts < T_OBEN
    for root, kopf in HEADS:
        ph = root["ph"]
        root.rotation_euler.z = .5 * math.sin(t * .4 + ph)
        kopf.rotation_euler.x = .45 + .25 * math.sin(t * .55 + ph * 1.7)
    rate = .25 if T_OBEN <= ts < 24 else .04
    for h_ in HANDY:
        h_.hide_render = ((t * 2.2 + h_["ph"] * 13) % 1) > (.9 if T_OBEN <= ts else .25)


os.makedirs(A.ordner, exist_ok=True)
N = int(round(D * A.fps))
liste = [int(round(float(x) * A.fps)) for x in A.nur.split(",")] if A.nur else list(range(A.start, N))
for f in liste:
    pfad = os.path.join(A.ordner, f"heben_{f:04d}.png")
    if os.path.exists(pfad) and not A.nur:
        continue
    zustand(f / A.fps); bpy.context.view_layer.update(); zustand(f / A.fps)
    sc.render.filepath = pfad
    bpy.ops.render.render(write_still=True); print("FERTIG", pfad, flush=True)
