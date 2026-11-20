"""Geschichte: Ein Tankwart am Flughafen hat einen Job: einen Airbus A380 betanken.
Basis: A380-Modell + Flughafen aus a380_3d.py (bis 'Kamera + Ablauf'), dazu: Vorfeld (Beton mit Fugen, Markierungen),
Fluggastbruecke, Hydranten-Tankwagen mit Hebebuehne, Schlaeuche, realistischer Arbeiter (MPFB), Roentgen-Tank im Fluegel,
6400 Autos (Array), Zeitraffer, Start auf der Piste. python3 tanker3d.py <ordner> [--nur t1,t2] [--start i]"""
import os, sys, math
HIER = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HIER)
quelle = open(os.path.join(HIER, "a380_3d.py")).read().split("# ======================================================================  Kamera + Ablauf")[0]
exec(quelle)
from mathutils import Vector, Matrix
import mensch_mh as MH

D = 28.4
sc.cycles.samples = A.samples
sc.view_settings.exposure = -1.5; sc.view_settings.look = "AgX - Punchy"
wolken.hide_render = True; meer.hide_render = True
# Mittagslicht
sky.sun_elevation = math.radians(40); sky.sun_rotation = math.radians(150)
sonne.rotation_euler = (math.radians(50), 0, math.radians(150 - 90)); sonne.data.energy = 4.8; sonne.data.color = (1, .96, .9)

# Flugzeug an der Position (Bug zum Terminal +y)
GATE = Vector((0, 330, 6.0))
flug.location = GATE; flug.rotation_euler = (0, 0, -P / 2)

# ---------- Vorfeld: Betonplatten mit Fugen, gelbe Fuehrungslinie, Flecken
vf = bpy.data.materials.new("vorfeld"); vf.use_nodes = True; n = vf.node_tree.nodes; l = vf.node_tree.links; b = n["Principled BSDF"]
tc = n.new("ShaderNodeTexCoord"); sp = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Object"], sp.inputs[0])
def fuge(achse, abstand):
    m1 = n.new("ShaderNodeMath"); m1.operation = "MULTIPLY"; m1.inputs[1].default_value = 1 / abstand; l.new(sp.outputs[achse], m1.inputs[0])
    f1 = n.new("ShaderNodeMath"); f1.operation = "FRACT"; l.new(m1.outputs[0], f1.inputs[0])
    g1 = n.new("ShaderNodeMath"); g1.operation = "LESS_THAN"; g1.inputs[1].default_value = .004 * 6 / abstand * 2; l.new(f1.outputs[0], g1.inputs[0]); return g1
