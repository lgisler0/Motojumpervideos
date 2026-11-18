"""Airbus A380 in 3D (Blender/Cycles). python3 a380_3d.py <ordner> --dauer D [--nur t1,t2] [--skala 50] [--start i]
Masse nach Hersteller: Laenge 72.72 m, Spannweite 79.75 m, Hoehe 24.09 m, Rumpf 7.14 m breit."""
import bpy, bmesh, math, random, sys, os, argparse, json
from mathutils import Vector

ap = argparse.ArgumentParser()
ap.add_argument("ordner"); ap.add_argument("--nur", default=""); ap.add_argument("--skala", type=int, default=50)
ap.add_argument("--samples", type=int, default=14); ap.add_argument("--fps", type=int, default=15)
ap.add_argument("--start", type=int, default=0); ap.add_argument("--dauer", type=float, default=24.0)
ap.add_argument("--zeiten", default="")
A = ap.parse_args(sys.argv[1:])
Z = json.loads(A.zeiten) if A.zeiten else {}

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = A.samples; sc.cycles.use_denoising = True
sc.cycles.max_bounces = 3; sc.cycles.diffuse_bounces = 1; sc.cycles.glossy_bounces = 2; sc.cycles.transparent_max_bounces = 6
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1080, 1920, A.skala
sc.render.use_persistent_data = True
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"; sc.view_settings.exposure = -.7
P = math.pi


def hexf(h):
    return tuple(((int(h[i:i + 2], 16) / 255) ** 2.2) for i in (0, 2, 4))


def mat(name, farbe, rau=.4, metall=0, leucht=0, lf=None):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*farbe, 1); b.inputs["Roughness"].default_value = rau; b.inputs["Metallic"].default_value = metall
    if leucht:
        b.inputs["Emission Color"].default_value = (*(lf or farbe), 1); b.inputs["Emission Strength"].default_value = leucht
    return m


def obj_aus(bm, name, m, glatt=True):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o)
    if m:
        me.materials.append(m)
    if glatt:
        for p in me.polygons:
            p.use_smooth = True
    return o


# ======================================================================  Flugzeug
# Achsen: x = vom Bug nach hinten (0..72.72), y = Spannweite (links +), z = oben. Rumpfachse auf z = 0 (lokal).
flug = bpy.data.objects.new("A380", None); sc.collection.objects.link(flug)


def kind(o):
    o.parent = flug
    return o


# --- Rumpf-Material: weiss mit zwei Fensterreihen (Ober- und Hauptdeck), Bauchlinie
rumpf_m = bpy.data.materials.new("rumpf"); rumpf_m.use_nodes = True
n = rumpf_m.node_tree.nodes; l = rumpf_m.node_tree.links; b = n["Principled BSDF"]
b.inputs["Roughness"].default_value = .28; b.inputs["Specular IOR Level"].default_value = .6
tc = n.new("ShaderNodeTexCoord"); sep = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Object"], sep.inputs[0])


def band(z0, z1):
    a1 = n.new("ShaderNodeMath"); a1.operation = "GREATER_THAN"; a1.inputs[1].default_value = z0; l.new(sep.outputs["Z"], a1.inputs[0])
    a2 = n.new("ShaderNodeMath"); a2.operation = "LESS_THAN"; a2.inputs[1].default_value = z1; l.new(sep.outputs["Z"], a2.inputs[0])
    m_ = n.new("ShaderNodeMath"); m_.operation = "MULTIPLY"; l.new(a1.outputs[0], m_.inputs[0]); l.new(a2.outputs[0], m_.inputs[1])
    return m_


