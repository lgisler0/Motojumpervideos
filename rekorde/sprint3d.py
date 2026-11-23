"""Geschichte: Ein Mann hat einen Job: 100 m schneller laufen als alle (Usain Bolt, Berlin 16.8.2009, 9,58 s, GWR).
Szene: Leichtathletikstadion bei Nacht (blaue Bahn, 9 Bahnen, Linien, Startbloecke, Ziellinie, Ranglisten-Tafel ohne Text,
Tribuenen mit Publikum + Blitzlichtern, Dachring mit Flutlicht, Kameraschiene mit Wagen), 8 Sprinter (MPFB) in Trikot + Shorts,
Startnummern, Rennen in Echtzeit mit realistischem Geschwindigkeitsverlauf.
python3 sprint3d.py <ordner> [--nur t1,t2] [--start i] [--samples n]"""
import bpy, bmesh, math, random, sys, os, argparse
from mathutils import Vector, Matrix
HIER = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HIER)
import mensch_mh as MH

ap = argparse.ArgumentParser()
ap.add_argument("ordner"); ap.add_argument("--nur", default=""); ap.add_argument("--skala", type=int, default=50)
ap.add_argument("--samples", type=int, default=10); ap.add_argument("--fps", type=int, default=15)
ap.add_argument("--start", type=int, default=0)
A = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
P = math.pi
D = 28.6
T0 = 12.38                     # Startschuss
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = A.samples; sc.cycles.use_denoising = True
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.transmission_bounces = 2
sc.cycles.adaptive_threshold = .03
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1080, 1920, A.skala
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"; sc.view_settings.exposure = -1.0
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


def emis(name, farbe, st):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0, 0, 0, 1); b.inputs["Emission Color"].default_value = (*hexf(farbe), 1)
    b.inputs["Emission Strength"].default_value = st; return m


def an_knochen(o, rig, bone):
    bpy.context.view_layer.update()
    bn = rig.data.bones[bone]
    o.parent = rig; o.parent_type = "BONE"; o.parent_bone = bone
    o.matrix_parent_inverse = (rig.matrix_world @ bn.matrix_local @ Matrix.Translation((0, bn.length, 0))).inverted()


def box(name, groesse, ort, m, bevel=.01, seg=2, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=ort, rotation=rot); o = bpy.context.object; o.name = name; o.scale = groesse
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        bv = o.modifiers.new("b", "BEVEL"); bv.width = bevel; bv.segments = seg
    o.data.materials.append(m)
    return o


def farbe_setzen(m, f, f2=None):
    for nd in m.node_tree.nodes:
        if nd.type == "MIX" and nd.data_type == "RGBA":
            nd.inputs[6].default_value = (*hexf(f), 1); nd.inputs[7].default_value = (*hexf(f2 or f), 1)


def trimmen(o, gruppen, z_min=None, z_max=None):
    """Huellen-Vertices entfernen: Gewicht in Knochengruppen (Praefix) > .4 oder Rest-Hoehe ausserhalb."""
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


# ======================================================================  Sprinter
TRIKOT = [("2e7d32", "f4d000"), ("c62828", "f2f2f2"), ("1565c0", "f2f2f2"), ("f4d000", "1b7a2c"), ("111111", "e53935"),
          ("ffffff", "1e3a8a"), ("ef6c00", "1b1b1b"), ("6a1b9a", "f2f2f2")]
