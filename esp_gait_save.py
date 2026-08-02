# esp_gait_save.py
#
# Gait "SAVE" - one-shot action, NOT a continuous mode like the other
# gaits. When RC_data["gait"] becomes 'SAVE', writes every leg's
# current leg.calibration to calibration.json on flash, then
# immediately switches back to gait 'CAL' so this never runs on a
# repeating loop (repeatedly writing to flash on every gait_selector
# poll would needlessly wear it out).
#
# Nothing is ever written unless this exact command is sent - CAL mode
# itself never touches the filesystem, only memory (see esp_gait_cal.py).

try:
    import ujson as json
except ImportError:
    import json

import esp_context

CALIBRATION_FILE = "calibration.json"


def gait_save(legs):
    if esp_context.RC_data["gait"] != 'SAVE':
        return

    try:
        data = {str(leg.leg_number): leg.calibration for leg in legs}
        with open(CALIBRATION_FILE, "w") as f:
            json.dump(data, f)
        print(f"[esp_gait_save.py] calibration saved to {CALIBRATION_FILE}: {data}")
    except Exception as e:
        print(f"[esp_gait_save.py] FAILED to save calibration: {e}")
    finally:
        esp_context.RC_data["gait"] = 'CAL'  # one-shot: bounce back to CAL automatically
