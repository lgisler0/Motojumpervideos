"""ThrustSSC in 3D (Blender/Cycles). Masse: Laenge 16.5 m, Breite 3.7 m (Quellen: GWR, IMechE).
Aufbau nach Fotos/Beschreibung: zwei Spey-Triebwerksgondeln links und rechts vom Cockpit, Cockpit dazwischen,
spitze Nase vor den Einlaessen, 2 feste Vorderraeder unter den Gondeln, 2 versetzte lenkende Hinterraeder im schmalen Heck,
Seitenleitwerk mit Hoehenleitwerk oben (T-Leitwerk), mattschwarz, Union Flag am Leitwerk, Aluminiumraeder ohne Reifen.
python3 thrust3d.py <ordner> --dauer D [--nur t1,t2] [--start i]"""
import bpy, bmesh, math, random, sys, os, argparse, json
from mathutils import Vector

ap = argparse.ArgumentParser()
ap.add_argument("ordner"); ap.add_argument("--nur", default=""); ap.add_argument("--skala", type=int, default=50)
ap.add_argument("--samples", type=int, default=16); ap.add_argument("--fps", type=int, default=15)
ap.add_argument("--start", type=int, default=0); ap.add_argument("--dauer", type=float, default=30.2)
A = ap.parse_args(sys.argv[1:])
HIER = os.path.dirname(os.path.abspath(__file__))

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = A.samples; sc.cycles.use_denoising = True
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.transparent_max_bounces = 8
sc.cycles.transmission_bounces = 3
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1080, 1920, A.skala
sc.render.use_persistent_data = True
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"; sc.view_settings.exposure = -1.1
P = math.pi


def hexf(h):
    return tuple(((int(h[i:i + 2], 16) / 255) ** 2.2) for i in (0, 2, 4))


def mat(name, farbe, rau=.4, metall=0, leucht=0, lf=None, cc=0):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*farbe, 1); b.inputs["Roughness"].default_value = rau; b.inputs["Metallic"].default_value = metall
    if cc:
        b.inputs["Coat Weight"].default_value = cc; b.inputs["Coat Roughness"].default_value = .08
    if leucht:
        b.inputs["Emission Color"].default_value = (*(lf or farbe), 1); b.inputs["Emission Strength"].default_value = leucht
    return m, b


def obj_aus(bm, name, m, glatt=True):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o)
    if m:
        me.materials.append(m)
    if glatt:
        for p in me.polygons:
            p.use_smooth = True
    return o


auto = bpy.data.objects.new("ThrustSSC", None); sc.collection.objects.link(auto)


def kind(o):
    o.parent = auto; return o


SCHWARZ, _ = mat("lack", hexf("08080a"), .42, 0, cc=.25)
ALU, _ = mat("alu", hexf("c9ccd1"), .18, 1)
TITAN, _ = mat("duese", hexf("4a4038"), .35, 1)
DUNKEL, _ = mat("einlass", hexf("050505"), .6)
GLAS, _ = mat("haube", hexf("1a2230"), .04, .5)


def rotations_koerper(name, profil, m, nv=40, yc=0.0, zc=1.0, ellipse=1.0):
    """profil: [(x, radius)] entlang x (Nase bei x=0, Heck +x)"""
    bm = bmesh.new(); ringe = []
    for x, r in profil:
        ringe.append([bm.verts.new((x, yc + r * math.cos(2 * P * k / nv), zc + r * ellipse * math.sin(2 * P * k / nv))) for k in range(nv)])
    spitze = bm.verts.new((profil[0][0] - .001, yc, zc))
    for k in range(nv):
        bm.faces.new((spitze, ringe[0][(k + 1) % nv], ringe[0][k]))
    for r0, r1 in zip(ringe, ringe[1:]):
        for k in range(nv):
            bm.faces.new((r0[k], r0[(k + 1) % nv], r1[(k + 1) % nv], r1[k]))
    bm.faces.new(list(reversed(ringe[-1])))
    return obj_aus(bm, name, m)


