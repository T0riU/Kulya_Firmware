# esp_gait_wave.py
#
# Gait "WAVE" - lifts and waves ONE leg (selected via RC_data["leg_num"],
# same field as LEG/CAL/ZERO) while the other five hold a standing
# pose, then automatically returns to WALK when done.
#
# This used to be two separate gaits, "wavl" and "wavr", each a
# hardcoded copy of the same state machine differing only in which leg
# index waves (4 or 5) and one smoothing constant. Now it's one gait -
# to wave a different leg, send a different leg_num, no code needed.
#
# leg_num is read ONCE when the gait starts (not every frame) so the
# waving leg can't change mid-sequence if leg_num is sent again while
# WAVE is already running - the routine always finishes the leg it
# started with.

import esp_context
from esp_legs_setup import legs
from esp_inverse_kinematics import IK, getSpread_xyz
from math import radians

SPREAD_RADIUS = 115
HEIGHT = 120
SHIFT_DX = 0
SHIFT_DY = -20
RX = 0
RY = radians(8)
RZ = 0

# was .35 for "wavl" / .7 for "wavr" separately - unified to one value
# now that the leg is a parameter rather than a hardcoded copy of the file
SMOOTH_RATE_SETTLE = .5
SMOOTH_RATE_FINISH = .7

# per-frame target angles for the waving leg: [coxa, femur, tibia]
WAVE_FRAME_ANGLES = {
    2: [-20, 60, 8],
    3: [20, 60, 8],
    4: [-20, 60, 8],
    5: [20, 60, 8],
}

NUM_FRAMES = 7  # frames 0..6


def _stand_all_legs():
    for leg in legs:
        leg.target_angles = IK(leg, getSpread_xyz(
            leg, SPREAD_RADIUS, 0, HEIGHT, SHIFT_DX, SHIFT_DY, RX, RY, RZ))


def _move_to_frame(frame, wave_leg_index):
    if frame == 0:                       # shift body backward / settle in
        esp_context.motion_smooth_rate = SMOOTH_RATE_SETTLE

    elif frame == 1:
        _stand_all_legs()
        legs[wave_leg_index].target_angles = [0, 60, 8]

    elif frame == 2:
        esp_context.motion_smooth_rate = .0001
        legs[wave_leg_index].target_angles = list(WAVE_FRAME_ANGLES[2])

    elif frame in (3, 4, 5):
        legs[wave_leg_index].target_angles = list(WAVE_FRAME_ANGLES[frame])

    elif frame == 6:
        esp_context.motion_smooth_rate = SMOOTH_RATE_FINISH
        _stand_all_legs()
        esp_context.RC_data["gait"] = 'WALK'   # done waving, resume walking


def gait_wave(all_legs):
    wave_leg_index = int(esp_context.RC_data["leg_num"])
    if not (0 <= wave_leg_index < len(all_legs)):
        print(f"[esp_gait_wave.py] invalid leg_num {wave_leg_index}")
        esp_context.RC_data["gait"] = 'STOP'
        return

    frame = 0
    print(f"gait:WAVE - waving leg {wave_leg_index}")

    while esp_context.RC_data["gait"] == 'WAVE':
        legs_on_target = True
        for leg in legs:
            legs_on_target = legs_on_target and leg.is_on_target()

        if legs_on_target:
            frame += 1
        if frame > NUM_FRAMES - 1:
            frame = 0

        _move_to_frame(frame, wave_leg_index)