fx_, fy_ = fuge("X", 6), fuge("Y", 6)
fm = n.new("ShaderNodeMath"); fm.operation = "MAXIMUM"; l.new(fx_.outputs[0], fm.inputs[0]); l.new(fy_.outputs[0], fm.inputs[1])
nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = .15; nz.inputs["Detail"].default_value = 12; l.new(tc.outputs["Object"], nz.inputs["Vector"])
cr = n.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (*hexf("8c8a84"), 1); cr.color_ramp.elements[1].color = (*hexf("b9b6ae"), 1)
l.new(nz.outputs["Fac"], cr.inputs["Fac"])
fl = n.new("ShaderNodeTexNoise"); fl.inputs["Scale"].default_value = .4; fl.inputs["Detail"].default_value = 6; l.new(tc.outputs["Object"], fl.inputs["Vector"])
fg = n.new("ShaderNodeMath"); fg.operation = "GREATER_THAN"; fg.inputs[1].default_value = .64; l.new(fl.outputs["Fac"], fg.inputs[0])
c1 = n.new("ShaderNodeMix"); c1.data_type = "RGBA"; l.new(cr.outputs[0], c1.inputs[6]); c1.inputs[7].default_value = (*hexf("5f5b54"), 1); l.new(fg.outputs[0], c1.inputs[0])
c2 = n.new("ShaderNodeMix"); c2.data_type = "RGBA"; l.new(c1.outputs[2], c2.inputs[6]); c2.inputs[7].default_value = (*hexf("3c3a36"), 1); l.new(fm.outputs[0], c2.inputs[0])
# gelbe Fuehrungslinie (x ~ 0)
ab_ = n.new("ShaderNodeMath"); ab_.operation = "ABSOLUTE"; l.new(sp.outputs["X"], ab_.inputs[0])
gl_ = n.new("ShaderNodeMath"); gl_.operation = "LESS_THAN"; gl_.inputs[1].default_value = .15; l.new(ab_.outputs[0], gl_.inputs[0])
c3 = n.new("ShaderNodeMix"); c3.data_type = "RGBA"; l.new(c2.outputs[2], c3.inputs[6]); c3.inputs[7].default_value = (*hexf("e8b10c"), 1); l.new(gl_.outputs[0], c3.inputs[0])
l.new(c3.outputs[2], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = .85
bp = n.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = .25; l.new(nz.outputs["Fac"], bp.inputs["Height"]); l.new(bp.outputs[0], b.inputs["Normal"])
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 260, .02)); vorfeld = bpy.context.object; vorfeld.scale = (700, 260, 1); bpy.ops.object.transform_apply(scale=True); vorfeld.data.materials.append(vf)
# Rollweg zur Piste
bpy.ops.mesh.primitive_plane_add(size=1, location=(-200, 75, .025)); o = bpy.context.object; o.scale = (40, 150, 1); o.data.materials.append(pm)
# Terminalfront mit Glas direkt am Gate + Fluggastbruecke
term_glas = mat("termglas", hexf("4a5a6b"), .08, .8)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 395, 11)); o = bpy.context.object; o.scale = (420, 30, 22); o.data.materials.append(term_glas)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 395, 22.5)); o = bpy.context.object; o.scale = (424, 34, 1.5); o.data.materials.append(term)
bruecke_m = mat("bruecke", hexf("c9ced4"), .35, .4)
for zz, yy, ll in ((8.5, 360, 34), (5.5, 362, 30)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-14 if zz > 7 else 14, yy, zz)); o = bpy.context.object; o.scale = (3.4, ll, 3.0)
    o.rotation_euler = (0, 0, .25 if zz > 7 else -.2); o.data.materials.append(bruecke_m)
    bpy.ops.mesh.primitive_cylinder_add(radius=.35, depth=zz - 1.5, location=(-14 if zz > 7 else 14, yy - ll / 2 + 3, (zz - 1.5) / 2)); o2 = bpy.context.object; o2.data.materials.append(grau)

# ---------- Hydranten-Tankwagen (Hebebuehne, Schlauchtrommel, Anzeige)
TW = bpy.data.objects.new("tankwagen", None); sc.collection.objects.link(TW)
weiss_lack = mat("tw_weiss", hexf("eceeed"), .35, .1)
gelb_lack = mat("tw_gelb", hexf("f2b800"), .35)
dunkel_m = mat("tw_dunkel", hexf("1d1f22"), .5, .4)
reifen_m = mat("tw_reifen", hexf("141414"), .85)
alu = mat("tw_alu", hexf("c8cdd2"), .3, 1)
scheibe = mat("tw_scheibe", hexf("1a2633"), .05, .5)
licht_o = mat("tw_orange", hexf("ff8a00"), .3, 0, 6)


def tbox(x0, x1, y0, y1, z0, z1, m, bev=.04, eltern=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)); o = bpy.context.object
    o.scale = (x1 - x0, y1 - y0, z1 - z0); o.data.materials.append(m); o.parent = eltern or TW
    if bev:
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        b_ = o.modifiers.new("b", "BEVEL"); b_.width = bev; b_.segments = 3
    return o


def trohr(p0, p1, r, m, v=16, eltern=None):
    p0, p1 = Vector(p0), Vector(p1); d_ = p1 - p0
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d_.length, vertices=v, location=(p0 + p1) / 2)
    o = bpy.context.object; o.rotation_euler = d_.to_track_quat("Z", "Y").to_euler(); o.data.materials.append(m); o.parent = eltern or TW
    for p in o.data.polygons:
        p.use_smooth = True
    return o


