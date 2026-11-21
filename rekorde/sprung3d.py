"""Geschichte: Ein Mann hat einen Job: vom Rand des Weltalls springen (Alan Eustace, 24.10.2014, 41'422 m, GWR).
Eigene Szene: Nishita-Himmel mit animierter Hoehe, Erdkappe (gekruemmt, km-Texturen + Wolkenschale), Stratosphaerenballon
(Startform Tropfen + Folienschlauch, oben Kuerbisform), realistischer Mensch (MPFB) im weissen Druckanzug mit Helm,
Brustmodul, Fallschirmpack, Stabilisierungsschirm, Hauptschirm, Wueste mit Bueschen.
python3 sprung3d.py <ordner> [--nur t1,t2] [--start i] [--samples n]"""
import bpy, bmesh, math, random, sys, os, argparse
from mathutils import Vector, Matrix, Euler
HIER = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HIER)
import mensch_mh as MH

ap = argparse.ArgumentParser()
ap.add_argument("ordner"); ap.add_argument("--nur", default=""); ap.add_argument("--skala", type=int, default=50)
ap.add_argument("--samples", type=int, default=14); ap.add_argument("--fps", type=int, default=15)
ap.add_argument("--start", type=int, default=0)
A = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
P = math.pi
D = 30.5
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = A.samples; sc.cycles.use_denoising = True
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 1; sc.cycles.glossy_bounces = 2; sc.cycles.transmission_bounces = 4
sc.cycles.transparent_max_bounces = 8; sc.cycles.adaptive_threshold = .03
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1080, 1920, A.skala
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"; sc.view_settings.exposure = -1.5
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


def rund_box(name, groesse, ort, m, bevel=.01, seg=3):
    bpy.ops.mesh.primitive_cube_add(size=1, location=ort); o = bpy.context.object; o.name = name; o.scale = groesse
    bpy.ops.object.transform_apply(scale=True)
    bv = o.modifiers.new("b", "BEVEL"); bv.width = bevel; bv.segments = seg
    o.data.materials.append(m)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def zyl(name, r, h, ort, m, rot=(0, 0, 0), v=32):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, vertices=v, location=ort, rotation=rot); o = bpy.context.object; o.name = name
    o.data.materials.append(m)
    bv = o.modifiers.new("b", "BEVEL"); bv.width = min(r, h) * .15; bv.segments = 2
    for p in o.data.polygons:
        p.use_smooth = True
    return o


# ======================================================================  Mensch im Druckanzug
M = MH.Arbeiter(name="springer", seed=7, maenn=1.0, alter=.62, muskel=.5, gewicht=.5, haut="caucasian", weste=False)
rig = M.rig; EV = M.EV


def anzug_stoff(m, farbe="eceae4"):
    n = m.node_tree.nodes; l = m.node_tree.links
    for nd in n:
        if nd.type == "MIX" and nd.data_type == "RGBA":
            nd.inputs[6].default_value = (*hexf(farbe), 1); nd.inputs[7].default_value = (*[c * .82 for c in hexf(farbe)], 1)
    b = n["Principled BSDF"]; b.inputs["Roughness"].default_value = .62; b.inputs["Sheen Weight"].default_value = .6
    # Steppnaehte (Ringe um die Glieder) als Bump ueber rest_z
    at = n.new("ShaderNodeAttribute"); at.attribute_name = "rest_z"
    mu = n.new("ShaderNodeMath"); mu.operation = "MULTIPLY"; mu.inputs[1].default_value = 1 / .085; l.new(at.outputs["Fac"], mu.inputs[0])
    fr = n.new("ShaderNodeMath"); fr.operation = "PINGPONG"; fr.inputs[1].default_value = .5; l.new(mu.outputs[0], fr.inputs[0])
    sm = n.new("ShaderNodeMath"); sm.operation = "SMOOTH_MIN"; sm.inputs[1].default_value = .06; sm.inputs[2].default_value = .05
    l.new(fr.outputs[0], sm.inputs[0])
    bp = n.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = .35; bp.inputs["Distance"].default_value = .004
    l.new(sm.outputs[0], bp.inputs["Height"])
    alt = b.inputs["Normal"].links[0].from_socket if b.inputs["Normal"].links else None
    if alt:
        l.new(alt, bp.inputs["Normal"])
    l.new(bp.outputs[0], b.inputs["Normal"])


for o in M.huellen:
    if o.name.endswith(("_hemd", "_hose")):
        anzug_stoff(o.active_material)
        d = o.modifiers["versatz"]; d.strength = .034 if o.name.endswith("_hemd") else .04
        if "rund" in o.modifiers:
            o.modifiers["rund"].iterations = 10; o.modifiers["rund"].factor = .7
    elif o.name.endswith("_hand"):
        b = o.active_material.node_tree.nodes["Principled BSDF"]
        for nd in o.active_material.node_tree.nodes:
            if nd.type == "MIX" and nd.data_type == "RGBA":
                nd.inputs[6].default_value = (*hexf("dcdad2"), 1); nd.inputs[7].default_value = (*hexf("a9a79f"), 1)
        o.modifiers["versatz"].strength = .009; b.inputs["Roughness"].default_value = .55
for o in M.stiefel:
    if o.active_material and o.active_material.name.startswith("stiefel"):
        bb = o.active_material.node_tree.nodes["Principled BSDF"]
        for nd in o.active_material.node_tree.nodes:
            if nd.type == "MIX" and nd.data_type == "RGBA":
                nd.inputs[6].default_value = (*hexf("e6e4dc"), 1); nd.inputs[7].default_value = (*hexf("bdbab0"), 1)
for o in M.helm:
    o.hide_render = True; o.hide_viewport = True
M.objekte = [o for o in M.objekte if o not in M.helm]

# Massstab des Kopfes
kopf = M.gm("joint-head"); hals = M.gm("joint-neck"); becken = M.gm("joint-pelvis")
schl = (M.gm("joint-l-clavicle") + M.gm("joint-r-clavicle")) / 2 if "joint-l-clavicle" in M.koerper.vertex_groups else hals - Vector((0, 0, .05))
ANZ = []
weiss = mat("anzug_hart", "efeee8", .4, Coat_Weight=0) if False else mat("anzug_hart", "efeee8", .4)
grau = mat("grau", "6b6e72", .45, .6)
alu = mat("alu", "c9ccd0", .25, 1.0)
blau = mat("ring_blau", "2f5d9e", .3, .8)
schwarz = mat("schwarz", "17181a", .6)
gurt = MH._stoff("gurt", "3a3d42", rau=.8, skala=900)
rot = mat("rot", "b3261e", .45)
# Helm: Kugelschale + Visier + Halsring (Ring am Hals, Helm am Kopfknochen)
auge = (M.gm("joint-l-eye") + M.gm("joint-r-eye")) / 2
hm = Vector((0, auge.y + .06, auge.z - .012))
print("KOPF", kopf, "AUGE", auge, "HALS", hals)
bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=160, v_segments=80, radius=.19)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -.15 or (v.co.y < -.05 and math.hypot(v.co.x, (v.co.z - .005) * 1.05) < .148)], context="VERTS")
me = bpy.data.meshes.new("helm"); bm.to_mesh(me); bm.free()
helm = bpy.data.objects.new("springer_druckhelm", me); sc.collection.objects.link(helm); helm.location = hm
me.materials.append(weiss)
helm.modifiers.new("d", "SOLIDIFY").thickness = .008
for p in me.polygons:
    p.use_smooth = True
