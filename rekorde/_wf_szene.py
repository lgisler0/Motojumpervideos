# ======================================================================  Himmel, Sonne
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; nt = w.node_tree
env = nt.nodes.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(os.path.join(ASSET, "tag.hdr"))
nt.links.new(env.outputs[0], nt.nodes["Background"].inputs[0]); nt.nodes["Background"].inputs[1].default_value = 1.0
bpy.ops.object.light_add(type="SUN", rotation=(math.radians(40), 0, math.radians(-60))); sonne = bpy.context.object
sonne.data.energy = 4.3; sonne.data.angle = math.radians(1.0); sonne.data.color = (1, .95, .88)
STAHL = pbr("stahl", "Metal012", 6, rau_mul=.6, rau_add=.15, metal=1.0)

H_FALL = 57.6                     # Fallhoehe (m)
C = Vector((34.0, 0, 0))          # Mitte des Kessels (Plunge Pool)
R_POOL = 30.0; Z_PLAT = 66.0


def sstep(a, b, x):
    t = min(1, max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t)


# ======================================================================  Gelaende (Hoehenfeld): Hochebene, Kessel, Oberlauf, Canyon
def gelaende(x, y):
    d = math.hypot(x - C.x, y - C.y)
    z = Z_PLAT + 1.5 * math.sin(x / 37) * math.sin(y / 29)
    # Kessel (steile Waende)
    k = sstep(R_POOL + 4.2, R_POOL + 3, d)
    z = z * (1 - k) + (-3) * k
    # Canyon flussabwaerts (+x)
    if x > C.x:
        bc = 26 + .08 * (x - C.x)
        kk = sstep(bc + 6, bc, abs(y))
        z = z * (1 - kk) + (-3) * kk
    # Oberlauf: Rinne bis zur Kante (x < 0)
    if x < 2:
        kk = sstep(14, 10, abs(y))
        bett = H_FALL - 1.0 + .015 * (-x)
        z = min(z, z * (1 - kk) + bett * kk)
    return z


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


