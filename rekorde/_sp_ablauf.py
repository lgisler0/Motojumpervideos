# ======================================================================  IK (Arme mit pole -P/2: Ellbogen natuerlich)
KF = PC
KF.Z = {nm: leer("kf_ik_" + nm) for nm in ("hand_L", "hand_R", "fuss_L", "fuss_R", "knie_L", "knie_R", "ell_L", "ell_R")}
KF.IK = {}
for bone, ziel, pol, pw in (("lowerarm02.L", "hand_L", "ell_L", -P / 2), ("lowerarm02.R", "hand_R", "ell_R", -P / 2),
                            ("lowerleg02.L", "fuss_L", "knie_L", -P / 2), ("lowerleg02.R", "fuss_R", "knie_R", -P / 2)):
    c = KF.rig.pose.bones[bone].constraints.new("IK"); c.target = KF.Z[ziel]; c.chain_count = 4
    c.pole_target = KF.Z[pol]; c.pole_angle = pw; KF.IK[ziel] = c


def rig_mat(H, Fc):
    Z = Vector(H).normalized(); Fc = Vector(Fc); Y = -(Fc - Z * Fc.dot(Z)).normalized(); X = Y.cross(Z)
    return Matrix((X, Y, Z)).transposed()


def seg(t, a, b):
    return min(1.0, max(0.0, (t - a) / (b - a)))


# ======================================================================  Zeitplan (Story-Zeit ts in s)
T_KREUZ = 3.6          # Beginn Impulsschritte / Speer zurueck
T_BLOCK = 4.98         # Stemmschritt links
T_REL = 5.22           # Abwurf
X_ = Vector((1, 0, 0)); UP = Vector((0, 0, 1))


def pel_x(t):
    if t < 4.95:
        return -29.5 + 5.6 * max(t, 0.0)
    if t < 5.3:
        return -1.78 + .78 * ease(seg(t, 4.95, 5.3))
    return -1.0 + .45 * ease(seg(t, 5.3, 5.9))


# Fusspunkte: (Zeit, x, y, Fuss)
PLANTS = []
fuss = "R"
for k in range(12):
    t = .1 + .3 * k; PLANTS.append((t, pel_x(t) + .3, -.11 if fuss == "R" else .11, fuss)); fuss = "L" if fuss == "R" else "R"
for t in (3.68, 3.96, 4.24, 4.50, 4.74):
    PLANTS.append((t, pel_x(t) + .25, .02 if fuss == "R" else .2, fuss)); fuss = "L" if fuss == "R" else "R"
PLANTS.append((T_BLOCK, -.75, .15, "L"))
PLANTS.append((5.55, -.3, -.3, "R"))


def fuesse_setzen(t):
    """Stand- und Schwungfuss aus der Fusspunkt-Liste"""
    pos = {}
    if t <= PLANTS[0][0]:
        pos["R"] = Vector((pel_x(t) + .1, -.11, .1)); pos["L"] = Vector((pel_x(t) - .25, .11, .1)); return pos
    k = max(i for i, p in enumerate(PLANTS) if p[0] <= t)
    tk, xk, yk, fk = PLANTS[k]
    stand_lift = 0.0
    if k + 1 < len(PLANTS):
        tn = PLANTS[k + 1][0]; f = seg(t, tk, tn)
        stand_lift = .06 * ease((f - .55) / .45) if tn - tk < .5 else 0.0
        pos[fk] = Vector((xk, yk, .1 + stand_lift))
        # Schwungfuss: von seinem letzten Punkt (k-1) zum naechsten (k+1)
        _, xa, ya, _ = PLANTS[k - 1] if k >= 1 else (0, pel_x(0) - .3, -.11 if fk == "L" else .11, "")
        _, xb, yb, fb = PLANTS[k + 1]
        hub = (.22 if tk < T_KREUZ else .14) * math.sin(P * f)
        e = ease(f)
        pos[fb] = Vector((xa + (xb - xa) * e, ya + (yb - ya) * e, .1 + hub))
    else:
        pos[fk] = Vector((xk, yk, .1))
        _, xa, ya, fa = PLANTS[k - 1]; pos[fa] = Vector((xa, ya, .1))
    return pos


