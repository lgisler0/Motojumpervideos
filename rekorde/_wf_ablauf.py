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


UP = Vector((0, 0, 1))
T_LIP = 10.0; V_AN = 3.5; V_SPRUNG = 5.2; Y_ZUNGE = -9.0
T_FALL = math.sqrt(2 * (H_FALL - .2) / G)            # ~3.42 s
T_AUF = T_LIP + T_FALL; T_POP = T_AUF + 1.9
X_AUF = V_SPRUNG * T_FALL


def kajak_zustand(ts):
    """Position und Ausrichtung (vorwaerts, Neigung) des Kajaks"""
    if ts < T_LIP:
        x = -V_AN * (T_LIP - ts)
        p = Vector((x, Y_ZUNGE + .4 * math.sin(ts * .7), H_FALL + .25 + .015 * max(0, -x) - .35 * sstep(-6, 0, x) + .05 * math.sin(ts * 3)))
        nick = -.12 * sstep(-6, 0, x); roll = .05 * math.sin(ts * 2.1)
    elif ts < T_AUF:
        t = ts - T_LIP
        p = Vector((V_SPRUNG * t, Y_ZUNGE, H_FALL + .2 - .5 * G * t * t))
        nick = -.12 - 1.05 * ease(seg(t, 0, 1.6)); roll = 0.0
    elif ts < T_POP:
        u = seg(ts, T_AUF, T_POP)
        p = Vector((X_AUF + 1.2 * u, Y_ZUNGE, -3.5 * math.sin(P * min(1, u * 1.3))))
        nick = -1.17 + .6 * u; roll = 0.0
    else:
        u = ts - T_POP
        p = Vector((X_AUF + 1.2 + .45 * u, Y_ZUNGE - .2 * u, .9 * math.exp(-u * 2.2) * math.cos(u * 4) + .05 * math.sin(ts * 2.5)))
        nick = -.57 * math.exp(-u * 2.5) + .06 * math.sin(u * 5) * math.exp(-u); roll = .08 * math.sin(u * 3) * math.exp(-u * .8)
    q = Quaternion((0, 0, 1), 0) @ Quaternion((0, 1, 0), -nick) @ Quaternion((1, 0, 0), roll)
    return p, q


def figur(ts):
    KF.zuruecksetzen()
    for c in KF.IK.values():
        c.influence = 1.0
    p, q = kajak_zustand(ts)
    KAJAK.location = p; KAJAK.rotation_quaternion = q
    M = q.to_matrix(); kf = M @ Vector((1, 0, 0)); kl = M @ Vector((0, 1, 0)); ku = M @ Vector((0, 0, 1))
    faellt = T_LIP < ts < T_AUF
    tuck = ease(seg(ts, T_LIP - .9, T_LIP + .2)) if ts < T_AUF else 0.0
    jubel = ease(seg(ts, T_POP + 1.8, T_POP + 2.6))
    lean = .1 + .75 * tuck - .05 * jubel
    pel = p + ku * .04 - kf * .05
    H = ku * math.cos(lean) + kf * math.sin(lean); Fc = kf * math.cos(lean) - ku * math.sin(lean)
    rq = rig_mat(H, Fc).to_quaternion()
    KF.rig.rotation_mode = "QUATERNION"; KF.rig.rotation_quaternion = rq
    KF.rig.location = pel - rq.to_matrix() @ (KF.PEL * KF.SK)
    # Beine im Boot: Fuesse vorne, Knie leicht hoch und aussen
    for sd, s in (("L", 1), ("R", -1)):
        KF.Z["fuss_" + sd].location = pel + kf * .95 + kl * (s * .1) + ku * .0
        KF.Z["knie_" + sd].location = pel + kf * .6 + kl * (s * 1.4) + ku * 1.0
    sh_c = pel + H * .48
    # Paddel: Mitte vor der Brust, Schaft quer, abwechselnd links/rechts eingetaucht
    TP = 1.3
    ph = 2 * P * ts / TP
    if ts < T_LIP - .9 or ts > T_POP + .6:
        paddeln = 1.0 if ts < T_LIP else (1 - jubel) * ease(seg(ts, T_POP + .6, T_POP + 1.0)) * .6
    else:
        paddeln = 0.0
    seite = math.sin(ph)                       # +1: links im Wasser, -1: rechts
    zug = math.cos(ph)                         # Blatt wandert von vorne nach hinten
    mitte = sh_c + kf * .36 - H * .14
    achse = (kl * math.cos(.75 * seite) + (-ku) * math.sin(.75 * seite) * 1.0)
    achse = Quaternion(ku, .45 * zug * paddeln).to_matrix() @ achse
    # ruhige Haltung beim Fallen: Paddel laengs neben dem Boot links, Haende an der linken Seite
    ruhe_achse = (kf * .9 + kl * .3 + ku * .1).normalized()
    ruhe_mitte = sh_c + kl * .3 + kf * .2 - H * .15
    a_eff = (achse * paddeln + kl * (1 - paddeln) * (1 - tuck) + ruhe_achse * tuck).normalized()
    m_eff = mitte * (1 - tuck) + ruhe_mitte * tuck
    if jubel > 0:     # Paddel hoch ueber den Kopf
        hoch = sh_c + H * .62 + kf * .05
        m_eff = m_eff.lerp(hoch, jubel); a_eff = (a_eff * (1 - jubel) + kl * jubel).normalized()
    PADDEL.location = m_eff
    PADDEL.rotation_quaternion = a_eff.to_track_quat("Y", "Z")
    KF.Z["hand_L"].location = m_eff + a_eff * .34
    KF.Z["hand_R"].location = m_eff - a_eff * .34
    KF.Z["ell_L"].location = sh_c - kf * .8 + kl * .9 - H * .3
    KF.Z["ell_R"].location = sh_c - kf * .8 - kl * .9 - H * .3
    KF.dreh("neck01", x=-.45 * lean + .15 * jubel)
    for sd in ("L", "R"):
        for ff in range(2, 6):
            for g in (1, 2, 3):
                KF.dreh(f"finger{ff}-{g}.{sd}", x=1.3)
        for g in (2, 3):
            KF.dreh(f"finger1-{g}.{sd}", x=.6)
    # unter Wasser: Fahrer versteckt sich mit dem Boot
    # Spritzer beim Aufprall
    dt = ts - T_AUF
    for o, v, r in SPRITZER:
        if 0 <= dt < 1.6:
            pp = Vector((X_AUF, Y_ZUNGE, 0)) + v * dt * .9 + Vector((0, 0, -4.9 * dt * dt))
            o.location = pp if pp.z > -.2 else Vector((0, 0, -60)); s_ = r * (1 + 1.5 * dt); o.scale = (s_ * (1 + .5 * v.x / 7), s_ * (1 - .3 * v.y / 7), s_ * .6)
        else:
            o.location = (0, 0, -60)
    # Wasser bewegt sich
    for mp, r in ZEIT:
        mp.inputs["Location"].default_value = (r[0] * ts * .3, r[1] * ts * .3, r[2] * ts * .3)
    jub = ts > T_POP + 1.5
    for o, z0, ph_ in RAND_LEUTE:
        o.location.z = z0 + (.08 * max(0, math.sin(ts * 7 + ph_)) if jub else 0.0)
    bpy.context.view_layer.update()
    return pel, kf