# Visier: Teil einer etwas groesseren Kugel vorne (-y)
bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=32, radius=.193)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not (v.co.y < -.05 and -.1 < v.co.z < .11 and abs(v.co.x) < .15)], context="VERTS")
me = bpy.data.meshes.new("visier"); bm.to_mesh(me); bm.free()
vis = bpy.data.objects.new("springer_visier", me); sc.collection.objects.link(vis); vis.location = hm
vm = bpy.data.materials.new("visier"); vm.use_nodes = True; vb = vm.node_tree.nodes["Principled BSDF"]
vb.inputs["Base Color"].default_value = (*hexf("f6ecd6"), 1); vb.inputs["Transmission Weight"].default_value = 1.0
vb.inputs["Roughness"].default_value = .0; vb.inputs["IOR"].default_value = 1.45; vb.inputs["Metallic"].default_value = .0
vn = vm.node_tree.nodes; vl = vm.node_tree.links
tr_ = vn.new("ShaderNodeBsdfTransparent"); tr_.inputs[0].default_value = (*hexf("f2e2bf"), 1)
gg = vn.new("ShaderNodeBsdfGlossy"); gg.inputs["Roughness"].default_value = .02
fz_ = vn.new("ShaderNodeFresnel"); fz_.inputs["IOR"].default_value = 1.6
mx_ = vn.new("ShaderNodeMixShader"); vl.new(fz_.outputs[0], mx_.inputs[0]); vl.new(tr_.outputs[0], mx_.inputs[1]); vl.new(gg.outputs[0], mx_.inputs[2])
vl.new(mx_.outputs[0], vn["Material Output"].inputs["Surface"])
me.materials.append(vm)
for p in me.polygons:
    p.use_smooth = True
VIS_B = vb
# Visierrahmen + Scharniere
rahmen = bpy.data.objects.new("springer_visrahmen", bpy.data.meshes.new("vr")); sc.collection.objects.link(rahmen)
bpy.ops.mesh.primitive_torus_add(major_radius=.155, minor_radius=.01, major_segments=64, location=hm + Vector((0, -.118, .005)), rotation=(P / 2, 0, 0))
rahmen = bpy.context.object; rahmen.name = "springer_rahmen"; rahmen.scale = (1, .95, 1); rahmen.data.materials.append(grau)
for s_ in (-1, 1):
    zyl("springer_scharnier", .03, .02, hm + Vector((s_ * .188, -.01, .0)), alu, rot=(0, P / 2, 0))
# Funkhaube (Snoopy-Kappe) unter dem Helm
km_ = Vector((0, auge.y + .085, auge.z + .02))
bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=32, radius=.108)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if (v.co.y < -.035 and -.085 < v.co.z < .035) or v.co.z < -.09], context="VERTS")
me = bpy.data.meshes.new("haube"); bm.to_mesh(me); bm.free()
haube = bpy.data.objects.new("springer_haube", me); sc.collection.objects.link(haube); haube.location = km_; haube.scale = (.95, 1.08, 1.05)
me.materials.append(MH._stoff("haube", "2b2620", rau=.8, skala=900))
haube.modifiers.new("d", "SOLIDIFY").thickness = .006
for p in me.polygons:
    p.use_smooth = True
for s_ in (-1, 1):
    o = zyl("springer_ohr", .038, .03, km_ + Vector((s_ * .1, .0, -.03)), MH._stoff("ohrmuschel", "1f1d1a", rau=.6, skala=900), rot=(0, P / 2, 0))
# Kamera am Helm + kleine Lampe
rund_box("springer_helmkam", (.03, .05, .03), hm + Vector((.12, .03, .14)), schwarz, .005)
HELMTEILE = [helm, vis, rahmen, haube] + [o for o in bpy.data.objects if o.name.startswith(("springer_scharnier", "springer_helmkam", "springer_ohr"))]
# Augenbrauen voll statt gepunktet
hm_mat = bpy.data.materials.get("haare")
if hm_mat:
    for nd in hm_mat.node_tree.nodes:
        if nd.type == "MATH" and nd.operation == "GREATER_THAN":
            nd.inputs[1].default_value = -1.0
for o in HELMTEILE:
    an_knochen(o, rig, "head")
# Halsring
hr = Vector((hals.x, hals.y + .0, hals.z - .03))
bpy.ops.mesh.primitive_torus_add(major_radius=.135, minor_radius=.02, major_segments=64, location=hr)
ring = bpy.context.object; ring.name = "springer_halsring"; ring.scale = (1.05, .95, 1); ring.data.materials.append(blau)
zyl("springer_halsring2", .145, .03, hr - Vector((0, 0, .025)), alu)
ring2 = bpy.context.object; ring2.scale = (1.05, .95, 1)
# Brustmodul (Instrumente) + Schlaeuche
bp_ = Vector((0, hals.y - .2, hals.z - .3))
brust = rund_box("springer_brust", (.3, .12, .2), bp_, weiss, .02)
anz_ = rund_box("springer_display", (.11, .01, .06), bp_ + Vector((-.05, -.062, .03)), schwarz, .004)
dm = bpy.data.materials.new("display"); dm.use_nodes = True; db = dm.node_tree.nodes["Principled BSDF"]
db.inputs["Emission Color"].default_value = (.35, 1, .55, 1); db.inputs["Emission Strength"].default_value = 2.5; db.inputs["Base Color"].default_value = (0, 0, 0, 1)
rund_box("springer_displaylicht", (.09, .004, .04), bp_ + Vector((-.05, -.068, .03)), dm, .002)
for i, f in enumerate(("rot", "gelb", "gruen")):
    km = mat("knopf_" + f, {"rot": "c62828", "gelb": "e0b000", "gruen": "2e9d4a"}[f], .3)
    zyl("springer_knopf", .012, .015, bp_ + Vector((.06 + i * .028, -.064, .03)), km, rot=(P / 2, 0, 0), v=16)
rund_box("springer_griff", (.14, .03, .025), bp_ + Vector((0, -.07, -.06)), rot, .008)
for s_ in (-1, 1):
    zyl("springer_anschluss", .022, .05, bp_ + Vector((s_ * .12, -.04, .1)), alu, rot=(P / 2, 0, 0))
# Fallschirm-Container auf dem Ruecken
rk = Vector((0, hals.y + .2, hals.z - .32))
cont = rund_box("springer_container", (.38, .18, .5), rk, MH._stoff("container", "3c4a3c", rau=.8, skala=700), .04, 4)
rund_box("springer_pilot", (.12, .03, .12), rk + Vector((0, .095, -.15)), rot, .02)
# Gurte: zwei Brustgurte + Beinschlaufen als flache Ringe um den Rumpf
for z_, r_ in ((hals.z - .2, .2), (hals.z - .42, .19), (becken.z + .02, .2)):
    bpy.ops.mesh.primitive_torus_add(major_radius=r_, minor_radius=.012, major_segments=48, location=(0, hals.y + .02, z_))
    g = bpy.context.object; g.name = "springer_gurt"; g.scale = (1, .82, 2.2); g.data.materials.append(gurt)
SPINE = [ring, ring2, brust, cont] + [o for o in bpy.data.objects if o.name.startswith(("springer_display", "springer_knopf", "springer_griff", "springer_anschluss", "springer_pilot", "springer_gurt"))]
for o in SPINE:
    an_knochen(o, rig, "spine03")
# Hoehenmesser am linken Unterarm
hm_ = M.gm("joint-l-elbow") * .4 + M.gm("joint-l-hand") * .6
alt_ = zyl("springer_hoehenmesser", .035, .025, hm_ + Vector((0, -.05, 0)), schwarz, rot=(P / 2, 0, 0))
an_knochen(alt_, rig, "lowerarm01.L")
# Handschuh-Manschetten (Ring zwischen Aermel und Handschuh)
MANSCH = []
for sd_, j in (("L", "l"), ("R", "r")):
    e_ = M.gm(f"joint-{j}-elbow"); h_ = M.gm(f"joint-{j}-hand"); d_ = (h_ - e_).normalized()
    o = zyl("springer_manschette_" + sd_, .052, .05, e_ + (h_ - e_) * .8, blau)
    o.rotation_euler = d_.to_track_quat("Z", "Y").to_euler(); o.scale = (1, .8, 1)
    an_knochen(o, rig, "lowerarm02." + sd_); MANSCH.append(o)
M.objekte += HELMTEILE + SPINE + [alt_] + MANSCH
M.zuruecksetzen()

# ======================================================================  Himmel + Sonne
w = bpy.data.worlds.new("welt"); sc.world = w; w.use_nodes = True; nt = w.node_tree
sky = nt.nodes.new("ShaderNodeTexSky")
try:
    sky.sky_type = "NISHITA"