HAUT = ["african", "african", "african", "african", "caucasian", "african", "african", "caucasian"]
SPR = []
for i in range(8):
    held = i == 3
    m = MH.Arbeiter(name=f"laeufer{i}", seed=100 + i * 7, maenn=1.0, alter=.3, muskel=.92 if held else .85, gewicht=.25,
                    haut=HAUT[i], weste=False)
    knie = m.gm("joint-l-knee").z
    TON = [(.20, .10, .055), (.14, .07, .04), (.26, .14, .08), (.15, .072, .04), (.62, .42, .30), (.22, .11, .06), (.30, .16, .09), (.70, .47, .35)][i]
    for sl in m.koerper.material_slots:
        g = sl.material.node_tree.nodes.get("colorgroup") if sl.material and sl.material.node_tree else None
        if g:
            g.inputs["SkinColor"].default_value = (*TON, 1); g.inputs["SkinOverride"].default_value = 1.0
    for o in m.huellen:
        if o.name.endswith("_hemd"):
            farbe_setzen(o.active_material, TRIKOT[i][0]); trimmen(o, ("upperarm", "lowerarm", "wrist", "finger", "shoulder"))
            o.modifiers["versatz"].strength = .004
            o.active_material.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = .45
        elif o.name.endswith("_hose"):
            farbe_setzen(o.active_material, TRIKOT[i][1]); trimmen(o, ("lowerleg", "foot", "toe"), z_min=knie + .22)
            o.modifiers["versatz"].strength = .005
        elif o.name.endswith(("_hand", "_gesicht")):
            o.hide_render = True
    for o in m.helm:
        o.hide_render = True
    for o in m.stiefel:
        if o.active_material and o.active_material.name.startswith("stiefel"):
            farbe_setzen(o.active_material, ["d4ff00", "ff3d00", "00e5ff", "ffffff"][i % 4])
        if "schaft" in o.name:
            o.scale.z *= .45
    m.objekte = [o for o in m.objekte if o not in m.helm and not o.name.endswith(("_hand", "_gesicht"))]
    hals = m.gm("joint-neck")
    nb = box(f"laeufer{i}_nummer", (.18, .006, .13), (0, hals.y - .17 + .0, hals.z - .3), mat(f"startnummer{i}", "f5f5f0", .7), .004)
    an_knochen(nb, m.rig, "spine03"); m.objekte.append(nb)
    SPR.append(m)
HELD = SPR[3]

