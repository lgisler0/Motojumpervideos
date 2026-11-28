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


# ======================================================================  Fahrt: Geschwindigkeit und Weg
VMAX = 73.59; TAU = 3.3; T_BREMS = 12.0; A_BREMS = 6.2
S_BREMS = VMAX * (T_BREMS - TAU * (1 - math.exp(-T_BREMS / TAU)))
V_BREMS = VMAX * (1 - math.exp(-T_BREMS / TAU))
T_STOP = T_BREMS + V_BREMS / A_BREMS


def weg(t):
    if t <= 0:
        return 0.0
    if t < T_BREMS:
        return VMAX * (t - TAU * (1 - math.exp(-t / TAU)))
    tb = min(t, T_STOP) - T_BREMS
    return S_BREMS + V_BREMS * tb - .5 * A_BREMS * tb * tb


def tempo(t):
    if t <= 0:
        return 0.0
    if t < T_BREMS:
        return VMAX * (1 - math.exp(-t / TAU))
    return max(0.0, V_BREMS - A_BREMS * (t - T_BREMS))


T_FALLE = None
lo, hi = 0.0, 20.0
for _ in range(50):
    m = (lo + hi) / 2
    if weg(m) < S_FALLE:
        lo = m
    else:
        hi = m
T_FALLE = lo
print("Lichtschranke bei t =", round(T_FALLE, 2), "v =", round(tempo(T_FALLE) * 3.6, 1), "km/h; Stopp bei", round(T_STOP, 1), "s, s =", round(weg(T_STOP)))


def figur(ts):
    KF.zuruecksetzen()
    for c in KF.IK.values():
        c.influence = 1.0
    s = weg(ts)
    p, fw, nr = kurs(s - (0 if ts > 0 else 0))
    if ts <= 0:
        p, fw, nr = kurs(0.0)
    le = nr.cross(fw).normalized()             # links (quer zur Piste)
    # Haltung: 0 = aufrecht, 1 = Ei (Hocke)
    hocke = ease(seg(ts, .6, 1.6)) * (1 - ease(seg(ts, T_BREMS + .2, T_BREMS + 1.6)))
    jubel = ease(seg(ts, T_STOP + .4, T_STOP + 1.2))
    schub = math.sin(P * seg(ts, -.2, .9)) if ts < .9 else 0.0      # Abstossen mit den Stoecken
    bremse = ease(seg(ts, T_BREMS + .8, T_BREMS + 1.8)) * (1 - jubel)
    lean = .15 + 1.15 * hocke + .25 * schub
    pel_h = .92 - .4 * hocke
    pel = p + nr * pel_h - fw * (.1 + .12 * hocke)
    H = nr * math.cos(lean) + fw * math.sin(lean); Fc = fw * math.cos(lean) - nr * math.sin(lean)
    rq = rig_mat(H, Fc).to_quaternion()
    KF.rig.rotation_mode = "QUATERNION"; KF.rig.rotation_quaternion = rq
    KF.rig.location = pel - rq.to_matrix() @ (KF.PEL * KF.SK)
    vib = .004 * math.sin(ts * 61) * seg(ts, 1, 3)
    for sd, sg in (("L", 1), ("R", -1)):
        fuss = p + le * (sg * .13) + nr * (.1 + vib) + fw * (.05 * hocke)
        KF.Z["fuss_" + sd].location = fuss
        KF.Z["knie_" + sd].location = pel + fw * 2.0 + le * (sg * .25) + nr * .2
        # Ski unter dem Fuss
        ski = SKIS[0 if sd == "L" else 1]
        ski.location = p + le * (sg * .13) + nr * .012 + fw * .15
        ski.rotation_quaternion = Matrix((fw, le, nr)).transposed().to_quaternion()
    sh_c = pel + H * .5
    # Arme: Ei -> Haende zusammen vor dem Gesicht; Start -> Stockschub; Bremsen -> Arme seitlich (Luftbremse)
    for sd, sg in (("L", 1), ("R", -1)):
        ei = sh_c + H * .08 + fw * .16 + le * (sg * .08) - nr * .14
        stand = sh_c - H * .4 + le * (sg * .28) + fw * (.12 - .45 * schub)
        breit = sh_c + le * (sg * .7) - H * .15 + fw * .05
        hand = stand.lerp(ei, hocke).lerp(breit, bremse)
        KF.Z["hand_" + sd].location = hand
        KF.Z["ell_" + sd].location = pel + le * (sg * .7) - nr * .6 + fw * .2 if hocke > .5 else pel - fw * 1.0 + le * (sg * .5) + nr * .3
        # Stock: Griff in der Hand, Spitze nach hinten (im Ei unter dem Arm)
        st = STOECKE[0 if sd == "L" else 1]
        richt = (-fw * .9 - nr * .3 + le * (sg * .15)).normalized() if hocke > .3 or bremse > .3 else (-nr * .85 - fw * .3 * (1 - schub) - fw * .6 * schub + le * (sg * .1)).normalized()
        st.location = hand
        q = richt.to_track_quat("-X", "Z")
        st.rotation_quaternion = q
    if jubel > 0:
        KF.IK["hand_L"].influence = 1 - jubel; KF.IK["hand_R"].influence = 1 - jubel
        KF.dreh("upperarm01.L", z=-.72 + 3.0 * jubel, x=.2 * jubel); KF.dreh("upperarm01.R", z=.72 - 3.0 * jubel, x=.2 * jubel)
        KF.dreh("lowerarm01.L", x=-.4 * jubel); KF.dreh("lowerarm01.R", x=-.4 * jubel)
        for sd, st in zip(("L", "R"), STOECKE):
            st.location = (0, 0, -900)
    KF.dreh("neck01", x=-.75 * hocke - .2 * lean * (1 - hocke)); KF.dreh("head", x=-.45 * hocke)
    for sd in ("L", "R"):
        for ff in range(2, 6):
            for g in (1, 2, 3):
                KF.dreh(f"finger{ff}-{g}.{sd}", x=(1.3 if jubel < .5 else .3))
        for g in (2, 3):
            KF.dreh(f"finger1-{g}.{sd}", x=.6)
    # Schneestaub hinter den Skiern ab ~150 km/h
    v = tempo(ts)
    st_ = 0.0
    for i, o in enumerate(STAUB):
        if st_ > 0 and ts < T_STOP:
            k = (i * .37 + ts * 3.1) % 1.0
            q_ = p - fw * (1.2 + 7 * k) + le * ((i % 5 - 2) * .12 * (1 + 2 * k)) + nr * (.03 + .5 * k * k)
            o.location = q_; r = (.03 + .16 * k) * st_; o.scale = (r * 2.2, r, r * .7)
        else:
            o.location = (0, 0, -900)
    # Anzeigetafel nach der Lichtschranke
    gemessen = ts > T_FALLE + .35
    TAFELN[0].hide_render = gemessen; TAFELN[1].hide_render = not gemessen
    for o, z0, ph_ in PUBLIKUM:
        o.location.z = z0 + (.09 * max(0, math.sin(ts * 7 + ph_)) if gemessen else 0.0)
    bpy.context.view_layer.update()
    return p, fw, nr