# Fahrzeug faehrt in -x Richtung (Fahrerhaus vorne bei x=0), Laenge 8 m, Breite 2.5 m
tbox(0, 2.2, -1.25, 1.25, .55, 2.75, weiss_lack, .12)                         # Fahrerhaus
tbox(-.02, .3, -1.1, 1.1, 1.55, 2.6, scheibe, .05)                            # Frontscheibe
for s in (-1, 1):
    tbox(.5, 1.9, s * 1.26 - .02, s * 1.26 + .02, 1.6, 2.5, scheibe, .02)    # Seitenscheiben
    tbox(-.05, .1, s * .85 - .2, s * .85 + .2, .8, 1.05, mat("tw_licht", hexf("fffbe8"), .2, 0, 4), .02)
tbox(-.1, .2, -1.2, 1.2, .35, .65, dunkel_m, .05)                             # Stossfaenger
tbox(.1, 8.0, -1.0, 1.0, .5, .85, dunkel_m, .03)                              # Rahmen
tbox(2.3, 7.9, -1.25, 1.25, .85, 1.9, weiss_lack, .08)                        # Aufbau (Filter, Pumpe)
for i in range(6):
    tbox(2.6 + i * .85, 3.2 + i * .85, 1.26, 1.29, 1.0, 1.75, alu, .01)       # Klappen
tbox(2.4, 7.8, -1.26, -1.23, 1.85, 1.9, gelb_lack, 0)
for x in (1.3, 5.6, 6.9):
    for s in (-1, 1):
        bpy.ops.mesh.primitive_cylinder_add(radius=.5, depth=.32, vertices=32, location=(x, s * 1.05, .5), rotation=(P / 2, 0, 0))
        o = bpy.context.object; o.parent = TW; o.data.materials.append(reifen_m)
        bpy.ops.mesh.primitive_cylinder_add(radius=.3, depth=.34, vertices=24, location=(x, s * 1.05, .5), rotation=(P / 2, 0, 0))
        o = bpy.context.object; o.parent = TW; o.data.materials.append(alu)
tbox(.9, 1.3, -.2, .2, 2.75, 2.9, licht_o, .03)                                # Rundumleuchte
# Schlauchtrommel hinten
bpy.ops.mesh.primitive_cylinder_add(radius=.55, depth=1.6, vertices=32, location=(7.3, 0, 2.45), rotation=(P / 2, 0, 0)); o = bpy.context.object; o.parent = TW; o.data.materials.append(dunkel_m)
bpy.ops.mesh.primitive_torus_add(major_radius=.55, minor_radius=.07, location=(7.3, 0, 2.45), rotation=(P / 2, 0, 0)); o = bpy.context.object; o.parent = TW; o.data.materials.append(dunkel_m)
# Bedienfeld mit Zaehler (leuchtende Anzeige)
anz_m = mat("anzeige", hexf("62ff8a"), .3, 0, 3)
tbox(4.0, 5.2, -1.3, -1.26, 1.2, 1.75, dunkel_m, .01)
tbox(4.15, 5.05, -1.31, -1.29, 1.45, 1.65, anz_m, 0)
# Hebebuehne (Scheren + Plattform mit Gelaender)
BUEHNE = bpy.data.objects.new("buehne", None); sc.collection.objects.link(BUEHNE); BUEHNE.parent = TW; BUEHNE.location = (4.6, 0, 1.9)
tbox(-1.3, 1.3, -1.05, 1.05, 0, .12, alu, .02, BUEHNE)
for x0, x1 in ((-1.3, 1.3),):
    for y in (-1.05, 1.05):
        trohr((x0, y, .12), (x1, y, .12), .03, gelb_lack, 10, BUEHNE); trohr((x0, y, 1.1), (x1, y, 1.1), .03, gelb_lack, 10, BUEHNE)
    for x in (x0, 0, x1):
        for y in (-1.05, 1.05):
            trohr((x, y, .12), (x, y, 1.1), .025, gelb_lack, 10, BUEHNE)
