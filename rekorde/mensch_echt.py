"""Echtere Menschen fuer die Rekord-Videos (Loris 24.11.: Figur soll echt aussehen, Details, Fake-Marken erlaubt).
Baut auf mensch_mh.Arbeiter auf und ergaenzt (alles MakeHuman-Systemassets, CC0, /home/claude/assets/mhsys):
  - Haut mit Foto-Textur (young/middleage_<herkunft>_<geschlecht>.mhmat, ENHANCED_SSS)
  - Haare, Augenbrauen, Wimpern als echte MakeHuman-Proxies
  - Sportkleidung ueber weiche Masken (aermellos / kurze Hose) statt zackig geloeschter Vertices
  - Aufdrucke (Fantasie-Marke, Startnummer) als Bild auf Brust/Bein, per Rest-Koordinaten projiziert
Verwendung:
    import mensch_echt as ME
    m = ME.mensch(name, seed, maenn, alter, muskel, gewicht, haut="african", haare="short02", braue="eyebrow001")
    ME.trikot(m, oben="singlet"|"tshirt"|"lang"|None, unten="shorts"|"tights"|"lang", farbe_oben, farbe_unten,
              brust=bildpfad, bein=bildpfad)
"""
import bpy, os, math, importlib, random
from mathutils import Vector
import mensch_mh as MH

SYS = "/home/claude/assets/mhsys"
hexf = MH.hexf


def _hs():
    HS, _ = MH._mpfb()
    return HS


def mensch(name="mensch", seed=1, maenn=1.0, alter=.4, muskel=.6, gewicht=.4, haut="caucasian", haare="short02",
           braue="eyebrow001", wimpern="eyelashes02", haarfarbe="050403", hautalter="young", schuhe="shoes06"):
    m = MH.Arbeiter(name=name, seed=seed, maenn=maenn, alter=alter, muskel=muskel, gewicht=gewicht, haut=haut, weste=False)
    HS = _hs()
    vorher = set(bpy.data.objects)
    geschl = "male" if maenn >= .5 else "female"
    skin = os.path.join(SYS, "skins", f"{hautalter}_{haut}_{geschl}", f"{hautalter}_{haut}_{geschl}.mhmat")
    if os.path.exists(skin):
        HS.set_character_skin(skin, m.koerper, skin_type="ENHANCED_SSS")
    for typ, ordner, nm in (("Eyebrows", "eyebrows", braue), ("Eyelashes", "eyelashes", wimpern), ("Hair", "hair", haare),
                            ("Clothes", "clothes", schuhe)):
        if not nm:
            continue
        p = os.path.join(SYS, ordner, nm, nm + ".mhclo")
        if os.path.exists(p):
            HS.add_mhclo_asset(p, m.koerper, asset_type=typ, subdiv_levels=0)
    neu = [o for o in bpy.data.objects if o not in vorher]
    for o in neu:
        if o.type == "MESH":
            # sicherstellen, dass die Proxies dem Skelett folgen
            if not any(md.type == "ARMATURE" for md in o.modifiers):
                md = o.modifiers.new("arm", "ARMATURE"); md.object = m.rig
            if not o.parent:
                o.parent = m.rig
            if haarfarbe and haare and o.name.endswith(haare):
                _haar_material(o, haarfarbe)
    m.proxies = neu
    m.objekte += neu
    # alte Gesichts-Huelle (eckige Brauen/Bart) und Helm weg
    for o in m.huellen:
        if o.name.endswith("_gesicht"):
            o.hide_render = True
        if o.name.endswith("_hand"):
            o.hide_render = True
    for o in m.helm:
        o.hide_render = True
    if schuhe:
        for o in m.stiefel:
            o.hide_render = True
    m.objekte = [o for o in m.objekte if o.hide_render is False or o.type != "MESH"]
    return m


