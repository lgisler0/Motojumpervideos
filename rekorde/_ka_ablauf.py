# ======================================================================  IK (Arme pole -P/2)
from mathutils import Quaternion
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


X_ = Vector((1, 0, 0)); Y_ = Vector((0, 1, 0)); UP = Vector((0, 0, 1))
T_A = 1.5                      # Armzyklus (s)
V_SW = 1.45                    # Schwimmtempo (m/s)
T_B0 = 24300.0; T_STEH = 24312.0; T_ZIEL = 24325.0


def boden_A(x):
    return -.1 * x if x > 0 else -.055 * x


def boden_B(x):
    return .09 * x


def gebiet(ts):
    return "A" if ts < 100 else ("M" if ts < 24000 else "B")


def schwimm_pos(ts):
    g = gebiet(ts)
    if g == "A":
        return A_ + Vector((6.0 + V_SW * (ts - 3.0), 0, 0))
    if g == "M":
        return M_ + Vector((V_SW * (ts - 6000.0), 0, 0))
    return B_ + Vector((-6.0 - V_SW * (T_STEH - ts), 0, 0))


# Hand-Bahn beim Kraulen (vorwaerts, aussen, hoch) relativ zur Schulter
ARM_KEYS = [(0.00, (.55, .08, -.04)), (.12, (.64, .05, -.30)), (.30, (.15, -.10, -.52)), (.50, (-.40, .04, -.38)),
            (.58, (-.55, .10, -.06)), (.72, (-.30, .26, .22)), (.86, (.22, .22, .20))]


def arm_bahn(u):
    u = u % 1.0
    ks = ARM_KEYS + [(1.0, ARM_KEYS[0][1])]
    for i in range(len(ks) - 1):
        if ks[i][0] <= u < ks[i + 1][0]:
            break
    f = (u - ks[i][0]) / (ks[i + 1][0] - ks[i][0])
    p0 = Vector(ks[(i - 1) % len(ARM_KEYS)][1]); p1 = Vector(ks[i][1]); p2 = Vector(ks[(i + 1) % len(ARM_KEYS)][1]); p3 = Vector(ks[(i + 2) % len(ARM_KEYS)][1])
    f2 = f * f; f3 = f2 * f
    return .5 * (2 * p1 + (-p0 + p2) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f2 + (-p0 + 3 * p1 - 3 * p2 + p3) * f3)


def gischt(punkte):
    for i, o in enumerate(GISCHT):
        if i < len(punkte):
            p_, r = punkte[i]; o.location = p_; o.scale = (r, r, r * .45)
        else:
            o.location = (0, 0, -50)


def schwimmen(ts):
    pel = schwimm_pos(ts)
    uR = (ts / T_A) % 1.0; uL = (uR + .5) % 1.0
    n = math.floor(ts / T_A)
    roll = .55 * math.sin(2 * P * (uR - .08))
    atem = 0.0
    if n % 2 == 0:
        atem = -.5 * math.sin(P * seg(uR, .52, .98))          # Kopf/Koerper zur rechten Seite drehen zum Atmen
    th = roll + atem
    H = Vector((math.cos(.06), 0, math.sin(.06)))
    Fc = Vector((0, math.sin(th), -math.cos(th)))
    pel = pel + Vector((0, 0, -.02 + .02 * math.sin(4 * P * ts / T_A)))
    rq = rig_mat(H, Fc).to_quaternion()
    KF.rig.rotation_mode = "QUATERNION"; KF.rig.rotation_quaternion = rq
    KF.rig.location = pel - rq.to_matrix() @ (KF.PEL * KF.SK)
    le = H.cross(Fc).normalized()
    spr = []
    for sd, s, u in (("L", 1, uL), ("R", -1, uR)):
        sh = pel + H * .5 + le * (.19 * s)
        k = arm_bahn(u)
        hand = sh + X_ * k.x + Y_ * (s * k.y) + UP * k.z
        KF.Z["hand_" + sd].location = hand
        KF.Z["ell_" + sd].location = sh + UP * 1.0 + Y_ * (s * .6) - X_ * .2
        if u < .14:
            e = 1 - u / .14
            for j in range(3):
                spr.append((Vector((hand.x + .1 * j - .1, hand.y + s * .06 * (j - 1), .03 + .1 * (1 - e) * (j + 1) / 3)), .02 + .03 * e))
        elif .54 < u < .64:
            spr.append((Vector((hand.x, hand.y, .08 + .2 * seg(u, .54, .64))), .018))
        # Beine: 6er-Beinschlag
        ph = 2 * P * 3 * ts / T_A + (0 if s > 0 else P)
        fz = -.24 + .12 * math.sin(ph)
        KF.Z["fuss_" + sd].location = pel - H * .9 + Y_ * (s * .1) + UP * fz
        KF.Z["knie_" + sd].location = pel - UP * 2.0 + X_ * .4 + Y_ * (s * .3)
        if fz > -.16:
            spr.append((Vector((pel.x - .95, pel.y + s * .1, .04)), .025 + .03 * seg(fz, -.16, -.12)))
    gischt(spr)
    KIEL.location = Vector((pel.x - .35, pel.y, .035)); KIEL.rotation_euler = (0, 0, 0)
    # Kopf leicht zur Atmung drehen
    KF.dreh("neck01", x=.35)
    for sd in ("L", "R"):
        for ff in range(2, 6):
            for g in (1, 2, 3):
                KF.dreh(f"finger{ff}-{g}.{sd}", x=.15 + .05 * g)       # Hand flach, Finger leicht geschlossen
        for g in (2, 3):
            KF.dreh(f"finger1-{g}.{sd}", x=.2)
    return pel, X_