SCHERE = []
for i in range(4):
    a_ = trohr((-1, -.9, 0), (1, -.9, 1), .05, gelb_lack, 10); b2_ = trohr((-1, .9, 0), (1, .9, 1), .05, gelb_lack, 10)
    SCHERE.append((a_, b2_))
# Schlauch Hydrant -> Wagen und Wagen -> Fluegel (Kurven)
schl_m = mat("schlauch", hexf("1a1a1a"), .6)
def kurve(name, r=.06):
    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = r; cu.bevel_resolution = 4
    sp_ = cu.splines.new("BEZIER"); sp_.bezier_points.add(3)
    ob = bpy.data.objects.new(name, cu); sc.collection.objects.link(ob); cu.materials.append(schl_m); return ob, sp_
SCHL_H, SPH = kurve("schlauch_hydrant", .07)
SCHL_F, SPF = kurve("schlauch_fluegel", .055)
# Hydrantengrube im Boden
bpy.ops.mesh.primitive_cylinder_add(radius=.45, depth=.06, vertices=32); grube = bpy.context.object; grube.data.materials.append(dunkel_m)
# Kupplung (Tankstutzen) unter dem Fluegel: Fluegel links (y lokal +9), x lokal 34
KUP_L = Vector((40.0, 20.0, -1.3))
bpy.ops.mesh.primitive_cylinder_add(radius=.18, depth=.25, vertices=24); kup = bpy.context.object; kup.data.materials.append(gelb_lack); kup.parent = flug; kup.location = KUP_L - Vector((0, 0, .1))
bpy.ops.mesh.primitive_cube_add(size=1); kp = bpy.context.object; kp.scale = (.9, .7, .03); kp.parent = flug; kp.location = KUP_L + Vector((0, 0, .02)); kp.data.materials.append(grau)

# ---------- Roentgen-Fluegel: Treibstoff (bernsteinfarben, leuchtend) fuellt die Tanks von innen nach aussen
ROENT = []
for m in (weiss, rumpf_m, gondel_m, seiten_m, grau):
    nn = m.node_tree.nodes; ll = m.node_tree.links; out = nn["Material Output"]
    src = out.inputs["Surface"].links[0].from_socket
    mx_ = nn.new("ShaderNodeMixShader"); tr_ = nn.new("ShaderNodeBsdfTransparent")
    ll.new(src, mx_.inputs[1]); ll.new(tr_.outputs[0], mx_.inputs[2]); ll.new(mx_.outputs[0], out.inputs["Surface"]); ROENT.append(mx_.inputs[0])
sprit = bpy.data.materials.new("sprit"); sprit.use_nodes = True; n = sprit.node_tree.nodes; l = sprit.node_tree.links; b = n["Principled BSDF"]
b.inputs["Base Color"].default_value = (*hexf("ffb12e"), 1); b.inputs["Emission Color"].default_value = (*hexf("ff9a10"), 1); b.inputs["Emission Strength"].default_value = 9
tc = n.new("ShaderNodeTexCoord"); sp = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Object"], sp.inputs[0])
ab_ = n.new("ShaderNodeMath"); ab_.operation = "ABSOLUTE"; l.new(sp.outputs["Y"], ab_.inputs[0])
SPRIT_STAND = n.new("ShaderNodeValue"); SPRIT_STAND.outputs[0].default_value = 0
lt_ = n.new("ShaderNodeMath"); lt_.operation = "LESS_THAN"; l.new(ab_.outputs[0], lt_.inputs[0]); l.new(SPRIT_STAND.outputs[0], lt_.inputs[1])
l.new(lt_.outputs[0], b.inputs["Alpha"])
SPRIT = []
for s in (1, -1):
    o = kind(obj_aus(fluegel_bm(SPW - 2.5, 3.0, 27.0, 13.5, 3.0, 33.5, 5.6, -2.6, 1.6, .25, s), f"sprit{s}", sprit)); o.visible_shadow = False
    SPRIT.append(o)

