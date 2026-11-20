"""Geschichte: Ein Fahrer muss einen 800-t-BelAZ 75710 auf der steilen Rampe in den Tagebau anhalten (elektrische Bremse).
Baut auf dem Modell aus belaz3d.py auf (bis 'Kamera + Ablauf'), dazu: Rampe, hohle Kabine mit Fahrer, Radmotoren,
Energieleitungen, gluehende Bremswiderstaende mit Luefter, Roentgen-Modus.
python3 fahrer3d.py <ordner> [--nur t1,t2] [--start i]"""
import os, sys, math
HIER = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HIER)
quelle = open(os.path.join(HIER, "belaz3d.py")).read().split("# ======================================================================  Kamera + Ablauf")[0]
sys.argv = [sys.argv[0]] + sys.argv[1:]
exec(quelle)
import fahrer as FM
from mathutils import Matrix

D = A.dauer if A.dauer != 30.5 else 33.4
STEIG = .1; WINKEL = math.atan(STEIG)

# Fels: grauer, mehr Kontrast, Bermen hell, Waende dunkel
_cr = [n for n in fels.node_tree.nodes if n.type == "VALTORGB"][0]
for e_, h_ in zip(_cr.color_ramp.elements, ("3a352f", "8a7f72", "55504a", "6e5440")):
    e_.color = (*hexf(h_), 1)
_wv = [n for n in fels.node_tree.nodes if n.type == "TEX_WAVE"][0]; _wv.inputs["Scale"].default_value = .02; _wv.inputs["Distortion"].default_value = 3
# ---------- alte Objekte ausblenden, die hier nicht gebraucht werden
for o in KABINE + MESS + MENSCHEN + AUTOS:
    o.hide_render = True
for o, *_ in BROCKEN:
    o.hide_render = True
ladung.hide_render = False

# ---------- Gelaende: Boden + Terrassen + Haufen auf den Grubenboden absenken
TIEF = -45
boden.location.z = TIEF; wand.location.z = TIEF
for o in list(sc.objects):
    if o.parent is None and o.type == "MESH" and o.name.split(".")[0] in ("Icosphere", "Cone") and abs(o.location.z) < 6:
        o.location.z += TIEF

# Rampe: Querschnitt (y, z) entlang x, Hoehe z = STEIG * x
QS = [(70, 22, "f"), (30, 16, "f"), (16.5, 1.5, "f"), (14.5, 0, "s"), (-13, 0, "s"), (-13.6, 1.2, "f"), (-14.6, 1.2, "f"),
      (-15.5, 0, "f"), (-52, TIEF + 4, "f"), (-110, TIEF, "f")]
bm = bmesh.new(); XS = [x for x in range(-230, 101, 6)]; rr2 = random.Random(5); rg = {}
for i, x in enumerate(XS):
    for j, (y, z, _) in enumerate(QS):
        rau = 0 if QS[j][2] == "s" or (j + 1 < len(QS) and QS[j + 1][2] == "s" and False) else rr2.uniform(-1, 1) * (1.2 if abs(y) > 16 else .2)
        rg[i, j] = bm.verts.new((x, y + (rau if abs(y) > 16 else 0), z + STEIG * x + rau * .6))
for i in range(len(XS) - 1):
    for j in range(len(QS) - 1):
        f = bm.faces.new((rg[i, j], rg[i + 1, j], rg[i + 1, j + 1], rg[i, j + 1]))
        f.material_index = 0 if (QS[j][2] == "s" and QS[j + 1][2] == "s") else 1
me = bpy.data.meshes.new("rampe"); bm.to_mesh(me); bm.free()
rampe = bpy.data.objects.new("rampe", me); sc.collection.objects.link(rampe); me.materials.append(bd); me.materials.append(fels)
for p in me.polygons:
    p.use_smooth = p.material_index == 1
