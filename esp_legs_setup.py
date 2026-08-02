# esp_legs_setup.py
#
# Creates the 6 Leg objects, run once from run.py at boot.
#
# Nothing about an individual leg is hardcoded here anymore:
#   - wiring (servo pins, per-joint invert flag) comes from legs_config.json
#   - which rotational direction the legs are wired in (clockwise or
#     counter-clockwise, viewed from above) comes from ONE flag,
#     legs_config.json's top-level "legs_clockwise" - flip that single
#     True/False if the whole leg order is mirrored, instead of having
#     to work out a per-leg fix
#   - calibration trim comes from calibration.json (written by gait "SAVE",
#     see esp_gait_save.py), defaulting to [0, 0, 0] for any leg not in it
#
# If legs_config.json is missing/corrupt, a minimal built-in fallback is
# used so the robot can still boot - but this is a last resort, not a
# place to maintain your real wiring. Fix legs_config.json instead.

try:
    import ujson as json
except ImportError:
    import json

from esp_Leg_class import Leg

LEGS_CONFIG_FILE = "legs_config.json"
CALIBRATION_FILE = "calibration.json"

NUM_LEGS = 6
ANGLE_STEP_DEG = 360 // NUM_LEGS  # 60 for 6 legs

# last-resort fallback ONLY, used if legs_config.json can't be read -
# matches what this robot originally shipped wired as. If your real
# wiring differs, fix legs_config.json; don't rely on this ever running.
_FALLBACK_WIRING = {
    "legs_clockwise": False,
    "0": {"pins": [1, 2, 3],    "invert": [True, False, True]},
    "1": {"pins": [6, 7, 8],    "invert": [True, False, True]},
    "2": {"pins": [9, 10, 11],  "invert": [True, False, True]},
    "3": {"pins": [14, 15, 16], "invert": [True, False, True]},
    "4": {"pins": [17, 18, 19], "invert": [True, False, True]},
    "5": {"pins": [22, 23, 24], "invert": [True, False, True]},
}


def _load_json(path, fallback, label):
    try:
        with open(path) as f:
            data = json.load(f)
        print(f"[esp_legs_setup.py] loaded {path}")
        return data
    except OSError:
        print(f"[esp_legs_setup.py] {path} not found, using {label}")
        return fallback
    except Exception as e:
        print(f"[esp_legs_setup.py] could not read {path} ({e}), using {label}")
        return fallback


def _leg_angles(clockwise, num_legs):
    """One flag flips the WHOLE sequence direction at once - leg_number 0
    always stays at 0 degrees, every subsequent leg just steps the other
    way around the circle."""
    step = -ANGLE_STEP_DEG if clockwise else ANGLE_STEP_DEG
    return [(i * step) % 360 for i in range(num_legs)]


_wiring = _load_json(LEGS_CONFIG_FILE, _FALLBACK_WIRING, "built-in wiring fallback")
_calibration = _load_json(CALIBRATION_FILE, {}, "zero calibration")

_legs_clockwise = bool(_wiring.get("legs_clockwise", False))
_leg_angle_list = _leg_angles(_legs_clockwise, NUM_LEGS)
print(f"[esp_legs_setup.py] legs_clockwise={_legs_clockwise}, leg angles={_leg_angle_list}")

legs = []
for leg_number in range(NUM_LEGS):
    key = str(leg_number)
    wiring = _wiring.get(key, _FALLBACK_WIRING[key])

    leg = Leg(leg_number, wiring["pins"], _leg_angle_list[leg_number], wiring.get("invert"))
    leg.calibration = _calibration.get(key, [0, 0, 0])
    legs.append(leg)
