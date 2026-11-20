"""Realistischer Mensch fuer die 3D-Videos: MakeHuman/MPFB2-Basismensch (CC0) mit Skelett, Augen, Haut,
dazu eigene Kleidung als Huellen (Hemd, Hose, Warnweste, Stiefel, Handschuhe), Helm, Augenbrauen, Bartschatten.
Kleidungsraender ueber geglaettete Vertex-Attribute (Alpha-Maske) statt eckiger Polygonkanten.

    import mensch_mh as MH
    m = MH.Arbeiter(name="fahrer", seed=1)    # baut alles, gibt Objekt mit .rig, .koerper
    m.pose_stehen(); m.pose_sitzen(pedal=.5); m.pose_gehen(phase); ...
    m.rig.location / rotation / parent wie gewohnt
"""
import bpy, bmesh, math, importlib, addon_utils, os, shutil, random
from mathutils import Vector, Matrix

P = math.pi
MPFB_SRC = "/tmp/mpfb2_test/src/mpfb"
MH_DATA = "/tmp/mh/makehuman/data"


def _mpfb():
    ext = bpy.utils.user_resource('EXTENSIONS', path="user_default", create=True)
    if not os.path.exists(os.path.join(ext, "mpfb")):
        shutil.copytree(MPFB_SRC, os.path.join(ext, "mpfb"))
    addon_utils.enable("bl_ext.user_default.mpfb", default_set=True)
    M = "bl_ext.user_default.mpfb."
    return (importlib.import_module(M + "services.humanservice").HumanService,
            importlib.import_module(M + "services.targetservice").TargetService)


def hexf(h):
    return tuple(((int(h[i:i + 2], 16) / 255) ** 2.2) for i in (0, 2, 4))


def _stoff(name, farbe, rau=.85, sheen=.4, skala=380, maske=None, extra=None):
    """Stoff mit Webstruktur; optional Alpha-Maske aus Vertex-Attribut (Wert > .5 sichtbar)."""
    m = bpy.data.materials.new(name); m.use_nodes = True; n = m.node_tree.nodes; l = m.node_tree.links
    b = n["Principled BSDF"]; b.inputs["Base Color"].default_value = (*hexf(farbe), 1); b.inputs["Roughness"].default_value = rau
    b.inputs["Sheen Weight"].default_value = sheen
    tc = n.new("ShaderNodeTexCoord"); wv = n.new("ShaderNodeTexWave"); wv.inputs["Scale"].default_value = skala
    wv.inputs["Distortion"].default_value = .5
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 6; nz.inputs["Detail"].default_value = 6
    l.new(tc.outputs["Object"], wv.inputs["Vector"]); l.new(tc.outputs["Object"], nz.inputs["Vector"])
    bp = n.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = .12; l.new(wv.outputs["Fac"], bp.inputs["Height"])
    bp2 = n.new("ShaderNodeBump"); bp2.inputs["Strength"].default_value = .25; l.new(nz.outputs["Fac"], bp2.inputs["Height"])
    l.new(bp.outputs[0], bp2.inputs["Normal"]); l.new(bp2.outputs[0], b.inputs["Normal"])
    # leichter Schmutz / Abnutzung
    cr = n.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].position = .45; cr.color_ramp.elements[1].position = .75
    l.new(nz.outputs["Fac"], cr.inputs["Fac"])
    mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.inputs[6].default_value = (*hexf(farbe), 1)
    mx.inputs[7].default_value = (*[c * .7 for c in hexf(farbe)], 1); l.new(cr.outputs[0], mx.inputs[0])
    l.new(mx.outputs[2], b.inputs["Base Color"])
    if extra:
        extra(m, n, l, b, mx)
    if maske:
        at = n.new("ShaderNodeAttribute"); at.attribute_name = maske
        st = n.new("ShaderNodeMath"); st.operation = "GREATER_THAN"; st.inputs[1].default_value = .5
        l.new(at.outputs["Fac"], st.inputs[0]); l.new(st.outputs[0], b.inputs["Alpha"])
    return m