def gier(t):
    """Drehung des Oberkoerpers um z (0 = Laufrichtung +x; negativ = linke Schulter vorne)"""
    if t < T_KREUZ:
        return 0.0
    if t < T_BLOCK:
        return -1.2 * ease(seg(t, T_KREUZ, 4.05))
    if t < T_REL:
        return -1.2 + 1.45 * ease(seg(t, T_BLOCK, T_REL))
    return .25 * (1 - ease(seg(t, T_REL, 5.8)))


def lehne(t):
    if t < T_KREUZ:
        return .12
    if t < T_BLOCK:
        return .12 - .32 * ease(seg(t, T_KREUZ, 4.6))
    if t < 5.35:
        return -.2 + .65 * ease(seg(t, T_BLOCK, 5.35))
    return .45 - .4 * ease(seg(t, 5.35, 6.3))


def speer_richtung(t):
    a = (math.radians(8) if t < T_KREUZ else math.radians(8) + math.radians(26) * ease(seg(t, T_KREUZ, 4.05)))
    if t >= T_BLOCK:
        a = math.radians(34) + math.radians(2) * seg(t, T_BLOCK, T_REL)
    return Vector((math.cos(a), 0, math.sin(a)))


# Flug: Abwurf an der Hand, Landung mit der Spitze bei 98,48 m
G = 9.81
REL = {}


def flugbahn(dt):
    p0 = REL["p"]; vx, vz = REL["v"]
    return Vector((p0.x + vx * dt, p0.y, p0.z + vz * dt - .5 * G * dt * dt)), Vector((vx, 0, vz - G * dt))


def landung_berechnen(p0):
    REL["p"] = p0.copy(); vz = 18.6
    # Zeit, bis die Mitte auf .45 m sinkt (Spitze steckt dann im Boden)
    a = -.5 * G; b = vz; c = p0.z - .45
    dt = (-b - math.sqrt(b * b - 4 * a * c)) / (2 * a)
    d_end = Vector((1, 0, (vz - G * dt) / 1)).normalized()
    # Spitze (1,1 m vor der Mitte) soll bei x = 98,48 landen
    vx = (98.48 - 1.1 * d_end.x * .9 - p0.x) / dt
    for _ in range(3):
        d_end = Vector((vx, 0, vz - G * dt)).normalized(); vx = (98.48 - 1.1 * d_end.x - p0.x) / dt
    REL["v"] = (vx, vz); REL["dt"] = dt; REL["d_end"] = d_end
    REL["p_end"] = flugbahn(dt)[0]


T_LAND = None


