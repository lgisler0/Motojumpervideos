"""Geschichte: Ein Mann hat einen Job: ins Wasser springen (Laso Schaller, Cascata del Salto, Maggia TI, 4.8.2015, 58,8 m, GWR).
Szene: Felsschlucht mit Wasserfall (animiertes Wasserband + Gischt), Becken (Glaswasser, Schaumfeld durch Luftblasen),
Absprungbrett am Felsrand, Wald auf den Kanten, Rettungsboot mit Helfern, Zuschauer auf Felsen, Vergleichsturm (schief),
Springer (MPFB) in Badehose mit Brustkamera; freier Fall in Echtzeit (58,8 m in ca. 3,5 s), Spritzer-Krone + Wellenringe.
python3 klippe3d.py <ordner> [--nur t1,t2] [--start i] [--samples n]"""
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
D = 27.5
H = 58.8
TS = 20.30                    # Absprung
TF = TS + math.sqrt(2 * H / 9.81) * 1.02     # Eintauchen (leicht gebremst durch Luft)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = A.samples; sc.cycles.use_denoising = True
sc.cycles.max_bounces = 5; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.transmission_bounces = 4
sc.cycles.adaptive_threshold = .03; sc.cycles.volume_bounces = 0; sc.cycles.volume_step_rate = 4
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1080, 1920, A.skala
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"; sc.view_settings.exposure = -2.4
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


def trimmen(o, gruppen, z_min=None):
    idx = {g.index: g.name for g in o.vertex_groups}
    me = o.data; rz = me.attributes.get("rest_z"); zv = [0.0] * len(me.vertices)
    if rz:
        rz.data.foreach_get("value", zv)
    bm = bmesh.new(); bm.from_mesh(me); dl = bm.verts.layers.deform.active; bm.verts.ensure_lookup_table()
    weg = [v for v in bm.verts if (dl and sum(val for gi, val in v[dl].items() if idx.get(gi, "").startswith(gruppen)) > .4) or (z_min is not None and zv[v.index] < z_min)]
    bmesh.ops.delete(bm, geom=weg, context="VERTS"); bm.to_mesh(me); bm.free()


def nackt_oben(m, hosenfarbe, barfuss=True):
    knie = m.gm("joint-l-knee").z
    for o in m.huellen:
        if o.name.endswith(("_hemd", "_hand", "_gesicht")):
            o.hide_render = True
        elif o.name.endswith("_hose"):
            farbe_setzen(o.active_material, *hosenfarbe); trimmen(o, ("lowerleg", "foot", "toe"), z_min=knie + .12)
            o.modifiers["versatz"].strength = .006
    for o in m.helm:
        o.hide_render = True
    weg = list(m.helm) + [o for o in m.huellen if o.name.endswith(("_hemd", "_hand", "_gesicht"))]
    if barfuss:
        for o in m.stiefel:
            o.hide_render = True
        weg += list(m.stiefel)
        mk = m.koerper.modifiers.get("fuesse")
        if mk:
            m.koerper.modifiers.remove(mk)
    m.objekte = [o for o in m.objekte if o not in weg]


# ======================================================================  Springer + Helfer
S = MH.Arbeiter(name="springer", seed=31, maenn=1.0, alter=.3, muskel=.8, gewicht=.3, haut="caucasian", weste=False)
nackt_oben(S, ("1f4fa8", "16387a"))
hals = S.gm("joint-neck")
kam = [box("springer_gopro", (.045, .03, .035), (0, hals.y - .2, hals.z - .22), mat("gopro", "141414", .4), .006),
       box("springer_linse", (.02, .01, .02), (0, hals.y - .218, hals.z - .22), mat("linse", "0a0a10", .05, Coat_Weight=1.0), .004)]
for o in kam:
    an_knochen(o, S.rig, "spine03")