# --- Mittelrumpf: spitze Nase (vor den Einlaessen), Cockpit, langes schmales Heck
rumpf = [(0, .02), (.3, .12), (.8, .24), (1.4, .34), (2.2, .42), (3.2, .48), (4.5, .52), (6, .53), (8, .52), (10, .5), (12, .45), (14, .38), (15.8, .3), (16.5, .22)]
kind(rotations_koerper("rumpf", rumpf, SCHWARZ, 48, 0, 1.05, 1.15))
# Unterteil des Hecks etwas tiefer (beherbergt Hinterraeder)
bpy.ops.mesh.primitive_cube_add(size=1, location=(13.4, 0, .72)); o = kind(bpy.context.object); o.scale = (5.6, .66, .7); o.data.materials.append(SCHWARZ)
bv = o.modifiers.new("b", "BEVEL"); bv.width = .2; bv.segments = 4
# --- Cockpit-Haube
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=40, ring_count=20, location=(4.4, 0, 1.55)); hb = kind(bpy.context.object)
hb.scale = (1.15, .38, .32); hb.data.materials.append(GLAS)
for p in hb.data.polygons:
    p.use_smooth = True
# --- Zwei Triebwerksgondeln (Spey) links/rechts des Cockpits
gondel = [(1.5, .55), (1.7, .66), (2.2, .7), (3.5, .72), (6, .72), (8, .7), (9.3, .64), (9.9, .56)]
for s in (1, -1):
    g = kind(rotations_koerper(f"gondel{s}", gondel, SCHWARZ, 48, s * 1.2, 1.05, 1.0))
    # Einlass: dunkles Loch + Alu-Lippe
    bpy.ops.mesh.primitive_torus_add(major_radius=.6, minor_radius=.05, location=(1.52, s * 1.2, 1.05), rotation=(0, P / 2, 0))
    kind(bpy.context.object).data.materials.append(ALU)
    bpy.ops.mesh.primitive_cylinder_add(radius=.56, depth=.08, location=(1.58, s * 1.2, 1.05), rotation=(0, P / 2, 0))
    kind(bpy.context.object).data.materials.append(DUNKEL)
    # Duese (Nachbrenner) hinten
    bpy.ops.mesh.primitive_cylinder_add(radius=.52, depth=.9, vertices=40, location=(10.2, s * 1.2, 1.05), rotation=(0, P / 2, 0))
    d = kind(bpy.context.object); d.data.materials.append(TITAN)
    bpy.ops.mesh.primitive_cylinder_add(radius=.44, depth=.05, vertices=40, location=(10.66, s * 1.2, 1.05), rotation=(0, P / 2, 0))
    kind(bpy.context.object).data.materials.append(DUNKEL)
    # Verbindung Gondel-Rumpf (Verkleidung)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(5.6, s * .6, 1.0)); v = kind(bpy.context.object)
    v.scale = (7.4, .9, .5); v.data.materials.append(SCHWARZ); bv = v.modifiers.new("b", "BEVEL"); bv.width = .15; bv.segments = 3

# --- Seitenleitwerk (T-Leitwerk) mit Union Flag
fin_m = bpy.data.materials.new("fin"); fin_m.use_nodes = True; n = fin_m.node_tree.nodes; l = fin_m.node_tree.links; b = n["Principled BSDF"]
img = n.new("ShaderNodeTexImage"); img.image = bpy.data.images.load(os.path.join(HIER, "unionflag.png")); img.extension = "CLIP"
tc = n.new("ShaderNodeTexCoord"); mp = n.new("ShaderNodeMapping")
# Flagge auf dem oberen Teil des Leitwerks: x 13.6..15.8, z 2.15..3.05
mp.inputs["Location"].default_value = (-13.6 / 2.2, -2.15 / .9 + 0, 0); mp.inputs["Scale"].default_value = (1 / 2.2, 1, 1 / .9)
sep = n.new("ShaderNodeSeparateXYZ"); com = n.new("ShaderNodeCombineXYZ")
l.new(tc.outputs["Object"], sep.inputs[0]); l.new(sep.outputs["X"], com.inputs["X"]); l.new(sep.outputs["Z"], com.inputs["Y"])
mp.vector_type = "POINT"; mp.inputs["Location"].default_value = (-13.6 / 2.2, -2.15 / .9, 0)
l.new(com.outputs[0], mp.inputs[0]); l.new(mp.outputs[0], img.inputs[0])
mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.inputs[6].default_value = (*hexf("0b0b0d"), 1)
l.new(img.outputs["Alpha"], mx.inputs[0]); l.new(img.outputs["Color"], mx.inputs[7]); l.new(mx.outputs[2], b.inputs["Base Color"])
b.inputs["Roughness"].default_value = .32; b.inputs["Coat Weight"].default_value = .6
bm = bmesh.new()
prof = [(0, 0), (.08, .09), (.45, .07), (1, 0), (.45, -.07), (.08, -.09)]
lagen = []
for xl, c, z in ((11.4, 4.9, 1.45), (14.4, 2.0, 3.1)):
    lagen.append([bm.verts.new((xl + c * px, py * (1 if z < 2 else .6), z)) for px, py in prof])
