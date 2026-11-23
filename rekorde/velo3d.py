"""Geschichte: Eine Frau hat einen Job: Velo fahren - 296,009 km/h im Windschatten (Denise Mueller-Korenek, Bonneville 16.9.2018, GWR).
Szene: Salzsee (Salzkruste mit Waben-Rissen, schwarze Fuehrungslinie, Markierungspfosten, Zeitmess-Lichtschranken, Boxengasse),
Dragster mit grossem Windschild-Kasten hinten, Abschleppseil, Rekordvelo (lang, Motorradraeder, Federgabel, Riesen-Kettenblatt mit
Doppel-Uebersetzung), Fahrerin (MPFB) im Rennanzug mit Aero-Helm, Beine/Arme per IK an Pedalen und Lenker.
python3 velo3d.py <ordner> [--nur t1,t2] [--start i] [--samples n]"""
import bpy, bmesh, math, random, sys, os, argparse
from mathutils import Vector, Matrix, Euler
HIER = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HIER)
import mensch_mh as MH

ap = argparse.ArgumentParser()
ap.add_argument("ordner"); ap.add_argument("--nur", default=""); ap.add_argument("--skala", type=int, default=50)
ap.add_argument("--samples", type=int, default=10); ap.add_argument("--fps", type=int, default=15)
ap.add_argument("--start", type=int, default=0); ap.add_argument("--blur", type=int, default=0)
A = ap.parse_args(sys.argv[1:])
P = math.pi
D = 26.6
TREL = 11.1        # Seil loesen
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = A.samples; sc.cycles.use_denoising = True
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.transmission_bounces = 2
sc.cycles.transparent_max_bounces = 6; sc.cycles.adaptive_threshold = .03
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1080, 1920, A.skala
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"; sc.view_settings.exposure = -2.3
sc.render.fps = A.fps
if A.blur:
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = .35
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


def box(name, groesse, ort, m, bevel=.01, seg=2, rot=(0, 0, 0), eltern=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=ort, rotation=rot); o = bpy.context.object; o.name = name; o.scale = groesse
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        bv = o.modifiers.new("b", "BEVEL"); bv.width = bevel; bv.segments = seg
    o.data.materials.append(m)
    if eltern:
        o.parent = eltern
    return o


def zyl(name, r, l, ort, m, rot=(0, 0, 0), eltern=None, v=24, bevel=0):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=l, vertices=v, location=ort, rotation=rot); o = bpy.context.object; o.name = name
    o.data.materials.append(m)
    for p in o.data.polygons:
        p.use_smooth = True
    if bevel:
        bv = o.modifiers.new("b", "BEVEL"); bv.width = bevel; bv.segments = 2; bv.limit_method = "ANGLE"
    if eltern:
        o.parent = eltern
    return o


def rohr(name, a, b, r, m, eltern=None):
    a, b = Vector(a), Vector(b); d = b - a
    o = zyl(name, r, d.length, (a + b) / 2, m, eltern=eltern, v=12)
    o.rotation_mode = "QUATERNION"; o.rotation_quaternion = d.to_track_quat("Z", "Y")
    return o


def leer(name, ort=(0, 0, 0), eltern=None):
    o = bpy.data.objects.new(name, None); sc.collection.objects.link(o); o.location = ort
    if eltern:
        o.parent = eltern
    return o


def rad(name, r, breite, m_reifen, m_felge, eltern, ort, speichen=6, reifen=.06):
    """Rad dreht um lokale y-Achse; Ursprung = Achse."""
    w = leer(name, ort, eltern)
    bpy.ops.mesh.primitive_torus_add(major_radius=r - reifen, minor_radius=reifen, major_segments=48, minor_segments=12,
                                     location=(0, 0, 0), rotation=(P / 2, 0, 0))
    t = bpy.context.object; t.name = name + "_reifen"; t.scale.y = breite / (2 * reifen); t.data.materials.append(m_reifen); t.parent = w
    for p in t.data.polygons:
        p.use_smooth = True
    zyl(name + "_felge", r - reifen * 1.6, breite * .3, (0, 0, 0), m_felge, rot=(P / 2, 0, 0), eltern=w, v=40)
    for k in range(speichen):
        a = 2 * P * k / speichen
        s = box(name + "_sp", (.03 * r / .3, breite * .5, (r - reifen) * .95), (0, 0, 0), m_felge, .004, eltern=w)
        s.rotation_euler = (0, a, 0); s.location = (math.sin(a) * (r - reifen) * .48, 0, math.cos(a) * (r - reifen) * .48)
    zyl(name + "_nabe", r * .16, breite * 1.05, (0, 0, 0), m_felge, rot=(P / 2, 0, 0), eltern=w)
    return w


# ======================================================================  Fahrerin
fr = MH.Arbeiter(name="fahrerin", seed=21, maenn=0.0, alter=.45, muskel=.85, gewicht=.3, haut="caucasian", weste=False)
SCHWARZ = mat("anzug_schwarz", "121214", .4)
for o in fr.huellen:
    if o.name.endswith("_hemd"):
        MH_m = o.active_material
        for nd in MH_m.node_tree.nodes:
            if nd.type == "MIX" and nd.data_type == "RGBA":
                nd.inputs[6].default_value = (*hexf("161618"), 1); nd.inputs[7].default_value = (*hexf("161618"), 1)
        MH_m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = .38
        o.modifiers["versatz"].strength = .004
    elif o.name.endswith("_hose"):
        for nd in o.active_material.node_tree.nodes:
            if nd.type == "MIX" and nd.data_type == "RGBA":
                nd.inputs[6].default_value = (*hexf("141416"), 1); nd.inputs[7].default_value = (*hexf("141416"), 1)
        o.modifiers["versatz"].strength = .004
    elif o.name.endswith("_gesicht"):
        o.hide_render = True
    elif o.name.endswith("_hand"):
        o.active_material = SCHWARZ
