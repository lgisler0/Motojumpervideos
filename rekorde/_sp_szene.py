# ======================================================================  Materialien, Himmel, Sonne
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; nt = w.node_tree
env = nt.nodes.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(os.path.join(ASSET, "tag.hdr"))
nt.links.new(env.outputs[0], nt.nodes["Background"].inputs[0]); nt.nodes["Background"].inputs[1].default_value = 1.0
bpy.ops.object.light_add(type="SUN", rotation=(math.radians(48), 0, math.radians(-140))); sonne = bpy.context.object
sonne.data.energy = 4.0; sonne.data.angle = math.radians(1.0); sonne.data.color = (1, .96, .9)
STAHL = pbr("stahl", "Metal012", 6, rau_mul=.6, rau_add=.15, metal=1.0)
BETON = pbr("beton", "Concrete034", .3, tint="b4afa6")
WEISS_M = mat("linie_weiss", "f4f4f2", .6)
TARTAN = mat("tartan", "a8402c", .8)
TARTAN_RW = mat("tartan_anlauf", "9a3826", .8)
RASEN = pbr("rasen", "Grass004", .35, tint="7fae5a")
# Maehstreifen im Rasen
nt_r = RASEN.node_tree
mxn = [n for n in nt_r.nodes if n.type == "MIX"][0]
tc_ = nt_r.nodes.new("ShaderNodeTexCoord"); sp_ = nt_r.nodes.new("ShaderNodeSeparateXYZ"); nt_r.links.new(tc_.outputs["Object"], sp_.inputs[0])
pp_ = nt_r.nodes.new("ShaderNodeMath"); pp_.operation = "PINGPONG"; pp_.inputs[1].default_value = 5.25; nt_r.links.new(sp_.outputs["X"], pp_.inputs[0])
lt_ = nt_r.nodes.new("ShaderNodeMath"); lt_.operation = "LESS_THAN"; lt_.inputs[1].default_value = 2.625; nt_r.links.new(pp_.outputs[0], lt_.inputs[0])
cm_ = nt_r.nodes.new("ShaderNodeMix"); cm_.data_type = "RGBA"; nt_r.links.new(lt_.outputs[0], cm_.inputs[0])
cm_.inputs[6].default_value = (*hexf("6f9f4c"), 1); cm_.inputs[7].default_value = (*hexf("8fbf66"), 1); nt_r.links.new(cm_.outputs[2], mxn.inputs[7])

# ======================================================================  Stadion: Rundbahn um STAD, Anlauf, Sektor
STAD = Vector((60.0, 0, 0)); GER = 84.39 / 2; R_IN = 36.5; BAHN = 9.76


def oval_pt(i, n_g, n_k, R):
    """Punkt i auf der Ovalbahn mit Radius R (vom Kurvenmittelpunkt)"""
    N = 2 * n_g + 2 * n_k
    i = i % N
    if i < n_g:
        return Vector((STAD.x - GER + 2 * GER * i / n_g, -R, 0))
    i -= n_g
    if i < n_k:
        a = -P / 2 + P * i / n_k; return Vector((STAD.x + GER + R * math.cos(a), R * math.sin(a), 0))
    i -= n_k
    if i < n_g:
        return Vector((STAD.x + GER - 2 * GER * i / n_g, R, 0))
    i -= n_g
    a = P / 2 + P * i / n_k; return Vector((STAD.x - GER + R * math.cos(a), R * math.sin(a), 0))


def oval_band(name, r0, r1, z, m, n_g=24, n_k=64):
    bm = bmesh.new(); N = 2 * n_g + 2 * n_k
    a = [bm.verts.new(oval_pt(i, n_g, n_k, r0) + Vector((0, 0, z))) for i in range(N)]
    b = [bm.verts.new(oval_pt(i, n_g, n_k, r1) + Vector((0, 0, z))) for i in range(N)]
    for i in range(N):
        bm.faces.new((a[i], a[(i + 1) % N], b[(i + 1) % N], b[i]))
    me_ = bpy.data.meshes.new(name); bm.to_mesh(me_); bm.free(); me_.materials.append(m)
    o = bpy.data.objects.new(name, me_); sc.collection.objects.link(o); return o


