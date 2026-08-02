# esp_gait_roll.py
#
# Gait "ROLL": legs open/close one at a time going around the hexapod,
# giving a rolling turning motion. Previously broken: it referenced
# esp_context.RC_data["roll_range"] / ["roll_turn"], which were never
# defined in esp_context.RC_data. Both keys now exist there (default
# roll_range=10, roll_turn=0), so this gait should actually run — but it
# is still experimental/untested on real hardware.

import esp_context
from utime import sleep

COXA_ANGLE_CLOSED = 0
FEMUR_ANGLE_CLOSED = 94
TIBIA_ANGLE_CLOSED = -113

NUM_LEGS = 6


def gait_roll(legs):
    current_leg = 0

    while esp_context.RC_data["gait"] == 'ROLL':
        roll_range = int(esp_context.RC_data["roll_range"])   # extra leg-open distance for turning/slope control
        speed = 100 - int(esp_context.RC_data["speed"])
        roll_turn = int(esp_context.RC_data["roll_turn"])

        legs[current_leg].target_angles = [
            COXA_ANGLE_CLOSED - roll_turn / 1.5,
            FEMUR_ANGLE_CLOSED - roll_range + roll_turn,
            TIBIA_ANGLE_CLOSED + roll_range + roll_turn,
        ]
        legs[current_leg].current_angles = list(legs[current_leg].target_angles)
        legs[current_leg].past_angles = list(legs[current_leg].target_angles)

        previous_leg = (current_leg - 1) % NUM_LEGS
        legs[previous_leg].target_angles = [COXA_ANGLE_CLOSED, FEMUR_ANGLE_CLOSED, TIBIA_ANGLE_CLOSED]
        legs[previous_leg].current_angles = list(legs[previous_leg].target_angles)
        legs[previous_leg].past_angles = list(legs[previous_leg].target_angles)

        current_leg = (current_leg + 1) % NUM_LEGS

        sleep(speed / 1000)