except Exception:
    pass
sky.sun_disc = True; sky.sun_size = math.radians(.8); sky.air_density = 1.0; sky.aerosol_density = .6
nt.links.new(sky.outputs[0], nt.nodes["Background"].inputs[0]); nt.nodes["Background"].inputs[1].default_value = .9
bpy.ops.object.light_add(type="SUN"); sonne = bpy.context.object; sonne.data.angle = math.radians(.6); sonne.data.energy = 4.5


def sonne_setzen(el, rot):
    sky.sun_elevation = math.radians(el); sky.sun_rotation = math.radians(rot)
    sonne.rotation_euler = (math.radians(90 - el), 0, math.radians(rot - 90))
    sonne.data.energy = 1.2 + 3.6 * ease(el / 18); sonne.data.color = (1, .78 + .2 * ease(el / 20), .62 + .32 * ease(el / 22))


# ======================================================================  Erdkappe (Ursprung = Bodenpunkt unter dem Mann)
R = 6371000.0


def kappe(name, rad, tmax=.14, NR=230, NS=384):
    bm = bmesh.new(); vs = [bm.verts.new((0, 0, rad - R))]
    ringe = []
    for i in range(1, NR + 1):
        th = tmax * (i / NR) ** 2.6; ring = []
        for j in range(NS):
            ph = 2 * P * j / NS
            ring.append(bm.verts.new((rad * math.sin(th) * math.cos(ph), rad * math.sin(th) * math.sin(ph), rad * math.cos(th) - R)))
        ringe.append(ring)
    for j in range(NS):
        bm.faces.new((vs[0], ringe[0][j], ringe[0][(j + 1) % NS]))
    for i in range(NR - 1):
        a, b = ringe[i], ringe[i + 1]
        for j in range(NS):
            bm.faces.new((a[j], b[j], b[(j + 1) % NS], a[(j + 1) % NS]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o)
    for p in me.polygons:
        p.use_smooth = True
    return o


erde = kappe("erde", R)
em = bpy.data.materials.new("erde"); em.use_nodes = True; n = em.node_tree.nodes; l = em.node_tree.links; b = n["Principled BSDF"]
tc = n.new("ShaderNodeTexCoord")


def rausch(skala, detail=8, rau=.55, vek=None):
    mp = n.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (skala, skala, skala); l.new(vek or tc.outputs["Object"], mp.inputs["Vector"])
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1; nz.inputs["Detail"].default_value = detail
    nz.inputs["Roughness"].default_value = rau; l.new(mp.outputs[0], nz.inputs["Vector"]); return nz


def rampe(eing, farben):
    cr = n.new("ShaderNodeValToRGB"); el = cr.color_ramp.elements
    while len(el) < len(farben):
        el.new(.5)
    for e_, (pos, f) in zip(el, farben):
        e_.position = pos; e_.color = (*hexf(f), 1)
    l.new(eing, cr.inputs["Fac"]); return cr


def mix(fac, a, b_, op="MIX"):
    m_ = n.new("ShaderNodeMix"); m_.data_type = "RGBA"; m_.blend_type = op
    l.new(fac, m_.inputs[0]) if not isinstance(fac, float) else None
    if isinstance(fac, float):
        m_.inputs[0].default_value = fac
    l.new(a, m_.inputs[6]); l.new(b_, m_.inputs[7]); return m_


gross = rausch(1 / 160000, 10, .6)          # Landschaften (~100 km)
mittel = rausch(1 / 9000, 10, .58)          # Huegel, Flussbetten (~km)
fein = rausch(1 / 220, 8, .6)               # Gelaendeflecken (~100 m)
korn = rausch(1 / .35, 6, .7)               # Kiesel/Sand fuer Nahaufnahmen
c_gross = rampe(gross.outputs["Fac"], [(.30, "6e5238"), (.45, "94795a"), (.55, "86684a"), (.68, "57503f")])
c_mittel = rampe(mittel.outputs["Fac"], [(.35, "634c36"), (.5, "a38b68"), (.62, "7d6448")])
m1 = mix(.6, c_gross.outputs[0], c_mittel.outputs[0], "OVERLAY")
berge = rampe(mittel.outputs["Fac"], [(.60, "000000"), (.70, "ffffff")])
bm_ = rampe(gross.outputs["Fac"], [(.55, "000000"), (.7, "ffffff")])
bergf = n.new("ShaderNodeMath"); bergf.operation = "MULTIPLY"; l.new(berge.outputs[0], bergf.inputs[0]); l.new(bm_.outputs[0], bergf.inputs[1])
m2 = mix(bergf.outputs[0], m1.outputs[2], rampe(fein.outputs["Fac"], [(.4, "4b4337"), (.6, "6a5d4b")]).outputs[0])
rinne = rausch(1 / 2600, 6, .55)
rs = n.new("ShaderNodeMath"); rs.operation = "SUBTRACT"; rs.inputs[1].default_value = .5; l.new(rinne.outputs["Fac"], rs.inputs[0])
ra = n.new("ShaderNodeMath"); ra.operation = "ABSOLUTE"; l.new(rs.outputs[0], ra.inputs[0])
rr0 = rampe(ra.outputs[0], [(.006, "ffffff"), (.018, "000000")])
rmk = rampe(rausch(1 / 40000, 4, .5).outputs["Fac"], [(.5, "000000"), (.6, "8c8c8c")])
rr_ = n.new("ShaderNodeMath"); rr_.operation = "MULTIPLY"; l.new(rr0.outputs[0], rr_.inputs[0]); l.new(rmk.outputs[0], rr_.inputs[1])
m2b = mix(rr_.outputs[0], m2.outputs[2], rampe(fein.outputs["Fac"], [(.4, "3e3529"), (.6, "564835")]).outputs[0])
lava = rausch(1 / 30000, 8, .6)
lv = rampe(lava.outputs["Fac"], [(.98, "000000"), (.99, "000000")])
m2c = mix(lv.outputs[0], m2b.outputs[2], rampe(fein.outputs["Fac"], [(.4, "3a3733"), (.6, "4a4540")]).outputs[0])
m2 = m2c
c_fein = rampe(fein.outputs["Fac"], [(.3, "000000"), (.7, "ffffff")])
m3 = mix(.45, m2.outputs[2], c_fein.outputs[0], "SOFT_LIGHT")
gruen = rampe(fein.outputs["Fac"], [(.66, "000000"), (.74, "ffffff")])     # Bueschel-Flecken
m4 = mix(gruen.outputs[0], m3.outputs[2], rampe(korn.outputs["Fac"], [(.3, "4c4a32"), (.7, "5f5b3c")]).outputs[0])
c_korn = rampe(korn.outputs["Fac"], [(.35, "000000"), (.65, "ffffff")])
m5 = mix(.18, m4.outputs[2], c_korn.outputs[0], "SOFT_LIGHT")
# Dunst zum Horizont (streifender Blick)
lw = n.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = .5
pw = n.new("ShaderNodeMath"); pw.operation = "POWER"; pw.inputs[1].default_value = 3.0; l.new(lw.outputs["Facing"], pw.inputs[0])
DUNST = pw.inputs[1]
dunst_f = (*hexf("a9c6ee"), 1)
md = n.new("ShaderNodeMix"); md.data_type = "RGBA"; l.new(pw.outputs[0], md.inputs[0]); l.new(m5.outputs[2], md.inputs[6]); md.inputs[7].default_value = dunst_f
l.new(md.outputs[2], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = .95
em_s = n.new("ShaderNodeMath"); em_s.operation = "MULTIPLY"; em_s.inputs[1].default_value = .9; l.new(pw.outputs[0], em_s.inputs[0])
b.inputs["Emission Color"].default_value = dunst_f; l.new(em_s.outputs[0], b.inputs["Emission Strength"])
DUNST_E = em_s.inputs[1]
bp1 = n.new("ShaderNodeBump"); bp1.inputs["Strength"].default_value = .5; bp1.inputs["Distance"].default_value = .02
l.new(korn.outputs["Fac"], bp1.inputs["Height"]); l.new(bp1.outputs[0], b.inputs["Normal"])
erde.data.materials.append(em)
# Wolkenschale (kleine Cumulus-Felder, 2.5 km hoch)
wolke = kappe("wolken", R + 2500, NR=180)
wm = bpy.data.materials.new("wolken"); wm.use_nodes = True; n = wm.node_tree.nodes; l = wm.node_tree.links; b = n["Principled BSDF"]
tc = n.new("ShaderNodeTexCoord")
w1 = rausch(1 / 6000, 12, .62); w2 = rausch(1 / 90000, 4, .5)
wa = n.new("ShaderNodeMath"); wa.operation = "MULTIPLY"; l.new(w1.outputs["Fac"], wa.inputs[0]); l.new(w2.outputs["Fac"], wa.inputs[1])
wr = rampe(wa.outputs[0], [(.36, "000000"), (.42, "ffffff")])
b.inputs["Base Color"].default_value = (1, 1, 1, 1); b.inputs["Roughness"].default_value = 1
l.new(wr.outputs[0], b.inputs["Alpha"])
wolke.data.materials.append(wm)
wolke.parent = erde

# ======================================================================  Startplatz (an der Erde befestigt)
BODEN = []
busch_m = MH._stoff("busch", "3d4128", rau=.9, skala=40)
bm = bmesh.new()
rb_ = random.Random(3)
for i in range(7):
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=rb_.uniform(.25, .45), matrix=Matrix.Translation((rb_.uniform(-.4, .4), rb_.uniform(-.4, .4), rb_.uniform(.15, .45))))
for v in bm.verts:
    v.co *= 1 + .35 * math.sin(v.co.x * 23 + v.co.y * 17) * math.cos(v.co.z * 19)
me = bpy.data.meshes.new("busch"); bm.to_mesh(me); bm.free(); me.materials.append(busch_m)
for p in me.polygons:
    p.use_smooth = True
rb_ = random.Random(11)
for i in range(420):
    r_ = 12 + 420 * rb_.random() ** 1.4; a_ = rb_.uniform(0, 2 * P)
    o = bpy.data.objects.new("busch", me); sc.collection.objects.link(o)
    o.location = (r_ * math.cos(a_), r_ * math.sin(a_), -.12); s_ = rb_.uniform(.35, 1.0); o.scale = (s_, s_, s_ * rb_.uniform(.6, 1))
    o.rotation_euler = (0, 0, rb_.uniform(0, 6.3)); o.parent = erde; BODEN.append(o)
# Tafelberge am Horizont
fels_m = MH._stoff("fels", "7a5a40", rau=.95, skala=3)
rm_ = random.Random(8); BERGE = []
for i in range(14):
    a_ = rm_.uniform(0, 2 * P); r_ = rm_.uniform(7000, 22000)
    bpy.ops.mesh.primitive_cylinder_add(radius=1, depth=1, vertices=48, location=(r_ * math.cos(a_), r_ * math.sin(a_), 0)); o = bpy.context.object
    o.scale = (rm_.uniform(600, 2200), rm_.uniform(400, 1500), rm_.uniform(120, 380)); o.data.materials.append(fels_m)
    bpy.ops.object.transform_apply(scale=True)
    bv = o.modifiers.new("b", "BEVEL"); bv.width = 90; bv.segments = 3
    tx = bpy.data.textures.new("fels%d" % i, "CLOUDS"); tx.noise_scale = 400; dsp = o.modifiers.new("d", "DISPLACE"); dsp.texture = tx; dsp.strength = 120
    sub = o.modifiers.new("s", "SUBSURF"); sub.levels = sub.render_levels = 2; o.modifiers.move(2, 1)
    o.location.z -= o.dimensions.z * .1 if False else 0
    o.location.z = - (r_ ** 2) / (2 * R); o.parent = erde; BERGE.append(o)
# Pickups + Anhaenger der Startmannschaft
lack = mat("lack", "e9e9e6", .25, Coat_Weight=.6); glas = mat("glas", "1d2530", .05)
reif = mat("reifen", "1a1a1a", .85)
STARTP = []


def pickup(ort, dreh):
    teile = []
    teile.append(rund_box("pk", (5.3, 1.95, .75), (0, 0, .95), lack, .08))
    teile.append(rund_box("pk", (2.4, 1.9, .85), (-.6, 0, 1.75), lack, .12))
    teile.append(rund_box("pk", (2.2, 1.92, .55), (-.6, 0, 1.78), glas, .1))
    for x_ in (-1.7, 1.6):
        for y_ in (-.92, .92):
            teile.append(zyl("pk", .4, .3, (x_, y_, .4), reif, rot=(P / 2, 0, 0)))
    leer = bpy.data.objects.new("pickup", None); sc.collection.objects.link(leer)
    for t_ in teile:
        t_.parent = leer
    leer.location = ort; leer.rotation_euler = (0, 0, dreh); leer.parent = erde; STARTP.append(leer); STARTP.extend(teile)


pickup((-14, 18, 0), .4); pickup((16, 24, 0), -1.1); pickup((-30, -8, 0), 2.0)
# Startfahrzeug (Kran-Lkw, der den Mann bis zum Abheben haelt)
kr_m = mat("kran", "d8d8d2", .35, Coat_Weight=.4); stahl = mat("stahl", "6f7378", .4, .9)
kr = [rund_box("kr", (8.5, 2.5, 1.2), (0, 0, 1.2), kr_m, .1), rund_box("kr", (2.2, 2.45, 1.6), (3.6, 0, 2.4), kr_m, .15),
      rund_box("kr", (.3, 2.3, 1.0), (4.75, 0, 2.5), glas, .1), rund_box("kr", (.35, .35, 9), (-2.4, 0, 6.0), stahl, .04)]
for x_ in (-3, -1.6, 3.3):
    for y_ in (-1.15, 1.15):
        kr.append(zyl("kr", .55, .4, (x_, y_, .55), reif, rot=(P / 2, 0, 0)))
krl = bpy.data.objects.new("kranwagen", None); sc.collection.objects.link(krl)
for t_ in kr:
    t_.parent = krl
krl.location = (5.5, 9, 0); krl.rotation_euler = (0, 0, -.3); krl.parent = erde; STARTP.extend(kr + [krl])
# Helfer (MPFB, Warnweste)
HELFER = []
for i, (ort, dr, sd) in enumerate((((3.2, -2.4, 0), 2.2, 21), ((-3.5, 1.5, 0), -1.0, 33))):
    hf = MH.Arbeiter(name=f"helfer{i}", seed=sd, maenn=1.0 if i == 0 else 0.0, alter=.4, muskel=.5, gewicht=.5, haut="caucasian" if i == 0 else "african")
    hf.dreh("upperarm01.L", z=-.72); hf.dreh("upperarm01.R", z=.72)
    hf.dreh("neck01", x=-.5); hf.rig.location = ort; hf.rig.rotation_euler = (0, 0, dr); hf.rig.parent = erde
    if i == 0:
        hf.dreh("upperarm01.R", x=2.4, z=.4); hf.dreh("lowerarm01.R", x=-.3)
    HELFER.append(hf)

# ======================================================================  Ballon (Formschluessel: Start-Tropfen -> Kuerbis)
NB, NG, ZG = 120, 216, 24
LT = 22.0                    # Seil Mann -> Ballonfuss


def profil_start(s, ph):
    Ht, rb = 150.0, 12.0; s0 = .8
    if s < s0:
        k = s / s0; z = k * (Ht - 2 * rb); r = .4 + 2.2 * k ** 1.5
        r *= 1 + .28 * math.sin(37 * ph + 7 * k) * min(1, k * 6)
    else:
        a = P * (s - s0) / (1 - s0); z = Ht - 2 * rb + rb * (1 - math.cos(a)) * 1.08
        r = max(rb * math.sin(a) * (1 + .1 * math.sin(a / 2)), 2.6 * (1 - a / P * 2)) * (1 + .012 * abs(math.sin(ZG / 2 * ph)))
    return r, z


def profil_oben(s, ph):
    Rb = 58.0; a = P * s
    r = Rb * math.sin(a) * (1 + .03 * abs(math.sin(ZG / 2 * ph))); z = Rb * (1 - math.cos(a)) * .86
    return r, z


bm = bmesh.new(); ring = []
for i in range(NB + 1):
    s = i / NB; rr = []
    for j in range(NG):
        ph = 2 * P * j / NG; r, z = profil_start(s, ph)
        rr.append(bm.verts.new((r * math.cos(ph), r * math.sin(ph), z)))
    ring.append(rr)
for i in range(NB):
    for j in range(NG):
        bm.faces.new((ring[i][j], ring[i][(j + 1) % NG], ring[i + 1][(j + 1) % NG], ring[i + 1][j]))
me = bpy.data.meshes.new("ballon"); bm.to_mesh(me); bm.free()
ballon = bpy.data.objects.new("ballon", me); sc.collection.objects.link(ballon)
ballon.shape_key_add(name="start"); sk = ballon.shape_key_add(name="oben")
for i in range(NB + 1):
    for j in range(NG):
        ph = 2 * P * j / NG; r, z = profil_oben(i / NB, ph); sk.data[i * NG + j].co = (r * math.cos(ph), r * math.sin(ph), z)
for p in me.polygons:
    p.use_smooth = True
BAL_K = sk
fm_ = bpy.data.materials.new("folie"); fm_.use_nodes = True; n = fm_.node_tree.nodes; l = fm_.node_tree.links
b = n["Principled BSDF"]; b.inputs["Base Color"].default_value = (.93, .94, .96, 1); b.inputs["Roughness"].default_value = .22
b.inputs["Coat Weight"].default_value = .4; b.inputs["Sheen Weight"].default_value = .3
tr = n.new("ShaderNodeBsdfTransparent"); ms = n.new("ShaderNodeMixShader"); ms.inputs[0].default_value = .62
fz = n.new("ShaderNodeFresnel"); fz.inputs["IOR"].default_value = 1.25
mm_ = n.new("ShaderNodeMath"); mm_.operation = "MULTIPLY_ADD"; mm_.inputs[1].default_value = .55; mm_.inputs[2].default_value = .38
l.new(fz.outputs[0], mm_.inputs[0]); l.new(mm_.outputs[0], ms.inputs[0])
l.new(tr.outputs[0], ms.inputs[1]); l.new(b.outputs[0], ms.inputs[2]); l.new(ms.outputs[0], n["Material Output"].inputs["Surface"])
# Lastbaender (Naehte) als dunklere Linien entlang der Bahnen
gc = n.new("ShaderNodeTexCoord"); sx = n.new("ShaderNodeSeparateXYZ"); l.new(gc.outputs["Object"], sx.inputs[0])
at2 = n.new("ShaderNodeMath"); at2.operation = "ARCTAN2"; l.new(sx.outputs[1], at2.inputs[0]); l.new(sx.outputs[0], at2.inputs[1])
mu = n.new("ShaderNodeMath"); mu.operation = "MULTIPLY"; mu.inputs[1].default_value = ZG / (2 * P); l.new(at2.outputs[0], mu.inputs[0])
fr = n.new("ShaderNodeMath"); fr.operation = "PINGPONG"; fr.inputs[1].default_value = .5; l.new(mu.outputs[0], fr.inputs[0])
lt = n.new("ShaderNodeMath"); lt.operation = "LESS_THAN"; lt.inputs[1].default_value = .025; l.new(fr.outputs[0], lt.inputs[0])
cm = n.new("ShaderNodeMix"); cm.data_type = "RGBA"; l.new(lt.outputs[0], cm.inputs[0]); cm.inputs[6].default_value = (.93, .94, .96, 1)
cm.inputs[7].default_value = (.55, .56, .6, 1); l.new(cm.outputs[2], b.inputs["Base Color"])
me.materials.append(fm_)
# Seil + Ballonfuss (Ring, Ventilbox)
seil_m = mat("seil", "d9d4c4", .7)
bpy.ops.mesh.primitive_cylinder_add(radius=.025, depth=1, vertices=12); seil = bpy.context.object; seil.name = "seil"; seil.data.materials.append(seil_m)
GRIFF = rund_box("ausloeser", (.03, .03, .13), (0, 0, 0), rot, .01)
bpy.ops.mesh.primitive_cylinder_add(radius=.006, depth=1, vertices=8); GKABEL = bpy.context.object; GKABEL.data.materials.append(rot)
TRAG = []
for i in range(2):
    bpy.ops.mesh.primitive_cylinder_add(radius=.018, depth=1, vertices=8); o = bpy.context.object; o.data.materials.append(gurt); TRAG.append(o)
bpy.ops.mesh.primitive_torus_add(major_radius=.05, minor_radius=.012); TRING = bpy.context.object; TRING.data.materials.append(alu)
fuss = zyl("ballonfuss", .45, .35, (0, 0, 0), stahl)
rund_box("ventilbox", (.7, .7, .8), (0, 0, -.6), weiss, .06).parent = fuss

# ======================================================================  Stabilisierungsschirm + Hauptschirm
def kuppel(name, r, m, tief=.55):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=20, radius=r)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < r * (1 - tief) - r * .0 and v.co.z < 0], context="VERTS")
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); o = bpy.data.objects.new(name, me); sc.collection.objects.link(o)
    me.materials.append(m); o.modifiers.new("d", "SOLIDIFY").thickness = .01
    for p in me.polygons:
        p.use_smooth = True
    return o


