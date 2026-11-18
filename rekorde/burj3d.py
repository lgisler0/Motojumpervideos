"""Burj Khalifa in 3D (Blender/Cycles). python3 burj3d.py <ordner> [--nur t1,t2] [--skala 50] [--start i --schritt n]"""
import bpy, math, random, sys, os, argparse
from mathutils import Vector

ap = argparse.ArgumentParser()
ap.add_argument("ordner"); ap.add_argument("--nur", default=""); ap.add_argument("--skala", type=int, default=50)
ap.add_argument("--samples", type=int, default=14); ap.add_argument("--fps", type=int, default=15)
ap.add_argument("--start", type=int, default=0); ap.add_argument("--schritt", type=int, default=1)
ap.add_argument("--dauer", type=float, default=22.6)
A = ap.parse_args(sys.argv[1:])

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = A.samples; sc.cycles.use_denoising = True
sc.cycles.max_bounces = 3; sc.cycles.diffuse_bounces = 1; sc.cycles.glossy_bounces = 2
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1080, 1920, A.skala
sc.render.use_persistent_data = True
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"
R = random.Random(5)
P = math.pi


def hexf(h):
    return tuple(((int(h[i:i + 2], 16) / 255) ** 2.2) for i in (0, 2, 4))


def mat(name, farbe, rau=.5, metall=0, leucht=0, lf=None, alpha=1):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*farbe, 1); b.inputs["Roughness"].default_value = rau; b.inputs["Metallic"].default_value = metall
    if leucht:
        b.inputs["Emission Color"].default_value = (*(lf or farbe), 1); b.inputs["Emission Strength"].default_value = leucht
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
    return m


def glas_fenster(name, basis, fenster_farbe, dichte=60):
    """Fassade mit leuchtenden Fensterreihen (Wave-Textur in Z)"""
    m = bpy.data.materials.new(name); m.use_nodes = True; n = m.node_tree.nodes; l = m.node_tree.links; b = n["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*basis, 1); b.inputs["Metallic"].default_value = .4; b.inputs["Roughness"].default_value = .3
    tc = n.new("ShaderNodeTexCoord"); sep = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Object"], sep.inputs[0])
    mul = n.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = dichte; l.new(sep.outputs["Z"], mul.inputs[0])
    fr = n.new("ShaderNodeMath"); fr.operation = "FRACT"; l.new(mul.outputs[0], fr.inputs[0])
    gt = n.new("ShaderNodeMath"); gt.operation = "GREATER_THAN"; gt.inputs[1].default_value = .72; l.new(fr.outputs[0], gt.inputs[0])
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 40; l.new(tc.outputs["Object"], nz.inputs["Vector"])
    nm = n.new("ShaderNodeMath"); nm.operation = "GREATER_THAN"; nm.inputs[1].default_value = .5; l.new(nz.outputs["Fac"], nm.inputs[0])
    mm = n.new("ShaderNodeMath"); mm.operation = "MULTIPLY"; l.new(gt.outputs[0], mm.inputs[0]); l.new(nm.outputs[0], mm.inputs[1])
    st = n.new("ShaderNodeMath"); st.operation = "MULTIPLY"; st.inputs[1].default_value = 2.5; l.new(mm.outputs[0], st.inputs[0])
    b.inputs["Emission Color"].default_value = (*fenster_farbe, 1); l.new(st.outputs[0], b.inputs["Emission Strength"])
    return m


def zylinder(r1, r2, h, z, verts=48, m=None, x=0, y=0):
    bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=r2, depth=h, vertices=verts, location=(x, y, z + h / 2))
    o = bpy.context.object
    if m:
        o.data.materials.append(m)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


# ---------------- Welt: Abendhimmel
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; nt = w.node_tree
sky = nt.nodes.new("ShaderNodeTexSky")
try:
    sky.sky_type = "NISHITA"
except Exception:
    pass
sky.sun_elevation = math.radians(2.5); sky.sun_rotation = math.radians(250)
try:
    sky.air_density = 1.4; sky.dust_density = 3.0
except Exception:
    pass
nt.links.new(sky.outputs[0], nt.nodes["Background"].inputs[0]); nt.nodes["Background"].inputs[1].default_value = .3
bpy.ops.object.light_add(type="SUN"); sonne = bpy.context.object
sonne.rotation_euler = (math.radians(86), 0, math.radians(250 - 90)); sonne.data.energy = 4.0; sonne.data.color = (1, .62, .35); sonne.data.angle = .02

