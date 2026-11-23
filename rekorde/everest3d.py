"""Geschichte: Ein Mann hat einen Job: Menschen auf das Dach der Welt bringen (Kami Rita Sherpa, 32. Besteigung am 17.5.2026).
Drei Schauplaetze: Gipfelgrat (Hoehenfeld mit Graten, Nachbargipfel, Wolkenmeer), Khumbu-Eisbruch (Seracs, Spalte, Leiter),
Basislager (gelbe Zelte, Gebetsfahnen, Moraene). Bergfuehrer (MPFB) in Daunenanzug mit Kapuze, Brille, Sauerstoffmaske,
Rucksack mit Flasche, Steigeisen; Kunde (MPFB) in Gelb; Seilschaft als kleine Figuren; Fixseil, Gebetsfahnen, Triebschnee.
python3 everest3d.py <ordner> [--nur t1,t2] [--start i] [--samples n]"""
import bpy, bmesh, math, random, sys, os, argparse
from mathutils import Vector, Matrix, noise
HIER = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HIER)
import mensch_mh as MH

ap = argparse.ArgumentParser()
ap.add_argument("ordner"); ap.add_argument("--nur", default=""); ap.add_argument("--skala", type=int, default=50)
ap.add_argument("--samples", type=int, default=10); ap.add_argument("--fps", type=int, default=15)
ap.add_argument("--start", type=int, default=0)
A = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
P = math.pi
D = 31.6
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = A.samples; sc.cycles.use_denoising = True
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.transmission_bounces = 2
sc.cycles.adaptive_threshold = .03
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1080, 1920, A.skala
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"; sc.view_settings.exposure = -1.6
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
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def zyl(name, r, h, ort, m, rot=(0, 0, 0), v=24, bevel=True):
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


def steppung(m, abstand=.09):
    n = m.node_tree.nodes; l = m.node_tree.links; b = n["Principled BSDF"]
    b.inputs["Roughness"].default_value = .55; b.inputs["Sheen Weight"].default_value = .6; b.inputs["Coat Weight"].default_value = .12
    at = n.new("ShaderNodeAttribute"); at.attribute_name = "rest_z"
    mu = n.new("ShaderNodeMath"); mu.operation = "MULTIPLY"; mu.inputs[1].default_value = 1 / abstand; l.new(at.outputs["Fac"], mu.inputs[0])
    fr = n.new("ShaderNodeMath"); fr.operation = "PINGPONG"; fr.inputs[1].default_value = .5; l.new(mu.outputs[0], fr.inputs[0])
    sm = n.new("ShaderNodeMath"); sm.operation = "SMOOTH_MIN"; sm.inputs[1].default_value = .08; sm.inputs[2].default_value = .06
    l.new(fr.outputs[0], sm.inputs[0])
    bp = n.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = .7; bp.inputs["Distance"].default_value = .012
    l.new(sm.outputs[0], bp.inputs["Height"])
    if b.inputs["Normal"].links:
        l.new(b.inputs["Normal"].links[0].from_socket, bp.inputs["Normal"])
    l.new(bp.outputs[0], b.inputs["Normal"])