# Fensterraster entlang x (Abstand ~0.53 m)
fx = n.new("ShaderNodeMath"); fx.operation = "MULTIPLY"; fx.inputs[1].default_value = 1.0 / .53; l.new(sep.outputs["X"], fx.inputs[0])
fr = n.new("ShaderNodeMath"); fr.operation = "FRACT"; l.new(fx.outputs[0], fr.inputs[0])
fl = n.new("ShaderNodeMath"); fl.operation = "LESS_THAN"; fl.inputs[1].default_value = .42; l.new(fr.outputs[0], fl.inputs[0])
# nur zwischen x = 6 und x = 60
xa = n.new("ShaderNodeMath"); xa.operation = "GREATER_THAN"; xa.inputs[1].default_value = 6.5; l.new(sep.outputs["X"], xa.inputs[0])
xb = n.new("ShaderNodeMath"); xb.operation = "LESS_THAN"; xb.inputs[1].default_value = 59; l.new(sep.outputs["X"], xb.inputs[0])
xm = n.new("ShaderNodeMath"); xm.operation = "MULTIPLY"; l.new(xa.outputs[0], xm.inputs[0]); l.new(xb.outputs[0], xm.inputs[1])
reihen = n.new("ShaderNodeMath"); reihen.operation = "ADD"
l.new(band(1.55, 2.05).outputs[0], reihen.inputs[0]); l.new(band(-1.15, -.65).outputs[0], reihen.inputs[1])
f1 = n.new("ShaderNodeMath"); f1.operation = "MULTIPLY"; l.new(reihen.outputs[0], f1.inputs[0]); l.new(fl.outputs[0], f1.inputs[1])
fenster = n.new("ShaderNodeMath"); fenster.operation = "MULTIPLY"; l.new(f1.outputs[0], fenster.inputs[0]); l.new(xm.outputs[0], fenster.inputs[1])
# Bauch etwas grauer
bauch = band(-9, -2.6)
farbe1 = n.new("ShaderNodeMix"); farbe1.data_type = "RGBA"; farbe1.inputs[6].default_value = (.92, .93, .95, 1); farbe1.inputs[7].default_value = (.62, .66, .72, 1)
l.new(bauch.outputs[0], farbe1.inputs[0])
farbe2 = n.new("ShaderNodeMix"); farbe2.data_type = "RGBA"; farbe2.inputs[7].default_value = (.02, .03, .05, 1)
l.new(farbe1.outputs[2], farbe2.inputs[6]); l.new(fenster.outputs[0], farbe2.inputs[0])
l.new(farbe2.outputs[2], b.inputs["Base Color"])
fem = n.new("ShaderNodeMath"); fem.operation = "MULTIPLY"; fem.inputs[1].default_value = .0; l.new(fenster.outputs[0], fem.inputs[0])
l.new(fem.outputs[0], b.inputs["Emission Strength"]); b.inputs["Emission Color"].default_value = (1, .8, .5, 1)
FENSTER_LICHT = fem.inputs[1]

LAENGE, HB, HH = 72.72, 3.57, 4.2


def rumpf_schnitt(x):
    """Halbbreite, Halbhoehe, Mittelpunkt-z des Rumpfquerschnitts bei x"""
    if x < 9:
        k = x / 9
        s = math.sqrt(max(0, 1 - (1 - k) ** 2)) ** .9
        return HB * s, HH * (.25 + .75 * s), -.9 * (1 - k) ** 2
    if x < 50:
        return HB, HH, 0
    k = (x - 50) / (LAENGE - 50)
    return HB * (1 - .86 * k ** 1.1), HH * (1 - .86 * k ** 1.05), 2.3 * k ** 1.4


bm = bmesh.new(); ringe = []; NV = 48
xs = [0.0, .05, .2, .5, 1, 1.6, 2.4, 3.4, 4.6, 6, 7.5, 9] + [9 + i * 1.5 for i in range(1, 28)] + [50 + i * 1.1 for i in range(1, 21)] + [LAENGE]
for x in xs:
    a, h, zc = rumpf_schnitt(x)
    ring = []
    for k in range(NV):
        w = 2 * P * k / NV
        y = a * math.cos(w); z = zc + h * math.sin(w) * (1 + (.05 if math.sin(w) > 0 else -.02))
        ring.append(bm.verts.new((x, y, z)))
    ringe.append(ring)