def figur(ts):
    global T_LAND
    KF.zuruecksetzen()
    for c in KF.IK.values():
        c.influence = 1.0
    t = ts
    g_ = gier(t); fw = Vector((math.cos(g_), math.sin(g_), 0)); le = Vector((-fw.y, fw.x, 0))
    lean = lehne(t)
    jubel = ease(seg(t, 9.35, 9.9)) if t > 9.3 else 0.0
    # Becken
    bob = .035 * math.sin(2 * P * (t - .1) / .3 - P / 2) if t < T_KREUZ else .02 * math.sin(2 * P * t / .26)
    tief = -.05 * math.sin(P * seg(t, T_KREUZ, T_REL)) - .04 * ease(seg(t, T_BLOCK - .1, T_BLOCK + .1)) * (1 - seg(t, T_REL, 5.6))
    hopp = .14 * abs(math.sin((t - 9.6) * 5.5)) * jubel if t < 12.5 else 0.0
    pel = Vector((pel_x(t), .0 + .06 * seg(t, T_KREUZ, 4.1) - .06 * seg(t, T_REL, 5.8), .97 + (bob if t < 5.3 else 0) + tief + hopp))
    H = fw * math.sin(lean) + UP * math.cos(lean); Fc = fw * math.cos(lean) - UP * math.sin(lean)
    rq = rig_mat(H, Fc).to_quaternion()
    KF.rig.rotation_mode = "QUATERNION"; KF.rig.rotation_quaternion = rq
    KF.rig.location = pel - rq.to_matrix() @ (KF.PEL * KF.SK)
    # Fuesse
    fp = fuesse_setzen(t)
    for sd in ("L", "R"):
        p_ = fp[sd]
        if hopp:
            p_ = p_ + Vector((0, 0, hopp * .9))
        KF.Z["fuss_" + sd].location = p_
    for sd, s_ in (("L", 1), ("R", -1)):
        KF.Z["knie_" + sd].location = pel + X_ * 2.0 + Vector((0, s_ * .35, -.3))
    sh_R = pel + H * .48 - le * .19; sh_L = pel + H * .48 + le * .19
    # rechte Hand (Speer)
    ph = 2 * P * (t - .1) / .6
    trag = sh_R + UP * .14 + X_ * (.02 + .03 * math.sin(ph)) + Vector((0, -.03, 0))
    zurueck = sh_R - X_ * .64 + UP * .06
    if t < T_KREUZ:
        hR = trag
    elif t < T_BLOCK:
        hR = trag.lerp(zurueck, ease(seg(t, T_KREUZ, 4.15)))
    elif t < T_REL:
        s = seg(t, T_BLOCK, T_REL) ** 1.5
        P0 = zurueck; P1 = sh_R + UP * .34 - X_ * .05; P2 = sh_R + X_ * .6 + UP * .2
        hR = P0 * (1 - s) ** 2 + P1 * 2 * s * (1 - s) + P2 * s * s
    elif t < 5.65:
        s = ease(seg(t, T_REL, 5.65))
        P2 = sh_R + X_ * .6 + UP * .2; P3 = pel + X_ * .38 + Vector((0, .22, -.08))
        hR = P2.lerp(P3, s)
    else:
        P3 = pel + X_ * .38 + Vector((0, .22, -.08)); ruhe = pel + Vector((.05, -.27, -.05))
        hR = P3.lerp(ruhe, ease(seg(t, 5.65, 6.6)))
    # linke Hand
    sp = -math.cos(ph)
    lauf_L = sh_L + X_ * (.08 + .24 * sp) - H * (.36 - .16 * sp) + Vector((0, .03, 0))
    vorn_L = sh_L + X_ * .58 + UP * .02
    zieh_L = pel + UP * .28 + Vector((-.05, .3, 0))
    if t < T_KREUZ:
        hL = lauf_L
    elif t < T_BLOCK:
        hL = lauf_L.lerp(vorn_L, ease(seg(t, T_KREUZ, 4.1)))
    elif t < 5.4:
        hL = vorn_L.lerp(zieh_L, ease(seg(t, T_BLOCK, 5.3)))
    else:
        hL = zieh_L.lerp(pel + Vector((.05, .27, -.05)), ease(seg(t, 5.4, 6.4)))
    KF.Z["hand_R"].location = hR; KF.Z["hand_L"].location = hL
    # Ellbogen: beim Wurf hoch/aussen, sonst nach hinten
    hoch = math.sin(P * seg(t, T_BLOCK, T_REL + .05))
    KF.Z["ell_R"].location = pel - X_ * 1.2 - le * .45 + UP * (.3 + 1.2 * hoch)
    KF.Z["ell_L"].location = pel - X_ * 1.2 + le * .45 + UP * .3
    if jubel > 0:
        KF.IK["hand_L"].influence = 1 - jubel; KF.IK["hand_R"].influence = 1 - jubel
        KF.dreh("upperarm01.L", z=-.72 + 3.0 * jubel, x=.2 * jubel); KF.dreh("upperarm01.R", z=.72 - 3.0 * jubel, x=.2 * jubel)
        KF.dreh("lowerarm01.L", x=-.4 * jubel); KF.dreh("lowerarm01.R", x=-.4 * jubel)
    # Kopf: schaut dem Speer nach (oben), sonst geradeaus
    blick = 0.0
    if T_REL < t < 9.3:
        dtf = t - T_REL; blick = -.55 * math.sin(P * min(1, dtf / 3.9)) + .1
    KF.dreh("neck01", x=-.5 * lean + blick)
    KF.dreh("head", z=-.6 * min(0, g_) * .8)        # Blick bleibt nach vorne, auch wenn der Koerper seitlich steht
    halt = t < T_REL
    for sd in ("L", "R"):
        for ff in range(2, 6):
            for g in (1, 2, 3):
                fest = (sd == "R" and halt)
                KF.dreh(f"finger{ff}-{g}.{sd}", x=(1.35 if fest else .5 + .12 * g) * (1 - jubel) + .1)
        for g in (2, 3):
            KF.dreh(f"finger1-{g}.{sd}", x=.45 * (1 - jubel))
    bpy.context.view_layer.update()
    # Speer
    if t < T_REL:
        d = speer_richtung(t)
        SPEER.location = hR + Vector((0, -.02, .0)) + d * .02
        SPEER.rotation_quaternion = d.to_track_quat("Y", "Z")
    else:
        if not REL:
            figur(T_REL - 1e-4)          # Abwurfpunkt genau aus der Hand
            landung_berechnen(SPEER.location.copy())
            return figur(ts)
        dtf = t - T_REL
        if dtf < REL["dt"]:
            p_, v_ = flugbahn(dtf)
            d = v_.normalized()
            SPEER.location = p_; SPEER.rotation_quaternion = d.to_track_quat("Y", "Z")
        else:
            d = REL["d_end"]; we = dtf - REL["dt"]
            wackel = .05 * math.sin(we * 38) * math.exp(-we * 3.0)
            q = d.to_track_quat("Y", "Z") @ Quaternion((1, 0, 0), wackel)
            SPEER.location = REL["p_end"]; SPEER.rotation_quaternion = q
            spitze = REL["p_end"] + REL["d_end"] * 1.05
            for o, v in KLUMPEN:
                if we < .9:
                    o.location = Vector((spitze.x, spitze.y, .05)) + Vector((v.x * we, v.y * we, v.z * we - 4.9 * we * we)) * .6
                    if o.location.z < .02:
                        o.location.z = .02
                else:
                    o.location.z = .02
    # Anzeigetafel nach der Landung
    land = REL and (t - T_REL) >= REL["dt"] + .6
    TAFELN[0].hide_render = bool(land); TAFELN[1].hide_render = not land
    for o, z0, ph_ in PUBLIKUM:
        o.location.z = z0 + (.1 * max(0, math.sin(t * 7 + ph_)) if land else 0.0)
    return pel, fw