box("umland", (900, 700, .2), STAD + Vector((0, 0, -.12)), mat("umland_gras", "5f7f45", .9), 0)
# Umgebung: Baeume, Haeuser, Parkplatz (Jena)
UM = Sammler(); ru = random.Random(21)
LAUB = [mat("laub%d" % i, f, .8) for i, f in enumerate(("3f6a2e", "4d7a34", "355c28"))]; STAMM = mat("stamm", "4a3a2a", .9)
DACH = [mat("dach%d" % i, f, .7) for i, f in enumerate(("8a3a2a", "5a5f66", "7a4a32"))]
WAND = [mat("hauswand%d" % i, f, .8) for i, f in enumerate(("e2dccd", "cfc6b4", "f0ece2", "bdb6a8"))]
for i in range(420):
    a = ru.uniform(0, 2 * P); r = ru.uniform(105, 260)
    p_ = STAD + Vector((r * math.cos(a) * 1.25, r * math.sin(a), 0))
    if abs(p_.y) < 70 and -60 < p_.x < 0:
        continue
    h = ru.uniform(7, 15)
    UM.zyl(.25, h * .4, p_ + Vector((0, 0, h * .2)), STAMM, v=6)
    lb = ru.choice(LAUB)
    for kk in range(3):
        UM.kugel(h * ru.uniform(.2, .28), p_ + Vector((ru.uniform(-.8, .8), ru.uniform(-.8, .8), h * (.55 + .15 * kk))), lb, skala=(1, 1, .85))
for i in range(90):
    a = ru.uniform(0, 2 * P); r = ru.uniform(230, 330)
    p_ = STAD + Vector((r * math.cos(a) * 1.2, r * math.sin(a), 0)); w_, l_, h = ru.uniform(10, 22), ru.uniform(12, 40), ru.uniform(8, 22)
    UM.box((w_, l_, h), p_ + Vector((0, 0, h / 2)), ru.choice(WAND), rot=(0, 0, a))
    UM.box((w_ + .6, l_ + .6, 1.2), p_ + Vector((0, 0, h + .6)), ru.choice(DACH), rot=(0, 0, a))
UM.box((60, 40, .05), STAD + Vector((0, -125, .02)), mat("parkplatz", "3a3b3e", .9))
AUTO = [mat("auto%d" % i, f, .3, Coat_Weight=.8) for i, f in enumerate(("c62828", "1565c0", "e6e6e6", "212121", "8a8f96"))]
for i in range(8):
    for j in range(14):
        if ru.random() < .3:
            continue
        p_ = STAD + Vector((-26 + j * 4.0, -140 + i * 4.5 + (1 if i % 2 else 0), 0))
        mm = ru.choice(AUTO); UM.box((1.8, 4.3, .8), p_ + Vector((0, 0, .55)), mm); UM.box((1.6, 2.4, .6), p_ + Vector((0, -.2, 1.2)), mm)
UM.fertig("umgebung", bevel=.04)
oval_band("innenraum", .01, R_IN, .0, RASEN, n_k=96)
oval_band("bahn", R_IN, R_IN + BAHN, .01, TARTAN, n_k=96)
oval_band("bahn_aussen", R_IN + BAHN, R_IN + BAHN + 4, .01, TARTAN, n_k=96)
for k in range(9):
    oval_band("bahnlinie%d" % k, R_IN + k * 1.22 - .025, R_IN + k * 1.22 + .025, .016, WEISS_M, n_k=96)
oval_band("bord", R_IN - .12, R_IN, .05, mat("bord", "e8e8e6", .5), n_k=96)
# Fussballfeld-Linien
SM = Sammler()
FW, FH = 105.0, 68.0
for (sx, sy, x, y) in ((FW, .12, 0, -FH / 2), (FW, .12, 0, FH / 2), (.12, FH, -FW / 2, 0), (.12, FH, FW / 2, 0), (.12, FH, 0, 0)):
    SM.box((sx, sy, .01), STAD + Vector((x, y, .012)), WEISS_M)