sd = rampe.modifiers.new("s", "SUBSURF"); sd.levels = 2; sd.render_levels = 2; sd.subdivision_type = "SIMPLE"
dr = rampe.modifiers.new("d", "DISPLACE"); dr.texture = tw; dr.strength = 1.4; dr.texture_coords = "GLOBAL"
vg = rampe.vertex_groups.new(name="fels")
vg.add([v.index for v in me.vertices if abs(v.co.y) > 15.2 or v.co.z - STEIG * v.co.x > .5], 1.0, "REPLACE")
dr.vertex_group = "fels"
# Lichtmasten an der Rampe (Rand oben)
for o in list(boden.children):
    o.hide_render = True
for i in range(6):
    x = -200 + i * 55; z0 = STEIG * x
    zyl((x, 15.5, z0), (x, 15.5, z0 + 12), .16, RAHMEN, 10, eltern=boden)
    box(x - .8, x + .8, 15.3, 15.7, z0 + 11.6, z0 + 12.1, RAHMEN, eltern=boden)
for o in boden.children:
    if not o.hide_render:
        o.location.z -= TIEF   # boden ist abgesenkt, Masten bleiben auf Rampenhoehe

# ---------- Roentgen: alle Lkw-Materialien bekommen eine Transparenz-Mischung
ROENT = []
for m in (GELB, GELB_M, RAHMEN, GUMMI, STAHL, CHROM, GRILL_D, ld_m, GLAS):
    n = m.node_tree.nodes; l = m.node_tree.links; out = n["Material Output"]
    src = out.inputs["Surface"].links[0].from_socket
    mx = n.new("ShaderNodeMixShader"); tr = n.new("ShaderNodeBsdfTransparent")
    l.new(src, mx.inputs[1]); l.new(tr.outputs[0], mx.inputs[2]); l.new(mx.outputs[0], out.inputs["Surface"])
    mx.inputs[0].default_value = 0; ROENT.append(mx.inputs[0])


def roentgen(v):
    for s in ROENT:
        s.default_value = v


# ---------- hohle Kabine mit Glas, Sitz, Lenkrad, Armaturen, Pedal
GLAS2 = bpy.data.materials.new("glas2"); GLAS2.use_nodes = True; n = GLAS2.node_tree.nodes; l = GLAS2.node_tree.links
for k in list(n):
    n.remove(k)
o_ = n.new("ShaderNodeOutputMaterial"); gl = n.new("ShaderNodeBsdfGlass"); gl.inputs["IOR"].default_value = 1.05; gl.inputs["Roughness"].default_value = .02
gl.inputs["Color"].default_value = (.85, .92, .95, 1)
tr = n.new("ShaderNodeBsdfTransparent"); lp = n.new("ShaderNodeLightPath"); mx = n.new("ShaderNodeMixShader")
l.new(lp.outputs["Is Shadow Ray"], mx.inputs[0]); l.new(gl.outputs[0], mx.inputs[1]); l.new(tr.outputs[0], mx.inputs[2]); l.new(mx.outputs[0], o_.inputs["Surface"])
INNEN, _ = mat("innen", hexf("3b3f44"), .7)
SITZ, _ = mat("sitz", hexf("1c1c1e"), .6)
X0k, X1k, Y0k, Y1k, Z0k, Z1k, ZF = .35, 3.5, -4.55, -1.95, 5.55, 7.75, 6.45
w_ = .09
box(X0k, X1k, Y0k, Y1k, Z0k, Z0k + .1, INNEN)                            # Boden
box(X0k, X1k, Y0k, Y1k, Z1k - .12, Z1k, GELB, .04)                         # Dach
box(X1k - w_, X1k, Y0k, Y1k, Z0k, Z1k, GELB)                               # Rueckwand
box(X0k, X0k + w_, Y0k, Y1k, Z0k, ZF, GELB)                                # Front unten
for y in (Y0k, Y1k - w_):
    box(X0k, X1k, y, y + w_, Z0k, ZF, GELB)                                # Seiten unten
for x, y in ((X0k, Y0k), (X0k, Y1k - w_), (X1k - w_, Y0k), (X1k - w_, Y1k - w_), (1.9, Y0k), (1.9, Y1k - w_)):
    box(x, x + w_, y, y + w_, ZF, Z1k, RAHMEN)                             # Saeulen
