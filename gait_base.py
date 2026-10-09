# gait_base.py
#
# Common interface for a motion mode. In v4 every mode was a function with
# its own infinite while + sleep (or no sleep at all - 100% CPU). Now a mode
# is an object with three short methods, called by the single loop in
# engine.py:
#
#   enter()   - once, on entry: set the neutral/starting target pose. The
#               engine then smoothly drives the robot there before step()
#               is called for the first time (no jerk on mode switch).
#   step(dt)  - every tick: update robot.tgt. dt is real elapsed seconds.
#   exit()    - on exit (only ZERO needs this).
#
# Attributes a mode sets for the interpolator once it becomes active:
#   vmax - joint speed cap, deg/s;  tau - smoothing time constant, s.

class Gait:
    name = ""
    vmax = 350.0
    tau = 0.0

    def __init__(self, ctx):
        self.ctx = ctx
        self.r = ctx.robot
        self.st = ctx.st
        self.cfg = ctx.cfg

    def enter(self):
        pass

    def step(self, dt):
        pass

    def exit(self):
        pass

    def stand_leg(self, i):
        """Put a single leg into the neutral stance (current height/spread)."""
        r = self.r
        R = self.st.spread
        r.foot(i, R * r.c[i], R * r.s[i], -self.st.height)
