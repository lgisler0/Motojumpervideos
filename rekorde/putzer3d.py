"""Geschichte: Ein Fensterputzer hat einen Job: die Fenster des Burj Khalifa putzen.
Basis: Stadt + Burj aus burj3d_v2.py (bis '# ---------------- Kamera'), dazu: detaillierte Fassade (Glas, Edelstahl-Lamellen),
Gondel (Korb) an Seilen, Fassadenbefahranlage (BMU), zwei realistische Arbeiter (MPFB), Abzieher + Schaum, weitere Gondeln.
python3 putzer3d.py <ordner> [--nur t1,t2] [--start i]"""
import os, sys, math
HIER = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HIER)
quelle = open(os.path.join(HIER, "burj3d_v2.py")).read().split("# ---------------- Kamera")[0]
_argv = sys.argv[:]
exec(quelle)
import bmesh
from mathutils import Vector, Matrix
import mensch_mh as MH

D = 29.6
sc.cycles.samples = A.samples
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"; sc.view_settings.exposure = -1.1
sc.cycles.max_bounces = 4; sc.cycles.glossy_bounces = 3; sc.cycles.transparent_max_bounces = 12

# ---------- Tageslicht statt Abend
sky.sun_elevation = math.radians(38); sky.sun_rotation = math.radians(215)
nt.nodes["Background"].inputs[1].default_value = .35
sonne.rotation_euler = (math.radians(52), 0, math.radians(215 - 90)); sonne.data.energy = 5.0; sonne.data.color = (1, .95, .88)
spitzlicht.hide_render = True
for m in fassaden + [burj_m]:
    for nd in m.node_tree.nodes:
        if nd.type == "MATH" and abs(nd.inputs[1].default_value - 2.5) < 1e-6:
            nd.inputs[1].default_value = .0
for o in eiffel_objs + [geist, k1, k2]:
    o.hide_render = True
for o in bpy.data.objects:
    if o.data is not None and hasattr(o.data, "materials") and len(o.data.materials) and o.data.materials[0] == beton:
        o.hide_render = True
# Burj-Glas am Tag: spiegelnd blau-silbern
bb = burj_m.node_tree.nodes["Principled BSDF"]
# Fassadenstruktur: vertikale Edelstahl-Lamellen + Geschossbaender (prozedural), dunkles Spiegelglas dazwischen
_n = burj_m.node_tree.nodes; _l = burj_m.node_tree.links
_tc = _n.new("ShaderNodeTexCoord"); _sp = _n.new("ShaderNodeSeparateXYZ"); _l.new(_tc.outputs["Object"], _sp.inputs[0])
_ang = _n.new("ShaderNodeMath"); _ang.operation = "ARCTAN2"; _l.new(_sp.outputs["Y"], _ang.inputs[0]); _l.new(_sp.outputs["X"], _ang.inputs[1])
_m1 = _n.new("ShaderNodeMath"); _m1.operation = "MULTIPLY"; _m1.inputs[1].default_value = 60; _l.new(_ang.outputs[0], _m1.inputs[0])
_f1 = _n.new("ShaderNodeMath"); _f1.operation = "FRACT"; _l.new(_m1.outputs[0], _f1.inputs[0])
_g1 = _n.new("ShaderNodeMath"); _g1.operation = "GREATER_THAN"; _g1.inputs[1].default_value = .8; _l.new(_f1.outputs[0], _g1.inputs[0])
_m2 = _n.new("ShaderNodeMath"); _m2.operation = "MULTIPLY"; _m2.inputs[1].default_value = 1 / 3.9; _l.new(_sp.outputs["Z"], _m2.inputs[0])
_f2 = _n.new("ShaderNodeMath"); _f2.operation = "FRACT"; _l.new(_m2.outputs[0], _f2.inputs[0])
_g2 = _n.new("ShaderNodeMath"); _g2.operation = "LESS_THAN"; _g2.inputs[1].default_value = .24; _l.new(_f2.outputs[0], _g2.inputs[0])
_mx = _n.new("ShaderNodeMath"); _mx.operation = "MAXIMUM"; _l.new(_g1.outputs[0], _mx.inputs[0]); _l.new(_g2.outputs[0], _mx.inputs[1])
_c = _n.new("ShaderNodeMix"); _c.data_type = "RGBA"; _c.inputs[6].default_value = (*hexf("4d6074"), 1); _c.inputs[7].default_value = (*hexf("c4c8cc"), 1)
_l.new(_mx.outputs[0], _c.inputs[0]); _l.new(_c.outputs[2], bb.inputs["Base Color"])
_r = _n.new("ShaderNodeMapRange"); _r.inputs["To Min"].default_value = .05; _r.inputs["To Max"].default_value = .3
_l.new(_mx.outputs[0], _r.inputs["Value"]); _l.new(_r.outputs["Result"], bb.inputs["Roughness"])
bb.inputs["Metallic"].default_value = .95
for o in bpy.data.objects:
    if o.type == "MESH" and len(o.data.materials) and o.data.materials[0] == burj_m:
        for md in o.modifiers:
            if md.type == "BEVEL":
                md.width = 1.2
