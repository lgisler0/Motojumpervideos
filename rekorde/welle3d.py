"""Groesste Welle 26,21 m (Sebastian Steudtner, Nazare 29.10.2020, GWR). Realistischer Stil, echte Figuren (mensch_echt).
python3 welle3d.py <ordner> [--nur t1,t2] [--start i] [--samples n]"""
import bpy, bmesh, math, random, sys, os, argparse
from mathutils import Vector, Matrix, Euler
HIER = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HIER)
import mensch_mh as MH

ap = argparse.ArgumentParser()
ap.add_argument("ordner"); ap.add_argument("--nur", default=""); ap.add_argument("--skala", type=int, default=50)
ap.add_argument("--samples", type=int, default=12); ap.add_argument("--fps", type=int, default=15)
ap.add_argument("--start", type=int, default=0)
A = ap.parse_args(sys.argv[1:])
P = math.pi
D = 23.6
ASSET = os.path.join(os.path.dirname(HIER), "assets")
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = A.samples; sc.cycles.use_denoising = True
sc.cycles.max_bounces = 5; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 3; sc.cycles.transmission_bounces = 2
sc.cycles.transparent_max_bounces = 8; sc.cycles.adaptive_threshold = .03
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1080, 1920, A.skala
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"; sc.view_settings.exposure = -.05
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