for r0, r1 in zip(ringe, ringe[1:]):
    for k in range(NV):
        bm.faces.new((r0[k], r1[k], r1[(k + 1) % NV], r0[(k + 1) % NV]))
bm.faces.new(list(reversed(ringe[-1])))
rumpf = kind(obj_aus(bm, "rumpf", rumpf_m))
sub = rumpf.modifiers.new("s", "SUBSURF"); sub.levels = 1; sub.render_levels = 2

# Cockpitfenster (dunkles Band vorne, zwischen den Decks)
glas = mat("glas", hexf("10161f"), .05, .6)
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=32, ring_count=16); ck = kind(bpy.context.object)
ck.scale = (1.3, 1.9, .45); ck.location = (2.6, 0, .35); ck.data.materials.append(glas)
for p in ck.data.polygons:
    p.use_smooth = True

# --- Fluegel (Bmesh-Profil, Pfeilung 33.5 Grad, V-Form 5.6 Grad)
weiss = mat("weiss", hexf("e9ecf1"), .3)
grau = mat("grau", hexf("9aa3b0"), .45, .3)


def fluegel_bm(spitze_y, wurzel_y, x_wurzel, c_wurzel, c_spitze, pfeil, vform, z0, dick0, dick1, seite):
    bm = bmesh.new(); profile = []
    for k in range(9):
        t = k / 8
        y = wurzel_y + (spitze_y - wurzel_y) * t
        le = x_wurzel + (y - wurzel_y) * math.tan(math.radians(pfeil))
        c = c_wurzel + (c_spitze - c_wurzel) * t
        z = z0 + (y - wurzel_y) * math.tan(math.radians(vform))
        d = dick0 + (dick1 - dick0) * t
        pts = [(0, 0), (.03, .45), (.12, .5), (.35, .42), (.7, .2), (1, 0), (.7, -.12), (.35, -.25), (.12, -.3), (.03, -.25)]
        profile.append([bm.verts.new((le + c * px, seite * y, z + d * pz)) for px, pz in pts])
    for p0, p1 in zip(profile, profile[1:]):
        for k in range(len(p0)):
            f = (p0[k], p0[(k + 1) % len(p0)], p1[(k + 1) % len(p0)], p1[k])
            bm.faces.new(f if seite > 0 else list(reversed(f)))
    bm.faces.new(profile[-1] if seite > 0 else list(reversed(profile[-1])))
    return bm


SPW = 79.75 / 2
for s in (1, -1):
    f = kind(obj_aus(fluegel_bm(SPW, 2.8, 25.5, 17.7, 4.0, 33.5, 5.6, -2.6, 2.1, .38, s), f"fluegel{s}", weiss))
    # Wingtip-Fence (oben + unten)
    yt = SPW; le = 25.5 + (yt - 2.8) * math.tan(math.radians(33.5)); zt = -2.6 + (yt - 2.8) * math.tan(math.radians(5.6))
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in ((le + .4, s * (yt + .05), zt - 1.1), (le + 4.2, s * (yt + .05), zt - .6), (le + 4.6, s * (yt + .05), zt + 1.6), (le + 3.4, s * (yt + .05), zt + 1.7))]
    bm.faces.new(vs)
    kind(obj_aus(bm, f"fence{s}", weiss, False))
    # Hoehenleitwerk (Spannweite 30.37 m)
    kind(obj_aus(fluegel_bm(15.2, 1.2, 60.5, 9.5, 3.2, 35, 5, .9, .9, .2, s), f"hlw{s}", weiss))