# Stadt: Fensterbaender dunkel statt leuchtend
for m in fassaden:
    _n = m.node_tree.nodes; _l = m.node_tree.links; _b = _n["Principled BSDF"]
    _g = [x for x in _n if x.type == "MATH" and x.operation == "GREATER_THAN" and abs(x.inputs[1].default_value - .72) < 1e-6][0]
    _c = _n.new("ShaderNodeMix"); _c.data_type = "RGBA"; _c.inputs[6].default_value = _b.inputs["Base Color"].default_value[:]
    _c.inputs[7].default_value = (*hexf("1b2430"), 1); _l.new(_g.outputs[0], _c.inputs[0]); _l.new(_c.outputs[2], _b.inputs["Base Color"])
    _b.inputs["Roughness"].default_value = .25; _b.inputs["Metallic"].default_value = .5
# Boden: Strassenraster + Gruenflaechen, See (Dubai Fountain) am Fuss
_n = mb.node_tree.nodes; _l = mb.node_tree.links; _b = _n["Principled BSDF"]
_tc = _n.new("ShaderNodeTexCoord"); _sp = _n.new("ShaderNodeSeparateXYZ"); _l.new(_tc.outputs["Object"], _sp.inputs[0])
def _strasse(achse):
    m1 = _n.new("ShaderNodeMath"); m1.operation = "MULTIPLY"; m1.inputs[1].default_value = 1 / 140; _l.new(_sp.outputs[achse], m1.inputs[0])
    f1 = _n.new("ShaderNodeMath"); f1.operation = "FRACT"; _l.new(m1.outputs[0], f1.inputs[0])
    g1 = _n.new("ShaderNodeMath"); g1.operation = "LESS_THAN"; g1.inputs[1].default_value = .1; _l.new(f1.outputs[0], g1.inputs[0]); return g1
_sx, _sy = _strasse("X"), _strasse("Y")
_smx = _n.new("ShaderNodeMath"); _smx.operation = "MAXIMUM"; _l.new(_sx.outputs[0], _smx.inputs[0]); _l.new(_sy.outputs[0], _smx.inputs[1])
_alt = _b.inputs["Base Color"].links[0].from_socket
_gr = _n.new("ShaderNodeTexNoise"); _gr.inputs["Scale"].default_value = .02; _l.new(_tc.outputs["Object"], _gr.inputs["Vector"])
_gg = _n.new("ShaderNodeMath"); _gg.operation = "GREATER_THAN"; _gg.inputs[1].default_value = .62; _l.new(_gr.outputs["Fac"], _gg.inputs[0])
_c1 = _n.new("ShaderNodeMix"); _c1.data_type = "RGBA"; _l.new(_alt, _c1.inputs[6]); _c1.inputs[7].default_value = (*hexf("4f6a35"), 1); _l.new(_gg.outputs[0], _c1.inputs[0])
_c2 = _n.new("ShaderNodeMix"); _c2.data_type = "RGBA"; _l.new(_c1.outputs[2], _c2.inputs[6]); _c2.inputs[7].default_value = (*hexf("2c2c30"), 1); _l.new(_smx.outputs[0], _c2.inputs[0])
_l.new(_c2.outputs[2], _b.inputs["Base Color"])
see_m = mat("see", hexf("1d4a63"), .05, .2)
bpy.ops.mesh.primitive_cylinder_add(radius=1, depth=.5, vertices=64, location=(80, -260, .3)); _see = bpy.context.object; _see.scale = (260, 120, 1); _see.data.materials.append(see_m)

