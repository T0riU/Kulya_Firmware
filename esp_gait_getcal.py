# esp_gait_getcal.py
#
# Gait "GETCAL" - one-shot action, NOT a continuous mode (same pattern
# as gait "SAVE", see esp_gait_save.py).
#
# When RC_data["gait"] becomes 'GETCAL', looks up legs[leg_num]'s
# current calibration and sends it back to the remote over BLE notify,
# formatted as:
#
#     CAL:<leg_num>:<coxa>,<femur>,<tibia>;
#
# e.g. "CAL:2:-8,3,0;" - then immediately switches gait back to 'CAL',
# so the remote can pre-fill its coxa/femur/tibia fields with the
# leg's ACTUAL current calibration before you send anything, instead
# of you having to remember/guess it (that's what was silently wiping
# other joints' calibration back to 0 - see esp_gait_cal.py).
#
# If nothing is connected over BLE, this just prints the values to the
# REPL instead (esp_ble.ESP32_BLE.send() already handles that safely).

import esp_context


def gait_getcal(legs):
    if esp_context.RC_data["gait"] != 'GETCAL':
        return

    try:
        leg_num = int(esp_context.RC_data["leg_num"])
        if not (0 <= leg_num < len(legs)):
            print(f"[esp_gait_getcal.py] invalid leg_num {leg_num}")
            return

        coxa, femur, tibia = legs[leg_num].calibration
        message = f"CAL:{leg_num}:{coxa},{femur},{tibia};"
        print(f"[esp_gait_getcal.py] {message}")

        if esp_context.ble_instance is not None:
            esp_context.ble_instance.send(message)
        else:
            print("[esp_gait_getcal.py] no BLE instance yet, not sent")

    finally:
        esp_context.RC_data["gait"] = 'CAL'  # one-shot: bounce back to CAL automatically
