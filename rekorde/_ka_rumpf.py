# ======================================================================  Schwimmer (zuerst): Badehose, Kappe, Brille
import mensch_echt as ME
LOGO = ME.logo_bild(os.path.join(HIER, "_logo_norda.png"), "NORDA", farbe=(1, 1, 1))
PC = ME.mensch("waschburger", 58, 1.0, .45, .7, .2, haut="caucasian", haare=None, braue="eyebrow001", haarfarbe="3a2a1e", schuhe=None)
for o in PC.stiefel:
    o.hide_render = True
ME.trikot(PC, None, "shorts", "111111", "14181f", bein=LOGO)
for o in PC.huellen:
    if "versatz" in o.modifiers:
        o.modifiers["versatz"].strength = .008
    for md in o.modifiers:
        if md.type == "SUBSURF":
            md.render_levels = 2
hoehe = max(v.z for v in PC.EV); PC.SK = 1.86 / hoehe; PC.rig.scale = (PC.SK,) * 3
PC.PEL = PC.rig.data.bones["upperleg01.L"].head_local.copy(); PC.PEL.x = 0
# Kappe + Schwimmbrille am Kopf-Knochen
bpy.context.view_layer.update()
kopf_b = PC.rig.data.bones["head"]
kh = PC.rig.matrix_world @ kopf_b.head_local; kt = PC.rig.matrix_world @ kopf_b.tail_local
kz = kh + (kt - kh) * .55
bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1, location=kz + Vector((0, .015, .035)))
kappe = bpy.context.object; kappe.name = "kappe"; kappe.scale = (.103, .117, .104); kappe.data.materials.append(mat("kappe", "f5c400", .35, Coat_Weight=.6))
bm = bmesh.new(); bm.from_mesh(kappe.data)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -.25 or (v.co.z < .15 and v.co.y < -.55)], context="VERTS"); bm.to_mesh(kappe.data); bm.free()
for p in kappe.data.polygons:
    p.use_smooth = True
BR_M = mat("brillenglas", "1a3a6a", .05, metal=.9, Coat_Weight=1)
brille = []
for sx in (-1, 1):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=10, radius=1, location=kz + Vector((sx * .034, -.098, -.018)))
    g_ = bpy.context.object; g_.name = "brille"; g_.scale = (.019, .011, .013); g_.data.materials.append(BR_M)
    for p in g_.data.polygons:
        p.use_smooth = True
    brille.append(g_)
bpy.ops.mesh.primitive_torus_add(major_radius=.103, minor_radius=.004, location=kz + Vector((0, .0, -.018)))
band = bpy.context.object; band.name = "brillenband"; band.scale = (1, 1.1, 1); band.data.materials.append(mat("band", "111111", .7))
bpy.context.view_layer.update()
PI = (PC.rig.matrix_world @ kopf_b.matrix_local @ Matrix.Translation((0, kopf_b.length, 0))).inverted()
for o in [kappe, band] + brille:
    o.parent = PC.rig; o.parent_type = "BONE"; o.parent_bone = "head"; o.matrix_parent_inverse = PI
print("ok mensch")