# ---------------- Boden
bpy.ops.mesh.primitive_plane_add(size=200000); boden = bpy.context.object
mb = bpy.data.materials.new("boden"); mb.use_nodes = True; n = mb.node_tree.nodes; l = mb.node_tree.links; b = n["Principled BSDF"]
nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.004 * 1000; nz.inputs["Detail"].default_value = 6
cr = n.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (*hexf("6b5a44"), 1); cr.color_ramp.elements[1].color = (*hexf("a88a63"), 1)
tc = n.new("ShaderNodeTexCoord"); mp = n.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (.001, .001, .001)
l.new(tc.outputs["Object"], mp.inputs[0]); l.new(mp.outputs[0], nz.inputs["Vector"]); l.new(nz.outputs["Fac"], cr.inputs["Fac"]); l.new(cr.outputs[0], b.inputs["Base Color"])
b.inputs["Roughness"].default_value = .95
boden.data.materials.append(mb)

# ---------------- Stadt (Bloecke mit Fenstern)
fassaden = [glas_fenster(f"f{i}", hexf(c), hexf("ffcf8a"), d) for i, (c, d) in enumerate((("2c3442", 30), ("3a4150", 40), ("4a4f58", 25), ("23303f", 50)))]
strasse = mat("strasse", hexf("2a2a2e"), .8)


def stadt(cx, cy, rmin, rmax, n, hmin, hmax, seed):
    r = random.Random(seed)
    for _ in range(n):
        a = r.uniform(0, 2 * P); d = r.uniform(rmin, rmax) ** 1.0
        x, y = cx + d * math.cos(a), cy + d * math.sin(a)
        nah = max(0, 1 - d / rmax)
        h = r.uniform(hmin, hmin + (hmax - hmin) * (.3 + .7 * nah ** 1.5))
        bx, by = r.uniform(18, 45), r.uniform(18, 45)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, h / 2)); o = bpy.context.object
        o.scale = (bx, by, h); o.rotation_euler[2] = r.choice((0, P / 4, .1))
        o.data.materials.append(r.choice(fassaden))


stadt(0, 0, 160, 1700, 230, 25, 300, 1)
stadt(1600, 500, 120, 900, 110, 20, 160, 2)

# ---------------- Burj Khalifa (gestufte Zylinder + Spitze)
burj_m = glas_fenster("burj", hexf("b7c3d4"), hexf("ffe6b8"), 0.25)
burj_m.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = .75
burj_m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = .18
kern = zylinder(16, 7, 600, 0, 48, burj_m)
for k, ang in enumerate((P / 2, P / 2 + 2 * P / 3, P / 2 + 4 * P / 3)):
    hoehe = 0
    laenge = 52
    seg = 0
    while laenge > 8:
        h = 46 + 4 * seg
        oben = hoehe + h
        # Fluegel endet gestaffelt: jeder Fluegel springt bei anderer Hoehe zurueck
        bpy.ops.mesh.primitive_cube_add(size=1); o = bpy.context.object; o.data.materials.append(burj_m)
        o.scale = (laenge, 19 - seg * .6, h); o.rotation_euler[2] = ang
        o.location = (math.cos(ang) * laenge / 2, math.sin(ang) * laenge / 2, hoehe + h / 2)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        bev = o.modifiers.new("b", "BEVEL"); bev.width = 3.5; bev.segments = 4; bev.limit_method = "ANGLE"
        for p in o.data.polygons:
            p.use_smooth = True
        hoehe = oben; seg += 1
        laenge -= 3.3 + (k * 1.1 if seg % 3 == k else 0)
zylinder(7, 3, 120, 600, 24, burj_m)
zylinder(3, .4, 108, 720, 16, burj_m)
bpy.ops.object.light_add(type="POINT", location=(0, 0, 832)); spitzlicht = bpy.context.object; spitzlicht.data.energy = 20000; spitzlicht.data.color = (1, .3, .2); spitzlicht.data.shadow_soft_size = 2

# ---------------- Eiffelturm (zum Vergleich, 330 m)
EX, EY = -320, 120
eis = mat("eisen", hexf("8a5a36"), .55, .6)
for sx in (-1, 1):
    for sy in (-1, 1):
        bpy.ops.mesh.primitive_cube_add(size=1); o = bpy.context.object; o.data.materials.append(eis)
        o.scale = (9, 9, 120); o.location = (EX + sx * 38, EY + sy * 38, 58); o.rotation_euler = (sy * -.3, sx * .3, 0)
zylinder(30, 22, 8, 57, 4, eis, x=EX, y=EY).rotation_euler[2] = P / 4
zylinder(22, 9, 60, 65, 4, eis, x=EX, y=EY).rotation_euler[2] = P / 4
zylinder(9, 6, 8, 115, 4, eis, x=EX, y=EY).rotation_euler[2] = P / 4
zylinder(6, 1.5, 160, 123, 4, eis, x=EX, y=EY).rotation_euler[2] = P / 4
zylinder(1.5, .4, 47, 283, 8, eis, x=EX, y=EY)
eiffel_objs = [o for o in bpy.data.objects if o.data and hasattr(o.data, "materials") and len(o.data.materials) and o.data.materials[0] == eis]