# ======================================================================  Bergsteiger (MPFB) in Daunenanzug
def bergsteiger(name, seed, farbe, haut="asian", alter=.55, muskel=.5, gewicht=.45, maenn=1.0):
    m = MH.Arbeiter(name=name, seed=seed, maenn=maenn, alter=alter, muskel=muskel, gewicht=gewicht, haut=haut, weste=False)
    for o in m.huellen:
        if o.name.endswith(("_hemd", "_hose")):
            farbe_setzen(o.active_material, farbe[0], farbe[1]); steppung(o.active_material)
            o.modifiers["versatz"].strength = .05 if o.name.endswith("_hemd") else .055
            if "rund" in o.modifiers:
                o.modifiers["rund"].iterations = 12; o.modifiers["rund"].factor = .8
        elif o.name.endswith("_hand"):
            farbe_setzen(o.active_material, "1b1c1f", "111214"); o.modifiers["versatz"].strength = .022
        elif o.name.endswith("_gesicht"):
            o.hide_render = True
    for o in m.helm:
        o.hide_render = True
    for o in m.stiefel:
        if o.active_material and o.active_material.name.startswith("stiefel"):
            farbe_setzen(o.active_material, "e8b81a", "b38a0e")
    m.objekte = [o for o in m.objekte if o not in m.helm and not o.name.endswith("_gesicht")]
    rig = m.rig
    aug = (m.gm("joint-l-eye") + m.gm("joint-r-eye")) / 2; hals = m.gm("joint-neck")
    stoff = MH._stoff(name + "_kapuze", farbe[0], rau=.4, skala=600); steppung(stoff, .05)
    teile = []
    # Kapuze (Halbkugel ueber Kopf, Gesicht offen) + Fellrand
    km = aug + Vector((0, .075, .01))
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=128, v_segments=64, radius=.155)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if (v.co.y < -.06 and v.co.z > -.13) or v.co.z < -.16], context="VERTS")
    me = bpy.data.meshes.new("kapuze"); bm.to_mesh(me); bm.free()
    kap = bpy.data.objects.new(name + "_kapuze", me); sc.collection.objects.link(kap); kap.location = km; me.materials.append(stoff)
    kap.modifiers.new("d", "SOLIDIFY").thickness = .015
    for p in me.polygons:
        p.use_smooth = True
    teile.append(kap)
    bpy.ops.mesh.primitive_torus_add(major_radius=.112, minor_radius=.022, major_segments=64, minor_segments=16, location=km + Vector((0, -.112, -.02)), rotation=(P / 2 + .15, 0, 0))
    fell = bpy.context.object; fell.scale = (1, 1.2, 1); ft = bpy.data.textures.new(name + "_fellt", "CLOUDS"); ft.noise_scale = .004
    fd = fell.modifiers.new("d", "DISPLACE"); fd.texture = ft; fd.strength = .012; fell.data.materials.append(MH._stoff(name + "_fell", "4a4036", rau=.95, skala=3000)); teile.append(fell)
    # Brille (Gletscherbrille) + Band
    gl_m = mat(name + "_glas", "2a2018", .05, .6, Coat_Weight=1.0)
    teile.append(box(name + "_brille", (.16, .04, .055), aug + Vector((0, -.04, .0)), gl_m, .018, 4))
    teile.append(box(name + "_brillenrahmen", (.17, .035, .062), aug + Vector((0, -.032, .0)), mat(name + "_rahmen", "202226", .5), .02, 4))
    # Sauerstoffmaske + Regler + Schlauch-Anfang
    mund = aug + Vector((0, -.04, -.075))
    ms_m = mat(name + "_maske", "3a3d42", .45)
    teile.append(box(name + "_maske", (.085, .06, .08), mund, ms_m, .03, 4))
    teile.append(zyl(name + "_regler", .02, .035, mund + Vector((0, -.04, -.012)), mat(name + "_reglerf", "55595e", .35, .6), rot=(P / 2, 0, 0)))
    for o in teile:
        an_knochen(o, rig, "head")
    # Rucksack mit Sauerstoffflasche
    rk = Vector((0, hals.y + .24, hals.z - .3))
    rs = [box(name + "_rucksack", (.34, .2, .52), rk, MH._stoff(name + "_ruck", "2d3440", rau=.7, skala=500), .05, 3),
          zyl(name + "_flasche", .055, .5, rk + Vector((.1, .02, .28)), mat(name + "_flaschef", "e0611f", .3, Coat_Weight=.7)),
          zyl(name + "_ventil", .02, .06, rk + Vector((.1, .02, .55)), mat(name + "_ventf", "b9bdc2", .25, 1.0))]
    for o in rs:
        an_knochen(o, rig, "spine03")
    # Steigeisen: Zacken unter den Stiefeln
    stahl = mat(name + "_stahl", "aeb3b8", .3, 1.0)
    st = []
    for sd_, j in (("L", "l"), ("R", "r")):
        fu = m.gm(f"joint-{j}-foot") if f"joint-{j}-foot" in m.koerper.vertex_groups else m.gm(f"joint-{j}-ankle")
        for k in range(5):
            for s_ in (-1, 1):
                bpy.ops.mesh.primitive_cone_add(radius1=.008, depth=.035, vertices=6, location=(fu.x + s_ * .04, fu.y - .12 + k * .06, .0), rotation=(P, 0, 0))
                c = bpy.context.object; c.data.materials.append(stahl); an_knochen(c, rig, "foot." + sd_); st.append(c)
    # Eispickel in der rechten Hand
    hr = m.gm("joint-r-hand")
    pk = [zyl(name + "_pickelschaft", .014, .65, hr + Vector((0, -.02, -.25)), stahl), box(name + "_pickelkopf", (.025, .26, .03), hr + Vector((0, -.02, .08)), stahl, .006)]
    for o in pk:
        an_knochen(o, rig, "lowerarm02.R")
    m.objekte += teile + rs + st + pk
    m.maske_mund = mund
    return m


G = bergsteiger("fuehrer", 23, ("c8261d", "8e1913"), haut="asian", alter=.6, muskel=.55, gewicht=.42)
K = bergsteiger("kunde", 57, ("f2c12e", "b38a14"), haut="caucasian", alter=.4, muskel=.45, gewicht=.5)

# ======================================================================  Gipfel: Hoehenfeld (Gipfel bei z=0)
SPITZEN = [(3400, -2200, -330, .72), (-6500, 4200, -900, .55), (12000, -6000, -620, .5), (-11000, -9000, -1150, .45),
           (8000, 9500, -1350, .5), (-16000, 1500, -700, .4), (20000, 14000, -900, .35), (-4000, -14000, -1300, .45)]