# --- Seitenleitwerk bis 24.09 m Gesamthoehe (Rumpfachse liegt im Stand 6.0 m ueber Boden -> Spitze bei z = 18.1)
seiten_m = bpy.data.materials.new("seite"); seiten_m.use_nodes = True
n2 = seiten_m.node_tree.nodes; l2 = seiten_m.node_tree.links; b2 = n2["Principled BSDF"]
tc2 = n2.new("ShaderNodeTexCoord"); sp2 = n2.new("ShaderNodeSeparateXYZ"); l2.new(tc2.outputs["Object"], sp2.inputs[0])
mr = n2.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 3; mr.inputs["From Max"].default_value = 18; l2.new(sp2.outputs["Z"], mr.inputs["Value"])
cr = n2.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (*hexf("0b2a6f"), 1); cr.color_ramp.elements[1].color = (*hexf("19b4e6"), 1)
l2.new(mr.outputs["Result"], cr.inputs["Fac"]); l2.new(cr.outputs[0], b2.inputs["Base Color"]); b2.inputs["Roughness"].default_value = .3
bm = bmesh.new()
pts_u = [(57.5, 2.6), (70.5, 2.9)]; pts_o = [(67.0, 18.1), (71.6, 18.1)]
prof = [(0, 0), (.1, .35), (.5, .3), (1, 0), (.5, -.3), (.1, -.35)]
lagen = []
for (xl, zl), (xt, _) in (((57.5, 2.6), (70.5, 0)), ((67.0, 18.1), (71.6, 0))):
    c = xt - xl; d = 1.1 if zl < 10 else .3
    lagen.append([bm.verts.new((xl + c * px, d * py, zl)) for px, py in prof])
for k in range(len(prof)):
    bm.faces.new((lagen[0][k], lagen[0][(k + 1) % 6], lagen[1][(k + 1) % 6], lagen[1][k]))
bm.faces.new(lagen[1])
kind(obj_aus(bm, "seitenleitwerk", seiten_m))

# --- 4 Triebwerke (Gondeln + Pylone)
gondel_m = mat("gondel", hexf("dfe3ea"), .25, .2)
dunkel = mat("einlass", hexf("15181d"), .4, .7)
ENG = []
for s in (1, -1):
    for yy in (14.6, 26.0):
        le = 25.5 + (yy - 2.8) * math.tan(math.radians(33.5)); zw = -2.6 + (yy - 2.8) * math.tan(math.radians(5.6))
        x0 = le - 4.2; zz = zw - 2.1
        bpy.ops.mesh.primitive_cylinder_add(radius=1.48, depth=6.8, vertices=40, rotation=(0, P / 2, 0), location=(x0 + 3.4, s * yy, zz))
        g = kind(bpy.context.object); g.data.materials.append(gondel_m)
        tap = g.modifiers.new("t", "SIMPLE_DEFORM"); tap.deform_method = "TAPER"; tap.factor = -.25; tap.deform_axis = "Z"
        bpy.ops.mesh.primitive_cylinder_add(radius=1.3, depth=.3, vertices=40, rotation=(0, P / 2, 0), location=(x0 - .02, s * yy, zz))
        kind(bpy.context.object).data.materials.append(dunkel)
        bpy.ops.mesh.primitive_cone_add(radius1=.55, radius2=0, depth=1.6, vertices=24, rotation=(0, P / 2, 0), location=(x0 + 7.2, s * yy, zz))
        kind(bpy.context.object).data.materials.append(grau)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x0 + 4.5, s * yy, zz + 1.5)); py_ = kind(bpy.context.object)
        py_.scale = (5.5, .45, 1.4); py_.data.materials.append(weiss)
        for p in g.data.polygons:
            p.use_smooth = True

# --- Fahrwerk: 22 Raeder (Bug 2, Fluegel 2x4, Rumpf 2x6)
rad_m = mat("rad", hexf("161616"), .8)
FAHRWERK = []