for k in range(len(prof)):
    bm.faces.new((lagen[0][k], lagen[0][(k + 1) % 6], lagen[1][(k + 1) % 6], lagen[1][k]))
bm.faces.new(lagen[1])
kind(obj_aus(bm, "fin", fin_m))
bpy.ops.mesh.primitive_cube_add(size=1, location=(15.3, 0, 3.12)); hl = kind(bpy.context.object); hl.scale = (1.5, 2.6, .07); hl.data.materials.append(SCHWARZ)
bv = hl.modifiers.new("b", "BEVEL"); bv.width = .03; bv.segments = 2

# --- Raeder: Aluminium-Scheiben ohne Reifen (Durchmesser ~0.93 m)
RAEDER = []
for x, y in ((3.6, 1.2), (3.6, -1.2), (13.0, .14), (14.0, -.14)):
    bpy.ops.mesh.primitive_cylinder_add(radius=.465, depth=.22, vertices=48, location=(x, y, .465), rotation=(P / 2, 0, 0))
    r = kind(bpy.context.object); r.data.materials.append(ALU); RAEDER.append(r)
    bv = r.modifiers.new("b", "BEVEL"); bv.width = .04; bv.segments = 3
# Pitotrohr an der Nase
bpy.ops.mesh.primitive_cylinder_add(radius=.025, depth=1.1, location=(-.5, 0, 1.05), rotation=(0, P / 2, 0)); kind(bpy.context.object).data.materials.append(ALU)

# --- Nachbrenner-Flammen (Emission, durchsichtig), Schockdiamanten
FLAMMEN = []
fl_m = bpy.data.materials.new("flamme"); fl_m.use_nodes = True; n = fl_m.node_tree.nodes; l = fl_m.node_tree.links
for k in list(n):
    n.remove(k)
out = n.new("ShaderNodeOutputMaterial"); em = n.new("ShaderNodeEmission"); tr = n.new("ShaderNodeBsdfTransparent"); add = n.new("ShaderNodeAddShader")
tc = n.new("ShaderNodeTexCoord"); sp = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Generated"], sp.inputs[0])
cr = n.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (1, .38, .06, 1); cr.color_ramp.elements[1].color = (1, .6, .2, 1)
l.new(sp.outputs["Z"], cr.inputs["Fac"]); l.new(cr.outputs[0], em.inputs["Color"])
FLAMM_ST = em.inputs["Strength"]; FLAMM_ST.default_value = 18
l.new(em.outputs[0], add.inputs[0]); l.new(tr.outputs[0], add.inputs[1]); l.new(add.outputs[0], out.inputs["Surface"])
for s in (1, -1):
    bpy.ops.mesh.primitive_cone_add(radius1=.42, radius2=.05, depth=3.2, vertices=32, location=(12.3, s * 1.2, 1.05), rotation=(0, P / 2, 0))
    f = kind(bpy.context.object); f.data.materials.append(fl_m); f.visible_shadow = False; FLAMMEN.append(f)
    for i in range(3):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=.16, location=(11.3 + i * .75, s * 1.2, 1.05)); dd = kind(bpy.context.object)
        dd.scale = (1.6, 1, 1); dd.data.materials.append(fl_m); dd.visible_shadow = False; FLAMMEN.append(dd)
    bpy.ops.object.light_add(type="POINT", location=(11.5, s * 1.2, 1.05)); pl = kind(bpy.context.object); pl.data.energy = 4000; pl.data.color = (1, .6, .3)
    FLAMMEN.append(pl)

# --- Staubfahne hinter dem Auto
st_m = bpy.data.materials.new("staub"); st_m.use_nodes = True; n = st_m.node_tree.nodes; l = st_m.node_tree.links
for k in list(n):
    n.remove(k)