for sgn in (-1, 1):
    for (sx, sy, dx) in ((16.5, .12, 8.25), (.12, 40.3, 16.5)):
        if sy > 1:
            SM.box((sx, sy, .01), STAD + Vector((sgn * (FW / 2 - dx), 0, .012)), WEISS_M)
        else:
            for yy in (-20.15, 20.15):
                SM.box((sx, sy, .01), STAD + Vector((sgn * (FW / 2 - dx), yy, .012)), WEISS_M)
for k in range(72):
    a = 2 * P * k / 72; a2 = 2 * P * (k + 1) / 72
    SM.rohr(STAD + Vector((9.15 * math.cos(a), 9.15 * math.sin(a), .012)), STAD + Vector((9.15 * math.cos(a2), 9.15 * math.sin(a2), .012)), .06, WEISS_M, v=4)
# Anlauf (x von -34 bis 0) mit Seitenlinien, Abwurfbogen, Sektor
box("anlauf", (34.0, 4.0, .03), Vector((-17.0, 0, .02)), TARTAN_RW, 0)
for sy in (-1, 1):
    SM.box((34.0, .05, .01), Vector((-17.0, sy * 2.0, .04)), WEISS_M)
C_ARC = Vector((-8.0, 0, 0))
for k in range(20):
    a = -.22 + .44 * k / 20; a2 = -.22 + .44 * (k + 1) / 20
    SM.box((.08, .1, .02), C_ARC + Vector((8 * math.cos(a), 8 * math.sin(a), .04)), WEISS_M, rot=(0, 0, a))
    SM.rohr(C_ARC + Vector((8 * math.cos(a), 8 * math.sin(a), .045)), C_ARC + Vector((8 * math.cos(a2), 8 * math.sin(a2), .045)), .035, WEISS_M, v=4)
SEKTOR = math.radians(28.96) / 2
for sgn in (-1, 1):
    d = Vector((math.cos(SEKTOR), sgn * math.sin(SEKTOR), 0))
    SM.rohr(C_ARC + d * 8 + Vector((0, 0, .02)), C_ARC + d * 110 + Vector((0, 0, .02)), .03, WEISS_M, v=4)
SCHILD_W = mat("distanzschild", "f6f6f4", .5)
for dist in range(50, 101, 10):
    r = dist + 8
    for k in range(30):
        a = -SEKTOR + 2 * SEKTOR * k / 30; a2 = -SEKTOR + 2 * SEKTOR * (k + 1) / 30
        SM.rohr(C_ARC + Vector((r * math.cos(a), r * math.sin(a), .02)), C_ARC + Vector((r * math.cos(a2), r * math.sin(a2), .02)), .025, WEISS_M, v=4)
SM.fertig("linien")
# Distanzschilder (aufgestellte Tafeln) an beiden Sektorrändern
for dist in range(50, 101, 10):
    r = dist + 8
    for sgn in (-1, 1):
        a = sgn * (SEKTOR + .015)
        p_ = C_ARC + Vector((r * math.cos(a), r * math.sin(a), 0))
        bpy.ops.object.text_add(location=p_ + Vector((0, 0, .45)), rotation=(P / 2, 0, -P / 2 + .5 * sgn * 0)); t_ = bpy.context.object
        t_.data.body = str(dist); t_.data.size = .5; t_.data.align_x = "CENTER"; t_.data.extrude = .01
        t_.data.materials.append(mat("schildzahl", "1a1a1a", .5) if not bpy.data.materials.get("schildzahl") else bpy.data.materials["schildzahl"])
        t_.location = p_ + Vector((-.06, 0, .35)); t_.rotation_euler = (P / 2, 0, -P / 2)
        box("distanztafel", (.06, .9, .7), p_ + Vector((0, 0, .5)), SCHILD_W, .01)
        rohr("tafelfuss", p_, p_ + Vector((0, 0, .15)), .02, STAHL)

