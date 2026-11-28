# ======================================================================  Himmel, Sonne
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; nt = w.node_tree
env = nt.nodes.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(os.path.join(ASSET, "tag.hdr"))
nt.links.new(env.outputs[0], nt.nodes["Background"].inputs[0]); nt.nodes["Background"].inputs[1].default_value = 1.0
bpy.ops.object.light_add(type="SUN", rotation=(math.radians(50), 0, math.radians(-120))); sonne = bpy.context.object
sonne.data.energy = 4.0; sonne.data.angle = math.radians(1.0); sonne.data.color = (1, .97, .92)
sc.view_settings.exposure = -.35
STAHL = pbr("stahl", "Metal012", 6, rau_mul=.6, rau_add=.15, metal=1.0)


def sstep(a, b, x):
    t = min(1, max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t)


# ======================================================================  Pistenprofil: Winkel ueber x, Hoehe, Bogenlaenge
def winkel(x):
    if x < 40:
        a = 44
    elif x < 130:
        a = 44 - 11 * sstep(40, 130, x)
    elif x < 460:
        a = 33 - 6 * sstep(130, 460, x)
    elif x < 640:
        a = 27 - 7 * sstep(460, 640, x)
    elif x < 780:
        a = 20 - 20 * sstep(640, 780, x)
    else:
        a = -6 * sstep(780, 900, x)
    return math.radians(a)


DX = .5
XS = [i * DX for i in range(int(1100 / DX) + 1)]
ZS = [0.0]; SS = [0.0]
for i in range(1, len(XS)):
    a = winkel(XS[i] - DX / 2)
    ZS.append(ZS[-1] - math.tan(a) * DX); SS.append(SS[-1] + DX / math.cos(a))
Z0 = -min(ZS) + 0.0
ZS = [z + 0 for z in ZS]


def z_kurs(x):
    if x <= 0:
        return ZS[0] + math.tan(winkel(0)) * (-x) * .8
    i = min(len(XS) - 2, int(x / DX)); f = (x - XS[i]) / DX
    return ZS[i] * (1 - f) + ZS[i + 1] * f


def x_von_s(s):
    lo, hi = 0, len(SS) - 1
    while hi - lo > 1:
        m = (lo + hi) // 2
        if SS[m] < s:
            lo = m
        else:
            hi = m
    f = (s - SS[lo]) / max(1e-6, SS[hi] - SS[lo])
    return XS[lo] + f * DX


def kurs(s):
    """Punkt, Laufrichtung, Normale der Piste bei Bogenlaenge s"""
    x = x_von_s(max(0.0, s)) if s >= 0 else s * math.cos(winkel(0))
    p = Vector((x, 0, z_kurs(x)))
    a = winkel(max(0.0, x))
    fw = Vector((math.cos(a), 0, -math.sin(a))); nr = Vector((math.sin(a), 0, math.cos(a)))
    return p, fw, nr


S_FALLE = 575.0                   # Lichtschranke (Speed trap)

# ======================================================================  Gelaende: Couloir mit Graten, Berge rundherum
_rf = random.Random(77)
OKT = [(_rf.uniform(0, 6.3), math.cos(a_), math.sin(a_), 2.0 ** k) for k in range(7) for a_ in (_rf.uniform(0, 6.3),)]


def fbm(x, y, amp):
    z = 0.0
    for ph, cx, sy, fr in OKT:
        u = (x * cx + y * sy) * fr / 60.0 + ph
        z += amp / fr * (1 - abs(math.sin(u)))
    return z - amp * .9


def gelaende(x, y):
    zc = z_kurs(min(max(x, -150), 1100))
    ay = abs(y)
    breite = 30 + 15 * sstep(500, 800, x)
    grat = 55 * sstep(breite, breite + 45, ay) + 25 * sstep(breite + 45, breite + 140, ay)
    rau = fbm(x, y, 9.0) * sstep(breite - 4, breite + 25, ay) + .25 * fbm(x * 3, y * 3, 2.0)
    hinten = 60 * sstep(0, -120, x)
    return zc + grat + rau + hinten


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


