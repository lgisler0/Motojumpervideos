"""SPEED-KLETTERN 5,99 s (Emma Hunt, Krakau 4.7.2026, World Climbing). Helfer aus heben3d.py. Alt: eine Stange heben - 511 kg Kreuzheben (Raul Flores, World Deadlift Championships,
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
D = 24.7
ASSET = os.path.join(os.path.dirname(HIER), "assets")
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = A.samples; sc.cycles.use_denoising = True
sc.cycles.max_bounces = 5; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 3; sc.cycles.transmission_bounces = 2
sc.cycles.transparent_max_bounces = 8; sc.cycles.adaptive_threshold = .03
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1080, 1920, A.skala
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"; sc.view_settings.exposure = -.8
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

# ======================================================================  Kletterinnen (echte Menschen) - zuerst, Materialien danach
import mensch_echt as ME
LOGO = ME.logo_bild(os.path.join(HIER, "_logo_norda.png"), "NORDA", farbe=(1, 1, 1))
BIB1 = ME.logo_bild(os.path.join(HIER, "_bib_kl1.png"), "17", farbe=(.05, .05, .05), symbol=False, hintergrund=(.97, .97, .95), num=True, unterzeile="SPEED")
BIB2 = ME.logo_bild(os.path.join(HIER, "_bib_kl2.png"), "24", farbe=(.05, .05, .05), symbol=False, hintergrund=(.97, .97, .95), num=True, unterzeile="SPEED")
K1 = ME.mensch("hunt", 63, 0.0, .3, .75, .25, haut="caucasian", haare="ponytail01", braue="eyebrow010", haarfarbe="6b4a2e")
ME.trikot(K1, "lang", "tights", "1f3f8f", "111318", brust=BIB1, brust_mass=(.15, .1), bein=LOGO)
K2 = ME.mensch("gegner", 88, 0.0, .3, .7, .2, haut="asian", haare="ponytail01", braue="eyebrow011", haarfarbe="0b0908")
ME.trikot(K2, "lang", "tights", "c2261e", "111318", brust=BIB2, brust_mass=(.15, .1), bein=LOGO)
for K in (K1, K2):
    for o in K.huellen:
        if "versatz" in o.modifiers:
            o.modifiers["versatz"].strength = .017 if o.name.endswith("_hemd") else .010
        for md in o.modifiers:
            if md.type == "SUBSURF":
                md.render_levels = 2
    hoehe = max(v.z for v in K.EV); K.SK = 1.66 / hoehe; K.rig.scale = (K.SK,) * 3
    K.PEL = K.rig.data.bones["upperleg01.L"].head_local.copy(); K.PEL.x = 0
print("ok menschen")

# ======================================================================  Materialien
STAHL = pbr("stahl", "Metal012", 6, rau_mul=.6, rau_add=.15, metal=1.0)
GUMMI = pbr("gummi", "Rubber004", 1.2)
BETON = pbr("beton", "Concrete034", .25, tint="4a4a4e")
MATTE = pbr("matte", "Fabric048", 1.0, tint="1f4fb4", normal=1.2)
GRIFF = mat("griff", "c8121a", .55, Coat_Weight=.15)
SCHWARZ = mat("schwarzlack", "0d0d0f", .4, Coat_Weight=.3)
GURT = mat("klettergurt", "1a1a1a", .7, Sheen_Weight=.4)
SEIL = mat("seil", "f0c419", .6, Sheen_Weight=.5)
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; nt = w.node_tree
env = nt.nodes.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(os.path.join(ASSET, "kletterhalle.hdr"))
nt.links.new(env.outputs[0], nt.nodes["Background"].inputs[0]); nt.nodes["Background"].inputs[1].default_value = .5
lp_ = nt.nodes.new("ShaderNodeLightPath"); mxw = nt.nodes.new("ShaderNodeMixShader"); dunkel = nt.nodes.new("ShaderNodeBackground")
dunkel.inputs[0].default_value = (.01, .012, .02, 1)
nt.links.new(lp_.outputs["Is Camera Ray"], mxw.inputs[0]); nt.links.new(nt.nodes["Background"].outputs[0], mxw.inputs[1])
nt.links.new(dunkel.outputs[0], mxw.inputs[2]); nt.links.new(mxw.outputs[0], nt.nodes["World Output"].inputs[0])

# ======================================================================  Speed-Wand (4 Bahnen, 15 m, 5 Grad Ueberhang)
NEIG = math.radians(5)
WAND_H = 15.0
BAHNEN = (-4.5, -1.5, 1.5, 4.5)
HB, GB_ = -1.5, 1.5            # Bahn Hunt / Gegnerin


def wand_y(z):
    return -z * math.tan(NEIG)


wand_m = bpy.data.materials.new("wand"); wand_m.use_nodes = True; n = wand_m.node_tree.nodes; l = wand_m.node_tree.links; b = n["Principled BSDF"]
pfad = os.path.join(ASSET, "PaintedPlaster017", "PaintedPlaster017_1K-JPG")
tc = n.new("ShaderNodeTexCoord"); mp = n.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (.6, .6, .6); l.new(tc.outputs["Object"], mp.inputs[0])
tcol = n.new("ShaderNodeTexImage"); tcol.image = bpy.data.images.load(pfad + "_Color.jpg"); tcol.projection = "BOX"; l.new(mp.outputs[0], tcol.inputs[0])
tn = n.new("ShaderNodeTexImage"); tn.image = bpy.data.images.load(pfad + "_NormalGL.jpg"); tn.image.colorspace_settings.name = "Non-Color"; tn.projection = "BOX"
l.new(mp.outputs[0], tn.inputs[0]); nm_ = n.new("ShaderNodeNormalMap"); nm_.inputs["Strength"].default_value = .6; l.new(tn.outputs[0], nm_.inputs["Color"])
sp = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Object"], sp.inputs[0])
# Plattenfugen (1.5 m) und Gewindeloch-Raster (12.5 cm)
def modrange(src, per, breite):
    m1 = n.new("ShaderNodeMath"); m1.operation = "PINGPONG"; m1.inputs[1].default_value = per / 2; l.new(src, m1.inputs[0])
    m2 = n.new("ShaderNodeMath"); m2.operation = "LESS_THAN"; m2.inputs[1].default_value = breite; l.new(m1.outputs[0], m2.inputs[0]); return m2
fx = modrange(sp.outputs["X"], 1.5, .006); fz = modrange(sp.outputs["Z"], 1.5, .006)
fuge = n.new("ShaderNodeMath"); fuge.operation = "MAXIMUM"; l.new(fx.outputs[0], fuge.inputs[0]); l.new(fz.outputs[0], fuge.inputs[1])
lx = modrange(sp.outputs["X"], .125, .007); lz = modrange(sp.outputs["Z"], .125, .007)
loch = n.new("ShaderNodeMath"); loch.operation = "MULTIPLY"; l.new(lx.outputs[0], loch.inputs[0]); l.new(lz.outputs[0], loch.inputs[1])
# Bahnfarben: abwechselnd Dunkelblau / Anthrazit
bf = n.new("ShaderNodeMath"); bf.operation = "PINGPONG"; bf.inputs[1].default_value = 3.0; l.new(sp.outputs["X"], bf.inputs[0])
bf2 = n.new("ShaderNodeMath"); bf2.operation = "GREATER_THAN"; bf2.inputs[1].default_value = 1.5; l.new(bf.outputs[0], bf2.inputs[0])
fa = n.new("ShaderNodeMix"); fa.data_type = "RGBA"; fa.inputs[6].default_value = (*hexf("1a2f6b"), 1); fa.inputs[7].default_value = (*hexf("2a2d33"), 1)
l.new(bf2.outputs[0], fa.inputs[0])
mul = n.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs[0].default_value = .8
l.new(fa.outputs[2], mul.inputs[6]); l.new(tcol.outputs[0], mul.inputs[7])
m3 = n.new("ShaderNodeMix"); m3.data_type = "RGBA"; m3.inputs[7].default_value = (.02, .02, .025, 1); l.new(fuge.outputs[0], m3.inputs[0]); l.new(mul.outputs[2], m3.inputs[6])
m4 = n.new("ShaderNodeMix"); m4.data_type = "RGBA"; m4.inputs[7].default_value = (.01, .01, .01, 1); l.new(loch.outputs[0], m4.inputs[0]); l.new(m3.outputs[2], m4.inputs[6])
l.new(m4.outputs[2], b.inputs["Base Color"]); l.new(nm_.outputs[0], b.inputs["Normal"]); b.inputs["Roughness"].default_value = .75
bpy.ops.mesh.primitive_plane_add(size=1); wand = bpy.context.object; wand.name = "wand"; wand.scale = (12.4, WAND_H, 1)
bpy.ops.object.transform_apply(scale=True); wand.rotation_euler = (P / 2 + NEIG, 0, 0); wand.location = (0, wand_y(WAND_H / 2) + .0, WAND_H / 2)
wand.data.materials.append(wand_m)
so = wand.modifiers.new("s", "SOLIDIFY"); so.thickness = .3; so.offset = -1
box("wand_rahmen_o", (12.8, 1.0, .4), (0, wand_y(WAND_H) + .3, WAND_H + .2), SCHWARZ, .02)
for x_ in (-6.3, 6.3):
    box("wand_rahmen_s", (.3, .6, WAND_H + .6), (x_, wand_y(WAND_H / 2) + .25, WAND_H / 2 + .1), SCHWARZ, .02, rot=(NEIG, 0, 0))
for x_ in (-3.0, 0.0, 3.0):          # Bahntrennung
    box("bahnlinie", (.04, .02, WAND_H), (x_, wand_y(WAND_H / 2) - .012, WAND_H / 2), mat("bahnweiss", "e8e8e8", .5) if not bpy.data.materials.get("bahnweiss") else bpy.data.materials["bahnweiss"], 0, rot=(NEIG, 0, 0))


def wandpunkt(x, z, ab=0.0):
    return Vector((x, wand_y(z) - ab, z))


# Griffe (genormte Route, auf allen Bahnen gleich) - Drehkoerper mit Delle, Schraube
def griff_mesh(gross):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=1)
    for v in bm.verts:
        x, y, z = v.co
        y = min(y, .1) if y > 0 else y                       # flache Rueckseite (zur Wand)
        sx, sz = (.16, .11) if gross else (.07, .05)
        dy = .055 if gross else .03
        v.co = Vector((x * sx * (1 + .25 * z), -abs(y) * dy - .005, z * sz + .03 * x * gross))
    me = bpy.data.meshes.new("griff_g" if gross else "griff_k"); bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(GRIFF); return me


GRIFF_G, GRIFF_K = griff_mesh(True), griff_mesh(False)
rr = random.Random(2)
HAENDE = [(-.05, 1.55)]
seite = 1
z = 1.55
while z < 14.2:
    z += rr.uniform(.72, .9); seite *= -1
    HAENDE.append((seite * rr.uniform(.25, .48) + rr.uniform(-.06, .06), z))
FUESSE = [(-.22, .32), (.2, .55)]
z = .55
while z < 13.4:
    z += rr.uniform(.8, 1.0)
    FUESSE.append((rr.uniform(-.35, .35), z))
for bx in BAHNEN:
    for (gx, gz) in HAENDE:
        o = bpy.data.objects.new("griff", GRIFF_G); sc.collection.objects.link(o)
        o.location = wandpunkt(bx + gx, gz); o.rotation_euler = (NEIG, rr.uniform(-.5, .5), 0)
    for (gx, gz) in FUESSE:
        o = bpy.data.objects.new("tritt", GRIFF_K); sc.collection.objects.link(o)
        o.location = wandpunkt(bx + gx, gz); o.rotation_euler = (NEIG, rr.uniform(-.8, .8), 0)
    # Top-Taster mit Leuchtrand, Seilautomat, Startplatten, Startampel
    box("toptaster", (.45, .06, .35), wandpunkt(bx, WAND_H - .25, .04), mat("taster", "f2f2f2", .4) if not bpy.data.materials.get("taster") else bpy.data.materials["taster"], .02, rot=(NEIG, 0, 0))
    box("toptaster_rand", (.49, .05, .39), wandpunkt(bx, WAND_H - .25, .02), emis("tasterlicht", "ff2a2a", 6) if not bpy.data.materials.get("tasterlicht") else bpy.data.materials["tasterlicht"], .01, rot=(NEIG, 0, 0))
    box("seilautomat", (.32, .3, .42), wandpunkt(bx + .4, WAND_H + .35, .2), mat("automat", "e5e5e5", .35, Coat_Weight=.4) if not bpy.data.materials.get("automat") else bpy.data.materials["automat"], .05)
    for dx in (-.25, .25):
        box("startplatte", (.36, .5, .05), (bx + dx, -.42, .045), STAHL, .01)
    box("ampel", (.18, .1, .44), (bx - 1.0, -.3, 2.2), SCHWARZ, .02)
LICHT_R, LICHT_G = [], []
for bx in BAHNEN:
    a = zyl("ampel_rot", .05, .02, (bx - 1.0, -.36, 2.33), emis("ampelrot", "ff1010", 25) if not bpy.data.materials.get("ampelrot") else bpy.data.materials["ampelrot"], rot=(P / 2, 0, 0)); LICHT_R.append(a)
    g = zyl("ampel_gruen", .05, .02, (bx - 1.0, -.36, 2.1), emis("ampelgruen", "10ff40", 25) if not bpy.data.materials.get("ampelgruen") else bpy.data.materials["ampelgruen"], rot=(P / 2, 0, 0)); LICHT_G.append(g)
# Zeit-Anzeigen ueber den Bahnen (Text)
ANZ = {}
for bx in (HB, GB_):
    box("anzeige", (1.3, .1, .5), (bx, wand_y(WAND_H) - .1, WAND_H + 1.0), SCHWARZ, .02)
    bpy.ops.object.text_add(location=(bx, wand_y(WAND_H) - .17, WAND_H + .88), rotation=(P / 2, 0, 0)); t = bpy.context.object
    t.data.body = "0.00"; t.data.align_x = "CENTER"; t.data.size = .34; t.data.extrude = .004
    t.data.materials.append(emis("anzeigetext", "ffb020", 14) if not bpy.data.materials.get("anzeigetext") else bpy.data.materials["anzeigetext"]); ANZ[bx] = t
# Boden: Halle + Fallschutzmatte vor der Wand
box("hallenboden", (120, 120, .1), (0, -20, -.05), BETON, 0)
box("fallschutz", (13, 4.2, .3), (0, -2.35, .15), MATTE, .06, seg=4)
# Seile (vom Automaten zum Gurt)
SEILE = {HB: zyl("seil", .006, 1, (0, 0, 0), SEIL, v=8), GB_: zyl("seil", .006, 1, (0, 0, 0), SEIL, v=8)}
# Licht: Flaechenlichter auf die Wand + Gegenlicht
for (x_, y_, z_, e) in ((-6, -14, 12, 9000), (6, -14, 12, 9000), (0, -10, 3, 3000), (0, -18, 20, 7000)):
    bpy.ops.object.light_add(type="AREA", location=(x_, y_, z_)); L_ = bpy.context.object; L_.data.size = 6; L_.data.energy = e * .9
    L_.rotation_euler = (Vector((0, 0, 7)) - L_.location).to_track_quat("-Z", "Y").to_euler(); L_.data.color = (1, .96, .9)
# Publikum: Tribuene gegenueber der Wand + LED-Band
trib_m = mat("tribuene", "16171b", .8)
r = random.Random(3)
koerper_me = []
for i, f in enumerate(["c62828", "1565c0", "f2f2f2", "2e7d32", "212121", "f9a825", "6a1b9a", "455a64"]):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=7, radius=1, matrix=Matrix.Translation((0, 0, .45)) @ Matrix.Diagonal((.24, .17, .34, 1)))
    bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=7, radius=.1, matrix=Matrix.Translation((0, 0, .93)))
    me = bpy.data.meshes.new("pub%d" % i); bm.to_mesh(me); bm.free(); me.materials.append(mat("pubm%d" % i, f, .8, Sheen_Weight=.4))
    for p in me.polygons:
        p.use_smooth = True
    koerper_me.append(me)
for reihe in range(16):
    yy = -14 - reihe * .85; hz = .2 + reihe * .45
    box("stufe", (34, .85, .45), (0, yy, hz - .22), trib_m, 0)
    for j in range(56):
        if r.random() < .1:
            continue
        o = bpy.data.objects.new("pub", r.choice(koerper_me)); sc.collection.objects.link(o)
        o.location = (-16.5 + j * .6 + r.uniform(-.05, .05), yy, hz); o.rotation_euler = (0, 0, P + r.uniform(-.3, .3))
box("ledband", (34, .1, .5), (0, -13.6, .45), emis("ledband", "ff6a1a", 3), .01)
for x_ in (-12, 12):
    box("seitenwand", (.3, 30, 22), (x_ * 1.6, -10, 11), mat("hallenwand", "202227", .8), 0)
box("hallendach", (60, 40, .3), (0, -10, 23), mat("dach", "15171b", .8), 0)
# ======================================================================  Bewegung: IK an Griffe
T_GRUEN = 10.85
for K in (K1, K2):
    K.Z = {nm: leer(K.name + "_ik_" + nm) for nm in ("hand_L", "hand_R", "fuss_L", "fuss_R", "knie_L", "knie_R", "ell_L", "ell_R")}
    K.IK = {}
    for bone, ziel, pol, pw in (("lowerarm02.L", "hand_L", "ell_L", 0), ("lowerarm02.R", "hand_R", "ell_R", 0),
                                ("lowerleg02.L", "fuss_L", "knie_L", -P / 2), ("lowerleg02.R", "fuss_R", "knie_R", -P / 2)):
        c = K.rig.pose.bones[bone].constraints.new("IK"); c.target = K.Z[ziel]; c.chain_count = 4
        c.pole_target = K.Z[pol]; c.pole_angle = pw; K.IK[ziel] = c
K1.DAUER, K2.DAUER = 5.99, 6.42
K1.BX, K2.BX = HB, GB_


def fortschritt(K, t):
    """0..1 Hoehenfortschritt; schneller Start, fast gleichmaessig"""
    k = (t - T_GRUEN) / K.DAUER
    if k <= 0:
        return 0.0
    if k >= 1:
        return 1.0
    return .82 * k + .18 * (1 - (1 - k) ** 3)


PEL_START, PEL_TOP = .95, 13.95


def halte(liste, pz, reichweite, seite):
    """Index des aktuell gehaltenen Griffs fuer eine Seite (Hand/Fuss wechselt ab)"""
    beste = None
    for i, (gx, gz) in enumerate(liste):
        if (i % 2 == 0) == (seite == "L") or i == 0:
            if gz <= pz + reichweite:
                beste = i
    return beste if beste is not None else 0


def griff_pos(K, liste, i, ab):
    gx, gz = liste[i]; return wandpunkt(K.BX + gx, gz, ab)


def kletter_pose(K, t):
    f = fortschritt(K, t)
    pz = PEL_START + (PEL_TOP - PEL_START) * f
    tf = t - T_GRUEN
    # Haende: Griff im Bereich bis 0.95 ueber Becken; Bewegung zum naechsten in .16 s Bogen
    ziele = {}
    for sd in ("L", "R"):
        for art, liste, reich, ab, dauer in (("hand", HAENDE, 1.0, .07, .16), ("fuss", FUESSE, -.32, .06, .14)):
            i = halte(liste, pz, reich, sd)
            alt = griff_pos(K, liste, i, ab)
            # Vorgriff: wenn der naechste Griff dieser Seite bald erreicht wird, schon unterwegs
            pz2 = PEL_START + (PEL_TOP - PEL_START) * fortschritt(K, t + dauer)
            j = halte(liste, pz2, reich, sd)
            if j != i and tf > 0:
                k = 1 - (pz2 - pz) and 0
                # Anteil der Bewegung: wie weit pz zwischen Ausloesung und Ankunft
                lo = liste[j][1] - reich
                k = max(0, min(1, 1 - (lo - pz) / max(1e-4, pz2 - pz)))
                neu = griff_pos(K, liste, j, ab)
                p = alt.lerp(neu, ease(k)); p.y -= .12 * math.sin(k * P)
            else:
                p = alt
            ziele[art + "_" + sd] = p
    if f >= 1:                                    # Abschlagen des Top-Tasters mit rechts
        ziele["hand_R"] = wandpunkt(K.BX, WAND_H - .25, .1)
    px = K.BX + .08 * math.sin(tf * 9) + .5 * ((ziele["hand_L"].x + ziele["hand_R"].x) / 2 - K.BX)
    pel = Vector((px, wand_y(pz) - .36, pz))
    return pel, ziele


def setze(K, rq, pel):
    K.rig.rotation_mode = "QUATERNION"; K.rig.rotation_quaternion = rq
    K.rig.location = pel - rq.to_matrix() @ (K.PEL * K.SK)


def q(rx=0, ry=0, rz=0):
    return Euler((rx, ry, rz)).to_quaternion()


def figur(K, t):
    K.zuruecksetzen()
    for c in K.IK.values():
        c.influence = 1.0
    rq_wand = q(rz=P) @ q(rx=NEIG * 0 - .05)                    # Gesicht zur Wand (+y)
    t_top = T_GRUEN + K.DAUER
    if t < T_GRUEN - 2.2:                                     # bereitmachen: stehen vor der Wand, lockern
        w = math.sin(t * 2.0)
        for c in K.IK.values():
            c.influence = 0
        setze(K, rq_wand, Vector((K.BX + .05 * w, -1.1, K.PEL.z * K.SK)))
        K.dreh("upperarm01.L", z=-.6 + .1 * w); K.dreh("upperarm01.R", z=.6 - .1 * w); K.dreh("neck01", x=-.25)
        K.dreh("lowerarm01.L", x=-.3); K.dreh("lowerarm01.R", x=-.3)
    elif t < T_GRUEN:                                         # Startposition: Fuss auf Platte, Hand am ersten Griff
        pel = Vector((K.BX, -.62, .98))
        setze(K, q(rz=P) @ q(rx=.18), pel)
        for sd, dx in (("L", -.25), ("R", .25)):
            K.Z["fuss_" + sd].location = (K.BX + dx, -.42 if sd == "L" else -.3, .09 + (.25 if sd == "R" else 0))
        K.Z["hand_L"].location = wandpunkt(K.BX + HAENDE[0][0], HAENDE[0][1], .07)
        K.Z["hand_R"].location = (K.BX + .35, -.75, 1.0)
        K.dreh("neck01", x=-.4)
    elif t < t_top + .55:                                     # Klettern
        pel, ziele = kletter_pose(K, min(t, t_top))
        if t > t_top:
            k = (t - t_top) / .55; ziele["hand_R"] = ziele["hand_R"] + Vector((0, -.25 * math.sin(k * P), .1 * k))
        setze(K, rq_wand, pel)
        for nm, p in ziele.items():
            K.Z[nm].location = p
        K.dreh("neck01", x=-.5); K.dreh("spine03", x=.1)
    else:                                                     # Ablassen am Seil, unten jubeln
        tl = t - (t_top + .55)
        pz = max(.95, PEL_TOP - 3.4 * tl)
        unten = pz <= .951
        if not unten:
            setze(K, q(rz=P) @ q(rx=-.35), Vector((K.BX, wand_y(pz) - .75, pz)))
            for sd, dx in (("L", -.22), ("R", .22)):
                K.Z["fuss_" + sd].location = wandpunkt(K.BX + dx, pz - .45, .04)
            K.Z["hand_L"].location = Vector((K.BX - .05, wand_y(pz) - .7, pz + .55))
            jub = K is K1
            K.Z["hand_R"].location = Vector((K.BX + .35, wand_y(pz) - .95, pz + (1.25 if jub else .45)))
        else:
            tb = tl - (PEL_TOP - .95) / 3.4
            for c in K.IK.values():
                c.influence = 0
            dreh = ease(tb / .6)
            setze(K, q(rz=P * (1 - dreh)), Vector((K.BX, -1.0, K.PEL.z * K.SK + (.08 * max(0, math.sin(tb * 8)) if K is K1 and tb > .8 else 0))))
            j = ease((tb - .3) / .5) if K is K1 else 0
            K.dreh("upperarm01.L", z=-.72 + 3.2 * j, x=.2 * j); K.dreh("upperarm01.R", z=.72 - 3.2 * j, x=.2 * j)
            K.dreh("lowerarm01.L", x=-.4 * j); K.dreh("lowerarm01.R", x=-.4 * j); K.dreh("neck01", x=-.3 * j)
            for ff in range(1, 6):
                for g in (1, 2, 3):
                    K.dreh(f"finger{ff}-{g}.L", x=1.1 * j); K.dreh(f"finger{ff}-{g}.R", x=1.1 * j)
    # Pole: Knie nach aussen/unten, Ellbogen nach aussen
    pelw = K.rig.location
    for sd, s in (("L", -1), ("R", 1)):
        K.Z["knie_" + sd].location = Vector((K.BX + s * 1.2, -2.0, K.rig.location.z + 1.0))
        K.Z["ell_" + sd].location = Vector((K.BX + s * 1.4, -1.6, K.rig.location.z + 1.0))
    # Finger um den Griff
    for sd in ("L", "R"):
        for ff in range(2, 6):
            for g in (1, 2, 3):
                if K.IK["hand_" + sd].influence > 0:
                    K.dreh(f"finger{ff}-{g}.{sd}", x=.9)


def seil(K):
    top = Vector((K.BX + .4, wand_y(WAND_H + .2) - .25, WAND_H + .2))
    gurt = K.rig.matrix_world @ (K.PEL + Vector((0, -.1, .05)))
    d = gurt - top; o = SEILE[K.BX]; o.location = (top + gurt) / 2; o.scale = (1, 1, max(.01, d.length))
    o.rotation_mode = "QUATERNION"; o.rotation_quaternion = d.to_track_quat("Z", "Y")


def figuren(t):
    for K in (K1, K2):
        figur(K, t)
    bpy.context.view_layer.update()
    for K in (K1, K2):
        seil(K)
        el = min(K.DAUER, max(0, t - T_GRUEN))
        ANZ[K.BX].data.body = f"{el:.2f}"
    for a in LICHT_R:
        a.hide_render = t >= T_GRUEN
    for g in LICHT_G:
        g.hide_render = t < T_GRUEN


def becken(K=None):
    K = K or K1
    return K.rig.matrix_world @ K.PEL


# ======================================================================  Kamera
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam
cam.data.clip_start = .03; cam.data.clip_end = 500; cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
cam.data.dof.use_dof = True
# (von, bis, ts0, ts1, pos0, pos1, ziel0, ziel1, linse); "B+" = relativ zum Becken von Hunt, Ziel "B" = Becken
SZ = [
    (0.00, 1.40, 13.60, 14.10, "B+", (1.6, -2.4, -.6), "B", "B", 30),                                  # Aufhaenger: Zeitlupe mitten im Lauf
    (1.40, 3.60, 1.40, 3.60, (-1.0, -6.5, .6), (-1.2, -6.0, .5), (-1.5, 0, 6.5), (-1.5, 0, 7.5), 18),       # ganze Wand von unten
    (3.60, 4.70, 3.60, 4.70, (-.4, -2.0, 14.3), (-.5, -1.9, 14.4), (-1.5, wand_y(14.75), 14.75), (-1.5, wand_y(14.75), 14.75), 40),  # Top-Taster
    (4.70, 7.20, 4.70, 7.20, (7, -12.5, 7.5), (5, -11.5, 7), (0, 0, 6.5), (0, 0, 7), 22),                         # Arena weit
    (7.20, 9.80, 7.20, 9.80, (-4.0, -5.0, 1.0), (-4.0, -5.5, 14.5), (-1.5, 0, 2.0), (-1.5, 0, 13.5), 26),   # Kranfahrt die Wand hoch
    (9.80, 11.00, 9.80, 11.00, (-2.9, -1.4, 1.9), (-2.85, -1.35, 1.9), (-1.0, -.3, 2.15), (-1.0, -.3, 2.15), 32),  # Ampel + Startposition
    (11.00, 12.60, 11.00, 12.60, "B+", (.3, -3.4, -1.8), "B", "B", 24),                                  # von hinten unten mitfahrend
    (12.60, 14.20, 12.60, 14.20, "B+", (2.0, -1.0, .2), "B", "B", 30),                                   # seitlich nah mitfahrend
    (14.20, 15.80, 14.20, 15.80, "B+", (-.6, -2.4, 2.6), "B", "B", 26),                                  # von oben
    (15.80, 17.40, 15.80, 17.40, (-.1, -2.4, 14.4), (-.15, -2.3, 14.45), (-1.5, wand_y(14.6), 14.6), (-1.5, wand_y(14.6), 14.6), 30),  # Abschlagen
    (17.40, 19.20, 16.70, 17.05, (-2.6, -1.7, 14.9), (-2.55, -1.65, 14.95), (-1.5, wand_y(14.6), 14.65), (-1.5, wand_y(14.6), 14.65), 45),  # Zeitlupe Abschlagen
    (19.20, 20.50, 18.40, 19.70, "B+", (1.8, -2.6, .3), "B", "B", 28),                                   # Ablassen
    (20.50, 24.70, 21.60, 25.80, (2.5, -6.0, 1.7), (6, -14, 6), (-1.5, -.8, 1.5), (-1.0, 0, 4.0), 26),       # Jubel, Rueckfahrt
]


def zustand(t):
    for s in SZ:
        if s[0] <= t < s[1]:
            break
    k = (t - s[0]) / (s[1] - s[0])
    ts = s[2] + (s[3] - s[2]) * k
    k = ease(k) * .7 + k * .3
    figuren(ts)
    bk = becken()
    if s[4] == "B+":
        pos = bk + Vector(s[5])
    else:
        pos = lerpv(s[4], s[5], k)
    ziel = bk if s[6] == "B" else lerpv(s[6], s[7], k)
    cam.location = pos; d = ziel - pos; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = s[8]; cam.data.dof.focus_distance = d.length; cam.data.dof.aperture_fstop = 2.2 if d.length < 4 else 5.6
    zit = .003
    cam.location += Vector((zit * math.sin(t * 7.3), zit * math.cos(t * 5.1), zit * math.sin(t * 9.7)))


os.makedirs(A.ordner, exist_ok=True)
N = int(round(D * A.fps))
liste = [int(round(float(x) * A.fps)) for x in A.nur.split(",")] if A.nur else list(range(A.start, N))
for f in liste:
    pfad = os.path.join(A.ordner, f"kletter_{f:04d}.png")
    if os.path.exists(pfad) and not A.nur:
        continue
    zustand(f / A.fps); bpy.context.view_layer.update(); zustand(f / A.fps)
    sc.render.filepath = pfad
    bpy.ops.render.render(write_still=True); print("FERTIG", pfad, flush=True)
