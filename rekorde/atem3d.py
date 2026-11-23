"""Geschichte: Ein Mann hat einen Job: nicht atmen (Vitomir Maričić, 14.6.2025, 29:03, GWR, Hotelpool 3 m, Opatija).
Szene: Hotelpool am Meer (Fliesen, Bahnleinen, Unterwasserlampen, Leiter, Liegen, Palmen, Hotelfassade), Wasseroberflaeche
(Glas, Ocean-Wellen), Wasservolumen, falsche Kaustik ueber Spot-Lichtmuster, Freitaucher (MPFB) im Neopren mit Nasenklammer
+ Bleigurt, Sicherheitstaucher, zwei Kampfrichter, Sauerstoffflasche mit Maske.
python3 atem3d.py <ordner> [--nur t1,t2] [--start i] [--samples n]"""
import bpy, bmesh, math, random, sys, os, argparse
from mathutils import Vector, Matrix
HIER = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HIER)
import mensch_mh as MH

ap = argparse.ArgumentParser()
ap.add_argument("ordner"); ap.add_argument("--nur", default=""); ap.add_argument("--skala", type=int, default=50)
ap.add_argument("--samples", type=int, default=14); ap.add_argument("--fps", type=int, default=15)
ap.add_argument("--start", type=int, default=0)
A = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
P = math.pi
D = 34.0
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = A.samples; sc.cycles.use_denoising = True
sc.cycles.max_bounces = 6; sc.cycles.diffuse_bounces = 1; sc.cycles.glossy_bounces = 3; sc.cycles.transmission_bounces = 6
sc.cycles.transparent_max_bounces = 8; sc.cycles.volume_bounces = 0; sc.cycles.volume_step_rate = 4; sc.cycles.adaptive_threshold = .03
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1080, 1920, A.skala
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"; sc.view_settings.exposure = -1.2
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
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def zyl(name, r, h, ort, m, rot=(0, 0, 0), v=32, bevel=True):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, vertices=v, location=ort, rotation=rot); o = bpy.context.object; o.name = name
    o.data.materials.append(m)
    if bevel:
        bv = o.modifiers.new("b", "BEVEL"); bv.width = min(r, h) * .15; bv.segments = 2
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def linie(o, a, b_):
    a, b_ = Vector(a), Vector(b_); d = b_ - a
    o.location = (a + b_) / 2; o.rotation_euler = d.to_track_quat("Z", "Y").to_euler(); o.scale = (1, 1, max(d.length, .001))


def farbe_setzen(m, f, f2=None):
    for nd in m.node_tree.nodes:
        if nd.type == "MIX" and nd.data_type == "RGBA":
            nd.inputs[6].default_value = (*hexf(f), 1); nd.inputs[7].default_value = (*hexf(f2 or f), 1)


def mensch(name, seed, kleid, hose_f, barfuss=True, haut="caucasian", maenn=1.0, alter=.45, muskel=.6, gewicht=.45):
    m = MH.Arbeiter(name=name, seed=seed, maenn=maenn, alter=alter, muskel=muskel, gewicht=gewicht, haut=haut, weste=False)
    for o in m.huellen:
        if o.name.endswith("_hemd"):
            farbe_setzen(o.active_material, *kleid)
        elif o.name.endswith("_hose"):
            farbe_setzen(o.active_material, *hose_f)
        elif o.name.endswith("_hand"):
            o.hide_render = True
    for o in m.helm:
        o.hide_render = True
    weg = list(m.helm) + [o for o in m.huellen if o.name.endswith("_hand")]
    if barfuss:
        for o in m.stiefel:
            o.hide_render = True
        weg += list(m.stiefel)
        mk = m.koerper.modifiers.get("fuesse")
        if mk:
            m.koerper.modifiers.remove(mk)
    m.objekte = [o for o in m.objekte if o not in weg]
    return m


def neopren(m):
    for o in m.huellen:
        if o.name.endswith(("_hemd", "_hose")):
            b = o.active_material.node_tree.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = .42
            b.inputs["Sheen Weight"].default_value = .15; b.inputs["Coat Weight"].default_value = .25
            o.modifiers["versatz"].strength = .006 if o.name.endswith("_hemd") else .008


# ======================================================================  Freitaucher
M = mensch("taucher", 12, ("15171a", "0d0e10"), ("15171a", "0d0e10"), alter=.42, muskel=.62, gewicht=.42)
neopren(M); rig = M.rig
nase = (M.gm("joint-l-eye") + M.gm("joint-r-eye")) / 2 + Vector((0, -.03, -.035))
blei_m = mat("blei", "5d6166", .35, .8); gurt_m = mat("gummigurt", "1c1c1c", .6)
stahl = mat("stahl", "b9bdc2", .25, 1.0)
becken = M.gm("joint-pelvis")
TEILE = []
bpy.ops.mesh.primitive_torus_add(major_radius=.17, minor_radius=.02, major_segments=48, location=(0, becken.y, becken.z + .08))
g = bpy.context.object; g.name = "taucher_bleigurt"; g.scale = (1, .78, .9); g.data.materials.append(gurt_m); TEILE.append(g)
for i, a_ in enumerate((-1.1, -.4, .4, 1.1)):
    TEILE.append(box("taucher_blei", (.06, .035, .05), (math.sin(a_) * .17, becken.y - math.cos(a_) * .135, becken.z + .08), blei_m, .006,
                     rot=(0, 0, -a_)))
