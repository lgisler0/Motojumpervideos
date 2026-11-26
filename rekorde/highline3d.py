"""Hoechste Highline ueber einem Wasserfall (Angel Falls, Venezuela, Okt. 2025, GWR/ISA: 148 m lang, >1000 m hoch). Realistischer Stil.
python3 highline3d.py <ordner> [--nur t1,t2] [--start i] [--samples n]"""
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
D = 27.0
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


# ======================================================================  Menschen (zuerst)
import mensch_echt as ME
LOGO = ME.logo_bild(os.path.join(HIER, "_logo_norda.png"), "NORDA", farbe=(1, 1, 1))
LU = ME.mensch("irmler", 23, 1.0, .4, .6, .25, haut="caucasian", haare="short04", braue="eyebrow001", haarfarbe="6b4a2e")
ME.trikot(LU, "lang", "tights", "2e7d32", "2b2f36", brust=LOGO, brust_mass=(.16, .08), bein=LOGO)
FREUNDE = []
for i, (sd, mn, hh, fo, fu, haut) in enumerate(((31, 1.0, "short02", "c62828", "1f2a44", "caucasian"), (44, 0.0, "ponytail01", "1565c0", "2b2f36", "caucasian"),
                                                (57, 1.0, "short03", "f9a825", "2b2f36", "african"))):
    F = ME.mensch("freund%d" % i, sd, mn, .35, .55, .3, haut=haut, haare=hh, braue="eyebrow010", haarfarbe="1a120c")
    ME.trikot(F, "lang", "tights", fo, fu, brust=LOGO, brust_mass=(.16, .08))
    FREUNDE.append(F)
for K, hs in [(LU, 1.80)] + [(F, 1.74) for F in FREUNDE]:
    for o in K.huellen:
        if "versatz" in o.modifiers:
            o.modifiers["versatz"].strength = .017 if o.name.endswith("_hemd") else .010
        for md in o.modifiers:
            if md.type == "SUBSURF":
                md.render_levels = 2
    hoehe = max(v.z for v in K.EV); K.SK = hs / hoehe; K.rig.scale = (K.SK,) * 3
    K.PEL = K.rig.data.bones["upperleg01.L"].head_local.copy(); K.PEL.x = 0
print("ok menschen")

# ======================================================================  Materialien, Himmel, Sonne
SCHWARZ = mat("schwarzlack", "0d0d0f", .4, Coat_Weight=.3)
STAHL = pbr("stahl", "Metal012", 6, rau_mul=.6, rau_add=.15, metal=1.0)
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; nt = w.node_tree
env = nt.nodes.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(os.path.join(ASSET, "tag.hdr"))
nt.links.new(env.outputs[0], nt.nodes["Background"].inputs[0]); nt.nodes["Background"].inputs[1].default_value = 1.0
bpy.ops.object.light_add(type="SUN", rotation=(math.radians(48), 0, math.radians(-30))); sonne = bpy.context.object
sonne.data.energy = 4.0; sonne.data.angle = math.radians(1.0); sonne.data.color = (1, .95, .86)