def aufrecht(ts):
    """Stehen am Start, ins Wasser laufen, aus dem Wasser gehen, jubeln"""
    g = gebiet(ts)
    if g == "A":
        boden = boden_A; basis = A_
        if ts < 0:
            px = -1.0; T = 99; gehen = False
        else:
            px = -1.0 + 6.0 * ease(seg(ts, 0, 2.6)) ** .8; T = .36; gehen = True
    else:
        boden = boden_B; basis = B_
        px = -6.0 + 10.5 * seg(ts, T_STEH, T_ZIEL) if ts < T_ZIEL else 4.5 + .4 * ease(seg(ts, T_ZIEL, T_ZIEL + 1.0))
        T = .7; gehen = ts < T_ZIEL + 1.0
    jubel = ease(seg(ts, T_ZIEL + .4, T_ZIEL + 1.2)) if g == "B" else 0.0
    gischt([]); KIEL.location = (0, 0, -50)
    # Fuesse: Schrittfolge entlang x
    def fpos(k, seite):
        if not gehen:
            return Vector((px + (.05 if seite > 0 else -.05), seite * .12, 0))
        t0 = (0 if g == "A" else T_STEH)
        tk = t0 + k * T
        if g == "A":
            xk = -1.0 + 6.0 * ease(seg(tk, 0, 2.6)) ** .8
        else:
            xk = -6.0 + 10.5 * seg(tk, T_STEH, T_ZIEL) if tk < T_ZIEL else 4.5 + .4 * ease(seg(tk, T_ZIEL, T_ZIEL + 1.0))
        return Vector((xk + .25, seite * .12, 0))
    t0 = 0 if g == "A" else T_STEH
    q = (ts - t0) / T if gehen else 0.0
    k = math.floor(q); f = q - k
    for sd, s_ in (("L", 1), ("R", -1)):
        if not gehen or q < 0:
            p_ = fpos(0, s_)
            lift = 0.0
        else:
            mein = (k % 2 == 0) == (sd == "L")          # dieser Fuss steht
            if mein:
                p_ = fpos(k, s_); lift = 0.0
            else:
                a = fpos(k - 1, s_); b_ = fpos(k + 1, s_); e = ease(f)
                p_ = a.lerp(b_, e); lift = (.2 if g == "A" else .12) * math.sin(P * f)
        p_ = basis + p_ + Vector((0, 0, boden(p_.x) + .1 + lift))
        KF.Z["fuss_" + sd].location = p_
    pel = basis + Vector((px, 0, boden(px) + .95 + (.03 * math.sin(2 * P * q) if gehen else 0)))
    if jubel:
        pel.z += .08 * abs(math.sin((ts - T_ZIEL) * 5)) * jubel
    lean = (.18 if g == "A" and gehen else .06) * (1 - jubel)
    H = X_ * math.sin(lean) + UP * math.cos(lean); Fc = X_ * math.cos(lean) - UP * math.sin(lean)
    rq = rig_mat(H, Fc).to_quaternion()
    KF.rig.rotation_mode = "QUATERNION"; KF.rig.rotation_quaternion = rq
    KF.rig.location = pel - rq.to_matrix() @ (KF.PEL * KF.SK)
    le = Y_
    for sd, s_ in (("L", 1), ("R", -1)):
        KF.Z["knie_" + sd].location = pel + X_ * 2.0 + Y_ * (s_ * .35) - UP * .3
        KF.Z["ell_" + sd].location = pel - X_ * 1.2 + Y_ * (s_ * .45) + UP * .3
        sh = pel + H * .48 + le * (s_ * .19)
        if gehen:
            sp = (-math.cos(P * q) if sd == "L" else math.cos(P * q)) * (1.0 if g == "A" else .6)
            hand = sh + X_ * (.08 + .22 * sp) - H * (.38 - .14 * sp) + le * (s_ * .04)
            if g == "B":
                hand = hand + le * (s_ * .12) + UP * .06      # Arme leicht seitlich zum Balancieren auf den Steinen
        else:
            hand = sh - H * .56 + X_ * .06 + le * (s_ * .06)
        KF.Z["hand_" + sd].location = hand
    if jubel > 0:
        KF.IK["hand_L"].influence = 1 - jubel; KF.IK["hand_R"].influence = 1 - jubel
        KF.dreh("upperarm01.L", z=-.72 + 3.0 * jubel, x=.2 * jubel); KF.dreh("upperarm01.R", z=.72 - 3.0 * jubel, x=.2 * jubel)
        KF.dreh("lowerarm01.L", x=-.4 * jubel); KF.dreh("lowerarm01.R", x=-.4 * jubel)
    KF.dreh("neck01", x=-.3 * lean + .1 * jubel)
    for sd in ("L", "R"):
        for ff in range(2, 6):
            for gg in (1, 2, 3):
                KF.dreh(f"finger{ff}-{gg}.{sd}", x=(.5 + .12 * gg) * (1 - jubel) + .1)
        for gg in (2, 3):
            KF.dreh(f"finger1-{gg}.{sd}", x=.45 * (1 - jubel))
    return pel, X_