schirm_m = bpy.data.materials.new("schirmstoff"); schirm_m.use_nodes = True; n = schirm_m.node_tree.nodes; l = schirm_m.node_tree.links
b = n["Principled BSDF"]; b.inputs["Roughness"].default_value = .55; b.inputs["Sheen Weight"].default_value = .5
gc = n.new("ShaderNodeTexCoord"); sx = n.new("ShaderNodeSeparateXYZ"); l.new(gc.outputs["Object"], sx.inputs[0])
at2 = n.new("ShaderNodeMath"); at2.operation = "ARCTAN2"; l.new(sx.outputs[1], at2.inputs[0]); l.new(sx.outputs[0], at2.inputs[1])
mu = n.new("ShaderNodeMath"); mu.operation = "MULTIPLY"; mu.inputs[1].default_value = 4 / P; l.new(at2.outputs[0], mu.inputs[0])
fl = n.new("ShaderNodeMath"); fl.operation = "FLOOR"; l.new(mu.outputs[0], fl.inputs[0])
md2 = n.new("ShaderNodeMath"); md2.operation = "FLOORED_MODULO"; md2.inputs[1].default_value = 2; l.new(fl.outputs[0], md2.inputs[0])
cm = n.new("ShaderNodeMix"); cm.data_type = "RGBA"; l.new(md2.outputs[0], cm.inputs[0]); cm.inputs[6].default_value = (*hexf("ff6a13"), 1)
cm.inputs[7].default_value = (*hexf("f2f2ee"), 1); l.new(cm.outputs[2], b.inputs["Base Color"])
drogue = kuppel("drogue", .75, schirm_m)
# Hauptschirm: Flaechenschirm mit Zellen (gebogen)
bm = bmesh.new(); NX, NY = 64, 16; Sp, Ch, Di = 8.2, 3.2, .5
gv = {}
for i in range(NX + 1):
    for j in range(NY + 1):
        for k_, sgn in ((0, 1), (1, -1)):
            x = (i / NX - .5) * Sp; y = (j / NY - .5) * Ch
            prof = Di * math.sin(P * (j / NY) ** .7) * (1 - .15 * abs(2 * i / NX - 1))
            zell = .06 * abs(math.sin(P * i / NX * 18)) if sgn > 0 else 0
            z = sgn * (prof * .5 + zell) - x * x * .09
            gv[(i, j, k_)] = bm.verts.new((x, y, z))