def hoehe(x, y):
    r = math.hypot(x, y); th = math.atan2(y, x)
    base = -r * 1.05 if r < 1800 else -1890 - (r - 1800) * .2
    base *= 1 - .22 * math.cos(3 * (th + .9))
    h = base
    for px, py, pz, s in SPITZEN:
        d = math.hypot(x - px, y - py); h = max(h, pz - d * s * (1 - .2 * math.cos(3 * math.atan2(y - py, x - px) + px)))
    rn = noise.ridged_multi_fractal(Vector((x / 900, y / 900, 0)), .9, 2.1, 6, 1.0, 2.0)
    h += (rn - 1.0) * 230 * min(1, r / 300)
    h += noise.noise(Vector((x / 60, y / 60, 3))) * 6 * min(1, r / 60)
    return h


def feld(name, rmax=45000, NR=420, NS=520):
    bm = bmesh.new(); mitte = bm.verts.new((0, 0, hoehe(0, 0))); ringe = []
    for i in range(1, NR + 1):
        r = rmax * (i / NR) ** 3.0; ring = []
        for j in range(NS):
            a = 2 * P * j / NS; x, y = r * math.cos(a), r * math.sin(a)
            ring.append(bm.verts.new((x, y, hoehe(x, y))))
        ringe.append(ring)
    for j in range(NS):
        bm.faces.new((mitte, ringe[0][j], ringe[0][(j + 1) % NS]))
    for i in range(NR - 1):
        a, b_ = ringe[i], ringe[i + 1]
        for j in range(NS):
            bm.faces.new((a[j], b_[j], b_[(j + 1) % NS], a[(j + 1) % NS]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o)
    for p in me.polygons:
        p.use_smooth = True
    return o


def schnee_fels(name, schnee="f4f7fb", fels="3b3632", steil=.72):
    m = bpy.data.materials.new(name); m.use_nodes = True; n = m.node_tree.nodes; l = m.node_tree.links; b = n["Principled BSDF"]
    geo = n.new("ShaderNodeNewGeometry"); sx = n.new("ShaderNodeSeparateXYZ"); l.new(geo.outputs["Normal"], sx.inputs[0])
    tc = n.new("ShaderNodeTexCoord")
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = .02; nz.inputs["Detail"].default_value = 10; l.new(tc.outputs["Object"], nz.inputs["Vector"])
    ad = n.new("ShaderNodeMath"); ad.operation = "MULTIPLY_ADD"; ad.inputs[1].default_value = .25; l.new(nz.outputs["Fac"], ad.inputs[0]); l.new(sx.outputs[2], ad.inputs[2])
    mr = n.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = steil; mr.inputs["From Max"].default_value = steil + .1
    l.new(ad.outputs[0], mr.inputs["Value"])
    fn = n.new("ShaderNodeTexNoise"); fn.inputs["Scale"].default_value = .8; fn.inputs["Detail"].default_value = 8; l.new(tc.outputs["Object"], fn.inputs["Vector"])
    fr = n.new("ShaderNodeValToRGB"); fr.color_ramp.elements[0].color = (*hexf(fels), 1); fr.color_ramp.elements[1].color = (*[c * 1.6 for c in hexf(fels)], 1)
    l.new(fn.outputs["Fac"], fr.inputs["Fac"])
    mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; l.new(mr.outputs[0], mx.inputs[0]); l.new(fr.outputs[0], mx.inputs[6])
    mx.inputs[7].default_value = (*hexf(schnee), 1); l.new(mx.outputs[2], b.inputs["Base Color"])
    rr = n.new("ShaderNodeMapRange"); rr.inputs["To Min"].default_value = .85; rr.inputs["To Max"].default_value = .45; l.new(mr.outputs[0], rr.inputs["Value"])
    l.new(rr.outputs[0], b.inputs["Roughness"])
    b.inputs["Sheen Weight"].default_value = .4
    # feine Windgangeln + Glitzern
    wv = n.new("ShaderNodeTexWave"); wv.inputs["Scale"].default_value = .9; wv.inputs["Distortion"].default_value = 6; l.new(tc.outputs["Object"], wv.inputs["Vector"])
    gl = n.new("ShaderNodeTexNoise"); gl.inputs["Scale"].default_value = 40; gl.inputs["Detail"].default_value = 3; l.new(tc.outputs["Object"], gl.inputs["Vector"])
    hb = n.new("ShaderNodeMath"); hb.operation = "MULTIPLY_ADD"; hb.inputs[1].default_value = .3; l.new(gl.outputs["Fac"], hb.inputs[0]); l.new(wv.outputs["Fac"], hb.inputs[2])
    bp = n.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = .35; bp.inputs["Distance"].default_value = .05; l.new(hb.outputs[0], bp.inputs["Height"])
    l.new(bp.outputs[0], b.inputs["Normal"])
    return m


gipfel = feld("gipfel"); gipfel.data.materials.append(schnee_fels("gipfelschnee", steil=.8))
# Wolkenmeer
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -3000)); wolken = bpy.context.object; wolken.scale = (160000, 160000, 1)
wm = bpy.data.materials.new("wolkenmeer"); wm.use_nodes = True; n = wm.node_tree.nodes; l = wm.node_tree.links; b = n["Principled BSDF"]
tc = n.new("ShaderNodeTexCoord"); nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1 / 2500; nz.inputs["Detail"].default_value = 12
nz.inputs["Roughness"].default_value = .62; l.new(tc.outputs["Object"], nz.inputs["Vector"])
cr = n.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].position = .35; cr.color_ramp.elements[0].color = (.72, .78, .86, 1)
cr.color_ramp.elements[1].position = .7; cr.color_ramp.elements[1].color = (1, 1, 1, 1); l.new(nz.outputs["Fac"], cr.inputs["Fac"])
l.new(cr.outputs[0], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 1
bp = n.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = .8; bp.inputs["Distance"].default_value = 300; l.new(nz.outputs["Fac"], bp.inputs["Height"]); l.new(bp.outputs[0], b.inputs["Normal"])
wolken.data.materials.append(wm)
GIPFEL_OBJ = [gipfel, wolken]

# Gebetsfahnen am Gipfel (Leinen mit bunten Fahnen, Wellen-Modifikator)
FAHNEN_F = ["2b5fd0", "f4f4f0", "d22a2a", "2f9e47", "f1c21b"]
FAHNEN = []


def fahnenleine(a, b_, n_=26, name="fahnen"):
    a, b_ = Vector(a), Vector(b_)
    bpy.ops.mesh.primitive_cylinder_add(radius=.006, depth=1, vertices=6); o = bpy.context.object; linie(o, a, b_)
    o.data.materials.append(mat("leine", "d8d0bf", .8)); FAHNEN.append(o)
    for i in range(n_):
        k = (i + .5) / n_; p = a.lerp(b_, k) - Vector((0, 0, math.sin(k * P) * .35))
        bpy.ops.mesh.primitive_plane_add(size=1, location=p - Vector((0, 0, .14))); f = bpy.context.object
        f.scale = (.2, .26, 1); f.rotation_euler = (P / 2, 0, math.atan2(b_.y - a.y, b_.x - a.x))
        f.data.materials.append(mat("fahne%d" % (i % 5), FAHNEN_F[i % 5], .8, Sheen_Weight=.5))
        sb = f.modifiers.new("s", "SUBSURF"); sb.subdivision_type = "SIMPLE"; sb.levels = sb.render_levels = 3
        wv = f.modifiers.new("w", "WAVE"); wv.height = .03; wv.width = .15; wv.speed = .3; wv.use_normal = True; wv.time_offset = -i * 3
        FAHNEN.append(f)


G0 = Vector((0, 0, hoehe(0, 0)))
for (a, b_) in (((-1.5, -1.2, .4), (2.5, 2.0, .3)), ((-2.0, 1.4, .5), (1.8, -2.2, .2)), ((0, -.5, .9), (-3.5, -5, -2.0))):
    fahnenleine(G0 + Vector(a), G0 + Vector(b_))
# Fixseil den Grat hinunter (Suedostgrat ca. Richtung -60 Grad)
GRAT = -1.05
seilm = mat("fixseil", "e03a2a", .6)
FIX = []
pts = []
for i in range(60):
    r = i * 3.0; x, y = r * math.cos(GRAT), r * math.sin(GRAT); pts.append(Vector((x, y, hoehe(x, y) + .15)))
for a, b_ in zip(pts, pts[1:]):
    bpy.ops.mesh.primitive_cylinder_add(radius=.006, depth=1, vertices=6); o = bpy.context.object; linie(o, a, b_); o.data.materials.append(seilm); FIX.append(o)


def grat_punkt(r, quer=0.0):
    x, y = r * math.cos(GRAT) - quer * math.sin(GRAT), r * math.sin(GRAT) + quer * math.cos(GRAT)
    return Vector((x, y, hoehe(x, y)))


# Seilschaft als kleine Figuren (fuer Weitwinkel)
MINI = []
mini_f = ["2f62c9", "f2c12e", "2a9d5b", "e06a1f", "8f2fb0", "c8261d"]
for i in range(9):
    p = grat_punkt(14 + i * 6.5, .3 * math.sin(i))
    fm = mat("mini%d" % i, mini_f[i % 6], .45, Sheen_Weight=.4)
    kor = box("mini", (.42, .3, 1.05), p + Vector((0, 0, .75)), fm, .14, 3)
    kopf = zyl("mini_kopf", .13, .24, p + Vector((0, 0, 1.45)), fm)
    ruck = box("mini_ruck", (.32, .2, .45), p + Vector((.15, .1, 1.0)), mat("miniruck%d" % i, "2d3440", .7), .05)
    for o in (kor, kopf, ruck):
        o.rotation_euler = (0, .08, GRAT + P); MINI.append(o)
GIPFEL_OBJ += FAHNEN + FIX + MINI

# ======================================================================  Eisbruch (X = 100 km, eigener Boden)
EB = Vector((100000, 0, 0))
eis_m = bpy.data.materials.new("eis"); eis_m.use_nodes = True; n = eis_m.node_tree.nodes; l = eis_m.node_tree.links; b = n["Principled BSDF"]
b.inputs["Base Color"].default_value = (*hexf("cfe6f5"), 1); b.inputs["Roughness"].default_value = .25; b.inputs["Coat Weight"].default_value = .5
b.inputs["Subsurface Weight"].default_value = 0.0
tc = n.new("ShaderNodeTexCoord"); nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = .6; nz.inputs["Detail"].default_value = 8
l.new(tc.outputs["Object"], nz.inputs["Vector"])
cr = n.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (*hexf("b9dcf0"), 1); cr.color_ramp.elements[1].color = (*hexf("fbfdff"), 1)
cr.color_ramp.elements[0].position = .35; l.new(nz.outputs["Fac"], cr.inputs["Fac"]); l.new(cr.outputs[0], b.inputs["Base Color"])
bp = n.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = .5; l.new(nz.outputs["Fac"], bp.inputs["Height"]); l.new(bp.outputs[0], b.inputs["Normal"])
EIS_OBJ = []


def eisblock(ort, groesse, rz=0.0, seed=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=ort, rotation=(0, 0, rz)); o = bpy.context.object; o.scale = groesse
    bpy.ops.object.transform_apply(scale=True)
    bv = o.modifiers.new("b", "BEVEL"); bv.width = min(groesse) * .25; bv.segments = 3
    sb = o.modifiers.new("s", "SUBSURF"); sb.levels = sb.render_levels = 3
    tx = bpy.data.textures.new("serac%d" % seed, "CLOUDS"); tx.noise_scale = 1.6; tx.noise_depth = 4; dp = o.modifiers.new("d", "DISPLACE"); dp.texture = tx; dp.strength = 1.4
    o.data.materials.append(eis_m); EIS_OBJ.append(o)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


# zwei Eisplatten mit Spalte (Spalte entlang x, 3 m breit), darunter Tiefe
for s_ in (-1, 1):
    eisblock(EB + Vector((0, s_ * 9.5, -4)), (40, 16, 8), seed=s_ + 5)
rr = random.Random(4)
for i in range(26):
    s_ = rr.choice((-1, 1))
    eisblock(EB + Vector((rr.uniform(-25, 25), s_ * rr.uniform(6, 30), rr.uniform(2, 6))), (rr.uniform(3, 8), rr.uniform(3, 7), rr.uniform(5, 14)), rr.uniform(0, 3), seed=i + 20)

# Leiter ueber die Spalte (y-Richtung) mit Handseilen
alu = mat("alu", "c9cdd2", .3, 1.0)
LEITER = []
for x_ in (-.22, .22):
    LEITER.append(box("holm", (.04, 4.4, .06), EB + Vector((x_, 0, .05)), alu, .005))
for k in range(15):
    LEITER.append(zyl("sprosse", .012, .44, EB + Vector((0, -2.1 + k * .3, .06)), alu, rot=(0, P / 2, 0), v=10))
for x_ in (-.55, .55):
    bpy.ops.mesh.primitive_cylinder_add(radius=.006, depth=1, vertices=6); o = bpy.context.object
    linie(o, EB + Vector((x_, -3.2, .95)), EB + Vector((x_, 3.2, .95))); o.data.materials.append(seilm); LEITER.append(o)
    for y_ in (-3.2, 3.2):
        LEITER.append(zyl("anker", .02, .5, EB + Vector((x_, y_, .2)), alu))
# Talwaende als Hintergrund
for s_ in (-1, 1):
    bpy.ops.mesh.primitive_plane_add(size=1, location=EB + Vector((s_ * 900, 400, 400)), rotation=(0, s_ * 1.2, 0)); o = bpy.context.object
    o.scale = (2000, 4000, 1); sb = o.modifiers.new("s", "SUBSURF"); sb.subdivision_type = "SIMPLE"; sb.levels = sb.render_levels = 7
    tx = bpy.data.textures.new("wand%d" % s_, "CLOUDS"); tx.noise_scale = 1.2; tx.noise_depth = 4; dp = o.modifiers.new("d", "DISPLACE"); dp.texture = tx; dp.strength = 260
    o.data.materials.append(schnee_fels("wandschnee%d" % s_, steil=.55)); EIS_OBJ.append(o)
EIS_OBJ += LEITER
EIS_OBJ.append(box("spaltengrund", (60, 4, 1), EB + Vector((0, 0, -25)), mat("tiefe", "0a1a2a", .9), 0))

# ======================================================================  Basislager (X = 200 km)
BC = Vector((200000, 0, 0))
mor_m = MH._stoff("moraene", "6b665f", rau=.95, skala=2)
bpy.ops.mesh.primitive_plane_add(size=1, location=BC); boden = bpy.context.object; boden.scale = (14000, 14000, 1)
sb = boden.modifiers.new("s", "SUBSURF"); sb.subdivision_type = "SIMPLE"; sb.levels = sb.render_levels = 8
tx = bpy.data.textures.new("moraene", "CLOUDS"); tx.noise_scale = .012; tx.noise_depth = 4; dp = boden.modifiers.new("d", "DISPLACE"); dp.texture = tx; dp.strength = 1.5
boden.data.materials.append(mor_m)
BC_OBJ = [boden]
zelt_m = MH._stoff("zelt", "f2b417", rau=.6, skala=300); zelt2 = MH._stoff("zelt2", "e0562a", rau=.6, skala=300)
rr = random.Random(9)
for i in range(34):
    p = BC + Vector((rr.uniform(-60, 60), rr.uniform(10, 120), 0))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=p + Vector((0, 0, 7.5)), segments=24, ring_count=12); o = bpy.context.object
    o.scale = (rr.uniform(1.4, 2.2), rr.uniform(1.2, 1.8), 1.1); o.data.materials.append(zelt_m if i % 4 else zelt2)
    o.location.z = BC.z + 1.0; BC_OBJ.append(o)