S.objekte += kam
HELF = []
for i in range(2):
    h = MH.Arbeiter(name=f"helfer{i}", seed=60 + i, maenn=1.0, alter=.4, muskel=.55, gewicht=.5, haut="caucasian", weste=False)
    for o in h.huellen:
        if o.name.endswith("_hemd"):
            farbe_setzen(o.active_material, "e84a1a", "b83a12")      # Rettungsweste-Farbe
        elif o.name.endswith("_hose"):
            farbe_setzen(o.active_material, "1b1b1b")
        elif o.name.endswith(("_hand", "_gesicht")):
            o.hide_render = True
    for o in h.helm:
        o.hide_render = True
    HELF.append(h)

# ======================================================================  Schlucht
fels = bpy.data.materials.new("fels"); fels.use_nodes = True; n = fels.node_tree.nodes; l = fels.node_tree.links; b = n["Principled BSDF"]
tc = n.new("ShaderNodeTexCoord")
nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = .6; nz.inputs["Detail"].default_value = 14; nz.inputs["Roughness"].default_value = .62
l.new(tc.outputs["Object"], nz.inputs["Vector"])
vo = n.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = .6; l.new(tc.outputs["Object"], vo.inputs["Vector"])
cr = n.new("ShaderNodeValToRGB"); el = cr.color_ramp.elements
el[0].position = .3; el[0].color = (*hexf("4a4741"), 1); el[1].position = .7; el[1].color = (*hexf("a19d92"), 1)
e3 = el.new(.5); e3.color = (*hexf("6f6a60"), 1)
l.new(nz.outputs["Fac"], cr.inputs["Fac"])
moos = n.new("ShaderNodeTexNoise"); moos.inputs["Scale"].default_value = .08; moos.inputs["Detail"].default_value = 6; l.new(tc.outputs["Object"], moos.inputs["Vector"])
mr = n.new("ShaderNodeValToRGB"); mr.color_ramp.elements[0].position = .58; mr.color_ramp.elements[1].position = .66; l.new(moos.outputs["Fac"], mr.inputs["Fac"])
mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; l.new(mr.outputs[0], mx.inputs[0]); l.new(cr.outputs[0], mx.inputs[6]); mx.inputs[7].default_value = (*hexf("3d5a2a"), 1)
l.new(mx.outputs[2], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = .85
bp = n.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = .9; bp.inputs["Distance"].default_value = .15
hb = n.new("ShaderNodeMath"); hb.operation = "ADD"; l.new(nz.outputs["Fac"], hb.inputs[0]); l.new(vo.outputs["Distance"], hb.inputs[1])
l.new(hb.outputs[0], bp.inputs["Height"]); l.new(bp.outputs[0], b.inputs["Normal"])


def wand(name, ort, groesse, rot, staerke=4.0, skala=.08, sub=8):
    bpy.ops.mesh.primitive_plane_add(size=1, location=ort, rotation=rot); o = bpy.context.object; o.name = name; o.scale = groesse
    bpy.ops.object.transform_apply(scale=True)
    sb = o.modifiers.new("s", "SUBSURF"); sb.subdivision_type = "SIMPLE"; sb.levels = sb.render_levels = sub
    tx = bpy.data.textures.new(name, "CLOUDS"); tx.noise_scale = skala; tx.noise_depth = 3
    dp = o.modifiers.new("d", "DISPLACE"); dp.texture = tx; dp.strength = staerke; dp.texture_coords = "GLOBAL"
    o.data.materials.append(fels)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


# Hauptwand hinter dem Becken (senkrecht, y=9), Plateau oben, Seitenwaende
WAND = wand("hauptwand", (0, 9.5, H / 2 - 4), (80, H + 12, 1), (P / 2, 0, 0), 2.2, 7.0)
wand("plateau", (0, 40, H - .4), (80, 60, 1), (0, 0, 0), 1.0, 9.0, 7)
for s_ in (-1, 1):
    wand("seitenwand", (s_ * 24, -12, H / 2 - 3), (50, H + 14, 1), (P / 2, 0, s_ * (P / 2 - .25)), 3.0, 8.0)
    wand("seitenplateau", (s_ * 44, -12, H + .5), (40, 80, 1), (0, 0, 0), 1.2, 9.0, 7)
wand("beckengrund", (0, -5, -8.5), (70, 40, 1), (0, 0, 0), 1.2, 4.0, 6)
# Absprungkante + Brett
holz = MH._stoff("brett", "8a6a45", rau=.7, skala=60); stahl = mat("stahl", "a7abb0", .3, 1.0)
BRETT = box("brett", (.6, 2.6, .08), (2, 7.6, H + .25), holz, .01)
for dy in (8.3, 9.3):
    box("brettstuetze", (.06, .06, .7), (2, dy, H - .1), stahl, .005)
bpy.ops.mesh.primitive_cylinder_add(radius=.015, depth=1, vertices=8); seil = bpy.context.object; seil.data.materials.append(mat("sicherungsseil", "e8c21a", .6))
# Wasserfall (Band entlang der Wand bei x=-7) mit wanderndem Rauschen
bpy.ops.mesh.primitive_plane_add(size=1, location=(-7, 8.6, H / 2 - .5), rotation=(P / 2, 0, 0)); wf = bpy.context.object
wf.scale = (6.5, H + 1, 1); bpy.ops.object.transform_apply(scale=True)
sb = wf.modifiers.new("s", "SUBSURF"); sb.subdivision_type = "SIMPLE"; sb.levels = sb.render_levels = 6
wfm = bpy.data.materials.new("wasserfall"); wfm.use_nodes = True; n = wfm.node_tree.nodes; l = wfm.node_tree.links; b = n["Principled BSDF"]
tc = n.new("ShaderNodeTexCoord"); mp = n.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (2.5, .12, 2.5); l.new(tc.outputs["Object"], mp.inputs["Vector"])
nz = n.new("ShaderNodeTexNoise"); nz.noise_dimensions = "4D"; nz.inputs["Scale"].default_value = 3; nz.inputs["Detail"].default_value = 10
l.new(mp.outputs[0], nz.inputs["Vector"]); WF_W = nz.inputs["W"]
cr = n.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].position = .38; cr.color_ramp.elements[1].position = .62; l.new(nz.outputs["Fac"], cr.inputs["Fac"])
b.inputs["Base Color"].default_value = (.93, .96, 1, 1); b.inputs["Roughness"].default_value = .4
l.new(cr.outputs[0], b.inputs["Alpha"]); b.inputs["Emission Color"].default_value = (1, 1, 1, 1); b.inputs["Emission Strength"].default_value = .15
wf.data.materials.append(wfm)
# Becken: Wasserflaeche (Glas, Wellen) + Schaumfeld (Luftblasen der Tanks)
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, -4, 0)); wasser = bpy.context.object; wasser.scale = (70, 40, 1)
bpy.ops.object.transform_apply(scale=True)
oc = wasser.modifiers.new("wellen", "OCEAN"); oc.geometry_mode = "DISPLACE"; oc.size = 1; oc.spatial_size = 20; oc.resolution = 12
oc.wave_scale = .12; oc.choppiness = .6; oc.wind_velocity = 6
wm = bpy.data.materials.new("wasser"); wm.use_nodes = True; n = wm.node_tree.nodes; l = wm.node_tree.links
for nd in list(n):
    if nd.type == "BSDF_PRINCIPLED":
        n.remove(nd)