box(X0k + .02, X0k + .05, Y0k + w_, Y1k - w_, ZF, Z1k - .12, GLAS2)          # Frontscheibe
for y in (Y0k + .02, Y1k - .05):
    box(X0k + w_, X1k - w_, y, y + .03, ZF, Z1k - .12, GLAS2)              # Seitenscheiben
box(.3, .42, -4.5, -2.0, Z1k - .15, Z1k - .03, RAHMEN)                     # Sonnenblende
box(X0k + w_, .95, Y0k + w_, Y1k - w_, Z0k + .1, 6.35, INNEN, .05)          # Armaturenbrett
box(.55, .7, -3.6, -2.9, 6.35, 6.5, RAHMEN)                                # Instrumente
bild_m, _ = mat("bildschirm", hexf("4fb3ff"), .3, 0, 2.5)
box(.62, .66, -3.5, -3.15, 6.4, 6.6, bild_m)
SITZX, SITZY = 1.95, -3.25
box(SITZX - .3, SITZX + .3, SITZY - .3, SITZY + .3, Z0k + .1, 6.05, SITZ, .06)       # Sitzflaeche
box(SITZX + .25, SITZX + .4, SITZY - .3, SITZY + .3, 6.05, 7.0, SITZ, .06)            # Lehne
bpy.ops.mesh.primitive_torus_add(major_radius=.2, minor_radius=.025, location=(1.38, SITZY, 6.55), rotation=(0, math.radians(60), 0))
lenk = kind(bpy.context.object); lenk.data.materials.append(RAHMEN)
zyl((1.38, SITZY, 6.55), (1.0, SITZY, 6.2), .04, RAHMEN, 10)
# Pedale (Retarder rechts = groesser, gelb markiert)
ped_m, _ = mat("pedal", hexf("c9a227"), .4, .5)
pedal = kind(bpy.data.objects.new("pedal_dreh", None)); sc.collection.objects.link(pedal); pedal.location = (1.22, SITZY + .1, Z0k + .1)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, .14)); pp = bpy.context.object; pp.scale = (.04, .16, .3); pp.parent = pedal
pp.rotation_euler = (0, .9, 0); pp.data.materials.append(ped_m)
bpy.ops.mesh.primitive_cube_add(size=1, location=(1.3, SITZY - .15, Z0k + .25)); p2 = kind(bpy.context.object); p2.scale = (.05, .1, .2)
p2.rotation_euler = (0, -.5, 0); p2.data.materials.append(RAHMEN)
bpy.ops.object.light_add(type="AREA", location=(2.0, -3.25, 7.55)); innenlicht = kind(bpy.context.object)
innenlicht.data.energy = 120; innenlicht.data.size = 1.2; innenlicht.data.color = (1, .95, .88)

# ---------- Radmotoren (Kupfer, Spulen leuchten), Energieleitungen, Widerstandsgitter, Luefter
kupfer, _ = mat("kupfer", hexf("b87333"), .3, 1)
spule = bpy.data.materials.new("spule"); spule.use_nodes = True; b = spule.node_tree.nodes["Principled BSDF"]
b.inputs["Base Color"].default_value = (.05, .05, .05, 1); SPULE_F = b.inputs["Emission Color"]; SPULE_S = b.inputs["Emission Strength"]
MOTOREN = []
for x in (4.6, 12.6):
    for s in (-1, 1):
        MOTOREN.append(zyl((x, s * 2.75, 2.04), (x, s * 3.85, 2.04), .62, kupfer, 32))
        for k in range(5):
            yy = s * (2.85 + k * .22)
            bpy.ops.mesh.primitive_torus_add(major_radius=.64, minor_radius=.05, location=(x, yy, 2.04), rotation=(P / 2, 0, 0))
            t_ = kind(bpy.context.object); t_.data.materials.append(spule); MOTOREN.append(t_)