def schnee_fels_mat(name, schnee_skala=.3):
    m = pbr(name, "Snow006", schnee_skala, tint="eef3fa", normal=.6)
    nt_ = m.node_tree; n = nt_.nodes; l = nt_.links; b = n["Principled BSDF"]
    basis = b.inputs["Base Color"].links[0].from_socket
    geo = n.new("ShaderNodeNewGeometry"); sp = n.new("ShaderNodeSeparateXYZ"); l.new(geo.outputs["Normal"], sp.inputs[0])
    st = n.new("ShaderNodeMapRange"); st.inputs[1].default_value = .55; st.inputs[2].default_value = .7; l.new(sp.outputs["Z"], st.inputs[0])
    no = n.new("ShaderNodeTexNoise"); no.inputs["Scale"].default_value = .08; no.inputs["Detail"].default_value = 10; l.new(geo.outputs["Position"], no.inputs["Vector"])
    fels = n.new("ShaderNodeMix"); fels.data_type = "RGBA"; l.new(no.outputs["Fac"], fels.inputs[0])
    fels.inputs[6].default_value = (*hexf("3a3632"), 1); fels.inputs[7].default_value = (*hexf("5f5a53"), 1)
    mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; l.new(st.outputs[0], mx.inputs[0]); l.new(fels.outputs[2], mx.inputs[6]); l.new(basis, mx.inputs[7])
    l.new(mx.outputs[2], b.inputs["Base Color"])
    b.inputs["Subsurface Weight"].default_value = .1
    return m


SCHNEE = schnee_fels_mat("schnee_fels")
hoehenfeld("couloir", -160, 1100, -260, 260, 3.0, gelaende, SCHNEE)


def berge(x, y):
    d = math.hypot((x - 450) / 1.3, y)
    base = z_kurs(min(max(x, -150), 1100)) if -150 < x < 1100 and abs(y) < 260 else -300
    h = 300 * sstep(600, 1800, d) + 380 * (math.sin(x / 310) * math.sin(y / 270) + 1) * sstep(800, 2200, d)
    if -150 < x < 1100 and abs(y) < 260:
        return base - 60
    return -350 + h + fbm(x / 6, y / 6, 160)


hoehenfeld("berge", -3200, 4000, -3600, 3600, 60.0, berge, schnee_fels_mat("berge_m", .05))
# Talboden weit unten
box("tal", (20000, 20000, .5), (450, 0, -420), mat("tal", "dfe6ee", .6), 0)
# Lärchen/Tannen im Tal und an den Hängen unten (rund)
BW = Sammler(); rb = random.Random(4)
NADEL = [mat("nadel%d" % i, f, .8) for i, f in enumerate(("2a3a26", "34472c", "223020"))]; STAMM = mat("stamm", "3a2a1e", .9)
for i in range(500):
    x = rb.uniform(600, 1100); y = rb.choice((-1, 1)) * rb.uniform(70, 260)
    z = gelaende(x, y)
    h = rb.uniform(6, 13)
    BW.zyl(.18, h * .3, (x, y, z + h * .15), STAMM, v=6)
    for k in range(3):
        BW.kugel(h * (.22 - .05 * k), (x, y, z + h * (.35 + .22 * k)), rb.choice(NADEL), skala=(1, 1, 1.5), sub=1)
BW.fertig("baeume")