def pbr(name, tex, skala=1.0, tint=None, rau_mul=1.0, rau_add=0.0, metal=0.0, normal=1.0, coat=0.0):
    """Foto-Textur (ambientCG) mit Box-Projektion auf Objektkoordinaten."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; n = nt.nodes; l = nt.links; b = n["Principled BSDF"]
    pfad = os.path.join(ASSET, tex, f"{tex}_1K-JPG")
    tc = n.new("ShaderNodeTexCoord"); mp = n.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (skala, skala, skala)
    l.new(tc.outputs["Object"], mp.inputs[0])

    def bild(suffix, farbe=True):
        if not os.path.exists(pfad + suffix):
            return None
        t = n.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(pfad + suffix, check_existing=True)
        if not farbe:
            t.image.colorspace_settings.name = "Non-Color"
        t.projection = "BOX"; t.projection_blend = .25; l.new(mp.outputs[0], t.inputs[0]); return t
    c = bild("_Color.jpg")
    if c:
        if tint:
            mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"; mx.inputs[0].default_value = 1
            l.new(c.outputs[0], mx.inputs[6]); mx.inputs[7].default_value = (*hexf(tint), 1); l.new(mx.outputs[2], b.inputs["Base Color"])
        else:
            l.new(c.outputs[0], b.inputs["Base Color"])
    r = bild("_Roughness.jpg", False)
    if r:
        ma = n.new("ShaderNodeMath"); ma.operation = "MULTIPLY_ADD"; ma.inputs[1].default_value = rau_mul; ma.inputs[2].default_value = rau_add
        l.new(r.outputs[0], ma.inputs[0]); l.new(ma.outputs[0], b.inputs["Roughness"])
    nm = bild("_NormalGL.jpg", False)
    if nm:
        nmap = n.new("ShaderNodeNormalMap"); nmap.inputs["Strength"].default_value = normal; l.new(nm.outputs[0], nmap.inputs["Color"])
        l.new(nmap.outputs[0], b.inputs["Normal"])
    b.inputs["Metallic"].default_value = metal
    if coat:
        b.inputs["Coat Weight"].default_value = coat; b.inputs["Coat Roughness"].default_value = .12
    return m


def emis(name, farbe, st):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0, 0, 0, 1); b.inputs["Emission Color"].default_value = (*hexf(farbe), 1)
    b.inputs["Emission Strength"].default_value = st; return m


def glatt(o, sub=1, bevel=0.0, seg=3):
    if bevel:
        bv = o.modifiers.new("b", "BEVEL"); bv.width = bevel; bv.segments = seg; bv.limit_method = "ANGLE"
    if sub:
        s = o.modifiers.new("s", "SUBSURF"); s.levels = sub; s.render_levels = sub
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def box(name, groesse, ort, m, bevel=.01, seg=3, rot=(0, 0, 0), eltern=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=ort, rotation=rot); o = bpy.context.object; o.name = name; o.scale = groesse
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        bv = o.modifiers.new("b", "BEVEL"); bv.width = bevel; bv.segments = seg
        for p in o.data.polygons:
            p.use_smooth = True
        o.data.shade_auto_smooth() if hasattr(o.data, "shade_auto_smooth") else None
    o.data.materials.append(m)
    if eltern:
        o.parent = eltern
    return o


def zyl(name, r, l, ort, m, rot=(0, 0, 0), eltern=None, v=32):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=l, vertices=v, location=ort, rotation=rot); o = bpy.context.object; o.name = name
    o.data.materials.append(m)
    bv = o.modifiers.new("b", "BEVEL"); bv.width = min(r, l) * .12; bv.segments = 2; bv.limit_method = "ANGLE"
    for p in o.data.polygons:
        p.use_smooth = True
    if eltern:
        o.parent = eltern
    return o


def rohr(name, a, b, r, m, eltern=None, v=10):
    a, b = Vector(a), Vector(b); d = b - a
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d.length, vertices=v, location=(a + b) / 2); o = bpy.context.object; o.name = name
    o.rotation_mode = "QUATERNION"; o.rotation_quaternion = d.to_track_quat("Z", "Y"); o.data.materials.append(m)
    for p in o.data.polygons:
        p.use_smooth = True
    if eltern:
        o.parent = eltern
    return o


def leer(name, ort=(0, 0, 0), eltern=None):
    o = bpy.data.objects.new(name, None); sc.collection.objects.link(o); o.location = ort
    if eltern:
        o.parent = eltern
    return o


def dreh_koerper(name, profil, m, nv=64):
    """profil: [(y, r)] - Drehkoerper um die y-Achse"""
    bm = bmesh.new(); ringe = []
    for y, r in profil:
        ringe.append([bm.verts.new((r * math.cos(2 * P * k / nv), y, r * math.sin(2 * P * k / nv))) for k in range(nv)])
    for a, b in zip(ringe, ringe[1:]):
        for k in range(nv):
            bm.faces.new((a[k], a[(k + 1) % nv], b[(k + 1) % nv], b[k]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o); me.materials.append(m)
    for p in me.polygons:
        p.use_smooth = True
    return o


# ======================================================================  Menschen (zuerst, Materialien danach)
import mensch_echt as ME
LOGO = ME.logo_bild(os.path.join(HIER, "_logo_norda.png"), "NORDA", farbe=(1, 1, 1))
SU = ME.mensch("steudtner", 52, 1.0, .4, .7, .3, haut="caucasian", haare="short02", braue="eyebrow001", haarfarbe="2a1d12")
ME.trikot(SU, "lang", "tights", "c62828", "121417", brust=LOGO, brust_mass=(.17, .09), bein=LOGO)
JF = ME.mensch("jetski", 77, 1.0, .35, .6, .35, haut="caucasian", haare="short03", braue="eyebrow010", haarfarbe="0b0908")
ME.trikot(JF, "lang", "tights", "f9a825", "121417", brust=LOGO, brust_mass=(.17, .09), bein=LOGO)
for K, hoehe_soll in ((SU, 1.80), (JF, 1.78)):
    for o in K.huellen:
        if "versatz" in o.modifiers:
            o.modifiers["versatz"].strength = .017 if o.name.endswith("_hemd") else .010
        for md in o.modifiers:
            if md.type == "SUBSURF":
                md.render_levels = 2
    hoehe = max(v.z for v in K.EV); K.SK = hoehe_soll / hoehe; K.rig.scale = (K.SK,) * 3
    K.PEL = K.rig.data.bones["upperleg01.L"].head_local.copy(); K.PEL.x = 0
print("ok menschen")

# ======================================================================  Materialien, Himmel, Sonne
FELS = pbr("fels", "Rock035", .08, tint="b0a090")
GRAS = pbr("gras", "Grass004", .25, tint="9aa070")
SAND = pbr("sand", "Ground054", .3, tint="e8d8b8")
STEIN = pbr("stein", "PaintedPlaster017", .4, tint="e0d4bc")
SCHWARZ = mat("schwarzlack", "0d0d0f", .4, Coat_Weight=.3)
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; nt = w.node_tree
env = nt.nodes.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(os.path.join(ASSET, "tag.hdr"))
nt.links.new(env.outputs[0], nt.nodes["Background"].inputs[0]); nt.nodes["Background"].inputs[1].default_value = 1.0
bpy.ops.object.light_add(type="SUN", rotation=(math.radians(55), 0, math.radians(200))); sonne = bpy.context.object
sonne.data.energy = 4.2; sonne.data.angle = math.radians(1.0); sonne.data.color = (1, .95, .86)


def wasser_mat(name, schaum_attr=True):
    """Meerwasser: dunkles Blaugruen, glaenzend, etwas Durchscheinen; Schaum (weiss) ueber Attribut + Rauschen."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt_ = m.node_tree; n = nt_.nodes; l = nt_.links; b = n["Principled BSDF"]
    b.inputs["Roughness"].default_value = .035; b.inputs["IOR"].default_value = 1.33; b.inputs["Specular IOR Level"].default_value = .7
    b.inputs["Subsurface Weight"].default_value = .25; b.inputs["Subsurface Radius"].default_value = (.3, 1.2, 1.0); b.inputs["Subsurface Scale"].default_value = .6
    tc = n.new("ShaderNodeTexCoord")
    # Grundfarbe: tief = dunkel, hoch (duenne Lippe) = tuerkis
    hoch = n.new("ShaderNodeAttribute"); hoch.attribute_name = "hoch"
    rampe = n.new("ShaderNodeValToRGB"); l.new(hoch.outputs["Fac"], rampe.inputs[0])
    rampe.color_ramp.elements[0].color = (*hexf("0a2f3d"), 1); rampe.color_ramp.elements[1].color = (*hexf("2a8f8a"), 1)
    rampe.color_ramp.elements[1].position = .95
    # Schaum
    no = n.new("ShaderNodeTexNoise"); no.inputs["Scale"].default_value = .35; no.inputs["Detail"].default_value = 8; no.inputs["Roughness"].default_value = .65
    l.new(tc.outputs["Object"], no.inputs["Vector"])
    vor = n.new("ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value = 1.4; vor.feature = "DISTANCE_TO_EDGE"; l.new(tc.outputs["Object"], vor.inputs["Vector"])
    adern = n.new("ShaderNodeMath"); adern.operation = "LESS_THAN"; adern.inputs[1].default_value = .06; l.new(vor.outputs["Distance"], adern.inputs[0])
    if schaum_attr:
        sa = n.new("ShaderNodeAttribute"); sa.attribute_name = "schaum"; src = sa.outputs["Fac"]
    else:
        sa = n.new("ShaderNodeAttribute"); sa.attribute_name = "foam"; src = sa.outputs["Fac"]
    mul = n.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = 1.25; l.new(src, mul.inputs[0])
    add = n.new("ShaderNodeMath"); add.operation = "ADD"; l.new(mul.outputs[0], add.inputs[0]); l.new(no.outputs[0], add.inputs[1])
    sub = n.new("ShaderNodeMath"); sub.operation = "SUBTRACT"; sub.inputs[1].default_value = .92; l.new(add.outputs[0], sub.inputs[0])
    adern_w = n.new("ShaderNodeMath"); adern_w.operation = "MULTIPLY"; adern_w.inputs[1].default_value = .22; l.new(adern.outputs[0], adern_w.inputs[0])
    adern_s = n.new("ShaderNodeMath"); adern_s.operation = "MULTIPLY"; l.new(adern_w.outputs[0], adern_s.inputs[0]); l.new(src, adern_s.inputs[1])
    ges = n.new("ShaderNodeMath"); ges.operation = "ADD"; ges.use_clamp = True; l.new(sub.outputs[0], ges.inputs[0]); l.new(adern_s.outputs[0], ges.inputs[1])
    sm = n.new("ShaderNodeMath"); sm.operation = "MULTIPLY"; sm.inputs[1].default_value = 3.5; sm.use_clamp = True; l.new(ges.outputs[0], sm.inputs[0])
    mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; l.new(sm.outputs[0], mx.inputs[0]); l.new(rampe.outputs[0], mx.inputs[6]); mx.inputs[7].default_value = (.93, .96, .97, 1)
    l.new(mx.outputs[2], b.inputs["Base Color"])
    rmx = n.new("ShaderNodeMapRange"); rmx.inputs[3].default_value = .035; rmx.inputs[4].default_value = .55; l.new(sm.outputs[0], rmx.inputs[0]); l.new(rmx.outputs[0], b.inputs["Roughness"])
    # kleine Riffel als Bump
    no2 = n.new("ShaderNodeTexNoise"); no2.inputs["Scale"].default_value = 2.2; no2.inputs["Detail"].default_value = 6; l.new(tc.outputs["Object"], no2.inputs["Vector"])
    bu = n.new("ShaderNodeBump"); bu.inputs["Strength"].default_value = .18; bu.inputs["Distance"].default_value = .3; l.new(no2.outputs[0], bu.inputs["Height"]); l.new(bu.outputs[0], b.inputs["Normal"])
    return m


WASSER = wasser_mat("welle")
MEER = wasser_mat("meer", schaum_attr=False)
SCHAUM = mat("schaum", "eef3f5", .7, Subsurface_Weight=1.0, Subsurface_Scale=2.0)

# ======================================================================  Meer (Ocean-Modifier auf grossem Gitter)
bpy.ops.mesh.primitive_grid_add(x_subdivisions=360, y_subdivisions=360, size=1400, location=(0, 150, 0)); meer = bpy.context.object; meer.name = "meer"
meer.data.materials.append(MEER)
for p in meer.data.polygons:
    p.use_smooth = True
oc = meer.modifiers.new("ocean", "OCEAN"); oc.geometry_mode = "DISPLACE"; oc.spatial_size = 60; oc.resolution = 10
oc.wave_scale = 1.4; oc.choppiness = 1.1; oc.wind_velocity = 18; oc.wave_alignment = .6; oc.wave_direction = P / 2; oc.use_normals = True
oc.use_foam = True; oc.foam_layer_name = "foam"; oc.foam_coverage = .25; oc.depth = 60

# ======================================================================  Die Welle
C_WELLE = 11.0                  # Wellengeschwindigkeit (+y, zur Kueste)
Y0_WELLE = -40.0
H_MAX = 26.21


def y_kamm(ts):
    return Y0_WELLE + C_WELLE * ts


def hoehe_x(x):
    """Wellenhoehe entlang des Kamms: Spitze bei x ~ 0..30, Schulter nach links (-x) flacher"""
    if x > 40:
        k = math.exp(-((x - 40) / 70) ** 2)
    elif x > -10:
        k = 1.0
    else:
        k = .3 + .7 * math.exp(-((x + 10) / 85) ** 2)
    return H_MAX * k


# Brechen: Punkt x_bruch(ts) laeuft dem Surfer hinterher (Ablauf setzt BRUCH)
BRUCH = {"x": 400.0}
V_BRUCH = 13.0                   # m/s, mit der die Brechzone entlang des Kamms laeuft
NB, NL, NF = 18, 14, 22          # Punkte Ruecken, Lippe, Front


def profil(x, ts):
    """Liste (q, z, schaum) quer zum Kamm (q>0 = vor dem Kamm). Mit Lippe, wenn dort schon gebrochen."""
    H = hoehe_x(x)
    p = (x - BRUCH["x"]) / V_BRUCH     # Sekunden seit dem Brechen an dieser Stelle
    # p < 0: ungebrochen; 0..1: Lippe wirft; 1..1.8: Lippe faellt; > 1.8: Weisswasser
    zusammen = ease((p - 1.8) / 2.5) if p > 1.8 else 0.0
    He = H * (1 - .62 * zusammen)
    pts = []
    for i in range(NB):                                      # Ruecken
        s = 1 - i / (NB - 1)
        q = -95 * s; z = He * (1 - s) ** 2.1 * (1 - .06 * math.sin(s * 9 + x * .05))
        pts.append((q, z, 0.0))
    lip = ease(p) if p > 0 else 0.0
    L = 14.0 * lip * (He / H_MAX) * (1 - zusammen)
    fall = ease((p - 1.0) / .8) if p > 1 else 0.0
    spitze_z = He - .6 * L - (He - .6 * L) * fall
    for i in range(NL):                                      # Kamm -> Lippe -> zurueck zur Front
        k = (i + 1) / NL
        if L < .05:
            q = 1.2 * k; z = He - .02 * He * k
            pts.append((q, z, .15 * k * (1 if p > -1.5 else 0)))
            continue
        if k < .6:
            kk = k / .6
            q = L * 1.15 * math.sin(kk * P / 2) ** .8
            z = He + .06 * L * math.sin(kk * P) * (1 - kk) - (He - spitze_z) * (kk ** 2.4)
        else:
            kk = (k - .6) / .4
            q = L * 1.15 * (1 - kk) + face_q(He, max(.05, spitze_z - 1.5 - 1.0 * kk), He) * kk
            z = spitze_z + (max(.05, spitze_z - 1.5) - spitze_z) * kk
        pts.append((q, z, .35 + .65 * fall if L > 1 else .2))
    z_start = pts[-1][1]
    for i in range(NF):                                      # Front bis zum Fuss der Welle
        k = (i + 1) / NF
        z = z_start * (1 - k) ** 1.8
        q = face_q(He, z, He) if z > .01 else 24.0 * (He / H_MAX) ** .6 + 4 * k
        q = max(q, pts[-1][0] + .05) if i == 0 else max(q, pts[-1][0] + .02)
        sch = 1.0 if zusammen > .05 else (.55 * k ** 3 + (.5 * fall if p > 1 else 0))
        pts.append((q, z, min(1, sch)))
    return pts


def face_q(H, z, Hn):
    """Vorderseite: Hoehe z -> Abstand q vor dem Kamm (konkave Wand: steil oben, flach unten)"""
    breite = 24.0 * (H / H_MAX) ** .6
    r = max(0, min(1, z / max(.01, H)))
    s = 1 - r ** (1 / 2.2)
    return 1.2 + breite * s


WX0, WX1, WNX = -260.0, 220.0, 240
WNV = NB + NL + NF
bm = bmesh.new(); grid = []
for j in range(WNX + 1):
    grid.append([bm.verts.new((0, 0, 0)) for _ in range(WNV)])
for j in range(WNX):
    for i in range(WNV - 1):
        bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
me = bpy.data.meshes.new("welle"); bm.to_mesh(me); bm.free()
welle = bpy.data.objects.new("welle", me); sc.collection.objects.link(welle); me.materials.append(WASSER)
for p in me.polygons:
    p.use_smooth = True
me.attributes.new("schaum", "FLOAT", "POINT"); me.attributes.new("hoch", "FLOAT", "POINT")
sd_ = welle.modifiers.new("s", "SUBSURF"); sd_.levels = 0; sd_.render_levels = 1


def welle_setzen(ts):
    yk = y_kamm(ts); co = []; sch = []; ho = []
    for j in range(WNX + 1):
        x = WX0 + (WX1 - WX0) * j / WNX
        H = max(.1, hoehe_x(x))
        for (q, z, s) in profil(x, ts):
            co += [x, yk + q, z]; sch.append(s); ho.append(min(1, z / H) ** 3 if q > -2 else .2 * min(1, z / H))
    me.vertices.foreach_set("co", co); me.attributes["schaum"].data.foreach_set("value", sch); me.attributes["hoch"].data.foreach_set("value", ho)
    me.update()


def welle_punkt(x, q, ts):
    """Punkt auf der Vorderseite (ungebrochenes Profil) + Normale"""
    H = hoehe_x(x)
    def z_von_q(qq):
        lo, hi = 0.0, H
        for _ in range(30):
            mi = (lo + hi) / 2
            if face_q(H, mi, H) > qq:
                lo = mi
            else:
                hi = mi
        return (lo + hi) / 2
    z = z_von_q(q); yk = y_kamm(ts)
    dz_dq = (z_von_q(q + .3) - z_von_q(q - .3)) / .6
    dz_dx = (z_von_q_x(x + .5, q) - z_von_q_x(x - .5, q)) / 1.0
    nn = Vector((-dz_dx, -dz_dq, 1)).normalized()
    return Vector((x, yk + q, z)), nn


def z_von_q_x(x, q):
    H = hoehe_x(x); lo, hi = 0.0, H
    for _ in range(24):
        mi = (lo + hi) / 2
        if face_q(H, mi, H) > q:
            lo = mi
        else:
            hi = mi
    return (lo + hi) / 2


# Gischt-Wolken (Explosion beim Aufprall der Lippe)
GISCHT = []
rg = random.Random(5)
tex = bpy.data.textures.new("wolke", "CLOUDS"); tex.noise_scale = .35; tex.noise_depth = 3
for i in range(70):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1, location=(0, -500, -50)); o = bpy.context.object; o.name = "gischt%02d" % i
    dm = o.modifiers.new("d", "DISPLACE"); dm.texture = tex; dm.strength = 1.5; dm.texture_coords = "OBJECT"
    o.data.materials.append(SCHAUM)
    for p in o.data.polygons:
        p.use_smooth = True
    GISCHT.append((o, rg.uniform(0, 1), rg.uniform(-1, 1), rg.uniform(.6, 1.4)))


