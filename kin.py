# kin.py
#
# Single-leg kinematics (3 degrees of freedom: coxa / femur / tibia).
#
#   top view: t1 is the leg's mounting angle, a1 is the distance from the
#   body center to the leg axis, a2/a3/a4 are coxa/femur/tibia length.
#   Pose 0/0/0 means: coxa pointing straight out, femur horizontal, tibia
#   straight down.
#

from math import sin, cos, atan2, acos, sqrt, pi

TWO_PI = 2.0 * pi
RAD2DEG = 180.0 / pi


class Geo:
    def __init__(self, g):
        self.a1 = float(g["a1"])
        self.a2 = float(g["a2"])
        self.a3 = float(g["a3"])
        self.a4 = float(g["a4"])
        a3, a4 = self.a3, self.a4
        self.k_beta = a3 * a3 - a4 * a4      # a3^2 - a4^2
        self.k_gam = a3 * a3 + a4 * a4       # a3^2 + a4^2
        self.two_a3 = 2.0 * a3
        self.two_a3a4 = 2.0 * a3 * a4
        self.reach_max = a3 + a4
        self.reach_min = abs(a3 - a4)


def ik(geo, t1, ox, oy, x, y, z, out, j):
    """Single-leg IK. Writes degrees into out[j], out[j+1], out[j+2].
    t1 is the leg mount angle (rad), (ox, oy) is the leg axis position.
    Returns 1 if the target was out of reach (leg clamped), else 0."""
    dx = x - ox
    dy = y - oy
    b = sqrt(dx * dx + dy * dy)
    t2 = t1 - atan2(dy, dx)
    if t2 > pi:                 # t1 in [0, 2pi), atan2 in (-pi, pi] -> t2 in (-pi, 3pi)
        t2 -= TWO_PI
    r = b - geo.a2
    c2 = z * z + r * r
    c = sqrt(c2)
    if c < 1e-3:
        c = 1e-3
    sat = 0

    cb = (geo.k_beta + c2) / (geo.two_a3 * c)
    if cb > 1.0:
        cb = 1.0
        sat = 1
    elif cb < -1.0:
        cb = -1.0
        sat = 1
    t3 = atan2(z, r) + acos(cb)

    cg = (geo.k_gam - c2) / geo.two_a3a4
    if cg > 1.0:
        cg = 1.0
        sat = 1
    elif cg < -1.0:
        cg = -1.0
        sat = 1
    t4 = acos(cg) - 0.5 * pi

    out[j] = t2 * RAD2DEG
    out[j + 1] = t3 * RAD2DEG
    out[j + 2] = t4 * RAD2DEG
    return sat


def fk(geo, t1, ox, oy, ang):
    """Forward kinematics (for tests/debugging): angles (deg) -> (x, y, z)."""
    t2 = ang[0] / RAD2DEG
    t3 = ang[1] / RAD2DEG
    t4 = ang[2] / RAD2DEG
    b = geo.a2 + geo.a3 * cos(t3) + geo.a4 * sin(t3 + t4)
    z = geo.a3 * sin(t3) - geo.a4 * cos(t3 + t4)
    phi = t1 - t2
    return (ox + b * cos(phi), oy + b * sin(phi), z)