# ---------- Fluegel k=0 nachrechnen: Segment bei ~z=500 (Seite x=+breite/2)
hoehe, laenge, seg = 0, 52, 0
SEG = []
while laenge > 8:
    h = 46 + 4 * seg; SEG.append((hoehe, hoehe + h, laenge, 19 - seg * .6)); hoehe += h; seg += 1
    laenge -= 3.3 + (0 if seg % 3 == 0 else 0)
z0s, z1s, LG, BR = [s for s in SEG if s[0] <= 500 < s[1]][0]
FX = BR / 2 + .02  # Fassadenebene
print("Segment", z0s, z1s, LG, BR, flush=True)

# ---------- detaillierte Fassade: Glasfelder, Bruestungen, Edelstahl-Lamellen
glas = bpy.data.materials.new("glas_fass"); glas.use_nodes = True; n = glas.node_tree.nodes; l = glas.node_tree.links; b = n["Principled BSDF"]
b.inputs["Base Color"].default_value = (*hexf("3f5468"), 1); b.inputs["Metallic"].default_value = .75; b.inputs["Roughness"].default_value = .06
nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 3; nz.inputs["Detail"].default_value = 4
tc = n.new("ShaderNodeTexCoord"); l.new(tc.outputs["Object"], nz.inputs["Vector"])
mr = n.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = .04; mr.inputs["To Max"].default_value = .14
l.new(nz.outputs["Fac"], mr.inputs["Value"]); l.new(mr.outputs["Result"], b.inputs["Roughness"])
stahl = mat("edelstahl", hexf("c9cdd2"), .28, 1)
bruest = mat("bruestung", hexf("c4c8cc"), .3, .9)
GESCH = 3.9; FELD = 1.37
FASS = []
zf0, zf1 = z0s + 2, min(z1s - 2, z0s + 60)
yf0, yf1 = 5.5, LG - 3.0
ncol = int((yf1 - yf0) / FELD); nrow = int((zf1 - zf0) / GESCH)
bm_g = bmesh.new(); bm_b = bmesh.new(); bm_s = bmesh.new()


def quader(bm, x0, x1, y0, y1, z0, z1):
    vs = [bm.verts.new((x, y, z)) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
        bm.faces.new([vs[i] for i in f])


for r in range(nrow):
    z = zf0 + r * GESCH
    quader(bm_b, FX - .05, FX + .02, yf0, yf0 + ncol * FELD, z, z + .95)               # Bruestung
    for c in range(ncol):
        y = yf0 + c * FELD
        quader(bm_g, FX - .02, FX, y + .04, y + FELD - .04, z + .95, z + GESCH)         # Glasfeld
for c in range(ncol + 1):
    y = yf0 + c * FELD
    quader(bm_s, FX, FX + .32, y - .05, y + .05, zf0, zf0 + nrow * GESCH)               # vertikale Lamelle
for bmx, mt, nm in ((bm_g, glas, "glasfelder"), (bm_b, bruest, "bruestungen"), (bm_s, stahl, "lamellen")):
    me = bpy.data.meshes.new(nm); bmx.to_mesh(me); bmx.free()
    o = bpy.data.objects.new(nm, me); sc.collection.objects.link(o); me.materials.append(mt); FASS.append(o)
    if nm == "lamellen":
        bv = o.modifiers.new("b", "BEVEL"); bv.width = .02; bv.segments = 2

# ---------- Gondel (Korb) mit zwei Arbeitern, Seile, Fassadenbefahranlage
KORB_Y = yf0 + ncol * FELD / 2
GX = FX + .32 + .25 + .55   # Korbmitte (x)
gelbgrau = mat("bmu", hexf("d9dcd8"), .4, .6)
korb_m = mat("korb", hexf("b9bec4"), .35, .85)
rot_m = mat("rot", hexf("c22a1f"), .5)
korb = bpy.data.objects.new("korb", None); sc.collection.objects.link(korb)


def kbox(x0, x1, y0, y1, z0, z1, m, bev=.01):
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)); o = bpy.context.object
    o.scale = (x1 - x0, y1 - y0, z1 - z0); o.data.materials.append(m); o.parent = korb
    if bev:
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        b_ = o.modifiers.new("b", "BEVEL"); b_.width = bev; b_.segments = 2
    return o