fluss = bpy.data.materials.new("fluss"); fluss.use_nodes = True; n = fluss.node_tree.nodes; l = fluss.node_tree.links
for k in list(n):
    n.remove(k)
o_ = n.new("ShaderNodeOutputMaterial"); em = n.new("ShaderNodeEmission"); tc = n.new("ShaderNodeTexCoord"); mp = n.new("ShaderNodeMapping")
wv = n.new("ShaderNodeTexWave"); wv.wave_type = "BANDS"; wv.bands_direction = "X"; wv.inputs["Scale"].default_value = 6
l.new(tc.outputs["Generated"], mp.inputs[0]); l.new(mp.outputs[0], wv.inputs["Vector"])
cr = n.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].position = .55; cr.color_ramp.elements[0].color = (.25, .08, .01, 1)
cr.color_ramp.elements[1].color = (1, .45, .08, 1); l.new(wv.outputs["Fac"], cr.inputs["Fac"]); l.new(cr.outputs[0], em.inputs["Color"])
em.inputs["Strength"].default_value = 30; l.new(em.outputs[0], o_.inputs["Surface"])
FLUSS_MAP = mp; FLUSS_RAMP = cr
LEITUNGEN = []
ZIEL = Vector((1.85, 3.2, 5.9))
for x in (4.6, 12.6):
    for s in (-1, 1):
        pts = [Vector((x, s * 2.7, 2.04)), Vector((x, s * 1.5, 2.7)), Vector((min(x, 7.0), s * 1.5, 3.1)), Vector((4.2, 1.5, 4.6)), Vector((2.6, 2.4, 5.4)), ZIEL]
        cu = bpy.data.curves.new("leitung", "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = .11; cu.bevel_resolution = 3
        sp_ = cu.splines.new("POLY"); sp_.points.add(len(pts) - 1)
        for i, p_ in enumerate(pts):
            sp_.points[i].co = (*p_, 1)
        ob = bpy.data.objects.new("leitung", cu); sc.collection.objects.link(ob); kind(ob); cu.materials.append(fluss); LEITUNGEN.append(ob)
# Widerstandsgitter im Schaltschrank: Front offen mit Heizbaendern
for o in SCHRANK:
    o.hide_render = True
box(.6, 3.1, 1.95, 4.45, 5.55, 5.7, GELB)
box(.6, 3.1, 1.95, 2.05, 5.55, 6.95, GELB); box(.6, .7, 1.95, 4.45, 5.55, 6.95, GELB); box(3.0, 3.1, 1.95, 4.45, 5.55, 6.95, GELB)
box(.6, 3.1, 1.95, 4.45, 6.85, 6.95, GELB)
glut = bpy.data.materials.new("glut"); glut.use_nodes = True; b = glut.node_tree.nodes["Principled BSDF"]
b.inputs["Base Color"].default_value = (.12, .1, .09, 1); b.inputs["Roughness"].default_value = .5; b.inputs["Metallic"].default_value = .6
b.inputs["Emission Color"].default_value = (1, .28, .04, 1); GLUT = b.inputs["Emission Strength"]
for i in range(9):
    z = 5.82 + i * .12
    for j in range(2):
        bpy.ops.mesh.primitive_cylinder_add(radius=.03, depth=2.3, vertices=10, location=(1.85, 2.6 + j * 1.2, z), rotation=(0, P / 2, 0))
        kind(bpy.context.object).data.materials.append(glut)
        for k in range(10):
            bpy.ops.mesh.primitive_cube_add(size=1, location=(.85 + k * .22, 2.6 + j * 1.2, z + .06)); c_ = kind(bpy.context.object)
            c_.scale = (.02, .55, .02); c_.data.materials.append(glut)
bpy.ops.object.light_add(type="POINT", location=(1.85, 3.2, 6.3)); glutlicht = kind(bpy.context.object); glutlicht.data.color = (1, .4, .1)
LUEFTER = []
for xx in (1.2, 2.5):
    zyl((xx, 3.2, 6.95), (xx, 3.2, 7.25), .55, RAHMEN, 32)
    bpy.ops.mesh.primitive_cylinder_add(radius=.5, depth=.02, vertices=32, location=(xx, 3.2, 7.26)); kind(bpy.context.object).data.materials.append(GRILL_D)
    rot = kind(bpy.data.objects.new("rotor", None)); sc.collection.objects.link(rot); rot.location = (xx, 3.2, 7.2)
    for k in range(6):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(.24, 0, 0)); bl = bpy.context.object; bl.scale = (.42, .1, .015)
        bl.parent = rot; bl.rotation_euler = (.35, 0, 0)
        m_ = Matrix.Rotation(2 * P * k / 6, 4, "Z"); bl.matrix_parent_inverse = m_; bl.data.materials.append(STAHL)
    LUEFTER.append(rot)