gl = n.new("ShaderNodeBsdfGlass"); gl.inputs["IOR"].default_value = 1.333; gl.inputs["Roughness"].default_value = .02
gl.inputs["Color"].default_value = (*hexf("7fb8a8"), 1)
tc = n.new("ShaderNodeTexCoord"); sx = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Object"], sx.inputs[0])
# Schaum: Kreis um den Aufprallpunkt (0,4) + Rauschen
ds = n.new("ShaderNodeVectorMath"); ds.operation = "DISTANCE"; l.new(tc.outputs["Object"], ds.inputs[0]); ds.inputs[1].default_value = (0, 8, 0)
sch = n.new("ShaderNodeTexNoise"); sch.inputs["Scale"].default_value = 1.4; sch.inputs["Detail"].default_value = 8; sch.noise_dimensions = "4D"
l.new(tc.outputs["Object"], sch.inputs["Vector"]); SCH_W = sch.inputs["W"]
rm = n.new("ShaderNodeMapRange"); rm.inputs["From Min"].default_value = 5.5; rm.inputs["From Max"].default_value = 1.5; l.new(ds.outputs["Value"], rm.inputs["Value"])
mu = n.new("ShaderNodeMath"); mu.operation = "MULTIPLY"; l.new(rm.outputs[0], mu.inputs[0]); l.new(sch.outputs["Fac"], mu.inputs[1])
gt = n.new("ShaderNodeMath"); gt.operation = "MULTIPLY"; gt.inputs[1].default_value = 1.6; l.new(mu.outputs[0], gt.inputs[0])
SCHAUM = gt.inputs[1]
wd = n.new("ShaderNodeBsdfDiffuse"); wd.inputs["Color"].default_value = (.95, .97, .97, 1)
ms = n.new("ShaderNodeMixShader"); l.new(gt.outputs[0], ms.inputs[0]); l.new(gl.outputs[0], ms.inputs[1]); l.new(wd.outputs[0], ms.inputs[2])
l.new(ms.outputs[0], n["Material Output"].inputs["Surface"]); wasser.data.materials.append(wm)
for p in wasser.data.polygons:
    p.use_smooth = True