def gischt_setzen(ts):
    yk = y_kamm(ts); xb = BRUCH["x"]
    for (o, a, b_, g) in GISCHT:
        x = xb + 10 + a * 120
        p = (x - xb) / V_BRUCH
        if p < 1.6 or x > WX1 or p > 7:
            o.hide_render = True; continue
        o.hide_render = False
        alt = p - 1.6
        H = hoehe_x(x)
        r = (2.0 + 3.5 * min(1, alt / 1.5)) * g * (H / H_MAX + .3)
        o.scale = (r, r * .9, r * (1.1 + .4 * b_))
        o.location = (x + b_ * 4, yk + 14 + 6 * min(1, alt) + b_ * 5, r * .55 + 3 * min(1, alt / 2) * (1 - min(1, alt / 4)) * g)
        o.rotation_euler = (a * 6, b_ * 3, g * 2)


# ======================================================================  Kueste: Klippe mit Fort und rotem Leuchtturm, Strand, Stadt
def klippe_z(x, y):
    # Landzunge rechts vorne (Nazare-Fort), Strand hinten (+y)
    d_land = max(0, y - 330)                       # Strand ab y=330
    z = -2 + min(3, d_land * .06) + max(0, y - 400) * .25
    # Landzunge: x > 140, y > 60
    dx = x - 140; dy = y - 60
    if dx > -30 and dy > -40:
        k = min(1, max(0, dx + 30) / 30) * min(1, max(0, dy + 40) / 30)
        z = max(z, -2 + 52 * k + 4 * rausch2(x, y))
    return z