def raeder(x, y, nx, ny, zachse=-6.0 + .68):
    for i in range(nx):
        for j in range(ny):
            bpy.ops.mesh.primitive_cylinder_add(radius=.68, depth=.5, vertices=24, rotation=(P / 2, 0, 0),
                                                location=(x + i * 1.8, y + (j - (ny - 1) / 2) * 1.1, zachse))
            r = kind(bpy.context.object); r.data.materials.append(rad_m); FAHRWERK.append(r)
    bpy.ops.mesh.primitive_cylinder_add(radius=.18, depth=3.2, location=(x + (nx - 1) * .9, y, zachse + 1.6))
    r = kind(bpy.context.object); r.data.materials.append(grau); FAHRWERK.append(r)


raeder(6.8, 0, 1, 2)
for s in (1, -1):
    raeder(36.2, s * 5.3, 2, 2)
    raeder(39.6, s * 2.2, 3, 2)

# ======================================================================  Umgebung
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; nt = w.node_tree
sky = nt.nodes.new("ShaderNodeTexSky")
try:
    sky.sky_type = "NISHITA"
except Exception:
    pass
sky.sun_elevation = math.radians(6); sky.sun_rotation = math.radians(200)
nt.links.new(sky.outputs[0], nt.nodes["Background"].inputs[0]); nt.nodes["Background"].inputs[1].default_value = .4
bpy.ops.object.light_add(type="SUN"); sonne = bpy.context.object
sonne.rotation_euler = (math.radians(81), 0, math.radians(200 - 90)); sonne.data.energy = 4.2; sonne.data.color = (1, .82, .62); sonne.data.angle = .02

# Boden: Gras + Piste mit Markierungen
bpy.ops.mesh.primitive_plane_add(size=60000, location=(0, 0, 0)); gras = bpy.context.object
gm = mat("gras", hexf("4c6b38"), .95); gras.data.materials.append(gm)
pm = bpy.data.materials.new("piste"); pm.use_nodes = True; n3 = pm.node_tree.nodes; l3 = pm.node_tree.links; b3 = n3["Principled BSDF"]
tc3 = n3.new("ShaderNodeTexCoord"); s3 = n3.new("ShaderNodeSeparateXYZ"); l3.new(tc3.outputs["Object"], s3.inputs[0])
# Mittellinie (gestrichelt) + Randlinien
mx = n3.new("ShaderNodeMath"); mx.operation = "MULTIPLY"; mx.inputs[1].default_value = 1 / 60; l3.new(s3.outputs["X"], mx.inputs[0])
fr3 = n3.new("ShaderNodeMath"); fr3.operation = "FRACT"; l3.new(mx.outputs[0], fr3.inputs[0])
st = n3.new("ShaderNodeMath"); st.operation = "LESS_THAN"; st.inputs[1].default_value = .5; l3.new(fr3.outputs[0], st.inputs[0])
ab = n3.new("ShaderNodeMath"); ab.operation = "ABSOLUTE"; l3.new(s3.outputs["Y"], ab.inputs[0])
mi = n3.new("ShaderNodeMath"); mi.operation = "LESS_THAN"; mi.inputs[1].default_value = .45; l3.new(ab.outputs[0], mi.inputs[0])
mi2 = n3.new("ShaderNodeMath"); mi2.operation = "MULTIPLY"; l3.new(mi.outputs[0], mi2.inputs[0]); l3.new(st.outputs[0], mi2.inputs[1])
rd = n3.new("ShaderNodeMath"); rd.operation = "GREATER_THAN"; rd.inputs[1].default_value = 28.5; l3.new(ab.outputs[0], rd.inputs[0])
li = n3.new("ShaderNodeMath"); li.operation = "MAXIMUM"; l3.new(mi2.outputs[0], li.inputs[0]); l3.new(rd.outputs[0], li.inputs[1])
mixp = n3.new("ShaderNodeMix"); mixp.data_type = "RGBA"; mixp.inputs[6].default_value = (*hexf("3a3c40"), 1); mixp.inputs[7].default_value = (.85, .85, .82, 1)
l3.new(li.outputs[0], mixp.inputs[0]); l3.new(mixp.outputs[2], b3.inputs["Base Color"]); b3.inputs["Roughness"].default_value = .8
bpy.ops.mesh.primitive_plane_add(size=1, location=(1200, 0, .03)); piste = bpy.context.object; piste.scale = (4000, 60, 1); piste.data.materials.append(pm)
bpy.ops.object.transform_apply(scale=True)
# Flughafen-Gebaeude in der Ferne
term = mat("terminal", hexf("b9c3cf"), .3, .5)
r = random.Random(3)
for i in range(16):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-300 + i * 160, 380 + r.uniform(0, 80), 0)); o = bpy.context.object
    h = r.uniform(12, 30); o.scale = (r.uniform(60, 140), r.uniform(30, 60), h); o.location.z = h / 2; o.data.materials.append(term)