def basalt_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt_ = m.node_tree; n = nt_.nodes; l = nt_.links; b = n["Principled BSDF"]
    geo = n.new("ShaderNodeNewGeometry"); sp = n.new("ShaderNodeSeparateXYZ"); l.new(geo.outputs["Normal"], sp.inputs[0])
    sp2 = n.new("ShaderNodeSeparateXYZ"); l.new(geo.outputs["Position"], sp2.inputs[0])
    gr = n.new("ShaderNodeMapRange"); gr.inputs[1].default_value = .7; gr.inputs[2].default_value = .85; l.new(sp.outputs["Z"], gr.inputs[0])
    hz = n.new("ShaderNodeMapRange"); hz.inputs[1].default_value = 60; hz.inputs[2].default_value = 63; l.new(sp2.outputs["Z"], hz.inputs[0])
    mu = n.new("ShaderNodeMath"); mu.operation = "MULTIPLY"; l.new(gr.outputs[0], mu.inputs[0]); l.new(hz.outputs[0], mu.inputs[1])
    vo = n.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = .5; vo.feature = "DISTANCE_TO_EDGE"
    mp = n.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1, 1, .08); l.new(geo.outputs["Position"], mp.inputs[0]); l.new(mp.outputs[0], vo.inputs["Vector"])
    kante = n.new("ShaderNodeMapRange"); kante.inputs[1].default_value = .0; kante.inputs[2].default_value = .06; l.new(vo.outputs["Distance"], kante.inputs[0])
    no = n.new("ShaderNodeTexNoise"); no.inputs["Scale"].default_value = .4; no.inputs["Detail"].default_value = 10; l.new(geo.outputs["Position"], no.inputs["Vector"])
    fc = n.new("ShaderNodeMix"); fc.data_type = "RGBA"; l.new(no.outputs["Fac"], fc.inputs[0])
    fc.inputs[6].default_value = (*hexf("2a221d"), 1); fc.inputs[7].default_value = (*hexf("4a3a2e"), 1)
    dk = n.new("ShaderNodeMix"); dk.data_type = "RGBA"; dk.blend_type = "MULTIPLY"; l.new(kante.outputs[0], dk.inputs[0])
    dk.inputs[0].default_value = 1; l.new(fc.outputs[2], dk.inputs[6])
    kc = n.new("ShaderNodeMapRange"); kc.inputs[3].default_value = .35; kc.inputs[4].default_value = 1.0; l.new(kante.outputs[0], kc.inputs[0])
    cc = n.new("ShaderNodeCombineColor"); l.new(kc.outputs[0], cc.inputs[0]); l.new(kc.outputs[0], cc.inputs[1]); l.new(kc.outputs[0], cc.inputs[2]); l.new(cc.outputs[0], dk.inputs[7])
    gras = n.new("ShaderNodeMix"); gras.data_type = "RGBA"; l.new(no.outputs["Fac"], gras.inputs[0])
    gras.inputs[6].default_value = (*hexf("5c6630"), 1); gras.inputs[7].default_value = (*hexf("857a44"), 1)
    mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; l.new(mu.outputs[0], mx.inputs[0]); l.new(dk.outputs[2], mx.inputs[6]); l.new(gras.outputs[2], mx.inputs[7])
    l.new(mx.outputs[2], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = .9
    bu = n.new("ShaderNodeBump"); bu.inputs["Strength"].default_value = .9; bu.inputs["Distance"].default_value = .8
    wand = n.new("ShaderNodeMath"); wand.operation = "SUBTRACT"; wand.inputs[0].default_value = 1.0; l.new(mu.outputs[0], wand.inputs[1])
    kw = n.new("ShaderNodeMath"); kw.operation = "MULTIPLY"; l.new(kante.outputs[0], kw.inputs[0]); l.new(wand.outputs[0], kw.inputs[1])
    ad = n.new("ShaderNodeMath"); ad.operation = "ADD"; l.new(kw.outputs[0], ad.inputs[0]); l.new(no.outputs["Fac"], ad.inputs[1])
    l.new(ad.outputs[0], bu.inputs["Height"]); l.new(bu.outputs[0], b.inputs["Normal"])
    return m


BASALT = basalt_mat("basalt")
hoehenfeld("gelaende", -260, 320, -260, 260, 2.0, gelaende, BASALT)
# Basaltsaeulen am Kesselrand (sechseckig, Hoehen variieren)
SA = Sammler(); rs = random.Random(3)
SAEULE = [mat("saeule%d" % i, f, .85) for i, f in enumerate(("3a2f28", "4a3c31", "5a4838"))]
for ring, (r0, z0, z1) in enumerate(((R_POOL + 3.5, -2, 30), (R_POOL + 5.5, 28, 58), (R_POOL + 7.5, 55, 64))):
    n_s = int(2 * P * r0 / 1.9)
    for k in range(n_s):
        a = 2 * P * k / n_s
        if abs(math.atan2(math.sin(a), math.cos(a))) < .55:          # offen flussabwaerts
            continue
        if abs(math.atan2(math.sin(a - P), math.cos(a - P))) < .28 and z1 > H_FALL - 4:   # Kerbe fuer den Fall
            continue
        h = (z1 - z0) * rs.uniform(.75, 1.0)
        p_ = C + Vector((r0 * math.cos(a) + rs.uniform(-.3, .3), r0 * math.sin(a) + rs.uniform(-.3, .3), z0 + h / 2))
        SA.zyl(rs.uniform(.9, 1.15), h, p_, rs.choice(SAEULE), rot=(0, 0, rs.uniform(0, 1)), v=6)
SA.fertig("basaltsaeulen", bevel=.06)
# Steppengras-Buesche auf der Hochebene (rund)
BG = Sammler(); BUSCH = [mat("busch%d" % i, f, .9) for i, f in enumerate(("8a7a44", "6e6a3a", "a39056"))]
for i in range(700):
    x = rs.uniform(-200, 260); y = rs.uniform(-220, 220)
    z = gelaende(x, y)
    if z < Z_PLAT - 3:
        continue
    BG.kugel(rs.uniform(.3, .8), (x, y, z + .2), rs.choice(BUSCH), skala=(1, 1, .6), sub=1)
BG.fertig("steppe")

# ======================================================================  Wasser: Oberlauf, Fallvorhang, Kessel, Gischt
ZEIT = []          # Mapping-Knoten, deren Versatz je Bild mit der Zeit laeuft


def fluss_mat(name, farbe, schaum, richtung, skala, schaumanteil):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt_ = m.node_tree; n = nt_.nodes; l = nt_.links; b = n["Principled BSDF"]
    tc = n.new("ShaderNodeTexCoord"); mp = n.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = skala; l.new(tc.outputs["Object"], mp.inputs[0])
    ZEIT.append((mp, richtung))
    no = n.new("ShaderNodeTexNoise"); no.inputs["Scale"].default_value = 2.0; no.inputs["Detail"].default_value = 12; no.inputs["Roughness"].default_value = .65
    l.new(mp.outputs[0], no.inputs["Vector"])
    mr = n.new("ShaderNodeMapRange"); mr.inputs[1].default_value = 1 - schaumanteil; mr.inputs[2].default_value = 1 - schaumanteil + .18; l.new(no.outputs["Fac"], mr.inputs[0])
    mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; l.new(mr.outputs[0], mx.inputs[0])
    mx.inputs[6].default_value = (*hexf(farbe), 1); mx.inputs[7].default_value = (*hexf(schaum), 1); l.new(mx.outputs[2], b.inputs["Base Color"])
    rr = n.new("ShaderNodeMapRange"); rr.inputs[3].default_value = .04; rr.inputs[4].default_value = .5; l.new(mr.outputs[0], rr.inputs[0]); l.new(rr.outputs[0], b.inputs["Roughness"])
    bu = n.new("ShaderNodeBump"); bu.inputs["Strength"].default_value = .35; l.new(no.outputs["Fac"], bu.inputs["Height"]); l.new(bu.outputs[0], b.inputs["Normal"])
    return m, mr


OBERLAUF_M, _ = fluss_mat("oberlauf", "2f5a46", "d8e4e0", (-1.0, 0, 0), (.25, .6, .25), .22)
POOL_M, pool_mr = fluss_mat("kessel", "21463c", "e4ecea", (0, 0, 0), (.3, .3, .3), .28)
# im Kessel: Schaum nahe dem Aufprall
nt_ = POOL_M.node_tree; n = nt_.nodes; l = nt_.links
geo = n.new("ShaderNodeNewGeometry"); vm = n.new("ShaderNodeVectorMath"); vm.operation = "DISTANCE"; vm.inputs[1].default_value = (14.0, 0, 0)
l.new(geo.outputs["Position"], vm.inputs[0])
nah = n.new("ShaderNodeMapRange"); nah.inputs[1].default_value = 22; nah.inputs[2].default_value = 6; l.new(vm.outputs["Value"], nah.inputs[0])
mxx = n.new("ShaderNodeMath"); mxx.operation = "MAXIMUM"; l.new(pool_mr.outputs[0], mxx.inputs[0])
mu2 = n.new("ShaderNodeMath"); mu2.operation = "MULTIPLY"; l.new(nah.outputs[0], mu2.inputs[0]); mu2.inputs[1].default_value = .85; l.new(mu2.outputs[0], mxx.inputs[1])
for lk in list(l):
    if lk.from_node == pool_mr and lk.to_node.type == "MIX":
        tgt = lk.to_socket; l.remove(lk); l.new(mxx.outputs[0], tgt)
# Oberlauf (Wasserflaeche in der Rinne), leicht geneigt
bpy.ops.mesh.primitive_grid_add(x_subdivisions=120, y_subdivisions=24, size=1, location=(-75, 0, 0)); OB = bpy.context.object; OB.name = "oberlauf"
OB.scale = (150, 26, 1); bpy.ops.object.transform_apply(scale=True)
for v in OB.data.vertices:
    v.co.z = H_FALL + .2 + .015 * (-(v.co.x - 75)) * 0 + .015 * -(v.co.x + -75 + 75) * 0
for v in OB.data.vertices:
    xw = v.co.x + OB.location.x
    v.co.z = H_FALL + .25 + .015 * max(0, -xw) - .35 * sstep(-6, 0, xw)
OB.data.materials.append(OBERLAUF_M)
for p in OB.data.polygons:
    p.use_smooth = True
# Fallvorhang: zwei Schichten, Parabel (v0 = 4 m/s)
FALL_M = bpy.data.materials.new("fallvorhang"); FALL_M.use_nodes = True
n = FALL_M.node_tree.nodes; l = FALL_M.node_tree.links; out = n["Material Output"]; bs = n["Principled BSDF"]
tc = n.new("ShaderNodeTexCoord"); mp = n.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (.9, 2.2, .12); l.new(tc.outputs["Object"], mp.inputs[0])
ZEIT.append((mp, (0, 0, 9.0)))
no = n.new("ShaderNodeTexNoise"); no.inputs["Scale"].default_value = 3.0; no.inputs["Detail"].default_value = 14; no.inputs["Roughness"].default_value = .7; l.new(mp.outputs[0], no.inputs["Vector"])
sp = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Object"], sp.inputs[0])
oben = n.new("ShaderNodeMapRange"); oben.inputs[1].default_value = H_FALL - 2; oben.inputs[2].default_value = H_FALL - 7; l.new(sp.outputs["Z"], oben.inputs[0])
cmx = n.new("ShaderNodeMix"); cmx.data_type = "RGBA"; l.new(oben.outputs[0], cmx.inputs[0])
cmx.inputs[6].default_value = (*hexf("3f7a5e"), 1); cmx.inputs[7].default_value = (.93, .95, .95, 1); l.new(cmx.outputs[2], bs.inputs["Base Color"])
bs.inputs["Roughness"].default_value = .35
al = n.new("ShaderNodeMapRange"); al.inputs[1].default_value = .35; al.inputs[2].default_value = .6; l.new(no.outputs["Fac"], al.inputs[0])
alm = n.new("ShaderNodeMath"); alm.operation = "MAXIMUM"; l.new(al.outputs[0], alm.inputs[0]); oben2 = n.new("ShaderNodeMath"); oben2.operation = "SUBTRACT"
oben2.inputs[0].default_value = 1.0; l.new(oben.outputs[0], oben2.inputs[1]); l.new(oben2.outputs[0], alm.inputs[1])
tr = n.new("ShaderNodeBsdfTransparent"); ms = n.new("ShaderNodeMixShader"); l.new(alm.outputs[0], ms.inputs[0]); l.new(tr.outputs[0], ms.inputs[1]); l.new(bs.outputs[0], ms.inputs[2])
l.new(ms.outputs[0], out.inputs["Surface"])
V0 = 4.0; G = 9.81
for schicht, (dx, breite) in enumerate(((0.0, 1.0), (.6, 1.12))):
    bm = bmesh.new(); rows = []
    NT = 40
    for i in range(NT + 1):
        t = 3.5 * i / NT
        x = V0 * t + dx * t / 3.5; z = H_FALL - .5 * G * t * t
        hw = (9.0 + 3.0 * t / 3.5) * breite
        rows.append([bm.verts.new((x, y, z)) for y in [-hw + 2 * hw * j / 24 for j in range(25)]])
    for a, b in zip(rows, rows[1:]):
        for j in range(24):
            bm.faces.new((a[j], a[j + 1], b[j + 1], b[j]))
    me_ = bpy.data.meshes.new("fall%d" % schicht); bm.to_mesh(me_); bm.free(); me_.materials.append(FALL_M)
    o = bpy.data.objects.new("fall%d" % schicht, me_); sc.collection.objects.link(o)
    for p in me_.polygons:
        p.use_smooth = True
# Kessel-Wasser
bpy.ops.mesh.primitive_plane_add(size=1, location=(C.x + 60, 0, 0)); POOL = bpy.context.object; POOL.name = "kessel"; POOL.scale = (260, 160, 1)
bpy.ops.object.transform_apply(scale=True)
pm = POOL.modifiers.new("wellen", "OCEAN"); pm.geometry_mode = "DISPLACE"
POOL.modifiers.remove(pm)
sub = POOL.modifiers.new("s", "SUBSURF"); sub.subdivision_type = "SIMPLE"; sub.levels = 0; sub.render_levels = 0
POOL.data.materials.append(POOL_M)
# Gischt / Nebel am Fuss des Falls (Volumen)
NEBEL = bpy.data.materials.new("nebel"); NEBEL.use_nodes = True
n = NEBEL.node_tree.nodes; l = NEBEL.node_tree.links; out = n["Material Output"]; n.remove(n["Principled BSDF"])
vol = n.new("ShaderNodeVolumePrincipled"); vol.inputs["Color"].default_value = (.95, .97, .98, 1); vol.inputs["Density"].default_value = .05
gr = n.new("ShaderNodeTexGradient"); gr.gradient_type = "SPHERICAL"; tcn = n.new("ShaderNodeTexCoord"); l.new(tcn.outputs["Object"], gr.inputs["Vector"])
mud = n.new("ShaderNodeMath"); mud.operation = "MULTIPLY"; mud.inputs[1].default_value = .008; l.new(gr.outputs["Fac"], mud.inputs[0]); l.new(mud.outputs[0], vol.inputs["Density"])
l.new(vol.outputs[0], out.inputs["Volume"])
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1, location=(15, 0, 3)); NB = bpy.context.object; NB.name = "nebel"; NB.scale = (14, 16, 9)
NB.data.materials.append(NEBEL)
# Aussichtspunkt mit Gelaender und Zuschauern (gegenueber, Suedrand)
AUS = C + Vector((10, -(R_POOL + 12), 0)); AUS.z = gelaende(AUS.x, AUS.y)
GL = Sammler()
for k in range(14):
    x0 = AUS.x - 14 + k * 2.0
    GL.rohr(Vector((x0, AUS.y + 2.5, AUS.z)), Vector((x0, AUS.y + 2.5, AUS.z + 1.05)), .03, STAHL)