def rausch2(x, y):
    return math.sin(x * .09 + 1) * math.cos(y * .07) + .5 * math.sin(x * .23 - y * .19)


bm = bmesh.new(); vs = []
NX_, NY_ = 220, 160
for j in range(NY_ + 1):
    row = []
    y = 20 + 700 * j / NY_
    for i in range(NX_ + 1):
        x = -500 + 1000 * i / NX_
        row.append(bm.verts.new((x, y, klippe_z(x, y))))
    vs.append(row)
for j in range(NY_):
    for i in range(NX_):
        bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
me_k = bpy.data.meshes.new("kueste"); bm.to_mesh(me_k); bm.free()
kueste = bpy.data.objects.new("kueste", me_k); sc.collection.objects.link(kueste)
for m_ in (FELS, GRAS, SAND):
    me_k.materials.append(m_)
for p in me_k.polygons:
    p.use_smooth = True
    c = p.center
    if p.normal.z < .75:
        p.material_index = 0
    elif c.z > 20:
        p.material_index = 1
    else:
        p.material_index = 2
# Fort (Mauern) + roter Leuchtturm an der Klippenkante
FX, FY = 185, 95
FZ = klippe_z(FX, FY)
for (dx, dy, sx, sy) in ((0, -14, 30, 1.6), (0, 14, 30, 1.6), (-15, 0, 1.6, 28), (15, 0, 1.6, 28)):
    box("fortmauer", (sx, sy, 6), (FX + dx, FY + dy, FZ + 2.5), STEIN, .1)
box("fortgebaeude", (16, 12, 7), (FX + 3, FY + 2, FZ + 3.5), STEIN, .1)
box("fortdach", (17, 13, .4), (FX + 3, FY + 2, FZ + 7.2), mat("dachgrau", "6d6a66", .7), .05)
ROT = mat("leuchtturmrot", "c0261c", .4, Coat_Weight=.5)
box("leuchtturm", (5, 5, 14), (FX - 6, FY - 8, FZ + 7), ROT, .08)
box("leuchtturm_kopf", (6, 6, .6), (FX - 6, FY - 8, FZ + 14.3), mat("weiss", "f2f2f2", .4), .05)
zyl("laterne", 1.8, 3, (FX - 6, FY - 8, FZ + 16.1), mat("laternenglas", "dfe8e8", .05, Coat_Weight=1, Metallic=.4))
zyl("laternendach", 2.2, .6, (FX - 6, FY - 8, FZ + 17.9), ROT)
for k in range(4):
    box("fenster_lt", (.08, 1.0, 1.4), (FX - 8.55, FY - 8, FZ + 4 + k * 3), mat("fensterdunkel", "1a1d22", .2) if not bpy.data.materials.get("fensterdunkel") else bpy.data.materials["fensterdunkel"], .01)