from mathutils import Quaternion


def becken():
    nk = KF.rig.matrix_world @ KF.rig.pose.bones["neck01"].head
    return (KF.rig.matrix_world @ KF.PEL) * .55 + nk * .45


def kopf():
    return KF.rig.matrix_world @ KF.rig.pose.bones["head"].head + Vector((0, 0, .1))


def fuesse():
    return (KF.Z["fuss_L"].matrix_world.translation + KF.Z["fuss_R"].matrix_world.translation) / 2 + Vector((0, 0, .15))


# ======================================================================  Kamera
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam
cam.data.clip_start = .03; cam.data.clip_end = 3000; cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
cam.data.dof.use_dof = True
SZ = [
    # t0, t1, ts0, ts1, modus, pos0, pos1, ziel0, ziel1, brennweite
    (0.00, 1.50, 4.98, 5.32, "P", (2.6, -2.7, .45), (2.5, -2.6, .5), "B", "B", 22),                    # Aufhaenger: Abwurf in Zeitlupe
    (1.50, 2.60, 6.6, 7.5, "P", (44, -1.6, .3), (46, -1.6, .3), "J", "J", 55),                          # Speer ueber der Kamera
    (2.60, 3.55, 4.1, 4.5, "P", (-52, -20, 26), (-50, -19, 25), (40, 0, 0), (42, 0, 0), 22),           # Stadion von hinten oben
    (3.55, 5.95, 0.0, 0.0, "P", (-95, -175, 95), (-60, -160, 80), (60, 0, 5), (60, 0, 5), 22),          # Stadion aus der Luft
    (5.95, 8.00, 1.0, 3.0, "T", (1.6, -4.6, 1.2), (1.3, -4.4, 1.2), "B", "B", 30),                     # Anlauf, seitlich mitfahrend
    (8.00, 9.20, 3.62, 4.4, "T", (1.0, -3.0, .4), (1.0, -2.9, .4), "FU", "FU", 18),                    # Kreuzschritte
    (9.20, 10.90, 4.3, 4.96, "T", (-2.0, -2.8, 1.7), (-1.6, -2.9, 1.6), "B", "B", 26),                 # Arm ganz zurueck
    (10.90, 12.20, 4.96, 5.42, "P", (3.2, -1.7, .7), (3.1, -1.8, .65), "B", "B", 20),                 # Peitschen nach vorn
    (12.20, 14.30, 5.6, 7.3, "J+", (-4.5, -8.5, -2.2), (-3.5, -8.5, -1.5), "J", "J", 32),             # steigt hoeher als ein Haus
    (14.30, 16.60, 7.3, 8.3, "P", (68, -6, 1.0), (69, -6, 1.0), "J", "J", 20),                         # fliegt und fliegt
    (16.60, 18.00, 8.55, 9.45, "P", (104, -6.5, .5), (104, -6.3, .5), (96, 0, .4), (97, 0, .5), 30),   # Landung hinter der 90-m-Linie
    (18.00, 20.00, 9.6, 11.6, "P", (94.6, -2.4, .75), (95.0, -2.2, .85), (154, 0, 9), (154, 0, 10), 38),  # Speer + Tafel 98.48
    (20.00, 21.60, 11.6, 13.0, "P", (52, -6, 150), (54, -6, 158), (52, 0, 0), (54, 0, 0), 24),         # von oben: fast ein Fussballfeld
    (21.60, 25.00, 9.5, 12.9, "B+", (2.0, -2.4, .1), (2.6, -1.0, .5), "B", "B", 24),                  # Jubel
    (25.00, 28.00, 13.0, 16.0, "P", (97.6, -3.6, .8), (100.6, -2.7, 1.3), (98.0, 0, .75), (98.1, 0, .8), 26),  # Speer steckt im Rasen
]