def becken():
    nk = KF.rig.matrix_world @ KF.rig.pose.bones["neck01"].head
    return (KF.rig.matrix_world @ KF.PEL) * .55 + nk * .45


def kopf():
    return KF.rig.matrix_world @ KF.rig.pose.bones["head"].head + Vector((0, 0, .05))


def fuesse():
    return (KF.Z["fuss_L"].matrix_world.translation + KF.Z["fuss_R"].matrix_world.translation) / 2


# ======================================================================  Kamera
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam
cam.data.clip_start = .03; cam.data.clip_end = 12000; cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
cam.data.dof.use_dof = True
pt_f, fw_f, nr_f = kurs(S_FALLE)
SZ = [
    # t0, t1, ts0, ts1, modus, pos0, pos1, ziel0, ziel1, brennweite   (S+ = im Pistensystem: vor, links, Normale)
    (0.00, 1.50, 10.55, 10.85, "S+", (1.6, -2.4, .35), (1.2, -2.4, .35), "B", "B", 22),                          # Aufhaenger: volles Tempo
    (1.50, 2.60, 3.0, 4.1, "S+", (-6.5, -1.2, 3.0), (-6.0, -1.0, 2.8), (30, 0, -8), (30, 0, -8), 20),            # gerade runter
    (2.60, 3.70, 10.4, 10.95, "P", pt_f + Vector((14, 7, 1.0)), pt_f + Vector((14, 7, 1.0)), "B", "B", 40),       # wie schnell? frontal
    (3.70, 5.90, 0.0, 0.0, "P", Vector((1350, -950, 420)), Vector((1250, -880, 400)), Vector((250, 0, -120)), Vector((250, 0, -120)), 26),  # Vars aus der Luft
    (5.90, 8.20, -1.4, .9, "P", kurs(4)[0] + Vector((0, -5.5, 2.2)), kurs(4)[0] + Vector((0, -5.0, 2.2)), "B", "B", 26),   # Abstossen am Start
    (8.20, 10.40, .8, 3.2, "P", Vector((30, -26, z_kurs(30) + 6)), Vector((31, -26, z_kurs(31) + 6)), "B", "B", 60),  # 45 Grad von der Seite
    (10.40, 12.40, 4.0, 4.5, "S+", (1.3, -.6, .55), (1.25, -.55, .5), "KO", "KO", 34),                           # Anzug + Aero-Helm
    (12.40, 14.20, 4.5, 5.0, "S+", (.6, -2.4, .45), (.3, -2.4, .45), "FU", "FU", 18),                            # Skier 2,4 m
    (14.20, 15.40, 5.0, 5.45, "S+", (0, -2.6, .5), (0, -2.6, .5), "B", "B", 26),                                 # Ei
    (15.40, 18.40, 3.2, 6.2, "S+", (5.0, 1.4, 1.0), (7.0, 1.8, 1.4), "B", "B", 28),                              # 200 km/h in < 6 s
    (18.40, 20.40, 7.6, 8.6, "P", kurs(weg(8.1))[0] + Vector((0, -6, .6)), kurs(weg(8.1))[0] + Vector((0, -6, .6)), "B", "B", 24),  # rauscht vorbei
    (20.40, 22.00, 9.8, 10.7, "P", pt_f + Vector((-6, -12, 4)), pt_f + Vector((-6, -12, 4)), "B", "B", 55),    # Lichtschranke
    (22.00, 24.40, 10.75, 12.0, "P", TAF + Vector((20, 18, 3.0)), TAF + Vector((19, 17, 3.0)), TAF + Vector((0, 0, 6)), TAF + Vector((0, 0, 6)), 30),  # Tafel 255.50
    (24.40, 27.30, T_STOP - .6, T_STOP + 2.3, "S+", (5.5, -3.0, 2.6), (4.2, -4.3, 2.9), "B", "B", 26),           # Jubel im Auslauf
    (27.30, 28.00, 10.41, 10.55, "S+", (1.6, -2.4, .35), (1.6, -2.4, .35), "B", "B", 22),                        # Loop: fuehrt nahtlos in den Anfang
]