for k_ in (0, 1):
    for i in range(NX):
        for j in range(NY):
            q = [gv[(i, j, k_)], gv[(i + 1, j, k_)], gv[(i + 1, j + 1, k_)], gv[(i, j + 1, k_)]]
            bm.faces.new(q if k_ == 0 else q[::-1])
me = bpy.data.meshes.new("hauptschirm"); bm.to_mesh(me); bm.free()
hs_m = bpy.data.materials.new("hauptstoff"); hs_m.use_nodes = True; n = hs_m.node_tree.nodes; l = hs_m.node_tree.links
b = n["Principled BSDF"]; b.inputs["Roughness"].default_value = .5; b.inputs["Sheen Weight"].default_value = .5
gc = n.new("ShaderNodeTexCoord"); sx = n.new("ShaderNodeSeparateXYZ"); l.new(gc.outputs["Object"], sx.inputs[0])
mu = n.new("ShaderNodeMath"); mu.operation = "MULTIPLY"; mu.inputs[1].default_value = 9 / Sp; l.new(sx.outputs[0], mu.inputs[0])
ad = n.new("ShaderNodeMath"); ad.operation = "ADD"; ad.inputs[1].default_value = 4.5; l.new(mu.outputs[0], ad.inputs[0])
fl = n.new("ShaderNodeMath"); fl.operation = "FLOOR"; l.new(ad.outputs[0], fl.inputs[0])
cr2 = n.new("ShaderNodeValToRGB"); cr2.color_ramp.interpolation = "CONSTANT"; el = cr2.color_ramp.elements
el[0].position = 0; el[0].color = (*hexf("1f3f8a"), 1); el[1].position = .3; el[1].color = (*hexf("ff6a13"), 1)
e3 = el.new(.42); e3.color = (*hexf("f2f2ee"), 1); e4 = el.new(.58); e4.color = (*hexf("ff6a13"), 1); e5 = el.new(.75); e5.color = (*hexf("1f3f8a"), 1)
dv = n.new("ShaderNodeMath"); dv.operation = "DIVIDE"; dv.inputs[1].default_value = 9; l.new(fl.outputs[0], dv.inputs[0]); l.new(dv.outputs[0], cr2.inputs["Fac"])
l.new(cr2.outputs[0], b.inputs["Base Color"])
haupt = bpy.data.objects.new("hauptschirm", me); sc.collection.objects.link(haupt); me.materials.append(hs_m)
HDISP = haupt.modifiers.new("knautsch", "DISPLACE"); HDISP.texture = bpy.data.textures.new("knautsch", "CLOUDS"); HDISP.texture.noise_scale = .6; HDISP.strength = 0
for p in me.polygons:
    p.use_smooth = True
