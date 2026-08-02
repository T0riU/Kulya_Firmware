# esp_inverse_kinematics.py
#
# Inverse kinematics for a single 3-DOF leg (coxa/femur/tibia).
#
#   -leg top view                                  T1 : leg angle
#                  [x,y,z]                          a1 : distance from robot origin to leg origin
#             y   /a4                               a2 : coxa length
#           (T4)./                                  a3 : femur length
#               /a3                                 a4 : tibia length
#         (T3)./                                [x,y,z]: end-effector position
#             /
#    T1      / a2
#    ._____./ T2     x
#    o    a1
#
#   -leg side view
#                       .T4                c : side   T3 -- [xyz]
#                      /\                  d : side   T1 -- [xyz]
#                  a3 /  \             alpha : angle  a2 <-> c
#                    /    \             beta : angle  c  <-> a3
#     (T1) (T2)  T3 /      \           gamma : angle  a3 <-> a4
#      ._ _ _.____./        \ a4
#         a1   a2            \
#                              \[x,y,z]

from math import sin, cos, radians, sqrt, atan2, acos, degrees, pi


def IK(leg, xyz):
    """Return [coxa_angle, femur_angle, tibia_angle] (degrees, clamped to leg limits)
    for the given leg to reach the target (x, y, z) position."""
    try:
        x, y, z = xyz

        # zero-division avoidance
        if x == 0:
            x += 0.0000001
        if y == 0:
            y += 0.0000001
        if z == 0:
            z += 0.0000001

        T1 = radians(leg.leg_angle)  # leg mount angle

        a1 = leg.origin_distance
        a2 = leg.coxa_length
        a3 = leg.femur_length
        a4 = leg.tibia_length

        x1_0 = a1 * cos(T1)  # leg origin X
        y1_0 = a1 * sin(T1)  # leg origin Y

        b = sqrt((x - x1_0) ** 2 + (y - y1_0) ** 2)   # hypotenuse, top view
        T2 = T1 - atan2((y - y1_0), (x - x1_0))       # coxa angle, radians

        if b == a2:
            b += 0.0000001  # zero-division avoidance

        c = sqrt(z ** 2 + (b - a2) ** 2)
        d = sqrt(z ** 2 + b ** 2)

        if c == 0:
            c += 0.0000001
        if d == 0:
            d += 0.0000001

        alpha = acos((a2 ** 2 + c ** 2 - d ** 2) / (2 * a2 * c))
        beta = acos((a3 ** 2 + c ** 2 - a4 ** 2) / (2 * a3 * c))
        gamma = acos((a3 ** 2 + a4 ** 2 - c ** 2) / (2 * a3 * a4))

        T3 = beta - (pi - alpha)
        T4 = -(pi / 2 - gamma)

        T2 = degrees(T2)
        T3 = degrees(T3)
        T4 = degrees(T4)

        # wrap into -180..180 so coxas on either half of the robot behave consistently
        if T2 > 180:
            T2 -= 360
        if T3 > 180:
            T3 -= 360
        if T4 > 180:
            T4 -= 360
        if T2 < -180:
            T2 += 360
        if T3 < -180:
            T3 += 360
        if T4 < -180:
            T4 += 360

        coxa_angle = round(T2)
        femur_angle = round(T3)
        tibia_angle = round(T4)

        # clamp to physical limits
        coxa_angle = min(max(coxa_angle, leg.coxa_limits[0]), leg.coxa_limits[1])
        femur_angle = min(max(femur_angle, leg.femur_limits[0]), leg.femur_limits[1])
        tibia_angle = min(max(tibia_angle, leg.tibia_limits[0]), leg.tibia_limits[1])

        return [coxa_angle, femur_angle, tibia_angle]

    except Exception as e:
        print("Inverse Kinematics Error: ", e)
        return leg.current_angles


def getSpread_xyz(leg, spread_radius_, turn_angle_, height_, dx_, dy_, rx_, ry_, rz_):
    """Compute the (x, y, z) target point for a leg given the current
    body spread/turn/height/shift/tilt parameters."""
    angle = radians(leg.leg_angle + turn_angle_ + rz_)
    x = spread_radius_ * cos(angle) + dx_
    y = spread_radius_ * sin(angle) + dy_
    z = (ry_ * spread_radius_ * sin(radians(leg.leg_angle + turn_angle_))
         + rx_ * spread_radius_ * cos(radians(leg.leg_angle + turn_angle_))
         - 1 - height_)

    return [x, y, z]
