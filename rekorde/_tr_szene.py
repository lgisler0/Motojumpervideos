# ======================================================================  Materialien, Himmel, Sonne
SCHWARZ = mat("schwarzlack", "0d0d0f", .4, Coat_Weight=.3)
STAHL = pbr("stahl", "Metal012", 6, rau_mul=.6, rau_add=.15, metal=1.0)
BETON = pbr("beton", "Concrete034", .6, tint="a8a49c")
PUTZ = pbr("putz", "PaintedPlaster017", .8, tint="d8d2c4")
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; nt = w.node_tree
env = nt.nodes.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(os.path.join(ASSET, "tag.hdr"))
nt.links.new(env.outputs[0], nt.nodes["Background"].inputs[0]); nt.nodes["Background"].inputs[1].default_value = 1.0


class Sammler:
    """viele Boxen/Zylinder pro Material in ein Mesh (schneller Aufbau)"""
    def __init__(self):
        self.bm = {}

    def _b(self, m, glatt):
        key = (m.name, glatt)
        if key not in self.bm:
            self.bm[key] = (bmesh.new(), m, glatt)
        return self.bm[key][0]

    def box(self, groesse, ort, m, rot=(0, 0, 0)):
        M = Matrix.Translation(Vector(ort)) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((*groesse, 1))
        bmesh.ops.create_cube(self._b(m, False), size=1, matrix=M)

    def zyl(self, r, l, ort, m, rot=(0, 0, 0), v=16):
        M = Matrix.Translation(Vector(ort)) @ Euler(rot).to_matrix().to_4x4()
        bmesh.ops.create_cone(self._b(m, True), cap_ends=True, segments=v, radius1=r, radius2=r, depth=l, matrix=M)

    def rohr(self, a, b, r, m, v=10):
        a, b = Vector(a), Vector(b); d = b - a
        M = Matrix.Translation((a + b) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
        bmesh.ops.create_cone(self._b(m, True), cap_ends=True, segments=v, radius1=r, radius2=r, depth=d.length, matrix=M)

    def fertig(self, name, bevel=0.0):
        obs = []
        for i, (bm, m, glatt) in enumerate(self.bm.values()):
            me_ = bpy.data.meshes.new("%s_%d" % (name, i)); bm.to_mesh(me_); bm.free()
            if glatt:
                for p in me_.polygons:
                    p.use_smooth = True
            me_.materials.append(m)
            o = bpy.data.objects.new("%s_%d" % (name, i), me_); sc.collection.objects.link(o)
            if bevel and not glatt:
                bv = o.modifiers.new("b", "BEVEL"); bv.width = bevel; bv.segments = 2; bv.limit_method = "ANGLE"
            obs.append(o)
        self.bm = {}
        return obs
bpy.ops.object.light_add(type="SUN", rotation=(math.radians(52), 0, math.radians(-35))); sonne = bpy.context.object
sonne.data.energy = 4.2; sonne.data.angle = math.radians(1.0); sonne.data.color = (1, .95, .88)


def streifen_mat(name, grund, fenster, per_x, per_z, br_x, br_z, glanz=.3):
    """Fassade: Raster aus Fenstern (dunkel, spiegelnd) und Pfeilern; per = Rastermass, br = Pfeileranteil"""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt_ = m.node_tree; n = nt_.nodes; l = nt_.links; b = n["Principled BSDF"]
    tc = n.new("ShaderNodeTexCoord"); sp = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Object"], sp.inputs[0])
    hor = n.new("ShaderNodeMath"); hor.operation = "ADD"; l.new(sp.outputs["X"], hor.inputs[0]); l.new(sp.outputs["Y"], hor.inputs[1])
    def raster(src, per, br):
        a = n.new("ShaderNodeMath"); a.operation = "PINGPONG"; a.inputs[1].default_value = per / 2; l.new(src, a.inputs[0])
        c = n.new("ShaderNodeMath"); c.operation = "LESS_THAN"; c.inputs[1].default_value = per / 2 * br; l.new(a.outputs[0], c.inputs[0]); return c
    px = raster(hor.outputs[0], per_x, br_x); pz = raster(sp.outputs["Z"], per_z, br_z)
    mx = n.new("ShaderNodeMath"); mx.operation = "MAXIMUM"; l.new(px.outputs[0], mx.inputs[0]); l.new(pz.outputs[0], mx.inputs[1])
    no = n.new("ShaderNodeTexNoise"); no.inputs["Scale"].default_value = .4; l.new(tc.outputs["Object"], no.inputs["Vector"])
    rnd = n.new("ShaderNodeTexWhiteNoise"); rnd.noise_dimensions = "3D"
    fl = n.new("ShaderNodeVectorMath"); fl.operation = "SNAP"; fl.inputs[1].default_value = (per_x, per_x, per_z); l.new(tc.outputs["Object"], fl.inputs[0]); l.new(fl.outputs[0], rnd.inputs["Vector"])
    fcol = n.new("ShaderNodeMix"); fcol.data_type = "RGBA"; l.new(rnd.outputs["Value"], fcol.inputs[0])
    fcol.inputs[6].default_value = (*hexf(fenster), 1); fcol.inputs[7].default_value = (*[min(1, c * 2.2) for c in hexf(fenster)], 1)
    gcol = n.new("ShaderNodeMix"); gcol.data_type = "RGBA"; gcol.blend_type = "MULTIPLY"; gcol.inputs[0].default_value = .25
    gcol.inputs[6].default_value = (*hexf(grund), 1); l.new(no.outputs["Color"], gcol.inputs[7])
    mix = n.new("ShaderNodeMix"); mix.data_type = "RGBA"; l.new(mx.outputs[0], mix.inputs[0]); l.new(fcol.outputs[2], mix.inputs[6]); l.new(gcol.outputs[2], mix.inputs[7])
    l.new(mix.outputs[2], b.inputs["Base Color"])
    rr = n.new("ShaderNodeMapRange"); rr.inputs[3].default_value = .08; rr.inputs[4].default_value = .75; l.new(mx.outputs[0], rr.inputs[0]); l.new(rr.outputs[0], b.inputs["Roughness"])
    mt = n.new("ShaderNodeMapRange"); mt.inputs[3].default_value = glanz; mt.inputs[4].default_value = 0; l.new(mx.outputs[0], mt.inputs[0]); l.new(mt.outputs[0], b.inputs["Metallic"])
    bu = n.new("ShaderNodeBump"); bu.inputs["Strength"].default_value = .6; bu.inputs["Distance"].default_value = .05; l.new(mx.outputs[0], bu.inputs["Height"]); l.new(bu.outputs[0], b.inputs["Normal"])
    return m


KALKSTEIN = streifen_mat("esb_fassade", "d6cdb8", "1c242c", 1.6, 3.8, .45, .3, .5)
STADT_MATS = [streifen_mat("haus_%d" % i, g, f, px, pz, bx, bz) for i, (g, f, px, pz, bx, bz) in enumerate((
    ("b9a58a", "202830", 2.2, 3.4, .5, .35), ("8a8f96", "18222c", 1.8, 3.6, .3, .25), ("c9c2b2", "26303a", 2.6, 3.2, .55, .4),
    ("6e5a4a", "1a1e22", 2.0, 3.4, .45, .35), ("a4acb4", "2a3a4a", 3.2, 3.8, .2, .15), ("d0c8b8", "222a34", 1.6, 3.0, .5, .3)))]

# ======================================================================  Manhattan (Stadt um das Empire State Building, Mittelpunkt bei STADT)
STADT = Vector((6000, 0, 0))
box("strassen", (4000, 4000, .2), STADT + Vector((0, 0, -.1)), mat("asphalt", "36373a", .9), 0)
rs = random.Random(11)
BLOCK_X, BLOCK_Y = 80.0, 260.0          # Manhattan-Raster (Strassen schmal, Avenues breit)
HOLZ_TANK = mat("holz_tank", "6a4a2a", .8)
SM = Sammler()
for i in range(-14, 15):
    for j in range(-6, 7):
        cx = STADT.x + i * BLOCK_X; cy = STADT.y + j * BLOCK_Y
        if abs(i) <= 1 and j == 0:
            continue
        d = math.hypot(i * BLOCK_X, j * BLOCK_Y)
        n_b = rs.randint(2, 4)
        for k in range(n_b):
            bx_ = BLOCK_X - 18; by_ = (BLOCK_Y - 30) / n_b; yk = cy - (BLOCK_Y - 30) / 2 + by_ * (k + .5)
            h = rs.choice((25, 40, 60, 90, 120, 160, 200)) * (1.25 if d < 700 else .8) * rs.uniform(.7, 1.2)
            mm = rs.choice(STADT_MATS)
            SM.box((bx_ - 2, by_ - 2, h), (cx, yk, h / 2), mm)
            if h > 120 and rs.random() < .4:                                 # Aufbau
                SM.box((bx_ * .5, by_ * .5, 8), (cx, yk, h + 4), mm)
            if rs.random() < .35:
                SM.zyl(2.2, 4, (cx + rs.uniform(-10, 10), yk, h + 2), HOLZ_TANK)
SM.fertig("stadt")
# Empire State Building (gestuft, Art-Deco-Krone, Mast)
E = STADT
ALUBAND = mat("aluband", "b8bcc0", .25, metal=1.0)
box("esb_sockel", (130, 57, 25), E + Vector((0, 0, 12.5)), KALKSTEIN, .3)
for (sx, sy, z0, z1) in ((95, 50, 25, 82), (75, 45, 82, 230), (62, 40, 230, 262), (50, 34, 262, 300), (40, 28, 300, 320)):
    box("esb_stufe", (sx, sy, z1 - z0), E + Vector((0, 0, (z0 + z1) / 2)), KALKSTEIN, .3)
    for sgn in (-1, 1):                                                       # vertikale Lisenen (Metallbaender)
        for k in range(-3, 4):
            SM.box((.6, .5, z1 - z0), E + Vector((k * sx / 8, sgn * (sy / 2 + .1), (z0 + z1) / 2)), ALUBAND)
SM.fertig("lisenen")
DECK_Z = 320.0
box("esb_krone", (25, 20, 28), E + Vector((0, 0, DECK_Z + 14)), KALKSTEIN, .3)
box("esb_krone2", (18, 14, 22), E + Vector((0, 0, DECK_Z + 39)), KALKSTEIN, .3)
zyl("esb_mast", 4, 60, E + Vector((0, 0, DECK_Z + 80)), mat("mast", "c8ccd0", .3, metal=.8))
zyl("esb_antenne", .8, 60, E + Vector((0, 0, DECK_Z + 140)), mat("antenne", "e6e6e6", .4, metal=.6))
# Aussichtsterrasse im 86. Stock: Boden, Bruestung, Gitter, Zielband, Zeittafel
DECK = E + Vector((0, 0, DECK_Z))
box("deck_boden", (40.2, 28.2, .3), DECK + Vector((0, 0, -.13)), pbr("deckplatten", "Concrete034", 1.2, tint="9a958c"), 0)
for (sx, sy, dx, dy) in ((40, .5, 0, -13.8), (40, .5, 0, 13.8), (.5, 28, -19.8, 0), (.5, 28, 19.8, 0)):
    box("bruestung", (sx, sy, 1.1), DECK + Vector((dx, dy, .55)), KALKSTEIN, .05)
GITTER = mat("gitter", "3a3d42", .4, metal=.8)
for x in range(-19, 20):
    for sy in (-1, 1):
        SM.rohr(DECK + Vector((x, sy * 13.8, 1.1)), DECK + Vector((x + .0, sy * 13.8 - sy * .6, 3.0)), .02, GITTER)
for x in range(-19, 20, 3):
    for sy in (-1, 1):
        SM.rohr(DECK + Vector((x, sy * 13.6, 2.2)), DECK + Vector((x + 3, sy * 13.6, 2.2)), .015, GITTER)
SM.fertig("gitter")
TUER_POS = DECK + Vector((-12.6, -5, 0))
TUERM = mat("tuer", "7a2a1a", .5, Coat_Weight=.4)
box("tuerrahmen", (.3, 1.6, 2.4), TUER_POS + Vector((0, 0, 1.2)), TUERM, .03)
TUER_ANGEL = leer("tuer_angel", TUER_POS + Vector((-.17, -.6, 0)))
box("tuerblatt", (.05, 1.2, 2.2), TUER_POS + Vector((-.17, 0, 1.1)), TUERM, .01, eltern=TUER_ANGEL).location = (0, .6, 1.1)
box("tueroeffnung", (.32, 1.2, 2.2), TUER_POS + Vector((0, 0, 1.1)), mat("dunkel", "080808", .9), .01)
ZIEL_POS = TUER_POS + Vector((-4.0, 0, 0))
for sy in (-1, 1):
    rohr("zielpfosten", ZIEL_POS + Vector((0, sy * 1.4, 0)), ZIEL_POS + Vector((0, sy * 1.4, 1.3)), .03, STAHL)
ZBM = mat("zielband", "d0141a", .5)
ZIELBAND = box("zielband", (.02, 2.8, .06), ZIEL_POS + Vector((0, 0, 1.2)), ZBM, 0)
ZB_HALB = []
for sy in (-1, 1):
    e_ = leer("zb_angel", ZIEL_POS + Vector((0, sy * 1.4, 1.2)))
    h_ = box("zb_halb", (.02, 1.4, .06), ZIEL_POS, ZBM, 0, eltern=e_); h_.location = (0, -sy * .7, 0); h_.hide_render = True
    ZB_HALB.append((e_, h_, sy))
p_uhr = os.path.join(HIER, "_tr_uhr.png")
ME.logo_bild(p_uhr, "9:33", farbe=(1, .2, .15), symbol=False, hintergrund=(.02, .02, .03), unterzeile="RUN-UP", breite=640, hoehe=320)
bpy.ops.mesh.primitive_plane_add(size=1, location=TUER_POS + Vector((-.32, -2.4, 2.5))); uhr = bpy.context.object; uhr.scale = (2.0, 1.0, 1); uhr.rotation_euler = (P / 2, 0, -P / 2)
mu = bpy.data.materials.new("uhr"); mu.use_nodes = True; ti = mu.node_tree.nodes.new("ShaderNodeTexImage"); ti.image = bpy.data.images.load(p_uhr)
bu_ = mu.node_tree.nodes["Principled BSDF"]; mu.node_tree.links.new(ti.outputs[0], bu_.inputs["Emission Color"]); bu_.inputs["Emission Strength"].default_value = 2.5; UHR_EM = bu_.inputs["Emission Strength"]
bu_.inputs["Base Color"].default_value = (0, 0, 0, 1); uhr.data.materials.append(mu)
box("uhr_rahmen", (.2, 2.2, 1.2), TUER_POS + Vector((-.2, -2.4, 2.5)), SCHWARZ, .03)

# ======================================================================  Lobby (Start): Marmor, Art-Deco-Wand, Startlinie
LOB = Vector((-400, 0, 0))
GOLD = mat("gold", "c9a24a", .25, metal=1.0)
MARMOR = pbr("marmor", "PaintedPlaster017", .4, tint="e4e0d8", rau_mul=.3)
box("lobby_boden", (40, 16, .2), LOB + Vector((0, 0, -.1)), MARMOR, 0)
box("lobby_decke", (40, 16, .3), LOB + Vector((0, 0, 9)), mat("decke", "b08a4a", .4, metal=.5), 0)
for sy in (-1, 1):
    box("lobby_wand", (40, .4, 9), LOB + Vector((0, sy * 8, 4.5)), mat("marmorwand", "7a5a3a", .25, Coat_Weight=.6), 0)
    for k in range(-9, 10, 2):
        SM.box((.25, .05, 8.6), LOB + Vector((k * 2, sy * 7.78, 4.3)), GOLD)
SM.fertig("gold")
box("lobby_vorne", (.4, 16, 9), LOB + Vector((-20, 0, 4.5)), bpy.data.materials["marmorwand"], 0)
box("lobby_rueck", (.4, 16, 9), LOB + Vector((20, 0, 4.5)), mat("marmorwand", "7a5a3a", .25) if not bpy.data.materials.get("marmorwand") else bpy.data.materials["marmorwand"], 0)
box("treppentuer", (.45, 2.0, 2.6), LOB + Vector((19.8, 0, 1.3)), mat("dunkel", "080808", .9) if not bpy.data.materials.get("dunkel") else bpy.data.materials["dunkel"], .02)
box("startlinie", (.3, 6, .02), LOB + Vector((10, 0, .01)), mat("startlinie", "f2f2f2", .5), 0)
for k in range(6):
    bpy.ops.object.light_add(type="AREA", location=LOB + Vector((-15 + k * 6, 0, 8.6))); L_ = bpy.context.object; L_.data.size = 3; L_.data.energy = 900; L_.data.color = (1, .95, .88)
    L_.rotation_euler = (P, 0, 0)

# ======================================================================  Treppenhaus (Module: 14 Geschosse uebereinander, wiederholt)
GH = 3.6; STUFE_H = .18; STUFE_T = .28; N_ST = 10; BREITE = 1.15; GAP = .22
_vor = set(bpy.data.objects)
LAUF_L = N_ST * STUFE_T
TR = Vector((0, 0, 0))
STUFEN_M = pbr("stufenbeton", "Concrete034", 1.6, tint="9c978e")
KANTE = mat("stufenkante", "e8c21a", .5)
WAND_M = mat("treppenwand", "d9d4c6", .85)
GELAENDER = mat("gelaender", "2a5a8a", .35, Coat_Weight=.5)
N_GESCH = 14
SCHILDER = []
SCHILD_T = mat("schild_text", "f2f2f2", .5); SCHILD_G = mat("schild_gruen", "1b6b3a", .4)
NOTL = emis("notlicht", "fff4e0", 8); LOESCH = mat("loescher", "c62828", .3, Coat_Weight=.7)
ROHR_M = [mat("rohr0", "c62828", .35, Coat_Weight=.5), mat("rohr1", "8a8f96", .35, Coat_Weight=.5)]
TUER_T = mat("treppentuer_m", "4a5a6a", .4, metal=.5)
ST = Sammler()
for g in range(N_GESCH):
    z0 = g * GH
    for lauf in (0, 1):                                       # Lauf A (+x, y<0) und Lauf B (-x, y>0)
        for s_ in range(N_ST):
            if lauf == 0:
                x = s_ * STUFE_T; y = -BREITE / 2 - GAP
            else:
                x = LAUF_L - (s_ + 1) * STUFE_T; y = BREITE / 2 + GAP
            zb = z0 + lauf * GH / 2; z = zb + (s_ + 1) * STUFE_H
            ST.box((STUFE_T, BREITE, z - zb + .15), TR + Vector((x + STUFE_T / 2, y, (z + zb - .15) / 2)), STUFEN_M)
            ST.box((.05, BREITE - .1, .012), TR + Vector((x + (STUFE_T - .03 if lauf == 1 else .03), y, z + .006)), KANTE)
    for (px_, pz_) in ((LAUF_L + .65, z0 + GH / 2), (-.65, z0 + GH)):
        ST.box((1.3, 2 * (BREITE + GAP), .25), TR + Vector((px_, 0, pz_ - .125)), STUFEN_M)
    for lauf, sy in ((0, -1), (1, 1)):                         # Gelaender innen mit Pfosten
        a = TR + Vector((0 if lauf == 0 else LAUF_L, sy * (GAP + .04), z0 + lauf * GH / 2 + .95))
        b_ = TR + Vector((LAUF_L if lauf == 0 else 0, sy * (GAP + .04), z0 + lauf * GH / 2 + GH / 2 + .95))
        ST.rohr(a, b_, .025, GELAENDER)
        ST.rohr(a - Vector((0, 0, .45)), b_ - Vector((0, 0, .45)), .012, GELAENDER)
        for k in range(0, 11, 2):
            p_ = a.lerp(b_, k / 10); ST.rohr(p_ - Vector((0, 0, .95 - .18 * (k % 2))), p_, .015, GELAENDER)
    ST.rohr(TR + Vector((LAUF_L, -GAP - .04, z0 + GH / 2 + .95)), TR + Vector((LAUF_L, GAP + .04, z0 + GH / 2 + .95)), .025, GELAENDER)
    ST.rohr(TR + Vector((0, GAP + .04, z0 + GH + .95)), TR + Vector((0, -GAP - .04, z0 + GH + .95)), .025, GELAENDER)
    # Schild, Tuer zum Stockwerk, Notlicht, Feuerloescher, Kabelkanal
    ST.box((.03, .8, .7), TR + Vector((-1.3, 0, z0 + GH + 1.86)), SCHILD_G)
    ST.box((.06, 1.0, 2.1), TR + Vector((-1.31, -.0 - 0, z0 + GH + 1.05)) + Vector((0, -BREITE - GAP + .62, 0)), TUER_T)
    ST.box((.04, .08, .03), TR + Vector((-1.27, -BREITE - GAP + .25, z0 + GH + 1.0)), STAHL)
    ST.box((.08, .3, .12), TR + Vector((LAUF_L + 1.28, .5, z0 + GH / 2 + 2.3)), NOTL)
    ST.box((.08, .3, .12), TR + Vector((-1.28, -.6, z0 + GH + 2.4)), NOTL)
    ST.zyl(.08, .5, TR + Vector((LAUF_L + 1.2, -.9, z0 + GH / 2 + .35)), LOESCH)
    ST.box((.05, .3, .12), TR + Vector((LAUF_L + 1.27, -.9, z0 + GH / 2 + .9)), LOESCH)
    bpy.ops.object.text_add(location=TR + Vector((-1.262, 0, z0 + GH + 1.7)), rotation=(P / 2, 0, P / 2)); t_ = bpy.context.object
    t_.data.body = "0"; t_.data.size = .55; t_.data.align_x = "CENTER"; t_.data.extrude = .01; t_.data.materials.append(SCHILD_T)
    SCHILDER.append((t_, g))
    for (lp, en) in (((LAUF_L + 1.0, .3, z0 + GH / 2 + 2.2), 90), ((-1.0, -.3, z0 + GH + 2.2), 70)):
        L_ = bpy.data.objects.new("licht_%d_%d" % (g, en), bpy.data.lights.new("licht_%d_%d" % (g, en), "POINT")); sc.collection.objects.link(L_)
        L_.location = TR + Vector(lp); L_.data.energy = en; L_.data.color = (1, .95, .85); L_.data.shadow_soft_size = .3
HW = N_GESCH * GH + 4
ST.box((LAUF_L + 3.2, .2, HW), TR + Vector((LAUF_L / 2, -BREITE - GAP - .2, HW / 2 - 2)), WAND_M)
ST.box((LAUF_L + 3.2, .2, HW), TR + Vector((LAUF_L / 2, BREITE + GAP + .2, HW / 2 - 2)), WAND_M)
ST.box((.2, 2 * (BREITE + GAP) + .5, HW), TR + Vector((LAUF_L + 1.4, 0, HW / 2 - 2)), WAND_M)
ST.box((.2, 2 * (BREITE + GAP) + .5, HW), TR + Vector((-1.4, 0, HW / 2 - 2)), WAND_M)
for k, yy in enumerate((-BREITE - GAP + .06, -BREITE - GAP + .2)):
    ST.zyl(.06 if k == 0 else .04, HW, TR + Vector((LAUF_L + 1.15, yy, HW / 2 - 2)), ROHR_M[k])
ST.box((.06, .1, HW), TR + Vector((-1.28, BREITE + GAP - .05, HW / 2 - 2)), mat("kabelkanal", "bdbab2", .6))
ST.fertig("treppe", bevel=.008)
STACK = leer("stack")
for o in set(bpy.data.objects) - _vor:
    if o.parent is None and o is not STACK:
        o.parent = STACK
print("ok szene")
