# gait_cal.py
#
# ZERO / ZEROALL / CAL. Replaces esp_gait_zero.py + esp_gait_cal.py +
# esp_gait_getcal.py + esp_gait_save.py.

from gait_base import Gait

try:
    import ujson as json
except ImportError:
    import json


def save_calibration(path, robot):
    tmp = path + ".tmp"
    try:
        import os
        data = {}
        for i in range(robot.n):
            j = i * 3
            data[str(i)] = [robot.cal[j], robot.cal[j + 1], robot.cal[j + 2]]
        with open(tmp, "w") as f:
            json.dump(data, f)
        try:
            os.rename(tmp, path)
        except OSError:
            os.remove(path)
            os.rename(tmp, path)
        return True
    except Exception as e:
        print("[cal] save failed:", e)
        return False


class Zero(Gait):
    """Drive ONE servo group (leg_num) to a raw 1500 us pulse, for setting horns
    by eye. ZEROALL does the same for every leg. (ZERO used to have
    all_legs = True as well, so it was identical to ZEROALL, and exit()
    released whichever leg_num was selected at that moment - a leg selected
    at enter() stayed stuck on 1500 forever.)"""
    name = "ZERO"
    vmax = 9e9                 # instant - this needs the exact center, no smoothing
    tau = 0.0
    all_legs = False

    def enter(self):
        r = self.r
        self.legs = tuple(range(r.n)) if self.all_legs else (self.st.leg_num,)
        for i in self.legs:
            r.raw[i] = True
        r.hold()

    def _release(self):
        r = self.r
        r.sync_center(self.legs)           # current pose := "center", no jump
        for i in self.legs:
            r.raw[i] = False

    def step(self, dt):
        # leg_num changed while in ZERO: hand the raw pulse over to the new leg
        if not self.all_legs:
            n = self.st.leg_num
            if n != self.legs[0] and 0 <= n < self.r.n:
                self._release()
                self.legs = (n,)
                self.r.raw[n] = True

    def exit(self):
        self._release()


class ZeroAll(Zero):
    name = "ZEROALL"
    all_legs = True


class Cal(Gait):
    """Manual joint calibration: coxa/femur/tibia (only the fields that
    arrived, per State.dirty) of leg_num. GETCAL/SAVE are handled in
    engine.py since they are one-shot actions, not part of step()."""
    name = "CAL"
    vmax = 9e9
    tau = 0.0

    def enter(self):
        # SAVE/GETCAL arriving mid-walk used to freeze the robot with a leg in
        # the air (hold() of whatever pose it was in). Calibrate from the
        # standing pose, reached smoothly through the engine's Settle.
        for i in range(self.r.n):
            self.stand_leg(i)

    def step(self, dt):
        st = self.st
        r = self.r
        i = st.leg_num
        if not (0 <= i < r.n):
            return
        names = ("coxa", "femur", "tibia")
        for k in range(3):
            if st.dirty[k]:
                r.set_cal(i, k, getattr(st, names[k]))