bpy.ops.mesh.primitive_cylinder_add(radius=6, depth=70, location=(500, 330, 35)); turm = bpy.context.object; turm.data.materials.append(term)
bpy.ops.mesh.primitive_cylinder_add(radius=11, depth=8, location=(500, 330, 74)); kanzel = bpy.context.object; kanzel.data.materials.append(glas)
BODEN_OBJ = [gras, piste, turm, kanzel] + [o for o in bpy.data.objects if o.data and getattr(o.data, "materials", None) and len(o.data.materials) and o.data.materials[0] == term]

# Wolkendecke (fuer Flugszenen): Ebene mit Rauschen als Alpha
wm = bpy.data.materials.new("wolken"); wm.use_nodes = True; n4 = wm.node_tree.nodes; l4 = wm.node_tree.links
for k in list(n4):
    n4.remove(k)
out = n4.new("ShaderNodeOutputMaterial"); dif = n4.new("ShaderNodeBsdfDiffuse"); tr = n4.new("ShaderNodeBsdfTransparent"); mx4 = n4.new("ShaderNodeMixShader")
dif.inputs["Color"].default_value = (1, .93, .86, 1)
tc4 = n4.new("ShaderNodeTexCoord"); mp4 = n4.new("ShaderNodeMapping"); mp4.inputs["Scale"].default_value = (.0016, .0016, .0016)
nz4 = n4.new("ShaderNodeTexNoise"); nz4.inputs["Detail"].default_value = 10; nz4.inputs["Roughness"].default_value = .6
cr4 = n4.new("ShaderNodeValToRGB"); cr4.color_ramp.elements[0].position = .45; cr4.color_ramp.elements[1].position = .62
l4.new(tc4.outputs["Object"], mp4.inputs[0]); l4.new(mp4.outputs[0], nz4.inputs["Vector"]); l4.new(nz4.outputs["Fac"], cr4.inputs["Fac"])
l4.new(cr4.outputs[0], mx4.inputs["Fac"]); l4.new(tr.outputs[0], mx4.inputs[1]); l4.new(dif.outputs[0], mx4.inputs[2]); l4.new(mx4.outputs[0], out.inputs["Surface"])
WOLKEN_MAP = mp4
bpy.ops.mesh.primitive_plane_add(size=80000, location=(0, 0, -400)); wolken = bpy.context.object; wolken.data.materials.append(wm)
bpy.ops.mesh.primitive_plane_add(size=80000, location=(0, 0, -1200)); meer = bpy.context.object; meer.data.materials.append(mat("unten", hexf("2b4a66"), .5))

# ======================================================================  Kamera + Ablauf
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam; cam.data.lens = 32; cam.data.clip_end = 90000; cam.data.sensor_fit = "VERTICAL"


def ease(x):
    x = min(1, max(0, x)); return x * x * (3 - 2 * x)


def lerpv(a, b, k):
    return tuple(x + (y - x) * k for x, y in zip(a, b))