wasser.visible_shadow = False
# Wasservolumen (fuer Unterwasser-Einstellung)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -4, -4.3)); vol = bpy.context.object; vol.scale = (69, 39, 8.5)
bpy.ops.object.transform_apply(scale=True)
vm = bpy.data.materials.new("wasservol"); vm.use_nodes = True; n = vm.node_tree.nodes; l = vm.node_tree.links
for nd in list(n):
    if nd.type == "BSDF_PRINCIPLED":
        n.remove(nd)
pv = n.new("ShaderNodeVolumePrincipled"); pv.inputs["Color"].default_value = (*hexf("6fc7b0"), 1); pv.inputs["Density"].default_value = .14
pv.inputs["Absorption Color"].default_value = (*hexf("2c8a76"), 1); l.new(pv.outputs[0], n["Material Output"].inputs["Volume"])
vol.data.materials.append(vm); vol.visible_shadow = False
# Luftblasen der Tanks (steigen auf)
blase_m = mat("blase", "ffffff", .05, Transmission_Weight=.7, Emission_Color=(1, 1, 1, 1), Emission_Strength=.3)
bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=.04); me = bpy.data.meshes.new("blase"); bm.to_mesh(me); bm.free()
me.materials.append(blase_m)
for p in me.polygons:
    p.use_smooth = True
BLASEN = []
rb = random.Random(2)
TANKS = [(math.cos(a) * 3.2, 8 - 4 + math.sin(a) * 3.2) for a in (k * P / 3 for k in range(6))]
for i in range(500):
    o = bpy.data.objects.new("blase", me); sc.collection.objects.link(o)
    tx_, ty_ = rb.choice(TANKS); o["p"] = (tx_ + rb.gauss(0, .5), ty_ + rb.gauss(0, .5), rb.random(), rb.uniform(.6, 1.6))
    s_ = rb.uniform(.4, 1.8); o.scale = (s_, s_, s_); BLASEN.append(o)
for tx_, ty_ in TANKS:
    bpy.ops.mesh.primitive_cylinder_add(radius=.15, depth=1.2, location=(tx_, ty_, -7.9), rotation=(0, P / 2, 0)); o = bpy.context.object
    o.data.materials.append(mat("tank", "d8d8d8", .3, .8)); o.hide_render = True