haupt.modifiers.new("s", "SUBSURF").levels = 1
LEINEN = []
for i in range(10):
    bpy.ops.mesh.primitive_cylinder_add(radius=.006, depth=1, vertices=6); o = bpy.context.object; o.data.materials.append(seil_m); LEINEN.append(o)
DLEINE = []
for i in range(6):
    bpy.ops.mesh.primitive_cylinder_add(radius=.005, depth=1, vertices=6); o = bpy.context.object; o.data.materials.append(seil_m); DLEINE.append(o)


def linie(o, a, b_):
    a, b_ = Vector(a), Vector(b_); d = b_ - a
    o.location = (a + b_) / 2; o.rotation_euler = d.to_track_quat("Z", "Y").to_euler(); o.scale = (1, 1, max(d.length, .001))


# Eiskristalle / Staub fuer Geschwindigkeit
EIS = []
eis_m = mat("eis", "ffffff", .3)
eis_m.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = (1, 1, 1, 1)
eis_m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = .6
bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=6, v_segments=4, radius=.007); me = bpy.data.meshes.new("eis"); bm.to_mesh(me); bm.free()
me.materials.append(eis_m)
re_ = random.Random(5)
for i in range(260):
    o = bpy.data.objects.new("eis", me); sc.collection.objects.link(o)
    a_ = re_.uniform(0, 2 * P); r_ = re_.uniform(1.4, 4.5)
    o["p"] = (r_ * math.cos(a_), r_ * math.sin(a_), re_.uniform(0, 1)); o.scale = (.7, .7, re_.uniform(10, 26)); EIS.append(o)
# Ueberschall-Ring (Druckwelle, leicht verzerrend)
bpy.ops.mesh.primitive_torus_add(major_radius=1, minor_radius=.16, major_segments=96, minor_segments=24); welle = bpy.context.object
wl = bpy.data.materials.new("welle"); wl.use_nodes = True; n = wl.node_tree.nodes; l = wl.node_tree.links
gl = n.new("ShaderNodeBsdfPrincipled"); gl.inputs["Base Color"].default_value = (1, 1, 1, 1); gl.inputs["Roughness"].default_value = 1
gl.inputs["Emission Color"].default_value = (1, 1, 1, 1); gl.inputs["Emission Strength"].default_value = .3
tr = n.new("ShaderNodeBsdfTransparent"); WELLE_MIX = n.new("ShaderNodeMixShader"); WELLE_MIX.inputs[0].default_value = .7
lw2 = n.new("ShaderNodeLayerWeight"); lw2.inputs["Blend"].default_value = .3
inv = n.new("ShaderNodeMath"); inv.operation = "POWER"; inv.inputs[1].default_value = 1.5; l.new(lw2.outputs["Facing"], inv.inputs[0])
nzw = n.new("ShaderNodeTexNoise"); nzw.inputs["Scale"].default_value = 3; nzw.inputs["Detail"].default_value = 6
mw = n.new("ShaderNodeMath"); mw.operation = "MULTIPLY"; l.new(inv.outputs[0], mw.inputs[0]); l.new(nzw.outputs["Fac"], mw.inputs[1])
tco = n.new("ShaderNodeTexCoord"); sxo = n.new("ShaderNodeSeparateXYZ"); l.new(tco.outputs["Object"], sxo.inputs[0])
fo1 = n.new("ShaderNodeMapRange"); fo1.inputs["From Min"].default_value = -1.75; fo1.inputs["From Max"].default_value = -.2; l.new(sxo.outputs[2], fo1.inputs["Value"])
fo2 = n.new("ShaderNodeMapRange"); fo2.inputs["From Min"].default_value = 1.75; fo2.inputs["From Max"].default_value = 1.0; l.new(sxo.outputs[2], fo2.inputs["Value"])
fo = n.new("ShaderNodeMath"); fo.operation = "MULTIPLY"; l.new(fo1.outputs[0], fo.inputs[0]); l.new(fo2.outputs[0], fo.inputs[1])
mw2 = n.new("ShaderNodeMath"); mw2.operation = "MULTIPLY"; l.new(mw.outputs[0], mw2.inputs[0]); l.new(fo.outputs[0], mw2.inputs[1]); mw = mw2
WELLE_ST = n.new("ShaderNodeMath"); WELLE_ST.operation = "MULTIPLY"; WELLE_ST.inputs[1].default_value = .8; l.new(mw.outputs[0], WELLE_ST.inputs[0])
l.new(WELLE_ST.outputs[0], WELLE_MIX.inputs[0])
l.new(tr.outputs[0], WELLE_MIX.inputs[1]); l.new(gl.outputs[0], WELLE_MIX.inputs[2]); l.new(WELLE_MIX.outputs[0], n["Material Output"].inputs["Surface"])
welle.data.materials.append(wl)
for p in welle.data.polygons:
    p.use_smooth = True
bpy.ops.mesh.primitive_cone_add(radius1=2.2, radius2=.05, depth=3.5, vertices=64, end_fill_type="NOTHING"); kegel = bpy.context.object
kegel.data.materials.append(wl)
for p in kegel.data.polygons:
    p.use_smooth = True

# ======================================================================  Kamera + Ablauf
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam
cam.data.clip_start = .03; cam.data.clip_end = 4e6; cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
cam.data.dof.use_dof = True
ALTMAX = 41422.0


