# esp_gait_dance.py
#
# Gait "DANCE" - a scripted routine of body height/tilt/turn moves,
# applied to ALL legs together through the exact same IK path every
# other gait uses (esp_inverse_kinematics.IK + getSpread_xyz). Nothing
# new or unsafe here - just a sequence of ordinary standing poses
# played back-to-back. Loops until you switch to any other gait.
#
# Multiple routines are selected the same way legs are - by index, via
# RC_data["dance_id"] (default 0). dance_id is re-read at the start of
# every full pass through the routine, so you CAN switch styles live
# while DANCE keeps running by just sending a new dance_id - no need
# to stop and restart the gait.
#
#     gait:DANCE;dance_id:0;   - "Sway": slow lean/twist routine
#     gait:DANCE;dance_id:1;   - "Bounce": faster crouch-bounce + spin
#     gait:DANCE;dance_id:2;   - "Jump": pure up/down, no lean or turn at all

import esp_context
from time import sleep
from math import radians
from esp_legs_setup import legs
from esp_inverse_kinematics import IK, getSpread_xyz

SPREAD_RADIUS = 115

# (height_mm, rx_deg, ry_deg, turn_angle_deg, hold_seconds)

_DANCE_SWAY = [
    (100, 0,   0,   0,   .4),   # crouch
    (140, 0,   0,   0,   .4),   # stand tall
    (120, 14,  0,   0,   .3),   # lean right
    (120, -14, 0,   0,   .3),   # lean left
    (120, 0,   14,  0,   .3),   # lean forward
    (120, 0,   -14, 0,   .3),   # lean back
    (120, 0,   0,   20,  .3),   # twist right
    (120, 0,   0,   -20, .3),   # twist left
    (120, 0,   0,   0,   .4),   # reset to neutral
]

_DANCE_BOUNCE = [
    (90,  0, 0, 0,   .2),   # quick crouch
    (150, 0, 0, 0,   .2),   # quick stand
    (90,  0, 0, 0,   .2),
    (150, 0, 0, 0,   .2),
    (120, 0, 0, 30,  .25),  # spin right
    (120, 0, 0, -30, .25),  # spin left
    (120, 0, 0, 30,  .25),
    (120, 0, 0, -30, .25),
    (120, 0, 0, 0,   .3),   # reset to neutral
]

# pure vertical bounce - no lean, no turn, just quick up/down
_DANCE_JUMP = [
    (85,  0, 0, 0, .15),   # crouch low
    (150, 0, 0, 0, .15),   # extend high
    (85,  0, 0, 0, .15),
    (150, 0, 0, 0, .15),
    (85,  0, 0, 0, .15),
    (150, 0, 0, 0, .15),
    (85,  0, 0, 0, .15),
    (150, 0, 0, 0, .15),
    (120, 0, 0, 0, .3),    # reset to neutral
]

DANCES = {
    0: _DANCE_SWAY,
    1: _DANCE_BOUNCE,
    2: _DANCE_JUMP,
}


def _apply_pose(height, rx_deg, ry_deg, turn_angle):
    rx = radians(rx_deg)
    ry = radians(ry_deg)
    for leg in legs:
        leg.target_angles = IK(leg, getSpread_xyz(
            leg, SPREAD_RADIUS, turn_angle, height, 0, 0, rx, ry, 0))


def gait_dance(all_legs):
    print("gait:DANCE - let's go")
    esp_context.motion_smooth_rate = .3

    while esp_context.RC_data["gait"] == 'DANCE':
        dance_id = int(esp_context.RC_data["dance_id"])
        moves = DANCES.get(dance_id)
        if moves is None:
            print(f"[esp_gait_dance.py] unknown dance_id {dance_id}, using 0")
            moves = DANCES[0]

        for height, rx_deg, ry_deg, turn_angle, hold in moves:
            if esp_context.RC_data["gait"] != 'DANCE':
                break
            _apply_pose(height, rx_deg, ry_deg, turn_angle)
            sleep(hold)