# ---------- 6400 Autos (80 x 80) als Array neben dem Flugzeug
bm = bmesh.new()
for (x0, x1, y0, y1, z0, z1) in ((-2.2, 2.2, -.88, .88, .3, 1.0), (-1.1, .9, -.8, .8, 1.0, 1.45)):
    r_ = bmesh.ops.create_cube(bm, size=1)["verts"]
    for v in r_:
        v.co = Vector(((x0 + x1) / 2 + v.co.x * (x1 - x0), (y0 + y1) / 2 + v.co.y * (y1 - y0), (z0 + z1) / 2 + v.co.z * (z1 - z0)))
bmesh.ops.bevel(bm, geom=bm.edges[:], offset=.12, segments=2, affect="EDGES")
autos = obj_aus(bm, "autos", None, True)
am = bpy.data.materials.new("autos"); am.use_nodes = True; n = am.node_tree.nodes; l = am.node_tree.links; b = n["Principled BSDF"]
tc = n.new("ShaderNodeTexCoord"); vo = n.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 1; mp_ = n.new("ShaderNodeMapping")
mp_.inputs["Scale"].default_value = (1 / 5.4, 1 / 2.6, 1)
l.new(tc.outputs["Object"], mp_.inputs[0]); l.new(mp_.outputs[0], vo.inputs["Vector"])
cr = n.new("ShaderNodeValToRGB"); cr.color_ramp.interpolation = "CONSTANT"
farben = ["d9dde2", "1c1d20", "8a9099", "f4f4f2", "9b1c1c", "1f3f7a", "5a5e63", "c9c3b4"]
cr.color_ramp.elements[0].color = (*hexf(farben[0]), 1); cr.color_ramp.elements[1].position = 1 / 8; cr.color_ramp.elements[1].color = (*hexf(farben[1]), 1)
for i, f_ in enumerate(farben[2:]):
    e_ = cr.color_ramp.elements.new((i + 2) / 8); e_.color = (*hexf(f_), 1)
l.new(vo.outputs["Color"], cr.inputs["Fac"]); l.new(cr.outputs[0], b.inputs["Base Color"])
b.inputs["Metallic"].default_value = .5; b.inputs["Roughness"].default_value = .25; b.inputs["Coat Weight"].default_value = .6
autos.data.materials.append(am)
for ax, off in (((5.4, 0, 0), 80), ((0, 2.6, 0), 80)):
    ar = autos.modifiers.new("arr", "ARRAY"); ar.use_relative_offset = False; ar.use_constant_offset = True; ar.constant_offset_displace = ax; ar.count = off
autos.location = (60, 60, 0)

# ---------- Bodenfahrzeuge fuer den Zeitraffer
FZ = []
for i, (farbe, gr) in enumerate((("f2b800", (3.5, 1.8, 1.6)), ("e9ecf1", (6, 2.4, 3.2)), ("2f6fb3", (3, 1.6, 1.4)), ("f2b800", (4, 1.8, 1.8)))):
    bpy.ops.mesh.primitive_cube_add(size=1); o = bpy.context.object; o.scale = gr; o.data.materials.append(mat(f"fz{i}", hexf(farbe), .4))
    bv = o.modifiers.new("b", "BEVEL"); bv.width = .15; bv.segments = 2; FZ.append(o)

# ---------- Arbeiter
AR = MH.Arbeiter("tankwart", seed=11, alter=.5, haut="african", muskel=.55)

# ======================================================================  Ablauf
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam; cam.data.lens = 30; cam.data.clip_end = 90000; cam.data.sensor_fit = "VERTICAL"
cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = 4
bpy.ops.object.light_add(type="AREA"); fill = bpy.context.object; fill.data.size = 1.5; fill.data.energy = 120; fill.data.color = (1, .94, .87)
fill.parent = cam; fill.location = (.6, .4, .3)