for o in fr.helm:
    o.hide_render = True
for o in fr.stiefel:
    if "schaft" in o.name:
        o.scale.z *= .4
    o.active_material = SCHWARZ
fr.objekte = [o for o in fr.objekte if o not in fr.helm and not o.name.endswith("_gesicht")]
# Aero-Helm (Tropfenform) am Kopfknochen
HK = fr.gm("joint-head")
bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=20, radius=1)
for v in bm.verts:
    x, y, z = v.co
    if y > 0:                      # nach hinten (Person schaut -y) lang ausgezogen
        y *= 1.0 + 1.6 * max(0, y) * (1 - .3 * abs(z)); z -= .35 * max(0, v.co.y) ** 2
    v.co = Vector((x * .118, y * .135, z * .13))
me = bpy.data.meshes.new("helm"); bm.to_mesh(me); bm.free()
helm = bpy.data.objects.new("aerohelm", me); sc.collection.objects.link(helm)
helm_m = mat("aerohelm", "f2f2f0", .22, Coat_Weight=.8); me.materials.append(helm_m)
for p in me.polygons:
    p.use_smooth = True
helm.location = HK + Vector((0, .012, .045))
visier = bpy.data.objects.new("visier", None)
bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=1)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y > -.35 or v.co.z > .45 or v.co.z < -.55], context="VERTS")
me = bpy.data.meshes.new("visier"); bm.to_mesh(me); bm.free()
visier = bpy.data.objects.new("visier", me); sc.collection.objects.link(visier)
me.materials.append(mat("visier", "1a1f2a", .05, .6, Coat_Weight=1.0))
for p in me.polygons:
    p.use_smooth = True
visier.scale = (.112, .128, .1); visier.location = HK + Vector((0, -.004, .01))
streif = box("helmstreifen", (.03, .2, .01), HK + Vector((0, .08, .175)), mat("helmstreifen", "e8ff2a", .3), .004)
bpy.context.view_layer.update()
bn = fr.rig.data.bones["head"]
PI_ = (fr.rig.matrix_world @ bn.matrix_local @ Matrix.Translation((0, bn.length, 0))).inverted()
for o in (helm, visier, streif):
    o.parent = fr.rig; o.parent_type = "BONE"; o.parent_bone = "head"; o.matrix_parent_inverse = PI_
    fr.objekte.append(o)
BECKEN = fr.gm("joint-pelvis")

# ======================================================================  Rekordvelo (faehrt +x; Ursprung Boden unter Tretlager)
VELO = leer("velo")
CARBON = mat("carbon", "18191c", .28, Coat_Weight=.7)
REIFEN = mat("reifen", "151515", .75)
ALU = mat("alu", "b9bdc4", .22, 1)
GELBL = mat("akzent", "e8ff2a", .35)
RR = .31
HINTEN, VORNE = Vector((-.95, 0, RR)), Vector((.85, 0, RR))
TL = Vector((-.02, 0, .30))                  # Tretlager
SATTEL = Vector((-.30, 0, .90))
STEUER = Vector((.62, 0, .78))
rad_h = rad("hinterrad", RR, .13, REIFEN, ALU, VELO, HINTEN)
rad_v = rad("vorderrad", RR, .11, REIFEN, ALU, VELO, VORNE)
for a, b, r in [(HINTEN, TL, .022), (HINTEN, Vector((-.36, 0, .78)), .02), (TL, Vector((-.36, 0, .78)), .03),
                (TL, STEUER + Vector((0, 0, -.1)), .034), (Vector((-.36, 0, .78)), STEUER, .03), (Vector((-.36, 0, .78)), SATTEL, .018)]:
    for dy in ((-.06, .06) if a == HINTEN else (0,)):
        rohr("rahmen", a + Vector((0, dy, 0)), b + Vector((0, dy * .2, 0)), r, CARBON, VELO)
rohr("steuerrohr", STEUER + Vector((.03, 0, .08)), STEUER + Vector((-.03, 0, -.14)), .032, CARBON, VELO)
# Federgabel (Motorrad-Stil): zwei Standrohre
for dy in (-.07, .07):
    rohr("gabel", VORNE + Vector((0, dy, 0)), STEUER + Vector((-.02, dy * .7, -.06)), .022, ALU, VELO)
    rohr("gabel_tauch", VORNE + Vector((0, dy, 0)), VORNE + Vector((-.06, dy, .22)), .03, CARBON, VELO)
box("sattel", (.26, .1, .04), SATTEL + Vector((0, 0, .02)), mat("sattel", "0e0e0e", .6), .015, eltern=VELO)
# Lenker: tiefer Aero-Lenker
GRIFF = [Vector((.40, .15, .74)), Vector((.40, -.15, .74))]
rohr("vorbau", STEUER + Vector((-.02, 0, .08)), Vector((.46, 0, .76)), .02, ALU, VELO)
rohr("lenker", Vector((.46, .17, .76)), Vector((.46, -.17, .76)), .016, ALU, VELO)
for g in GRIFF:
    rohr("griff", g + Vector((.05, 0, .02)), g + Vector((-.06, 0, -.01)), .02, mat("griffband", "1b1b1b", .8), VELO)