def krohr(p0, p1, r, m, v=12):
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d.length, vertices=v, location=(p0 + p1) / 2)
    o = bpy.context.object; o.rotation_euler = d.to_track_quat("Z", "Y").to_euler(); o.data.materials.append(m); o.parent = korb
    for p in o.data.polygons:
        p.use_smooth = True
    return o


KL, KB = 4.6, 1.0   # Korb Laenge (y), Breite (x)
kbox(-KB / 2, KB / 2, -KL / 2, KL / 2, -.05, 0, korb_m)                       # Boden (Gitterrost)
gitter = mat("gitter", hexf("6f757b"), .5, .8)
for i in range(46):
    y = -KL / 2 + .05 + i * .1
    kbox(-KB / 2 + .02, KB / 2 - .02, y, y + .02, -.06, .005, gitter, 0)
kbox(-KB / 2, KB / 2, -KL / 2, KL / 2, -.25, -.05, korb_m)                     # Bodenrahmen
for y in (-KL / 2, -KL / 6, KL / 6, KL / 2):
    for x in (-KB / 2, KB / 2):
        krohr((x, y, 0), (x, y, 1.12), .03, korb_m)                           # Pfosten
for z in (.55, 1.12):
    for x in (-KB / 2, KB / 2):
        krohr((x, -KL / 2, z), (x, KL / 2, z), .028, korb_m)                  # Handlauf
    for y in (-KL / 2, KL / 2):
        krohr((-KB / 2, y, z), (KB / 2, y, z), .028, korb_m)
kbox(-KB / 2, KB / 2, -KL / 2, KL / 2, 0, .15, korb_m)                          # Fussleiste
kbox(KB / 2 - .02, KB / 2 + .02, -.9, .9, .2, .5, rot_m)                         # Steuerkasten aussen
for y in (-KL / 2 + .3, KL / 2 - .3):
    kbox(-.15, .15, y - .15, y + .15, 1.12, 1.45, gelbgrau)                     # Seilwinden
    for s in (-1, 1):                                                           # Abstandsrollen zur Fassade
        bpy.ops.mesh.primitive_cylinder_add(radius=.09, depth=.08, vertices=24, location=(-KB / 2 - .2, y, .6 + s * .3), rotation=(P / 2, 0, 0))
        o = bpy.context.object; o.parent = korb; o.data.materials.append(gitter)
        krohr((-KB / 2, y, .6 + s * .3), (-KB / 2 - .2, y, .6 + s * .3), .025, korb_m)
eimer_m = mat("eimer", hexf("2f6fb3"), .4)
bpy.ops.mesh.primitive_cone_add(radius1=.14, radius2=.17, depth=.32, vertices=32, location=(.25, 1.3, .16)); o = bpy.context.object
o.parent = korb; o.data.materials.append(eimer_m)
schaum_m = mat("schaum", hexf("f4f6f6"), .6)
bpy.ops.mesh.primitive_cylinder_add(radius=.15, depth=.02, vertices=32, location=(.25, 1.3, .3)); o = bpy.context.object; o.parent = korb; o.data.materials.append(schaum_m)
SEILE = []
seil_m = mat("seil", hexf("3a3c3e"), .5, .7)
for y in (-KL / 2 + .3, KL / 2 - .3):
    bpy.ops.mesh.primitive_cylinder_add(radius=.012, depth=1, vertices=8); s_ = bpy.context.object; s_.data.materials.append(seil_m); SEILE.append((s_, y))
