# ======================================================================  Kajakfahrer (zuerst): Drytop, Helm
import mensch_echt as ME
PC = ME.mensch("bradt", 44, 1.0, .3, .65, .2, haut="caucasian", haare="short02", braue="eyebrow001", haarfarbe="6b4a2e", schuhe=None)
for o in PC.stiefel:
    o.hide_render = True
ME.trikot(PC, "lang", "tights", "f2b705", "15171b")
for o in PC.huellen:
    if "versatz" in o.modifiers:
        o.modifiers["versatz"].strength = .014 if o.name.endswith("_hemd") else .010
    for md in o.modifiers:
        if md.type == "SUBSURF":
            md.render_levels = 2
hoehe = max(v.z for v in PC.EV); PC.SK = 1.80 / hoehe; PC.rig.scale = (PC.SK,) * 3
PC.PEL = PC.rig.data.bones["upperleg01.L"].head_local.copy(); PC.PEL.x = 0
bpy.context.view_layer.update()
kopf_b = PC.rig.data.bones["head"]
kh = PC.rig.matrix_world @ kopf_b.head_local; kt = PC.rig.matrix_world @ kopf_b.tail_local
kz = kh + (kt - kh) * .55
bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1, location=kz + Vector((0, .012, .03)))
helm = bpy.context.object; helm.name = "helm"; helm.scale = (.118, .132, .118); helm.data.materials.append(mat("helm", "c62828", .3, Coat_Weight=1.0))
bm = bmesh.new(); bm.from_mesh(helm.data)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -.05 and v.co.y < .2], context="VERTS"); bm.to_mesh(helm.data); bm.free()
helm.modifiers.new("d", "SOLIDIFY").thickness = .08
for p in helm.data.polygons:
    p.use_smooth = True
bpy.context.view_layer.update()
PI = (PC.rig.matrix_world @ kopf_b.matrix_local @ Matrix.Translation((0, kopf_b.length, 0))).inverted()
helm.parent = PC.rig; helm.parent_type = "BONE"; helm.parent_bone = "head"; helm.matrix_parent_inverse = PI
print("ok mensch")