D = A.dauer
t_name = Z.get("name", 2.6); t_deck = Z.get("deck", 7.5); t_pax = Z.get("pax", 10.0); t_start = Z.get("start", 13.2)
t_251 = Z.get("built", 17.5); t_ende = Z.get("ende", 20.8)

# Flugzustand: im Flug steht das Flugzeug bei (0,0,0) (Wolken ziehen vorbei), am Boden steht die Rumpfachse auf z=6.0


def flugzeug_lage(t):
    """liefert (x, z, nick, boden) - boden=True: Bodenszene"""
    if t_pax - .05 <= t < t_251 - .2:
        # Bodenszene: rollt, hebt ab
        tr_ = max(0, t - t_start)
        x = 4.5 * tr_ ** 2 * 6           # Beschleunigung
        nick = math.radians(min(9, max(0, (tr_ - 1.6) * 10)))
        z = 6.0 + max(0, tr_ - 1.9) ** 2 * 9
        return x, z, nick, True
    return 0, 0, math.radians(2 + .6 * math.sin(t * .8)), False


START = ((-52, -62, -15), (32, 0, -1))   # schraeg von vorne unten: Spannweite gut sichtbar


def kamera(t, boden, fx, fz):
    if not boden:
        keys = [(0, *START), (t_name, (-48, -66, -13), (32, 0, -1)), (t_name + 1.6, (-12, -60, 4), (34, 0, 0)),
                (t_deck - .1, (10, -58, 2), (36, 0, 1)), (t_deck + 1.2, (36, -34, 1.5), (30, 0, 1)), (t_pax - .05, (40, -30, 1.5), (30, 0, 1)),
                (t_251 - .2, (90, -95, 18), (36, 0, 0)), (t_251 + 1.5, (140, 40, 30), (36, 0, 0)), (t_ende, (-40, -70, -8), (36, 0, -1)),
                (D - .8, *START), (D, *START)]
    else:
        keys = [(t_pax - .05, (64, -62, 4.0), (28, 0, 7)), (t_start - .3, (-20, -60, 3), (30, 0, 7)),
                (t_start + .5, (-60, -55, 4), (fx + 30, 0, fz)), (t_251 - .2, (-80, -95, 10), (fx + 30, 0, fz))]
    for a, b in zip(keys, keys[1:]):
        if a[0] <= t <= b[0]:
            k = ease((t - a[0]) / max(b[0] - a[0], 1e-6))
            return lerpv(a[1], b[1], k), lerpv(a[2], b[2], k)
    return keys[-1][1], keys[-1][2]


def zustand(t):
    x, z, nick, boden = flugzeug_lage(t)
    flug.location = (x, 0, z); flug.rotation_euler = (math.radians(.8 * math.sin(t * .6)), -nick, 0)
    for o in BODEN_OBJ:
        o.hide_render = not boden
    wolken.hide_render = boden; meer.hide_render = boden
    for r in FAHRWERK:
        r.hide_render = not boden
    WOLKEN_MAP.inputs["Location"].default_value = (t * 250 * .0016 * 1, 0, 0)
    FENSTER_LICHT.default_value = 1.5 if boden else 0
    pos, ziel = kamera(t, boden, x, z)
    if boden and t >= t_start + .5:
        pos = (pos[0] + x * .85, pos[1], pos[2] + (z - 6) * .8)
    cam.location = Vector(pos); d = Vector(ziel) - Vector(pos); cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


os.makedirs(A.ordner, exist_ok=True)
N = int(round(D * A.fps))
liste = [int(round(float(x) * A.fps)) for x in A.nur.split(",")] if A.nur else list(range(A.start, N))
for f in liste:
    pfad = os.path.join(A.ordner, f"a380_{f:04d}.png")
    if os.path.exists(pfad) and not A.nur:
        continue
    zustand(f / A.fps); sc.render.filepath = pfad
    bpy.ops.render.render(write_still=True); print("FERTIG", pfad, flush=True)