# ======================================================================  Stadion (Bahn entlang +x, Start bei x=0, Ziel bei x=100)
BB = 1.22; NB = 9
bahn_m = bpy.data.materials.new("bahn"); bahn_m.use_nodes = True; n = bahn_m.node_tree.nodes; l = bahn_m.node_tree.links; b = n["Principled BSDF"]
tc = n.new("ShaderNodeTexCoord"); nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 300; nz.inputs["Detail"].default_value = 4
l.new(tc.outputs["Object"], nz.inputs["Vector"])
cr = n.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (*hexf("1f4fa0"), 1); cr.color_ramp.elements[1].color = (*hexf("2f66c4"), 1)
l.new(nz.outputs["Fac"], cr.inputs["Fac"]); l.new(cr.outputs[0], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = .8
bp = n.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = .4; bp.inputs["Distance"].default_value = .002
l.new(nz.outputs["Fac"], bp.inputs["Height"]); l.new(bp.outputs[0], b.inputs["Normal"])
box("bahn", (150, NB * BB + 2, .02), (50, NB * BB / 2, -.01), bahn_m, 0)
linie_m = mat("linie", "f4f4f4", .6)
for k in range(NB + 1):
    box("bahnlinie", (150, .05, .004), (50, k * BB, .002), linie_m, 0)
box("startlinie", (.05, NB * BB, .004), (0, NB * BB / 2, .002), linie_m, 0)
box("ziellinie", (.05, NB * BB, .004), (100, NB * BB / 2, .002), linie_m, 0)
for x_ in (10, 20, 30, 40, 50, 60, 70, 80, 90):
    for k in range(NB):
        box("markierung", (.05, .25, .004), (x_, k * BB + .15, .002), linie_m, 0)
# Rasen (Innenraum) + Aussenbereich
rasen = MH._stoff("rasen", "2f6b2a", rau=.9, skala=80)
box("rasen", (180, 70, .02), (50, NB * BB + 36, -.02), rasen, 0)
box("aussen", (180, 8, .02), (50, -4.5, -.015), mat("tartan_aussen", "1a3f82", .85), 0)
# Startbloecke
block_m = mat("block", "b0b5bb", .3, .8); pedal_m = mat("pedal", "1d1d1d", .7)
BLOCK = []
for k in range(8):
    y_ = (k + 1.5) * BB
    BLOCK.append(box("blockschiene", (.7, .1, .05), (-.45, y_, .03), block_m, .01))
    for dx, dy in ((-.25, -.11), (-.6, .11)):
        BLOCK.append(box("pedal", (.08, .14, .14), (dx, y_ + dy, .09), pedal_m, .01, rot=(0, -.8, 0)))
# Zielpfosten + Zeitmesser-Saeule
box("zielpfosten", (.12, .12, 1.4), (100, -.4, .7), mat("pfosten", "f2f2f2", .4), .01)
box("zielkamera", (.25, .4, .3), (100, -.4, 1.55), mat("kamerakoerper", "222222", .4), .02)
# Kameraschiene mit Wagen neben Bahn 0
box("schiene", (130, .3, .08), (45, -1.4, .04), mat("schiene", "555a60", .4, .7), .01)
wagen = box("kamerawagen", (.8, .6, .6), (0, -1.4, .4), mat("wagen", "2b2b2b", .5), .03)
# Tribuenen (Stufen) rundherum (Oval), Publikum als Instanzen
trib_m = mat("tribuene", "5b6068", .8); sitz_m = mat("sitze", "3b5a9a", .6)
MITTE = Vector((50, NB * BB / 2 + 30, 0)); RA, RB = 110, 75
bm = bmesh.new(); NRG = 160; STUF = 26
verts = []
for s_ in range(STUF + 1):
    rr = 1 + s_ * .012; hz = 1.0 + s_ * 1.1
    ring = [bm.verts.new((MITTE.x + RA * rr * math.cos(2 * P * j / NRG), MITTE.y + RB * rr * math.sin(2 * P * j / NRG), hz)) for j in range(NRG)]
    verts.append(ring)
for s_ in range(STUF):
    for j in range(NRG):
        a, b_ = verts[s_], verts[s_ + 1]
        bm.faces.new((a[j], a[(j + 1) % NRG], b_[(j + 1) % NRG], b_[j]))
me = bpy.data.meshes.new("tribuene"); bm.to_mesh(me); bm.free()
trib = bpy.data.objects.new("tribuene", me); sc.collection.objects.link(trib); me.materials.append(trib_m)
# Bande
box("bande", (150, .1, 1.0), (50, -9, .5), mat("bande", "1e2a52", .5), 0)
# Publikum: einfache Figuren als verknuepfte Kopien
pub_cols = ["e53935", "fdd835", "1e88e5", "43a047", "fafafa", "212121", "ff7043", "8e24aa", "000000", "ffeb3b"]
pm = [mat("pub%d" % i, c, .7) for i, c in enumerate(pub_cols)]
haut_pub = [mat("pubhaut%d" % i, c, .6) for i, c in enumerate(["8d5524", "c68642", "e0ac69", "f1c27d", "ffdbac"])]
koerper_me = []
for i, mm in enumerate(pm):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1, matrix=Matrix.Diagonal((.42, .3, .6, 1)) @ Matrix.Translation((0, 0, .5)))
    me = bpy.data.meshes.new("pubk%d" % i); bm.to_mesh(me); bm.free(); me.materials.append(mm); koerper_me.append(me)
kopf_me = []
for i, mm in enumerate(haut_pub):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=1, radius=.12, matrix=Matrix.Translation((0, 0, .75)))
    me = bpy.data.meshes.new("pubh%d" % i); bm.to_mesh(me); bm.free(); me.materials.append(mm); kopf_me.append(me)
rp = random.Random(3)
PUB = []
for s_ in range(0, STUF, 1):
    rr = 1 + (s_ + .5) * .012; hz = 1.0 + (s_ + .5) * 1.1
    for j in range(0, 380):
        a = 2 * P * (j + rp.random() * .6) / 380
        p = Vector((MITTE.x + RA * rr * math.cos(a), MITTE.y + RB * rr * math.sin(a), hz - .05))
        if rp.random() < .12:
            continue
        for me_ in (rp.choice(koerper_me), rp.choice(kopf_me)):
            o = bpy.data.objects.new("pub", me_); sc.collection.objects.link(o); o.location = p
            o.rotation_euler = (0, 0, a + P / 2 + P / 2 + rp.uniform(-.3, .3)); PUB.append(o)
