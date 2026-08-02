# esp_gait_cal.py
#
# Gait "CAL" - live software calibration.
#
# Select a leg the same way as gait "LEG": RC_data["leg_num"].
# Send calibration numbers through the SAME fields gait "LEG" already
# uses (RC_data["coxa"/"femur"/"tibia"]) - here they are written
# straight into leg.calibration instead of leg.target_angles.
#
# IMPORTANT: this SETS leg.calibration = [coxa, femur, tibia] wholesale
# every time CAL runs - all three numbers, not just the one you meant
# to change. If you only want to adjust one joint, you still have to
# resend the other two joints' CURRENT calibration values in the same
# command, or you will overwrite them back to whatever the fields
# happen to hold (usually 0).
#
# Calibration numbers are clamped to CAL_LIMIT_DEG in each direction -
# calibration should only ever be a few degrees of trim. If you need
# more than that, the servo horn is mounted wrong; fix it mechanically
# (see esp_gait_zero.py) instead of masking it here.
#
# The selected leg is held at the kinematic reference pose (target
# angle 0/0/0) for as long as CAL is active, so whatever you see move
# is purely the effect of the calibration number you just sent - and
# it goes through the exact same esp_legmover.py math (T-offsets,
# deg2pulse, pulse clamping) the robot uses in every other gait. This
# is deliberately NOT a bypass like esp_gait_zero.py: the whole point
# is to tune the numbers that get used for real.
#
# Leaving CAL (switching to any other gait) keeps whatever calibration
# values were last sent - it does not reset or save them. Calibration
# values live only in memory until gait "SAVE" writes them to flash
# (esp_gait_save.py) or the board reboots (falls back to
# esp_legs_setup.LEG_CONFIG / calibration.json).

import esp_context
from time import sleep

CAL_LIMIT_DEG = 20  # sanity clamp: calibration should only ever be a small trim


def _clamp(value, lo, hi):
    return min(max(value, lo), hi)


def gait_cal(legs):
    print("gait:CAL - calibration mode")
    last_sent = None

    while esp_context.RC_data["gait"] == 'CAL':
        leg_num = int(esp_context.RC_data["leg_num"])
        if not (0 <= leg_num < len(legs)):
            print(f"[esp_gait_cal.py] invalid leg_num {leg_num}")
            sleep(.05)
            continue

        leg = legs[leg_num]

        raw = (
            int(esp_context.RC_data["coxa"]),
            int(esp_context.RC_data["femur"]),
            int(esp_context.RC_data["tibia"]),
        )
        leg.calibration = [_clamp(v, -CAL_LIMIT_DEG, CAL_LIMIT_DEG) for v in raw]

        # print only when the requested values actually change, so the
        # REPL log stays readable instead of spamming every 50ms
        request = (leg_num, raw)
        if request != last_sent:
            print(f"[esp_gait_cal.py] leg {leg_num}: requested {raw}"
                  f" -> applied calibration {leg.calibration}")
            last_sent = request

        # hold this leg at the kinematic reference pose while calibration is dialed in
        leg.target_angles = [0, 0, 0]
        if leg.target_angles == leg.current_angles:
            leg.past_angles = list(leg.target_angles)

        sleep(.05)  # don't peg the CPU in a fully tight loop