# Antrieb: Riesen-Kettenblatt am Tretlager (rechts, -y), Zwischenwelle (Doppel-Uebersetzung), Ritzel hinten
KURBEL = leer("kurbel", TL, VELO)


def kettenblatt(name, r, zaehne, y, eltern, ort=(0, 0, 0)):
    bm = bmesh.new(); n = zaehne * 2; aus, inn = [], []
    ri = r - max(.012, r * .14)
    for k in range(n):
        a = 2 * P * k / n; rr = r + (.008 if k % 2 == 0 else 0)
        aus.append(bm.verts.new((rr * math.cos(a), y, rr * math.sin(a)))); inn.append(bm.verts.new((ri * math.cos(a), y, ri * math.sin(a))))
    fl = [bm.faces.new((aus[k], aus[(k + 1) % n], inn[(k + 1) % n], inn[k])) for k in range(n)]
    bmesh.ops.solidify(bm, geom=fl, thickness=.006)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o); me.materials.append(ALU); o.parent = eltern; o.location = ort
    if r > .1:
        for k in range(5):
            a = 2 * P * k / 5 + .3
            box(name + "_arm", (.03, .008, ri), (ri / 2 * math.cos(a), y, ri / 2 * math.sin(a)), CARBON, .004, rot=(0, P / 2 - a, 0), eltern=o)
    zyl(name + "_mitte", min(.04, r * .5), .02, (0, y, 0), ALU, rot=(P / 2, 0, 0), eltern=o)
    return o


blatt = kettenblatt("kettenblatt", .25, 60, -.1, KURBEL)
ARME = []
for s, dy in ((1, -.125), (-1, .125)):
    arm_ = box("kurbelarm", (.035, .018, .175), (0, dy, -s * .0875), ALU, .006, eltern=KURBEL)
    ped = box("pedal", (.09, .06, .016), (0, dy * 1.45, -s * .175), mat("pedalm", "202020", .5) if not bpy.data.materials.get("pedalm") else bpy.data.materials["pedalm"], .005, eltern=KURBEL)
    ARME.append(ped)
ZW = Vector((-.5, 0, .42))
zwr = leer("zwischenwelle", ZW, VELO)
kettenblatt("zw_ritzel", .05, 14, -.1, zwr); kettenblatt("zw_blatt", .09, 24, -.13, zwr)
ritzel = kettenblatt("ritzel", .06, 16, -.13, rad_h)
rohr("zw_halter", ZW, TL, .015, CARBON, VELO); rohr("zw_halter2", ZW, HINTEN, .015, CARBON, VELO)
KETTE = mat("kette", "3a3a3a", .4, .8)
for (pa, ra), (pb, rb), y in (((TL, .25), (ZW, .05), -.1), ((ZW, .09), (HINTEN, .06), -.13)):
    for sgn in (1, -1):
        d = (pb - pa).normalized(); nrm = Vector((-d.z, 0, d.x)) * sgn
        rohr("kette", pa + nrm * ra + Vector((0, y, 0)), pb + nrm * rb + Vector((0, y, 0)), .006, KETTE, VELO)
# Seilhaken vorne am Velo
HAKEN = Vector((.72, 0, .62))
box("haken", (.06, .04, .04), HAKEN, mat("haken", "d23c2c", .4, .5), .008, eltern=VELO)

# ======================================================================  Dragster (faehrt +x; Ursprung = Hinterkante Windschild-Kasten)
DR = leer("dragster")
LACK = mat("lack", "103a8c", .25, Coat_Weight=1.0)
WEISSL = mat("weisslack", "f1f1ee", .3, Coat_Weight=.8)
CHROM = mat("chrom", "d8dde3", .08, 1)
DUNKEL = mat("dunkel", "0c0c0c", .6)
# Windschild-Kasten: hinten offen, seitlich kurze Schuerzen
KW, KH = 1.9, 2.15
bm = bmesh.new()
def q(a, b, c, d):
    vs = [bm.verts.new(p) for p in (a, b, c, d)]; bm.faces.new(vs)
y0, y1, z0, z1 = -KW / 2, KW / 2, .12, KH
q((1.3, y0, z0), (1.3, y1, z0), (1.3, y1, z1), (1.3, y0, z1))                     # Rueckwand des Fahrzeugs (Front fuer Velo)
q((0, y0, z0), (1.3, y0, z0), (1.3, y0, z1), (0, y0, z1)); q((0, y1, z0), (1.3, y1, z0), (1.3, y1, z1), (0, y1, z1))
q((0, y0, z1), (1.3, y0, z1), (1.3, y1, z1), (0, y1, z1))
me = bpy.data.meshes.new("kasten"); bm.to_mesh(me); bm.free()
kasten = bpy.data.objects.new("kasten", me); sc.collection.objects.link(kasten); kasten.parent = DR; me.materials.append(WEISSL)
so = kasten.modifiers.new("s", "SOLIDIFY"); so.thickness = .035; bv = kasten.modifiers.new("b", "BEVEL"); bv.width = .03; bv.segments = 3
# Front des Kastens gerundet (Nase zum Fahrtwind)
bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1, location=(1.3, 0, (z0 + z1) / 2)); kn = bpy.context.object
kn.scale = (1.0, KW / 2, (z1 - z0) / 2); kn.data.materials.append(LACK); kn.parent = DR; kn.name = "kasten_nase"
bm = bmesh.new(); bm.from_mesh(kn.data); bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.x < 0], context="VERTS"); bm.to_mesh(kn.data); bm.free()
for p in kn.data.polygons:
    p.use_smooth = True