# Stadt am Strand: weisse Haeuser mit roten Daechern
HAUS = mat("haus", "f1ede6", .7); DACH = mat("ziegel", "b0442a", .6)
rh = random.Random(9); n_h = 0
for j in range(420):
    x = rh.uniform(-480, 120); y = rh.uniform(420, 700)
    z = klippe_z(x, y); w_, d_, h_ = rh.uniform(6, 12), rh.uniform(6, 10), rh.uniform(5, 11)
    box("haus%03d" % n_h, (w_, d_, h_), (x, y, z + h_ / 2 - .5), HAUS, .1)
    o = box("dach%03d" % n_h, (w_ + .6, d_ + .6, .8), (x, y, z + h_ - .1), DACH, .2); n_h += 1
# Zuschauer auf der Klippe
koerper_me = []
for i, f in enumerate(["c62828", "1565c0", "f2f2f2", "2e7d32", "212121", "f9a825", "6a1b9a", "e65100"]):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=7, radius=1, matrix=Matrix.Translation((0, 0, .55)) @ Matrix.Diagonal((.26, .19, .42, 1)))
    bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=7, radius=.11, matrix=Matrix.Translation((0, 0, 1.08)))
    me_p = bpy.data.meshes.new("pub%d" % i); bm.to_mesh(me_p); bm.free(); me_p.materials.append(mat("pubm%d" % i, f, .8, Sheen_Weight=.5))
    for p in me_p.polygons:
        p.use_smooth = True
    koerper_me.append(me_p)
rp = random.Random(3); n_pub = 0
for j in range(900):
    x = rp.uniform(130, 175); y = rp.uniform(30, 75)
    if klippe_z(x, y) < 40 or (abs(x - FX) < 17 and abs(y - FY) < 16):
        continue
    o = bpy.data.objects.new("pub%04d" % n_pub, rp.choice(koerper_me)); sc.collection.objects.link(o); n_pub += 1
    o.location = (x, y, klippe_z(x, y) - .05); o.rotation_euler = (0, 0, rp.uniform(2.2, 3.6))
print("ok kueste")
# ======================================================================  Surfbrett, Jetski mit Rettungsschlitten, Seil
BRETT_M = bpy.data.materials.new("brett"); BRETT_M.use_nodes = True; nb_ = BRETT_M.node_tree.nodes; lb_ = BRETT_M.node_tree.links
tcb = nb_.new("ShaderNodeTexCoord"); sepb = nb_.new("ShaderNodeSeparateXYZ"); lb_.new(tcb.outputs["Object"], sepb.inputs[0])
absb = nb_.new("ShaderNodeMath"); absb.operation = "ABSOLUTE"; lb_.new(sepb.outputs["Y"], absb.inputs[0])
strb = nb_.new("ShaderNodeMath"); strb.operation = "LESS_THAN"; strb.inputs[1].default_value = .035; lb_.new(absb.outputs[0], strb.inputs[0])
mxb_ = nb_.new("ShaderNodeMix"); mxb_.data_type = "RGBA"; mxb_.inputs[6].default_value = (.95, .95, .93, 1); mxb_.inputs[7].default_value = (*hexf("c62828"), 1)
lb_.new(strb.outputs[0], mxb_.inputs[0]); lb_.new(mxb_.outputs[2], nb_["Principled BSDF"].inputs["Base Color"])
nb_["Principled BSDF"].inputs["Roughness"].default_value = .25; nb_["Principled BSDF"].inputs["Coat Weight"].default_value = .7


def brett_mesh():
    bm = bmesh.new(); r_ = []
    n = 40
    for i in range(n + 1):
        x = -.9 + 1.8 * i / n
        k = abs(x) / .9
        br = .25 * (1 - k ** 2.2) ** .5 + .004
        z = .1 * max(0, x / .9) ** 2.5 + .04 * max(0, -x / .9) ** 2
        r_.append([bm.verts.new((x, sy * br * f, z + dz)) for sy, f, dz in ((-1, .9, 0), (-1, 1, .02), (-1, .8, .055), (1, .8, .055), (1, 1, .02), (1, .9, 0))])
    for a, b_ in zip(r_, r_[1:]):
        for k in range(6):
            bm.faces.new((a[k], a[(k + 1) % 6], b_[(k + 1) % 6], b_[k]))
    bm.faces.new(r_[0][::-1]); bm.faces.new(r_[-1])
    me = bpy.data.meshes.new("brett"); bm.to_mesh(me); bm.free(); me.materials.append(BRETT_M)
    for p in me.polygons:
        p.use_smooth = True
    return me


brett = bpy.data.objects.new("brett", brett_mesh()); sc.collection.objects.link(brett)
s_ = brett.modifiers.new("s", "SUBSURF"); s_.levels = 1; s_.render_levels = 2
for xx in (.33, -.33, -.55):                      # Fussschlaufen
    box("schlaufe", (.13, .17, .035), (xx, 0, .085), SCHWARZ, .015, eltern=brett)
for yy in (-.13, 0, .13):                         # Finnen
    box("finne", (.11, .012, .09), (-.72, yy, -.04), SCHWARZ, .005, eltern=brett)

GELB = mat("jetski_gelb", "f9a825", .3, Coat_Weight=.8)
WEISS_L = mat("jetski_weiss", "f2f2f2", .3, Coat_Weight=.8)


def jetski_rumpf():
    bm = bmesh.new(); r_ = []
    n = 24
    for i in range(n + 1):
        x = -1.6 + 3.3 * i / n
        k = (x + 1.6) / 3.3
        br = .58 * (1 - max(0, (k - .55) / .45) ** 1.7) + .02
        tief = .28 * (1 - max(0, (k - .7) / .3) ** 2)
        oben = .5 + .15 * max(0, (k - .55) / .45)
        sec = [(-br * .35, -tief), (-br, -.02), (-br * .98, oben * .9), (-br * .6, oben), (br * .6, oben), (br * .98, oben * .9), (br, -.02), (br * .35, -tief)]
        r_.append([bm.verts.new((x, y, z + .1 * max(0, (k - .6) / .4) ** 2)) for y, z in sec])
    for a, b_ in zip(r_, r_[1:]):
        for k in range(8):
            bm.faces.new((a[k], a[(k + 1) % 8], b_[(k + 1) % 8], b_[k]))
    bm.faces.new(r_[0][::-1]); bm.faces.new(r_[-1])
    me = bpy.data.meshes.new("jetski"); bm.to_mesh(me); bm.free()
    me.materials.append(WEISS_L); me.materials.append(GELB)
    for p in me.polygons:
        p.use_smooth = True
        p.material_index = 1 if p.center.z > .35 else 0
    return me