# ======================================================================  Tribuenen mit echten (gebackenen) Zuschauern
SITZ_M = [mat("sitz%d" % i, f, .4) for i, f in enumerate(("1565c0", "c62828", "f9a825", "e6e6e6"))]
ST = Sammler()
REIHEN = 16
PLAETZE = []          # (pos, blick)
for sgn in (-1, 1):
    y0 = sgn * (R_IN + BAHN + 6.0)
    for r in range(REIHEN):
        y = y0 + sgn * r * .85; z = 1.2 + r * .45
        ST.box((2 * GER + 12, .85, z), Vector((STAD.x, y, z / 2)), BETON)
        ST.box((2 * GER + 12, .45, .12), Vector((STAD.x, y + sgn * .15, z + .32)), SITZ_M[(r // 4) % 4])
        x = STAD.x - GER - 5
        while x < STAD.x + GER + 5:
            PLAETZE.append((Vector((x, y + sgn * .05, z)), P if sgn < 0 else 0.0))
            x += .62
    ST.box((2 * GER + 14, .3, 3.2), Vector((STAD.x, y0 + sgn * (REIHEN * .85 + .2), 1.2 + REIHEN * .45 + 1.6)), BETON)
    # Dach
    zt = 1.2 + REIHEN * .45 + 6.5
    ST.box((2 * GER + 16, REIHEN * .85 + 6, .4), Vector((STAD.x, y0 + sgn * (REIHEN * .85 / 2 + 1.0), zt)), mat("dach", "d8dade", .4, metal=.4))
    for k in range(8):
        ST.rohr(Vector((STAD.x - GER - 6 + k * (2 * GER + 12) / 7, y0 + sgn * (REIHEN * .85 + .2), 0)),
                Vector((STAD.x - GER - 6 + k * (2 * GER + 12) / 7, y0 + sgn * (REIHEN * .85 + .2), zt)), .25, STAHL)
# Kurventribuenen (West hinter dem Anlauf und Ost hinter der Anzeigetafel): nur Stufen + Publikum
for cx_, a0, a1 in ((STAD.x - GER, P / 2 + .25, 3 * P / 2 - .25), (STAD.x + GER, -P / 2 + .25, P / 2 - .25)):
    for r in range(10):
        R = R_IN + BAHN + 8 + r * .85; z = 1.2 + r * .45
        n = int((a1 - a0) * R / 1.2)
        for k in range(n):
            a = a0 + (a1 - a0) * (k + .5) / n
            ST.box((.85, 1.25, z), Vector((cx_ + R * math.cos(a), R * math.sin(a), z / 2)), BETON, rot=(0, 0, a))
            if (k + r) % 2 == 0:
                PLAETZE.append((Vector((cx_ + R * math.cos(a), R * math.sin(a), z)), a - P / 2))
ST.fertig("tribuenen")
rz = random.Random(7)
PUBLIKUM = []
for i, (p_, blick) in enumerate(PLAETZE):
    if rz.random() > .62:
        continue
    o = bpy.data.objects.new("zs_%d" % i, rz.choice(ZUSCH_ME)); sc.collection.objects.link(o)
    o.location = p_ + Vector((0, 0, -.45)); o.rotation_euler = (0, 0, blick + rz.uniform(-.3, .3)); s_ = rz.uniform(.95, 1.03); o.scale = (s_, s_, s_)
    PUBLIKUM.append((o, o.location.z, rz.uniform(0, 6)))
print("publikum", len(PUBLIKUM))
# Kampfrichter am Sektor (stehende Menschen, keine Tribuene)
for (x, y, b) in ((88, 9, P), (100, -11, P / 2 + .3), (-1.5, 4.0, -P / 2 - .4), (60, 14, P)):
    o = bpy.data.objects.new("richter", ZUSCH_ME[(int(x) + 3) % len(ZUSCH_ME)]); sc.collection.objects.link(o)
    o.location = (x, y, 0); o.rotation_euler = (0, 0, b)

# Flutlichtmasten
FL = emis("flutlicht", "fff6e0", 3.0)
for sx in (-1, 1):
    for sy in (-1, 1):
        p_ = Vector((STAD.x + sx * (GER + 30), sy * (R_IN + BAHN + 24), 0))
        rohr("mast", p_, p_ + Vector((0, 0, 46)), .7, STAHL)
        box("strahlerfeld", (1.0, 7, 4), p_ + Vector((0, 0, 47)), FL, .05, rot=(0, -.5 * sx * 0, 0))

# Anzeigetafel (Ost) - vor dem Wurf "JAVELIN", danach 98.48
TAF = Vector((STAD.x + GER + R_IN + BAHN + 10, 0, 0))
p_a = os.path.join(HIER, "_sp_tafel_a.png"); p_b = os.path.join(HIER, "_sp_tafel_b.png")
ME.logo_bild(p_a, "JAVELIN", farbe=(1, .85, .2), symbol=False, hintergrund=(.02, .02, .04), unterzeile="MEN  -  JENA 1996", breite=1024, hoehe=512)
ME.logo_bild(p_b, "98.48", farbe=(1, .85, .2), symbol=False, hintergrund=(.02, .02, .04), unterzeile="ZELEZNY (CZE)  WR", breite=1024, hoehe=512)
TAFELN = []
for p_img in (p_a, p_b):
    bpy.ops.mesh.primitive_plane_add(size=1, location=TAF + Vector((-.36, 0, 12))); t_ = bpy.context.object; t_.scale = (20, 10, 1); t_.rotation_euler = (P / 2, 0, -P / 2)
    m_ = bpy.data.materials.new("tafel"); m_.use_nodes = True; ti = m_.node_tree.nodes.new("ShaderNodeTexImage"); ti.image = bpy.data.images.load(p_img)
    bsdf = m_.node_tree.nodes["Principled BSDF"]; m_.node_tree.links.new(ti.outputs[0], bsdf.inputs["Emission Color"]); bsdf.inputs["Emission Strength"].default_value = 3.0
    bsdf.inputs["Base Color"].default_value = (0, 0, 0, 1); t_.data.materials.append(m_); TAFELN.append(t_)
box("tafel_rahmen", (.6, 21, 11), TAF + Vector((0, 0, 12)), mat("tafelrahmen", "15161a", .5), .05)
for sy in (-1, 1):
    rohr("tafel_bein", TAF + Vector((.2, sy * 7, 0)), TAF + Vector((.2, sy * 7, 7)), .45, STAHL)

# ======================================================================  Speer (2,6 m; Spitze vorne +y)
SPEER_M = mat("speer", "c8ccd2", .22, metal=1.0, Coat_Weight=.4)
SPEER = dreh_koerper("speer", [(-1.50, .0), (-1.49, .004), (-1.40, .008), (-.6, .013), (-.10, .0145), (.10, .0145), (.6, .012), (.98, .008), (1.02, .007), (1.10, .0)], SPEER_M, nv=24)
SPEER.rotation_mode = "QUATERNION"
GRIFF = dreh_koerper("speer_griff", [(-.09, .0155), (-.085, .0175), (.085, .0175), (.09, .0155)], mat("griff", "1d2a55", .8), nv=24)
GRIFF.parent = SPEER
SPITZE = dreh_koerper("speer_spitze", [(.98, .0085), (1.0, .0078), (1.10, .0)], mat("spitze", "2a2a2e", .35, metal=.8), nv=24)
SPITZE.parent = SPEER
# Rasenstuecke beim Einstich
KLUMPEN = []
rk = random.Random(3)
for i in range(7):
    o = box("klumpen", (.05, .04, .03), (0, 0, -5), mat("erde", "4a3a28", .9), .01)
    KLUMPEN.append((o, Vector((rk.uniform(-1.5, 1.5), rk.uniform(-1.2, 1.2), rk.uniform(1.5, 3.0)))))
print("ok szene")