TEILE.append(box("taucher_schnalle", (.05, .015, .04), (0, becken.y - .14, becken.z + .08), stahl, .004))
for o in TEILE:
    an_knochen(o, rig, "spine05" if "spine05" in rig.data.bones else "pelvis")
# Nasenklammer (zwei Polster + Buegel) am Kopf
nk = []
nk_m = mat("klammer", "e33b2b", .35)
for s_ in (-1, 1):
    nk.append(zyl("taucher_klammerpolster", .009, .012, nase + Vector((s_ * .016, 0, 0)), nk_m, rot=(0, P / 2, 0), v=16))
bpy.ops.mesh.primitive_torus_add(major_radius=.018, minor_radius=.0025, location=nase + Vector((0, -.012, .006)), rotation=(P / 2, 0, 0))
o = bpy.context.object; o.data.materials.append(nk_m); nk.append(o)
for o in nk:
    an_knochen(o, rig, "head")
for o in nk:
    o.hide_render = True
# Kurze Haare (Kappe ueber dem Schaedel, vorne bis zur Stirn)
aug0 = (M.gm("joint-l-eye") + M.gm("joint-r-eye")) / 2
hz = aug0 + Vector((0, .085, .025))
bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=32, radius=.099)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if (v.co.y < -.01 and v.co.z < .045) or (v.co.y >= -.01 and v.co.z < -.02 and abs(v.co.x) > .06) or v.co.z < -.075], context="VERTS")
me = bpy.data.meshes.new("haare"); bm.to_mesh(me); bm.free()
haar = bpy.data.objects.new("taucher_haare", me); sc.collection.objects.link(haar); haar.location = hz; haar.scale = (.93, 1.06, 1.0)
hm_ = MH._stoff("kopfhaar", "2a1d14", rau=.55, skala=2500); hm_.node_tree.nodes["Principled BSDF"].inputs["Sheen Weight"].default_value = .8
me.materials.append(hm_)
for p in me.polygons:
    p.use_smooth = True
an_knochen(haar, rig, "head")
haar.hide_render = True
M.objekte += TEILE

# ======================================================================  Sicherheitstaucher + Kampfrichter
S = mensch("sicherung", 41, ("1d2a3a", "0f1620"), ("1d2a3a", "0f1620"), alter=.35, muskel=.55)
neopren(S)
mk_m = mat("maskenglas", "9fb3c4", .02, Transmission_Weight=1.0); rahmen_m = mat("maskenrahmen", "17181b", .5)
aug = (S.gm("joint-l-eye") + S.gm("joint-r-eye")) / 2
mt = [box("sicherung_maske", (.13, .03, .055), aug + Vector((0, -.045, .002)), rahmen_m, .012, 3),
      box("sicherung_maskenglas", (.11, .012, .042), aug + Vector((0, -.062, .002)), mk_m, .008, 3)]
schn = zyl("sicherung_schnorchel", .01, .32, aug + Vector((.085, -.01, .1)), mat("schnorchel", "e0b000", .4))
mt.append(schn)
for o in mt:
    an_knochen(o, S.rig, "head")
flosse_m = mat("flosse", "1b1e24", .3, Coat_Weight=.6)
FL = []
for sd_, j in (("L", "l"), ("R", "r")):
    fu = S.gm(f"joint-{j}-foot") if f"joint-{j}-foot" in S.koerper.vertex_groups else S.gm(f"joint-{j}-ankle")
    o = box("sicherung_flosse", (.11, .62, .015), fu + Vector((0, -.34, -.03)), flosse_m, .01)
    an_knochen(o, S.rig, "foot." + sd_); FL.append(o)
S.objekte += mt + FL
R1 = mensch("richter1", 55, ("f2f2ee", "d5d5cf"), ("1e2a44", "141c2e"), barfuss=False, alter=.55, muskel=.45, gewicht=.55)
R2 = mensch("richter2", 66, ("f2f2ee", "d5d5cf"), ("1e2a44", "141c2e"), barfuss=False, maenn=0.0, alter=.4, muskel=.4, gewicht=.45, haut="caucasian")
uhr_m = mat("stoppuhr", "1a1a1a", .4)
UHR = box("stoppuhr", (.05, .02, .065), (0, 0, 0), uhr_m, .008)
BRETT = box("klemmbrett", (.24, .012, .32), (0, 0, 0), mat("brett", "c9b48a", .7), .006)

# ======================================================================  Pool (Wasser z=0, Boden z=-3)
PL, PB, TIEF = 25.0, 12.5, 3.0


