# ======================================================================  Speedskifahrer (zuerst): Latexanzug, Aero-Helm
import mensch_echt as ME
LOGO = ME.logo_bild(os.path.join(HIER, "_logo_norda.png"), "NORDA", farbe=(1, 1, 1))
BIB = ME.logo_bild(os.path.join(HIER, "_bib_sk.png"), "3", farbe=(.05, .05, .05), symbol=False, hintergrund=(.97, .97, .95), num=True, unterzeile="VARS", breite=512, hoehe=256)
PC = ME.mensch("billy", 23, 1.0, .35, .7, .22, haut="caucasian", haare="short02", braue="eyebrow001", haarfarbe="3a2a1e", schuhe=None)
for o in PC.stiefel:
    o.hide_render = False          # Skischuhe (Stiefel-Huelle) bleiben sichtbar
ME.trikot(PC, "lang", "tights", "1d4fd8", "1d4fd8", brust=BIB, brust_mass=(.16, .11), bein=LOGO, rau=.18)
for o in PC.huellen:
    if "versatz" in o.modifiers:
        o.modifiers["versatz"].strength = .009
    for md in o.modifiers:
        if md.type == "SUBSURF":
            md.render_levels = 2
hoehe = max(v.z for v in PC.EV); PC.SK = 1.82 / hoehe; PC.rig.scale = (PC.SK,) * 3
PC.PEL = PC.rig.data.bones["upperleg01.L"].head_local.copy(); PC.PEL.x = 0
bpy.context.view_layer.update()
kopf_b = PC.rig.data.bones["head"]
kh = PC.rig.matrix_world @ kopf_b.head_local; kt = PC.rig.matrix_world @ kopf_b.tail_local
kz = kh + (kt - kh) * .55
# Aero-Helm: tropfenfoermig nach hinten verlaengert, dunkles Visier vorne
bm = bmesh.new()
bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=20, radius=1)
for v in bm.verts:
    y = v.co.y
    if y > 0:
        v.co.y = y * (1 + .75 * y)          # Schweif nach hinten
        v.co.z *= (1 - .3 * y * y)
me_h = bpy.data.meshes.new("aerohelm"); bm.to_mesh(me_h); bm.free()
helm = bpy.data.objects.new("aerohelm", me_h); sc.collection.objects.link(helm)
helm.location = kz + Vector((0, .02, .025)); helm.scale = (.122, .13, .128)
helm.data.materials.append(mat("helm", "d91e2a", .15, Coat_Weight=1.0))
for p in me_h.polygons:
    p.use_smooth = True
bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1, location=kz + Vector((0, -.07, -.005)))
visier = bpy.context.object; visier.name = "visier"; visier.scale = (.105, .07, .07); visier.data.materials.append(mat("visier", "15181e", .04, metal=.8, Coat_Weight=1))
for p in visier.data.polygons:
    p.use_smooth = True
bpy.context.view_layer.update()
PI = (PC.rig.matrix_world @ kopf_b.matrix_local @ Matrix.Translation((0, kopf_b.length, 0))).inverted()
for o in (helm, visier):
    o.parent = PC.rig; o.parent_type = "BONE"; o.parent_bone = "head"; o.matrix_parent_inverse = PI
print("ok mensch")