def zustand(t):
    for s in SZ:
        if s[0] <= t < s[1]:
            break
    k = (t - s[0]) / (s[1] - s[0])
    ts = s[2] + (s[3] - s[2]) * k
    k = ease(k) * .7 + k * .3
    p, fw, nr = figur(ts)
    le = nr.cross(fw).normalized()
    bk = becken()
    o = Vector(lerpv(s[5], s[6], k))
    if s[4] == "S+":
        pos = p + fw * o.x + le * o.y + nr * o.z
        ziel = {"B": bk, "KO": kopf(), "FU": fuesse()}.get(s[7]) if isinstance(s[7], str) else p + fw * lerpv(s[7], s[8], k)[0] + le * lerpv(s[7], s[8], k)[1] + nr * lerpv(s[7], s[8], k)[2]
    else:
        pos = o
        ziel = bk if s[7] == "B" else Vector(lerpv(s[7], s[8], k))
    cam.location = pos; d = ziel - pos; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = s[9]; cam.data.dof.focus_distance = d.length; cam.data.dof.aperture_fstop = 2.8 if d.length < 6 else 11
    zit = .006 + .02 * seg(tempo(ts), 40, 70) * (1 if s[4] == "S+" else 0)
    cam.location += Vector((zit * math.sin(t * 37.3), zit * math.cos(t * 41.1), zit * math.sin(t * 29.7)))


os.makedirs(A.ordner, exist_ok=True)
N = int(round(D * A.fps))
liste = [int(round(float(x) * A.fps)) for x in A.nur.split(",")] if A.nur else list(range(A.start, N))
for f in liste:
    pfad = os.path.join(A.ordner, f"speed_{f:04d}.png")
    if os.path.exists(pfad) and not A.nur:
        continue
    zustand(f / A.fps); bpy.context.view_layer.update(); zustand(f / A.fps)
    sc.render.filepath = pfad
    print("CAM", f, tuple(round(c, 1) for c in cam.location), flush=True)
    bpy.ops.render.render(write_still=True); print("FERTIG", pfad, flush=True)