def fliesen(name, farbe, fuge="dfe6ea", skala=4.0, glanz=.08):
    m = bpy.data.materials.new(name); m.use_nodes = True; n = m.node_tree.nodes; l = m.node_tree.links; b = n["Principled BSDF"]
    tc = n.new("ShaderNodeTexCoord"); br = n.new("ShaderNodeTexBrick"); br.inputs["Scale"].default_value = skala
    br.inputs["Mortar Size"].default_value = .025; br.offset = 0; br.squash = 1; br.inputs["Brick Width"].default_value = .5
    br.inputs["Row Height"].default_value = .5
    br.inputs["Color1"].default_value = (*hexf(farbe), 1); br.inputs["Color2"].default_value = (*[c * .93 for c in hexf(farbe)], 1)
    br.inputs["Mortar"].default_value = (*hexf(fuge), 1)
    mp = n.new("ShaderNodeMapping"); l.new(tc.outputs["Object"], mp.inputs["Vector"]); l.new(mp.outputs[0], br.inputs["Vector"])
    l.new(br.outputs["Color"], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = glanz
    bp = n.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = .3; bp.invert = True; l.new(br.outputs["Fac"], bp.inputs["Height"])
    l.new(bp.outputs[0], b.inputs["Normal"]); b.inputs["Coat Weight"].default_value = .3
    return m


poolf = fliesen("poolfliesen", "8ccbe0", skala=8.0)
streifen = fliesen("bahnstreifen", "13355c", fuge="2b4f7a", skala=8.0)
deckf = fliesen("deck", "d9cbb2", fuge="b8a88d", skala=1.6, glanz=.55)
# Becken als Kasten ohne Deckel (Innenseite)
bm = bmesh.new()
v = [bm.verts.new((x, y, z)) for z in (-TIEF, .15) for y in (-PB / 2, PB / 2) for x in (-PL / 2, PL / 2)]
bm.faces.new((v[0], v[1], v[3], v[2]))            # Boden
for a_, b_, c_, d_ in ((0, 1, 5, 4), (1, 3, 7, 5), (3, 2, 6, 7), (2, 0, 4, 6)):
    bm.faces.new((v[a_], v[b_], v[c_], v[d_]))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
me = bpy.data.meshes.new("becken"); bm.to_mesh(me); bm.free()
becken_o = bpy.data.objects.new("becken", me); sc.collection.objects.link(becken_o); me.materials.append(poolf)
for p in me.polygons:
    p.flip()
# Bahnmarkierungen am Boden + T-Enden
for i in range(-2, 3):
    y_ = i * 2.5
    box("bahn", (PL - 4, .25, .004), (0, y_, -TIEF + .002), streifen, 0)
    for s_ in (-1, 1):
        box("bahn_t", (.25, 1.0, .004), (s_ * (PL / 2 - 2), y_, -TIEF + .002), streifen, 0)
# Deck rundherum + Ueberlaufrinne
for s_ in (-1, 1):
    box("deck", (PL + 14, 7, .3), (0, s_ * (PB / 2 + 3.5), 0), deckf, 0)
    box("deck", (7, PB, .3), (s_ * (PL / 2 + 3.5), 0, 0), deckf, 0)
rinne_m = mat("rinne", "e8e8e2", .3)
for s_ in (-1, 1):
    box("rinne", (PL + .3, .25, .08), (0, s_ * (PB / 2 + .12), .16), rinne_m, .02)
    box("rinne", (.25, PB + .3, .08), (s_ * (PL / 2 + .12), 0, .16), rinne_m, .02)
# Unterwasserlampen
lampe_m = emis("lampe", "fff4d8", 18)
for s_ in (-1, 1):
    for x_ in (-8, -2.7, 2.7, 8):
        zyl("lampe", .16, .03, (x_, s_ * (PB / 2 - .01), -.8), lampe_m, rot=(P / 2, 0, 0), v=24, bevel=False)
# Leiter
for x_ in (-.25, .25):
    bpy.ops.curve.primitive_bezier_curve_add(); cu = bpy.context.object
    sp = cu.data.splines[0]; sp.bezier_points[0].co = (PL / 2 - 3 + x_, -PB / 2 + .15, -1.4); sp.bezier_points[0].handle_left = sp.bezier_points[0].co
    sp.bezier_points[0].handle_right = (PL / 2 - 3 + x_, -PB / 2 + .15, .2)
    sp.bezier_points[1].co = (PL / 2 - 3 + x_, -PB / 2 - .45, .5); sp.bezier_points[1].handle_left = (PL / 2 - 3 + x_, -PB / 2 + .1, .9)
    sp.bezier_points[1].handle_right = sp.bezier_points[1].co
    cu.data.bevel_depth = .022; cu.data.materials.append(stahl)
for z_ in (-1.2, -.8, -.4):
    box("sprosse", (.5, .07, .02), (PL / 2 - 3, -PB / 2 + .17, z_), stahl, .005)
# Wasseroberflaeche (Glas, Wellen)
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0)); wasser = bpy.context.object; wasser.name = "wasser"
wasser.scale = (PL + .4, PB + .4, 1); bpy.ops.object.transform_apply(scale=True)
oc = wasser.modifiers.new("wellen", "OCEAN"); oc.geometry_mode = "DISPLACE"; oc.size = 1; oc.spatial_size = 10
oc.resolution = 12; oc.wave_scale = .06; oc.choppiness = .5; oc.wind_velocity = 4
sub = wasser.modifiers.new("s", "SUBSURF"); sub.levels = sub.render_levels = 0
wm = bpy.data.materials.new("wasser"); wm.use_nodes = True; n = wm.node_tree.nodes; l = wm.node_tree.links
for nd in list(n):
    if nd.type == "BSDF_PRINCIPLED":
        n.remove(nd)