def fels_mat():
    """Tepui-Sandstein: dunkelgrau mit orangen Streifen (Schichten) + Foto-Textur"""
    m = bpy.data.materials.new("tepui"); m.use_nodes = True; nt_ = m.node_tree; n = nt_.nodes; l = nt_.links; b = n["Principled BSDF"]
    pfad = os.path.join(ASSET, "Rock035", "Rock035_1K-JPG", "Rock035_1K-JPG")
    tc = n.new("ShaderNodeTexCoord"); mp = n.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (.06, .06, .06); l.new(tc.outputs["Object"], mp.inputs[0])
    c = n.new("ShaderNodeTexImage"); c.image = bpy.data.images.load(pfad + "_Color.jpg", check_existing=True); c.projection = "BOX"; c.projection_blend = .3
    l.new(mp.outputs[0], c.inputs[0])
    nm = n.new("ShaderNodeTexImage"); nm.image = bpy.data.images.load(pfad + "_NormalGL.jpg", check_existing=True); nm.image.colorspace_settings.name = "Non-Color"
    nm.projection = "BOX"; l.new(mp.outputs[0], nm.inputs[0])
    nmap = n.new("ShaderNodeNormalMap"); nmap.inputs["Strength"].default_value = 1.2; l.new(nm.outputs[0], nmap.inputs["Color"]); l.new(nmap.outputs[0], b.inputs["Normal"])
    sep = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Object"], sep.inputs[0])
    no = n.new("ShaderNodeTexNoise"); no.inputs["Scale"].default_value = .02; no.inputs["Detail"].default_value = 4; l.new(tc.outputs["Object"], no.inputs["Vector"])
    zz = n.new("ShaderNodeMath"); zz.operation = "MULTIPLY_ADD"; zz.inputs[1].default_value = 30; l.new(no.outputs[0], zz.inputs[0]); l.new(sep.outputs["Z"], zz.inputs[2])
    wv = n.new("ShaderNodeTexWave"); wv.wave_type = "BANDS"; wv.bands_direction = "Z"; wv.inputs["Scale"].default_value = .012; wv.inputs["Distortion"].default_value = 3
    cz = n.new("ShaderNodeCombineXYZ"); l.new(zz.outputs[0], cz.inputs["Z"]); l.new(cz.outputs[0], wv.inputs["Vector"])
    rp = n.new("ShaderNodeValToRGB"); l.new(wv.outputs["Fac"], rp.inputs[0])
    rp.color_ramp.elements[0].color = (*hexf("2a2622"), 1); rp.color_ramp.elements[1].color = (*hexf("7a5038"), 1)
    rp.color_ramp.elements.new(.55).color = (*hexf("5a4a3e"), 1)
    mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"; mx.inputs[0].default_value = .85
    l.new(rp.outputs[0], mx.inputs[6]); l.new(c.outputs[0], mx.inputs[7])
    # Oberseite: Gruen (Moos/Gras) wo die Flaeche flach ist
    geo = n.new("ShaderNodeNewGeometry"); sn = n.new("ShaderNodeSeparateXYZ"); l.new(geo.outputs["Normal"], sn.inputs[0])
    rn = n.new("ShaderNodeMapRange"); rn.inputs[1].default_value = .92; rn.inputs[2].default_value = .97; l.new(sn.outputs["Z"], rn.inputs[0])
    gr = n.new("ShaderNodeMix"); gr.data_type = "RGBA"; l.new(rn.outputs[0], gr.inputs[0]); l.new(mx.outputs[2], gr.inputs[6]); gr.inputs[7].default_value = (*hexf("4a5a2a"), 1)
    l.new(gr.outputs[2], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = .85
    return m


FELS = fels_mat()


def dschungel_mat():
    m = bpy.data.materials.new("dschungel"); m.use_nodes = True; nt_ = m.node_tree; n = nt_.nodes; l = nt_.links; b = n["Principled BSDF"]
    tc = n.new("ShaderNodeTexCoord")
    vo = n.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = .25; l.new(tc.outputs["Object"], vo.inputs["Vector"])
    no = n.new("ShaderNodeTexNoise"); no.inputs["Scale"].default_value = .03; l.new(tc.outputs["Object"], no.inputs["Vector"])
    rp = n.new("ShaderNodeValToRGB"); l.new(no.outputs["Fac"], rp.inputs[0])
    rp.color_ramp.elements[0].color = (*hexf("1d3a14"), 1); rp.color_ramp.elements[1].color = (*hexf("4f7a2a"), 1)
    mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"; mx.inputs[0].default_value = .6
    l.new(rp.outputs[0], mx.inputs[6]); l.new(vo.outputs["Distance"], mx.inputs[7])
    l.new(mx.outputs[2], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = .9
    bu = n.new("ShaderNodeBump"); bu.inputs["Strength"].default_value = .8; l.new(vo.outputs["Distance"], bu.inputs["Height"]); l.new(bu.outputs[0], b.inputs["Normal"])
    return m


DSCHUNGEL = dschungel_mat()

# ======================================================================  Tafelberg mit Schlucht (Hoehenfeld)
LINE_L = 148.0
AX, BX = -LINE_L / 2, LINE_L / 2
BODEN = -1008.0
SCHLUCHT_Y = 70.0          # Rueckwand der Schlucht (dort faellt der Wasserfall)


def rauh(x, y, f, s):
    return math.sin(x * f + s) * math.cos(y * f * 1.3 + s * 2) + .5 * math.sin(x * f * 2.3 - y * f * 1.9 + s * 3)


def plateau_abstand(x, y):
    """>0 innen (Plateau), <0 aussen (Luft)."""
    # Plateau-Vorderkante bei y = -160 (+ Zacken), Schlucht zwischen x = AX..BX bis zur Rueckwand
    d_vorne = y + 160 + 25 * rauh(x, 0, .02, 1)
    halb = LINE_L / 2 + 6 * rauh(0, y, .05, 2) + max(0, -y - 40) * .25
    d_schlucht = max(abs(x) - halb, y - SCHLUCHT_Y - 6 * rauh(x, 0, .1, 3))
    d_seiten = 380 - abs(x) + 15 * rauh(0, y, .03, 4)
    d_hinten = 320 - y + 15 * rauh(x, 0, .03, 6)
    return min(d_vorne, d_schlucht, d_seiten, d_hinten)


def gelaende_z(x, y):
    d = plateau_abstand(x, y)
    k = max(0, min(1, (d + 2.0) / 4.0))
    oben = -2.0 + 1.5 * rauh(x, y, .08, 5) + .6 * rauh(x, y, .3, 7)
    unten = BODEN + 25 * rauh(x, y, .006, 9) + max(0, -d) * .05
    z = unten + (oben - unten) * (k * k * (3 - 2 * k))
    # Stufen in der Wand (Schichten)
    if 0 < k < 1:
        z += 0
    return z


def gitter(name, x0, x1, y0, y1, nx, ny, fz, material):
    bm = bmesh.new(); vs = []
    for j in range(ny + 1):
        row = []
        y = y0 + (y1 - y0) * j / ny
        for i in range(nx + 1):
            x = x0 + (x1 - x0) * i / nx
            row.append(bm.verts.new((x, y, fz(x, y))))
        vs.append(row)
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o); me.materials.append(material)
    for p in me.polygons:
        p.use_smooth = True
    return o


tepui = gitter("tepui", -420, 420, -420, 360, 420, 390, gelaende_z, FELS)
# Wandstruktur: Displace mit Wolken-Textur (nur waagrecht wirksam ueber Normale)
tx = bpy.data.textures.new("wandtex", "CLOUDS"); tx.noise_scale = 6; tx.noise_depth = 2
dmw = tepui.modifiers.new("d", "DISPLACE"); dmw.texture = tx; dmw.strength = 2.5; dmw.mid_level = .5
boden = gitter("boden", -3000, 3000, -3500, 2500, 160, 160, lambda x, y: BODEN - 8 + 18 * rauh(x, y, .004, 2) if abs(x) > 400 or y < -400 or y > 340 else BODEN - 40, DSCHUNGEL)
# ferne Tepuis am Horizont
for (cx, cy, r, h) in ((-2600, -1800, 700, 900), (2400, -2200, 900, 1100), (-1800, 1800, 800, 800), (2600, 1200, 600, 700)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=r, depth=h, location=(cx, cy, BODEN + h / 2)); o = bpy.context.object
    o.data.materials.append(FELS); dm = o.modifiers.new("d", "DISPLACE"); dm.texture = tx; dm.strength = 60
    ss = o.modifiers.new("s", "SUBSURF"); ss.levels = 2; ss.render_levels = 2
    o.modifiers.move(1, 0)

# ======================================================================  Wasserfall (faellt an der Rueckwand der Schlucht)
WF_X = 0.0


def wasser_band(name, breite0, breite1, abstand, mat_):
    bm = bmesh.new(); r_ = []
    n = 120
    for i in range(n + 1):
        k = i / n
        z = -4 - 975 * k
        y = SCHLUCHT_Y - 4 - abstand * (1 - (1 - k) ** 2) - 6 * k
        br = breite0 + (breite1 - breite0) * k ** .7
        r_.append([bm.verts.new((WF_X + br * s / 2 + 3 * math.sin(k * 9), y + 2 * math.sin(k * 7 + s), z)) for s in (-1, -.33, .33, 1)])
    for a, b_ in zip(r_, r_[1:]):
        for k in range(3):
            bm.faces.new((a[k], a[k + 1], b_[k + 1], b_[k]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    uv = me.uv_layers.new();
    for poly in me.polygons:
        for li in poly.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = ((v.x + 60) / 120, -v.z / 975)
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o); me.materials.append(mat_)
    for p in me.polygons:
        p.use_smooth = True
    return o


def fall_mat(name, dichte):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt_ = m.node_tree; n = nt_.nodes; l = nt_.links; b = n["Principled BSDF"]
    out = n["Material Output"]
    tc = n.new("ShaderNodeTexCoord"); mp = n.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (14, 2.5, 1)
    l.new(tc.outputs["UV"], mp.inputs[0]); FALL_MAPS.append(mp)
    no = n.new("ShaderNodeTexNoise"); no.inputs["Scale"].default_value = 3; no.inputs["Detail"].default_value = 6; no.inputs["Distortion"].default_value = .4
    l.new(mp.outputs[0], no.inputs["Vector"])
    rr = n.new("ShaderNodeMapRange"); rr.inputs[1].default_value = .45 - dichte; rr.inputs[2].default_value = .65; l.new(no.outputs["Fac"], rr.inputs[0])
    b.inputs["Base Color"].default_value = (.95, .97, .98, 1); b.inputs["Roughness"].default_value = .5
    b.inputs["Subsurface Weight"].default_value = .5; b.inputs["Emission Color"].default_value = (1, 1, 1, 1); b.inputs["Emission Strength"].default_value = .08
    tr = n.new("ShaderNodeBsdfTransparent"); mx = n.new("ShaderNodeMixShader"); l.new(rr.outputs[0], mx.inputs[0])
    l.new(tr.outputs[0], mx.inputs[1]); l.new(b.outputs[0], mx.inputs[2]); l.new(mx.outputs[0], out.inputs["Surface"])
    return m


FALL_MAPS = []
fall1 = wasser_band("wasserfall", 14, 70, 26, fall_mat("fall_kern", .25))
fall2 = wasser_band("wasserfall_gischt", 24, 120, 34, fall_mat("fall_gischt", .05))
# Fluss auf dem Plateau, der zur Kante fliesst
FLUSS = mat("fluss", "3a2a18", .05, Coat_Weight=1.0)
bpy.ops.mesh.primitive_plane_add(size=1, location=(WF_X, SCHLUCHT_Y + 40, -1.6)); fl = bpy.context.object; fl.scale = (14, 82, 1); fl.data.materials.append(FLUSS)
# Wolken/Nebel unter der Leine (halbtransparente Ebenen mit Rauschen)
NEBEL_M = bpy.data.materials.new("nebel"); NEBEL_M.use_nodes = True; nn_ = NEBEL_M.node_tree.nodes; ln_ = NEBEL_M.node_tree.links
noi = nn_.new("ShaderNodeTexNoise"); noi.inputs["Scale"].default_value = .004; noi.inputs["Detail"].default_value = 6; tcn = nn_.new("ShaderNodeTexCoord")
ln_.new(tcn.outputs["Object"], noi.inputs["Vector"]); NEBEL_NOISE = noi
rrn = nn_.new("ShaderNodeMapRange"); rrn.inputs[1].default_value = .52; rrn.inputs[2].default_value = .7; ln_.new(noi.outputs["Fac"], rrn.inputs[0])
trn = nn_.new("ShaderNodeBsdfTransparent"); mxn = nn_.new("ShaderNodeMixShader"); ln_.new(rrn.outputs[0], mxn.inputs[0])
bn = nn_["Principled BSDF"]; bn.inputs["Base Color"].default_value = (1, 1, 1, 1); bn.inputs["Roughness"].default_value = 1; bn.inputs["Subsurface Weight"].default_value = .6
ln_.new(trn.outputs[0], mxn.inputs[1]); ln_.new(bn.outputs[0], mxn.inputs[2]); ln_.new(mxn.outputs[0], nn_["Material Output"].inputs["Surface"])
for zz_ in (-420, -700):
    bpy.ops.mesh.primitive_plane_add(size=5000, location=(0, -400, zz_)); o = bpy.context.object; o.data.materials.append(NEBEL_M)
    o.rotation_euler = (0, 0, zz_ * .01)

# ======================================================================  Leine, Anker, Sicherung
LINE_Z = 0.0
ANKER_A = Vector((AX - 2, 0, LINE_Z)); ANKER_B = Vector((BX + 2, 0, LINE_Z))
BAND_M = mat("band", "e65100", .5, Sheen_Weight=.6)
NBAND = 300
bm = bmesh.new(); r_ = []
for i in range(NBAND + 1):
    r_.append([bm.verts.new((0, 0, 0)), bm.verts.new((0, 0, 0)), bm.verts.new((0, 0, 0)), bm.verts.new((0, 0, 0))])
for a, b_ in zip(r_, r_[1:]):
    for k in range(4):
        bm.faces.new((a[k], a[(k + 1) % 4], b_[(k + 1) % 4], b_[k]))
me_b = bpy.data.meshes.new("leine"); bm.to_mesh(me_b); bm.free()
leine = bpy.data.objects.new("leine", me_b); sc.collection.objects.link(leine); me_b.materials.append(BAND_M)
SAG_MAX = 9.0


def leine_z(x, u, schwank):
    """Hoehe der Leine an x, wenn der Laeufer an Anteil u steht (Durchhang dort am groessten)."""
    k = (x - ANKER_A.x) / (ANKER_B.x - ANKER_A.x); k = min(1, max(0, k))
    xs = ANKER_A.x + (ANKER_B.x - ANKER_A.x) * u
    sag = .8 + SAG_MAX * 4 * u * (1 - u)
    if x <= xs:
        t = k / max(1e-3, u); z = -sag * t
    else:
        t = (1 - k) / max(1e-3, 1 - u); z = -sag * t
    z -= .8 * 4 * k * (1 - k)          # Grunddurchhang
    return LINE_Z + z, schwank * math.sin(k * P) * (1 - abs(k - u) * 1.5 if abs(k - u) < .66 else 0)


def leine_setzen(u, schwank):
    co = []
    for i in range(NBAND + 1):
        x = ANKER_A.x + (ANKER_B.x - ANKER_A.x) * i / NBAND
        z, y = leine_z(x, u, schwank)
        for (dy, dz) in ((-.0125, 0), (-.0125, .004), (.0125, .004), (.0125, 0)):
            co += [x, y + dy, z + dz]
    me_b.vertices.foreach_set("co", co); me_b.update()


for A_ in (ANKER_A, ANKER_B):
    s_ = 1 if A_.x < 0 else -1
    for dy in (-.6, .6):
        zyl("bolzen", .03, .12, A_ + Vector((-s_ * 1.2, dy, -1.6)), STAHL, rot=(0, P / 2, 0))
        rohr("schlinge", A_ + Vector((-s_ * 1.2, dy, -1.6)), A_, .012, mat("schlinge", "1565c0", .6) if not bpy.data.materials.get("schlinge") else bpy.data.materials["schlinge"])
    box("spanner", (.3, .08, .08), A_ + Vector((s_ * .2, 0, 0)), STAHL, .01)
# Sicherungsring + Leash
RING = bpy.data.objects.new("ring", None); sc.collection.objects.link(RING)
bpy.ops.mesh.primitive_torus_add(major_radius=.05, minor_radius=.008, location=(0, 0, 0)); ring = bpy.context.object; ring.data.materials.append(STAHL)
leash = zyl("leash", .007, 1, (0, 0, 0), mat("leashseil", "c62828", .6), v=8)
gurt = box("gurt", (.34, .26, .07), (0, 0, 0), mat("gurtband", "1a1a1a", .7), .02)
print("ok szene")
# ======================================================================  IK fuer den Laeufer
LU.Z = {nm: leer("lu_ik_" + nm) for nm in ("hand_L", "hand_R", "fuss_L", "fuss_R", "knie_L", "knie_R", "ell_L", "ell_R")}
LU.IK = {}
for bone, ziel, pol, pw in (("lowerarm02.L", "hand_L", "ell_L", 0), ("lowerarm02.R", "hand_R", "ell_R", 0),
                            ("lowerleg02.L", "fuss_L", "knie_L", -P / 2), ("lowerleg02.R", "fuss_R", "knie_R", -P / 2)):
    c = LU.rig.pose.bones[bone].constraints.new("IK"); c.target = LU.Z[ziel]; c.chain_count = 4
    c.pole_target = LU.Z[pol]; c.pole_angle = pw; LU.IK[ziel] = c


def rig_mat(H, Fc):
    Z = Vector(H).normalized(); Fc = Vector(Fc); Y = -(Fc - Z * Fc.dot(Z)).normalized(); X = Y.cross(Z)
    return Matrix((X, Y, Z)).transposed()


def setze_rig(K, pel_w, H, Fc):
    rq = rig_mat(H, Fc).to_quaternion()
    K.rig.rotation_mode = "QUATERNION"; K.rig.rotation_quaternion = rq
    K.rig.location = pel_w - rq.to_matrix() @ (K.PEL * K.SK)


# Freunde am Ziel (stehen auf dem Fels, schauen zum Laeufer)
for i, F in enumerate(FREUNDE):
    x = BX + 5 + i * 1.6; y = (-2.2, 2.0, -.4)[i]
    zb = gelaende_z(x, y)
    setze_rig(F, Vector((x, y, zb + F.PEL.z * F.SK + .02)), (0, 0, 1), (-1, -.15 * y, 0))
    F.x0 = (x, y, zb)

T_GESAMT = 268.0
LS = .44                     # Schrittlaenge
T_SCHRITT = .8
START_X = AX + 1.6


def weg_d(ts):
    return min(BX - 6.0 - START_X, LS * ts / T_SCHRITT)


def fuss_x(ts, versatz):
    s = ts / T_SCHRITT + versatz
    n = math.floor(s / 2); ph = s / 2 - n
    pos = 2 * LS * n + (2 * LS * ease((ph - .5) / .5) if ph > .5 else 0)
    hub = .06 * math.sin(max(0, (ph - .5) / .5) * P) if ph > .5 else 0
    return min(BX - 5.8, START_X + pos - LS * .5 - LS * versatz), hub


def zustand_figur(ts):
    LU.zuruecksetzen()
    d = weg_d(ts); u = (START_X + d - ANKER_A.x) / (ANKER_B.x - ANKER_A.x)
    schwank = .18 * math.sin(ts * 1.9) + .08 * math.sin(ts * 4.3)
    leine_setzen(u, schwank)
    fertig = START_X + weg_d(ts) >= BX - 6.01
    for c in LU.IK.values():
        c.influence = 1.0
    fx = {}
    for sd, vs in (("L", 0.0), ("R", 1.0)):
        x, hub = fuss_x(ts, vs) if not fertig else (START_X + d + (.15 if sd == "L" else -.15), 0)
        z, y = leine_z(x, u, schwank)
        fx[sd] = Vector((x, y, z + .045 + hub))
        LU.Z["fuss_" + sd].location = fx[sd]
    px = (fx["L"].x + fx["R"].x) / 2
    zl, yl = leine_z(px, u, schwank)
    seit = .05 * math.sin(ts * 2.6)
    pel_w = Vector((px, yl + seit, zl + .93))
    jubel = ease((ts - (T_GESAMT - 1.6)) / .7) if fertig else 0.0
    H = Vector((0, -.06 * math.sin(ts * 2.6) - schwank * .1, 1))
    setze_rig(LU, pel_w, H, (1, 0, 0))
    arm = .1 * math.sin(ts * 3.1)
    LU.Z["hand_L"].location = pel_w + Vector((.08, .66, .62 + arm))
    LU.Z["hand_R"].location = pel_w + Vector((.08, -.66, .62 - arm))
    for sd, s_ in (("L", 1), ("R", -1)):
        LU.Z["knie_" + sd].location = pel_w + Vector((1.6, s_ * .45, -.4))
        LU.Z["ell_" + sd].location = pel_w + Vector((-.3, s_ * 1.4, -.2))
    if jubel > 0:
        LU.IK["hand_L"].influence = 1 - jubel; LU.IK["hand_R"].influence = 1 - jubel
        LU.dreh("upperarm01.L", z=-.72 + 3.0 * jubel, x=.2 * jubel); LU.dreh("upperarm01.R", z=.72 - 3.0 * jubel, x=.2 * jubel)
        LU.dreh("lowerarm01.L", x=-.4 * jubel); LU.dreh("lowerarm01.R", x=-.4 * jubel)
    LU.dreh("neck01", x=.12 - .3 * jubel)                       # Blick leicht nach vorne unten auf die Leine
    for sd in ("L", "R"):
        for ff in range(2, 6):
            for g in (1, 2, 3):
                LU.dreh(f"finger{ff}-{g}.{sd}", x=.25 + .4 * jubel)
    # Freunde jubeln am Ende
    for i, F in enumerate(FREUNDE):
        F.zuruecksetzen()
        j = ease((ts - (T_GESAMT - 2.2 + i * .25)) / .6)
        hop = .08 * max(0, math.sin((ts + i) * 9)) * j
        x, y, zb = F.x0
        setze_rig(F, Vector((x, y, zb + F.PEL.z * F.SK + .02 + hop)), (0, 0, 1), (-1, -.15 * y, 0))
        F.dreh("upperarm01.L", z=-.72 + 3.0 * j, x=.2 * j); F.dreh("upperarm01.R", z=.72 - 3.0 * j, x=.2 * j)
        F.dreh("lowerarm01.L", x=-.3 - .3 * j); F.dreh("lowerarm01.R", x=-.3 - .3 * j)
    bpy.context.view_layer.update()
    # Fuesse entlang der Leine ausrichten (leicht nach aussen gedreht)
    for sd, s_ in (("L", 1), ("R", -1)):
        pb = LU.rig.pose.bones["foot." + sd]
        Mb = LU.rig.matrix_world @ pb.matrix
        ist = (Mb.to_3x3() @ Vector((0, 1, 0))).normalized()
        soll = Vector((math.cos(.3), s_ * math.sin(.3), -.25)).normalized()
        dq = ist.rotation_difference(soll)
        pb.matrix = LU.rig.matrix_world.inverted() @ (Matrix.Translation(Mb.translation) @ (dq.to_matrix() @ Mb.to_3x3()).to_4x4())
    bpy.context.view_layer.update()
    # Gurt, Ring, Leash
    gurt.location = pel_w + Vector((0, 0, .02)); gurt.rotation_euler = (0, 0, 0)
    rx = max(ANKER_A.x + .5, px - 1.1); rz, ry = leine_z(rx, u, schwank)
    ring.location = (rx, ry, rz + .01); ring.rotation_euler = (P / 2, 0, P / 2)
    a = gurt.location; b_ = Vector((rx, ry, rz + .04))
    dv = b_ - a; leash.location = (a + b_) / 2; leash.scale = (1, 1, max(.01, dv.length))
    leash.rotation_mode = "QUATERNION"; leash.rotation_quaternion = dv.to_track_quat("Z", "Y")
    # Wasserfall + Nebel bewegen
    for mp in FALL_MAPS:
        mp.inputs["Location"].default_value[1] = ts * .35
    NEBEL_NOISE.inputs["W"].default_value = ts * .01 if "W" in NEBEL_NOISE.inputs else 0
    return pel_w, (fx["L"] + fx["R"]) / 2


NEBEL_NOISE.noise_dimensions = "4D"


def becken():
    nk = LU.rig.matrix_world @ LU.rig.pose.bones["neck01"].head
    return (LU.rig.matrix_world @ LU.PEL) * .55 + nk * .45


# ======================================================================  Kamera
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam
cam.data.clip_start = .03; cam.data.clip_end = 12000; cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
cam.data.dof.use_dof = True
SZ = [
    (0.00, 1.50, 130.0, 130.6, "B+", (2.5, -4.0, -2.5), (2.6, -4.2, -2.6), "B", "B", 24),                     # Aufhaenger: von unten, Wasserfall dahinter
    (1.50, 2.80, 40.0, 41.6, "B+", (.7, -1.5, -.8), (.8, -1.5, -.8), "F", "F", 35),                            # Fuesse auf dem Band
    (2.80, 3.60, 60.0, 61.0, "B+", (1, -3, 0), (12, -70, -18), "B", "B", 24),                                 # schnell zurueck: Abgrund
    (3.60, 5.20, 80.0, 80.0, "P", (-380, -720, 160), (-350, -705, 150), (0, 60, -330), (0, 60, -320), 28),     # Angel Falls, weit
    (5.20, 7.40, 80.0, 82.0, "P", (70, -150, -560), (70, -150, -530), (0, 60, -150), (0, 60, -20), 24),       # am Wasserfall hoch
    (7.40, 10.00, 0.0, 0.0, "P", (260, -1350, BODEN + 70), (210, -980, BODEN + 90), (0, -160, -350), (0, -160, -300), 24),  # Dschungel-Flug
    (10.00, 12.70, 30.0, 33.0, "P", (AX - 1.5, .7, 3.2), (AX - 1.0, .7, 2.9), (BX, 0, -5.0), (BX, 0, -5.0), 20),              # ganze Leine von der Seite
    (12.70, 16.20, 100.0, 103.5, "B+", (.45, .5, 2.3), (.45, .5, 2.7), "U", "U", 18),                         # senkrecht nach unten
    (16.20, 18.00, 150.0, 151.8, "B+", (.2, -2.2, -.7), (.3, -2.2, -.7), "F", "F", 32),                       # Schritte
    (18.00, 20.50, 160.0, 162.5, "B+", (14, -28, -3), (15, -28, -2.6), "B", "B", 30),                          # Wasserfall daneben
    (20.50, 21.60, 266.0, 267.6, "B+", (2.6, -3.8, .8), (2.5, -4.0, .9), "B", "B", 28),                    # geschafft
    (21.60, 23.50, 267.6, 270.0, "P", (BX + 12, -6, 2.5), (BX + 13, -6.5, 2.8), (BX - 3, 0, -.5), (BX - 3, 0, -.5), 26),  # Freunde
    (23.50, 27.00, 270.0, 273.5, "P", (BX + 20, -30, 8), (260, -430, 120), (0, 20, -60), (0, 20, -80), 26),       # Rueckfahrt weit
]


def zustand(t):
    for s in SZ:
        if s[0] <= t < s[1]:
            break
    k = (t - s[0]) / (s[1] - s[0])
    ts = s[2] + (s[3] - s[2]) * k
    k = ease(k) * .7 + k * .3
    pel_w, fuss = zustand_figur(ts)
    bk = becken()
    if s[4] == "B+":
        pos = bk + lerpv(s[5], s[6], k)
    else:
        pos = lerpv(s[5], s[6], k)
    if s[7] == "B":
        ziel = bk
    elif s[7] == "F":
        ziel = fuss + Vector((0, 0, .15))
    elif s[7] == "U":
        ziel = Vector((bk.x + .3, bk.y + 2, BODEN))
    else:
        ziel = lerpv(s[7], s[8], k)
    cam.location = pos; d = ziel - pos; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = s[9]; cam.data.dof.focus_distance = min(d.length, 4.0) if s[7] == "U" else d.length
    cam.data.dof.aperture_fstop = 2.8 if d.length < 6 else 16
    zit = .006
    cam.location += Vector((zit * math.sin(t * 7.3), zit * math.cos(t * 5.1), zit * math.sin(t * 9.7)))


os.makedirs(A.ordner, exist_ok=True)
N = int(round(D * A.fps))
liste = [int(round(float(x) * A.fps)) for x in A.nur.split(",")] if A.nur else list(range(A.start, N))
for f in liste:
    pfad = os.path.join(A.ordner, f"highline_{f:04d}.png")
    if os.path.exists(pfad) and not A.nur:
        continue
    zustand(f / A.fps); bpy.context.view_layer.update(); zustand(f / A.fps)
    sc.render.filepath = pfad
    bpy.ops.render.render(write_still=True); print("FERTIG", pfad, flush=True)
