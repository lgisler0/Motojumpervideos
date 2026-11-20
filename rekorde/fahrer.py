"""Prozeduraler Mensch (Minenarbeiter) fuer Blender: Skin-Modifier-Koerper, Kopf mit Gesicht, Helm, Warnweste.
Posen ueber Gelenkwinkel: stehen, gehen, steigen, sitzen. Person blickt in lokale +x Richtung."""
import bpy, bmesh, math
from mathutils import Vector, Matrix

P = math.pi


def _mat(name, farbe, rau=.5, leucht=0, metall=0):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*farbe, 1); b.inputs["Roughness"].default_value = rau; b.inputs["Metallic"].default_value = metall
    if leucht:
        b.inputs["Emission Color"].default_value = (*farbe, 1); b.inputs["Emission Strength"].default_value = leucht
    return m, b


def hexf(h):
    return tuple(((int(h[i:i + 2], 16) / 255) ** 2.2) for i in (0, 2, 4))


def _weste_mat():
    m = bpy.data.materials.new("weste"); m.use_nodes = True; n = m.node_tree.nodes; l = m.node_tree.links; b = n["Principled BSDF"]
    tc = n.new("ShaderNodeTexCoord"); sp = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Object"], sp.inputs[0])
    # Reflexstreifen: zwei waagrechte Baender (Objekt-z, Rumpf von 0.95..1.5)
    w1 = n.new("ShaderNodeMath"); w1.operation = "COMPARE"; w1.inputs[1].default_value = 1.12; w1.inputs[2].default_value = .025
    w2 = n.new("ShaderNodeMath"); w2.operation = "COMPARE"; w2.inputs[1].default_value = 1.30; w2.inputs[2].default_value = .025
    l.new(sp.outputs["Z"], w1.inputs[0]); l.new(sp.outputs["Z"], w2.inputs[0])
    mx = n.new("ShaderNodeMath"); mx.operation = "MAXIMUM"; l.new(w1.outputs[0], mx.inputs[0]); l.new(w2.outputs[0], mx.inputs[1])
    c = n.new("ShaderNodeMix"); c.data_type = "RGBA"; c.inputs[6].default_value = (*hexf("ff6a10"), 1); c.inputs[7].default_value = (*hexf("d8dde0"), 1)
    l.new(mx.outputs[0], c.inputs[0]); l.new(c.outputs[2], b.inputs["Base Color"])
    r = n.new("ShaderNodeMapRange"); r.inputs["To Min"].default_value = .75; r.inputs["To Max"].default_value = .25
    l.new(mx.outputs[0], r.inputs["Value"]); l.new(r.outputs["Result"], b.inputs["Roughness"])
    m2 = n.new("ShaderNodeMath"); m2.operation = "MULTIPLY"; m2.inputs[1].default_value = 1.5; l.new(mx.outputs[0], m2.inputs[0])
    b.inputs["Emission Color"].default_value = (1, 1, 1, 1); l.new(m2.outputs[0], b.inputs["Emission Strength"])
    return m


# Gelenkliste und Glieder (Kanten), mit Hautradien
GELENKE = ["becken", "bauch", "brust", "hals", "s_l", "s_r", "e_l", "e_r", "h_l", "h_r",
           "hu_l", "hu_r", "k_l", "k_r", "f_l", "f_r", "z_l", "z_r"]
TEILE = {
    "rumpf": ([("becken", "bauch"), ("bauch", "brust"), ("brust", "hals"), ("brust", "s_l"), ("brust", "s_r")],
              {"becken": (.15, .11), "bauch": (.145, .105), "brust": (.165, .115), "hals": (.058, .058), "s_l": (.07, .07), "s_r": (.07, .07)}, "weste"),
    "arme": ([("s_l", "e_l"), ("e_l", "h_l"), ("s_r", "e_r"), ("e_r", "h_r")],
             {"s_l": (.065, .065), "e_l": (.052, .052), "h_l": (.045, .045), "s_r": (.065, .065), "e_r": (.052, .052), "h_r": (.045, .045)}, "hemd"),
    "beine": ([("becken", "hu_l"), ("hu_l", "k_l"), ("k_l", "f_l"), ("becken", "hu_r"), ("hu_r", "k_r"), ("k_r", "f_r")],
              {"becken": (.11, .09), "hu_l": (.085, .085), "k_l": (.065, .065), "f_l": (.055, .055), "hu_r": (.085, .085), "k_r": (.065, .065), "f_r": (.055, .055)}, "hose"),
    "schuhe": ([("f_l", "z_l"), ("f_r", "z_r")], {"f_l": (.065, .055), "z_l": (.05, .04), "f_r": (.065, .055), "z_r": (.05, .04)}, "schuh"),
}