gl = n.new("ShaderNodeBsdfGlass"); gl.inputs["IOR"].default_value = 1.333; gl.inputs["Roughness"].default_value = .01
gl.inputs["Color"].default_value = (*hexf("e9fbff"), 1)
l.new(gl.outputs[0], n["Material Output"].inputs["Surface"]); wasser.data.materials.append(wm)
for p in wasser.data.polygons:
    p.use_smooth = True
# Wasservolumen (nur Volumen, etwas kleiner als das Becken)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, -TIEF / 2 - .01)); vol = bpy.context.object; vol.name = "wasservolumen"
vol.scale = (PL - .04, PB - .04, TIEF - .03); bpy.ops.object.transform_apply(scale=True)
vm = bpy.data.materials.new("wasservol"); vm.use_nodes = True; n = vm.node_tree.nodes; l = vm.node_tree.links
for nd in list(n):
    if nd.type == "BSDF_PRINCIPLED":
        n.remove(nd)
pv = n.new("ShaderNodeVolumePrincipled"); pv.inputs["Color"].default_value = (*hexf("6fd2e6"), 1)
pv.inputs["Density"].default_value = .15; pv.inputs["Absorption Color"].default_value = (*hexf("1d8fb5"), 1)
VOL_D = pv.inputs["Density"]
l.new(pv.outputs[0], n["Material Output"].inputs["Volume"]); vol.data.materials.append(vm)
vol.visible_shadow = False
wasser.visible_shadow = False
for o in M.huellen:
    if o.name.endswith("_gesicht"):
        o.hide_render = True
M.objekte = [o for o in M.objekte if not o.name.endswith("_gesicht")]

# ======================================================================  Umgebung: Himmel, Meer, Hotel, Palmen, Liegen
w = bpy.data.worlds.new("welt"); sc.world = w; w.use_nodes = True; nt = w.node_tree
sky = nt.nodes.new("ShaderNodeTexSky"); sky.sun_disc = True; sky.sun_size = math.radians(.6)
sky.sun_elevation = math.radians(48); sky.sun_rotation = math.radians(200); sky.aerosol_density = .8
nt.links.new(sky.outputs[0], nt.nodes["Background"].inputs[0]); nt.nodes["Background"].inputs[1].default_value = .8
bpy.ops.object.light_add(type="SUN"); sonne = bpy.context.object; sonne.data.energy = 4.2; sonne.data.angle = math.radians(.8)
sonne.rotation_euler = (math.radians(42), 0, math.radians(200 - 90)); sonne.data.color = (1, .96, .9)
# Kaustik: Spot hoch oben mit Voronoi-Muster (Normal-Koordinaten), animiert ueber W
bpy.ops.object.light_add(type="SPOT", location=(0, 0, 40)); kau = bpy.context.object; kau.data.spot_size = math.radians(38)
kau.data.energy = 260000; kau.data.shadow_soft_size = 0; kau.data.use_nodes = True
ln = kau.data.node_tree.nodes; ll = kau.data.node_tree.links
tcn = ln.new("ShaderNodeTexCoord"); mpn = ln.new("ShaderNodeMapping"); mpn.inputs["Scale"].default_value = (55, 55, 55)
vor = ln.new("ShaderNodeTexVoronoi"); vor.voronoi_dimensions = "4D"; vor.feature = "SMOOTH_F1"; vor.inputs["Smoothness"].default_value = .6
vor2 = ln.new("ShaderNodeTexVoronoi"); vor2.voronoi_dimensions = "4D"; vor2.feature = "DISTANCE_TO_EDGE"
ll.new(tcn.outputs["Normal"], mpn.inputs["Vector"]); ll.new(mpn.outputs[0], vor2.inputs["Vector"])
cr = ln.new("ShaderNodeMapRange"); cr.inputs["From Min"].default_value = .0; cr.inputs["From Max"].default_value = .09
cr.inputs["To Min"].default_value = 1.0; cr.inputs["To Max"].default_value = .12
ll.new(vor2.outputs["Distance"], cr.inputs["Value"])
pw = ln.new("ShaderNodeMath"); pw.operation = "POWER"; pw.inputs[1].default_value = 2.5; ll.new(cr.outputs[0], pw.inputs[0])
em_ = ln["Emission"]; ll.new(pw.outputs[0], em_.inputs["Strength"]); em_.inputs["Color"].default_value = (1, .98, .92, 1)
KAU_W = vor2.inputs["W"]
kau.rotation_euler = (math.radians(-8), math.radians(-6), 0)
# Meer + Horizont (Hotel an der Kueste)
meer_m = mat("meer", "1f5c7a", .08, Coat_Weight=.5)
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 1200, -6)); meer = bpy.context.object; meer.scale = (6000, 2300, 1)
meer.data.materials.append(meer_m)
tx = bpy.data.textures.new("meerw", "CLOUDS"); tx.noise_scale = 3
bm2 = meer.modifiers.new("sub", "SUBSURF"); bm2.subdivision_type = "SIMPLE"; bm2.levels = bm2.render_levels = 6
dm = meer.modifiers.new("d", "DISPLACE"); dm.texture = tx; dm.strength = .4
# Kuestenhuegel
huegel_m = MH._stoff("huegel", "4f6340", rau=.95, skala=1)
for i, (x_, r_) in enumerate(((-2500, 1400), (1800, 1100), (4200, 1600))):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(x_, 3800, -300)); o = bpy.context.object
    o.scale = (r_, 500, 650); o.data.materials.append(huegel_m)