def becken():
    nk = KF.rig.matrix_world @ KF.rig.pose.bones["neck01"].head
    return (KF.rig.matrix_world @ KF.PEL) * .55 + nk * .45


# ======================================================================  Kamera
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam
cam.data.clip_start = .03; cam.data.clip_end = 5000; cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
cam.data.dof.use_dof = True
SZ = [
    # t0, t1, ts0, ts1, modus, pos0, pos1, ziel0, ziel1, brennweite   (K+ = relativ zum Kajak in Weltachsen)
    (0.00, 1.60, 11.25, 11.7, "K+", (3.0, -6.5, .8), (3.0, -6.5, 1.0), "B", "B", 24),                                 # Aufhaenger: freier Fall
    (1.60, 3.00, 7.4, 8.9, "K+", (-6.0, -2.4, 2.8), (-5.5, -2.2, 2.9), (8, 2, -5), (8, 2, -6), 22),                   # zur Kante
    (3.00, 4.30, 8.0, 8.6, "P", (70, -10, 2.5), (69, -9.5, 2.6), (6, -4, 34), (6, -4, 36), 20),                        # wie hoch? von unten
    (4.30, 6.90, 8.0, 8.0, "P", (175, -70, 100), (150, -58, 88), (12, 0, 28), (12, 0, 28), 24),                   # Palouse Falls von oben
    (6.90, 8.90, 3.0, 5.0, "K+", (3.4, -2.0, .9), (3.1, -1.7, .95), "B", "B", 26),                                   # paddelt zur Kante
    (8.90, 11.50, 8.4, 9.7, "P", (6.5, -5.5, 61.2), (6.8, -5.8, 61.0), "B", "B", 20),               # 57 m nichts
    (11.50, 13.30, 9.0, 9.8, "P", (42, -40, 75), (40, -39, 75), (4, -6, 30), (4, -6, 30), 24),                        # hoeher als Niagara
    (13.30, 15.30, 9.3, 10.6, "K+", (2.3, -2.6, .9), (2.6, -2.8, -.6), "B", "B", 24),                                # lehnt sich vor, kippt
    (15.30, 17.40, 10.6, 13.2, "K+", (3.6, -6.0, -2.2), (3.6, -6.0, -2.6), "B", "B", 22),                            # freier Fall
    (17.40, 19.30, 12.9, 14.4, "P", (30, -20, 1.6), (29, -19.5, 1.6), (14, -9, 1.5), (14, -9, 1.0), 22),             # Aufprall
    (19.30, 21.20, 14.6, 16.2, "P", (24, -16, 1.2), (23.5, -15.6, 1.2), (16.5, -9, .3), (16.5, -9, .4), 26),          # weg ... wieder da
    (21.20, 25.20, 16.2, 20.2, "P", (25.5, -14.0, 1.6), (24.0, -16.0, 2.4), "B", "B", 24),                            # Jubel vor dem Fall
]


def zustand(t):
    for s in SZ:
        if s[0] <= t < s[1]:
            break
    k = (t - s[0]) / (s[1] - s[0])
    ts = s[2] + (s[3] - s[2]) * k
    k = ease(k) * .7 + k * .3
    pel, kf = figur(ts)
    bk = becken()
    o = Vector(lerpv(s[5], s[6], k))
    if s[4] == "K+":
        pos = KAJAK.location + o
        ziel = bk if s[7] == "B" else KAJAK.location + Vector(lerpv(s[7], s[8], k))
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
    pfad = os.path.join(A.ordner, f"fall_{f:04d}.png")
    if os.path.exists(pfad) and not A.nur:
        continue
    zustand(f / A.fps); bpy.context.view_layer.update(); zustand(f / A.fps)
    sc.render.filepath = pfad
    bpy.ops.render.render(write_still=True); print("FERTIG", pfad, flush=True)