def ease(x):
    x = min(1, max(0, x)); return x * x * (3 - 2 * x)


def lerpv(a, b, k):
    return Vector(a).lerp(Vector(b), k)


def flug_welt(p):
    return flug.matrix_world @ Vector(p)


# Wagen-Endposition: unter dem linken Fluegel, parallel zum Rumpf, Buehne unter der Kupplung
def tw_zustand(t):
    # Kupplung in Welt (Flugzeug am Gate)
    M = Matrix.Translation(GATE) @ Matrix.Rotation(-P / 2, 4, "Z")
    kw = M @ KUP_L
    ende = Vector((kw.x, kw.y - 4.6, 0))   # Buehne (lokal x=4.6) liegt nach der Drehung bei +4.6 in y
    rich = P / 2   # Fahrzeug-x (vorne = -x lokal? Fahrerhaus bei x=0..2.2, faehrt nach -x) -> Welt -y
    if t < 5.0:
        k = 0.0; pos = ende + Vector((0, 60, 0))
    elif t < 8.1:
        k = ease((t - 5.0) / 3.1); pos = ende + Vector((0, 60 * (1 - k), 0))
    else:
        pos = ende
    if t >= 24.4:   # Flugzeug weg: Wagen steht etwas abseits
        pos = ende + Vector((14, 14, 0))
    TW.location = pos; TW.rotation_euler = (0, 0, rich)
    hub = 0.0
    if 8.1 <= t < 24.4:
        hub = ease((t - 8.1) / 1.4)
    zmax = (kw.z - .25) - 1.9 - 2.1   # Buehne so hoch, dass der Arbeiter die Kupplung erreicht
    BUEHNE.location.z = 1.9 + max(.2, zmax) * hub
    for i, (a_, b_) in enumerate(SCHERE):
        z0 = 1.9 + (BUEHNE.location.z - 1.9) * i / 4; z1 = 1.9 + (BUEHNE.location.z - 1.9) * (i + 1) / 4
        for o, yy, sg in ((a_, -.9, 1), (b_, .9, -1)):
            p0 = Vector((4.6 - sg * 1.0, yy, z0)); p1 = Vector((4.6 + sg * 1.0, yy, z1)); d_ = p1 - p0
            o.location = (p0 + p1) / 2; o.rotation_euler = d_.to_track_quat("Z", "Y").to_euler(); o.scale = (1, 1, d_.length / 1.414)
    return kw, hub


T_START = 24.45


def flug_zustand(t):
    if t < T_START:
        flug.location = GATE; flug.rotation_euler = (0, 0, -P / 2)
    elif t < 26.45:   # Start auf der Piste (Zeitsprung)
        k = (t - T_START) / 2.0
        x = 900 - 260 * k - 120 * k * k; z = 6.0 + max(0, (k - .45)) ** 1.6 * 60
        flug.location = (x, 0, z); flug.rotation_euler = (0, max(0, min(.14, (k - .4) * .5)), 0)
    else:   # naechster A380 rollt ans Gate
        k = ease((t - 26.45) / (D - 26.45))
        flug.location = GATE + Vector((0, -60 * (1 - k), 0)); flug.rotation_euler = (0, 0, -P / 2)