out = n.new("ShaderNodeOutputMaterial"); df = n.new("ShaderNodeBsdfDiffuse"); tr = n.new("ShaderNodeBsdfTransparent"); mx = n.new("ShaderNodeMixShader")
df.inputs["Color"].default_value = (*hexf("d9cdb4"), 1)
tc = n.new("ShaderNodeTexCoord"); mp = n.new("ShaderNodeMapping"); nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.2; nz.inputs["Detail"].default_value = 8
cr = n.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].position = .42; cr.color_ramp.elements[1].position = .75
gr = n.new("ShaderNodeSeparateXYZ"); fade = n.new("ShaderNodeMath"); fade.operation = "MULTIPLY"
l.new(tc.outputs["Object"], mp.inputs[0]); l.new(mp.outputs[0], nz.inputs["Vector"]); l.new(nz.outputs["Fac"], cr.inputs["Fac"])
l.new(tc.outputs["Generated"], gr.inputs[0])
inv = n.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0; l.new(gr.outputs["Z"], inv.inputs[1])
l.new(cr.outputs[0], fade.inputs[0]); l.new(inv.outputs[0], fade.inputs[1])
dichte = n.new("ShaderNodeMath"); dichte.operation = "MULTIPLY"; dichte.inputs[1].default_value = .85; l.new(fade.outputs[0], dichte.inputs[0])
l.new(dichte.outputs[0], mx.inputs["Fac"]); l.new(tr.outputs[0], mx.inputs[1]); l.new(df.outputs[0], mx.inputs[2]); l.new(mx.outputs[0], out.inputs["Surface"])
STAUB_MAP = mp; STAUB_D = dichte.inputs[1]
bpy.ops.mesh.primitive_cone_add(radius1=7, radius2=.8, depth=90, vertices=48, location=(60, 0, 2.5), rotation=(0, -P / 2, 0))
staub = kind(bpy.context.object); staub.data.materials.append(st_m); staub.visible_shadow = False

# --- Schockwelle (Schlieren-Effekt): fast senkrechte, leicht brechende Scheibe
sw_m = bpy.data.materials.new("schock"); sw_m.use_nodes = True; n = sw_m.node_tree.nodes; l = sw_m.node_tree.links
for k in list(n):
    n.remove(k)
out = n.new("ShaderNodeOutputMaterial"); gl = n.new("ShaderNodeBsdfRefraction"); gl.inputs["IOR"].default_value = 1.04; gl.inputs["Roughness"].default_value = .02
l.new(gl.outputs[0], out.inputs["Surface"])
bpy.ops.mesh.primitive_cone_add(radius1=14, radius2=.3, depth=3, vertices=64, location=(1.2, 0, 1.05), rotation=(0, P / 2, 0))
schock = kind(bpy.context.object); schock.data.materials.append(sw_m); schock.visible_shadow = False

# ======================================================================  Wueste (Black Rock Desert)
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; nt = w.node_tree
sky = nt.nodes.new("ShaderNodeTexSky")
try:
    sky.sky_type = "NISHITA"
except Exception:
    pass
sky.sun_elevation = math.radians(28); sky.sun_rotation = math.radians(140)
nt.links.new(sky.outputs[0], nt.nodes["Background"].inputs[0]); nt.nodes["Background"].inputs[1].default_value = .3
bpy.ops.object.light_add(type="SUN"); sonne = bpy.context.object
sonne.rotation_euler = (math.radians(62), 0, math.radians(140 - 90)); sonne.data.energy = 4.5; sonne.data.color = (1, .93, .84); sonne.data.angle = .01