# Wald auf den Kanten (Nadelbaeume)
nadel = MH._stoff("nadel", "2f4a24", rau=.9, skala=20); stamm = mat("stamm", "4a3526", .9)
rt = random.Random(5)
for i in range(160):
    seite = rt.choice(("hinten", "links", "rechts"))
    if seite == "hinten":
        x_, y_ = rt.uniform(-40, 40), rt.uniform(14, 60)
    else:
        s_ = -1 if seite == "links" else 1; x_, y_ = s_ * rt.uniform(28, 60), rt.uniform(-40, 20)
    h_ = rt.uniform(9, 22)
    bpy.ops.mesh.primitive_cone_add(radius1=h_ * .22, depth=h_, vertices=10, location=(x_, y_, H + h_ / 2 + .5)); c = bpy.context.object
    c.data.materials.append(nadel)
    bpy.ops.mesh.primitive_cylinder_add(radius=.2, depth=2, vertices=8, location=(x_, y_, H + .5)); c.data.materials  # Stamm
    bpy.context.object.data.materials.append(stamm)
# Boot mit Helfern
boot_m = mat("boot", "e85a1a", .5)
bpy.ops.mesh.primitive_cylinder_add(radius=.38, depth=3.8, vertices=24, location=(6.5, -1.5, .2), rotation=(P / 2, 0, .3)); boot = bpy.context.object
boot.scale = (1, .55, 1); boot.data.materials.append(boot_m)
box("bootboden", (1.2, 3.4, .1), (6.5, -1.5, .12), mat("bootboden", "2a2a2a", .7), .02, rot=(0, 0, .3))
# Zuschauer auf Felsen (einfach) + Vergleichsturm
zm = [mat("zusch%d" % i, c, .7) for i, c in enumerate(("d62828", "2a6fdb", "f2c12e", "2e9d4a", "ffffff"))]
ZU = []
for i in range(14):
    x_ = rt.uniform(-20, -11) if i % 2 else rt.uniform(11, 20); y_ = rt.uniform(-14, -6)
    ZU.append(box("zuschauer", (.4, .3, 1.1), (x_, y_, 1.5 + .55), zm[i % 5], .1))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=.12, location=(x_, y_, 2.8)); bpy.context.object.data.materials.append(mat("zkopf%d" % i, "e0b090", .6))
    wand("zfels%d" % i, (x_, y_, 1.0), (2.5, 2.5, 1), (0, 0, 0), .5, 1.0, 4)
turm_m = mat("turm", "f1ede4", .6)
TURM = []
tz = Vector((13, -4, 0))
for k in range(8):
    r_ = 7.7 if k < 7 else 6.0; h_ = 7.0 if k < 7 else 5.0
    bpy.ops.mesh.primitive_cylinder_add(radius=r_ - .8, depth=h_, vertices=48, location=tz + Vector((0, 0, h_ / 2 + k * 7.0))); TURM.append(bpy.context.object)
    TURM[-1].data.materials.append(turm_m)
    bpy.ops.mesh.primitive_cylinder_add(radius=r_, depth=.5, vertices=48, location=tz + Vector((0, 0, (k + 1) * 7.0 - .25))); TURM.append(bpy.context.object)
    TURM[-1].data.materials.append(turm_m)
    for j in range(24 if k < 7 else 12):
        a_ = 2 * P * j / (24 if k < 7 else 12)
        bpy.ops.mesh.primitive_cylinder_add(radius=.18, depth=h_ - .6, vertices=8, location=tz + Vector((r_ * .93 * math.cos(a_), r_ * .93 * math.sin(a_), h_ / 2 + k * 7.0)))
        TURM.append(bpy.context.object); TURM[-1].data.materials.append(turm_m)
for o in TURM:
    o.location = tz + Matrix.Rotation(math.radians(4), 3, "X") @ (o.location - tz)
    o.rotation_euler = (math.radians(4), 0, 0)
