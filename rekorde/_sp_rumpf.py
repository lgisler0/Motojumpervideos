# ======================================================================  Werfer (zuerst)
import mensch_echt as ME
LOGO = ME.logo_bild(os.path.join(HIER, "_logo_norda.png"), "NORDA", farbe=(1, 1, 1))
BIB = ME.logo_bild(os.path.join(HIER, "_bib_sp.png"), "7", farbe=(.05, .05, .05), symbol=False, hintergrund=(.97, .97, .95), num=True, unterzeile="JENA 96")
PC = ME.mensch("zelezny", 31, 1.0, .5, .75, .25, haut="caucasian", haare="short02", braue="eyebrow001", haarfarbe="4a3426")
ME.trikot(PC, "singlet", "tights", "f2f2f2", "1f2a44", brust=BIB, brust_mass=(.16, .11), bein=LOGO)
for o in PC.huellen:
    if "versatz" in o.modifiers:
        o.modifiers["versatz"].strength = .017 if o.name.endswith("_hemd") else .010
    for md in o.modifiers:
        if md.type == "SUBSURF":
            md.render_levels = 2
hoehe = max(v.z for v in PC.EV); PC.SK = 1.85 / hoehe; PC.rig.scale = (PC.SK,) * 3
PC.PEL = PC.rig.data.bones["upperleg01.L"].head_local.copy(); PC.PEL.x = 0
print("ok mensch")