# Blitzlichter im Publikum (werden zufaellig ein/aus geschaltet)
blitz_m = emis("blitz", "ffffff", 60)
BLITZ = []
for i in range(160):
    s_ = rp.randrange(STUF); a = rp.uniform(0, 2 * P); rr = 1 + (s_ + .5) * .012
    o = box("blitz", (.08, .08, .08), (MITTE.x + RA * rr * math.cos(a), MITTE.y + RB * rr * math.sin(a), 1.0 + (s_ + .5) * 1.1 + .9), blitz_m, 0)
    o["ph"] = rp.random(); BLITZ.append(o)
# Dachring + Flutlichtbaender
dach_m = mat("dach", "d9dde2", .5)
bm = bmesh.new(); ring_i, ring_a = [], []
for j in range(NRG):
    a = 2 * P * j / NRG
    ring_i.append(bm.verts.new((MITTE.x + RA * 1.12 * math.cos(a), MITTE.y + RB * 1.12 * math.sin(a), 36)))
    ring_a.append(bm.verts.new((MITTE.x + RA * 1.55 * math.cos(a), MITTE.y + RB * 1.55 * math.sin(a), 40)))
for j in range(NRG):
    bm.faces.new((ring_i[j], ring_i[(j + 1) % NRG], ring_a[(j + 1) % NRG], ring_a[j]))
me = bpy.data.meshes.new("dach"); bm.to_mesh(me); bm.free(); dach = bpy.data.objects.new("dach", me); sc.collection.objects.link(dach)
me.materials.append(dach_m); dach.modifiers.new("d", "SOLIDIFY").thickness = .8
fl_m = emis("flutlicht", "fff6e8", 40)
for j in range(0, NRG, 4):
    a = 2 * P * j / NRG
    box("fluter", (2.4, 2.4, .25), (MITTE.x + RA * 1.14 * math.cos(a), MITTE.y + RB * 1.14 * math.sin(a), 35.6), fl_m, 0)
for (x_, y_) in ((-10, -20), (50, -25), (110, -20), (50, 60), (-20, 30), (120, 30)):
    bpy.ops.object.light_add(type="AREA", location=(x_, y_, 34)); L = bpy.context.object; L.data.size = 18; L.data.energy = 120000
    L.rotation_euler = (Vector((50, 6, 0)) - L.location).to_track_quat("-Z", "Y").to_euler(); L.data.color = (1, .97, .92)