for z_ in (.55, 1.65):
    for dy in (-KW / 2 - .03, KW / 2 + .03):
        box("kastenstreifen", (1.32, .02, .09), (.66, dy, z_), LACK, .005, eltern=DR)
KANTE = mat("kante", "d23c2c", .4)
for dy in (-KW / 2, KW / 2):
    box("kastenkante", (.07, .1, KH - .05), (0, dy, (z0 + z1) / 2 + .02), KANTE, .01, eltern=DR)
box("kastenkante_o", (.07, KW + .1, .1), (0, 0, z1), KANTE, .01, eltern=DR)
# Fahrgestell
for dy in (-.32, .32):
    rohr("rahmen_dr", (1.6, dy, .32), (9.2, dy * .3, .22), .035, CHROM, DR)
    rohr("rahmen_dr2", (2.2, dy, .32), (3.6, dy * .8, .95), .025, CHROM, DR)
# Hinterraeder (breite Slicks)
DRAD = []
for dy in (-1.08, 1.08):
    DRAD.append(rad("dr_hinten", .55, .45, REIFEN, CHROM, DR, (2.35, dy, .55), speichen=8, reifen=.17))
for dy in (-.48, .48):
    DRAD.append(rad("dr_vorne", .22, .07, REIFEN, CHROM, DR, (9.0, dy, .22), speichen=6, reifen=.04))
rohr("achse_h", (2.35, -1.0, .55), (2.35, 1.0, .55), .05, CHROM, DR); rohr("achse_v", (9.0, -.45, .22), (9.0, .45, .22), .025, CHROM, DR)
# Karosserie: lange Spitze vorne
bm = bmesh.new(); prof = [(2.3, .55, .45), (3.6, .52, .5), (5.0, .42, .42), (7.0, .28, .28), (8.6, .18, .18), (9.6, .05, .06)]
ringe = []
for x, ry, rz in prof:
    ringe.append([bm.verts.new((x, ry * math.cos(2 * P * k / 24), .42 + rz * .7 * math.sin(2 * P * k / 24))) for k in range(24)])
for a, b in zip(ringe, ringe[1:]):
    for k in range(24):
        bm.faces.new((a[k], a[(k + 1) % 24], b[(k + 1) % 24], b[k]))
me = bpy.data.meshes.new("karosse"); bm.to_mesh(me); bm.free()
kar = bpy.data.objects.new("karosse", me); sc.collection.objects.link(kar); kar.parent = DR; me.materials.append(LACK)
for p in me.polygons:
    p.use_smooth = True
kar.modifiers.new("s", "SUBSURF").levels = 1
box("streifen", (5.5, .04, .1), (5.6, 0, .78), WEISSL, .01, eltern=DR)
# Cockpit + Ueberrollkaefig + Motor mit Kompressor und Auspuffrohren
box("cockpit", (.9, .62, .25), (2.9, 0, .82), DUNKEL, .03, eltern=DR)
for dy in (-.3, .3):
    rohr("kaefig", (2.5, dy, .8), (2.75, dy, 1.45), .025, CHROM, DR); rohr("kaefig2", (3.3, dy, .8), (2.75, dy, 1.45), .025, CHROM, DR)
rohr("kaefig_q", (2.75, -.3, 1.45), (2.75, .3, 1.45), .025, CHROM, DR)
box("fahrerhelm_dr", (.24, .22, .24), (2.75, 0, 1.12), mat("drhelm", "f2f2f2", .25), .1, eltern=DR)
box("motor", (1.0, .55, .45), (4.2, 0, .82), mat("motor", "2a2d33", .35, .7), .04, eltern=DR)
box("kompressor", (.7, .38, .3), (4.25, 0, 1.2), CHROM, .05, eltern=DR)
box("lufthutze", (.35, .32, .3), (4.4, 0, 1.48), LACK, .06, eltern=DR)
for i in range(8):
    for dy in (-.3, .3):
        x_ = 3.8 + i * .12
        rohr("auspuff", (x_, dy, .85), (x_ - .12, dy * 1.9, 1.05), .028, mat("rohr%d" % i, "8a6a4a", .35, 1) if i == 0 else bpy.data.materials["rohr0"], DR)
# Salzstaub hinter den Dragster-Hinterraedern (halbtransparente Fahnen)
staub_m = bpy.data.materials.new("staub"); staub_m.use_nodes = True; n = staub_m.node_tree.nodes; l = staub_m.node_tree.links
for k in list(n):
    n.remove(k)