# Basis-Steine + Gebetsfahnen-Mast
for i in range(140):
    p = BC + Vector((rr.uniform(-80, 80), rr.uniform(-10, 160), .3))
    bpy.ops.mesh.primitive_ico_sphere_add(radius=rr.uniform(.2, .9), subdivisions=1, location=p); o = bpy.context.object
    o.scale = (1, rr.uniform(.6, 1.3), rr.uniform(.4, .8)); o.data.materials.append(mor_m); BC_OBJ.append(o)
n0 = len(FAHNEN)
mast = BC + Vector((0, 35, .3))
BC_OBJ.append(zyl("mast", .06, 5, mast + Vector((0, 0, 2.5)), mat("holz", "6f4e2e", .8)))
for a_ in range(6):
    fahnenleine(mast + Vector((0, 0, 4.9)), mast + Vector((22 * math.cos(a_), 22 * math.sin(a_), -.3)), 34)
BC_OBJ += FAHNEN[n0:]
# Hintergrundberge des Basislagers (weiche, steile Bergkoerper hinter dem Lager)
for i, (dx, dy, hh, rr_) in enumerate(((-1800, 3200, 2600, 1500), (600, 3800, 3300, 1700), (2900, 2600, 2300, 1300), (-4200, 2000, 1900, 1500), (4800, 4200, 2800, 1600))):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=96, ring_count=48, location=BC + Vector((dx, dy, 0))); o = bpy.context.object
    o.scale = (rr_, rr_ * .8, hh)
    tx = bpy.data.textures.new("bcb%d" % i, "CLOUDS"); tx.noise_scale = .35; tx.noise_depth = 3
    dp = o.modifiers.new("d", "DISPLACE"); dp.texture = tx; dp.strength = 150; dp.texture_coords = "GLOBAL"
    o.data.materials.append(schnee_fels("bcberg%d" % i, steil=.62)); BC_OBJ.append(o)
    for p in o.data.polygons:
        p.use_smooth = True
