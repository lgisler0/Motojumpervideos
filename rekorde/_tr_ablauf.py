# ======================================================================  IK
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


# ======================================================================  Zuschauer: Lobby und Terrasse
BAR_M = mat("absperrung", "1b1b1f", .4, metal=.6); BAND_M = mat("absperrband", "c9a24a", .4)
PUBLIKUM = []
rp = random.Random(4)


def absperrung(a, b):
    a, b = Vector(a), Vector(b); n = max(1, int((b - a).length / 1.6))
    for k in range(n + 1):
        p_ = a.lerp(b, k / n); zyl("pfosten_abs", .035, 1.0, p_ + Vector((0, 0, .5)), BAR_M, v=12)
        zyl("fuss_abs", .16, .03, p_ + Vector((0, 0, .015)), BAR_M, v=16)
        if k < n:
            q_ = a.lerp(b, (k + 1) / n); rohr("band_abs", p_ + Vector((0, 0, .92)), q_ + Vector((0, 0, .92)), .025, BAND_M)


def leute(x0, x1, y0, sy, reihen, z, blick, dichte=.8):
    for reihe in range(reihen):
        x = x0
        while x < x1:
            x += rp.uniform(.55, .8)
            if rp.random() > dichte:
                continue
            o = bpy.data.objects.new("pub_%d" % len(PUBLIKUM), rp.choice(ZUSCH_ME)); sc.collection.objects.link(o)
            o.location = (x, y0 + sy * (reihe * .7 + rp.uniform(-.15, .15)), z)
            o.rotation_euler = (0, 0, blick + rp.uniform(-.5, .5)); s_ = rp.uniform(.95, 1.05); o.scale = (s_, s_, s_)
            PUBLIKUM.append((o, z, rp.uniform(0, 6)))


for sy in (-1, 1):
    absperrung(LOB + Vector((-6, sy * 2.6, 0)), LOB + Vector((18.5, sy * 2.6, 0)))
    leute(LOB.x - 6, LOB.x + 18, LOB.y + sy * 3.2, sy, 3, 0, (0 if sy > 0 else P))
    absperrung(DECK + Vector((-19, sy * 1.9, 0)) + Vector((0, -5, 0)), DECK + Vector((-13.2, sy * 1.9, 0)) + Vector((0, -5, 0)))
    leute(DECK.x - 19.3, DECK.x - 13.4, DECK.y - 5 + sy * 2.5, sy, 2, DECK.z, (0 if sy > 0 else P), .85)
print("publikum", len(PUBLIKUM))

# ======================================================================  Gang: Fusspunkte (Stufen zwei auf einmal, Lobby und Terrasse flach)
LANE = GAP + .35
RAIL_Y = GAP + .04
T_STAIR_END = 571.0
LOBBY_SCHRITT = 1.1
LOBBY_ANZ = 9.8 / LOBBY_SCHRITT
N_FLOORS = 85
TP = T_STAIR_END / (N_FLOORS * 14 + LOBBY_ANZ)
T_ST = LOBBY_ANZ * TP
DECK_SCHRITT = .96
START = LOB + Vector((10.0, 0, 0))


def plan_lokal(j):
    """Fusspunkt-Mitte j (0..13) innerhalb eines Geschosses; z = Stufenoberflaeche"""
    if j <= 4:
        i = 2 * j + 1; return Vector(((i + .5) * STUFE_T, -LANE, (i + 1) * STUFE_H))
    if j == 5:
        return Vector((LAUF_L + .35, -GAP - .25, GH / 2))
    if j == 6:
        return Vector((LAUF_L + .4, GAP + .25, GH / 2))
    if j <= 11:
        i = 2 * (j - 7) + 1; return Vector((LAUF_L - (i + .5) * STUFE_T, LANE, GH / 2 + (i + 1) * STUFE_H))
    if j == 12:
        return Vector((-.35, GAP + .25, GH))
    return Vector((-.4, -GAP - .25, GH))


def c_treppe(k):
    F = k // 14; j = k % 14
    return plan_lokal(j) + Vector((0, 0, F * GH))


def c_lobby(k):
    return START + Vector((LOBBY_SCHRITT * k, 0, 0))


def c_deck(k):
    return TUER_POS + Vector((-.2 - DECK_SCHRITT * k, 0, 0))


DECK_STOP = 5.4


def phase(ts):
    """liefert (Mittelpunktfunktion, q, qmax)"""
    if ts < T_ST:
        return c_lobby, max(-.001, ts / TP), LOBBY_ANZ + 3
    if ts < T_STAIR_END:
        return c_treppe, (ts - T_ST) / TP, 1e9
    return c_deck, (ts - T_STAIR_END) / TP, DECK_STOP