def hoehe(t):
    if t < 4.0:
        return 41000.0 + 400 * t / 4
    if t < 5.86:
        return 0.0
    if t < 7.8:
        return 30 * ease((t - 6.3) / 1.5) ** 1.3
    if t < 9.74:
        k = (t - 7.8) / 1.94; return 30 + (ALTMAX - 30) * (k ** 1.6 * (3 - 2 * k))
    if t < 16.22:
        return ALTMAX
    if t < 23.74:
        k = (t - 16.22) / 7.52; return ALTMAX - (ALTMAX - 6000) * k ** 3
    if t < 25.58:
        return 6000 - 4800 * (t - 23.74) / 1.84
    if t < 27.15:
        k = (t - 25.58) / 1.57; return 15 * (1 - k) ** 1.3
    return 0.0


def punkt(bone, v):
    pb = rig.pose.bones[bone]; bn = rig.data.bones[bone]
    return rig.matrix_world @ pb.matrix @ bn.matrix_local.inverted() @ Vector(v)


SCHULTER = Vector((0, hals.y + .02, hals.z - .02))
KOPF = Vector(hm); BRUST = Vector(bp_); RUECKEN = Vector(rk)


def pose(t, art):
    M.zuruecksetzen(); rig.rotation_euler = (0, 0, 0)
    w = math.sin(t * 2.1)
    if art in ("stehen", "haengen"):
        M.dreh("upperarm01.L", z=-.62, x=.12 + .04 * w); M.dreh("upperarm01.R", z=.62, x=.1 - .04 * w)
        M.dreh("lowerarm01.L", x=-.35); M.dreh("lowerarm01.R", x=-.3)
        M.dreh("neck01", x=.08, z=.15 * math.sin(t * .7))
        if art == "haengen":
            M.dreh("upperleg01.L", x=-.12 + .03 * w); M.dreh("upperleg01.R", x=-.05 - .03 * w)
            M.dreh("lowerleg01.L", x=.22); M.dreh("lowerleg01.R", x=.15)
            M.dreh("foot.L", x=.35); M.dreh("foot.R", x=.3)
    elif art == "griff":
        k = ease((t - 13.7) / .6); z = ease((t - 14.75) / .3)
        M.dreh("upperarm01.L", z=-.62, x=.12); M.dreh("lowerarm01.L", x=-.35)
        M.dreh("upperarm01.R", z=.62 - .42 * k, x=.1 + 2.55 * k); M.dreh("lowerarm01.R", x=-.3 - .25 * k - .55 * z)
        M.dreh("neck01", x=.08 - .3 * k)
        M.dreh("upperleg01.L", x=-.12); M.dreh("lowerleg01.L", x=.22); M.dreh("lowerleg01.R", x=.15)
    elif art == "fallen":
        rig.rotation_euler = (P / 2 - .25 + .05 * w, .04 * math.sin(t * 1.3), .0)
        M.dreh("upperarm01.L", z=.55, x=.25); M.dreh("upperarm01.R", z=-.55, x=.25)
        M.dreh("lowerarm01.L", x=-.9); M.dreh("lowerarm01.R", x=-.9)
        M.dreh("upperleg01.L", z=-.12, x=.25); M.dreh("upperleg01.R", z=.12, x=.25)
        M.dreh("lowerleg01.L", x=.8); M.dreh("lowerleg01.R", x=.8)
        M.dreh("neck01", x=-.55); M.dreh("spine03", x=-.15)
    elif art == "schirm":
        M.dreh("upperarm01.L", z=.25, x=.4); M.dreh("upperarm01.R", z=-.25, x=.4)
        M.dreh("lowerarm01.L", x=-1.2); M.dreh("lowerarm01.R", x=-1.2)
        M.dreh("upperleg01.L", x=-.15); M.dreh("upperleg01.R", x=-.05); M.dreh("lowerleg01.L", x=.2); M.dreh("lowerleg01.R", x=.1)
        M.dreh("neck01", x=-.25)
    elif art == "landen":
        M.dreh("upperarm01.L", z=-.3, x=.3); M.dreh("upperarm01.R", z=.3, x=.3)
        M.dreh("lowerarm01.L", x=-.5); M.dreh("lowerarm01.R", x=-.5)
        M.dreh("neck01", x=-.55 * ease((t - 28.3) / 1.2), z=.1)


# Einstellungen: (von, bis, pos0, ziel0, pos1, ziel1, linse) relativ zum Mann (Ursprung) bzw. absolut
SZ = [
    (0.00, 1.84, (.5, -1.15, 1.72), (0, -.05, 1.58), (.36, -.95, 1.68), (0, -.05, 1.6), 40),
    (1.84, 4.00, (-95, -205, 30), (0, 0, 10), (-75, -220, 26), (0, 0, 12), 24),
    (4.00, 5.86, (5.5, -14, 1.5), (0, 0, 2.5), (4.0, -13, 1.3), (0, 0, 45), 20),
    (5.86, 7.80, (6, -12, .7), (0, 0, 1.1), (5, -11, .6), (0, 0, 1.1), 17),
    (7.80, 9.74, (4.8, -6.5, 3.6), (0, 0, -.6), (5.3, -5.6, 3.2), (0, 0, -.4), 24),
    (9.74, 10.86, (2.5, -4.5, -.8), (0, 0, 4), (2.1, -4.3, -.9), (0, 0, 4.5), 14),
    (10.86, 11.98, (.6, -1.0, 1.0), (0, -.1, 1.2), (.3, -1.0, 1.35), (0, -.1, 1.5), 38),
    (11.98, 13.60, (-600, -1100, 120), (0, 0, -160), (-540, -1020, 110), (0, 0, -150), 32),
    (13.60, 15.18, (.15, -1.95, 1.55), (.06, -.05, 1.85), (.1, -1.8, 1.6), (.06, -.05, 1.85), 28),
    (15.18, 16.22, (.9, -.6, 2.6), (0, 0, -6), (.9, -.6, 2.6), (0, 0, -12), 18),
    (16.22, 18.78, (5.2, -3.6, .9), (0, -.9, .1), (4.6, -4.2, 1.2), (0, -.9, .1), 28),
    (18.78, 21.62, (-.5, -4.4, -2.6), (0, -.9, .5), (.4, -3.8, -2.3), (0, -.9, .5), 22),
    (21.62, 23.74, (-11, -12, -2), (0, -.9, .8), (-9, -13, -1.5), (0, -.9, .8), 30),
    (23.74, 25.58, (1.5, -3.0, -1.2), (0, 0, 5), (1.2, -2.6, -1.0), (0, 0, 6), 22),
    (25.58, 27.54, (9, -22, 1.5), (0, 0, 3), (8, -20, 1.4), (0, 0, 1.6), 22),
    (27.54, 30.50, (1.0, -3.4, 1.1), (0, 0, 1.5), (2.2, -6.5, 1.0), (0, 1, 1.8), 26),
]