# BMU auf dem naechsten Ruecksprung (oben)
BMU_Z = z1s + .2
bmu = bpy.data.objects.new("bmu", None); sc.collection.objects.link(bmu); bmu.location = (FX - 4.0, KORB_Y, BMU_Z)
def bbox(x0, x1, y0, y1, z0, z1, m):
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)); o = bpy.context.object
    o.scale = (x1 - x0, y1 - y0, z1 - z0); o.data.materials.append(m); o.parent = bmu
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    b_ = o.modifiers.new("b", "BEVEL"); b_.width = .03; b_.segments = 2
    return o
bbox(-2.2, 2.2, -1.6, 1.6, 0, 2.4, gelbgrau)                                   # Maschinenhaus
bbox(-1.8, 1.8, -1.2, 1.2, 2.4, 3.0, gelbgrau)
for x in (-1.8, 1.8):
    for y in (-1.3, 1.3):
        bpy.ops.mesh.primitive_cylinder_add(radius=.25, depth=.2, vertices=24, location=(x, y, .05), rotation=(P / 2, 0, 0)); o = bpy.context.object; o.parent = bmu; o.data.materials.append(gitter)
# Ausleger (Fachwerk) bis ueber die Fassade
AUS = (FX + .9 + 1.3) - (FX - 4.0)
for y in (-.35, .35):
    for z in (2.6, 3.3):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(1.0 + AUS / 2 - .5, y, z)); o = bpy.context.object; o.scale = (AUS + 1, .1, .1); o.parent = bmu; o.data.materials.append(gelbgrau)
for i in range(int(AUS) + 2):
    x = 1.0 + i - .5
    for y in (-.35, .35):
        bpy.ops.mesh.primitive_cylinder_add(radius=.03, depth=.75, vertices=8, location=(x, y, 2.95), rotation=(0, .6 if i % 2 else -.6, 0)); o = bpy.context.object; o.parent = bmu; o.data.materials.append(gelbgrau)
bpy.ops.mesh.primitive_cube_add(size=1, location=(AUS + .3, 0, 2.9)); o = bpy.context.object; o.scale = (.6, KL, .4); o.parent = bmu; o.data.materials.append(gelbgrau)   # Querbalken fuer beide Seile
warn = mat("warnlicht", hexf("ff8a00"), .3, 0, 8)
bpy.ops.mesh.primitive_uv_sphere_add(radius=.12, location=(AUS + .3, 0, 3.2)); o = bpy.context.object; o.parent = bmu; o.data.materials.append(warn)

# Weitere Gondeln (einfach) auf anderen Fluegeln fuer die Totale
ANDERE = []
for k, (ang, zz) in enumerate(((P / 2 + 2 * P / 3, 300), (P / 2 + 4 * P / 3, 420), (P / 2, 210), (P / 2 + 2 * P / 3, 560), (P / 2 + 4 * P / 3, 150),
                               (P / 2, 380), (P / 2 + 2 * P / 3, 120), (P / 2 + 4 * P / 3, 610), (P / 2, 640), (P / 2 + 2 * P / 3, 460), (P / 2 + 4 * P / 3, 260))):
    s_ = [s for s in SEG if s[0] <= zz < s[1]]
    if not s_:
        continue
    _, _, lg, br = s_[0]; d_ = lg * .55; sd = 1 if k % 2 else -1
    pos = Vector((math.cos(ang) * d_, math.sin(ang) * d_, zz)) + Vector((-math.sin(ang), math.cos(ang), 0)) * sd * (br / 2 + .6)
    bpy.ops.mesh.primitive_cube_add(size=1, location=pos); o = bpy.context.object; o.scale = (4.6, 1.0, 1.1); o.rotation_euler[2] = ang
    o.data.materials.append(korb_m); ANDERE.append((o, pos.copy()))