# Spritzer: Tropfen + Kronenkegel + Wellenringe
tropf_m = mat("tropfen", "ffffff", .1, Transmission_Weight=.4, Emission_Color=(1, 1, 1, 1), Emission_Strength=.2)
bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=1, radius=.05); me = bpy.data.meshes.new("tropfen"); bm.to_mesh(me); bm.free(); me.materials.append(tropf_m)
TROPF = []
rs = random.Random(8)
for i in range(420):
    o = bpy.data.objects.new("tropfen", me); sc.collection.objects.link(o)
    a = rs.uniform(0, 2 * P)
    if i % 5 < 3:      # Krone: schraeg nach aussen
        v = rs.uniform(2.5, 6); vz = rs.uniform(3, 7)
    else:              # Saeule: steil nach oben
        v = rs.uniform(0, 1.2); vz = rs.uniform(7, 14)
    o["v"] = (math.cos(a) * v, math.sin(a) * v, vz, rs.uniform(.6, 2.2)); TROPF.append(o)
RINGE = []
for i in range(3):
    bpy.ops.mesh.primitive_torus_add(major_radius=1, minor_radius=.06, major_segments=64); o = bpy.context.object
    o.data.materials.append(mat("ring%d" % i, "ffffff", .3, Emission_Color=(1, 1, 1, 1), Emission_Strength=.2)); RINGE.append(o)
# Himmel + Sonne
w = bpy.data.worlds.new("welt"); sc.world = w; w.use_nodes = True; nt = w.node_tree
sky = nt.nodes.new("ShaderNodeTexSky"); sky.sun_disc = True; sky.sun_elevation = math.radians(52); sky.sun_rotation = math.radians(160)
nt.links.new(sky.outputs[0], nt.nodes["Background"].inputs[0]); nt.nodes["Background"].inputs[1].default_value = .8
bpy.ops.object.light_add(type="SUN"); sonne = bpy.context.object; sonne.data.energy = 3.0; sonne.data.angle = math.radians(1)
sonne.rotation_euler = (math.radians(38), 0, math.radians(160 - 90))

# ======================================================================  Ablauf
LAND = Vector((2, 4.6, 0))


def sprung_pos(t):
    if t < TS:
        return Vector((2, 7.0, H + .3)), 0.0
    tt = t - TS; k = min(1, tt / (TF - TS))
    z = H + .3 - (H + .3) * (tt / (TF - TS)) ** 2
    y = 7.0 - 2.4 * k
    if t >= TF:
        tu = t - TF; z = -2.2 * (1 - math.exp(-tu * 2.5)) + 3.0 * max(0, tu - 1.2) ** 1.5
        z = min(z, -.9) if tu > 1.2 and z > -.9 else z
        if tu > 2.0:
            z = -.85 + .05 * math.sin(tu * 3)
    return Vector((2, y, z)), tt


