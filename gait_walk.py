# gait_walk.py
#
# WALK / STOP.

from math import exp, sin, cos, sqrt, pi
from gait_base import Gait

DEG2RAD = 0.017453292519943295


class Walk(Gait):
    name = "WALK"
    stand_only = False

    def __init__(self, ctx):
        Gait.__init__(self, ctx)
        m = self.cfg["motion"]
        w = self.cfg["walk"]
        self.vmax = m["vmax_walk"]
        self.tau = 0.0                      # targets are already smooth
        self.tau_b = max(m["tau_body_ms"], 1.0) / 1000.0      # never 0: exp(-dt/0) would raise
        self.tau_s = max(m["tau_stride_ms"], 1.0) / 1000.0
        self.cyc_slow = w["cycle_ms"][0] / 1000.0
        self.cyc_fast = w["cycle_ms"][1] / 1000.0
        self.lift_full = max(float(w["lift_full_mm"]), 0.1)      # 0 would divide by zero
        # Fewest servo frames per walk cycle we allow. On a slow UART (9600 baud
        # = ~150 ms per frame) a 0.5 s cycle is only 3 frames: the swing arc and
        # the stance line turn into a few straight jumps, feet drag and lift at
        # the wrong time. So the cycle is stretched to min_samples * frame time.
        self.min_samples = float(w["min_samples"])
        # Coxa limit -> longest stride the legs can follow without the soft
        # limit clipping the foot path (a clipped foot is dragged over the floor).
        geo = self.cfg["geometry"]
        cl = geo["limits"]["coxa"]
        self.a1 = float(geo["a1"])
        self.sin_cox = sin(min(abs(cl[0]), abs(cl[1])) * DEG2RAD)
        self.phase = 0.0
        self.wt = -1
        self.off = []
        self.sw = 0.5
        # filtered values: h, R, rx, ry, rz, bx, by, sx, sy, turn
        self.f = [0.0] * 10
        self.moving = False

    # -------------------------------------------------------------- gait type
    def _set_type(self, wt):
        n = self.r.n
        if wt == 1 and n % 2 == 0:            # pairs: leg i and leg i+n/2 swing together
            half = n // 2
            self.off = [(i % half) / half for i in range(n)]
            self.sw = 1.0 / half
        elif wt == 2:                         # wave: one leg at a time, around the body
            self.off = [i / n for i in range(n)]
            self.sw = 1.0 / n
        else:                                 # tripod
            wt = 0
            self.off = [0.0 if (i % 2) == 0 else 0.5 for i in range(n)]
            self.sw = 0.5
        self.wt = wt

    # ------------------------------------------------------------------ targets
    def _targets(self):
        st = self.st
        moving = (not self.stand_only) and st.speed >= 1
        if moving:
            sx, sy, tn = st.dx, st.dy, st.turn_angle
            bx = by = 0.0
        else:
            sx = sy = tn = 0.0
            bx, by = st.dx, st.dy
        return (moving, (st.height, st.spread, st.rx * 0.01, st.ry * 0.01, st.rz, bx, by, sx, sy, tn))

    def enter(self):
        st = self.st
        self._set_type(st.wtype)
        moving, tg = self._targets()
        f = self.f
        for k in range(10):
            f[k] = tg[k]
        f[7] = f[8] = f[9] = 0.0                     # always start from zero stride
        self.r.pose_all(f[0], f[1], f[2], f[3], f[4], f[5], f[6])
        self.moving = False
        self.idle = False

    # --------------------------------------------------------------------- step
    def step(self, dt):
        st = self.st
        r = self.r
        moving, tg = self._targets()
        if not moving and st.wtype != self.wt:
            self._set_type(st.wtype)
        f = self.f
        ab = 1.0 - exp(-dt / self.tau_b)
        as_ = 1.0 - exp(-dt / self.tau_s)
        ch = 0.0
        for k in range(10):
            d = tg[k] - f[k]
            if d > 0.001 or d < -0.001:
                d *= ab if k < 7 else as_
                f[k] += d
                ch += d if d > 0.0 else -d
            else:
                f[k] = tg[k]
        # nothing is moving and nothing changed -> targets are unchanged, skip IK
        if not moving and ch < 1e-4 and self.idle:
            return
        self.idle = not moving and ch < 1e-4

        h = f[0]
        R = f[1]
        rx = f[2]
        ry = f[3]
        rz = f[4]
        bx = f[5]
        by = f[6]
        sx = f[7]
        sy = f[8]
        tn = f[9]

        sm = sqrt(sx * sx + sy * sy) + (tn if tn > 0.0 else -tn) * R * DEG2RAD

        # stride limiter. A foot that moves within a circle of radius s around its
        # neutral point (distance b from the coxa axis) swings the coxa by at most
        # asin(s / b) - in ANY direction, radial + tangential combined. Keep the
        # stride inside the coxa limit (5 % margin).
        b = R - self.a1
        if b > 1.0:
            lim = 0.95 * b * self.sin_cox
            if sm > lim:
                k = lim / sm
                sx *= k
                sy *= k
                tn *= k
                sm = lim

        # leg lift scales with stride length (no marching in place)
        lf = sm / self.lift_full
        if lf > 1.0:
            lf = 1.0
        lift = st.raise_h * lf

        if moving:
            sp = st.speed
            cyc = self.cyc_slow + (self.cyc_fast - self.cyc_slow) * (sp - 1) / 99.0
            cmin = self.min_samples * self.ctx.frame_s
            if cyc < cmin:
                cyc = cmin
            if cyc < 0.05:                    # cycle_ms = 0 and min_samples = 0 would divide by zero
                cyc = 0.05
            ph = self.phase + dt / cyc
            if ph >= 1.0:
                ph -= 1.0
            self.phase = ph
        phase = self.phase

        flat = (tn < 1e-3 and tn > -1e-3 and rz < 1e-3 and rz > -1e-3)
        stance = 1.0 - self.sw
        sw = self.sw
        off = self.off
        rc = r.c
        rs = r.s
        for i in range(r.n):
            p = phase + off[i]
            if p >= 1.0:
                p -= 1.0
            if p < stance:                     # stance: foot slides backwards along the ground
                u = 1.0 - 2.0 * p / stance
                z = 0.0
            else:                              # swing: forward arc with lift
                s = (p - stance) / sw
                u = -cos(pi * s)
                z = lift * sin(pi * s)
            c = rc[i]
            sn = rs[i]
            if flat:
                x = R * c
                y = R * sn
            else:
                a = (u * tn + rz) * DEG2RAD
                ca = cos(a)
                sa = sin(a)
                x = R * (c * ca - sn * sa)
                y = R * (sn * ca + c * sa)
            r.foot(i, x + u * sx - bx, y + u * sy - by, R * (rx * c + ry * sn) - h + z)
        self.moving = moving


class Stand(Walk):
    """STOP.: "no handler, the robot freezes wherever it was" (including
    with a leg mid-air). v5: smoothly settles into the neutral stance and
    holds it."""
    name = "STOP"
    stand_only = True