def _haar_material(o, farbe):
    """Haarkarten: eigene Farbe, Alpha aus der Textur behalten, leichter Glanz."""
    alt = o.active_material
    bilder = [nd.image for nd in alt.node_tree.nodes if nd.type == "TEX_IMAGE" and nd.image] if alt and alt.use_nodes else []
    m = bpy.data.materials.new(o.name + "_haar"); m.use_nodes = True; n = m.node_tree.nodes; l = m.node_tree.links; b = n["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*hexf(farbe), 1); b.inputs["Roughness"].default_value = .5
    b.inputs["Specular IOR Level"].default_value = .25
    diff = next((im for im in bilder if "normal" not in im.name.lower()), None)
    if diff:
        t = n.new("ShaderNodeTexImage"); t.image = diff
        l.new(t.outputs["Alpha"], b.inputs["Alpha"])
        mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"; mx.inputs[0].default_value = .25
        l.new(t.outputs["Color"], mx.inputs[6]); mx.inputs[7].default_value = (*hexf(farbe), 1); l.new(mx.outputs[2], b.inputs["Base Color"])
    o.data.materials.clear(); o.data.materials.append(m)


def _rest(o):
    """Rest-Positionen eines Huellen-Objekts (mit Formschluesseln, ohne Skelett)"""
    zust = [md.show_viewport for md in o.modifiers]
    for md in o.modifiers:
        md.show_viewport = False
    dg = bpy.context.evaluated_depsgraph_get(); oe = o.evaluated_get(dg); me = oe.to_mesh()
    co = [v.co.copy() for v in me.vertices]; oe.to_mesh_clear()
    for md, z in zip(o.modifiers, zust):
        md.show_viewport = z
    return co


def _gruppen_gewicht(o, praefixe):
    idx = {g.index: g.name for g in o.vertex_groups}
    out = []
    for v in o.data.vertices:
        out.append(min(1.0, sum(g.weight for g in v.groups if idx.get(g.group, "").startswith(praefixe))))
    return out


def _sm(x, a, b):
    t = min(1, max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t)


def _farbe(mat, f1, f2=None):
    for nd in mat.node_tree.nodes:
        if nd.type == "MIX" and nd.data_type == "RGBA" and not nd.inputs[6].is_linked:
            nd.inputs[6].default_value = (*hexf(f1), 1); nd.inputs[7].default_value = (*hexf(f2 or f1), 1)
            break


def _aufdruck(o, mat, bild, mitte, breite, hoehe, vorne=True, spiegel_x=False):
    """Bild (PNG mit Alpha) auf die Huelle drucken: Projektion entlang y auf Rest-Koordinaten (rx, rz)."""
    n = mat.node_tree.nodes; l = mat.node_tree.links; b = n["Principled BSDF"]
    ax = n.new("ShaderNodeAttribute"); ax.attribute_name = "rx"
    az = n.new("ShaderNodeAttribute"); az.attribute_name = "rz"
    ay = n.new("ShaderNodeAttribute"); ay.attribute_name = "ry"
    u = n.new("ShaderNodeMath"); u.operation = "MULTIPLY_ADD"; u.inputs[1].default_value = (-1 if spiegel_x else 1) / breite
    u.inputs[2].default_value = .5 - (-1 if spiegel_x else 1) * mitte[0] / breite; l.new(ax.outputs["Fac"], u.inputs[0])
    v = n.new("ShaderNodeMath"); v.operation = "MULTIPLY_ADD"; v.inputs[1].default_value = 1 / hoehe
    v.inputs[2].default_value = .5 - mitte[2] / hoehe; l.new(az.outputs["Fac"], v.inputs[0])
    cx = n.new("ShaderNodeCombineXYZ"); l.new(u.outputs[0], cx.inputs[0]); l.new(v.outputs[0], cx.inputs[1])
    tex = n.new("ShaderNodeTexImage"); tex.image = bpy.data.images.load(bild, check_existing=True); tex.extension = "CLIP"
    tex.interpolation = "Cubic"; l.new(cx.outputs[0], tex.inputs[0])
    seite = n.new("ShaderNodeMath"); seite.operation = "LESS_THAN" if vorne else "GREATER_THAN"
    seite.inputs[1].default_value = mitte[1]; l.new(ay.outputs["Fac"], seite.inputs[0])
    al = n.new("ShaderNodeMath"); al.operation = "MULTIPLY"; l.new(tex.outputs["Alpha"], al.inputs[0]); l.new(seite.outputs[0], al.inputs[1])
    # bestehende Basisfarbe abfangen
    alt = b.inputs["Base Color"].links[0].from_socket if b.inputs["Base Color"].is_linked else None
    mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"
    if alt:
        l.new(alt, mx.inputs[6])
    else:
        mx.inputs[6].default_value = b.inputs["Base Color"].default_value
    l.new(tex.outputs["Color"], mx.inputs[7]); l.new(al.outputs[0], mx.inputs[0]); l.new(mx.outputs[2], b.inputs["Base Color"])


def trikot(m, oben="singlet", unten="shorts", farbe_oben="b3131b", farbe_unten="0d2a6b", brust=None, brust_mass=(.17, .12),
           bein=None, rau=.42):
    """Sportkleidung: Masken der Huellen anpassen (weiche Raender), Farben, Aufdrucke."""
    neck = m.gm("joint-neck")
    knie = m.gm("joint-l-knee")
    for o in m.huellen:
        typ = o.name.rsplit("_", 1)[-1]
        if typ not in ("hemd", "hose"):
            continue
        co = _rest(o)
        for k, nm in ((0, "rx"), (1, "ry"), (2, "rz")):
            a = o.data.attributes.get(nm) or o.data.attributes.new(nm, "FLOAT", "POINT")
            a.data.foreach_set("value", [c[k] for c in co])
        at = o.data.attributes.get(typ)
        if at is None:
            continue
        val = [0.0] * len(o.data.vertices); at.data.foreach_get("value", val)
        if typ == "hemd":
            if oben is None:
                o.hide_render = True; continue
            arm = _gruppen_gewicht(o, ("upperarm", "lowerarm", "wrist", "finger"))
            oberarm = _gruppen_gewicht(o, ("upperarm01",))
            for i, c in enumerate(co):
                if oben == "singlet":
                    w = 1 - _sm(arm[i], .25, .45)
                    # tieferer Halsausschnitt + Armloch-Rundung
                    hals = _sm(math.hypot(c.x * 1.1, (c.z - (neck.z - .02)) * 1.4), .09, .11) if c.z > neck.z - .16 else 1
                    val[i] *= w * hals
                elif oben == "tshirt":
                    unterarm = _gruppen_gewicht(o, ("lowerarm", "wrist", "finger"))[i] if False else 0
                    w = 1 - _sm(arm[i] - oberarm[i] * .55, .25, .45)
                    val[i] *= w
        else:
            unterbein = _gruppen_gewicht(o, ("lowerleg", "foot", "toe"))
            for i, c in enumerate(co):
                if unten == "shorts":
                    val[i] *= _sm(c.z, knie.z + .13, knie.z + .16) * (1 - _sm(unterbein[i], .2, .4))
                elif unten == "tights":
                    val[i] *= _sm(c.z, knie.z - .06, knie.z - .03)
        at.data.foreach_set("value", val)
        mat = o.active_material
        _farbe(mat, farbe_oben if typ == "hemd" else farbe_unten)
        b = mat.node_tree.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = rau; b.inputs["Sheen Weight"].default_value = .3
        if typ == "hemd" and brust:
            _aufdruck(o, mat, brust, (0, neck.y - .02, neck.z - .26), brust_mass[0], brust_mass[1], vorne=True)
        if typ == "hose" and bein:
            hl = m.gm("joint-l-knee")
            _aufdruck(o, mat, bein, (hl.x, knie.y, knie.z + .3), .07, .045, vorne=True)


def logo_bild(pfad, text, farbe=(1, 1, 1), symbol=True, breite=512, hoehe=256, unterzeile=None, hintergrund=None, num=False):
    """Fantasie-Marke / Startnummer als PNG mit Alpha zeichnen."""
    import cairo
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, breite, hoehe); c = cairo.Context(s)
    if hintergrund:
        c.set_source_rgb(*hintergrund); r = 18
        c.new_sub_path(); c.arc(r, r, r, math.pi, 1.5 * math.pi); c.arc(breite - r, r, r, 1.5 * math.pi, 0)
        c.arc(breite - r, hoehe - r, r, 0, .5 * math.pi); c.arc(r, hoehe - r, r, .5 * math.pi, math.pi); c.close_path(); c.fill()
    c.set_source_rgb(*farbe)
    if symbol:      # eigenes Zeichen: zwei schraege Balken (keine echte Marke)
        c.save(); c.translate(breite * .5, hoehe * .3)
        for dx in (-26, 6):
            c.move_to(dx, 30); c.line_to(dx + 22, -30); c.line_to(dx + 38, -30); c.line_to(dx + 16, 30); c.close_path(); c.fill()
        c.restore()
    c.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    gr = hoehe * (.62 if num else .3); c.set_font_size(gr)
    e = c.text_extents(text); y = hoehe * (.62 if num else (.82 if symbol else .6))
    c.move_to(breite / 2 - e.width / 2 - e.x_bearing, y + (e.height / 2 if num else 0)); c.show_text(text)
    if unterzeile:
        c.set_font_size(hoehe * .13); e = c.text_extents(unterzeile)
        c.move_to(breite / 2 - e.width / 2 - e.x_bearing, hoehe * .93); c.show_text(unterzeile)
    s.write_to_png(pfad)
    return pfad
