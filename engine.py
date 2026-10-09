
import time
from gait_walk import Walk, Stand
from gait_pose import CE, Leg, Roll
from gait_show import Dance, Wave
from gait_cal import Zero, ZeroAll, Cal, save_calibration

try:
    _ticks_diff = time.ticks_diff          # MicroPython: correct across the ticks_ms() wrap-around
except AttributeError:                     # CPython (tests)
    _ticks_diff = lambda a, b: a - b

GAIT_CLASSES = {
    "WALK": Walk, "STOP": Stand, "CE": CE, "LEG": Leg, "ROLL": Roll,
    "DANCE": Dance, "WAVE": Wave, "ZERO": Zero, "ZEROALL": ZeroAll, "CAL": Cal,
}


class Settle:
    """A transitional pseudo-mode: drive the joints to the NEW mode's targets,
    then hand control over to it. This is what removes the jerk on a mode
    switch (v4 had no such thing at all - a switch was applied as-is,
    including e.g. a mid-dance pose)."""
    def __init__(self, vmax, tol, timeout_s, target):
        self.vmax = vmax
        self.tau = 0.0
        self.tol = tol
        self.timeout = timeout_s
        self.target = target
        self.t = 0.0

    def done(self, robot):
        return robot.err <= self.tol or self.t > self.timeout


class Engine:
    def __init__(self, cfg, robot, st):
        self.cfg = cfg
        self.robot = robot
        self.st = st
        self.gait = None
        self.pending = None
        self.settle = None
        self.cur_name = None
        self.notify_cb = None
        self._first_switch = True     # the very first switch uses vmax_boot, not vmax_settle
        self.frame_s = cfg["tick_ms"] / 1000.0   # real frame period, updated by main.py every loop
        self._switch(st.gait)

    # -------------------------------------------------------------- switching
    def _switch(self, name):
        cls = GAIT_CLASSES.get(name, Stand)
        g = cls(self)
        g.enter()
        target = list(self.robot.tgt)
        self.robot.tau = 0.0
        m = self.cfg["motion"]
        vmax = m["vmax_boot"] if self._first_switch else m["vmax_settle"]
        self._first_switch = False
        self.settle = Settle(vmax, m["settle_tol"], m["settle_timeout_ms"] / 1000.0, target)
        self.pending = g
        self.cur_name = name

    def _apply_actions(self):
        st = self.st
        if not st.actions:
            return
        for a in st.actions:
            if a == "SAVE":
                save_calibration(self.cfg.get("_cal_path", "calibration.json"), self.robot)
            elif a == "GETCAL" and self.notify_cb:
                r = self.robot
                i = st.leg_num
                if 0 <= i < r.n:
                    j = i * 3
                    self.notify_cb("CAL:%g,%g,%g;" % (r.cal[j], r.cal[j + 1], r.cal[j + 2]))   # %d cut 2.6 down to 2
        st.actions = []

    # -------------------------------------------------------------------- tick
    def tick(self, dt, now_ms):
        st = self.st
        link = self.cfg["link"]["timeout_ms"]
        if link and st.rx_ms and _ticks_diff(now_ms, st.rx_ms) > link:
            st.stop_motion()
            if st.gait not in ("STOP", "ZERO", "ZEROALL", "CAL"):
                st.gait = "STOP"

        self._apply_actions()

        if st.gait != self.cur_name:
            # exit() must go to the gait whose enter() ran LAST: the pending one
            # if we are still inside a Settle, otherwise the active one. (It used
            # to be called on the old, already-exited gait a second time - for
            # ZERO that re-ran sync_center() and snapped `cur` while the legs
            # were mid-transition, and the pending ZERO never released its legs.)
            last = self.pending if self.pending is not None else self.gait
            if last is not None:
                last.exit()
            self.gait = None
            self.pending = None
            self._switch(st.gait)

        robot = self.robot
        if self.settle is not None:
            self.settle.t += dt
            robot.vmax = self.settle.vmax
            robot.tau = self.settle.tau
            robot.update(dt)
            if self.settle.done(robot):
                self.settle = None
                self.gait = self.pending
                self.pending = None
        else:
            g = self.gait
            robot.vmax = g.vmax
            robot.tau = g.tau
            g.step(dt)
            robot.update(dt)

    def recover(self):
        """Called by main.py after an unexpected exception in tick(): drop
        whatever state the engine was in and fall back to a clean STOP."""
        r = self.robot
        raw = [i for i in range(r.n) if r.raw[i]]
        if raw:
            r.sync_center(raw)
            for i in raw:
                r.raw[i] = False
        self.gait = None
        self.pending = None
        self.settle = None
        self.cur_name = None
        self.st.stop_motion()
        self.st.gait = "STOP"
