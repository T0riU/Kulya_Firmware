# esp_gait_leg.py
#
# Gait "LEG": manual single-leg jog mode, used for calibration/testing.
# Reads leg_num/coxa/femur/tibia straight from esp_context.RC_data and
# drives that one leg to the requested angles, clamped to that leg's
# own coxa/femur/tibia_limits so a stray value (e.g. typo'd 66 for a
# ±29° coxa) can't drive a servo past its mechanical stop.

from time import sleep
import esp_context


def _clamp(value, limits):
    return min(max(value, limits[0]), limits[1])


def gait_leg(legs):
    esp_context.motion_smooth_rate = .4
    last_sent = None

    while esp_context.RC_data["gait"] == 'LEG':
        leg_num = int(esp_context.RC_data["leg_num"])
        if not (0 <= leg_num < len(legs)):
            print(f"[esp_gait_leg.py] invalid leg_num {leg_num}")
            sleep(.05)
            continue

        coxa = int(esp_context.RC_data["coxa"])
        femur = int(esp_context.RC_data["femur"])
        tibia = int(esp_context.RC_data["tibia"])

        leg = legs[leg_num]

        clamped = [
            _clamp(coxa, leg.coxa_limits),
            _clamp(femur, leg.femur_limits),
            _clamp(tibia, leg.tibia_limits),
        ]

        # print only when the requested values actually change, so the
        # REPL log stays readable instead of spamming every 50ms
        request = (leg_num, coxa, femur, tibia)
        if request != last_sent:
            print(f"[esp_gait_leg.py] leg {leg_num}: requested [{coxa},{femur},{tibia}]"
                  f" -> clamped target {clamped}  (calibration={leg.calibration})")
            last_sent = request

        leg.target_angles = clamped

        if leg.target_angles == leg.current_angles:
            leg.past_angles = list(leg.target_angles)

        sleep(.05)  # don't peg the CPU in a fully tight loop