# ======================================================================  Himmel, Sonne, Triebschnee
w = bpy.data.worlds.new("welt"); sc.world = w; w.use_nodes = True; nt = w.node_tree
sky = nt.nodes.new("ShaderNodeTexSky"); sky.sun_disc = True; sky.sun_size = math.radians(.6); sky.aerosol_density = .4
nt.links.new(sky.outputs[0], nt.nodes["Background"].inputs[0]); nt.nodes["Background"].inputs[1].default_value = .9
bpy.ops.object.light_add(type="SUN"); sonne = bpy.context.object; sonne.data.angle = math.radians(.6)


def sonne_setzen(el, rot, en=4.6):
    sky.sun_elevation = math.radians(el); sky.sun_rotation = math.radians(rot)
    sonne.rotation_euler = (math.radians(90 - el), 0, math.radians(rot - 90)); sonne.data.energy = en
    sonne.data.color = (1, .9 + .1 * ease(el / 25), .82 + .18 * ease(el / 30))


TRIEB = []
tm = mat("triebschnee", "ffffff", .5, Emission_Color=(1, 1, 1, 1), Emission_Strength=.4)
bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=6, v_segments=4, radius=.006); me = bpy.data.meshes.new("flocke"); bm.to_mesh(me); bm.free()
me.materials.append(tm)
rr = random.Random(17)
for i in range(240):
    o = bpy.data.objects.new("flocke", me); sc.collection.objects.link(o)
    o["p"] = (rr.uniform(-6, 6), rr.uniform(-6, 6), rr.uniform(0, 1), rr.uniform(.6, 1.4)); o.scale = (rr.uniform(3, 7), 1, 1); TRIEB.append(o)