def C(cf, x):
    k = math.floor(x); f = x - k
    return cf(k).lerp(cf(k + 1), f)


def links(fw):
    return Vector((-fw.y, fw.x, 0))


def fwd_at(cf, x):
    d = C(cf, x + .35) - C(cf, x - .35); d.z = 0
    return d.normalized() if d.length > 1e-4 else Vector((1, 0, 0))


def fusspunkt(cf, k):
    fw = fwd_at(cf, k); seite = .095 if k % 2 == 0 else -.095
    return cf(k) + links(fw) * seite + Vector((0, 0, .1))


def floor_von(ts):
    if ts < T_ST:
        return 0
    if ts >= T_STAIR_END:
        return N_FLOORS
    return int(((ts - T_ST) / TP) // 14)


def tsp(F, j):
    return T_ST + (F * 14 + j) * TP


def figur(ts):
    KF.zuruecksetzen()
    for c in KF.IK.values():
        c.influence = 1.0
    cf, q, qmax = phase(ts)
    steht = q < 0 or q >= qmax
    qq = min(max(q, 0.0), qmax)
    k = math.floor(qq); f = qq - k
    treppe = cf is c_treppe
    if steht:
        fw = fwd_at(cf, qq)
        lf = cf(math.floor(qq)) if q >= qmax else cf(0)
        for sd, s_ in (("L", 1), ("R", -1)):
            KF.Z["fuss_" + sd].location = lf + links(fw) * (s_ * .12) + Vector((0, 0, .1)) + fw * (.12 if (sd == "L") == (q < 0) else 0) * (-1 if q < 0 else 1)
        pel = lf + Vector((0, 0, .95 if q >= qmax else .9))
        lean = 0.0 if q >= qmax else .15
    else:
        stand = fusspunkt(cf, k)
        sw0 = fusspunkt(cf, k - 1); sw1 = fusspunkt(cf, k + 1)
        if k == 0:
            sw0 = cf(0) + links(fwd_at(cf, 0)) * (.095 if k % 2 else -.095) + Vector((0, 0, .1)) - fwd_at(cf, 0) * .3
        e = ease(f)
        swing = sw0.lerp(sw1, e) + Vector((0, 0, (.26 if treppe else .18) * math.sin(P * f)))
        # Ferse loest sich am Ende der Stuetzphase
        stand = stand + Vector((0, 0, .05 * ease((f - .6) / .4)))
        st_sd, sw_sd = ("L", "R") if k % 2 == 0 else ("R", "L")
        KF.Z["fuss_" + st_sd].location = stand; KF.Z["fuss_" + sw_sd].location = swing
        fw = fwd_at(cf, qq)
        pel = C(cf, qq - .5) + Vector((0, 0, (.83 if treppe else .9) + .035 * math.sin(2 * P * f - P / 2)))
        pel -= fw * (.02 if treppe else 0)
        lean = .38 if treppe else .2
        if cf is c_deck:
            lean *= 1 - ease((q - (DECK_STOP - 1.2)) / 1.2)
    up = Vector((0, 0, 1)); le = links(fw)
    H = (fw * math.sin(lean) + up * math.cos(lean)); Fc = (fw * math.cos(lean) - up * math.sin(lean))
    rq = rig_mat(H, Fc).to_quaternion()
    KF.rig.rotation_mode = "QUATERNION"; KF.rig.rotation_quaternion = rq
    KF.rig.location = pel - rq.to_matrix() @ (KF.PEL * KF.SK)
    for sd, s_ in (("L", 1), ("R", -1)):
        KF.Z["knie_" + sd].location = pel + fw * 2.0 + le * (s_ * .35) - up * .3
        KF.Z["ell_" + sd].location = pel - fw * 1.2 + le * (s_ * .45) + up * .3     # Ellbogen zeigen nach hinten
    # Arme: links am Gelaender (Treppe), rechts pumpt; flach: beide pumpen
    ph = 2 * P * (qq / 2.0)
    schulter = pel + H * .5
    jubel = ease((ts - (T_STAIR_END + DECK_STOP * TP + .25)) / .8) if cf is c_deck else 0.0
    if treppe:
        xr = qq - .5 + .25
        rail = C(cf, xr) + le * (LANE - RAIL_Y) * .8
        rail.z = C(cf, xr).z + .95 + .04
        KF.Z["hand_L"].location = rail
        sp = math.cos(ph)                               # rechter Arm schwingt gegengleich zum rechten Bein
        KF.Z["hand_R"].location = schulter - le * (.19 - .04 * sp) + fw * (.06 + .2 * sp) - H * (.36 - .14 * sp)
    elif steht and q < 0:
        for sd, s_ in (("L", 1), ("R", -1)):
            KF.Z["hand_" + sd].location = schulter + le * (s_ * .26) - H * .42 + fw * (.15 if sd == "R" else -.05)
    else:
        amp = 0 if steht else 1
        for sd, s_ in (("L", 1), ("R", -1)):
            sp = (-math.cos(ph) if sd == "L" else math.cos(ph)) * amp      # Arm gegengleich zum Bein, Ellbogen ~90 Grad
            KF.Z["hand_" + sd].location = schulter + le * (s_ * (.2 - .05 * max(0, sp))) + fw * (.08 + .24 * sp) - H * (.36 - .16 * sp)
    if jubel > 0:
        KF.IK["hand_L"].influence = 1 - jubel; KF.IK["hand_R"].influence = 1 - jubel
        KF.dreh("upperarm01.L", z=-.72 + 3.0 * jubel, x=.2 * jubel); KF.dreh("upperarm01.R", z=.72 - 3.0 * jubel, x=.2 * jubel)
        KF.dreh("lowerarm01.L", x=-.4 * jubel); KF.dreh("lowerarm01.R", x=-.4 * jubel)
    KF.dreh("neck01", x=-.6 * lean + .15 * jubel)
    for sd in ("L", "R"):
        for ff in range(2, 6):
            for g in (1, 2, 3):
                KF.dreh(f"finger{ff}-{g}.{sd}", x=(1.2 if (treppe and sd == "L") else .55 + .12 * g) * (1 - jubel) + .12)
        for g in (2, 3):
            KF.dreh(f"finger1-{g}.{sd}", x=.45 * (1 - jubel))                    # Daumen locker angelegt
    # Treppenhaus mitfuehren (identische Geschosse), Stockwerk-Schilder
    Fi = floor_von(ts)
    STACK.location = (0, 0, GH * (Fi - 6))
    for t_, g in SCHILDER:
        Fa = Fi - 6 + g
        txt = str(Fa + 2) if Fa >= 0 else ""
        if t_.data.body != txt:
            t_.data.body = txt
    # Tuer und Zielband
    UHR_EM.default_value = 2.5 if ts >= 573.0 else 0.0
    TUER_ANGEL.rotation_euler = (0, 0, 1.75 * ease((ts - (T_STAIR_END - .5)) / .5))
    zx = KF.rig.location.x
    gerissen = cf is c_deck and C(cf, qq).x < ZIEL_POS.x + .15
    ZIELBAND.hide_render = gerissen
    for e_, h_, sy in ZB_HALB:
        h_.hide_render = not gerissen
        if gerissen:
            dt = ts - 573.0
            e_.rotation_euler = (sy * -1.3 * ease(dt / .6) + sy * .1 * math.sin(dt * 9) * math.exp(-dt * 2), 0, -.5 * sy * ease(dt / .4))
    for o, z0, ph_ in PUBLIKUM:
        o.location.z = z0 + (.1 * max(0, math.sin(ts * 7 + ph_)) if ts > 572.8 else .015 * math.sin(ts * 2 + ph_))
    bpy.context.view_layer.update()
    return pel, fw


def becken():
    nk = KF.rig.matrix_world @ KF.rig.pose.bones["neck01"].head
    return (KF.rig.matrix_world @ KF.PEL) * .55 + nk * .45


def kopf():
    return KF.rig.matrix_world @ KF.rig.pose.bones["head"].head + Vector((0, 0, .1))


def fuesse():
    return (KF.Z["fuss_L"].matrix_world.translation + KF.Z["fuss_R"].matrix_world.translation) / 2 + Vector((0, 0, .15))


# ======================================================================  Kamera
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam
cam.data.clip_start = .03; cam.data.clip_end = 9000; cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
cam.data.dof.use_dof = True
Fh = 40; Ff = 20; Fz = 30; Fg = 60
SZ = [
    # t0, t1, ts0, ts1, modus, pos0, pos1, ziel0, ziel1, brennweite, extra
    (0.00, 1.40, tsp(Fh, 2.3), tsp(Fh, 3.2), "R+", (-1.5, .05, -.45), (-1.35, .1, -.4), "KO", "KO", 16, {}),       # Aufhaenger: von unten hinten, Zeitlupe
    (1.40, 2.40, tsp(Ff, 1.0), tsp(Ff, 3.0), "R+", (.75, -.55, -.25), (.8, -.55, -.25), "FU", "FU", 20, {}),          # Fuesse, zwei Stufen
    (2.40, 3.70, tsp(10, 3), tsp(10, 5.5), "S", (1.4, 0, .5), (1.4, 0, .5), (1.4, .02, 40), (1.5, .3, 40), 14, {"dF": -2}),  # Blick hoch ins Treppenauge
    (3.70, 5.90, 300, 300, "P", E + Vector((-420, -620, 260)), E + Vector((-380, -560, 280)), E + Vector((0, 0, 190)), E + Vector((0, 0, 205)), 24, {}),   # Empire State Building
    (5.90, 7.50, 300, 300, "P", E + Vector((-55, -75, 3)), E + Vector((-55, -75, 8)), E + Vector((-10, -10, 120)), E + Vector((0, 0, 330)), 14, {}),  # Fassade hoch
    (7.50, 10.00, -1.2, 1.6, "P", LOB + Vector((12.8, -1.9, 1.0)), LOB + Vector((13.6, -1.8, 1.15)), "B", "B", 22, {}),  # Lobby-Start
    (10.00, 13.10, tsp(Fz, -.1), tsp(Fz, 4.3), "R+", (-1.35, -.38, .45), (-1.2, -.36, .5), "B", "B", 20, {}),        # zwei Stufen + Gelaender
    (13.10, 15.60, tsp(Fg, -.1), tsp(Fg, 4.1), "R+", (.95, -.12, .45), (.85, -.1, .42), "KO", "KO", 42, {}),          # Gesicht
    (15.60, 16.50, tsp(55, 11.3), tsp(55, 13.4), "S", (1.3, -.75, GH + 1.3), (1.3, -.75, GH + 1.35), (-1.28, 0, GH + 1.2), (-1.28, 0, GH + 1.2), 18, {"dF": 0}),
    (16.50, 17.40, tsp(66, 11.3), tsp(66, 13.4), "S", (1.3, -.75, GH + 1.3), (1.3, -.75, GH + 1.35), (-1.28, 0, GH + 1.2), (-1.28, 0, GH + 1.2), 18, {"dF": 0}),
    (17.40, 18.40, tsp(77, 11.3), tsp(77, 13.4), "S", (1.3, -.75, GH + 1.3), (1.3, -.75, GH + 1.35), (-1.28, 0, GH + 1.2), (-1.28, 0, GH + 1.2), 18, {"dF": 0}),
    (18.40, 20.50, 569.9, 572.0, "P", TUER_POS + Vector((-6.5, -1.5, 1.3)), TUER_POS + Vector((-6.3, -1.4, 1.3)), TUER_POS + Vector((-.5, 0, 1.2)), TUER_POS + Vector((-1.8, 0, 1.2)), 24, {}),  # Tuer geht auf
    (20.50, 22.40, 572.15, 573.45, "P", ZIEL_POS + Vector((-2.5, 1.5, 1.0)), ZIEL_POS + Vector((-2.4, 1.4, 1.05)), "B", "B", 26, {}),       # Ziel 9:33
    (22.40, 26.60, 573.6, 577.8, "B+", Vector((-1.6, 1.2, -.2)), Vector((-1.3, 2.4, .5)), "B", "B", 22, {}),        # Jubel mit Skyline
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
    o = lerpv(s[5], s[6], k)
    if s[4] == "R+":
        pos = bk + fw * o[0] + links(fw) * o[1] + Vector((0, 0, o[2]))
    elif s[4] == "B+":
        pos = bk + Vector(o)
    elif s[4] == "S":
        base = Vector((0, 0, GH * (floor_von(s[2]) + s[10].get("dF", 0))))
        pos = base + Vector(o)
    else:
        pos = Vector(o)
    if s[7] == "B":
        ziel = bk
    elif s[7] == "KO":
        ziel = kopf()
    elif s[7] == "FU":
        ziel = fuesse()
    elif s[4] == "S":
        ziel = base + Vector(lerpv(s[7], s[8], k))
    else:
        ziel = lerpv(s[7], s[8], k)
    cam.location = pos; d = ziel - pos; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = s[9]; cam.data.dof.focus_distance = d.length; cam.data.dof.aperture_fstop = 2.8 if d.length < 6 else 11
    zit = .004
    cam.location += Vector((zit * math.sin(t * 7.3), zit * math.cos(t * 5.1), zit * math.sin(t * 9.7)))


os.makedirs(A.ordner, exist_ok=True)
N = int(round(D * A.fps))
liste = [int(round(float(x) * A.fps)) for x in A.nur.split(",")] if A.nur else list(range(A.start, N))
for f in liste:
    pfad = os.path.join(A.ordner, f"treppe_{f:04d}.png")
    if os.path.exists(pfad) and not A.nur:
        continue
    zustand(f / A.fps); bpy.context.view_layer.update(); zustand(f / A.fps)
    sc.render.filepath = pfad
    print("CAM", f, tuple(round(c, 2) for c in cam.location), tuple(round(c, 2) for c in becken()), flush=True)
    bpy.ops.render.render(write_still=True); print("FERTIG", pfad, flush=True)