jet = bpy.data.objects.new("jetski", jetski_rumpf()); sc.collection.objects.link(jet)
s_ = jet.modifiers.new("s", "SUBSURF"); s_.levels = 1; s_.render_levels = 2
box("sitz", (1.1, .42, .22), (-.35, 0, .68), mat("sitz", "1a1a1a", .6, Sheen_Weight=.3), .08, seg=4, eltern=jet)
box("lenksaeule", (.25, .3, .25), (.42, 0, .72), GELB, .06, eltern=jet)
rohr("lenker", (.48, -.36, .95), (.48, .36, .95), .022, SCHWARZ, eltern=jet)
for yy in (-.34, .34):
    zyl("griff", .03, .12, (.48, yy, .95), mat("griffgummi", "222222", .8), rot=(P / 2, 0, 0), eltern=jet)
box("schlitten", (1.4, 1.1, .1), (-2.45, 0, .12), GELB, .05, seg=3, eltern=jet)
for yy in (-.5, .5):
    rohr("schlitten_griff", (-3.0, yy, .2), (-1.9, yy, .2), .02, SCHWARZ, eltern=jet)
rohr("schlitten_bug", (-1.75, -.5, .12), (-1.75, .5, .12), .03, SCHWARZ, eltern=jet)
SEIL_M = mat("seil", "f9d71c", .6, Sheen_Weight=.5)
seil = zyl("seil", .008, 1, (0, 0, 0), SEIL_M, v=8)
griff_s = rohr("seilgriff", (-.18, 0, 0), (.18, 0, 0), .018, SCHWARZ)
# Gischt hinter Brett und Jetski
SPRITZ = []
for i in range(14):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, location=(0, -500, -50)); o = bpy.context.object; o.name = "spritz%02d" % i
    dm = o.modifiers.new("d", "DISPLACE"); dm.texture = tex; dm.strength = .35; dm.texture_coords = "OBJECT"; o.data.materials.append(SCHAUM)
    SPRITZ.append(o)

# ======================================================================  IK fuer beide Figuren
for K in (SU, JF):
    K.Z = {nm: leer(K.name + "_ik_" + nm) for nm in ("hand_L", "hand_R", "fuss_L", "fuss_R", "knie_L", "knie_R", "ell_L", "ell_R")}
    K.IK = {}
    for bone, ziel, pol, pw in (("lowerarm02.L", "hand_L", "ell_L", 0), ("lowerarm02.R", "hand_R", "ell_R", 0),
                                ("lowerleg02.L", "fuss_L", "knie_L", -P / 2), ("lowerleg02.R", "fuss_R", "knie_R", -P / 2)):
        c = K.rig.pose.bones[bone].constraints.new("IK"); c.target = K.Z[ziel]; c.chain_count = 4
        c.pole_target = K.Z[pol]; c.pole_angle = pw; K.IK[ziel] = c

# ======================================================================  Wege (Story-Zeit ts)
def catmull(keys, ts):
    if ts <= keys[0][0]:
        return keys[0][1:]
    if ts >= keys[-1][0]:
        return keys[-1][1:]
    for i in range(len(keys) - 1):
        if keys[i][0] <= ts <= keys[i + 1][0]:
            break
    p0 = keys[max(0, i - 1)]; p1 = keys[i]; p2 = keys[i + 1]; p3 = keys[min(len(keys) - 1, i + 2)]
    t = (ts - p1[0]) / (p2[0] - p1[0])
    out = []
    for d in range(1, len(p1)):
        a, b_, c, e = p0[d], p1[d], p2[d], p3[d]
        out.append(.5 * ((2 * b_) + (-a + c) * t + (2 * a - 5 * b_ + 4 * c - e) * t * t + (-a + 3 * b_ - 3 * c + e) * t ** 3))
    return out


T_LOS = 4.0
SURF = [(0, 80, 11), (4.0, 25, 6.5), (6.5, -8, 18), (8.6, -35, 29), (11.0, -95, 24), (12.6, -135, 8), (13.4, -148, .5), (14.0, -155, -5), (16.0, -165, -14)]
JET = [(0, 102, 13), (4.0, 2, 8.5), (5.0, -22, 26), (6.5, -48, 46), (9.0, -95, 56), (12.0, -150, 60), (16.0, -195, 62)]
T_BRUCH0, X_BRUCH0 = 6.5, 7.3


def bruch_x(ts):
    return 400.0 if ts < T_BRUCH0 - .4 else X_BRUCH0 - V_BRUCH * (ts - T_BRUCH0)


def flaeche_z(x, q):
    H = hoehe_x(x)
    if q >= 1.2:
        if q > face_q(H, 0.0, H) - .01:
            return 0.0
        return z_von_q_x(x, q)
    if q >= 0:
        return H * (1 - .02 * q / 1.2)
    return H * max(0, 1 + q / 95) ** 2.1


def weltpunkt(x, q, ts):
    return Vector((x, y_kamm(ts) + q, flaeche_z(x, q)))


def rahmen_weg(keys, ts, hub=.03):
    x, q = catmull(keys, ts)
    p = weltpunkt(x, q, ts)
    x2, q2 = catmull(keys, ts + .05); x1, q1 = catmull(keys, ts - .05)
    f = weltpunkt(x2, q2, ts + .05) - weltpunkt(x1, q1, ts - .05)
    e = .25
    nx = weltpunkt(x + e, q, ts) - weltpunkt(x - e, q, ts); nq = weltpunkt(x, q + e, ts) - weltpunkt(x, q - e, ts)
    nn = nx.cross(nq).normalized()
    if nn.z < 0:
        nn = -nn
    f = (f - nn * f.dot(nn)).normalized()
    l = nn.cross(f).normalized(); up = f.cross(l)
    M = Matrix((f, l, up)).transposed()
    if p.z < .4:                       # flaches Wasser: Meereswellen (Ocean) liegen hoeher
        p = p + Vector((0, 0, .55 * (1 - p.z / .4)))
    return p + nn * hub, M, (x, q)


def rig_mat(H, Fc):
    Z = Vector(H).normalized(); Fc = Vector(Fc); Y = -(Fc - Z * Fc.dot(Z)).normalized(); X = Y.cross(Z)
    return Matrix((X, Y, Z)).transposed()