# ======================================================================  Pistenausstattung: Markierungen, Netze, Lichtschranke, Anzeigetafel, Zuschauer
PM = Sammler()
BLAU = mat("farbspur", "1f4fbf", .9); ZWEIG = mat("tannenzweig", "2b4a2a", .9); NETZ = mat("netz", "ff6a00", .7)
s = 0.0
while s < 900:
    p, fw, nr = kurs(s)
    for sy in (-1, 1):
        q = p + Vector((0, sy * 17, 0)); q.z = gelaende(q.x, q.y) + .03
        PM.box((2.0, .35, .02), q, BLAU, rot=(0, math.atan2(-fw.z, fw.x), 0))
        if int(s) % 20 == 0:
            r = p + Vector((0, sy * 22, 0)); r.z = gelaende(r.x, r.y)
            PM.kugel(.35, r + Vector((0, 0, .3)), ZWEIG, skala=(1, 1, 1.4), sub=1)
    s += 2.0
# Querlinie an der Lichtschranke
pt, fwt, nrt = kurs(S_FALLE)
PM.box((.4, 34, .02), pt + Vector((0, 0, .03)), mat("rot_linie", "d01818", .8), rot=(0, math.atan2(fwt.z, fwt.x) * -1, 0))
# Fangnetze unten
for x in range(600, 900, 3):
    for sy in (-1, 1):
        y = sy * (28 + 15 * sstep(500, 800, x)); z = gelaende(x, y)
        PM.box((3.0, .04, 1.6), Vector((x + 1.5, y, z + .8)), NETZ)
        PM.zyl(.04, 1.9, Vector((x, y, z + .95)), STAHL, v=8)
PM.fertig("pistenausstattung")
# Lichtschranken-Portal + Anzeigetafel
for sy in (-1, 1):
    q = pt + Vector((0, sy * 18, 0)); q.z = gelaende(q.x, q.y)
    rohr("portal_pfosten", q, q + Vector((0, 0, 6.5)), .18, STAHL)
pp = pt + Vector((0, 0, 0)); pp.z = max(gelaende(pt.x, 18), gelaende(pt.x, -18)) + 6.5
p_ban = os.path.join(HIER, "_sk_banner.png")
ME.logo_bild(p_ban, "SPEED TRAP", farbe=(1, 1, 1), symbol=False, hintergrund=(.75, .06, .08), breite=1024, hoehe=160)
bpy.ops.mesh.primitive_plane_add(size=1, location=pp); ban = bpy.context.object; ban.scale = (36, 1.6, 1); ban.rotation_euler = (P / 2, 0, P / 2)
mb = bpy.data.materials.new("banner"); mb.use_nodes = True; ti = mb.node_tree.nodes.new("ShaderNodeTexImage"); ti.image = bpy.data.images.load(p_ban)
mb.node_tree.links.new(ti.outputs[0], mb.node_tree.nodes["Principled BSDF"].inputs["Base Color"]); ban.data.materials.append(mb)
ban.rotation_euler = (P / 2, 0, -P / 2)
TAF = pt + Vector((40, -34, 0)); TAF.z = gelaende(TAF.x, TAF.y)
p_a = os.path.join(HIER, "_sk_tafel_a.png"); p_b = os.path.join(HIER, "_sk_tafel_b.png")
ME.logo_bild(p_a, "- - -", farbe=(1, .85, .2), symbol=False, hintergrund=(.02, .02, .04), unterzeile="KM/H", breite=1024, hoehe=512)
ME.logo_bild(p_b, "255.50", farbe=(1, .85, .2), symbol=False, hintergrund=(.02, .02, .04), unterzeile="KM/H  -  WORLD RECORD", breite=1024, hoehe=512)
TAFELN = []
for p_img in (p_a, p_b):
    bpy.ops.mesh.primitive_plane_add(size=1, location=TAF + Vector((-.48 * .5, .88 * .5, 7))); t_ = bpy.context.object; t_.scale = (10, 5, 1); t_.rotation_euler = (P / 2, 0, P + .5)
    m_ = bpy.data.materials.new("tafel"); m_.use_nodes = True; ti = m_.node_tree.nodes.new("ShaderNodeTexImage"); ti.image = bpy.data.images.load(p_img)
    bsdf = m_.node_tree.nodes["Principled BSDF"]; m_.node_tree.links.new(ti.outputs[0], bsdf.inputs["Emission Color"]); bsdf.inputs["Emission Strength"].default_value = 3.0
    bsdf.inputs["Base Color"].default_value = (0, 0, 0, 1); t_.data.materials.append(m_); TAFELN.append(t_)