# Hotelfassade hinter dem Pool (Sueden), mit Balkonen und Fenstern
fass_m = mat("fassade", "efe6d6", .8); glas_m = mat("hotelglas", "2c3e4c", .05, Coat_Weight=1.0); gel_m = mat("gelaender", "e9e9e9", .3)
fass = box("fassade", (60, 14, 22), (0, -PB / 2 - 21, 10.8), fass_m, 0)
for st_ in range(6):
    z_ = 2 + st_ * 3.3
    for x_ in range(-26, 27, 4):
        box("fenster", (2.6, .1, 2.1), (x_, -PB / 2 - 13.97, z_ + .3), glas_m, 0)
        box("balkon", (3.4, 1.3, .14), (x_, -PB / 2 - 13.3, z_ - .9), fass_m, .02)
        box("gelaender", (3.4, .04, .9), (x_, -PB / 2 - 12.68, z_ - .4), glas_m, 0)
        box("handlauf", (3.4, .06, .05), (x_, -PB / 2 - 12.68, z_ + .07), gel_m, 0)
# Liegen + Sonnenschirme
liege_m = mat("liege", "f4f1ea", .5); holz_m = MH._stoff("teak", "8a5a32", rau=.6, skala=60)
schirm_m = MH._stoff("schirmst", "f3efe6", rau=.8, skala=200)
for i, x_ in enumerate(range(-10, 11, 4)):
    for s_ in (-1,):
        y_ = s_ * (PB / 2 + 2.6)
        box("liege", (.75, 1.95, .08), (x_, y_, .5), liege_m, .03)
        box("liege_lehne", (.75, .7, .08), (x_, y_ + .95, .75), liege_m, .03, rot=(-.7, 0, 0))
        for dx in (-.32, .32):
            for dy in (-.85, .75):
                box("liege_bein", (.05, .05, .35), (x_ + dx, y_ + dy, .33), holz_m, .01)
        box("handtuch", (.6, .9, .03), (x_, y_ - .3, .555), mat("tuch%d" % i, ["2b6cb0", "f2f2f2", "e8a33d"][i % 3], .9), .01)
        if i % 2 == 0:
            zyl("schirmstock", .03, 2.6, (x_ + 2, y_, 1.45), holz_m)
            bpy.ops.mesh.primitive_cone_add(radius1=1.6, depth=.6, vertices=8, location=(x_ + 2, y_, 2.85)); o = bpy.context.object
            o.data.materials.append(schirm_m)
# Palmen (Stamm aus Ringen + Wedel)
stamm_m = MH._stoff("stamm", "7a6248", rau=.95, skala=40); blatt_m = MH._stoff("palmblatt", "3e6b2c", rau=.7, skala=80)
for i, (x_, y_) in enumerate(((-15, 9), (15, 9), (-15, -9), (15.5, -8.5), (0, 11))):
    rr = random.Random(i)
    for k in range(14):
        zyl("stamm", .2 - k * .006, .5, (x_ + k * .03, y_, .2 + k * .48), stamm_m, v=12)
    top = Vector((x_ + 14 * .03, y_, .2 + 14 * .48))
    for k in range(9):
        a_ = 2 * P * k / 9 + rr.uniform(-.2, .2)
        bpy.ops.mesh.primitive_plane_add(size=1); o = bpy.context.object; o.scale = (2.6, .45, 1)
        bpy.ops.object.transform_apply(scale=True)
        for vv in o.data.vertices:
            vv.co.x += 1.3; vv.co.z -= (vv.co.x / 2.6) ** 2 * 1.3
        o.location = top; o.rotation_euler = (0, -.15, a_); o.data.materials.append(blatt_m)
        sm = o.modifiers.new("s", "SUBSURF"); sm.levels = sm.render_levels = 2