# Anzeigetafel (ohne Text) + Banner
box("tafel", (24, 1, 10), (MITTE.x + RA * 1.08, MITTE.y, 28), mat("tafel", "0b0b0b", .3), .1)
box("tafel_bild", (22, .2, 8.4), (MITTE.x + RA * 1.08 - .6, MITTE.y, 28), emis("tafellicht", "2a4c9c", 2.0), 0)
# Nachthimmel
w = bpy.data.worlds.new("welt"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (*hexf("0a1222"), 1); w.node_tree.nodes["Background"].inputs[1].default_value = .6

# ======================================================================  Rennen
def weg(t, vmax, tau, reakt=.15):
    t = max(0, t - reakt); return vmax * (t - tau * (1 - math.exp(-t / tau)))


def kalib(ziel):
    v = 12.0
    for _ in range(40):
        v *= 100 / weg(ziel, v, 1.25)
    return v


ZIELE = [9.93, 10.03, 9.71, 9.58, 9.84, 9.93, 10.00, 10.00]
VMAX = [kalib(z) for z in ZIELE]


def pos_laeufer(i, t):
    if t < T0:
        return 0.0
    tt = t - T0; z = ZIELE[i]
    if tt <= z:
        return weg(tt, VMAX[i], 1.25)
    v_end = (weg(z, VMAX[i], 1.25) - weg(z - .05, VMAX[i], 1.25)) / .05
    k = min(tt - z, 3.0); return 100 + v_end * k - .5 * 3.2 * k * k


def pose_lauf(m, ph, kraft=1.0):
    s = math.sin(ph); c = math.cos(ph)
    m.dreh("upperleg01.L", x=-.95 * s * kraft - .35); m.dreh("upperleg01.R", x=.95 * s * kraft - .35)
    m.dreh("lowerleg01.L", x=.4 + 1.1 * max(0, c) * kraft); m.dreh("lowerleg01.R", x=.4 + 1.1 * max(0, -c) * kraft)
    m.dreh("foot.L", x=-.3 * s); m.dreh("foot.R", x=.3 * s)
    m.dreh("upperarm01.L", z=-.65, x=1.0 * s * kraft + .2); m.dreh("upperarm01.R", z=.65, x=-1.0 * s * kraft + .2)
    m.dreh("lowerarm01.L", x=-1.45); m.dreh("lowerarm01.R", x=-1.45)
    m.dreh("spine03", x=.12 * kraft); m.dreh("neck01", x=-.1)


START = {"marks": (1.25, .40, -1.9, 2.3, -1.25, 2.4, 1.2), "set": (1.15, .62, -1.55, 1.6, -.85, 1.15, 1.1)}


def pose_start(m, art):
    """Rumpf nach vorne gekippt (Rig-Drehung), Beine angewinkelt, Arme senkrecht zum Boden."""
    lean, hz, ulL, llL, ulR, llR, arm = START[art]
    m.rig.location.z = hz; m.rig.rotation_euler = (lean, 0, P / 2)
    m.dreh("upperleg01.L", x=ulL); m.dreh("lowerleg01.L", x=llL); m.dreh("upperleg01.R", x=ulR); m.dreh("lowerleg01.R", x=llR)
    m.dreh("upperarm01.L", z=-.55, x=arm); m.dreh("upperarm01.R", z=.55, x=arm)
    m.dreh("neck01", x=.15)


def figuren(t):
    for i, m in enumerate(SPR):
        m.zuruecksetzen(); y_ = (i + 1.5) * BB
        x = pos_laeufer(i, t)
        if t < 8.7:                       # vor dem Start: lockern/stehen hinter den Bloecken
            m.rig.location = (-2.2 + .1 * math.sin(t + i), y_, 0); m.rig.rotation_euler = (0, 0, P / 2)
            m.dreh("upperarm01.L", z=-.66 + .05 * math.sin(t * 2 + i)); m.dreh("upperarm01.R", z=.66)
            m.dreh("neck01", z=.2 * math.sin(t * .7 + i)); continue
        if t < T0:
            art = "marks" if t < 11.56 else "set"
            m.rig.location = (-1.05, y_, 0); pose_start(m, art); continue
        tt = t - T0
        kraft = min(1, .55 + tt * .5)
        if x > 100 + 1:
            kraft = max(.3, kraft - (x - 101) * .05)
        ph = (x / 2.44) * P                    # ca. 41 Schritte auf 100 m
        lean = 1.0 * math.exp(-tt / .75) + .08
        m.rig.location = (x - .3, y_, .02 + .04 * abs(math.sin(ph)) - .25 * (1 - math.exp(-tt / .25)) * math.exp(-tt / .6)); m.rig.rotation_euler = (lean, 0, P / 2)
        pose_lauf(m, ph, kraft)
    # Jubel des Helden nach dem Ziel
    if t >= 23.38:
        m = HELD; m.zuruecksetzen(); k = ease((t - 23.4) / .7)
        m.rig.location = (106, (3 + 1.5) * BB, 0); m.rig.rotation_euler = (0, 0, P / 2 + 1.2)
        m.dreh("upperarm01.L", z=-.65 + 2.3 * k, x=.2); m.dreh("upperarm01.R", z=.65 - 2.3 * k, x=.2)
        m.dreh("lowerarm01.L", x=-.2); m.dreh("lowerarm01.R", x=-.2); m.dreh("neck01", x=-.4 * k)
    bpy.context.view_layer.update()


def punkt(m, bone, v):
    pb = m.rig.pose.bones[bone]; bn = m.rig.data.bones[bone]
    return m.rig.matrix_world @ pb.matrix @ bn.matrix_local.inverted() @ Vector(v)


bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam
cam.data.clip_start = .03; cam.data.clip_end = 2000; cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
cam.data.dof.use_dof = True
HK = HELD.gm("joint-head"); HY = (3 + 1.5) * BB
# Einstellungen: (von, bis, typ, a, b, linse); typ "kopf"/"held" relativ zum Helden, "frei" absolut (pos0, ziel0, pos1, ziel1)
SZ = [
    (0.00, 2.08, "held", (11, -1.2, .4), (8, -1.0, .5), 70),
    (2.08, 5.42, "frei", ((-14, HY - 1.0, 1.4), (100, HY, .6), (-13, HY - .8, 1.3), (100, HY, .6)), 26),
    (5.42, 8.70, "frei", ((70, -32, 28), (40, 25, 0), (55, -36, 27), (40, 25, 0)), 22),
    (8.70, 10.50, "frei", ((-1.6, -2.2, .35), (-1.0, 8, .3), (-1.6, -1.8, .3), (-1.0, 8, .3)), 24),
    (10.50, 11.56, "frei", ((.9, HY - .9, .35), (-.05, HY, .15), (.85, HY - .8, .32), (-.05, HY, .15)), 40),
    (11.56, 12.38, "frei", ((-1.0, HY - 2.6, .55), (-.9, HY, .6), (-1.0, HY - 2.5, .55), (-.9, HY, .6)), 35),
    (12.38, 13.50, "frei", ((4.5, HY + .2, .25), "H", (4.5, HY + .2, .25), "H"), 26),
    (13.50, 16.26, "held", (0, -4.2, 1.0), (0, -4.2, 1.0), 30),
    (16.26, 18.12, "held", (14, -.6, 1.2), (9, -.4, 1.2), 85),
    (18.12, 21.24, "held", (2.0, -3.0, .5), (1.2, -3.0, .6), 26),
    (21.24, 23.38, "frei", ((101.8, -3.2, 1.0), (99.8, HY, .9), (101.8, -3.2, 1.0), (99.8, HY, .9)), 35),
    (23.38, 25.26, "frei", ((109.5, HY - 2.6, 1.4), "H", (109, HY - 2.4, 1.5), "H"), 32),
    (25.26, 28.70, "frei", ((112, HY - 1.5, 1.2), (40, HY, .5), (118, HY - 1, 5), (40, HY, .5)), 26),
]


def zustand(t):
    for s in SZ:
        if s[0] <= t < s[1]:
            break
    k = (t - s[0]) / (s[1] - s[0]); k = ease(k) * .8 + k * .2
    figuren(18.4 + t * .45 if t < 2.08 else t)      # Aufhaenger: Zeitlupe mitten aus dem Rennen
    kopf = punkt(HELD, "head", HK + Vector((0, -.04, .02)))
    if s[2] == "kopf":
        pos = kopf + lerpv(s[3], s[4], k); ziel = kopf
    elif s[2] == "held":
        hb = HELD.rig.location + Vector((0, 0, 1.0)); pos = hb + lerpv(s[3], s[4], k); ziel = hb + Vector((0, 0, .1))
    else:
        p0, z0, p1, z1 = s[3]; pos = lerpv(p0, p1, k)
        ziel = (HELD.rig.location + Vector((0, 0, .9))) if z0 == "H" else lerpv(z0, z1, k)
    cam.location = pos; d = ziel - pos; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = s[-1]; cam.data.dof.focus_distance = d.length; cam.data.dof.aperture_fstop = 2.8 if d.length < 6 else 8
    cam.location += Vector((.004 * math.sin(t * 7), .003 * math.cos(t * 5), .004 * math.sin(t * 9))) * min(d.length, 6)
    wagen.location.x = HELD.rig.location.x if 13.5 <= t < 21.24 else 0
    # Blitzlichter: waehrend des Rennens viel, sonst wenig
    rate = .25 if T0 <= t < 24 else .05
    for o in BLITZ:
        ph = (t * 3.0 + o["ph"] * 97) % 1
        o.hide_render = not (ph < rate * .3)


os.makedirs(A.ordner, exist_ok=True)
N = int(round(D * A.fps))
liste = [int(round(float(x) * A.fps)) for x in A.nur.split(",")] if A.nur else list(range(A.start, N))
for f in liste:
    pfad = os.path.join(A.ordner, f"sprint_{f:04d}.png")
    if os.path.exists(pfad) and not A.nur:
        continue
    zustand(f / A.fps); bpy.context.view_layer.update(); zustand(f / A.fps)
    sc.render.filepath = pfad
    bpy.ops.render.render(write_still=True); print("FERTIG", pfad, flush=True)