out = n.new("ShaderNodeOutputMaterial"); mx = n.new("ShaderNodeMixShader"); tr = n.new("ShaderNodeBsdfTransparent")
df = n.new("ShaderNodeBsdfDiffuse"); df.inputs[0].default_value = (.95, .95, .93, 1)
tc = n.new("ShaderNodeTexCoord"); nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 3; nz.inputs["Detail"].default_value = 5
l.new(tc.outputs["Generated"], nz.inputs["Vector"])
sep = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Generated"], sep.inputs[0])
mu = n.new("ShaderNodeMath"); mu.operation = "MULTIPLY"; l.new(nz.outputs["Fac"], mu.inputs[0]); l.new(sep.outputs["X"], mu.inputs[1])
cr = n.new("ShaderNodeMapRange"); cr.inputs["From Min"].default_value = .25; cr.inputs["From Max"].default_value = .7
cr.inputs["To Max"].default_value = .32; l.new(mu.outputs[0], cr.inputs["Value"])
l.new(cr.outputs[0], mx.inputs[0]); l.new(tr.outputs[0], mx.inputs[1]); l.new(df.outputs[0], mx.inputs[2]); l.new(mx.outputs[0], out.inputs[0])
STAUB = []
for dy in (-1.08, 1.08):
    bpy.ops.mesh.primitive_cone_add(radius1=.2, radius2=.65, depth=5, vertices=24, location=(-.6, dy * 1.3, .4), rotation=(0, P / 2, 0))
    o = bpy.context.object; o.parent = DR; o.data.materials.append(staub_m); o.visible_shadow = False; STAUB.append(o)
    o.rotation_euler = (0, -P / 2 + .06, 0)
    o.scale.z = 1.0
# Seil
SEIL = zyl("seil", .008, 1, (0, 0, 0), mat("seil", "e8e2c8", .7))

# ======================================================================  Salzsee
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; nt = w.node_tree
sky = nt.nodes.new("ShaderNodeTexSky"); sky.sun_elevation = math.radians(38); sky.sun_rotation = math.radians(205)
try:
    sky.aerosol_density = 1.5
except Exception:
    pass
nt.links.new(sky.outputs[0], nt.nodes["Background"].inputs[0]); nt.nodes["Background"].inputs[1].default_value = .35
bpy.ops.object.light_add(type="SUN"); sonne = bpy.context.object
sonne.rotation_euler = Euler((math.radians(52), 0, math.radians(205 - 90))); sonne.data.energy = 4.2; sonne.data.color = (1, .95, .88); sonne.data.angle = .012

salz = bpy.data.materials.new("salz"); salz.use_nodes = True; n = salz.node_tree.nodes; l = salz.node_tree.links; b = n["Principled BSDF"]
tc = n.new("ShaderNodeTexCoord")
vo = n.new("ShaderNodeTexVoronoi"); vo.feature = "DISTANCE_TO_EDGE"; vo.inputs["Scale"].default_value = 1.1; l.new(tc.outputs["Object"], vo.inputs["Vector"])
rid = n.new("ShaderNodeMapRange"); rid.inputs["From Min"].default_value = 0; rid.inputs["From Max"].default_value = .06
rid.inputs["To Min"].default_value = 1; rid.inputs["To Max"].default_value = 0; l.new(vo.outputs["Distance"], rid.inputs["Value"])
nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = .02; nz.inputs["Detail"].default_value = 8; l.new(tc.outputs["Object"], nz.inputs["Vector"])
nz2 = n.new("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = 9; nz2.inputs["Detail"].default_value = 4; l.new(tc.outputs["Object"], nz2.inputs["Vector"])
cr = n.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (*hexf("b9b5aa"), 1); cr.color_ramp.elements[1].color = (*hexf("dcd8cf"), 1)
l.new(nz.outputs["Fac"], cr.inputs["Fac"])
mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.inputs[7].default_value = (*hexf("eeebe4"), 1)
l.new(rid.outputs[0], mx.inputs[0]); l.new(cr.outputs[0], mx.inputs[6])
# schwarze Fuehrungslinie bei y = +3.2 (Breite 0.3 m)
sp = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Object"], sp.inputs[0])
sb = n.new("ShaderNodeMath"); sb.operation = "SUBTRACT"; sb.inputs[1].default_value = 3.2; l.new(sp.outputs["Y"], sb.inputs[0])
ab = n.new("ShaderNodeMath"); ab.operation = "ABSOLUTE"; l.new(sb.outputs[0], ab.inputs[0])
lt = n.new("ShaderNodeMath"); lt.operation = "LESS_THAN"; lt.inputs[1].default_value = .15; l.new(ab.outputs[0], lt.inputs[0])
mx2 = n.new("ShaderNodeMix"); mx2.data_type = "RGBA"; mx2.inputs[7].default_value = (*hexf("161616"), 1)
l.new(lt.outputs[0], mx2.inputs[0]); l.new(mx.outputs[2], mx2.inputs[6]); l.new(mx2.outputs[2], b.inputs["Base Color"])
b.inputs["Roughness"].default_value = .82
bp = n.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = .55; bp.inputs["Distance"].default_value = .02
ad = n.new("ShaderNodeMath"); ad.operation = "ADD"; l.new(rid.outputs[0], ad.inputs[0]); l.new(nz2.outputs["Fac"], ad.inputs[1])
l.new(ad.outputs[0], bp.inputs["Height"]); l.new(bp.outputs[0], b.inputs["Normal"])
bpy.ops.mesh.primitive_plane_add(size=60000); boden = bpy.context.object; boden.data.materials.append(salz); boden.location.x = 10000
# Berge am Horizont (dunstig blau-grau)
berg_m = mat("berg", "596173", .95)
r = random.Random(7)
tx = bpy.data.textures.new("bergtex", "CLOUDS"); tx.noise_scale = .3
for i in range(26):
    a_ = r.uniform(0, 2 * P); d = r.uniform(9000, 16000)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=5, radius=1, location=(1500 + d * math.cos(a_), d * math.sin(a_), -200))
    o = bpy.context.object; o.scale = (r.uniform(2000, 4500), r.uniform(2000, 4500), r.uniform(600, 1500)); o.data.materials.append(berg_m)
    dm = o.modifiers.new("d", "DISPLACE"); dm.texture = tx; dm.strength = .35; dm.texture_coords = "LOCAL"
    for p in o.data.polygons:
        p.use_smooth = True