# Sauerstoffflasche mit Druckminderer, Schlauch, Maske (am Beckenrand)
o2_m = mat("o2koerper", "e9e9e6", .35, Coat_Weight=.6); o2_s = mat("o2schulter", "f5f5f5", .3)
O2P = Vector((-3.2, -PB / 2 - .7, .15))
O2 = [zyl("o2", .11, 1.2, O2P + Vector((0, 0, .75)), o2_m), zyl("o2", .11, .12, O2P + Vector((0, 0, 1.33)), o2_s),
      zyl("o2", .03, .08, O2P + Vector((0, 0, 1.43)), stahl), box("o2_regler", (.08, .06, .1), O2P + Vector((0, -.05, 1.5)), stahl, .01),
      zyl("o2_manometer", .035, .02, O2P + Vector((.06, -.09, 1.52)), mat("mano", "f0f0f0", .2), rot=(P / 2, 0, 0)),
      box("o2_wagen", (.36, .36, .06), O2P + Vector((0, 0, .18)), mat("wagen", "2a2a2a", .5), .01)]
gruen = mat("o2gruen", "2f8f4e", .4)
O2.append(zyl("o2_band", .112, .05, O2P + Vector((0, 0, 1.2)), gruen))
bpy.ops.curve.primitive_bezier_curve_add(); schl = bpy.context.object; schl.data.bevel_depth = .009
schl.data.materials.append(mat("schlauch", "d9eef0", .2, Transmission_Weight=.5))
SCHL_P = schl.data.splines[0].bezier_points
o2maske = box("o2maske", (.07, .06, .09), (0, 0, 0), mat("maske", "dfeff2", .1, Transmission_Weight=.6), .03, 4)

# Kaustik nur unter Wasser (Lichtverknuepfung)
kc = bpy.data.collections.new("kaustik_empf")
for o in bpy.data.objects:
    if o.type in ("MESH", "CURVE") and (o.name.startswith(("becken", "bahn", "lampe", "sprosse", "taucher", "sicherung")) or o.parent in (M.rig, S.rig)):
        kc.objects.link(o)
try:
    kau.light_linking.receiver_collection = kc
except Exception as e:
    print("LICHTLINK", e)
# ======================================================================  Kamera + Ablauf
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam
cam.data.clip_start = .02; cam.data.clip_end = 20000; cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
cam.data.dof.use_dof = True
LIEG = Vector((-1.0, -1.6, -TIEF))      # Fusspunkt des liegenden Tauchers (Kopf Richtung +y)
KOPF_R = M.gm("joint-head")


def pose_taucher(t, art):
    M.zuruecksetzen(); r = M.rig; r.rotation_euler = (0, 0, 0)
    atm = math.sin(t * 1.3)
    if art == "liegen":
        r.rotation_euler = (-P / 2, 0, 0); r.location = LIEG + Vector((0, 0, .14))
        M.dreh("upperarm01.L", x=-.3, z=1.6); M.dreh("upperarm01.R", x=-.3, z=-1.6)
        M.dreh("lowerarm01.L", z=2.2); M.dreh("lowerarm01.R", z=-2.2)
        M.dreh("upperleg01.L", z=-.06, x=-.03); M.dreh("upperleg01.R", z=.06, x=-.03)
        M.dreh("neck01", x=-.12)
    elif art == "rand":          # im Wasser am Beckenrand, Arme auf dem Rand, Maske vor dem Gesicht
        r.location = Vector((-3.2, -PB / 2 + .45, -1.45)); r.rotation_euler = (0, 0, P)
        M.dreh("upperarm01.L", x=1.5, z=.1); M.dreh("upperarm01.R", x=1.5, z=-.1)
        M.dreh("lowerarm01.L", x=-1.3); M.dreh("lowerarm01.R", x=-1.7)
        M.dreh("upperleg01.L", x=-.25 + .1 * atm); M.dreh("lowerleg01.L", x=.4); M.dreh("upperleg01.R", x=.1 - .1 * atm); M.dreh("lowerleg01.R", x=.3)
    elif art == "abtauchen":
        k = ease((t - 13.9) / 1.9)
        r.location = Vector((-3.2, -PB / 2 + .7 + 1.4 * k, -1.45 - 1.3 * k)); r.rotation_euler = (-.9 * k, 0, P)
        M.dreh("upperarm01.L", x=1.5 * (1 - k), z=-.6 * k); M.dreh("upperarm01.R", x=1.5 * (1 - k), z=.6 * k)
        M.dreh("lowerarm01.L", x=-1.3 * (1 - k)); M.dreh("lowerarm01.R", x=-1.3 * (1 - k))
        M.dreh("upperleg01.L", x=-.3 * math.sin(t * 6)); M.dreh("upperleg01.R", x=.3 * math.sin(t * 6))
    elif art == "auftauchen":
        k = ease((t - 24.3) / 3.1)
        r.location = LIEG.lerp(Vector((-1.0, -.4, -1.5)), k) + Vector((0, 0, .14)); r.rotation_euler = (-P / 2 * (1 - k), 0, 0)
        M.dreh("upperarm01.L", x=.3 + 2.4 * (1 - k), z=-.3); M.dreh("upperarm01.R", x=.3 + 2.4 * (1 - k), z=.3)
        M.dreh("lowerarm01.L", x=-2.2 * (1 - k)); M.dreh("lowerarm01.R", x=-2.2 * (1 - k))
        M.dreh("upperleg01.L", x=-.35 * math.sin(t * 5)); M.dreh("upperleg01.R", x=.35 * math.sin(t * 5))
    elif art == "oben":         # an der Oberflaeche, OK-Zeichen
        k = ease((t - 27.4) / .8)
        r.location = Vector((-1.0, -.4, -1.48 + .1 * math.sin(t * 2))); r.rotation_euler = (0, 0, .25)
        M.dreh("upperarm01.R", x=1.1 + .5 * k, z=.1); M.dreh("lowerarm01.R", x=-1.6 * k)
        M.dreh("upperarm01.L", x=.6, z=-.4); M.dreh("lowerarm01.L", x=-.5)
        M.dreh("neck01", x=-.15)