# ---------- Arbeiter
A1 = MH.Arbeiter("putzer1", seed=3, alter=.45, haut="caucasian")
A2 = MH.Arbeiter("putzer2", seed=7, alter=.6, haut="asian", muskel=.5)
for a_, yy in ((A1, -.7), (A2, 1.0)):
    a_.rig.parent = korb; a_.rig.location = (.05, yy, 0); a_.rig.rotation_euler = (0, 0, -P / 2)
# Abzieher (Stiel + Gummilippe) in der rechten Hand von A1, Wischer in der Hand von A2
abz = bpy.data.objects.new("abzieher", None); sc.collection.objects.link(abz)
gummi = mat("gummi", hexf("161616"), .7)
gr_m = mat("griff", hexf("e8b000"), .4)
for (p0, p1, r_, m_) in (((0, 0, 0), (0, 0, .5), .016, korb_m), ((0, -.24, .5), (0, .24, .5), .018, gr_m), ((0, -.25, .52), (0, .25, .52), .008, gummi)):
    p0, p1 = Vector(p0), Vector(p1); d_ = p1 - p0
    bpy.ops.mesh.primitive_cylinder_add(radius=r_, depth=d_.length, vertices=12, location=(p0 + p1) / 2)
    o = bpy.context.object; o.rotation_euler = d_.to_track_quat("Z", "Y").to_euler(); o.parent = abz; o.data.materials.append(m_)
bn = A1.rig.data.bones["wrist.R"]
abz.parent = A1.rig; abz.parent_type = "BONE"; abz.parent_bone = "wrist.R"
abz.location = (0, -bn.length + .06, 0); abz.rotation_euler = (-P / 2, 0, 0)
# Schaum auf dem Glas vor A1 (wird von oben nach unten abgezogen)
schaum = bpy.data.materials.new("schaumglas"); schaum.use_nodes = True; n = schaum.node_tree.nodes; l = schaum.node_tree.links; b = n["Principled BSDF"]
b.inputs["Base Color"].default_value = (.95, .97, .98, 1); b.inputs["Roughness"].default_value = .4; b.inputs["Transmission Weight"].default_value = .3
tc = n.new("ShaderNodeTexCoord"); vo = n.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 60; l.new(tc.outputs["Object"], vo.inputs["Vector"])
nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 8; nz.inputs["Detail"].default_value = 8; l.new(tc.outputs["Object"], nz.inputs["Vector"])
sp = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Object"], sp.inputs[0])
SCHAUM_GRENZE = n.new("ShaderNodeValue"); SCHAUM_GRENZE.outputs[0].default_value = 2.0
lt = n.new("ShaderNodeMath"); lt.operation = "LESS_THAN"; l.new(sp.outputs["Z"], lt.inputs[0]); l.new(SCHAUM_GRENZE.outputs[0], lt.inputs[1])
gt = n.new("ShaderNodeMath"); gt.operation = "GREATER_THAN"; gt.inputs[1].default_value = .55; l.new(nz.outputs["Fac"], gt.inputs[0])
mm = n.new("ShaderNodeMath"); mm.operation = "MULTIPLY"; l.new(lt.outputs[0], mm.inputs[0]); l.new(gt.outputs[0], mm.inputs[1])
l.new(mm.outputs[0], b.inputs["Alpha"])
bp = n.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = .6; l.new(vo.outputs["Distance"], bp.inputs["Height"]); l.new(bp.outputs[0], b.inputs["Normal"])
bpy.ops.mesh.primitive_plane_add(size=1); sch = bpy.context.object; sch.scale = (1.8, 1.25, 1); sch.rotation_euler = (0, P / 2, 0)
sch.data.materials.append(schaum); sch.visible_shadow = False

# ======================================================================  Ablauf
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam; cam.data.lens = 30; cam.data.clip_end = 30000; cam.data.sensor_fit = "VERTICAL"
cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = 4
bpy.ops.object.light_add(type="AREA"); fill = bpy.context.object; fill.data.size = 1.5; fill.data.energy = 150; fill.data.color = (1, .93, .85)
fill.parent = cam; fill.location = (.6, .4, .3)


