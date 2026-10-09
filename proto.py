# proto.py
#
# Command state (State) and the "param:value;param:value;" line parser.
# The format is COMPATIBLE with v4 (same parameter names, same joystick
# modes):
#
#   gait, spread, height, raise, turn_angle, speed, dx, dy, rx, ry, rz,
#   espi, servoi, ce_value, leg_num, coxa, femur, tibia, roll_range, roll_turn,
#   dance_id, J_mode, J_XY:x|y
#

from math import sqrt

GAITS = ("WALK", "CE", "LEG", "ROLL", "WAVE", "DANCE", "ZERO", "ZEROALL", "CAL", "STOP")
J_MODES = ("steer", "sides", "shift", "tilt", "yaw")

# protocol name -> (State attribute, min, max)
_NUM = {
    "spread": ("spread", 30, 200),
    "height": ("height", 30, 200),
    "raise": ("raise_h", 0, 100),
    "turn_angle": ("turn_angle", -45, 45),
    "speed": ("speed", 0, 100),
    "dx": ("dx", -100, 100),
    "dy": ("dy", -100, 100),
    "rx": ("rx", -60, 60),
    "ry": ("ry", -60, 60),
    "rz": ("rz", -45, 45),
    "espi": ("espi", 5, 500),
    "servoi": ("servoi", 10, 1000),
    "ce_value": ("ce_value", 0, 100),
    "roll_range": ("roll_range", 0, 60),
    "roll_turn": ("roll_turn", -40, 40),
    "dance_id": ("dance_id", 0, 255),
    "wtype": ("wtype", 0, 2),
    "tempo": ("tempo", 20, 300),
}
_ANG = {"coxa": 0, "femur": 1, "tibia": 2}
_INTS = ("dance_id", "wtype")       # used as list indices / enums: "dance_id:3.5" used to crash Dance


def _num(v):
    try:
        return int(v)
    except ValueError:
        f = float(v)
        if f != f or f > 1e9 or f < -1e9:      # nan / inf
            raise ValueError
        return f