# Hitzeflimmern: leicht leuchtende, transparente Schleier ueber den Lueftern
hz = bpy.data.materials.new("hitze"); hz.use_nodes = True; n = hz.node_tree.nodes; l = hz.node_tree.links
for k in list(n):
    n.remove(k)
o_ = n.new("ShaderNodeOutputMaterial"); rf = n.new("ShaderNodeBsdfRefraction"); rf.inputs["IOR"].default_value = 1.015
tc = n.new("ShaderNodeTexCoord"); HZ_MAP = n.new("ShaderNodeMapping"); nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 4
bp_ = n.new("ShaderNodeBump"); bp_.inputs["Strength"].default_value = .6
l.new(tc.outputs["Object"], HZ_MAP.inputs[0]); l.new(HZ_MAP.outputs[0], nz.inputs["Vector"]); l.new(nz.outputs["Fac"], bp_.inputs["Height"])
l.new(bp_.outputs[0], rf.inputs["Normal"]); l.new(rf.outputs[0], o_.inputs["Surface"])
HITZE = []
for xx in (1.2, 2.5):
    bpy.ops.mesh.primitive_cylinder_add(radius=.5, depth=2.2, vertices=24, location=(xx, 3.2, 8.4)); h_ = kind(bpy.context.object)
    h_.data.materials.append(hz); h_.visible_shadow = False; HITZE.append(h_)

# ---------- Fahrer
fa = FM.Fahrer(sc); fa.root.parent = lkw
# Wo landet der Fuss beim Sitzen? -> Pedal dorthin
J_sitz = FM.Fahrer.pose("sitzen", pedal=0)

# ======================================================================  Ablauf
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam; cam.data.lens = 28; cam.data.clip_end = 5000; cam.data.sensor_fit = "VERTICAL"
cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = 4


def ease(x):
    x = min(1, max(0, x)); return x * x * (3 - 2 * x)


def lerpv(a, b, k):
    return Vector(a).lerp(Vector(b), k)


T_LOS, T_VOLL, T_BREMS, T_STOP, VMAX, X0 = 9.2, 12.6, 17.3, 29.1, 8.0, 40.0


def v_von(t):
    if t < T_LOS:
        return 0
    if t < T_VOLL:
        return VMAX * ease((t - T_LOS) / (T_VOLL - T_LOS))
    if t < T_BREMS:
        return VMAX
    if t < T_STOP:
        k = (t - T_BREMS) / (T_STOP - T_BREMS); return VMAX * (1 - k) ** 1.6
    return 0


WEG = [0.0]
for i in range(1, int(D * 100) + 2):
    WEG.append(WEG[-1] + v_von((i - .5) / 100) * .01)


def weg(t):
    return WEG[min(len(WEG) - 1, max(0, int(round(t * 100))))]


def lkw_matrix(t):
    x = X0 - weg(t); bump = (.02 * math.sin(t * 9) + .012 * math.sin(t * 23)) * min(1, v_von(t) / 3)
    return Matrix.Translation((x, 0, STEIG * x + bump)) @ Matrix.Rotation(-WINKEL, 4, "Y")


def W(t, p):
    return lkw_matrix(t) @ Vector(p)