GL.rohr(Vector((AUS.x - 14, AUS.y + 2.5, AUS.z + 1.05)), Vector((AUS.x + 12, AUS.y + 2.5, AUS.z + 1.05)), .03, STAHL)
GL.rohr(Vector((AUS.x - 14, AUS.y + 2.5, AUS.z + .55)), Vector((AUS.x + 12, AUS.y + 2.5, AUS.z + .55)), .02, STAHL)
GL.fertig("gelaender")
rz = random.Random(17); RAND_LEUTE = []
for i in range(12):
    x = AUS.x - 12 + i * 2.0 + rz.uniform(-.3, .3)
    o = bpy.data.objects.new("rand_%d" % i, rz.choice(ZUSCH_ME)); sc.collection.objects.link(o)
    o.location = (x, AUS.y + rz.uniform(.3, 1.6), AUS.z); o.rotation_euler = (0, 0, P + rz.uniform(-.4, .4))
    RAND_LEUTE.append((o, AUS.z, rz.uniform(0, 6)))

# ======================================================================  Kajak (rot) + Paddel
def kajak_mesh():
    """Rumpf: Querschnitte entlang x (Laenge 2,6 m), flacher Boden, gewoelbtes Deck"""
    bm = bmesh.new(); ringe = []; NX = 26; NU = 20
    for i in range(NX + 1):
        x = -1.3 + 2.6 * i / NX
        f = 1 - (abs(x) / 1.3) ** 2.2
        bw = .34 * max(f, .02) ** .6; hh = .28 * max(f, .05) ** .5
        ring = []
        for j in range(NU):
            a = 2 * P * j / NU
            y = bw * math.cos(a); z = (hh * math.sin(a) if math.sin(a) > 0 else .6 * hh * math.sin(a))
            ring.append(bm.verts.new((x, y, z + .02 * (x / 1.3) ** 2)))
        ringe.append(ring)
    for a, b in zip(ringe, ringe[1:]):
        for j in range(NU):
            bm.faces.new((a[j], a[(j + 1) % NU], b[(j + 1) % NU], b[j]))
    bmesh.ops.contextual_create(bm, geom=ringe[0]); bmesh.ops.contextual_create(bm, geom=ringe[-1])
    me_ = bpy.data.meshes.new("kajak"); bm.to_mesh(me_); bm.free()
    for p in me_.polygons:
        p.use_smooth = True
    return me_