# ======================================================================  Posen + Kamera
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam
cam.data.clip_start = .03; cam.data.clip_end = 300000; cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
cam.data.dof.use_dof = True


def gehen(m, t, tempo=1.0, stark=1.0):
    ph = t * 3.2 * tempo; s = math.sin(ph) * stark
    m.dreh("upperleg01.L", x=-.35 * s - .1); m.dreh("upperleg01.R", x=.35 * s - .1)
    m.dreh("lowerleg01.L", x=.45 * max(0, s) + .15); m.dreh("lowerleg01.R", x=.45 * max(0, -s) + .15)
    m.dreh("upperarm01.L", z=-.55, x=.2 + .25 * s); m.dreh("upperarm01.R", z=.55, x=.6 - .25 * s); m.dreh("lowerarm01.R", x=-.9)
    m.dreh("spine03", x=.18); m.dreh("neck01", x=-.15)


def stellen(m, ort, blick):
    m.rig.location = ort; m.rig.rotation_euler = (0, 0, blick)


def zustand_figuren(t, ort):
    G.zuruecksetzen(); K.zuruecksetzen()
    if ort == "gipfel":
        if 25.08 <= t < 27.62:          # Ankunft am Gipfel, Arme hoch
            k = ease((t - 25.6) / .8)
            stellen(G, G0 + Vector((.3, -.2, -.05)), GRAT + P / 2 + .3)
            G.dreh("upperarm01.L", z=-.55 + 2.0 * k, x=.3); G.dreh("upperarm01.R", z=.55 - 2.0 * k, x=.3)
            G.dreh("lowerarm01.L", x=-.3); G.dreh("lowerarm01.R", x=-.3)
        elif 7.26 <= t < 10.68 or t >= 27.62 or t < 1.88:
            stellen(G, G0 + Vector((.3, -.2, -.05)), GRAT + P / 2 + .3)
            G.dreh("upperarm01.L", z=-.6); G.dreh("upperarm01.R", z=.55, x=.4); G.dreh("lowerarm01.R", x=-.7)
            G.dreh("neck01", z=.25 * math.sin(t * .5))
        else:
            r_g = max(3.5, 22 - (t - 1.88) * .6) if t < 21.0 else max(2.5, 10 - (t - 21.0) * 2.2)
            p = grat_punkt(r_g, .15); stellen(G, p, GRAT + P / 2); gehen(G, t, .6)
        p2 = grat_punkt(max(G.rig.location.length, 3.5) + 7.0, -.1)
        stellen(K, p2, GRAT + P / 2); gehen(K, t + .7, .6)
    elif ort == "eis":
        k = (t - 14.88) / 2.62
        stellen(G, EB + Vector((0, -2.6 + 4.8 * k, .07)), P); gehen(G, t, .9, .8)
        G.dreh("upperarm01.L", z=.1, x=.3); G.dreh("upperarm01.R", z=-.1, x=.3)
        stellen(K, EB + Vector((0, -6.5, 0)), P); K.dreh("upperarm01.L", z=-.6); K.dreh("upperarm01.R", z=.6)
    elif ort == "lager":
        stellen(G, BC + Vector((2, 24, .4)), .4); gehen(G, t, .7)
        stellen(K, BC + Vector((-1.5, 21, .4)), .6); gehen(K, t + .5, .7)
    bpy.context.view_layer.update()