class Fahrer:
    def __init__(self, sc, name="fahrer"):
        self.sc = sc
        self.root = bpy.data.objects.new(name, None); sc.collection.objects.link(self.root)
        mats = {"weste": _weste_mat(), "hemd": _mat("hemd", hexf("27324a"), .8)[0], "hose": _mat("hose", hexf("1e2533"), .85)[0],
                "schuh": _mat("schuh", hexf("2a1e16"), .6)[0]}
        haut, _ = _mat("haut", hexf("c98f6b"), .5)
        b = haut.node_tree.nodes["Principled BSDF"]; b.inputs["Subsurface Weight"].default_value = .25
        b.inputs["Subsurface Radius"].default_value = (.4, .15, .08)
        self.teile = {}
        for tn, (kanten, radien, mn) in TEILE.items():
            namen = sorted({a for k in kanten for a in k}, key=GELENKE.index)
            me = bpy.data.meshes.new(tn); bm = bmesh.new(); vs = {g: bm.verts.new((0, 0, 0)) for g in namen}
            for a, c in kanten:
                bm.edges.new((vs[a], vs[c]))
            bm.to_mesh(me); bm.free()
            o = bpy.data.objects.new(tn, me); sc.collection.objects.link(o); o.parent = self.root
            sk = o.modifiers.new("skin", "SKIN"); sk.use_smooth_shade = True
            sd = o.modifiers.new("sub", "SUBSURF"); sd.levels = 2; sd.render_levels = 2
            for i, g in enumerate(namen):
                me.skin_vertices[0].data[i].radius = radien[g]
            me.skin_vertices[0].data[0].use_root = True
            me.materials.append(mats[mn]); self.teile[tn] = (o, namen)
        # Kopf (mit Gesicht), Helm, Haende
        self.kopf = bpy.data.objects.new("kopf", None); sc.collection.objects.link(self.kopf); self.kopf.parent = self.root
        bpy.ops.mesh.primitive_uv_sphere_add(radius=.1, segments=32, ring_count=16, location=(0, 0, 0))
        k = bpy.context.object; k.scale = (1.0, .88, 1.15); k.parent = self.kopf; k.data.materials.append(haut)
        for p in k.data.polygons:
            p.use_smooth = True
        auge, _ = _mat("auge", hexf("101010"), .2)
        for s in (-1, 1):
            bpy.ops.mesh.primitive_uv_sphere_add(radius=.012, location=(.088, s * .035, .02)); a = bpy.context.object; a.parent = self.kopf; a.data.materials.append(auge)
            bpy.ops.mesh.primitive_cube_add(size=1, location=(.09, s * .036, .048)); bb = bpy.context.object; bb.scale = (.01, .03, .007)
            bb.parent = self.kopf; bb.data.materials.append(mats["schuh"])
            bpy.ops.mesh.primitive_uv_sphere_add(radius=.025, location=(0, s * .088, 0)); oh = bpy.context.object; oh.scale = (.6, .4, 1)
            oh.parent = self.kopf; oh.data.materials.append(haut)
        bpy.ops.mesh.primitive_cone_add(radius1=.022, radius2=.008, depth=.04, location=(.105, 0, -.005), rotation=(0, P / 2, 0))
        n_ = bpy.context.object; n_.parent = self.kopf; n_.data.materials.append(haut)
        helm, _ = _mat("helm", hexf("f4f4f0"), .25)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=.125, segments=32, ring_count=16, location=(0, 0, .04)); h = bpy.context.object
        h.scale = (1.1, 1.0, .85); h.parent = self.kopf; h.data.materials.append(helm)
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=1)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -.05], context="VERTS"); bm.to_mesh(h.data); bm.free()
        for p in h.data.polygons:
            p.use_smooth = True
        h.scale = (.135, .125, .11)
        bpy.ops.mesh.primitive_cylinder_add(radius=1, depth=1, location=(.03, 0, .035)); kr = bpy.context.object
        kr.scale = (.165, .14, .008); kr.parent = self.kopf; kr.data.materials.append(helm)
        hand, _ = _mat("handschuh", hexf("5c5a52"), .8)
        self.haende = []
        for s in "lr":
            bpy.ops.mesh.primitive_uv_sphere_add(radius=.045, location=(0, 0, 0)); hd = bpy.context.object; hd.scale = (1.1, .7, 1.3)
            hd.parent = self.root; hd.data.materials.append(hand); self.haende.append((s, hd))
            for p in hd.data.polygons:
                p.use_smooth = True
        self.objs = [o for o, _ in self.teile.values()] + [self.kopf] + [hd for _, hd in self.haende] + list(self.kopf.children)

    def sichtbar(self, ja):
        for o in self.objs:
            o.hide_render = not ja

    # ---------- Posen: Gelenke in lokalen Koordinaten (x vorne, y links, z oben)
    @staticmethod
    def pose(art="stehen", ph=0.0, sitz=0.0, pedal=0.0, blick=0.0, arme_vorne=0.0):
        """art: stehen, gehen (ph=Phase 0..1), steigen (Treppe), sitzen. Rueckgabe: dict Gelenk->Vector."""
        J = {}
        OS, US, FH = .44, .43, .08   # Ober-/Unterschenkel, Fusshoehe
        becken_z = .95
        hw = {}
        for s, sy in (("l", 1), ("r", -1)):
            ph_s = ph + (0 if s == "l" else .5)
            a = 2 * P * ph_s
            if art == "gehen":
                hip = .38 * math.sin(a); knie = .55 * max(0, math.sin(a + 1.2)) + .08
            elif art == "steigen":
                hip = .55 * (.5 + .5 * math.sin(a)); knie = 1.0 * (.5 + .5 * math.sin(a + .6)) + .1
            elif art == "sitzen":
                hip = P / 2 * .95; knie = P / 2 * .95 - (pedal * .45 if s == "r" else 0)
            else:
                hip = 0; knie = .04
            hw[s] = (hip, knie, sy)
        if art == "sitzen":
            becken_z = .55
        for s in "lr":
            hip, knie, sy = hw[s]
            hu = Vector((0, sy * .1, becken_z - .04))
            k = hu + Vector((math.sin(hip) * OS, 0, -math.cos(hip) * OS))
            ka = hip - knie
            f = k + Vector((math.sin(ka) * US, 0, -math.cos(ka) * US))
            z = f + Vector((.17, 0, -.04))
            J["hu_" + s], J["k_" + s], J["f_" + s], J["z_" + s] = hu, k, f, z
        if art in ("gehen", "steigen"):
            # Becken so heben, dass der tiefere Fuss den Boden beruehrt
            tief = min(J["f_l"].z, J["f_r"].z) - FH
            for kk in list(J):
                J[kk] = J[kk] - Vector((0, 0, tief))
            becken_z -= tief
        vorn = .08 if art == "steigen" else (.03 if art == "gehen" else 0)
        J["becken"] = Vector((0, 0, becken_z))
        J["bauch"] = Vector((vorn * .5, 0, becken_z + .22))
        J["brust"] = Vector((vorn, 0, becken_z + .45))
        J["hals"] = Vector((vorn * 1.1, 0, becken_z + .66))
        kopf = Vector((vorn * 1.2 + .01, 0, becken_z + .79))
        for s, sy in (("l", 1), ("r", -1)):
            sch = J["brust"] + Vector((0, sy * .19, .1))
            a = 2 * P * (ph + (.5 if s == "l" else 0))
            schw = .35 * math.sin(a) if art in ("gehen", "steigen") else 0
            if art == "sitzen" or arme_vorne:
                ob = Vector((.18, sy * .03, -.2)); un = Vector((.26, -sy * .05, .06))
            else:
                ob = Vector((math.sin(schw) * .3, sy * .04, -math.cos(schw) * .3))
                un = Vector((math.sin(schw + .25) * .27, 0, -math.cos(schw + .25) * .27))
            J["s_" + s] = sch; J["e_" + s] = sch + ob; J["h_" + s] = sch + ob + un
        J["_kopf"] = kopf
        J["_blick"] = blick
        return J

    def setze(self, J, ort, richtung=0.0):
        self.root.location = Vector(ort); self.root.rotation_euler = (0, 0, richtung)
        for o, namen in self.teile.values():
            for i, g in enumerate(namen):
                o.data.vertices[i].co = J[g]
            o.data.update()
        self.kopf.location = J["_kopf"]; self.kopf.rotation_euler = (0, -J["_blick"], 0)
        for s, hd in self.haende:
            hd.location = J["h_" + s] + Vector((.03, 0, -.03))
