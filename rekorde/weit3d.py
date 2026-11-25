"""Weitsprung 8,95 m (Mike Powell, Tokio 30.8.1991, World Athletics/GWR). Realistischer Stil, echte Figur (mensch_echt).
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
D = 23.2
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


# ======================================================================  Springer (MPFB) - zuerst, Materialien danach
import mensch_echt as ME
H = ME.mensch("springer", 47, 1.0, .4, .85, .2, haut="african", haare="short04", braue="eyebrow003")
BIB = ME.logo_bild(os.path.join(HIER, "_bib_weit.png"), "1023", farbe=(.05, .05, .05), symbol=False, hintergrund=(.97, .97, .95), num=True, unterzeile="TOKYO 91")
LOGO = ME.logo_bild(os.path.join(HIER, "_logo_norda.png"), "NORDA", farbe=(1, 1, 1))
ME.trikot(H, "singlet", "shorts", "0f2f7a", "0f2f7a", brust=BIB, brust_mass=(.19, .13), bein=LOGO)
for o in H.huellen:
    if "versatz" in o.modifiers:
        o.modifiers["versatz"].strength = .011 if o.name.endswith("_hemd") else .004
BN = H.rig.data.bones
PEL = BN["upperleg01.L"].head_local.copy(); PEL.x = 0
KOERPER_H = max(v.z for v in H.EV)
SK = 1.88 / KOERPER_H; H.rig.scale = (SK, SK, SK)
print("GROESSE", KOERPER_H, SK)

# ======================================================================  Materialien
WEISSLACK = mat("weisslack", "f2f2f0", .25, Coat_Weight=.5)
STAHL = pbr("stahl", "Metal012", 6, rau_mul=.6, rau_add=.15, metal=1.0)
TARTAN = pbr("tartan", "Rubber004", 1.6, tint="c0472f", rau_mul=1.0, normal=1.4)
RASEN = pbr("rasen", "Grass004", .35, normal=.8)
MATTE = pbr("matte", "Fabric048", 1.2, tint="2457c9", normal=1.2, rau_mul=.9)
MATTE_S = pbr("matte_seite", "Fabric030", 3, tint="183d94")
SCHUH = mat("schuh", "1a1a1a", .4)

LINIE = mat("linie", "f4f4f0", .6)
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; nt = w.node_tree
env = nt.nodes.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(os.path.join(ASSET, "tag.hdr"))
mpw = nt.nodes.new("ShaderNodeMapping"); tcw = nt.nodes.new("ShaderNodeTexCoord"); nt.links.new(tcw.outputs["Generated"], mpw.inputs[0])
mpw.inputs["Rotation"].default_value = (0, 0, math.radians(200)); nt.links.new(mpw.outputs[0], env.inputs[0])
nt.links.new(env.outputs[0], nt.nodes["Background"].inputs[0]); nt.nodes["Background"].inputs[1].default_value = .7
# ======================================================================  Anlage: Rasen, Anlaufbahn, Balken, Sandgrube
SAND = pbr("sand", "Ground054", .9, tint="e0c89a", normal=.6, rau_mul=1.0)
HOLZ_R = mat("grubenrand", "e9e9e4", .55)
box("rasen", (400, 400, .02), (0, 0, -.03), RASEN, 0)
box("grubenumfeld", (16, 7, .02), (5.5, 0, -.012), TARTAN, 0)
box("anlauf", (46, 1.22, .01), (-22, 0, .004), TARTAN, 0)
box("anlauf_rand", (46, 3.2, .006), (-22, 0, .002), TARTAN, 0)
for dy in (-.61, .61):
    box("anlauf_linie", (46, .05, .004), (-22, dy, .01), LINIE, 0)
for k in range(8):                                         # Rundbahn daneben
    box("bahn", (220, 1.22, .006), (0, -6 - k * 1.22, .003), TARTAN, 0)
    box("bahnlinie", (220, .05, .004), (0, -6 + .61 - k * 1.22, .008), LINIE, 0)
box("balken", (.2, 1.22, .012), (-.1, 0, .007), mat("balkenweiss", "f4f4f2", .5), .003)
box("knetbrett", (.1, 1.22, .014), (.05, 0, .008), mat("knete", "f2f2f2", .9), .004)
box("knetstreifen", (.098, 1.2, .002), (.05, 0, .016), mat("plastilin", "7da35a", .8), 0)
# Sandgrube: Ebene mit Unterteilung, Abdruck nach der Landung (zweites Objekt)
GX0, GX1, GB = 1.0, 10.5, 2.9


def sandflaeche(name, abdruck):
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=380, y_subdivisions=116, size=1, location=((GX0 + GX1) / 2, 0, 0))
    o = bpy.context.object; o.name = name; o.scale = (GX1 - GX0, GB, 1); bpy.ops.object.transform_apply(scale=True)
    rr = random.Random(9)
    for v in o.data.vertices:
        x, y = v.co.x, v.co.y
        z = .006 * math.sin(y * 70 + .4 * math.sin(x * 3)) + .004 * math.sin(x * 23 + y * 5)      # Rechenspuren
        z += .01 * (1 - min(1, abs(y) / (GB / 2)) ** 6) + .012
        if abdruck:
            for (cx, cy, rx, ry, tief) in ((8.98, .1, .16, .11, .07), (9.0, -.12, .16, .11, .07), (8.65, 0, .35, .24, .11), (9.15, 0, .2, .3, .05)):
                d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
                if d < 1:
                    z -= tief * (1 - d) ** 1.5
                elif d < 2.2:
                    z += .025 * math.sin((d - 1) / 1.2 * math.pi) * (tief / .1)
            if 9.2 < x < 10.3 and abs(y) < .6:
                z += .01 * rr.random() * math.exp(-(x - 9.4) * 2)
        v.co.z = z
    for p in o.data.polygons:
        p.use_smooth = True
    o.data.materials.append(SAND)
    return o


SAND_GLATT = sandflaeche("sand_glatt", False)
SAND_ABDRUCK = sandflaeche("sand_abdruck", True)
for (x_, y_, l, b_) in (((GX0 + GX1) / 2, GB / 2 + .06, GX1 - GX0 + .24, .12), ((GX0 + GX1) / 2, -GB / 2 - .06, GX1 - GX0 + .24, .12),
                        (GX0 - .06, 0, .12, GB), (GX1 + .06, 0, .12, GB)):
    box("grubenrand", (l, b_, .07), (x_, y_, .0), HOLZ_R, .02)
# Messband entlang der Grube + Distanztafeln 7/8/9 m
box("messband", (GX1 - .4, .03, .002), ((GX1 + .4) / 2, GB / 2 + .16, .004), mat("band_gelb", "f2c41a", .4), 0)
for m_ in range(1, 11):
    box("strich", (.012, .05, .003), (m_, GB / 2 + .16, .005), mat("strich", "111111", .4) if not bpy.data.materials.get("strich") else bpy.data.materials["strich"], 0)
for m_ in (7, 8, 9):
    zyl("tafelstab", .015, .55, (m_, GB / 2 + .5, .27), STAHL)
    box("distanztafel", (.32, .03, .26), (m_, GB / 2 + .5, .62), mat("tafelweiss", "f5f5f2", .5) if not bpy.data.materials.get("tafelweiss") else bpy.data.materials["tafelweiss"], .01)
    bpy.ops.object.text_add(location=(m_, GB / 2 + .48, .56), rotation=(P / 2, 0, 0)); t = bpy.context.object
    t.data.body = f"{m_} m"; t.data.align_x = "CENTER"; t.data.size = .14; t.data.extrude = .002
    t.data.materials.append(mat("tafeltext", "111111", .5) if not bpy.data.materials.get("tafeltext") else bpy.data.materials["tafeltext"])
# Windmesser, Rechen, Anzeige-Tafel, Kampfrichter-Stuehle, Fahne
for k in range(3):
    a = 2 * P * k / 3
    rohr("windstativ", (-2 + .25 * math.cos(a), -1.8 + .25 * math.sin(a), 0), (-2, -1.8, 1.0), .01, STAHL)
box("windmesser", (.1, .1, .14), (-2, -1.8, 1.08), mat("windgeh", "222222", .4), .01)
zyl("windrad", .05, .02, (-1.94, -1.8, 1.2), STAHL, rot=(0, P / 2, 0))
rohr("rechenstiel", (11.4, 1.9, .03), (12.9, 2.6, .03), .014, mat("rechenholz", "b58a52", .6))
box("rechenkopf", (.08, .55, .05), (11.4, 1.9, .04), mat("rechenalu", "9aa0a6", .3, .8), .01, rot=(0, 0, .45))
box("anzeige", (1.1, .1, .6), (12.2, -2.2, 1.25), mat("anzeigegeh", "151515", .4), .02)
zyl("anzeigefuss", .03, 1.0, (12.2, -2.2, .5), STAHL)
bpy.ops.object.text_add(location=(12.13, -2.26, 1.14), rotation=(P / 2, 0, P / 2)); ANZ = bpy.context.object
ANZ.data.body = "8.95"; ANZ.data.align_x = "CENTER"; ANZ.data.size = .36; ANZ.data.extrude = .005
ANZ.data.materials.append(emis("anzeigetext", "ffb020", 18))
for i, (x_, y_) in enumerate(((2.6, -3.6), (3.2, -3.6), (6.5, 2.6))):
    box("stuhl", (.45, .45, .45), (x_, y_, .45), mat("stuhl%d" % i, "e6e6e6", .5), .03)
zyl("fahnenmast", .02, 1.6, (-.6, 1.5, .8), STAHL)
box("fahne_weiss", (.01, .45, .32), (-.6, 1.73, 1.4), mat("fahnew", "f5f5f5", .7, Sheen_Weight=.4), 0)
# Sandkoerner fuer die Landung
SPR = []
rk = random.Random(5)
for i in range(160):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=rk.uniform(.006, .02), location=(0, 0, -5))
    o = bpy.context.object; o.data.materials.append(SAND); o.hide_render = True
    o["v"] = (rk.uniform(.5, 4.5), rk.uniform(-1.6, 1.6), rk.uniform(.8, 3.2)); o["s"] = (rk.uniform(8.7, 9.1), rk.uniform(-.25, .25))
    SPR.append(o)

# ======================================================================  Stadion: Tribuenen-Oval, Dach, Flutlicht-Masten, Publikum
MITTE = Vector((-10, 40, 0)); RA, RB = 105, 78
trib_m = pbr("tribuene", "Concrete034", .2, tint="8a8a8a")
sitz_m = mat("sitze", "1e5bb0", .45)
bm = bmesh.new(); NRG = 180; STUF = 30; ringe = []
for s_ in range(STUF + 1):
    rr = 1 + s_ * .01; hz = .8 + s_ * .9
    ringe.append([bm.verts.new((MITTE.x + RA * rr * math.cos(2 * P * j / NRG), MITTE.y + RB * rr * math.sin(2 * P * j / NRG), hz)) for j in range(NRG)])
for a, b_ in zip(ringe, ringe[1:]):
    for j in range(NRG):
        bm.faces.new((a[j], a[(j + 1) % NRG], b_[(j + 1) % NRG], b_[j]))
me = bpy.data.meshes.new("tribuene"); bm.to_mesh(me); bm.free()
trib = bpy.data.objects.new("tribuene", me); sc.collection.objects.link(trib); me.materials.append(sitz_m)
dach_m = mat("dach", "d0d4d9", .35, .6)
bm = bmesh.new(); ri, ra_ = [], []
for j in range(NRG):
    a = 2 * P * j / NRG
    ri.append(bm.verts.new((MITTE.x + RA * 1.2 * math.cos(a), MITTE.y + RB * 1.2 * math.sin(a), 34)))
    ra_.append(bm.verts.new((MITTE.x + RA * 1.5 * math.cos(a), MITTE.y + RB * 1.5 * math.sin(a), 37)))
for j in range(NRG):
    bm.faces.new((ri[j], ri[(j + 1) % NRG], ra_[(j + 1) % NRG], ra_[j]))
me = bpy.data.meshes.new("dach"); bm.to_mesh(me); bm.free(); dach = bpy.data.objects.new("dach", me); sc.collection.objects.link(dach)
me.materials.append(dach_m); dach.modifiers.new("d", "SOLIDIFY").thickness = .6
fl_m = emis("flutlicht", "fff4e2", 25)
for j in range(0, NRG, 6):
    a = 2 * P * j / NRG
    box("fluter", (2.0, 2.0, .2), (MITTE.x + RA * 1.21 * math.cos(a), MITTE.y + RB * 1.21 * math.sin(a), 33.6), fl_m, 0)
r = random.Random(4)
koerper_me = []
for i, f in enumerate(["c62828", "1565c0", "f2f2f2", "2e7d32", "212121", "f9a825", "6a1b9a", "455a64", "ef6c00"]):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=7, radius=1, matrix=Matrix.Translation((0, 0, .45)) @ Matrix.Diagonal((.24, .17, .34, 1)))
    bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=7, radius=.1, matrix=Matrix.Translation((0, 0, .93)))
    me = bpy.data.meshes.new("pub%d" % i); bm.to_mesh(me); bm.free(); me.materials.append(mat("pubm%d" % i, f, .8, Sheen_Weight=.4))
    for p in me.polygons:
        p.use_smooth = True
    koerper_me.append(me)
for s_ in range(0, STUF, 1):
    rr = 1 + (s_ + .5) * .01; hz = .8 + (s_ + .5) * .9
    for j in range(560):
        if r.random() < .15:
            continue
        a = 2 * P * (j + r.random() * .5) / 560
        o = bpy.data.objects.new("pub", r.choice(koerper_me)); sc.collection.objects.link(o)
        o.location = (MITTE.x + RA * rr * math.cos(a), MITTE.y + RB * rr * math.sin(a), hz - .05); o.rotation_euler = (0, 0, a + P / 2 + P / 2)
# Sonne passend zum HDRI + Flutlicht als Flaechenlichter
bpy.ops.object.light_add(type="SUN"); sonne = bpy.context.object; sonne.data.energy = 3.0; sonne.data.angle = .02
sonne.rotation_euler = Euler((math.radians(50), 0, math.radians(150))); sonne.data.color = (1, .9, .78)
for (x_, y_) in ((-40, -20), (30, -25), (-40, 80), (30, 85)):
    bpy.ops.object.light_add(type="AREA", location=(x_, y_, 36)); L = bpy.context.object; L.data.size = 12; L.data.energy = 90000
    L.rotation_euler = (Vector((0, 0, 0)) - L.location).to_track_quat("-Z", "Y").to_euler(); L.data.color = (1, .96, .9)
# ======================================================================  Ablauf
T_LOS, T_ABS = 5.7, 8.6
FLUG = .92
T_LAND = T_ABS + FLUG
X0 = -29.0
YAW = P / 2


def anlauf(t):
    """Weg ab Start mit Beschleunigung bis ca. 11 m/s"""
    k = max(0, min(1, (t - T_LOS) / (T_ABS - T_LOS)))
    s_ = (-.3 - X0) * (.45 * k * k + .55 * k)
    return X0 + s_


def q(rx=0, ry=0, rz=0):
    return Euler((rx, ry, rz)).to_quaternion()


PT3 = Vector((-.05, 0, 1.12)); PL3 = Vector((8.45, 0, .42))
VZ = 3.55


def flug_pos(tf):
    u = tf / FLUG
    x = PT3.x + (PL3.x - PT3.x) * u
    z = PT3.z + VZ * tf - 4.905 * tf * tf
    z = z + (PL3.z - (PT3.z + VZ * FLUG - 4.905 * FLUG * FLUG)) * u          # Endhoehe angleichen
    return Vector((x, 0, z))


def setze(rot_q, pel):
    H.rig.rotation_mode = "QUATERNION"; H.rig.rotation_quaternion = rot_q
    H.rig.location = pel - rot_q.to_matrix() @ (PEL * SK)


def laufpose(ph, kraft):
    s, c = math.sin(ph), math.cos(ph)
    H.dreh("upperleg01.L", x=-1.0 * s * kraft - .35); H.dreh("upperleg01.R", x=1.0 * s * kraft - .35)
    H.dreh("lowerleg01.L", x=.4 + 1.2 * max(0, c) * kraft); H.dreh("lowerleg01.R", x=.4 + 1.2 * max(0, -c) * kraft)
    H.dreh("upperarm01.L", z=-.65, x=1.1 * s * kraft + .2); H.dreh("upperarm01.R", z=.65, x=-1.1 * s * kraft + .2)
    H.dreh("lowerarm01.L", x=-1.4); H.dreh("lowerarm01.R", x=-1.4); H.dreh("neck01", x=-.05)


def figuren(t):
    H.zuruecksetzen()
    SAND_GLATT.hide_render = t >= T_LAND; SAND_ABDRUCK.hide_render = t < T_LAND
    ANZ.hide_render = t < T_LAND + 3.0
    for o in SPR:
        tt = t - T_LAND
        if 0 <= tt < 1.0:
            vx, vy, vz = o["v"]; sx, sy = o["s"]
            z = .02 + vz * tt - 4.905 * tt * tt
            o.hide_render = z < 0; o.location = (sx + vx * tt * .7, sy + vy * tt * .5, max(z, 0))
        else:
            o.hide_render = True
    if t < T_LOS:                                            # Vorbereitung: wippen, Blick zur Grube
        w = math.sin(t * 2.2)
        setze(q(rz=YAW) @ q(rx=.06 + .05 * w), Vector((X0, 0, PEL.z * SK - .02 + .02 * w)))
        H.dreh("upperarm01.L", z=-.6 + .08 * w); H.dreh("upperarm01.R", z=.6 - .08 * w)
        H.dreh("lowerarm01.L", x=-.35); H.dreh("lowerarm01.R", x=-.35); H.dreh("neck01", x=.08)
        H.dreh("upperleg01.R", x=-.25 * max(0, w)); H.dreh("lowerleg01.R", x=.4 * max(0, w))
    elif t < T_ABS - .1:                                     # Anlauf
        x = anlauf(t); kraft = min(1, .55 + (t - T_LOS) * .35)
        ph = (x - X0) / 2.25 * P
        lean = .32 * math.exp(-(t - T_LOS) / .9) + .1
        setze(q(rz=YAW) @ q(rx=lean), Vector((x, 0, PEL.z * SK - .05 + .05 * abs(math.sin(ph)))))
        laufpose(ph, kraft)
    elif t < T_ABS:                                          # Absprung: Schwungbein hoch, Arme hoch
        k = ease((t - (T_ABS - .1)) / .1)
        setze(q(rz=YAW) @ q(rx=-.08 * k), Vector((-.15, 0, PEL.z * SK + .02)))
        H.dreh("upperleg01.R", x=-1.4 * k); H.dreh("lowerleg01.R", x=1.6 * k); H.dreh("upperleg01.L", x=.2 * k)
        H.dreh("upperarm01.L", z=-.5, x=1.8 * k); H.dreh("upperarm01.R", z=.5, x=-.4 * k)
    elif t < T_LAND:                                         # Flug im Hang-Stil
        tf = t - T_ABS; u = tf / FLUG
        kn = max(0, 1 - u / .22)                             # Schwungbein loest sich
        hang = math.sin(min(1, max(0, (u - .12) / .4)) * P / 2) * (1 - ease((u - .55) / .2))
        land = ease((u - .58) / .3)
        pitch = -.18 * hang + .55 * land
        setze(q(rz=YAW) @ q(rx=pitch), flug_pos(tf))
        for sd in ("L", "R"):
            H.dreh("upperleg01." + sd, x=(-1.4 * kn if sd == "R" else .2 * kn) + .45 * hang - 1.75 * land)
            H.dreh("lowerleg01." + sd, x=(1.6 * kn if sd == "R" else .2) + 1.1 * hang * (1 - land) + .05 * land)
        for b_ in ("spine01", "spine02", "spine03"):
            H.dreh(b_, x=-.12 * hang + .22 * land)
        H.dreh("neck01", x=-.2 * hang + .15 * land)
        arm_x = 1.8 * kn + 2.6 * hang * (1 - land) + .9 * land
        H.dreh("upperarm01.L", z=-.45, x=arm_x); H.dreh("upperarm01.R", z=.45, x=arm_x)
        H.dreh("lowerarm01.L", x=-.2); H.dreh("lowerarm01.R", x=-.2)
    else:                                                    # Landung im Sand, aufstehen, jubeln
        tl = t - T_LAND
        if tl < 1.6:
            k = ease(tl / .35)
            pel = PL3.lerp(Vector((8.9, 0, .22)), k)
            setze(q(rz=YAW) @ q(rx=.55 + .35 * k), pel)
            H.dreh("upperleg01.L", x=-1.75 + .2 * k); H.dreh("upperleg01.R", x=-1.75 + .2 * k)
            H.dreh("lowerleg01.L", x=.05 + 1.6 * k); H.dreh("lowerleg01.R", x=.05 + 1.6 * k)
            H.dreh("upperarm01.L", z=-.45, x=.9 - .5 * k); H.dreh("upperarm01.R", z=.45, x=.9 - .5 * k)
            for b_ in ("spine01", "spine02", "spine03"):
                H.dreh(b_, x=.22)
        else:
            k = ease((tl - 1.6) / .9)
            pel = Vector((8.9, 0, .22)).lerp(Vector((9.4, 0, PEL.z * SK)), k)
            setze(q(rz=YAW) @ q(rx=.9 * (1 - k)), pel)
            H.dreh("upperleg01.L", x=-1.55 * (1 - k)); H.dreh("upperleg01.R", x=-1.55 * (1 - k))
            H.dreh("lowerleg01.L", x=1.65 * (1 - k)); H.dreh("lowerleg01.R", x=1.65 * (1 - k))
            j = ease((tl - 2.8) / .5)
            hop = max(0, math.sin((tl - 6.0) * 7)) * .06 if 6.0 < tl < 7.4 else 0
            H.rig.location.z += hop
            H.dreh("upperarm01.L", z=-.72 * (1 - j) + 2.6 * j, x=.2 * j); H.dreh("upperarm01.R", z=.72 * (1 - j) - 2.6 * j, x=.2 * j)
            H.dreh("lowerarm01.L", x=-.5 * j); H.dreh("lowerarm01.R", x=-.5 * j); H.dreh("neck01", x=-.3 * j)
            for f in range(1, 6):
                for g in (1, 2, 3):
                    H.dreh(f"finger{f}-{g}.L", x=1.1 * j); H.dreh(f"finger{f}-{g}.R", x=1.1 * j)
    bpy.context.view_layer.update()


def becken():
    return H.rig.matrix_world @ PEL


# ======================================================================  Kamera
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam
cam.data.clip_start = .03; cam.data.clip_end = 3000; cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
cam.data.dof.use_dof = True
SZ = [
    (0.00, 1.30, 8.85, 9.15, "B+", (.6, -3.4, -.3), "B", "B", 32),                                   # Aufhaenger: Hang in Zeitlupe
    (1.30, 3.40, 1.30, 3.40, (10.8, -1.3, .32), (10.6, -1.2, .32), (4, 0, .05), (4, 0, .05), 26),       # Grube, glatter Sand
    (3.40, 4.50, 3.40, 4.50, (2.0, -2.4, .9), (8.0, -2.4, .9), (3.0, .6, .1), (9.0, .6, .1), 26),      # an den Tafeln entlang
    (4.50, 6.60, 4.50, 6.60, (26, -28, 17), (22, -24, 15), (-8, 4, 0), (-8, 4, 0), 26),                # Stadion weit
    (6.60, 7.70, 6.60, 7.70, "B+", (7.0, -.7, -.55), "B", "B", 50),                                   # Anlauf frontal (Tele)
    (7.70, 8.75, 7.70, 8.75, "B+", (1.6, -2.6, -.75), "F", "F", 28),       # Balken
    (8.75, 10.20, 8.75, 10.20, "B+", (0, -6.0, -.1), "B", "B", 34),                                  # Flug seitlich mitfahrend
    (10.20, 12.40, 8.60, 9.52, (12.5, 1.4, .55), (12.3, 1.3, .6), "B", "B", 55),                    # Zeitlupe von vorne
    (12.40, 14.30, 12.40, 14.30, (8.6, -1.0, 4.3), (8.7, -.8, 4.0), (8.95, 0, 0), (8.95, 0, 0), 30),    # von oben: Abdruck + Band
    (14.30, 16.60, 14.30, 16.60, (14.8, -4.6, 2.0), (14.3, -4.2, 1.9), (8.0, 0, .8), (8.2, 0, .8), 24),         # ganze Sprungweite
    (16.60, 18.00, 16.60, 18.00, (11.4, -1.7, 1.6), (11.3, -1.6, 1.62), (9.4, 0, 1.45), (9.4, 0, 1.45), 42),
    (18.00, 23.20, 18.00, 23.20, (14.5, -6, 2.6), (30, -30, 15), (6, 0, .5), (6, 0, .5), 26),
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
        pos = bk + Vector(s[5]) + Vector((0, 0, -bk.z + 1.1))
    else:
        pos = lerpv(s[4], s[5], k)
    ziel = bk if s[6] == "B" else (Vector((bk.x, bk.y, .5)) if s[6] == "F" else lerpv(s[6], s[7], k))
    cam.location = pos; d = ziel - pos; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = s[8]; cam.data.dof.focus_distance = d.length; cam.data.dof.aperture_fstop = 2.2 if d.length < 4 else 5.6
    zit = .003
    cam.location += Vector((zit * math.sin(t * 7.3), zit * math.cos(t * 5.1), zit * math.sin(t * 9.7)))


os.makedirs(A.ordner, exist_ok=True)
N = int(round(D * A.fps))
liste = [int(round(float(x) * A.fps)) for x in A.nur.split(",")] if A.nur else list(range(A.start, N))
for f in liste:
    pfad = os.path.join(A.ordner, f"weit_{f:04d}.png")
    if os.path.exists(pfad) and not A.nur:
        continue
    zustand(f / A.fps); bpy.context.view_layer.update(); zustand(f / A.fps)
    sc.render.filepath = pfad
    bpy.ops.render.render(write_still=True); print("FERTIG", pfad, flush=True)