def zustand(t):
    alt = hoehe(t)
    erde.location = (0, 0, -alt); wolke.hide_render = alt < 6000 and not (25.58 <= t)
    wolke.hide_render = alt < 5000
    for o in BERGE:
        o.hide_render = alt > 2500
    sky.altitude = min(alt, 59000)
    # Dunst: am Boden schwach, oben stark (Erdrand)
    DUNST.default_value = 4.0 if alt > 15000 else (5.0 if alt > 1500 else 9.0)
    DUNST_E.default_value = .18 if alt > 15000 else .1
    # Sonne: Morgendaemmerung beim Start, spaeter hoeher
    if 4.0 <= t < 7.8:
        sonne_setzen(5 + 1.5 * (t - 4) / 3.8, 95)
    elif 7.8 <= t < 9.74:
        sonne_setzen(6.5 + 15 * ease((t - 7.8) / 1.94), 95 + 20 * ease((t - 7.8) / 1.94))
    elif t >= 23.74:
        sonne_setzen(26, 122)
    else:
        sonne_setzen(22, 115)
    for o in STARTP + HELFER_OBJ:
        o.hide_render = not (4.0 <= t < 7.8)
    # Pose
    if t < 4.0 or 5.86 <= t < 13.6:
        art = "stehen" if 4.0 <= t < 6.4 else "haengen"
    elif 4.0 <= t < 5.86:
        art = "stehen"
    elif t < 15.18:
        art = "griff"
    elif t < 15.6:
        art = "haengen"
    elif t < 24.1:
        art = "fallen"
    elif t < 27.1:
        art = "schirm"
    else:
        art = "landen"
    if 4.0 <= t < 5.86:
        art = "stehen"
    pose(t, art)
    if 15.18 <= t < 16.22:
        # Fall weg vom Seil (Zeit gestreckt)
        k = t - 15.18; rig.location = (0, -.6 * k, -0.5 * 9.81 * (k * 2.2) ** 2 / 1.0)
        rig.rotation_euler = (min(P / 2 - .25, k * 2.0), 0, 0)
    elif 23.74 <= t < 24.6:
        k = ease((t - 23.74) / .86); rig.location = (0, 0, 0)
        rig.rotation_euler = ((P / 2 - .25) * (1 - k), 0, 0)
    else:
        rig.location = (0, 0, 0)
    if t >= 27.1:
        rig.location = (0, 0, 0)
    bpy.context.view_layer.update()
    # Ballon + Seil
    an_seil = t < 15.18 or (15.18 <= t < 16.22)
    fall_off = 0.0
    if 15.18 <= t < 16.22:
        fall_off = 0
    form = 1.0 if t < 4.0 else (0.0 if t < 7.8 else (ease((t - 7.8) / 1.94) if t < 9.74 else 1.0))
    BAL_K.value = form
    sichtbar_b = t < 16.22
    ballon.hide_render = fuss.hide_render = seil.hide_render = not sichtbar_b
    for o_ in fuss.children:
        o_.hide_render = not sichtbar_b
    neig = .12 * (1 - form) if 4.0 <= t < 9.74 else 0
    ballon.location = (0, LT * math.sin(neig), LT + 1.9); ballon.rotation_euler = (-neig, 0, 0)
    fuss.location = (0, 0, LT + 1.9 + .2)
    oben = punkt("spine03", SCHULTER + Vector((0, -.02, .85)))
    an_ = t < 15.18
    for i, o in enumerate(TRAG):
        o.hide_render = not an_
        linie(o, punkt("spine03", SCHULTER + Vector(((-.17, .17)[i], -.02, .02))), oben)
    TRING.hide_render = not an_; TRING.location = oben; TRING.rotation_euler = (P / 2, 0, 0)
    g_on = 13.6 <= t < 15.18
    GRIFF.hide_render = GKABEL.hide_render = not g_on
    if g_on:
        hand = punkt("lowerarm02.R", M.gm("joint-r-hand"))
        k = ease((t - 13.7) / .6)
        rast = oben + Vector((.08, -.06, -.25))
        gp = rast.lerp(hand + Vector((0, 0, .02)), ease((t - 14.2) / .25)) if t >= 14.2 else rast
        GRIFF.location = gp; GRIFF.rotation_euler = (0, .3, 0)
        linie(GKABEL, gp, oben)
    if t < 15.18:
        linie(seil, oben, fuss.location)
    else:
        linie(seil, (0, 0, LT * .55), fuss.location)
    # Stabilisierungsschirm (nach Ausstieg bis Hauptschirm)
    dr_on = 16.22 <= t < 24.0
    ruck = punkt("spine03", RUECKEN + Vector((0, .1, .1)))
    drogue.hide_render = not dr_on
    dp = ruck + Vector((0, .3, 5.5))
    drogue.location = dp; drogue.rotation_euler = (0, 0, t * .8)
    for i, o in enumerate(DLEINE):
        o.hide_render = not dr_on
        a_ = 2 * P * i / len(DLEINE)
        linie(o, ruck, dp + Vector((.7 * math.cos(a_ + t * .8), .7 * math.sin(a_ + t * .8), .35)))
    # Hauptschirm
    h_on = t >= 23.9; HDISP.strength = 0
    haupt.hide_render = not h_on
    sch = punkt("spine03", SCHULTER)
    if t < 27.3:
        k = ease((t - 23.9) / .8)
        haupt.scale = (.18 + .82 * k, .35 + .65 * k, .4 + .6 * k)
        haupt.location = sch + Vector((0, .3, 2 + 5.3 * k)); haupt.rotation_euler = (.12 * k, 0, .05 * math.sin(t))
    else:
        k = ease((t - 27.3) / 1.4)
        if k < 1:
            haupt.scale = (1, 1, 1 - .3 * k); haupt.location = Vector((0, 2 + 3.5 * k, 7.3 * (1 - k) + .35 * k))
            haupt.rotation_euler = (.12 + 1.4 * k * (1 - k), 0, .05)
        else:
            haupt.scale = (.95, .9, .12); haupt.location = Vector((.4, 5.6, .3)); haupt.rotation_euler = (0, 0, .25)
        HDISP.strength = .7 * k
        if t >= 27.54:
            haupt.hide_render = True
    for i, o in enumerate(LEINEN):
        o.hide_render = not h_on or t > 27.45
        if h_on:
            ii = i % 5; s_ = -1 if i < 5 else 1
            ende = haupt.matrix_world @ Vector(((ii / 4 - .5) * 7.6, s_ * 1.2, -.3 - .09 * ((ii / 4 - .5) * 7.6) ** 2))
            linie(o, sch + Vector((.18 * (1 if (ii / 4 - .5) > 0 else -1), 0, .05)), ende)
    # Eis/Staub, Druckwelle
    fall = 16.22 <= t < 23.74
    for o in EIS:
        o.hide_render = not fall
        if fall:
            x, y, f = o["p"]; z = ((f + t * 2.7) % 1) * 40 - 20
            o.location = (x, y, z)
    wv = 21.62 <= t < 23.4
    welle.hide_render = not wv; kegel.hide_render = True
    if wv:
        k = (t - 21.62) / 1.78; welle.location = (0, -.9, .6 + 2.5 * k); s_ = 1.0 + 8 * k ** .7; welle.scale = (s_, s_, s_ * .5)
        WELLE_ST.inputs[1].default_value = .9 * math.sin(P * min(1, k * 1.3)) ** .7
        kegel.location = (0, -.9, 1.1 + .3 * k); kegel.rotation_euler = (P, 0, 0); kegel.scale = (1.1 + .5 * k, 1.1 + .5 * k, 1.0 + .2 * k)
    # Kamera
    for s in SZ:
        if s[0] <= t < s[1]:
            k = (t - s[0]) / (s[1] - s[0]); k = ease(k) * .8 + k * .2
            pos = lerpv(s[2], s[4], k); ziel = lerpv(s[3], s[5], k); lin = s[6]; nr = SZ.index(s)
            break
    if nr == 3:      # Kamera steht am Boden
        pos = Vector((pos.x, pos.y, -alt + pos.z)); ziel = Vector((0, 0, -alt * .45 + 1.0))
    if nr == 9:      # Blick nach unten vom Seil aus: fest
        ziel = Vector(rig.location) + Vector((0, -2.5, -4))
    if nr == 14:     # Kamera steht am Boden (Landung)
        pos = Vector((pos.x, pos.y, -alt + pos.z)); ziel = Vector((0, 0, -alt * .5 + 1.0))
    cam.location = pos; d = ziel - pos; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lin
    cam.data.dof.focus_distance = min(d.length, 5000)
    cam.data.dof.aperture_fstop = 5.6 if d.length < 4 else 16
    cam.location += Vector((.004 * math.sin(t * 9), .003 * math.cos(t * 7), .004 * math.sin(t * 11))) * min(d.length, 10)


HELFER_OBJ = [o for hf in HELFER for o in hf.objekte]
os.makedirs(A.ordner, exist_ok=True)
N = int(round(D * A.fps))
liste = [int(round(float(x) * A.fps)) for x in A.nur.split(",")] if A.nur else list(range(A.start, N))
for f in liste:
    pfad = os.path.join(A.ordner, f"sprung_{f:04d}.png")
    if os.path.exists(pfad) and not A.nur:
        continue
    zustand(f / A.fps); bpy.context.view_layer.update(); zustand(f / A.fps)
    sc.render.filepath = pfad
    bpy.ops.render.render(write_still=True); print("FERTIG", pfad, flush=True)