# Markierungspfosten mit Fahnen alle 100 m, Lichtschranken (Zeitmessung) alle 400 m
pf_m = mat("pfosten", "f05a1a", .5); fahne_m = mat("fahne", "ffd21a", .6, Sheen_Weight=.5)
for i in range(-2, 32):
    x_ = i * 100
    for y_ in (-6.5, 9.5):
        zyl("pfosten", .04, 1.6, (x_, y_, .8), pf_m)
        box("fahne", (.45, .01, .3), (x_ - .24, y_, 1.42), fahne_m, 0)
    if i % 4 == 0:
        for y_ in (-4.5, 7.5):
            for k in range(3):
                a = 2 * P * k / 3
                rohr("stativ", (x_ + .35 * math.cos(a), y_ + .35 * math.sin(a), 0), (x_, y_, .9), .015, mat("stativ", "222222", .5) if k == 0 and i == -0 and y_ < 0 else bpy.data.materials.get("stativ"))
            box("lichtschranke", (.16, .14, .12), (x_, y_, .95), mat("ls", "eeeeee", .4) if not bpy.data.materials.get("ls") else bpy.data.materials["ls"], .01)
            box("ls_linse", (.02, .06, .06), (x_, y_ + (.08 if y_ < 0 else -.08), .95), mat("linse", "c0102a", .1, Emission_Color=(1, .1, .1, 1), Emission_Strength=4) if not bpy.data.materials.get("linse") else bpy.data.materials["linse"], 0)
# Boxengasse beim Start: Anhaenger, Pickups, Zelte, Zuschauer
r = random.Random(11)
farben = ["d7d7d7", "2b2b2b", "b71c1c", "1e4fa3", "f2f2f2", "37474f", "e0e0e0"]
for i in range(16):
    x_ = -60 + i * 14 + r.uniform(-3, 3); y_ = 38 + r.uniform(-4, 6)
    if i % 3 == 0:
        box("anhaenger", (11, 2.5, 3.0), (x_, y_, 1.8), mat("anh%d" % i, r.choice(farben), .35), .05)
    else:
        box("pickup", (5.4, 2.0, 1.0), (x_, y_, .85), mat("pk%d" % i, r.choice(farben), .3, Coat_Weight=.6), .12)
        box("pickup_kabine", (2.0, 1.8, .8), (x_ + .8, y_, 1.7), bpy.data.materials["pk%d" % i], .12)
        for dx in (-1.7, 1.7):
            for dy in (-.95, .95):
                zyl("pkrad", .38, .28, (x_ + dx, y_ + dy, .38), REIFEN, rot=(P / 2, 0, 0))
for i in range(5):
    x_ = -40 + i * 40; y_ = 28
    box("zeltdach", (5, 5, .15), (x_, y_, 2.6), mat("zelt%d" % i, ["f2f2f2", "1e4fa3", "f2f2f2", "d23c2c", "f2f2f2"][i], .7), .02)
    for dx in (-2.4, 2.4):
        for dy in (-2.4, 2.4):
            zyl("zeltbein", .03, 2.6, (x_ + dx, y_ + dy, 1.3), CHROM)
zk = [mat("zk%d" % i, c, .7) for i, c in enumerate(["e53935", "1e88e5", "fdd835", "fafafa", "212121", "43a047", "ff7043"])]
zh = mat("zkopf", "c68642", .6)
for i in range(70):
    x_ = r.uniform(-60, 160); y_ = r.uniform(20, 32)
    box("zuschauer", (.4, .28, 1.2), (x_, y_, .6), r.choice(zk), .05)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=.12, location=(x_, y_, 1.35)); bpy.context.object.data.materials.append(zh)

# ======================================================================  Windschlieren (nur in den Wind-Einstellungen sichtbar)
wind_m = mat("windstreifen", "ffffff", .5, Alpha=.35, Emission_Color=(1, 1, 1, 1), Emission_Strength=.6)
WIND = []
r = random.Random(5)
while len(WIND) < 140:
    y_, z_ = r.uniform(-3.2, 3.2), r.uniform(.15, 3.2)
    if abs(y_) < 1.1 and z_ < 2.3:       # im Windschatten keine Streifen
        continue
    o = zyl("wind", .005, r.uniform(1.5, 4), (0, 0, 0), wind_m, rot=(0, P / 2, 0), v=6)
    o["y"], o["z"], o["ph"] = y_, z_, r.random(); o.visible_shadow = False; WIND.append(o)

# ======================================================================  Bewegung
def v_rad(t):
    if t < TREL:
        return 18 + 2.4 * max(t, 0)
    if t < 19.0:
        k = (t - TREL) / (19.0 - TREL); return 44.64 + (82.22 - 44.64) * (1 - (1 - k) ** 2)
    if t < 24.0:
        return 82.22
    return max(20, 82.22 - 7 * (t - 24))


