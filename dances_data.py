# dances_data.py
#
# Dances as DATA. Each step is a tuple:
#
#   (duration_s, height_mm, rx_deg, ry_deg, yaw_deg, shift_x_mm, shift_y_mm, radius_mm, legs)
#
#   height = 0  -> use the current height from the remote;  radius = 0 -> use the current spread
#   legs (raised by dance.lift_mm): 0 - none, 1 - even legs (0,2,4), 2 - odd legs (1,3,5), 3 - all
#   rx/ry tilt the body (same convention as v4), yaw twists the body
#
# To add your own dance, just append an entry to DANCES (id = its index).
# dance_id:255 plays all of them back to back.

from math import sin, cos, pi


def _v4(h, rx, ry, yaw, hold):           # v4-style dance step format
    return (hold, h, rx, ry, yaw, 0, 0, 0, 0)


SWAY = [                                 # 0 - v4 "Sway" (unchanged)
    _v4(100, 0, 0, 0, .4), _v4(140, 0, 0, 0, .4),
    _v4(120, 14, 0, 0, .3), _v4(120, -14, 0, 0, .3),
    _v4(120, 0, 14, 0, .3), _v4(120, 0, -14, 0, .3),
    _v4(120, 0, 0, 20, .3), _v4(120, 0, 0, -20, .3),
    _v4(120, 0, 0, 0, .4),
]

BOUNCE = [                               # 1 - v4 "Bounce" (unchanged)
    _v4(90, 0, 0, 0, .2), _v4(150, 0, 0, 0, .2),
    _v4(90, 0, 0, 0, .2), _v4(150, 0, 0, 0, .2),
    _v4(120, 0, 0, 30, .25), _v4(120, 0, 0, -30, .25),
    _v4(120, 0, 0, 30, .25), _v4(120, 0, 0, -30, .25),
    _v4(120, 0, 0, 0, .3),
]

SHIMMY = [(0.18, 120, 0, 0, 10, 25, 0, 0, 0),        # 2 - quick side-to-side shake
          (0.18, 120, 0, 0, -10, -25, 0, 0, 0)] * 4 + [(0.3, 120, 0, 0, 0, 0, 0, 0, 0)]

HULA = [(0.17, 118, 12 * cos(k * pi / 6), 12 * sin(k * pi / 6), 0,   # 3 - body circles via tilt
         12 * cos(k * pi / 6), 12 * sin(k * pi / 6), 0, 0) for k in range(12)] * 2 \
       + [(0.3, 120, 0, 0, 0, 0, 0, 0, 0)]

MARCH = [(0.3, 120, 0, 0, 0, 0, 0, 0, 1),           # 4 - marching in place (leg trios alternate)
         (0.3, 120, 0, 0, 0, 0, 0, 0, 2)] * 4 + [(0.4, 120, 0, 0, 0, 0, 0, 0, 0)]

BREATHE = [(1.4, 106, 0, 0, 0, 0, 0, 100, 0),        # 5 - "breathing": slow down-up
           (1.4, 134, 0, 0, 0, 0, 0, 126, 0)] * 2 + [(0.5, 120, 0, 0, 0, 0, 0, 0, 0)]

SQUATS = [(0.7, 76, 0, 0, 0, 0, 0, 130, 0),          # 6 - deep squats
          (0.7, 148, 0, 0, 0, 0, 0, 106, 0)] * 3 + [(0.5, 120, 0, 0, 0, 0, 0, 0, 0)]

DISCO = [(0.3, 120, 0, 10, -10, -14, 0, 0, 1),       # 7 - disco: tilt + twist + leg raise
         (0.3, 120, 0, -10, 10, 14, 0, 0, 2)] * 4 + [(0.4, 120, 0, 0, 0, 0, 0, 0, 0)]

HEART = [(0.12, 104, 0, 0, 0, 0, 0, 0, 0), (0.12, 132, 0, 0, 0, 0, 0, 0, 0),   # 8 - "heartbeat"
         (0.12, 104, 0, 0, 0, 0, 0, 0, 0), (0.12, 138, 0, 0, 0, 0, 0, 0, 0),
         (0.7, 120, 0, 0, 0, 0, 0, 0, 0)] * 2

TWIST = [(0.25, 120, 0, 0, a, 0, 0, 0, 0)            # 9 - smooth body twist
         for a in (0, 25, 35, 25, 0, -25, -35, -25)] * 2 + [(0.3, 120, 0, 0, 0, 0, 0, 0, 0)]

DANCES = (
    ("SWAY", SWAY),
    ("BOUNCE", BOUNCE),
    ("SHIMMY", SHIMMY),
    ("HULA", HULA),
    ("MARCH", MARCH),
    ("BREATHE", BREATHE),
    ("SQUATS", SQUATS),
    ("DISCO", DISCO),
    ("HEARTBEAT", HEART),
    ("TWIST", TWIST),
)