box("tafel_rahmen", (10.6, .5, 5.6), TAF + Vector((0, -.2, 7)), mat("tafelrahmen", "15161a", .5), .05, rot=(0, 0, .5))
for sx in (-1, 1):
    rohr("tafel_bein", TAF + Vector((sx * 3.5, .7, -1)), TAF + Vector((sx * 3.5, .7, 4.3)), .15, STAHL)
# Zuschauer im Auslauf (gebacken), hinter den Netzen
rz = random.Random(19); PUBLIKUM = []
for i in range(180):
    x = rz.uniform(650, 860); sy = rz.choice((-1, 1))
    y = sy * (31 + 15 * sstep(500, 800, x) + rz.uniform(.5, 6))
    z = gelaende(x, y)
    o = bpy.data.objects.new("zs_%d" % i, rz.choice(ZUSCH_ME)); sc.collection.objects.link(o)
    o.location = (x, y, z); o.rotation_euler = (0, 0, (P if sy < 0 else 0) + rz.uniform(-.5, .5))
    PUBLIKUM.append((o, z, rz.uniform(0, 6)))
# Starthaus oben
p0, fw0, nr0 = kurs(-4)
box("starthaus", (3, 4, 2.8), p0 + Vector((-3.5, 0, 1.0)), mat("starthaus", "c8ccd2", .5), .05)
box("startdach", (3.6, 4.6, .3), p0 + Vector((-3.5, 0, 2.5)), mat("startdach", "d01818", .5), .05)

# ======================================================================  Skier und Stoecke (bmesh, keine duennen Bevel-Boxen)
SKI_M = mat("ski", "e8e8e8", .25, Coat_Weight=.8); SKI_K = mat("ski_kante", "d01818", .3)
SKIS = []
for sd in ("L", "R"):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1, matrix=Matrix.Diagonal((2.4, .095, .02, 1)))
    for v in bm.verts:                          # Schaufel vorne hoch
        if v.co.x > 1.0:
            v.co.z += .12 * ((v.co.x - 1.0) / .2) ** 2
    me_ = bpy.data.meshes.new("ski_" + sd); bm.to_mesh(me_); bm.free(); me_.materials.append(SKI_M)
    o = bpy.data.objects.new("ski_" + sd, me_); sc.collection.objects.link(o); o.rotation_mode = "QUATERNION"
    SKIS.append(o)
STOECKE = []
for sd in ("L", "R"):
    bm = bmesh.new()
    pts = [Vector((0, 0, 0)), Vector((-.25, 0, -.12)), Vector((-.6, 0, -.2)), Vector((-1.1, 0, -.18))]     # gebogener Rennstock
    for a, b in zip(pts, pts[1:]):
        d = b - a
        bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=.012, radius2=.012, depth=d.length,
                              matrix=Matrix.Translation((a + b) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4())
    me_ = bpy.data.meshes.new("stock_" + sd); bm.to_mesh(me_); bm.free(); me_.materials.append(mat("stock", "222428", .3, metal=.5))
    o = bpy.data.objects.new("stock_" + sd, me_); sc.collection.objects.link(o); o.rotation_mode = "QUATERNION"
    STOECKE.append(o)
# Schneestaub hinter den Skiern
STAUB_M = mat("schneestaub", "f4f7fb", .9, Emission_Color=(1, 1, 1, 1), Emission_Strength=.15)
STAUB = []
for i in range(40):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, location=(0, 0, -900)); o = bpy.context.object; o.data.materials.append(STAUB_M)
    for p in o.data.polygons:
        p.use_smooth = True
    STAUB.append(o)
print("ok szene")
