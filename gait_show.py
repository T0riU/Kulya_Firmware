# gait_show.py
#
# DANCE and WAVE. Replaces esp_gait_dance.py / esp_gait_wave.py.


from math import exp
from gait_base import Gait
from dances_data import DANCES

DEG2RAD = 0.017453292519943295


class Dance(Gait):
    name = "DANCE"
    vmax = 450.0
    tau = 0.0

    def enter(self):
        st = self.st
        mf = float(self.cfg["dance"]["move_frac"])
        self.mf = 0.05 if mf < 0.05 else (1.0 if mf > 1.0 else mf)   # 0 would divide by zero in step()
        self.lift_mm = self.cfg["dance"]["lift_mm"]
        self.pose = [float(st.height), float(st.spread), 0.0, 0.0, 0.0, 0.0, 0.0]
        self.lifts = [0.0] * self.r.n
        self.pass_no = 0
        self._load()
        p = self.pose
        self.r.pose_all(p[0], p[1], p[2], p[3], p[4], p[5], p[6], self.lifts, self.lift_mm)

    def _load(self):
        did = self.st.dance_id                  # re-read every pass, same as v4
        n = len(DANCES)
        if did == 255:
            idx = self.pass_no % n              # 255 = play every dance in a loop
        else:
            idx = did if did < n else 0
        self.steps = DANCES[idx][1]
        self.i = 0
        self._begin()

    def _begin(self):
        st = self.st
        dur, h, rx, ry, yaw, bx, by, R, mask = self.steps[self.i]
        self.p0 = list(self.pose)
        self.l0 = list(self.lifts)
        self.p1 = [h if h else float(st.height), R if R else float(st.spread),
                   rx * DEG2RAD, ry * DEG2RAD, yaw, bx, by]
        self.l1 = [1.0 if (mask & (1 if (i & 1) == 0 else 2)) else 0.0 for i in range(self.r.n)]
        self.dur = dur * 100.0 / st.tempo
        self.t = 0.0

    def step(self, dt):
        self.t += dt
        while self.t >= self.dur:                # step finished -> advance (carry the remainder)
            rem = self.t - self.dur              # _begin() resets self.t, so keep the leftover here:
            self.pose = list(self.p1)            # dropping it made every step up to one tick too long
            self.lifts = list(self.l1)           # (on 9600 baud, ~150 ms/tick: dances ran ~55 % slow)
            self.i += 1
            if self.i >= len(self.steps):
                self.pass_no += 1
                self._load()
            else:
                self._begin()
            self.t = rem
        f = self.t / (self.dur * self.mf)
        if f > 1.0:
            f = 1.0
        s = f * f * (3.0 - 2.0 * f)
        p0 = self.p0
        p1 = self.p1
        p = self.pose
        for k in range(7):
            p[k] = p0[k] + (p1[k] - p0[k]) * s
        l0 = self.l0
        l1 = self.l1
        lf = self.lifts
        for i in range(len(lf)):
            lf[i] = l0[i] + (l1[i] - l0[i]) * s
        self.r.pose_all(p[0], p[1], p[2], p[3], p[4], p[5], p[6], lf, self.lift_mm)


class Wave(Gait):
    """Wave a SINGLE leg (leg_num, read once on entry), then return to WALK -
    same behaviour as v4. Body shift/tilt is now derived from the waving
    leg's direction (v4 hard-coded it for legs 4/5), so any leg can wave."""
    name = "WAVE"
    vmax = 400.0
    tau = 0.10

    SHIFT_MM = 22.0
    TILT = 0.15
    # (duration, body shifted?, waving-leg angles or None)
    SEQ = ((0.6, True, None),
           (0.6, True, (0, 60, 8)),
           (0.35, True, (-20, 60, 8)), (0.35, True, (20, 60, 8)),
           (0.35, True, (-20, 60, 8)), (0.35, True, (20, 60, 8)),
           (0.4, True, (0, 60, 8)),
           (0.6, False, None))

    def enter(self):
        st = self.st
        L = st.leg_num
        if not (0 <= L < self.r.n):
            st.gait = "STOP"
            self.i = len(self.SEQ)             # never run step() on a half-initialised object
            self.t = 0.0
            self.dur = 0.0
            self.r.pose_all(st.height, st.spread, 0.0, 0.0, 0.0, 0.0, 0.0)
            return
        self.leg = L
        c = self.r.c[L]
        s = self.r.s[L]
        # the body shifts AWAY from the waving leg, and tilts away too
        self.body = (-self.SHIFT_MM * c, -self.SHIFT_MM * s, -self.TILT * c, -self.TILT * s)
        self.i = 0
        self.t = 0.0
        self._apply()

    def _apply(self):
        st = self.st
        dur, on, ang = self.SEQ[self.i]
        r = self.r
        if on:
            bx, by, rx, ry = self.body
        else:
            bx = by = rx = ry = 0.0
        r.pose_all(st.height, st.spread, rx, ry, 0.0, bx, by)
        if ang is not None:
            r.joints(self.leg, ang[0], ang[1], ang[2], True)
        self.dur = dur * 100.0 / st.tempo

    def step(self, dt):
        self.t += dt
        if self.t < self.dur:
            return
        self.t -= self.dur                       # carry the remainder (see Dance.step)
        self.i += 1
        if self.i >= len(self.SEQ):
            self.st.gait = "WALK"                # done - return to walking (same as v4)
            return
        self._apply()