# Szenen: (start, ende, cam_a, ziel_a, cam_b, ziel_b, modus) ; modus "l" = relativ zum Lkw, "w" = Welt (bei T_STOP-Lage)
S1 = ((-2.6, -13.5, .7), (4.2, -4.4, 3.4), (-1.6, -11.6, .8), (4.2, -4.4, 3.4))
SZ = [
    (0.0, 2.08, *S1, "l"),
    (2.08, 3.6, (-90, -150, 95), (-40, 0, -10), (-75, -140, 85), (-35, 0, -10), "w0"),
    (3.6, 5.55, (26, 8, 10), (-30, -3, -3), (22, 8.5, 8.5), (-30, -3, -4), "l"),
    (5.55, 7.2, (-10, 4.5, 2.4), (-1.2, 2.2, 2.4), (-9.5, 3, 3.4), (-1.2, .8, 3.6), "l"),
    (7.2, 8.95, (-5, -3.8, 5.8), (-1.2, .6, 4.2), (-4.6, -4.2, 6.6), (-.6, -1.6, 5.6), "l"),
    (8.95, 11.5, (6, -25, 2.6), (10, 0, 4), (10, -23, 3.4), (10, 0, 4.2), "l"),
    (11.5, 14.0, (-11, -9, 15), (8, 0, 6), (-8, -11, 17), (8, 0, 6), "l"),
    (14.0, 16.5, (2.9, -3.0, 7.35), (-30, -1.6, 2.4), (2.8, -3.05, 7.3), (-30, -1.8, 2.0), "l"),
    (16.5, 18.7, (1.0, -2.55, 6.6), (1.2, -3.15, 5.68), (1.0, -2.6, 6.5), (1.2, -3.15, 5.66), "l"),
    (18.7, 21.6, (15.5, -11, 2.6), (12.6, -3.3, 2.0), (14.3, -9.5, 2.3), (12.6, -3.3, 2.0), "l"),
    (21.6, 23.55, (5, -27, 13), (7.5, 0, 3.6), (4, -25, 11), (7, 0, 3.8), "l"),
    (23.55, 25.85, (-1.8, 7.4, 7.9), (1.85, 3.2, 6.3), (-1.2, 6.8, 7.6), (1.85, 3.2, 6.4), "l"),
    (25.85, 29.95, (-22, -6, 1.2), (6, 0, 3.5), (-20, -5.5, 1.3), (6, 0, 3.5), "w"),
    (29.95, 31.0, (-3.6, -3.2, 7.0), (2.0, -3.25, 6.6), (-3.2, -3.2, 7.0), (2.0, -3.25, 6.6), "l"),
    (31.0, D + .01, S1[2], S1[3], S1[0], S1[1], "l"),
]


def fahrer_zustand(t):
    """Fahrer: steht vor dem Reifen (Anfang/Ende), steigt Treppe, sitzt in der Kabine."""
    if t < 2.08 or t >= 31.0:
        J = FM.Fahrer.pose("stehen", blick=.3); fa.setze(J, (2.6, -6.2, 0), -P / 2 - .55); return True
    if 5.55 <= t < 8.95:
        a0 = Vector((-1.15, 3.6, .8)); a1 = Vector((-1.15, -1.3, 5.2)); k = (t - 5.55) / 3.4
        if k < .08:
            ort = Vector((-3.0, 4.6, 0)).lerp(a0, k / .08); art = "gehen"
        else:
            ort = a0.lerp(a1, (k - .08) / .92); art = "steigen"
        J = FM.Fahrer.pose(art, ph=t * 1.6); fa.setze(J, (ort.x, ort.y, ort.z - .1), -P / 2); return True
    if t >= 8.95:
        ped = 0.0
        if t >= 16.9:
            ped = ease((t - 16.9) / .45)
        if t >= 29.5:
            ped = 1 - ease((t - 29.5) / .4)
        J = FM.Fahrer.pose("sitzen", pedal=ped, arme_vorne=1)
        if 29.95 <= t < 31.0:  # zuruecklehnen
            k = ease((t - 30.0) / .5)
            for g in ("e_l", "e_r", "h_l", "h_r"):
                J[g] = J[g].lerp(J["s_" + g[-1]] + Vector((.05, 0, -.45 if g[0] == "h" else -.27)), k)
            J["_blick"] = .15 * k
        fa.setze(J, (SITZX - .08, SITZY, 5.63), P)
        pedal.rotation_euler = (0, .3 * ped, 0)
        return True
    return False


