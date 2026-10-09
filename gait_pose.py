# gait_pose.py
#
# "Pose" modes: CE (collapse/expand), LEG (manual single leg), ROLL (roll-out).
# Replaces esp_gait_ce.py / esp_gait_leg.py / esp_gait_roll.py.


from gait_base import Gait


class CE(Gait):
    """Collapse/Expand: ce_value 0 = folded, 100 = fully unfolded (0/0/0)."""
    name = "CE"
    vmax = 300.0
    tau = 0.08

    def enter(self):
        # Set the target immediately (same contract as every other gait's
        # enter()), so the engine's Settle transition actually has something
        # to move towards instead of instantly reporting "done".
        v = self.st.ce_value
        self.last = v
        self.r.fold_pose(1.0 - v / 100.0)

    def step(self, dt):
        v = self.st.ce_value
        if v == self.last:
            return
        self.last = v
        self.r.fold_pose(1.0 - v / 100.0)


class Leg(Gait):
    """Manual control of a single leg (leg_num, coxa, femur, tibia) - for
    testing individual servos. Every other leg stays in the stance pose."""
    name = "LEG"
    vmax = 350.0
    tau = 0.06

    def enter(self):
        st = self.st
        for i in range(self.r.n):
            self.stand_leg(i)
        self.last = None
        self.prev = st.leg_num

    def step(self, dt):
        st = self.st
        req = (st.leg_num, st.coxa, st.femur, st.tibia)
        if req == self.last:
            return
        self.last = req
        if st.leg_num != self.prev:
            self.stand_leg(self.prev)           # the previously selected leg returns to stance
            self.prev = st.leg_num
        # joints() clamps the values to the leg's soft limits
        self.r.joints(st.leg_num, st.coxa, st.femur, st.tibia, True)


class Roll(Gait):
    """Legs open up one by one, going around the body - a "roll" motion.
    Experimental, same as in v4. Step timing: 100 + (100-speed)*3 ms (v4
    used (100-speed) ms, but in practice was throttled by the UART to
    ~250 ms anyway)."""
    name = "ROLL"
    vmax = 500.0
    tau = 0.05

    def enter(self):
        self.r.fold_pose(1.0)
        self.idx = 0
        self.t = 1e9                            # take the first step immediately

    def step(self, dt):
        st = self.st
        r = self.r
        period = (100 + (100 - st.speed) * 3) / 1000.0
        self.t += dt
        if self.t < period:
            return
        self.t = 0.0
        f = r.fold
        rr = st.roll_range
        rt = st.roll_turn
        r.joints(self.idx, f[0] - rt / 1.5, f[1] - rr + rt, f[2] + rr + rt, False)
        prev = (self.idx - 1) % r.n
        r.joints(prev, f[0], f[1], f[2], False)
        self.idx = (self.idx + 1) % r.n