pl_m = bpy.data.materials.new("playa"); pl_m.use_nodes = True; n = pl_m.node_tree.nodes; l = pl_m.node_tree.links; b = n["Principled BSDF"]
tc = n.new("ShaderNodeTexCoord"); mp = n.new("ShaderNodeMapping"); l.new(tc.outputs["Object"], mp.inputs[0])
vo = n.new("ShaderNodeTexVoronoi"); vo.feature = "DISTANCE_TO_EDGE"; vo.inputs["Scale"].default_value = 1.6; l.new(mp.outputs[0], vo.inputs["Vector"])
risse = n.new("ShaderNodeMath"); risse.operation = "LESS_THAN"; risse.inputs[1].default_value = .012; l.new(vo.outputs["Distance"], risse.inputs[0])
nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = .03; nz.inputs["Detail"].default_value = 6; l.new(mp.outputs[0], nz.inputs["Vector"])
cr = n.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (*hexf("a89a80"), 1); cr.color_ramp.elements[1].color = (*hexf("c4b79c"), 1)
l.new(nz.outputs["Fac"], cr.inputs["Fac"])
mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.inputs[7].default_value = (*hexf("857760"), 1)
l.new(risse.outputs[0], mx.inputs[0]); l.new(cr.outputs[0], mx.inputs[6])
# Spur in der Mitte (dunklere Fahrbahn-Markierung)
sp = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Object"], sp.inputs[0]); ab = n.new("ShaderNodeMath"); ab.operation = "ABSOLUTE"; l.new(sp.outputs["Y"], ab.inputs[0])
sm = n.new("ShaderNodeMath"); sm.operation = "LESS_THAN"; sm.inputs[1].default_value = 6; l.new(ab.outputs[0], sm.inputs[0])
sm2 = n.new("ShaderNodeMath"); sm2.operation = "MULTIPLY"; sm2.inputs[1].default_value = .18; l.new(sm.outputs[0], sm2.inputs[0])
mx2 = n.new("ShaderNodeMix"); mx2.data_type = "RGBA"; mx2.inputs[7].default_value = (*hexf("9d917a"), 1)
l.new(sm2.outputs[0], mx2.inputs[0]); l.new(mx.outputs[2], mx2.inputs[6]); l.new(mx2.outputs[2], b.inputs["Base Color"])
b.inputs["Roughness"].default_value = .95
BODEN_MAP = mp
bpy.ops.mesh.primitive_plane_add(size=40000); playa = bpy.context.object; playa.data.materials.append(pl_m)
# Berge am Horizont
berg_m, _ = mat("berg", hexf("8c8a8e"), .95)
r = random.Random(4)
tx = bpy.data.textures.new("bergtex", "CLOUDS"); tx.noise_scale = .35
for i in range(22):
    a_ = r.uniform(0, 2 * P); d = r.uniform(7000, 13000)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=5, radius=1, location=(d * math.cos(a_), d * math.sin(a_), -150))
    o = bpy.context.object; o.scale = (r.uniform(1800, 4000), r.uniform(1800, 4000), r.uniform(500, 1100)); o.data.materials.append(berg_m)
    dm = o.modifiers.new("d", "DISPLACE"); dm.texture = tx; dm.strength = .35; dm.texture_coords = "LOCAL"
    for p in o.data.polygons:
        p.use_smooth = True
# Markierungspfosten der Messmeile
PFOSTEN = []
pf_m, _ = mat("pfosten", hexf("1a1a1a"), .5)
for i in range(24):
    bpy.ops.mesh.primitive_cube_add(size=1); p = bpy.context.object; p.scale = (.4, .4, 3); p.data.materials.append(pf_m); PFOSTEN.append(p)
    bpy.ops.mesh.primitive_cube_add(size=1); q = bpy.context.object; q.scale = (.42, .42, .8)
    q.data.materials.append(mat(f"pfr{i}", hexf("e8e8e8") if i % 2 else hexf("d23c2c"), .5)[0]); PFOSTEN.append(q)

# --- Vergleich (Stand): Mensch 1.8 m + normales Auto 4.5 m
mensch_m, _ = mat("mensch", hexf("e6e2da"), .7)
VERGL = []
def mensch(x, y):
    obs = []
    bpy.ops.mesh.primitive_uv_sphere_add(radius=.12, location=(x, y, 1.68)); obs.append(bpy.context.object)
    bpy.ops.mesh.primitive_cylinder_add(radius=.19, depth=.62, location=(x, y, 1.22)); obs.append(bpy.context.object)
    for dy in (-.1, .1):
        bpy.ops.mesh.primitive_cylinder_add(radius=.075, depth=.9, location=(x, y + dy, .46)); obs.append(bpy.context.object)
        bpy.ops.mesh.primitive_cylinder_add(radius=.055, depth=.65, location=(x, y + dy * 2.4, 1.18)); obs.append(bpy.context.object)
    for o in obs:
        o.data.materials.append(mensch_m)
    return obs
VERGL += mensch(6.0, -3.2)
pkw_m, _ = mat("pkw", hexf("8a9bb0"), .25, .6, cc=.5)
bpy.ops.mesh.primitive_cube_add(size=1, location=(-3.6, -4.6, .72)); k1 = bpy.context.object; k1.scale = (4.5, 1.8, .7)
bpy.ops.mesh.primitive_cube_add(size=1, location=(-3.4, -4.6, 1.25)); k2 = bpy.context.object; k2.scale = (2.3, 1.6, .55)
for o in (k1, k2):
    o.data.materials.append(pkw_m); bv = o.modifiers.new("b", "BEVEL"); bv.width = .18; bv.segments = 4; VERGL.append(o)
for dx in (-1.4, 1.4):
    for dy in (-.85, .85):
        bpy.ops.mesh.primitive_cylinder_add(radius=.33, depth=.22, location=(-3.6 + dx, -4.6 + dy, .33), rotation=(P / 2, 0, 0))
        o = bpy.context.object; o.data.materials.append(DUNKEL); VERGL.append(o)