def pose_rest(t):
    S.zuruecksetzen(); sr = S.rig
    sr.location = Vector((2.2, 1.6, -2.1 + .05 * math.sin(t * 1.1))); sr.rotation_euler = (-1.25, 0, 2.6)
    S.dreh("upperarm01.L", z=-.3, x=.4); S.dreh("upperarm01.R", z=.3, x=.4); S.dreh("lowerarm01.L", x=-.6); S.dreh("lowerarm01.R", x=-.6)
    S.dreh("upperleg01.L", x=-.3 * math.sin(t * 1.6)); S.dreh("upperleg01.R", x=.3 * math.sin(t * 1.6)); S.dreh("neck01", x=-.6)
    for i, (rr, ort, dr) in enumerate(((R1, (-.2, -PB / 2 - .9, .15), .15), (R2, (-2.0, -PB / 2 - 1.1, .15), -.2))):
        rr.zuruecksetzen(); rr.rig.location = ort; rr.rig.rotation_euler = (0, 0, P + dr + .05 * math.sin(t * .4 + i))
        rr.dreh("upperarm01.L", z=-.62); rr.dreh("upperarm01.R", z=.62)
        rr.dreh("neck01", x=.55); rr.dreh("spine03", x=.12)
        if i == 0:
            rr.dreh("upperarm01.R", z=.3, x=.9); rr.dreh("lowerarm01.R", x=-1.2)
        else:
            rr.dreh("upperarm01.L", z=-.3, x=.7); rr.dreh("lowerarm01.L", x=-1.5); rr.dreh("upperarm01.R", z=.3, x=.6); rr.dreh("lowerarm01.R", x=-1.5)
    bpy.context.view_layer.update()


def punkt(m, bone, v):
    pb = m.rig.pose.bones[bone]; bn = m.rig.data.bones[bone]
    return m.rig.matrix_world @ pb.matrix @ bn.matrix_local.inverted() @ Vector(v)


# Einstellungen (von, bis, pos0, ziel0, pos1, ziel1, linse); Koordinaten absolut
pose_taucher(0, "liegen"); bpy.context.view_layer.update()
KO = punkt(M, "head", nase + Vector((0, .03, .0)))        # Gesicht liegend
BR = punkt(M, "spine03", Vector((0, -.12, 1.28)))         # Brust liegend
print("KO", KO, "BR", BR)
SZ = [
    (0.00, 2.10, KO + Vector((.25, .3, .55)), KO, KO + Vector((.18, .22, .45)), KO, 50),
    (2.10, 3.40, KO + Vector((.1, -.15, .42)), KO + Vector((0, -.01, 0)), KO + Vector((.08, -.12, .36)), KO + Vector((0, -.01, 0)), 55),
    (3.40, 5.90, (16, 13, 7), (-1, -2, -.5), (13.5, 14, 6.2), (-1, -2, -.5), 22),
    (5.90, 8.90, (5.5, -4.5, -1.3), BR + Vector((0, -.2, 0)), (4.6, -5.2, -1.6), BR + Vector((0, -.3, 0)), 20),
    (8.90, 12.50, (-2.0, -PB / 2 + 1.6, .12), (-3.2, -PB / 2 + .3, -.1), (-2.3, -PB / 2 + 1.5, .1), (-3.2, -PB / 2 + .3, -.05), 32),
    (12.50, 15.80, (-1.4, -PB / 2 + 3.6, -.05), (-3.0, -PB / 2 + 1.3, -1.0), (-1.2, -PB / 2 + 4.2, -.5), (-2.9, -PB / 2 + 2.0, -2.0), 24),
    (15.80, 17.00, (2.8, 1.2, -2.0), BR, (2.6, .9, -2.05), BR, 24),
    (17.00, 17.84, (-2.6, -3.2, -2.3), BR, (-2.5, -3.1, -2.35), BR, 26),
    (17.84, 18.78, (.2, 4.5, -1.2), KO, (.1, 4.3, -1.3), KO, 30),
    (18.78, 19.84, (0, 1.3, 2.8), BR + Vector((0, .3, 0)), (0, 1.3, 2.6), BR + Vector((0, .3, 0)), 26),
    (19.84, 22.10, BR + Vector((1.0, .1, .5)), BR + Vector((0, .1, .05)), BR + Vector((.85, .15, .45)), BR + Vector((0, .1, .05)), 35),
    (22.10, 24.30, (-.6, -PB / 2 - 3.4, 1.95), (-1.0, -1.2, -2.6), (-.9, -PB / 2 - 3.2, 1.9), (-1.0, -1.2, -2.6), 24),
    (24.30, 27.40, (-1.0, 2.6, -2.9), (-1.0, -.6, -1.3), (-1.0, 2.4, -2.8), (-1.0, -.4, -.6), 22),
    (27.40, 28.90, (1.8, 2.6, .5), (-1.0, -.4, .2), (1.6, 2.3, .45), (-1.0, -.4, .25), 32),
    (28.90, 32.40, (3.4, -1.6, -1.9), BR + Vector((0, -.2, -.05)), (3.0, -1.2, -2.1), BR + Vector((0, -.2, -.05)), 24),
    (32.40, 34.10, KO + Vector((.32, .38, .65)), KO, KO + Vector((.25, .3, .55)), KO, 50),
]