KAJAK = bpy.data.objects.new("kajak", kajak_mesh()); sc.collection.objects.link(KAJAK)
KAJAK.data.materials.append(mat("kajak_rot", "c4161c", .3, Coat_Weight=.9))
KAJAK.modifiers.new("s", "SUBSURF").render_levels = 2
KAJAK.rotation_mode = "QUATERNION"
bpy.ops.mesh.primitive_torus_add(major_radius=.3, minor_radius=.025, location=(0, 0, .27)); sull = bpy.context.object; sull.name = "suelrand"; sull.scale = (1.25, .85, 1)
sull.data.materials.append(mat("schwarz", "121212", .5)); sull.parent = KAJAK
bpy.ops.mesh.primitive_cylinder_add(radius=.3, depth=.02, location=(0, 0, .272)); sk = bpy.context.object; sk.name = "spritzdecke"; sk.scale = (1.22, .82, 1)
sk.data.materials.append(mat("neopren", "1b1d22", .7)); sk.parent = KAJAK
# Paddel: Schaft entlang lokal y, Blaetter an beiden Enden
PADDEL = leer("paddel"); PADDEL.rotation_mode = "QUATERNION"
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=.016, radius2=.016, depth=2.0, matrix=Matrix.Rotation(P / 2, 4, "X"))
me_s = bpy.data.meshes.new("schaft"); bm.to_mesh(me_s); bm.free(); me_s.materials.append(mat("schaft", "1a1a1a", .3, metal=.3))
o_s = bpy.data.objects.new("schaft", me_s); sc.collection.objects.link(o_s); o_s.parent = PADDEL
bm = bmesh.new()
for sy in (-1, 1):
    bmesh.ops.create_cube(bm, size=1, matrix=Matrix.Translation((0, sy * 1.12, 0)) @ Matrix.Rotation(sy * .12, 4, "Z") @ Matrix.Diagonal((.014, .44, .18, 1)))
me_b = bpy.data.meshes.new("blaetter"); bm.to_mesh(me_b); bm.free(); me_b.materials.append(mat("blatt", "f2f2f2", .35, Coat_Weight=.6))
o_b = bpy.data.objects.new("blaetter", me_b); sc.collection.objects.link(o_b); o_b.parent = PADDEL
# Spritzer beim Aufprall
SPR_M = mat("spritzer", "f4f8fa", .8, Emission_Color=(1, 1, 1, 1), Emission_Strength=.25)
SPRITZER = []
rk = random.Random(8)
for i in range(60):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, location=(0, 0, -60)); o = bpy.context.object; o.name = "spritzer%d" % i
    o.data.materials.append(SPR_M)
    for p in o.data.polygons:
        p.use_smooth = True
    a = rk.uniform(0, 2 * P); v = rk.uniform(5, 14); h = rk.uniform(.3, 1.0)
    SPRITZER.append((o, Vector((math.cos(a) * v * .45, math.sin(a) * v * .45, v * h)), rk.uniform(.12, .3)))
print("ok szene")