class State:
    def __init__(self, cfg):
        self.n = cfg["n_legs"]
        self.dz = float(cfg["joy"]["deadzone"])
        # defaults - matches RC_data in v4
        self.gait = "WALK"
        self.spread = 115
        self.height = 120
        self.raise_h = 55
        self.turn_angle = 0
        self.speed = 0
        self.dx = 0
        self.dy = 0
        self.rx = 0
        self.ry = 0
        self.rz = 0
        self.espi = 0             # 0 = not set by the remote (config.tick_ms is used)
        self.servoi = 0           # 0 = not set by the remote (auto)
        self.ce_value = 100
        self.leg_num = 0
        self.coxa = 0
        self.femur = 0
        self.tibia = 0
        self.roll_range = 10
        self.roll_turn = 0
        self.dance_id = 0
        self.wtype = 0
        self.tempo = 100
        self.J_mode = "steer"
        # internal
        self.actions = []                 # one-shot actions: "SAVE", "GETCAL"
        self.dirty = [False, False, False]  # which of coxa/femur/tibia arrived for CAL
        self.rx_ms = 0                    # timestamp of the last command (for the link failsafe)
        self.rx_count = 0

    # -------------------------------------------------------------- joystick
    def _joystick(self, value):
        p = value.split("|", 1)
        x = float(p[0])
        y = float(p[1])
        if x > 100.0:
            x = 100.0
        elif x < -100.0:
            x = -100.0
        if y > 100.0:
            y = 100.0
        elif y < -100.0:
            y = -100.0
        dz = self.dz
        # Per-axis dead zone (a "+" shaped dead zone, not a circular one
        # around center): each axis is blanked independently below dz and
        # rescaled to still reach 100 at full deflection. This matters
        # specifically for "steer": pushing the stick hard to one side but
        # not perfectly on-axis leaves a small residual on the OTHER axis;
        # a circular dead zone only protects the very center of the stick,
        # so that residual survives once you're pushing hard in any
        # direction and leaks into "steer" mode as a slow, persistent drift
        # (e.g. a pure-left push with a tiny bit of leftover forward/back
        # deflection reads as "turn AND keep walking straight"). Zeroing
        # each axis independently removes that residual instead.
        if -dz <= x <= dz:
            x = 0.0
        elif dz > 0.0:
            x = (x - dz if x > 0.0 else x + dz) * 100.0 / (100.0 - dz)
        if -dz <= y <= dz:
            y = 0.0
        elif dz > 0.0:
            y = (y - dz if y > 0.0 else y + dz) * 100.0 / (100.0 - dz)
        r = sqrt(x * x + y * y)
        if r > 100.0:                      # the two independent per-axis rescales can push a
            k = 100.0 / r                  # diagonal corner slightly past 100 - clamp the vector
            x *= k                         # radius without touching its direction
            y *= k
            r = 100.0
        speed = int(r + 0.5)
        mode = self.J_mode

        if mode == "sides":
            self.dx = x * .45
            self.dy = y * .45
            self.speed = speed
            self.turn_angle = 0
        elif mode == "steer":
            self.turn_angle = round(x * .10)
            self.dx = 0
            self.dy = y * .45
            self.speed = speed
        elif mode == "shift":
            self.dx = x * .45
            self.dy = y * .45
            self.speed = 0
            self.turn_angle = 0
        elif mode == "tilt":
            self.rx = x * .35
            self.ry = y * .35
            self.speed = 0
            self.turn_angle = 0
        elif mode == "yaw":                # new: rotate the body in place, +-30 deg
            self.rz = x * .30
            self.speed = 0
            self.turn_angle = 0

        # A real movement-intent joystick deflection brings the robot back to
        # walking from any passive/showcase mode - not just STOP (v4 only
        # covered STOP; DANCE/CE/ROLL/WAVE left the joystick dead until an
        # explicit "gait:WALK" arrived). LEG/ZERO/ZEROALL/CAL are
        # deliberately excluded - those are calibration/test modes and
        # should not be interrupted by an accidental stick nudge.
        if self.gait in ("STOP", "DANCE", "CE", "ROLL", "WAVE") and speed > 0 and mode in ("sides", "steer"):
            self.gait = "WALK"

    # ---------------------------------------------------------------- parser
    def parse(self, text, now_ms=0):
        """Parse a command string. Never raises."""
        self.rx_ms = now_ms
        for pair in text.replace("\n", ";").split(";"):
            pair = pair.strip()
            if not pair or ":" not in pair:
                continue
            k, v = pair.split(":", 1)
            k = k.strip()
            v = v.strip()
            try:
                spec = _NUM.get(k)
                if spec is not None:
                    x = _num(v)
                    if x < spec[1]:
                        x = spec[1]
                    elif x > spec[2]:
                        x = spec[2]
                    if spec[0] in _INTS:
                        x = int(x)
                    setattr(self, spec[0], x)
                elif k == "J_XY":
                    self.rx_count += 1
                    self._joystick(v)
                elif k == "gait":
                    self._set_gait(v.upper())
                elif k in _ANG:
                    x = _num(v)
                    if -180 <= x <= 180:
                        setattr(self, k, x)
                        self.dirty[_ANG[k]] = True
                elif k == "leg_num":
                    x = int(v)
                    if 0 <= x < self.n:
                        self.leg_num = x
                        self._disarm()
                elif k == "J_mode":
                    if v in J_MODES:
                        self.J_mode = v
            except (ValueError, IndexError):
                pass          # garbage value - just skip this pair

    def _disarm(self):
        d = self.dirty
        d[0] = d[1] = d[2] = False

    def _set_gait(self, g):
        if g in ("SAVE", "GETCAL"):
            self.actions.append(g)
            g = "CAL"                      # same as v4: after a one-shot action, fall into CAL
        if g not in GAITS:
            return
        if g == "CAL":
            self._disarm()                 # coxa/femur/tibia left over from another mode must not apply
        self.gait = g

    # ------------------------------------------------------------------ misc
    def stop_motion(self):
        """Zero out motion (failsafe / link loss)."""
        self.speed = 0
        self.dx = 0
        self.dy = 0
        self.turn_angle = 0

    def on_disconnect(self):
        # same as v4: a BLE disconnect means STOP. (In v5, STOP is a smooth
        # stance, not a "freeze in place".)
        self.stop_motion()
        self.gait = "STOP"