class Arbeiter:
    def __init__(self, name="arbeiter", seed=1, maenn=1.0, alter=.5, muskel=.6, gewicht=.55, haut="caucasian", weste=True):
        HS, TS = _mpfb()
        rnd = random.Random(seed)
        vorher = set(bpy.data.objects)
        macro = TS.get_default_macro_info_dict()
        macro.update({"gender": maenn, "age": alter, "muscle": muskel, "weight": gewicht, "height": .5 + rnd.uniform(-.1, .1)})
        rasse = {"asian": .15, "caucasian": .15, "african": .15}; rasse[haut] = .7; macro["race"] = rasse
        h = HS.create_human(macro_detail_dict=macro)
        rig = HS.add_builtin_rig(h, "default")
        HS.add_mhclo_asset(os.path.join(MH_DATA, "eyes/high-poly/high-poly.mhclo"), h, asset_type="Eyes", subdiv_levels=0)
        HS.set_character_skin(None, h, skin_type="LAYERED")
        self.koerper, self.rig, self.name = h, rig, name
        rig.name = name + "_rig"; h.name = name + "_koerper"
        # Ruhepositionen (mit Zielformen, ohne Skelett) fuer Masken
        for m_ in h.modifiers:
            m_.show_viewport = False
        dg = bpy.context.evaluated_depsgraph_get(); he = h.evaluated_get(dg); tm = he.to_mesh()
        EV = [v.co.copy() for v in tm.vertices]; he.to_mesh_clear()
        for m_ in h.modifiers:
            m_.show_viewport = True
        self.EV = EV
        gname = {g.index: g.name for g in h.vertex_groups}
        DEF = {b.name for b in rig.data.bones if b.use_deform}

        def grp_mitte(n):
            gi = h.vertex_groups[n].index; pts = [EV[v.index] for v in h.data.vertices if any(g.group == gi for g in v.groups)]
            return sum(pts, Vector()) / len(pts)
        self.gm = grp_mitte
        neck = grp_mitte("joint-neck"); kopf = grp_mitte("joint-head")
        hl, hr = grp_mitte("joint-l-hand"), grp_mitte("joint-r-hand")
        el, er = grp_mitte("joint-l-elbow"), grp_mitte("joint-r-elbow")
        al, ar = grp_mitte("joint-l-ankle"), grp_mitte("joint-r-ankle")
        pelvis = grp_mitte("joint-pelvis")
        augen = [grp_mitte("joint-l-eye"), grp_mitte("joint-r-eye")]
        mund = grp_mitte("joint-mouth")

        def knochen(i):
            v = h.data.vertices[i]; best, bw = "", 0
            for g in v.groups:
                n_ = gname.get(g.group)
                if n_ in DEF and g.weight > bw:
                    best, bw = n_, g.weight
            return best
        kn = [knochen(i) for i in range(len(EV))]
        gb = h.vertex_groups["body"].index
        IST_KOERPER = [any(g.group == gb and g.weight > .5 for g in v.groups) for v in h.data.vertices]
        for i in range(len(kn)):
            if not IST_KOERPER[i]:
                kn[i] = "__helper"

        def smooth(x, a, b):
            t = min(1, max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t)

        # Masken pro Vertex (0..1): Hemd, Hose, Weste, Stiefel, Handschuh, Brauen, Bart
        M = {k: [0.0] * len(EV) for k in ("hemd", "hose", "weste", "stiefel", "hand", "braue", "bart")}
        for i, c in enumerate(EV):
            b = kn[i]
            if b == "__helper":
                continue
            arm = b.startswith(("upperarm", "lowerarm", "shoulder", "clavicle"))
            hand = b.startswith(("wrist", "finger", "metacarpal"))
            bein = b.startswith(("upperleg", "lowerleg", "pelvis", "foot", "toe"))
            rumpf = b.startswith(("spine", "breast", "clavicle", "shoulder"))
            kopf_frei = 1 - smooth(c.z, neck.z - .07, neck.z - .02)
            hand_d = min((c - hl).length, (c - hr).length)
            if not hand:
                # Hemd: alles oberhalb der Huefte ausser Kopf/Hals und Haende (Aermel bis kurz vor die Hand)
                M["hemd"][i] = smooth(c.z, pelvis.z - .06, pelvis.z - .01) * kopf_frei * smooth(hand_d, .07, .11)
                # Hose: Knoechel bis Hueftguertel
                an = al if c.x > 0 else ar
                if not arm and abs(c.x) < .25:
                    M["hose"][i] = smooth(c.z, an.z + .04, an.z + .09) * (1 - smooth(c.z, pelvis.z + .1, pelvis.z + .15))
            # Handschuhe
            M["hand"][i] = 1.0 if hand else ((1 - smooth(hand_d, .09, .13)) if b.startswith("lowerarm02") else 0)
            # Weste: Rumpf ohne Arme, V-Ausschnitt vorne, Armloecher
            if not b.startswith("lowerarm") and not hand and c.z > pelvis.z + .02 and abs(c.x) < .2:
                vorne = c.y < neck.y
                v_aus = smooth(abs(c.x) - (c.z - (neck.z - .2)) / 2.5, -.004, .02) if vorne else 1
                schulter = 1 - smooth(c.z, neck.z - .035, neck.z - .01)
                armloch = 1 - smooth(abs(c.x), .155, .185) * smooth(c.z, neck.z - .3, neck.z - .25)
                unten = smooth(c.z, pelvis.z + .03, pelvis.z + .08)
                M["weste"][i] = v_aus * schulter * armloch * unten
            # Augenbrauen: Bogen ueber jedem Auge, nur vorne im Gesicht
            for e in augen:
                dx = c.x - e.x; dz = c.z - e.z - .022 - .0
                bogen = dz + (dx * dx) * 8 - (dx * (1 if e.x > 0 else -1)) * .05
                if c.y < e.y + .01 and abs(dx) < .034:
                    M["braue"][i] = max(M["braue"][i], 1 - smooth(abs(bogen), .0035, .0065))
            # Bartschatten: Kiefer, Kinn, Oberlippe
            if c.y < mund.y + .03 and c.z > neck.z + .015 and abs(c.x) < .06:
                kinn = (1 - smooth(c.z, mund.z - .012, mund.z - .004)) * smooth(c.z, neck.z + .015, neck.z + .045)
                lippe = smooth(c.z, mund.z + .006, mund.z + .009) * (1 - smooth(c.z, mund.z + .014, mund.z + .018)) * (1 - smooth(abs(c.x), .02, .03))
                M["bart"][i] = max(kinn, lippe) * (1 - smooth(abs(c.x), .045, .06))
        self.M = M

        def attr(obj, key):
            a = obj.data.attributes.new(key, "FLOAT", "POINT")
            a.data.foreach_set("value", M[key])

        # ---------- Huellen erzeugen (Kopien des Koerpers mit eigenem Versatz)
        def huelle(key, mat, versatz, glatt=6, sub=1, dicke=0.0):
            bpy.ops.object.select_all(action="DESELECT"); h.select_set(True); bpy.context.view_layer.objects.active = h
            bpy.ops.object.duplicate(); o = bpy.context.object; o.name = f"{name}_{key}"
            bm = bmesh.new(); bm.from_mesh(o.data)
            weg = [v for v in bm.verts if v.index < len(EV) and M[key][v.index] < .02]
            bmesh.ops.delete(bm, geom=weg, context="VERTS"); bm.to_mesh(o.data); bm.free()
            # Attribut nach dem Loeschen neu setzen (Indizes haben sich geaendert): ueber Rest-Positionen
            o.data.materials.clear(); o.data.materials.append(mat)
            return o
        # einfacher: Attribute VOR dem Duplizieren auf den Koerper legen, dann wandern sie mit
        for k in M:
            attr(h, k)
        vg = {}
        for k, w in (("hemd", 1), ("hose", 1), ("weste", 1), ("stiefel", 1), ("hand", 1)):
            g = h.vertex_groups.new(name="m_" + k); vg[k] = g
            for i, val in enumerate(M[k]):
                if val > .02:
                    g.add([i], val, "REPLACE")

        def mod_vorne(o, mod):
            o.modifiers.move(o.modifiers.find(mod.name), 0)

        hose_m = _stoff("hose", "2d3340", skala=300, maske="hose")
        hand_m = _stoff("handschuh", "7a7360", rau=.7, skala=500, maske="hand")

        def stiefel_extra(m, n, l, b, mx):
            b.inputs["Roughness"].default_value = .45; b.inputs["Coat Weight"].default_value = .3
        stief_m = _stoff("stiefel", "3b2a1d", rau=.5, sheen=0, skala=120, extra=stiefel_extra)

        def weste_extra(m, n, l, b, mx):
            at = n.new("ShaderNodeAttribute"); at.attribute_name = "rest_z"
            c1 = n.new("ShaderNodeMath"); c1.operation = "COMPARE"; c1.inputs[1].default_value = pelvis.z + .2; c1.inputs[2].default_value = .022
            c2 = n.new("ShaderNodeMath"); c2.operation = "COMPARE"; c2.inputs[1].default_value = pelvis.z + .34; c2.inputs[2].default_value = .022
            l.new(at.outputs["Fac"], c1.inputs[0]); l.new(at.outputs["Fac"], c2.inputs[0])
            mm = n.new("ShaderNodeMath"); mm.operation = "MAXIMUM"; l.new(c1.outputs[0], mm.inputs[0]); l.new(c2.outputs[0], mm.inputs[1])
            c = n.new("ShaderNodeMix"); c.data_type = "RGBA"; l.new(mx.outputs[2], c.inputs[6]); c.inputs[7].default_value = (*hexf("d7dde0"), 1)
            l.new(mm.outputs[0], c.inputs[0]); l.new(c.outputs[2], b.inputs["Base Color"])
            l.new(mm.outputs[0], b.inputs["Metallic"])
            ro = n.new("ShaderNodeMapRange"); ro.inputs["To Min"].default_value = .75; ro.inputs["To Max"].default_value = .2
            l.new(mm.outputs[0], ro.inputs["Value"]); l.new(ro.outputs["Result"], b.inputs["Roughness"])
        weste_m = _stoff("weste", "ff5a0a", rau=.7, skala=220, maske="weste", extra=weste_extra)
        hemd_m = _stoff("hemd", "33415a", maske="hemd")
        if weste:
            # Weste ins Hemd-Material mischen (keine zweite Huelle -> nichts sticht durch)
            n = hemd_m.node_tree.nodes; l = hemd_m.node_tree.links
            out = n["Material Output"]; hb = n["Principled BSDF"]
            wn = weste_m.node_tree; grp = bpy.data.node_groups.new("weste_gruppe", "ShaderNodeTree")
            # einfacher: zweites BSDF mit Westen-Look und Mix ueber Attribut
            wb = n.new("ShaderNodeBsdfPrincipled")
            for k_ in ("Roughness", "Sheen Weight"):
                wb.inputs[k_].default_value = .7 if k_ == "Roughness" else .3
            at = n.new("ShaderNodeAttribute"); at.attribute_name = "rest_z"
            c1 = n.new("ShaderNodeMath"); c1.operation = "COMPARE"; c1.inputs[1].default_value = pelvis.z + .2; c1.inputs[2].default_value = .022
            c2 = n.new("ShaderNodeMath"); c2.operation = "COMPARE"; c2.inputs[1].default_value = pelvis.z + .34; c2.inputs[2].default_value = .022
            l.new(at.outputs["Fac"], c1.inputs[0]); l.new(at.outputs["Fac"], c2.inputs[0])
            mm = n.new("ShaderNodeMath"); mm.operation = "MAXIMUM"; l.new(c1.outputs[0], mm.inputs[0]); l.new(c2.outputs[0], mm.inputs[1])
            cc = n.new("ShaderNodeMix"); cc.data_type = "RGBA"; cc.inputs[6].default_value = (*hexf("ff5a0a"), 1); cc.inputs[7].default_value = (*hexf("d7dde0"), 1)
            l.new(mm.outputs[0], cc.inputs[0]); l.new(cc.outputs[2], wb.inputs["Base Color"]); l.new(mm.outputs[0], wb.inputs["Metallic"])
            l.new(hb.inputs["Normal"].links[0].from_socket, wb.inputs["Normal"])
            aw = n.new("ShaderNodeAttribute"); aw.attribute_name = "weste"
            gt = n.new("ShaderNodeMath"); gt.operation = "GREATER_THAN"; gt.inputs[1].default_value = .5; l.new(aw.outputs["Fac"], gt.inputs[0])
            ms = n.new("ShaderNodeMixShader"); l.new(gt.outputs[0], ms.inputs[0]); l.new(hb.outputs[0], ms.inputs[1]); l.new(wb.outputs[0], ms.inputs[2])
            # Alpha: Hemd-Maske gilt fuer beide
            l.new(hb.inputs["Alpha"].links[0].from_socket, wb.inputs["Alpha"])
            l.new(ms.outputs[0], out.inputs["Surface"])
        rz = h.data.attributes.new("rest_z", "FLOAT", "POINT"); rz.data.foreach_set("value", [c.z for c in EV])

        self.huellen = []
        for key, mat_, vers, glatt in (("hemd", hemd_m, .009, 4), ("hose", hose_m, .016, 6), ("hand", hand_m, .004, 2)):
            if key == "weste" and not weste:
                continue
            bpy.ops.object.select_all(action="DESELECT"); h.select_set(True); bpy.context.view_layer.objects.active = h
            bpy.ops.object.duplicate(); o = bpy.context.object; o.name = f"{name}_{key}"
            bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
            weg = [v for v in bm.verts if v.index >= len(EV) or M[key][v.index] < .02]
            bmesh.ops.delete(bm, geom=weg, context="VERTS"); bm.to_mesh(o.data); bm.free()
            o.data.materials.clear(); o.data.materials.append(mat_)
            for m_ in list(o.modifiers):
                if m_.type == "MASK":
                    o.modifiers.remove(m_)
            d = o.modifiers.new("versatz", "DISPLACE"); d.strength = vers; d.mid_level = 0; mod_vorne(o, d)
            if glatt:
                cs = o.modifiers.new("glatt", "CORRECTIVE_SMOOTH"); cs.iterations = glatt; cs.smooth_type = "LENGTH_WEIGHTED"
                o.modifiers.move(o.modifiers.find("glatt"), 1)
            if key in ("weste", "hose", "hemd"):
                sm = o.modifiers.new("rund", "SMOOTH"); sm.factor = .5; sm.iterations = {"weste": 8, "hose": 4, "hemd": 3}[key]
                o.modifiers.move(o.modifiers.find("rund"), 1)
            if key == "stiefel":
                sm = o.modifiers.new("rund", "SMOOTH"); sm.factor = .9; sm.iterations = 6; o.modifiers.move(o.modifiers.find("rund"), 1)
            sd = o.modifiers.new("sub", "SUBSURF"); sd.levels = 1; sd.render_levels = 1
            if key in ("weste",):
                so = o.modifiers.new("dicke", "SOLIDIFY"); so.thickness = .004
            for p in o.data.polygons:
                p.use_smooth = True
            self.huellen.append(o)
        # Gesichtsueberzug fuer Augenbrauen + Bart (transparent ausser Maske)
        bpy.ops.object.select_all(action="DESELECT"); h.select_set(True); bpy.context.view_layer.objects.active = h
        bpy.ops.object.duplicate(); fo = bpy.context.object; fo.name = f"{name}_gesicht"
        bm = bmesh.new(); bm.from_mesh(fo.data)
        weg = [v for v in bm.verts if v.index >= len(EV) or (M["braue"][v.index] < .01 and M["bart"][v.index] < .01)]
        bmesh.ops.delete(bm, geom=weg, context="VERTS"); bm.to_mesh(fo.data); bm.free()
        fm = bpy.data.materials.new("haare"); fm.use_nodes = True; n = fm.node_tree.nodes; l = fm.node_tree.links; b = n["Principled BSDF"]
        haar = hexf(rnd.choice(["2a1c12", "3b2a1c", "151210", "4a3624"]))
        b.inputs["Base Color"].default_value = (*haar, 1); b.inputs["Roughness"].default_value = .6
        a1 = n.new("ShaderNodeAttribute"); a1.attribute_name = "braue"; a2 = n.new("ShaderNodeAttribute"); a2.attribute_name = "bart"
        tc = n.new("ShaderNodeTexCoord"); nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 900; nz.inputs["Detail"].default_value = 2
        l.new(tc.outputs["Object"], nz.inputs["Vector"])
        st = n.new("ShaderNodeMath"); st.operation = "GREATER_THAN"; st.inputs[1].default_value = .48; l.new(nz.outputs["Fac"], st.inputs[0])
        bb = n.new("ShaderNodeMath"); bb.operation = "MULTIPLY"; l.new(a1.outputs["Fac"], bb.inputs[0]); l.new(st.outputs[0], bb.inputs[1])
        bt = n.new("ShaderNodeMath"); bt.operation = "MULTIPLY"; bt.inputs[1].default_value = .35 * rnd.uniform(.6, 1.2)
        bt2 = n.new("ShaderNodeMath"); bt2.operation = "MULTIPLY"; l.new(a2.outputs["Fac"], bt2.inputs[0]); l.new(st.outputs[0], bt2.inputs[1])
        l.new(bt2.outputs[0], bt.inputs[0])
        mm = n.new("ShaderNodeMath"); mm.operation = "MAXIMUM"; l.new(bb.outputs[0], mm.inputs[0]); l.new(bt.outputs[0], mm.inputs[1])
        l.new(mm.outputs[0], b.inputs["Alpha"])
        fo.data.materials.clear(); fo.data.materials.append(fm)
        for m_ in list(fo.modifiers):
            if m_.type == "MASK":
                fo.modifiers.remove(m_)
        d = fo.modifiers.new("versatz", "DISPLACE"); d.strength = .0012; d.mid_level = 0; mod_vorne(fo, d)
        self.huellen.append(fo)
        # Koerper selbst: Kleidungsbereiche leicht nach innen, damit nichts durchsticht
        kv = h.vertex_groups.new(name="unter_kleid")
        for i in range(len(EV)):
            w = max(M["hemd"][i], M["hose"][i], M["stiefel"][i], M["hand"][i])
            if w > .02:
                kv.add([i], w, "REPLACE")
        fg = h.vertex_groups.new(name="fuss_weg")
        fg.add([i for i in range(len(EV)) if kn[i].startswith(("foot", "toe"))], 1.0, "REPLACE")
        mk = h.modifiers.new("fuesse", "MASK"); mk.vertex_group = "fuss_weg"; mk.invert_vertex_group = True
        d = h.modifiers.new("innen", "DISPLACE"); d.strength = -.003; d.mid_level = 0; d.vertex_group = "unter_kleid"; mod_vorne(h, d)
        # ---------- Stiefel: abgerundete Schale am Fussknochen + Schaft
        self.stiefel = []
        for sd_, an in (("L", al), ("R", ar)):
            fus = [EV[i] for i in range(len(EV)) if kn[i].startswith(("foot." + sd_, "toe")) and ((EV[i].x > 0) == (an.x > 0))]
            mnf = Vector((min(c.x for c in fus), min(c.y for c in fus), 0)); mxf = Vector((max(c.x for c in fus), max(c.y for c in fus), max(c.z for c in fus)))
            bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
            me = bpy.data.meshes.new("stiefel"); bm.to_mesh(me); bm.free()
            o = bpy.data.objects.new(f"{name}_stiefel_{sd_}", me); bpy.context.scene.collection.objects.link(o)
            o.scale = ((mxf.x - mnf.x) + .035, (mxf.y - mnf.y) + .04, an.z + .05)
            o.location = ((mnf.x + mxf.x) / 2, (mnf.y + mxf.y) / 2 - .005, (an.z + .05) / 2)
            ss = o.modifiers.new("sub", "SUBSURF"); ss.levels = 3; ss.render_levels = 3
            me.materials.append(stief_m)
            for p in me.polygons:
                p.use_smooth = True
            bpy.ops.mesh.primitive_cylinder_add(radius=.062, depth=.2, vertices=32, location=(an.x, an.y + .005, an.z + .07)); sch = bpy.context.object
            sch.name = f"{name}_schaft_{sd_}"; sch.scale = (1, 1.15, 1); sch.data.materials.append(stief_m)
            bv = sch.modifiers.new("b", "BEVEL"); bv.width = .01; bv.segments = 3
            for p in sch.data.polygons:
                p.use_smooth = True
            bpy.ops.mesh.primitive_cube_add(size=1, location=((mnf.x + mxf.x) / 2, (mnf.y + mxf.y) / 2 - .005, .012)); so_ = bpy.context.object
            so_.name = f"{name}_sohle_{sd_}"; so_.scale = ((mxf.x - mnf.x) + .04, (mxf.y - mnf.y) + .035, .024)
            sohle_m = bpy.data.materials.get("sohle") or bpy.data.materials.new("sohle"); sohle_m.diffuse_color = (.02, .02, .02, 1)
            sohle_m.use_nodes = True
            if True:
                sohle_m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (.025, .022, .02, 1); sohle_m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = .8
            so_.data.materials.append(sohle_m)
            bv = so_.modifiers.new("b", "BEVEL"); bv.width = .008; bv.segments = 2
            bpy.context.view_layer.update()
            for o_, bone in ((o, "foot." + sd_), (so_, "foot." + sd_), (sch, "lowerleg02." + sd_)):
                bn_ = rig.data.bones[bone]
                o_.parent = rig; o_.parent_type = "BONE"; o_.parent_bone = bone
                o_.matrix_parent_inverse = (rig.matrix_world @ bn_.matrix_local @ Matrix.Translation((0, bn_.length, 0))).inverted()
                self.stiefel.append(o_)
        # ---------- Helm am Kopfknochen
        gi = h.vertex_groups["scalp"].index
        zs = [EV[v.index] for v in h.data.vertices if any(g.group == gi for g in v.groups)]
        mn = Vector((min(c.x for c in zs), min(c.y for c in zs), min(c.z for c in zs)))
        mxv = Vector((max(c.x for c in zs), max(c.y for c in zs), max(c.z for c in zs)))
        mid = (mn + mxv) / 2; sx = (mxv.x - mn.x) / 2 + .022; sy = (mxv.y - mn.y) / 2 + .026
        helm_m = bpy.data.materials.new("helm"); helm_m.use_nodes = True; b = helm_m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*hexf(rnd.choice(["f4f4f0", "f2c200", "f4f4f0"])), 1); b.inputs["Roughness"].default_value = .28
        b.inputs["Coat Weight"].default_value = .5
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=1)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -.02], context="VERTS")
        me = bpy.data.meshes.new("helm"); bm.to_mesh(me); bm.free()
        helm = bpy.data.objects.new(name + "_helm", me); bpy.context.scene.collection.objects.link(helm); me.materials.append(helm_m)
        for p in me.polygons:
            p.use_smooth = True
        helm.scale = (sx, sy, .1); helm.location = (mid.x, mid.y + .006, mxv.z - .078)
        so = helm.modifiers.new("s", "SOLIDIFY"); so.thickness = .012
        bv = helm.modifiers.new("b", "BEVEL"); bv.width = .004; bv.segments = 2
        bpy.ops.mesh.primitive_cylinder_add(radius=1, depth=1, vertices=64, location=(mid.x, mid.y - .03, mxv.z - .075)); kr = bpy.context.object
        kr.scale = (sx + .018, sy + .045, .005); kr.data.materials.append(helm_m); kr.name = name + "_krempe"
        bv = kr.modifiers.new("b", "BEVEL"); bv.width = .002; bv.segments = 2
        bpy.context.view_layer.update()
        bn = rig.data.bones["head"]
        PI = (rig.matrix_world @ bn.matrix_local @ Matrix.Translation((0, bn.length, 0))).inverted()
        for o in (helm, kr):
            o.parent = rig; o.parent_type = "BONE"; o.parent_bone = "head"; o.matrix_parent_inverse = PI
        self.helm = [helm, kr]
        self.objekte = [o for o in bpy.data.objects if o not in vorher]
        for pb in rig.pose.bones:
            pb.rotation_mode = "XYZ"

    # ---------- Posen (Knochen-Drehungen; Achsen am Standard-Rig ausgemessen)
    def zuruecksetzen(self):
        for pb in self.rig.pose.bones:
            pb.rotation_euler = (0, 0, 0); pb.location = (0, 0, 0)

    def dreh(self, bone, x=0, y=0, z=0):
        self.rig.pose.bones[bone].rotation_euler = (x, y, z)

    def sichtbar(self, ja):
        for o in self.objekte:
            o.hide_render = not ja