def zustand(t):
    M = lkw_matrix(t); lkw.matrix_world = M
    x = weg(t)
    for r in RAEDER:
        r.rotation_euler = (P / 2, -x / 2.04, 0)
    v = v_von(t)
    STAUB_MAP.inputs["Location"].default_value = (x * .05, 0, t * .25)
    staub.hide_render = v < 1.5
    fa.sichtbar(fahrer_zustand(t))
    # Roentgen + Motoren + Leitungen
    r = 0.0
    if 18.9 <= t < 23.55:
        r = .82 * ease((t - 18.9) / .5)
    roentgen(r)
    for o in MOTOREN:
        o.hide_render = r < .05
    gen = ease((t - 20.2) / .6)
    blau, orange = Vector((.2, .55, 1)), Vector((1, .42, .06))
    c = blau.lerp(orange, gen); SPULE_F.default_value = (*c, 1); SPULE_S.default_value = 10 + 8 * math.sin(t * 20) ** 2
    for o in LEITUNGEN:
        o.hide_render = not (21.0 <= t < 23.55)
    FLUSS_MAP.inputs["Location"].default_value = (-t * 1.4, 0, 0)
    # Widerstaende gluehen waehrend des Bremsens
    g = 0.0
    if T_BREMS <= t < T_STOP + 1.5:
        g = ease((t - T_BREMS - .5) / 2.5) * (1 - ease((t - T_STOP) / 1.5))
    GLUT.default_value = 18 * g * (1 + .08 * math.sin(t * 13)); glutlicht.data.energy = 900 * g
    for h_ in HITZE:
        h_.hide_render = g < .2
    HZ_MAP.inputs["Location"].default_value = (0, 0, -t * 1.5)
    for i, rot in enumerate(LUEFTER):
        rot.rotation_euler = (0, 0, t * (14 * g + 1.5) * (1 if i else -1))
    innenlicht.hide_render = not (14.0 <= t < 18.7 or 29.95 <= t < 31.0)
    # Kamera
    for s in SZ:
        if s[0] <= t < s[1]:
            k = ease((t - s[0]) / (s[1] - s[0])) * .85 + (t - s[0]) / (s[1] - s[0]) * .15
            pa, za = lerpv(s[2], s[4], k), lerpv(s[3], s[5], k); mod = s[6]; break
    if mod == "l":
        pos, ziel = W(t, pa), W(t, za)
    elif mod == "w":
        pos, ziel = W(T_STOP, pa), W(T_STOP, za)
    else:  # Weltkoordinaten relativ zur Startposition
        pos, ziel = W(0, pa), W(0, za)
    wk = .035 * min(1, v / 4)
    if 14.0 <= t < 16.5:
        wk = .02
    pos = pos + Vector((0, wk * math.sin(t * 27), wk * math.sin(t * 31)))
    cam.location = pos; d = ziel - pos; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.dof.focus_distance = d.length
    cam.data.lens = 22 if (14.0 <= t < 16.5) else (32 if 16.5 <= t < 18.7 else 30)
    cam.data.dof.aperture_fstop = 2.2 if (16.5 <= t < 18.7 or 23.55 <= t < 25.85) else 5.6


os.makedirs(A.ordner, exist_ok=True)
N = int(round(D * A.fps))
liste = [int(round(float(x) * A.fps)) for x in A.nur.split(",")] if A.nur else list(range(A.start, N))
for f in liste:
    pfad = os.path.join(A.ordner, f"fahrer_{f:04d}.png")
    if os.path.exists(pfad) and not A.nur:
        continue
    zustand(f / A.fps); sc.render.filepath = pfad
    bpy.ops.render.render(write_still=True); print("FERTIG", pfad, flush=True)