# ---------------- Jeddah Tower (Baustelle + geplante Silhouette)
JX, JY = 1600, 500
beton = mat("beton", hexf("b8b4ab"), .7)
for k, ang in enumerate((0, 2 * P / 3, 4 * P / 3)):
    zylinder(30, 18, 470, 0, 24, beton, x=JX + 25 * math.cos(ang), y=JY + 25 * math.sin(ang))
zylinder(34, 22, 470, 0, 36, beton, x=JX, y=JY)
gelb = mat("kran", hexf("ffc41a"), .4, 0, 2, hexf("ffb000"))
bpy.ops.mesh.primitive_cube_add(size=1, location=(JX, JY, 500)); k1 = bpy.context.object; k1.scale = (3, 3, 70); k1.data.materials.append(gelb)
bpy.ops.mesh.primitive_cube_add(size=1, location=(JX + 35, JY, 532)); k2 = bpy.context.object; k2.scale = (95, 2.5, 2.5); k2.data.materials.append(gelb)
geist_m = mat("geist", hexf("ffd23f"), .5, 0, 6, hexf("ffd23f"))
geist = zylinder(28, 1.5, 1008 - 470, 470, 12, geist_m, x=JX, y=JY)
wf = geist.modifiers.new("wf", "WIREFRAME"); wf.thickness = 1.6
geist.visible_shadow = False

# ---------------- Kamera
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam; cam.data.lens = 30; cam.data.clip_end = 30000; cam.data.sensor_fit = "VERTICAL"


def blick(pos, ziel):
    cam.location = Vector(pos); d = Vector(ziel) - Vector(pos); cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def ease(x):
    x = min(1, max(0, x)); return x * x * (3 - 2 * x)


def lerpv(a, b, k):
    return tuple(x + (y - x) * k for x, y in zip(a, b))


D = A.dauer
t_name, t_seit, t_eiffel, t_saudi, t_jeddah, t_bis = 2.3, 4.6, 7.7, 10.8, 14.5, 19.0
START = ((900, -1350, 260), (0, 0, 420))
KEYS = [
    (0.0, *START),
    (t_name, (860, -1290, 250), (0, 0, 420)),
    (t_name + .6, (120, -160, 25), (0, 0, 120)),            # unten am Fuss
    (t_seit + 1.4, (90, -110, 790), (0, 0, 640)),           # Drohne steigt bis zur Spitze
    (t_eiffel - .2, (420, -900, 400), (0, 0, 380)),
    (t_eiffel + .8, (-80, -950, 220), (-180, 60, 250)),     # Vergleich mit Eiffelturm
    (t_saudi - .1, (-40, -930, 230), (-160, 60, 250)),
    (t_saudi + 1.2, (1450, -700, 300), (1600, 500, 300)),   # Flug zum Jeddah Tower
    (t_jeddah + .8, (1150, -1350, 420), (1500, 500, 560)),
    (t_bis, (1050, -1500, 450), (1300, 400, 560)),
    (D - .8, *START), (D, *START)]


def kamera(t):
    for a, b in zip(KEYS, KEYS[1:]):
        if a[0] <= t <= b[0]:
            k = ease((t - a[0]) / max(b[0] - a[0], 1e-6))
            pos = lerpv(a[1], b[1], k); ziel = lerpv(a[2], b[2], k)
            # sanftes Schweben
            pos = (pos[0] + 6 * math.sin(t * .7), pos[1], pos[2] + 4 * math.sin(t * .9))
            return pos, ziel
    return KEYS[-1][1], KEYS[-1][2]


def zustand(t):
    pos, ziel = kamera(t); blick(pos, ziel)
    sichtbar = t_eiffel - .3 <= t <= D - .9
    for o in eiffel_objs:
        o.hide_render = not sichtbar
    geist.hide_render = not (t_jeddah - .3 <= t <= D - .6)
    spitzlicht.data.energy = 20000 * (.6 + .4 * math.sin(t * 6))


os.makedirs(A.ordner, exist_ok=True)
N = int(round(D * A.fps))
liste = [int(round(float(x) * A.fps)) for x in A.nur.split(",")] if A.nur else list(range(A.start, N, A.schritt))
for f in liste:
    pfad = os.path.join(A.ordner, f"burj_{f:04d}.png")
    if os.path.exists(pfad) and not A.nur:
        continue
    zustand(f / A.fps); sc.render.filepath = pfad
    bpy.ops.render.render(write_still=True); print("FERTIG", pfad, flush=True)