def arbeiter(t, kw, hub):
    AR.zuruecksetzen()
    AR.dreh("upperarm01.L", z=-.72); AR.dreh("upperarm01.R", z=.72)
    if t < 5.0 or t >= 26.45:   # steht vor dem Flugzeug, schaut hoch
        AR.rig.parent = None; AR.rig.location = GATE.xy.to_3d() + Vector((7, -14, 0)); AR.rig.rotation_euler = (0, 0, .42)
        AR.dreh("neck01", x=-.3 - .05 * math.sin(t), z=-.25); AR.dreh("upperarm01.R", z=.6, x=.2); AR.dreh("lowerarm01.R", x=-.4)
    elif t < 8.1:   # faehrt (im Fahrerhaus nicht sichtbar)
        AR.sichtbar(False); return
    elif t < 24.4:  # auf der Buehne, Kupplung anschliessen
        AR.rig.parent = TW; AR.rig.location = (4.6, .3, BUEHNE.location.z + .12); AR.rig.rotation_euler = (0, 0, P)
        greif = ease((t - 8.6) / .9) if t < 10.1 else 1.0
        AR.dreh("upperarm01.R", x=1.9 * greif + .1, z=.72 * (1 - greif) + .15)
        AR.dreh("upperarm01.L", x=1.6 * greif, z=-.72 * (1 - greif) - .15)
        AR.dreh("lowerarm01.R", x=-.3 * greif); AR.dreh("neck01", x=-.6 * greif)
    else:   # schaut dem startenden Flugzeug nach
        AR.rig.parent = None; AR.rig.location = GATE.xy.to_3d() + Vector((-3.3, -27.3, 0)); AR.rig.rotation_euler = (0, 0, 1.1)
        AR.dreh("neck01", x=-.15, z=.2)
    AR.sichtbar(True)


S1 = ((GATE.x + 8.6, GATE.y - 17.6, 1.35), (GATE.x + 7, GATE.y - 14, 1.65), (GATE.x + 8.3, GATE.y - 16.8, 1.4), (GATE.x + 7, GATE.y - 14, 1.65))
SZ = [
    (0.0, 2.1, *S1),
    (2.1, 5.0, (GATE.x + 70, GATE.y - 95, 3), (GATE.x, GATE.y - 36, 9), (GATE.x + 60, GATE.y - 80, 6), (GATE.x, GATE.y - 36, 9)),
    (5.0, 8.1, "tw", (-6, -6, 2.0), (3, 0, 1.6), (-5, -5, 2.4), (3, 0, 2.0)),
    (8.1, 10.15, "tw", (1.6, -3.8, 2.6), (4.6, .3, 4.0), (2.0, -3.4, 3.0), (4.6, .2, 4.4)),
    (10.15, 12.4, "tw", (7.2, -2.8, 1.0), (4.8, .2, 4.2), (6.8, -2.4, 1.2), (4.8, .2, 4.4)),
    (12.4, 14.55, "tw", (11, -7, 1.2), (4.6, 0, 3.5), (9.5, -6, 1.5), (4.6, 0, 4.0)),
    (14.55, 18.15, (GATE.x + 300, GATE.y - 420, 260), (GATE.x + 160, GATE.y - 150, 0), (GATE.x + 270, GATE.y - 400, 240), (GATE.x + 150, GATE.y - 150, 0)),
    (18.15, 20.95, (GATE.x + 34, GATE.y - 72, 19), (GATE.x + 14, GATE.y - 36, 4), (GATE.x + 32, GATE.y - 68, 17), (GATE.x + 14, GATE.y - 36, 4)),
    (20.95, 24.45, (GATE.x - 120, GATE.y - 160, 45), (GATE.x, GATE.y - 30, 5), (GATE.x - 110, GATE.y - 150, 40), (GATE.x, GATE.y - 30, 5)),
    (24.45, 26.45, (GATE.x - 7.5, GATE.y - 25.5, 1.75), (700, 0, 12), (GATE.x - 7.4, GATE.y - 25.6, 1.75), (560, 0, 30)),
    (26.45, D + .01, S1[2], S1[3], S1[0], S1[1]),
]