def zustand(t):
    if t < 9.0 or (15.8 <= t < 24.3) or t >= 32.4 or (3.4 <= t < 5.9):
        art = "liegen"
    elif t < 13.9:
        art = "rand"
    elif t < 15.8:
        art = "abtauchen"
    elif t < 27.4:
        art = "auftauchen"
    else:
        art = "oben"
    if 28.9 <= t < 32.4:
        art = "liegen"
    pose_taucher(t, art); pose_rest(t)
    # Kaustik + Wellen (Zeitraffer schneller in der Minuten-Montage)
    tf = t * (6.0 if 15.8 <= t < 19.84 else 1.0)
    KAU_W.default_value = tf * .35
    wasser.modifiers["wellen"].time = tf * .8
    # Sauerstoff-Maske am Gesicht nur bei "rand"
    m_on = art == "rand"
    o2maske.hide_render = not m_on; schl.hide_render = False
    if m_on:
        mp = punkt(M, "head", nase + Vector((0, -.03, -.015)))
        o2maske.location = mp; o2maske.rotation_euler = (0, 0, P)
        a = O2P + Vector((0, -.05, 1.5)); e = mp
    else:
        a = O2P + Vector((0, -.05, 1.5)); e = O2P + Vector((.25, -.2, .2))
        o2maske.hide_render = False; o2maske.location = e + Vector((0, 0, .02)); o2maske.rotation_euler = (P / 2, 0, 0)
    SCHL_P[0].co = a; SCHL_P[0].handle_left = a; SCHL_P[0].handle_right = a + Vector((0, 0, -.6))
    SCHL_P[1].co = e; SCHL_P[1].handle_left = e + Vector((0, -.2, .1)); SCHL_P[1].handle_right = e
    # Stoppuhr/Klemmbrett in den Haenden der Richter
    UHR.location = punkt(R1, "lowerarm02.R", R1.gm("joint-r-hand")); UHR.rotation_euler = (1.0, 0, P)
    BRETT.location = (punkt(R2, "lowerarm02.L", R2.gm("joint-l-hand")) + punkt(R2, "lowerarm02.R", R2.gm("joint-r-hand"))) / 2 + Vector((0, 0, .05))
    BRETT.rotation_euler = (.9, 0, P - .2)
    # Kamera
    nr = 0
    for i, s in enumerate(SZ):
        if s[0] <= t < s[1]:
            k = (t - s[0]) / (s[1] - s[0]); k = ease(k) * .8 + k * .2
            pos = lerpv(s[2], s[4], k); ziel = lerpv(s[3], s[5], k); lin = s[6]; nr = i
            break
    if nr == 12:     # Auftauchen: Kamera folgt dem Kopf
        ziel = punkt(M, "head", KOPF_R) + Vector((0, 0, .1))
    if nr in (4, 13):
        ziel = punkt(M, "head", KOPF_R) if nr == 4 else ziel
    cam.location = pos; d = ziel - pos; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    if nr in (0, 1, 15):     # Gesicht von oben: Kopf soll im Bild oben sein (+y)
        zv = -d.normalized(); yv = Vector((0, 1, 0)); yv = (yv - zv * yv.dot(zv)).normalized(); xv = yv.cross(zv)
        cam.rotation_euler = Matrix((xv, yv, zv)).transposed().to_euler()
    cam.data.lens = lin; cam.data.dof.focus_distance = d.length
    cam.data.dof.aperture_fstop = 4.0 if d.length < 1.5 else 11
    unten = pos.z < 0
    VOL_D.default_value = .15
    sc.view_settings.exposure = -.7 if unten else -1.3
    cam.location += Vector((.003 * math.sin(t * 7), .002 * math.cos(t * 5), .003 * math.sin(t * 9))) * min(d.length, 6)


os.makedirs(A.ordner, exist_ok=True)
N = int(round(D * A.fps))
liste = [int(round(float(x) * A.fps)) for x in A.nur.split(",")] if A.nur else list(range(A.start, N))
for f in liste:
    pfad = os.path.join(A.ordner, f"atem_{f:04d}.png")
    if os.path.exists(pfad) and not A.nur:
        continue
    zustand(f / A.fps); bpy.context.view_layer.update(); zustand(f / A.fps)
    sc.render.filepath = pfad
    bpy.ops.render.render(write_still=True); print("FERTIG", pfad, flush=True)
