from math import sin, cos, exp, radians
import kin

K_PULSE = 2000.0 / 180.0        # us per degree (same as v4: -90..90 -> 500..2500)
DEG2RAD = 0.017453292519943295


class Robot:
    def __init__(self, cfg, bus):
        g = cfg["geometry"]
        self.geo = kin.Geo(g)
        self.bus = bus
        n = cfg["n_legs"]
        self.n = n
        self.N = 3 * n
        wiring = cfg["wiring"]

        # Leg mount angles: a single legs_clockwise flag mirrors the whole order.
        step = 360.0 / n
        if wiring.get("legs_clockwise", False):
            step = -step
        self.leg_deg = [(i * step) % 360.0 for i in range(n)]
        self.t1 = [radians(a) for a in self.leg_deg]
        self.c = [cos(t) for t in self.t1]
        self.s = [sin(t) for t in self.t1]
        self.ox = [self.geo.a1 * v for v in self.c]
        self.oy = [self.geo.a1 * v for v in self.s]

        lim = g["limits"]
        offs = g["offsets"]
        self.pins = []
        self.sgn = []
        self.lo = []
        self.hi = []
        self.off = []
        for i in range(n):
            w = wiring[str(i)]
            self.pins.extend(w["pins"])
            inv = w.get("invert", [True, False, True])
            for v in inv:
                self.sgn.append(-1.0 if v else 1.0)
            for name in ("coxa", "femur", "tibia"):
                self.lo.append(float(lim[name][0]))
                self.hi.append(float(lim[name][1]))
            self.off.extend(offs)
        self.leg_of = [j // 3 for j in range(self.N)]

        # Calibration (format check: 3 numbers per leg, otherwise zero).
        cl = cfg["poses"]["cal_limit"]
        self.cal = [0] * self.N
        self.cal_limit = cl
        for i in range(n):
            v = cfg["cal"].get(str(i))
            if isinstance(v, list) and len(v) == 3:
                for k in range(3):
                    x = v[k]
                    if isinstance(x, (int, float)) and x == x:
                        self.cal[i * 3 + k] = max(-cl, min(cl, x))
        self.bias = [self.off[j] + self.cal[j] for j in range(self.N)]

        self.fold = list(cfg["poses"]["fold"])
        self.cur = [0.0] * self.N
        self.tgt = [0.0] * self.N
        self.tau = 0.0            # joint smoothing time constant, s (0 = no smoothing)
        self.vmax = 600.0         # joint speed cap, deg/s
        self.err = 0.0            # max |tgt-cur| after the last update() call
        self.sat = 0              # count of unreachable-target events (diagnostics)
        self.raw = [False] * n    # legs currently in ZERO mode (send a raw 1500 center pulse)
        self.last = [-1] * self.N # last pulse value actually sent per channel
        self.refresh_ms = cfg["refresh_ms"]
        self.t_scale = cfg["servo_t_scale"]
        self._since_full = 0.0

    # ------------------------------------------------------------ targets
    def foot(self, i, x, y, z):
        """Set leg i's target from a foot point (x, y, z) in the body frame,
        with soft joint-limit clamping."""
        j = i * 3
        tgt = self.tgt
        if kin.ik(self.geo, self.t1[i], self.ox[i], self.oy[i], x, y, z, tgt, j):
            self.sat += 1
        lo = self.lo
        hi = self.hi
        for k in range(j, j + 3):
            v = tgt[k]
            if v < lo[k]:
                tgt[k] = lo[k]
            elif v > hi[k]:
                tgt[k] = hi[k]

    def joints(self, i, coxa, femur, tibia, soft=True):
        """Set leg i's target directly by angles. soft=False skips clamping
        (needed for poses like the fold pose, which sit outside the soft IK
        limits but are still within the 500..2500 us pulse range)."""
        j = i * 3
        tgt = self.tgt
        tgt[j] = coxa
        tgt[j + 1] = femur
        tgt[j + 2] = tibia
        if soft:
            lo = self.lo
            hi = self.hi
            for k in range(j, j + 3):
                if tgt[k] < lo[k]:
                    tgt[k] = lo[k]
                elif tgt[k] > hi[k]:
                    tgt[k] = hi[k]

    def pose_all(self, h, R, rx, ry, yaw, bx, by, lifts=None, lift_mm=0.0):
        """All legs at once: stance height h, radius R, tilt (rx, ry - as a
        slope fraction, same convention as v4), body yaw (deg), body shift
        (bx, by). lifts[i] (0..1) * lift_mm optionally raises leg i (dances)."""
        a = yaw * DEG2RAD
        cy = cos(a)
        sy = sin(a)
        c = self.c
        s = self.s
        for i in range(self.n):
            ci = c[i]
            si = s[i]
            x = R * (ci * cy - si * sy) - bx
            y = R * (si * cy + ci * sy) - by
            z = R * (rx * ci + ry * si) - h
            if lifts is not None:
                z += lifts[i] * lift_mm
            self.foot(i, x, y, z)

    def fold_pose(self, k=1.0):
        """k=1 fully folded, k=0 fully unfolded (0/0/0)."""
        f = self.fold
        for i in range(self.n):
            self.joints(i, 0.0, f[1] * k, f[2] * k, False)

    def set_cal(self, i, k, value):
        cl = self.cal_limit                # clamp here too (it used to be only on load)
        if value > cl:
            value = cl
        elif value < -cl:
            value = -cl
        j = i * 3 + k
        self.cal[j] = value
        self.bias[j] = self.off[j] + value

    def hold(self):
        for j in range(self.N):
            self.tgt[j] = self.cur[j]

    def snap(self):
        """Force current position := target (no motion)."""
        for j in range(self.N):
            self.cur[j] = self.tgt[j]
        self.err = 0.0

    def sync_center(self, legs):
        """After ZERO: assume the physical legs are now sitting at the 1500 us
        center pulse."""
        for i in legs:
            for k in range(3):
                j = i * 3 + k
                self.cur[j] = self.tgt[j] = -self.bias[j]
                self.last[j] = 1500

    # ------------------------------------------------------- interpolator
    def update(self, dt):
        """cur -> tgt: exponential smoothing (tau) plus a speed cap (vmax).
        Both depend only on dt, so motion looks the same at any loop rate."""
        cur = self.cur
        tgt = self.tgt
        tau = self.tau
        a = 1.0 if tau <= 0.0 else 1.0 - exp(-dt / tau)
        vm = self.vmax * dt
        e = 0.0
        for j in range(self.N):
            d = tgt[j] - cur[j]
            if d > 0.001 or d < -0.001:
                d *= a
                if d > vm:
                    d = vm
                elif d < -vm:
                    d = -vm
                cur[j] += d
                d = tgt[j] - cur[j]
                if d < 0.0:
                    d = -d
                if d > e:
                    e = d
            else:
                cur[j] = tgt[j]
        self.err = e

    # ------------------------------------------------------------- output
    def send(self, period_ms, dt_ms, t_override=None, force=False):
        """Build and send a ch24 command: only the channels that changed.
        Returns the number of bytes sent (0 = nothing to send)."""
        self._since_full += dt_ms
        if self._since_full >= self.refresh_ms:
            force = True
            self._since_full = 0.0
        cur = self.cur
        bias = self.bias
        sgn = self.sgn
        pins = self.pins
        last = self.last
        raw = self.raw
        leg_of = self.leg_of
        parts = []
        for j in range(self.N):
            if raw[leg_of[j]]:
                p = 1500
            else:
                p = int(1500.5 + sgn[j] * (cur[j] + bias[j]) * K_PULSE)
                if p < 500:
                    p = 500
                elif p > 2500:
                    p = 2500
            if p != last[j] or force:
                last[j] = p
                parts.append("#%dP%d" % (pins[j], p))
        if not parts:
            return 0
        t = t_override if t_override is not None else int(period_ms * self.t_scale)
        if t < 20:
            t = 20
        cmd = "".join(parts) + "T%d\r\n" % t
        self.bus.write(cmd)
        return len(cmd)