def ease(x):
    x = min(1, max(0, x)); return x * x * (3 - 2 * x)


def lerpv(a, b, k):
    return Vector(a).lerp(Vector(b), k)


KZ_OBEN = 520.0


def korb_z(t):
    """Korbhoehe: oben arbeiten, in der Totale/Schluss abwaerts, am Ende wieder oben"""
    if t < 20.5:
        return KZ_OBEN - .12 * t
    if t < 26.4:
        return KZ_OBEN - 2.5 - 470 * ease((t - 20.5) / 5.9)   # Zeitraffer abwaerts
    return KZ_OBEN


def L(p):  # Korb-lokale Koordinate -> Welt
    return korb.matrix_world @ Vector(p)


# Szenen: (start, ende, pos_a, ziel_a, pos_b, ziel_b, modus)  modus k=korb-lokal, w=welt
S1 = ((2.5, -1.5, 1.45), (.05, -.75, 1.6), (2.2, -1.3, 1.5), (.05, -.75, 1.6))
SZ = [
    (0.0, 2.0, *S1, "k"),
    (2.0, 4.6, (60, -40, 30), (-2, 0, 5), (420, -620, 160), (0, 0, -80), "k"),
    (4.6, 7.9, (90, -120, -505), (0, 0, -250), (70, -95, -505), (0, 0, -100), "k"),
    (7.9, 10.8, (2.2, -5.5, 3.2), (-1.2, 2.5, 1.5), (2.0, 1.5, 2.8), (-1.2, 6, 1.0), "k"),
    (10.8, 13.0, (.8, .2, .4), (-1.6, 0, 40), (.7, .4, .5), (-1.8, 0, 40), "k"),
    (13.0, 15.45, (62, -14, 19), (-3, 0, 20), (56, -10, 21), (-3, 0, 20), "k"),
    (15.45, 18.1, (-.2, -1.9, 1.5), (-.55, -.7, 1.8), (-.2, -1.7, 1.4), (-.55, -.7, 1.4), "k"),
    (18.1, 20.5, (.9, -1.6, 1.4), (6, -1.2, -300), (.9, -1.6, 1.3), (5, -1.2, -300), "k"),
    (20.5, 24.5, (900, -1300, 330), (0, 0, 380), (860, -1250, 300), (0, 0, 330), "w"),
    (24.5, 26.4, (14, -10, 3), (0, 0, 1), (12, -8, 2.5), (0, 0, 1.5), "k"),
    (26.4, 28.6, (40, -30, -480), (0, 0, -400), S1[0], S1[1], "k"),
    (28.6, D + .01, S1[0], S1[1], S1[2], S1[3], "k"),
]


def posen(t):
    for a_ in (A1, A2):
        a_.zuruecksetzen()
    # A1 wischt mit dem Abzieher (rechter Arm hoch, Auf/Ab-Bewegung)
    w = math.sin(t * 2.2)
    A1.dreh("upperarm01.L", z=-.72)
    A1.dreh("upperarm01.R", x=1.35 + .35 * w, z=.25)
    A1.dreh("lowerarm01.R", x=-.5 - .2 * w)
    A1.dreh("spine03", x=.06 + .04 * w); A1.dreh("neck01", x=-.15 - .1 * w)
    # A2 haelt sich am Gelaender, schaut nach unten / zum Kollegen
    A2.dreh("upperarm01.L", x=.5, z=-.55); A2.dreh("lowerarm01.L", x=-.6)
    A2.dreh("upperarm01.R", z=.72)
    A2.dreh("neck01", x=.25 + .1 * math.sin(t * .7), z=.2 * math.sin(t * .4))
    hook = 0 <= t < 2.0 or t >= 28.6
    A1.rig.rotation_euler = (0, 0, P / 2 if hook else -P / 2)
    if hook:   # Hook: A1 schaut ueber die Stadt, Abzieher locker in der Hand
        A1.dreh("upperarm01.R", z=.72, x=.15); A1.dreh("lowerarm01.R", x=-.9); A1.dreh("neck01", x=.12, z=.15 * math.sin(t))
        A1.dreh("spine03", x=0)
    # Schaum: Abzieher-Hoehe ~ Grenze (lokale Schaum-Koordinaten -1.2..1.2 entlang z)
    SCHAUM_GRENZE.outputs[0].default_value = .5 * (1 + math.cos(min(t, 20) * .45)) * .9 - .1