# ======================================================================  Kamera + Ablauf
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam; cam.data.lens = 35; cam.data.clip_end = 60000; cam.data.sensor_fit = "VERTICAL"
cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = 5.6


def ease(x):
    x = min(1, max(0, x)); return x * x * (3 - 2 * x)


def lerpv(a, b, k):
    return tuple(x + (y - x) * k for x, y in zip(a, b))


D = A.dauer
t_name, t_1997, t_schall, t_eng, t_lang, t_30, t_rek = 3.88, 8.2, 12.2, 14.1, 19.96, 24.04, 26.98
STAND = (t_lang - .1, t_30 - .1)
START = ((-13, -12, 1.5), (6.5, 0, 1.5))
KEYS = [(0, *START), (t_name - .6, (-12, -12.5, 1.4), (6.5, 0, 1.5)),
        (t_name + .5, (28, -19, 4.5), (9.5, 0, 1.4)), (t_1997 - .2, (32, -14, 3.6), (9.5, 0, 1.4)),
        (t_1997 + 1.2, (-160, -170, 90), (20, 0, 0)), (t_schall - .3, (-120, -140, 60), (10, 0, 0)), (t_eng - .4, (-60, -80, 25), (8, 0, 1)),
        (t_eng + .4, (24, -6, 2.2), (10, 0, 1.1)), (t_lang - .2, (20, -5, 1.6), (10, 0, 1.1)),
        (t_lang - .1, (6, -64, 3.5), (5.5, -2, 1.8)), (t_30 - .1, (4, -61, 3.2), (5.5, -2, 1.8)),
        (t_30 + .3, (-14, 5, .7), (6, 0, 1.2)), (t_rek, (-12, 7, .8), (6, 0, 1.2)),
        (D - .9, *START), (D, *START)]
V_VIS = 95.0  # sichtbare Geschwindigkeit fuer Bodentextur (m/s)


def fahrt(t):
    return not (STAND[0] <= t < STAND[1])


def zustand(t):
    faehrt = fahrt(t)
    # Boden laeuft unter dem Auto durch (Auto faehrt Richtung -x)
    weg = V_VIS * t if faehrt else V_VIS * STAND[0]
    if t >= STAND[1]:
        weg = V_VIS * (t - (STAND[1] - STAND[0]))
    BODEN_MAP.inputs["Location"].default_value = (-weg, 0, 0)
    STAUB_MAP.inputs["Location"].default_value = (-weg * .04, 0, t * .3)
    STAUB_D.default_value = .85 if faehrt else 0
    staub.hide_render = not faehrt
    for f in FLAMMEN:
        f.hide_render = not faehrt
    FLAMM_ST.default_value = 7 + 2.5 * math.sin(t * 37) * math.sin(t * 13)
    schock.hide_render = not (t_schall <= t <= t_eng - .2)
    for o in VERGL:
        o.hide_render = faehrt
    for i, p in enumerate(PFOSTEN):
        k = i // 2
        x = ((k * 100 + weg) % 2400) - 600
        p.location = (x, -16, 1.5 if i % 2 == 0 else 3.2)
    for r in RAEDER:
        r.rotation_euler[1] = weg / .465 if faehrt else 0
    auto.location = (0, 0, .015 * math.sin(t * 41) if faehrt else 0)
    for a, b in zip(KEYS, KEYS[1:]):
        if a[0] <= t <= b[0]:
            k = ease((t - a[0]) / max(b[0] - a[0], 1e-6)); pos = lerpv(a[1], b[1], k); ziel = lerpv(a[2], b[2], k); break
    else:
        pos, ziel = KEYS[-1][1], KEYS[-1][2]
    if faehrt:
        pos = (pos[0], pos[1] + .04 * math.sin(t * 29), pos[2] + .04 * math.sin(t * 23))
    cam.location = Vector(pos); d = Vector(ziel) - Vector(pos); cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.dof.focus_distance = d.length


os.makedirs(A.ordner, exist_ok=True)
N = int(round(D * A.fps))
liste = [int(round(float(x) * A.fps)) for x in A.nur.split(",")] if A.nur else list(range(A.start, N))
for f in liste:
    pfad = os.path.join(A.ordner, f"thrust_{f:04d}.png")
    if os.path.exists(pfad) and not A.nur:
        continue
    zustand(f / A.fps); sc.render.filepath = pfad
    bpy.ops.render.render(write_still=True); print("FERTIG", pfad, flush=True)