def figur(ts):
    KF.zuruecksetzen()
    for c in KF.IK.values():
        c.influence = 1.0
    g = gebiet(ts)
    schwimmt = (g == "A" and ts >= 3.0) or g == "M" or (g == "B" and ts < T_STEH)
    pel, fw = schwimmen(ts) if schwimmt else aufrecht(ts)
    # Meer, Boot, Schiff je Gebiet
    om.time = ts % 1000.0
    if g == "A":
        OZEAN.location = A_ + Vector((55, -180, 0)); BOOT.location = A_ + Vector((60, 25, 0)); BOOT.rotation_euler = (0, 0, .3)
        SCHIFF.location = A_ + Vector((2200, 600, 0)); SCHIFF.rotation_euler = (0, 0, P / 2)
    elif g == "M":
        OZEAN.location = M_ + Vector((-120, -180, 0))
        BOOT.location = schwimm_pos(ts) + Vector((-2.0, 12.0, 0)); BOOT.rotation_euler = (0, 0, 0)
        SCHIFF.location = M_ + Vector((112, 6.5 * (ts - 6045.0), 0)); SCHIFF.rotation_euler = (0, 0, P / 2)
    else:
        OZEAN.location = B_ + Vector((-415, -180, 0)); BOOT.location = B_ + Vector((-55, 18, 0)); BOOT.rotation_euler = (0, 0, .2)
        SCHIFF.location = B_ + Vector((-2600, -900, 0)); SCHIFF.rotation_euler = (0, 0, P / 2)
    # Boot schaukelt
    BOOT.location.z = .12 * math.sin(ts * 1.3); BOOT.rotation_euler.x = .03 * math.sin(ts * 1.1); BOOT.rotation_euler.y = .02 * math.sin(ts * .9)
    fertig = g == "B" and ts > T_ZIEL
    for o, z0, ph_ in STRAND_LEUTE:
        o.location.z = z0 + (.08 * max(0, math.sin(ts * 7 + ph_)) if fertig else 0.0)
    bpy.context.view_layer.update()
    return pel, fw


def becken():
    nk = KF.rig.matrix_world @ KF.rig.pose.bones["neck01"].head
    return (KF.rig.matrix_world @ KF.PEL) * .55 + nk * .45


