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
