# esp_gait_ce.py
#
# Gait "CE" (Collapse / Expand): every leg's femur/tibia angle is driven
# together from esp_context.RC_data["ce_value"] (0..100), letting the
# body squat down or stand up evenly on all six legs.

import esp_context

FEMUR_LIMITS = (94, 0)
TIBIA_LIMITS = (-113, 0)


def _map(x, in_min, in_max, out_min, out_max):
    return int((x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)


def gait_ce(legs):
    while esp_context.RC_data["gait"] == 'CE':
        ce_value = int(esp_context.RC_data["ce_value"])

        femur_angle = _map(ce_value, 0, 100, FEMUR_LIMITS[0], FEMUR_LIMITS[1])
        tibia_angle = _map(ce_value, 0, 100, TIBIA_LIMITS[0], TIBIA_LIMITS[1])

        for leg in legs:
            leg.current_angles = [0, femur_angle, tibia_angle]
            leg.target_angles = list(leg.current_angles)
            leg.past_angles = list(leg.current_angles)