def surf_pose(ts):
    tow = dict(pel=(0, .1, .95), H=(-.18, .1, 1), hand=((.55, -.08, 1.05), (.52, .1, 1.02)), fuss=((.33, 0, .1), (-.36, 0, .1)), nacken=-.1)
    surf = dict(pel=(0, -.02, .8), H=(.12, .14, 1), hand=((.78, -.18, 1.12), (-.6, .1, .92)), fuss=((.33, 0, .1), (-.36, 0, .1)), nacken=-.05)
    tief = dict(pel=(0, .04, .66), H=(.16, .32, 1), hand=((.7, -.3, 1.0), (-.25, .62, .32)), fuss=((.33, 0, .1), (-.36, 0, .1)), nacken=.05)
    steh = dict(pel=(0, 0, .9), H=(0, 0, 1), hand=((.3, -.25, .9), (-.3, -.25, .9)), fuss=((.33, 0, .1), (-.36, 0, .1)), nacken=0)
    if ts < T_LOS:
        return tow
    if ts < 8.0:
        return mix_pose(tow, surf, ease((ts - T_LOS) / .6))
    if ts < 10.4:
        return mix_pose(surf, tief, ease((ts - 8.0) / .8))
    if ts < 12.6:
        return mix_pose(tief, surf, ease((ts - 10.4) / .8))
    return mix_pose(surf, steh, ease((ts - 12.6) / .8))


def mix_pose(a, b, k):
    if k <= 0:
        return a
    if k >= 1:
        return b
    out = {}
    for key in a:
        va, vb = a[key], b[key]
        if isinstance(va, (int, float)):
            out[key] = va + (vb - va) * k
        elif isinstance(va[0], (int, float)):
            out[key] = tuple(x + (y - x) * k for x, y in zip(va, vb))
        else:
            out[key] = tuple(tuple(x + (y - x) * k for x, y in zip(pa, pb)) for pa, pb in zip(va, vb))
    return out


def setze_rig(K, pos, M, pel_l, H_l, Fc_l):
    Mw = M @ rig_mat(H_l, Fc_l); rq = Mw.to_quaternion()
    pel_w = pos + M @ Vector(pel_l)
    K.rig.rotation_mode = "QUATERNION"; K.rig.rotation_quaternion = rq
    K.rig.location = pel_w - rq.to_matrix() @ (K.PEL * K.SK)
    return pel_w


SURF_STATUS = {}


def figuren(ts):
    BRUCH["x"] = bruch_x(ts)
    welle_setzen(ts); gischt_setzen(ts); oc.time = ts
    # --- Surfer
    SU.zuruecksetzen(); JF.zuruecksetzen()
    pos, M, (xs, qs) = rahmen_weg(SURF, ts, hub=.1)
    brett.matrix_world = Matrix.Translation(pos) @ M.to_4x4()
    po = surf_pose(ts)
    pel_w = setze_rig(SU, pos, M, po["pel"], po["H"], (0, -1, 0))
    for c in SU.IK.values():
        c.influence = 1.0
    for sd, f_ in zip(("L", "R"), po["fuss"]):
        SU.Z["fuss_" + sd].location = pos + M @ Vector(f_)
        s_ = 1 if sd == "L" else -1
        SU.Z["knie_" + sd].location = pel_w + M @ Vector((s_ * .5, -1.6, .2))
        SU.Z["ell_" + sd].location = pel_w + M @ Vector((s_ * .9, .6, .3))
    for sd, h in zip(("L", "R"), po["hand"]):
        SU.Z["hand_" + sd].location = pos + M @ Vector(h)
    jubel = ease((ts - 13.5) / .6)
    if jubel > 0:
        SU.IK["hand_L"].influence = 1 - jubel; SU.IK["hand_R"].influence = 1 - jubel
        SU.dreh("upperarm01.L", z=-.72 + 3.0 * jubel, x=.2 * jubel); SU.dreh("upperarm01.R", z=.72 - 3.0 * jubel, x=.2 * jubel)
        SU.dreh("lowerarm01.L", x=-.4 * jubel); SU.dreh("lowerarm01.R", x=-.4 * jubel)
    SU.dreh("neck01", x=po["nacken"], z=.35 if ts > T_LOS else 0)       # Blick in Fahrtrichtung
    for sd in ("L", "R"):
        for ff in range(2, 6):
            for g in (1, 2, 3):
                SU.dreh(f"finger{ff}-{g}.{sd}", x=(1.2 if ts < T_LOS else .35) + .5 * jubel)
    # --- Jetski + Fahrer
    jpos, JM, (xj, qj) = rahmen_weg(JET, ts, hub=.05)
    neig = .12 * math.sin(ts * 1.7)
    jet.matrix_world = Matrix.Translation(jpos) @ JM.to_4x4() @ Matrix.Rotation(neig, 4, "X") @ Matrix.Rotation(-.08, 4, "Y")
    JW = jet.matrix_world.to_3x3()
    pj = setze_rig(JF, jpos, JW, (-.28, 0, .8), (.35, 0, 1), (1, 0, 0))
    for c in JF.IK.values():
        c.influence = 1.0
    for sd, s_ in (("L", 1), ("R", -1)):
        JF.Z["fuss_" + sd].location = jpos + JW @ Vector((.05, s_ * .3, .38))
        JF.Z["hand_" + sd].location = jpos + JW @ Vector((.48, s_ * .32, .97))
        JF.Z["knie_" + sd].location = pj + JW @ Vector((1.5, s_ * .8, .3))
        JF.Z["ell_" + sd].location = pj + JW @ Vector((-.2, s_ * 1.2, -.2))
    JF.dreh("neck01", x=-.2, z=(-.6 if ts < T_LOS else 0))                # schaut zurueck zum Surfer
    for sd in ("L", "R"):
        for ff in range(2, 6):
            for g in (1, 2, 3):
                JF.dreh(f"finger{ff}-{g}.{sd}", x=1.2)
    bpy.context.view_layer.update()
    # --- Seil + Griff
    heck = jet.matrix_world @ Vector((-1.75, 0, .5))
    haende = (SU.rig.matrix_world @ SU.rig.pose.bones["lowerarm02.L"].tail + SU.rig.matrix_world @ SU.rig.pose.bones["lowerarm02.R"].tail) / 2
    if ts < T_LOS:
        g = haende
    else:
        k = ease((ts - T_LOS) / 1.0)
        hinten = jet.matrix_world @ Vector((-16, 0, 0)); hinten.z = flaeche_z(xj - 16, qj) + .05
        g = haende.lerp(hinten, k); g.z += 2.0 * math.sin(min(1, (ts - T_LOS) / 1.0) * P) * (1 - k)
    d = g - heck; seil.location = (heck + g) / 2; seil.scale = (1, 1, max(.01, d.length))
    seil.rotation_mode = "QUATERNION"; seil.rotation_quaternion = d.to_track_quat("Z", "Y")
    griff_s.location = g; griff_s.rotation_mode = "QUATERNION"; griff_s.rotation_quaternion = d.to_track_quat("Y", "Z")
    # --- Spritzwasser hinter Brett und Jetski
    for i, o in enumerate(SPRITZ):
        o.hide_render = True
        continue
        quelle, mm, ww = (brett, M, .42) if i < 9 else (jet, JW, .6)
        k = (i % 9) / 8 if i < 9 else (i - 9) / 4
        hinten = quelle.matrix_world @ Vector((-1.0 - 2.5 * k, (.3 if i % 2 else -.3) * k * 3, .1 + .5 * math.sin(k * P)))
        o.location = hinten; r = ww * (.25 + .5 * math.sin(k * P)); o.scale = (r, r * .8, r * .7); o.rotation_euler = (i, ts * 3 + i, 0)
    return pel_w