def zustand(t):
    for s in SZ:
        if s[0] <= t < s[1]:
            break
    k = (t - s[0]) / (s[1] - s[0])
    ts = s[2] + (s[3] - s[2]) * k
    k = ease(k) * .7 + k * .3
    pel, fw = figur(ts)
    bk = becken()
    o = Vector(lerpv(s[5], s[6], k))
    jp = SPEER.location.copy()
    if s[4] == "T":
        pos = Vector((pel.x, 0, 0)) + o
    elif s[4] == "B+":
        pos = bk + o
    elif s[4] == "J+":
        pos = jp + o
    else:
        pos = o
    if s[7] == "B":
        ziel = bk
    elif s[7] == "FU":
        ziel = fuesse()
    elif s[7] == "J":
        ziel = jp
    else:
        ziel = Vector(lerpv(s[7], s[8], k))
    cam.location = pos; d = ziel - pos; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = s[9]; cam.data.dof.focus_distance = d.length; cam.data.dof.aperture_fstop = 2.8 if d.length < 6 else 11
    zit = .004
    cam.location += Vector((zit * math.sin(t * 7.3), zit * math.cos(t * 5.1), zit * math.sin(t * 9.7)))


os.makedirs(A.ordner, exist_ok=True)
N = int(round(D * A.fps))
liste = [int(round(float(x) * A.fps)) for x in A.nur.split(",")] if A.nur else list(range(A.start, N))
for f in liste:
    pfad = os.path.join(A.ordner, f"speer_{f:04d}.png")
    if os.path.exists(pfad) and not A.nur:
        continue
    zustand(f / A.fps); bpy.context.view_layer.update(); zustand(f / A.fps)
    sc.render.filepath = pfad
    bpy.ops.render.render(write_still=True); print("FERTIG", pfad, flush=True)
