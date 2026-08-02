# esp_gait_walk.py
#
# Gait "WALK": alternating tripod gait. Legs are split into two groups
# (blue/green) that step through 4 frames each, offset from each other,
# so one tripod is always on the ground while the other moves.
#
#         -----(2)
#         -----/\
#         ----/--\
#         ---/----\
#         --/------\
#         -/________\
#         (1)--(4)--(3)

import esp_context
from esp_inverse_kinematics import IK, getSpread_xyz

# frame sequence for each tripod group: green does 1,2,3,4 - blue does 3,4,1,2
FRAME_SEQUENCE = [[1, 2, 3, 4],
                   [3, 4, 1, 2]]


def gait_walk(legs):
    frame = 1

    group_blue = legs[0::2]   # every other leg starting at 0 - not tied to exactly 6 legs
    group_green = legs[1::2]

    esp_context.motion_smooth_rate = .25

    def move_to_frame(leg, target_frame, turn_angle, height, dx, dy,
                       spread_radius, raise_h, shift_dx, shift_dy, rx, ry, rz):
        xyz1 = getSpread_xyz(leg, spread_radius, -turn_angle, height, -dx, -dy, rx, ry, rz)
        xyz2 = getSpread_xyz(leg, spread_radius, 0, height - raise_h, shift_dx, shift_dy, rx, ry, rz)
        xyz3 = getSpread_xyz(leg, spread_radius, turn_angle, height, dx, dy, rx, ry, rz)   # forward reach point
        xyz4 = getSpread_xyz(leg, spread_radius, 0, height, shift_dx, shift_dy, rx, ry, rz)

        target_xyz = {1: xyz1, 2: xyz2, 3: xyz3, 4: xyz4}[target_frame]
        leg.target_angles = IK(leg, target_xyz)

    while esp_context.RC_data["gait"] == 'WALK':
        turn_angle = int(esp_context.RC_data["turn_angle"])
        speed = int(esp_context.RC_data["speed"])
        dx = int(esp_context.RC_data["dx"])
        dy = int(esp_context.RC_data["dy"])
        spread_radius = int(esp_context.RC_data["spread"])
        height = int(esp_context.RC_data["height"])
        raise_h = int(esp_context.RC_data["raise"])
        rx = int(esp_context.RC_data["rx"]) / 100
        ry = int(esp_context.RC_data["ry"]) / 100
        rz = int(esp_context.RC_data["rz"])
        shift_dx = 0
        shift_dy = 0

        if speed <= 0 and frame in (0, 2):
            # legs grounded, standing still mid-frame -> nudge speed so IK still resolves
            speed = 25

        if speed <= 0 and frame in (1, 3):
            # legs grounded, standing still at a stance frame -> hold position, don't lift
            raise_h = 0
            shift_dx = -dx
            shift_dy = -dy

        else:  # moving: advance to the next frame once every leg has reached its target
            raise_h = int(esp_context.RC_data["raise"])
            shift_dx = 0
            shift_dy = 0

            legs_on_target = True
            for leg in legs:
                legs_on_target = legs_on_target and leg.is_on_target()

            if legs_on_target:
                frame += 1
            if frame > 3:
                frame = 0

        for leg in group_green:
            move_to_frame(leg, FRAME_SEQUENCE[0][frame], turn_angle, height, dx, dy,
                          spread_radius, raise_h, shift_dx, shift_dy, rx, ry, rz)

        for leg in group_blue:
            move_to_frame(leg, FRAME_SEQUENCE[1][frame], turn_angle, height, dx, dy,
                          spread_radius, raise_h, shift_dx, shift_dy, rx, ry, rz)