def punkt(m, bone, v):
    pb = m.rig.pose.bones[bone]; bn = m.rig.data.bones[bone]
    return m.rig.matrix_world @ pb.matrix @ bn.matrix_local.inverted() @ Vector(v)


GK = G.gm("joint-head")
# Einstellungen: (von, bis, ort, typ, a, b, linse)
#  typ "kopf": Kamera relativ zum Kopf des Fuehrers; "frei": absolute Positionen (pos0, ziel0, pos1, ziel1)
SZ = [
    (0.00, 1.88, "gipfel", "kopf", (.95, -1.75, .05), (.8, -1.5, .05), 50),
    (1.88, 4.28, "gipfel", "frei", (G0 + Vector((-140, -250, 15)), G0 + Vector((10, -20, -25)), G0 + Vector((-110, -265, 12)), G0 + Vector((10, -20, -22))), 24),
    (4.28, 7.26, "gipfel", "kopf", (1.6, -2.4, -.3), (1.2, -2.0, -.2), 30),
    (7.26, 10.68, "gipfel", "frei", (G0 + Vector((5.5, 3.5, 1.2)), G0 + Vector((0, 0, .9)), G0 + Vector((4.6, 4.2, 1.6)), G0 + Vector((0, 0, 1.0))), 26),
    (10.68, 11.48, "gipfel", "frei", (G0 + Vector((-35, -70, 14)), G0 + Vector((22, -38, -26)), G0 + Vector((-33, -68, 13)), G0 + Vector((22, -38, -26))), 30),
    (11.48, 12.50, "gipfel", "kopf", (-1.4, -1.8, .4), (-1.2, -1.6, .35), 32),
    (12.50, 13.56, "eis", "frei", (EB + Vector((13, -1.2, 4.5)), EB + Vector((0, 0, -2.5)), EB + Vector((12, -1.0, 4.2)), EB + Vector((0, 0, -2.5))), 24),
    (13.56, 14.88, "gipfel", "frei", (G0 + Vector((-8, 6, 2.5)), G0 + Vector((0, 0, .8)), G0 + Vector((-7, 7, 3)), G0 + Vector((0, 0, .8))), 28),
    (14.88, 17.50, "eis", "frei", (EB + Vector((5.5, -1.5, .2)), EB + Vector((0, -.3, .5)), EB + Vector((5.0, .5, .1)), EB + Vector((0, .8, .5))), 24),
    (17.50, 19.10, "gipfel", "fuss", (1.4, -2.4, .8), (1.25, -2.2, .75), 38),
    (19.10, 21.00, "gipfel", "kopf", (1.0, -1.7, .2), (.85, -1.5, .15), 45),
    (21.00, 25.08, "gipfel", "frei", (G0 + Vector((7, -14, 2.5)), "G", G0 + Vector((5.5, -11, 2.2)), "G"), 30),
    (25.08, 27.62, "gipfel", "frei", (G0 + Vector((2.6, -3.8, .6)), G0 + Vector((.3, -.2, 1.2)), G0 + Vector((2.2, -3.3, .5)), G0 + Vector((.3, -.2, 1.3))), 26),
    (27.62, 30.04, "gipfel", "frei", (G0 + Vector((150, -230, 55)), G0 + Vector((0, 0, -10)), G0 + Vector((200, -170, 50)), G0 + Vector((0, 0, -10))), 30),
    (30.04, 31.70, "gipfel", "kopf", (1.1, -2.0, .08), (.95, -1.75, .05), 50),
]