def becken():
    nk = SU.rig.matrix_world @ SU.rig.pose.bones["neck01"].head
    return (SU.rig.matrix_world @ SU.PEL) * .6 + nk * .4


# ======================================================================  Kamera
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam
cam.data.clip_start = .05; cam.data.clip_end = 6000; cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
cam.data.dof.use_dof = True
# Positionen: "B+" Versatz zum Surfer, "W" in Wellen-Koordinaten (x, q vor dem Kamm, z), sonst Welt
SZ = [
    (0.00, 1.50, 8.75, 9.00, "B+", (-7, 8, .5), (-7, 8, .6), "B", "B", 30),                                   # Aufhaenger: Zeitlupe, Lippe kracht dahinter
    (1.50, 2.70, 4.6, 5.8, "P", (160, 50, 58), (158, 50, 58), "B", "B", 55),                                   # von der Klippe (Tele)
    (2.70, 4.00, 2.0, 3.0, "W", (10, 46, 1.4), (6, 45, 1.6), ("W", (10, 0, 22)), ("W", (6, 0, 23)), 18),       # Wand von unten
    (4.00, 5.40, 0.0, 0.8, "P", (FX + 30, FY + 10, klippe_z(FX + 30, FY + 10) + 8), (FX + 27, FY + 8, klippe_z(FX + 30, FY + 10) + 8.5), (FX - 6, FY - 8, FZ + 11), (FX - 6, FY - 8, FZ + 11), 30),  # Leuchtturm + Welle
    (5.40, 6.80, 0.8, 2.2, "B+", (-8, 18, 6), (-11, 18, 6), "M", "M", 22),                                    # Jetski zieht, seitlich
    (6.80, 8.20, 2.2, 3.6, "B+", (6, 1.8, 2.2), (6, 1.8, 2.2), "J", "J", 26),                                # hinter dem Surfer, Blick zum Jetski
    (8.20, 9.40, 3.75, 4.3, "B+", (1.4, 2.0, .9), (1.3, 2.1, 1.0), "B", "B", 30),                             # loslassen, Zeitlupe
    (9.40, 11.30, 4.3, 5.6, "B+", (-6, 12, -1.0), (-7, 12, -.6), "B", "B", 22),                            # vorne unten: Wand dahinter
    (11.30, 13.30, 5.6, 6.4, "W", (-30, 52, 1.5), (-30, 58, 30), ("W", (-30, 3, 4)), ("W", (-30, 0, 26)), 22), # Kranfahrt die Wand hoch
    (13.30, 15.20, 6.6, 8.0, "B+", (3.5, 3.0, 1.5), (3.5, 3.0, 1.6), "B", "B", 28),                          # runter, mitfahrend
    (15.20, 17.10, 8.4, 9.6, "B+", (-16, 20, 2.0), (-17, 20, 2.0), "B", "B", 26),                            # bricht hinter ihm
    (17.10, 19.50, 9.0, 9.6, "W", (-75, 82, 4), (-72, 82, 4.5), ("W", (-25, 8, 12)), ("W", (-25, 8, 12)), 30),  # weit, 26.21 m
    (19.50, 21.60, 12.6, 13.8, "B+", (-5, 5, 1.2), (-5.5, 5, 1.6), "B", "B", 30),                            # rausfahren, Jubel
    (21.60, 23.60, 13.8, 15.6, "B+", (-10, 22, 4), (-16, 42, 12), "B", "B", 26),                               # Rueckfahrt weit
]


def wpkt(v, ts):
    return Vector((v[0], y_kamm(ts) + v[1], v[2]))


def zustand(t):
    for s in SZ:
        if s[0] <= t < s[1]:
            break
    k = (t - s[0]) / (s[1] - s[0])
    ts = s[2] + (s[3] - s[2]) * k
    k = ease(k) * .7 + k * .3
    figuren(ts)
    bk = becken()
    if s[4] == "B+":
        pos = bk + lerpv(s[5], s[6], k)
    elif s[4] == "W":
        pos = wpkt(lerpv(s[5], s[6], k), ts)
    else:
        pos = lerpv(s[5], s[6], k)
    if s[7] == "B":
        ziel = bk
    elif s[7] == "M":
        ziel = (bk + jet.matrix_world.translation) / 2
    elif s[7] == "J":
        ziel = jet.matrix_world.translation + Vector((0, 0, .8))
    elif isinstance(s[7], tuple) and s[7][0] == "W":
        ziel = wpkt(lerpv(s[7][1], s[8][1], k), ts)
    else:
        ziel = lerpv(s[7], s[8], k)
    pos.z = max(pos.z, .6)
    cam.location = pos; d = ziel - pos; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = s[9]; cam.data.dof.focus_distance = d.length; cam.data.dof.aperture_fstop = 2.8 if d.length < 8 else 11
    zit = .012
    cam.location += Vector((zit * math.sin(t * 7.3), zit * math.cos(t * 5.1), zit * math.sin(t * 9.7)))


os.makedirs(A.ordner, exist_ok=True)
N = int(round(D * A.fps))
liste = [int(round(float(x) * A.fps)) for x in A.nur.split(",")] if A.nur else list(range(A.start, N))
for f in liste:
    pfad = os.path.join(A.ordner, f"welle_{f:04d}.png")
    if os.path.exists(pfad) and not A.nur:
        continue
    zustand(f / A.fps); bpy.context.view_layer.update(); zustand(f / A.fps)
    sc.render.filepath = pfad
    bpy.ops.render.render(write_still=True); print("FERTIG", pfad, flush=True)