TAB = []; xx = 0.0; tt = -3.0
while tt < D + 3:
    TAB.append(xx); xx += v_rad(tt) * .005; tt += .005


def x_von(t):
    i = (t + 3.0) / .005; i0 = int(i); k = i - i0
    return TAB[i0] * (1 - k) + TAB[min(i0 + 1, len(TAB) - 1)] * k


KURBEL_TAB = []; ph = 0.0; tt = -3.0
while tt < D + 3:
    KURBEL_TAB.append(ph); ph += 2 * P * (.9 + 1.2 * min(1, max(0, (v_rad(tt) - 40) / 42))) * .005; tt += .005


def kurbel_von(t):
    i = int((t + 3.0) / .005); return KURBEL_TAB[min(i, len(KURBEL_TAB) - 1)]


def abstand(t):
    """Abstand Kastenhinterkante -> Velo-Ursprung"""
    if t < TREL:
        return 4.2
    return 4.2 - 2.55 * ease((t - TREL) / 1.6)


# IK: Fuesse an Pedale, Haende an Lenker
LEAN = 1.32
ZIELE = {}
for nm in ("fuss_L", "fuss_R", "hand_L", "hand_R", "knie_pol", "ell_L", "ell_R"):
    ZIELE[nm] = leer("ik_" + nm, (0, 0, 0), VELO)
for bone, ziel, pol, kette, pw in (("lowerleg02.L", "fuss_L", "knie_pol", 4, -P / 2), ("lowerleg02.R", "fuss_R", "knie_pol", 4, -P / 2),
                                   ("lowerarm02.L", "hand_L", "ell_L", 4, 0), ("lowerarm02.R", "hand_R", "ell_R", 4, 0)):
    c = fr.rig.pose.bones[bone].constraints.new("IK"); c.target = ZIELE[ziel]; c.chain_count = kette
    c.pole_target = ZIELE[pol]; c.pole_angle = pw
ZIELE["knie_pol"].location = (1.6, 0, 1.0)
ZIELE["ell_L"].location = (.1, .9, .4); ZIELE["ell_R"].location = (.1, -.9, .4)
ZIELE["hand_L"].location = GRIFF[0] + Vector((-.02, .02, .03)); ZIELE["hand_R"].location = GRIFF[1] + Vector((-.02, -.02, .03))
# Becken auf den Sattel: Rig (Person schaut -y; Gier P/2 -> schaut +x), Vorneigung um X
fr.rig.parent = VELO
R_ = Euler((LEAN, 0, P / 2)).to_matrix()
fr.rig.rotation_euler = (LEAN, 0, P / 2)
fr.rig.location = SATTEL + Vector((.02, 0, .06)) - R_ @ BECKEN


def figuren(t):
    xv = x_von(t); xb = xv - abstand(t)
    DR.location = (xv, 0, 0); VELO.location = (xb, 0, 0)
    v = v_rad(t)
    for w_ in DRAD:
        w_.rotation_euler.y = xv / (.55 if w_.name.startswith("dr_hinten") else .22)
    rad_h.rotation_euler.y = xb / RR; rad_v.rotation_euler.y = xb / RR
    a = kurbel_von(t); KURBEL.rotation_euler.y = a; zwr.rotation_euler.y = a * 3.1
    for k, nm in enumerate(("fuss_R", "fuss_L")):
        aa = a + k * P
        p = TL + Vector((.175 * math.sin(aa), (-.19 if nm == "fuss_R" else .19), -.175 * math.cos(aa))) + Vector((-.03, 0, .07))
        ZIELE[nm].location = p
    fr.zuruecksetzen()
    fr.dreh("neck01", x=-.55); fr.dreh("neck02", x=-.25); fr.dreh("head", x=-.15)
    fr.dreh("spine03", x=.05 * math.sin(a * 2)); fr.dreh("spine01", x=-.1)
    # Seil
    if t < TREL:
        p0 = Vector((xv - .02, 0, .62)); p1 = VELO.matrix_world @ HAKEN if False else Vector((xb, 0, 0)) + HAKEN
    else:
        k = min(1, (t - TREL) / .5)
        p0 = Vector((xv - .02, 0, .62)); p1 = Vector((xv - .02 - 3.2 * (1 - k) - .4 * k, 0, max(.01, .62 - .9 * k * k)))
        if t > TREL + 1.2:
            p1 = p0 + Vector((-.3, 0, -.6))
    d = p1 - p0; SEIL.location = (p0 + p1) / 2; SEIL.scale = (1, 1, max(d.length, .01))
    SEIL.rotation_mode = "QUATERNION"; SEIL.rotation_quaternion = d.to_track_quat("Z", "Y")
    # Staubfahnen je nach Tempo
    for o in STAUB:
        o.scale = (1, 1, .4 + .6 * min(1, v / 80)); o.hide_render = t > 7.0
    # Windschlieren relativ zum Velo, laufen nach hinten
    for o in WIND:
        u = (o["ph"] + t * 2.4) % 1
        o.location = (xb + 3 - u * 9, o["y"], o["z"])
    bpy.context.view_layer.update()


def punkt(m, bone, v):
    pb = m.rig.pose.bones[bone]; bn = m.rig.data.bones[bone]
    return m.rig.matrix_world @ pb.matrix @ bn.matrix_local.inverted() @ Vector(v)


bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam
cam.data.clip_start = .03; cam.data.clip_end = 40000; cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
cam.data.dof.use_dof = True
# Einstellungen: (von, bis, bezug, pos0, pos1, ziel0, ziel1, linse, wind)
#  bezug "v" = relativ zum Velo-Ursprung (mitfahrend), "s" = fest am Boden relativ zur Velo-Position bei Einstellungsbeginn
SZ = [
    (0.00, 1.30, "v", (.9, -1.15, .32), (.6, -1.1, .34), (-.1, 0, .85), (-.1, 0, .85), 24, True),       # Aufhaenger (Zeitlupe)
    (1.30, 2.70, "v", (1.5, -2.7, 1.3), (1.4, -2.6, 1.25), (.2, 0, .85), (.2, 0, .85), 30, False),   # Helm/Gesicht seitlich
    (2.70, 4.00, "s", (14, -2.7, .14), (14, -2.7, .14), "V", "V", 22, False),                       # bodennah, Velo rauscht vorbei
    (4.00, 5.40, "v", (-14, -17, 9), (-6, -19, 8), (2.5, 0, .6), (3.5, 0, .6), 26, False),            # Drohne weit
    (5.40, 6.90, "s", (42, 6.0, .25), (60, 7.0, .25), "D", "D", 30, False),                         # tief auf der Kruste
    (6.90, 8.30, "v", (.15, -1.15, .26), (.05, -1.1, .27), (-.15, 0, .33), (-.17, 0, .33), 26, False),   # Riesen-Kettenblatt
    (8.30, 10.00, "v", (.95, -.9, .45), (.85, -.95, .5), (0, 0, .45), (0, 0, .45), 28, False),       # Beine treten
    (10.00, 11.70, "v", (2.5, -1.7, 1.05), (2.4, -1.8, 1.0), (.8, 0, .6), (.9, 0, .6), 26, False),   # Seil loesen
    (11.70, 13.00, "v", (.3, -4.6, 1.0), (.4, -4.4, 1.0), (.3, 0, .9), (.4, 0, .9), 24, False),      # seitlich: Luecke Kasten-Rad
    (13.00, 14.60, "v", (.2, -.4, 7.5), (.6, -.3, 7.0), (.6, 0, 0), (.7, 0, 0), 22, False),          # von oben
    (14.60, 16.90, "v", (-2.6, -.25, 1.25), (-2.3, -.2, 1.2), (1.5, 0, 1.0), (1.5, 0, 1.0), 22, True),  # von hinten, Windschlieren
    (16.90, 18.30, "v", (.25, -1.0, .12), (.0, -1.0, .12), (.3, 0, .5), (.1, 0, .5), 18, True),       # ganz tief am Rad
    (18.30, 20.60, "v", (6, -9, 1.2), (3, -9.5, 1.0), (0, 0, .7), (0, 0, .7), 65, False),            # Tele seitlich, Pfosten fliegen vorbei
    (20.60, 21.90, "v", (-1.7, -2.3, 1.9), (-1.4, -2.4, 1.8), (.2, 0, .7), (.2, 0, .7), 26, True),      # schraeg hinten oben
    (21.90, 23.60, "v", (1.7, -2.2, 1.15), (1.6, -2.3, 1.1), (.4, 0, .9), (.4, 0, .9), 38, False),  # Helm nah
    (23.60, 26.60, "v", (-12, -14, 4), (-30, -40, 22), (2, 0, .5), (6, 0, 0), 26, False),             # Drohne zieht weg
]


def zustand(t):
    for s in SZ:
        if s[0] <= t < s[1]:
            break
    k = (t - s[0]) / (s[1] - s[0]); k = ease(k) * .7 + k * .3
    ts = 19.6 + t * .35 if t < 1.3 else t           # Aufhaenger: Zeitlupe bei Hoechsttempo
    figuren(ts)
    xb = VELO.location.x
    if s[2] == "v":
        pos = Vector((xb, 0, 0)) + lerpv(s[3], s[4], k); ziel = Vector((xb, 0, 0)) + lerpv(s[5], s[6], k)
    else:
        xs = x_von(s[0]) - abstand(s[0]); pos = Vector((xs, 0, 0)) + Vector(s[3])
        ziel = Vector((xb + .2, 0, .7)) if s[5] == "V" else Vector((DR.location.x - 2, 0, .9))
    cam.location = pos; d = ziel - pos; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = s[7]; cam.data.dof.focus_distance = d.length; cam.data.dof.aperture_fstop = 2.8 if d.length < 3 else 8
    zitter = .002 + .004 * min(1, v_rad(ts) / 82) * (1 if s[2] == "v" else 0)
    cam.location += Vector((zitter * math.sin(t * 37), zitter * math.cos(t * 29), zitter * math.sin(t * 43)))
    for o in WIND:
        o.hide_render = not s[8]


os.makedirs(A.ordner, exist_ok=True)
N = int(round(D * A.fps))
liste = [int(round(float(x) * A.fps)) for x in A.nur.split(",")] if A.nur else list(range(A.start, N))
for f in liste:
    pfad = os.path.join(A.ordner, f"velo_{f:04d}.png")
    if os.path.exists(pfad) and not A.nur:
        continue
    sc.frame_set(f)
    zustand(f / A.fps); bpy.context.view_layer.update(); zustand(f / A.fps)
    sc.render.filepath = pfad
    bpy.ops.render.render(write_still=True); print("FERTIG", pfad, flush=True)