def zustand(t):
    for s in SZ:
        if s[0] <= t < s[1]:
            break
    k = (t - s[0]) / (s[1] - s[0]); k = ease(k) * .8 + k * .2
    ort = s[2]
    for o in GIPFEL_OBJ:
        o.hide_render = ort != "gipfel"
    for o in EIS_OBJ:
        o.hide_render = ort != "eis"
    for o in BC_OBJ:
        o.hide_render = ort != "lager"
    if ort == "gipfel":
        sky.altitude = 8800; sonne_setzen(24 if t < 21 else 30, 135, 3.0); sc.view_settings.exposure = -4.3
    elif ort == "eis":
        sky.altitude = 5500; sonne_setzen(30, 150, 3.0); sc.view_settings.exposure = -2.3
    else:
        sky.altitude = 5300; sonne_setzen(18, 120, 3.0); sc.view_settings.exposure = -3.7
    zustand_figuren(t, ort)
    kopf = punkt(G, "head", GK + Vector((0, -.05, .02)))
    if s[3] == "kopf":
        ziel = kopf
        dreh = Matrix.Rotation(G.rig.rotation_euler.z, 3, "Z"); pos = kopf + dreh @ lerpv(s[4], s[5], k)
    elif s[3] == "fuss":
        fuss = G.rig.location + Vector((0, 0, .1)); dreh = Matrix.Rotation(G.rig.rotation_euler.z, 3, "Z")
        pos = fuss + dreh @ lerpv(s[4], s[5], k); ziel = fuss + Vector((0, 0, .1))
    else:
        p0, z0, p1, z1 = s[4]
        pos = lerpv(p0, p1, k)
        ziel = (kopf - Vector((0, 0, .6))) if z0 == "G" else lerpv(z0, z1, k)
    cam.location = pos; d = ziel - pos; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = s[-1]; cam.data.dof.focus_distance = d.length; cam.data.dof.aperture_fstop = 4 if d.length < 3 else 14
    cam.location += Vector((.004 * math.sin(t * 7), .003 * math.cos(t * 5), .004 * math.sin(t * 9))) * min(d.length, 8)
    # Triebschnee um die Kamera (Wind von rechts)
    an = ort == "gipfel" and s[3] in ("kopf", "fuss")
    for o in TRIEB:
        o.hide_render = not an
        if an:
            x, y, f, v = o["p"]; xx = ((f + t * 1.6 * v) % 1) * 12 - 6
            o.location = cam.location + cam.matrix_world.to_3x3() @ Vector((xx, y * .4, -1.5 - abs(x) * .6))
            o.rotation_euler = cam.rotation_euler


os.makedirs(A.ordner, exist_ok=True)
N = int(round(D * A.fps))
liste = [int(round(float(x) * A.fps)) for x in A.nur.split(",")] if A.nur else list(range(A.start, N))
for f in liste:
    pfad = os.path.join(A.ordner, f"everest_{f:04d}.png")
    if os.path.exists(pfad) and not A.nur:
        continue
    zustand(f / A.fps); bpy.context.view_layer.update(); zustand(f / A.fps)
    sc.render.filepath = pfad
    bpy.ops.render.render(write_still=True); print("FERTIG", pfad, flush=True)