def figuren(t):
    S.zuruecksetzen(); r = S.rig
    p, tt = sprung_pos(t)
    if t < TS - .5:
        r.location = p; r.rotation_euler = (0, 0, 0)
        S.dreh("upperarm01.L", z=-.6 + .05 * math.sin(t)); S.dreh("upperarm01.R", z=.6); S.dreh("neck01", x=.45)
    elif t < TS:
        k = ease((t - (TS - .5)) / .5)
        r.location = p; r.rotation_euler = (0, 0, 0)
        S.dreh("upperarm01.L", z=-.6 + 1.0 * k); S.dreh("upperarm01.R", z=.6 - 1.0 * k); S.dreh("neck01", x=.3)
        S.dreh("upperleg01.L", x=-.4 * k); S.dreh("lowerleg01.L", x=.4 * k)
    elif t < TF:
        r.location = p; r.rotation_euler = (.05 * math.sin(tt * 2), 0, 0)
        kr = 1 - ease((tt - 2.6) / .6)                 # vor dem Eintauchen Arme an den Koerper
        S.dreh("upperarm01.L", z=(.3 + .5 * math.sin(tt * 7)) * kr - .72 * (1 - kr), x=.5 * math.cos(tt * 7) * kr)
        S.dreh("upperarm01.R", z=-(.3 + .5 * math.sin(tt * 7 + 1)) * kr + .72 * (1 - kr), x=.5 * math.cos(tt * 7 + 1) * kr)
        S.dreh("upperleg01.L", x=-.15 * kr); S.dreh("upperleg01.R", x=.05 * kr); S.dreh("lowerleg01.L", x=.25 * kr)
        S.dreh("neck01", x=.25)
    else:
        r.location = p; r.rotation_euler = (0, 0, -.6)
        k = ease((t - TF - 1.6) / .6)
        S.dreh("upperarm01.R", z=.6 - 2.3 * k, x=.2); S.dreh("lowerarm01.R", x=-.5 * k); S.dreh("upperarm01.L", z=-.2, x=.6)
    # Helfer im Boot
    for i, h in enumerate(HELF):
        h.zuruecksetzen(); h.rig.location = Vector((6.5, -1.5, .15)) + Matrix.Rotation(.3, 3, "Z") @ Vector((0, -.8 + i * 1.5, 0))
        h.rig.rotation_euler = (0, 0, P + .5); h.dreh("upperleg01.L", x=-1.5); h.dreh("upperleg01.R", x=-1.5)
        h.dreh("lowerleg01.L", x=1.5); h.dreh("lowerleg01.R", x=1.5); h.rig.location.z = -.35
        h.dreh("neck01", x=-.3 if t < TF else .1)
    bpy.context.view_layer.update()


def effekte(t):
    WF_W.default_value = t * 1.8
    SCH_W.default_value = t * .4
    wasser.modifiers["wellen"].time = t * .9
    SCHAUM.default_value = 1.6 + (2.5 * math.exp(-(t - TF) / 1.2) if t > TF else 0)
    for o in BLASEN:
        x, y, f, v = o["p"]; z = -7.8 + ((f + t * .12 * v) % 1) * 7.7
        o.location = (x + .15 * math.sin(t * 2 + f * 9), y, z)
    an = t >= TF
    tu = t - TF
    for o in TROPF:
        vx, vy, vz, s_ = o["v"]
        if an and tu < 2.0:
            o.hide_render = False
            o.location = LAND + Vector((vx * tu, vy * tu, max(-.2, vz * tu - 4.9 * tu * tu)))
            s2 = s_ * max(.2, 1 - tu * .4); o.scale = (s2, s2, s2 * (1 + vz * .08))
        else:
            o.hide_render = True
    for i, o in enumerate(RINGE):
        k = tu - i * .35
        o.hide_render = not (an and 0 < k < 3)
        if not o.hide_render:
            s_ = .5 + k * 2.2; o.location = LAND + Vector((0, 0, .05)); o.scale = (s_, s_, 1)


def punkt(m, bone, v):
    pb = m.rig.pose.bones[bone]; bn = m.rig.data.bones[bone]
    return m.rig.matrix_world @ pb.matrix @ bn.matrix_local.inverted() @ Vector(v)


bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam
cam.data.clip_start = .03; cam.data.clip_end = 3000; cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
cam.data.dof.use_dof = True
SK = S.gm("joint-head")
# (von, bis, typ, daten, linse); typ "s": relativ zum Springer (pos0, pos1); "frei": (pos0, ziel0, pos1, ziel1)
SZ = [
    (0.00, 1.82, "s", ((3.2, -2.6, -1.2), (2.8, -2.4, -1.6)), 32),
    (1.82, 3.36, "frei", ((4.2, 5.0, H + 2.4), (2.0, 1.5, 0), (4.0, 4.8, H + 2.3), (2.0, 2.0, 0)), 20),
    (3.36, 5.06, "frei", ((6, -22, 1.4), (2, 7.5, H - 6), (6, -21, 1.3), (2, 7.5, H - 6)), 18),
    (5.06, 6.08, "frei", ((26, -70, 32), (0, 5, 22), (22, -72, 30), (0, 5, 22)), 22),
    (6.08, 7.90, "frei", ((4.5, 5.0, H + 1.6), "S", (4.2, 4.6, H + 1.5), "S"), 32),
    (7.90, 9.60, "frei", ((2.6, 10.5, H + 3.6), (2.0, 0.0, 0), (2.5, 10.3, H + 3.5), (2.0, .5, 0)), 22),
    (9.60, 12.70, "frei", ((10, -32, 20), (2, 6, H - 2), (9, -33, 18), (2, 6, 8)), 22),
    (12.70, 15.34, "frei", ((12, -75, 28), (12, 5, 27), (6, -78, 27), (12, 5, 27)), 26),
    (15.34, 17.80, "frei", ((-2.5, -1, -6.8), (1.5, 4.5, -3.2), (-2.2, -.6, -6.6), (1.5, 4.5, -3.0)), 20),
    (17.80, 19.96, "frei", ((6, -3, 6), (1.5, 4.2, 0), (5, -2.5, 5.4), (1.5, 4.2, 0)), 26),
    (19.96, 21.68, "s", ((4.0, -3.0, -.4), (4.2, -3.6, -2.4)), 26),
    (21.68, 23.20, "s", ((5.0, -6.0, -2.5), (5.0, -6.0, -2.5)), 26),
    (23.20, 25.62, "frei", ((-5, -10, .9), (2, 4.6, 1.2), (-5.4, -10.5, 1.0), (2, 4.6, 1.6)), 30),
    (25.62, 27.60, "frei", ((5.5, -4.0, 1.4), "S", (5.2, -3.6, 1.3), "S"), 34),
]


def zustand(t):
    for s in SZ:
        if s[0] <= t < s[1]:
            break
    k = (t - s[0]) / (s[1] - s[0]); k = ease(k) * .8 + k * .2
    tf = TS + 1.4 + t * .4 if t < 1.82 else t        # Aufhaenger: Zeitlupe mitten aus dem Fall
    figuren(tf); effekte(tf)
    kopf = punkt(S, "head", SK)
    if s[2] == "s":
        pos = kopf + lerpv(s[3][0], s[3][1], k); ziel = kopf - Vector((0, 0, .6))
    else:
        p0, z0, p1, z1 = s[3]; pos = lerpv(p0, p1, k)
        ziel = (kopf - Vector((0, 0, .5))) if z0 == "S" else lerpv(z0, z1, k)
    vol.hide_render = not (pos.z < 0)
    cam.location = pos; d = ziel - pos; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = s[-1]; cam.data.dof.focus_distance = d.length; cam.data.dof.aperture_fstop = 4 if d.length < 5 else 11
    cam.location += Vector((.004 * math.sin(t * 7), .003 * math.cos(t * 5), .004 * math.sin(t * 9))) * min(d.length, 8)
    sc.view_settings.exposure = -1.6 if pos.z < 0 else -2.4
    for o in TURM:
        o.hide_render = not (12.7 <= t < 15.34)
    seil.hide_render = True


os.makedirs(A.ordner, exist_ok=True)
N = int(round(D * A.fps))
liste = [int(round(float(x) * A.fps)) for x in A.nur.split(",")] if A.nur else list(range(A.start, N))
for f in liste:
    pfad = os.path.join(A.ordner, f"klippe_{f:04d}.png")
    if os.path.exists(pfad) and not A.nur:
        continue
    zustand(f / A.fps); bpy.context.view_layer.update(); zustand(f / A.fps)
    sc.render.filepath = pfad
    bpy.ops.render.render(write_still=True); print("FERTIG", pfad, flush=True)
