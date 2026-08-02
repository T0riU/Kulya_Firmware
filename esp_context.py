# esp_context.py
#
# Shared state module. Every other module imports this one to read/write
# the robot's current control parameters (RC_data) instead of passing
# values around explicitly. Values are updated by esp_parse_update.py
# (from BLE / ESP-NOW commands) and read by the gait modules.

RC_data = {
    "gait": "WALK",
    "spread": 115,       # leg spread radius, mm
    "height": 120,       # body height, mm
    "raise": 55,         # leg lift height during a step, mm
    "turn_angle": 0,     # turning angle, degrees
    "speed": 0,          # 0..100 %
    "dx": 0,             # step offset X
    "dy": 0,             # step offset Y
    "rx": 0,             # body roll (tilt around X)
    "ry": 0,             # body pitch (tilt around Y)
    "rz": 0,             # body yaw
    "espi": 90,          # ESP32 update interval, ms
    "servoi": 150,       # servo controller update interval, ms
    "ce_value": 100,     # collapse/expand amount, 0..100
    "leg_num": 0,        # leg index selected by LEG / CAL / ZERO / WAVE / GETCAL
    "coxa": 0,           # manual coxa target ("LEG") or calibration offset ("CAL")
    "femur": 0,          # manual femur target ("LEG") or calibration offset ("CAL")
    "tibia": 0,          # manual tibia target ("LEG") or calibration offset ("CAL")
    "roll_range": 10,    # ROLL gait: extra leg-open distance
    "roll_turn": 0,      # ROLL gait: turn bias
    "dance_id": 0,       # DANCE gait: which routine to play (see esp_gait_dance.py)
    "J_mode": "steer",   # joystick interpretation mode
}

legmover_on = False

ble_instance = None  # set by esp_ble.ESP32_BLE.__init__ once BLE starts; used by
                      # gaits (e.g. esp_gait_getcal.py) to push data back to the remote

motion_smooth_rate = 0.2      # low-pass filter factor for leg motion (0..1, higher = slower)
