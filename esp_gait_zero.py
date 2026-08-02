# esp_gait_zero.py
#
# Raw servo-centering helpers for mounting servo horns. Two gaits:
#
#   ZERO    - centers ONE leg, selected via RC_data["leg_num"]
#              (same field used by gait "LEG"/"CAL")
#   ZEROALL - centers ALL legs at once, one command from the remote
#
# Both send the TRUE electrical center pulse (1500 us == 0 degrees on
# an uncalibrated servo) directly over UART, completely bypassing
# calibration[] and the T-offset angles from esp_Leg_class.py. This is
# for the mechanical step: power the servo with this signal BEFORE the
# horn is fixed on the shaft, then mount/adjust the horn so the leg
# sits in the reference pose (coxa horizontal outward, femur
# horizontal, tibia straight down).
#
# IMPORTANT: legs NOT being centered are simply left out of the UART
# command string entirely - the ch24 controller only updates the
# channels it's told about, so untouched legs just hold their last
# position. Never send a pulse of 0 to a channel you don't want to
# move - that is not a valid "leave alone" pulse width, it's an
# invalid signal that can snap a servo to an extreme.
#
# While either gait is active, the normal esp_legmover.py loop is
# paused for ALL legs (esp_context.legmover_on = False) so nothing else
# writes conflicting commands to the same UART. Normal operation
# resumes automatically once you leave the gait.

import machine
from time import sleep

import esp_context
from esp_legs_setup import legs

uart = machine.UART(2, 9600)

CENTER_PULSE = 1500        # true servo center / 0 degrees, no calibration, no offset
REFRESH_INTERVAL_S = 0.2   # resend periodically in case the servo controller needs a keep-alive


def _center_command(target_legs):
    parts = []
    for leg in target_legs:
        parts.append(f"#{leg.coxa_pin}P{CENTER_PULSE}")
        parts.append(f"#{leg.femur_pin}P{CENTER_PULSE}")
        parts.append(f"#{leg.tibia_pin}P{CENTER_PULSE}")
    parts.append(f"T{int(REFRESH_INTERVAL_S * 1000)}")
    return ''.join(parts)


def _run_centering(target_legs, label):
    was_legmover_on = esp_context.legmover_on
    esp_context.legmover_on = False  # stop the normal pipeline from also writing to UART

    print(f"gait:{label} - raw servo centering, legmover paused")
    command = _center_command(target_legs)

    try:
        while esp_context.RC_data["gait"] == label:
            uart.write(command + '\r\n')
            sleep(REFRESH_INTERVAL_S)
    finally:
        esp_context.legmover_on = was_legmover_on
        print(f"gait:{label} - done, legmover resumed")


def gait_zero(all_legs):
    leg_num = int(esp_context.RC_data["leg_num"])
    if not (0 <= leg_num < len(all_legs)):
        print(f"[esp_gait_zero.py] invalid leg_num {leg_num}")
        return
    _run_centering([all_legs[leg_num]], 'ZERO')


def gait_zero_all(all_legs):
    _run_centering(all_legs, 'ZEROALL')
