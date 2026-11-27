# ======================================================================  Laeufer (zuerst)
import mensch_echt as ME
LOGO = ME.logo_bild(os.path.join(HIER, "_logo_norda.png"), "NORDA", farbe=(1, 1, 1))
BIB = ME.logo_bild(os.path.join(HIER, "_bib_tr.png"), "1", farbe=(.05, .05, .05), symbol=False, hintergrund=(.97, .97, .95), num=True, unterzeile="RUN-UP")
PC = ME.mensch("crake", 76, 1.0, .45, .65, .15, haut="caucasian", haare="short02", braue="eyebrow001", haarfarbe="6b4a2e")
ME.trikot(PC, "singlet", "shorts", "1565c0", "15171b", brust=BIB, brust_mass=(.16, .11), bein=LOGO)
for o in PC.huellen:
    if "versatz" in o.modifiers:
        o.modifiers["versatz"].strength = .017 if o.name.endswith("_hemd") else .010
    for md in o.modifiers:
        if md.type == "SUBSURF":
            md.render_levels = 2
hoehe = max(v.z for v in PC.EV); PC.SK = 1.76 / hoehe; PC.rig.scale = (PC.SK,) * 3
PC.PEL = PC.rig.data.bones["upperleg01.L"].head_local.copy(); PC.PEL.x = 0
print("ok mensch")