def zustand(t):
    flug_zustand(t)
    kw, hub = tw_zustand(t)
    bpy.context.view_layer.update()
    arbeiter(t, kw, hub)
    # Schlaeuche
    gw = TW.matrix_world
    grube.location = gw @ Vector((5.5, -4.0, 0)) + Vector((0, 0, .03))
    p_ = [gw @ Vector((5.5, -4.0, .05)), gw @ Vector((5.5, -2.8, .1)), gw @ Vector((5.2, -1.5, .5)), gw @ Vector((4.8, -1.27, 1.2))]
    for i, bp_ in enumerate(SPH.bezier_points):
        bp_.co = p_[i]; bp_.handle_left_type = bp_.handle_right_type = "AUTO"
    SCHL_H.hide_render = not (8.1 <= t < 24.4)
    q_ = [gw @ Vector((7.3, -.6, 2.0)), gw @ Vector((6.4, -.6, BUEHNE.location.z - .2)), gw @ Vector((4.9, .2, BUEHNE.location.z + .9)), kw + Vector((0, 0, -.2))]
    for i, bp_ in enumerate(SPF.bezier_points):
        bp_.co = q_[i]; bp_.handle_left_type = bp_.handle_right_type = "AUTO"
    SCHL_F.hide_render = not (9.6 <= t < 24.4)
    # Roentgen-Fluegel
    r = .85 * ease((t - 18.3) / .5) * (1 - ease((t - 20.6) / .3))
    for s in ROENT:
        s.default_value = r
    for o in SPRIT:
        o.hide_render = r < .05
    SPRIT_STAND.outputs[0].default_value = 3 + 36 * ease((t - 18.5) / 2.0)
    autos.hide_render = not (14.55 <= t < 18.15)
    TW.hide_render = t >= 24.45 and t < 26.45 and False
    # Zeitraffer: Sonne + Bodenfahrzeuge
    if 20.95 <= t < 24.45:
        k = (t - 20.95) / 3.5
        el = 40 - 18 * k; rot = 150 + 60 * k
    else:
        el, rot = 40, 150
    sky.sun_elevation = math.radians(el); sky.sun_rotation = math.radians(rot); sonne.rotation_euler = (math.radians(90 - el), 0, math.radians(rot - 90))
    for i, o in enumerate(FZ):
        if 20.95 <= t < 24.45:
            k = (t - 20.95) / 3.5 * (1.4 + .3 * i) + i * .27; k = k % 1
            pfad = [(GATE.x - 40, GATE.y - 20 - i * 8), (GATE.x + 20 - i * 6, GATE.y - 10 - i * 9), (GATE.x + 45, GATE.y - 40 + i * 5)]
            a_ = Vector(pfad[int(k * 2)]); b_ = Vector(pfad[int(k * 2) + 1]); kk = (k * 2) % 1
            pp = a_.lerp(b_, kk); o.location = (pp.x, pp.y, o.scale.z / 2); d_ = b_ - a_; o.rotation_euler = (0, 0, math.atan2(d_.y, d_.x))
            o.hide_render = False
        else:
            o.hide_render = True
    # Kamera
    for s in SZ:
        if s[0] <= t < s[1]:
            if s[2] == "tw":
                k = (t - s[0]) / (s[1] - s[0]); k = ease(k) * .85 + k * .15
                pos = gw @ lerpv(s[3], s[5], k); ziel = gw @ lerpv(s[4], s[6], k)
            else:
                k = (t - s[0]) / (s[1] - s[0]); k = ease(k) * .85 + k * .15
                pos = lerpv(s[2], s[4], k); ziel = lerpv(s[3], s[5], k)
            break
    cam.location = pos; d = ziel - pos; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.dof.focus_distance = min(d.length, 3000)
    nah = t < 2.1 or (8.1 <= t < 14.55) or t >= 26.45
    fill.hide_render = not nah
    cam.data.dof.aperture_fstop = 2.8 if nah else 11
    cam.data.lens = 35 if nah else (24 if 14.55 <= t < 18.15 else (45 if 24.45 <= t < 26.45 else 30))


os.makedirs(A.ordner, exist_ok=True)
N = int(round(D * A.fps))
liste = [int(round(float(x) * A.fps)) for x in A.nur.split(",")] if A.nur else list(range(A.start, N))
for f in liste:
    pfad = os.path.join(A.ordner, f"tanker_{f:04d}.png")
    if os.path.exists(pfad) and not A.nur:
        continue
    zustand(f / A.fps); bpy.context.view_layer.update(); zustand(f / A.fps)
    sc.render.filepath = pfad
    bpy.ops.render.render(write_still=True); print("FERTIG", pfad, flush=True)