def zustand(t):
    zk = korb_z(t); _s = [s_ for s_ in SEG if s_[0] <= zk < s_[1]] or [SEG[0]]
    gx = _s[0][3] / 2 + .02 + .32 + .25 + .55
    korb.location = (gx, KORB_Y if zk > 300 else min(KORB_Y, _s[0][2] - 3), zk); korb.rotation_euler = (0, .01 * math.sin(t * .9), 0)
    for s_, y in SEILE:
        oben = Vector((FX + .9 + 1.0, KORB_Y + y, BMU_Z + 2.9)); unten = L((0, y, 1.45))
        d_ = oben - unten; s_.location = (oben + unten) / 2; s_.scale = (1, 1, d_.length); s_.rotation_euler = d_.to_track_quat("Z", "Y").to_euler()
    sch.location = (FX + .33 + .01, KORB_Y - .7, korb_z(t) + 1.9)
    sch.hide_render = True
    posen(t)
    # Totale: andere Gondeln fahren im Zeitraffer
    for i, (o, p0) in enumerate(ANDERE):
        o.location = p0 - Vector((0, 0, 40 * ease((t - 20.5) / 4) * (1 if i % 2 else .6))) if t >= 20.5 else p0
    # Zeitraffer-Sonne in der Totale
    if 20.5 <= t < 24.5:
        k = (t - 20.5) / 4.0; sky.sun_elevation = math.radians(38 - 30 * k); sky.sun_rotation = math.radians(215 + 40 * k)
        sonne.rotation_euler = (math.radians(90 - (38 - 30 * k)), 0, math.radians(215 + 40 * k - 90))
    else:
        sky.sun_elevation = math.radians(38); sky.sun_rotation = math.radians(215); sonne.rotation_euler = (math.radians(52), 0, math.radians(125))
    for s in SZ:
        if s[0] <= t < s[1]:
            k = ease((t - s[0]) / (s[1] - s[0])) * .85 + (t - s[0]) / (s[1] - s[0]) * .15
            pa, za = lerpv(s[2], s[4], k), lerpv(s[3], s[5], k); mod = s[6]; break
    if mod == "k":
        pos, ziel = L(pa), L(za)
    else:
        pos, ziel = pa, za
    wk = .02 if mod == "k" else 0
    pos = pos + Vector((0, wk * math.sin(t * 7.3), wk * math.sin(t * 5.1)))
    cam.location = pos; d = ziel - pos; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.dof.focus_distance = min(d.length, 2000)
    nah = (0 <= t < 2.0) or (7.9 <= t < 10.8) or (15.45 <= t < 18.1) or t >= 28.6
    cam.data.dof.aperture_fstop = 2.8 if nah else 11
    fill.hide_render = not nah
    cam.data.lens = 35 if nah else (22 if 18.1 <= t < 20.5 or 10.8 <= t < 13.0 else 30)


os.makedirs(A.ordner, exist_ok=True)
N = int(round(D * A.fps))
liste = [int(round(float(x) * A.fps)) for x in A.nur.split(",")] if A.nur else list(range(A.start, N))
for f in liste:
    pfad = os.path.join(A.ordner, f"putzer_{f:04d}.png")
    if os.path.exists(pfad) and not A.nur:
        continue
    bpy.context.view_layer.update()
    zustand(f / A.fps); bpy.context.view_layer.update()
    zustand(f / A.fps)
    sc.render.filepath = pfad
    bpy.ops.render.render(write_still=True); print("FERTIG", pfad, flush=True)