# ======================================================================  Kamera
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam
cam.data.clip_start = .03; cam.data.clip_end = 20000; cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
cam.data.dof.use_dof = True
SZ = [
    # t0, t1, ts0, ts1, modus, pos0, pos1, ziel0, ziel1, brennweite   (R = relativ zum Becken, Ziel "B" oder relativer Punkt "R:")
    (0.00, 1.50, 6043.6, 6044.3, "R", (-1.1, -1.8, .5), (-.9, -1.75, .52), (.5, 0, .05), (.6, 0, .05), 24),        # Aufhaenger: Wasserhoehe, Schiff dahinter
    (1.50, 2.50, 6010.0, 6011.0, "R", (-3.0, -2.0, 6.0), (-2.6, -2.0, 6.0), (2, 0, 0), (2.4, 0, 0), 28),           # Drohne ueber dem Schwimmer
    (2.50, 3.70, 6020.0, 6021.2, "R", (-170, -230, 200), (-160, -225, 190), (0, 0, 0), (0, 0, 0), 40),            # winzig im offenen Meer
    (3.70, 4.60, -1.0, -0.8, "P", A_ + Vector((260, -140, 14)), A_ + Vector((250, -132, 14)), A_ + Vector((-80, 0, 45)), A_ + Vector((-80, 0, 45)), 26),   # Kreideklippen Dover
    (4.60, 6.30, -2.0, -0.3, "P", A_ + Vector((6.5, -3.0, 1.1)), A_ + Vector((6.0, -2.7, 1.15)), "B", "B", 26),   # am Strand
    (6.30, 9.10, 0.0, 2.3, "P", A_ + Vector((10.0, -5.2, 1.0)), A_ + Vector((10.2, -4.6, 1.0)), "B", "B", 28),   # laeuft ins Wasser
    (9.10, 12.10, 6000.0, 6003.0, "R", (-9, -12, 5), (-30, -46, 26), (0, 0, 0), (0, 0, 0), 26),                    # offenes Meer, Boot
    (12.10, 14.30, 6040.5, 6046.0, "R", (-6.5, -4.0, 1.0), (-5.8, -3.6, 1.1), (6, 1.0, 4.0), (6, 1.5, 4.6), 18),         # Schiff kreuzt
    (14.30, 15.40, 6020.0, 6021.3, "R", (.35, -1.6, .5), (.4, -1.55, .5), (.25, 0, .1), (.3, 0, .1), 26),        # Arm ueber Arm
    (15.40, 17.90, 6012.0, 6015.0, "R", (-4.0, -1.6, 2.2), (-3.6, -1.3, 2.2), (1.5, 0, 0), (1.5, 0, 0), 28),                # Stunde um Stunde (von oben)
    (17.90, 20.20, 24302.0, 24304.3, "R", (-1.4, -.6, .55), (-1.3, -.55, .58), (60, 0, 18), (60, 0, 18), 26),      # Klippen Frankreichs
    (20.20, 23.60, 24320.4, 24325.8, "P", B_ + Vector((9.5, -3.6, 1.7)), B_ + Vector((9.0, -3.1, 1.6)), "B", "B", 26),   # aus dem Wasser
    (23.60, 27.40, 24325.8, 24329.6, "R", (-3.0, -1.8, 1.1), (-2.6, -2.8, 1.5), "B", "B", 24),         # Jubel vor den Klippen
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
    if s[4] == "R":
        anker = Vector((pel.x, pel.y, 0)) if gebiet(ts) != "B" or ts < T_STEH else Vector((bk.x, bk.y, boden_B(bk.x - B_.x)))
        pos = anker + o
        pos.z = max(pos.z, .45)
        ziel = bk if s[7] == "B" else anker + Vector(lerpv(s[7], s[8], k))
    else:
        pos = o
        ziel = bk if s[7] == "B" else Vector(lerpv(s[7], s[8], k))
    cam.location = pos; d = ziel - pos; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = s[9]; cam.data.dof.focus_distance = d.length; cam.data.dof.aperture_fstop = 2.8 if d.length < 6 else 11
    zit = .006
    cam.location += Vector((zit * math.sin(t * 7.3), zit * math.cos(t * 5.1), zit * math.sin(t * 9.7)))


os.makedirs(A.ordner, exist_ok=True)
N = int(round(D * A.fps))
liste = [int(round(float(x) * A.fps)) for x in A.nur.split(",")] if A.nur else list(range(A.start, N))
for f in liste:
    pfad = os.path.join(A.ordner, f"kanal_{f:04d}.png")
    if os.path.exists(pfad) and not A.nur:
        continue
    zustand(f / A.fps); bpy.context.view_layer.update(); zustand(f / A.fps)
    sc.render.filepath = pfad
    bpy.ops.render.render(write_still=True); print("FERTIG", pfad, flush=True)
