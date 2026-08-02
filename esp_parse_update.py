# esp_parse_update.py
#
# Parses "param:value;param:value;..." strings coming in over BLE or
# ESP-NOW and updates esp_context.RC_data accordingly. Also handles the
# special "J_XY" joystick pair, converting it to polar coordinates and
# then, depending on the current joystick mode, into the actual
# dx/dy/turn_angle/speed/rx/ry parameters the gaits consume.

import esp_context
from math import sqrt


def _apply_joystick(value):
    """value is the raw 'Jx|Jy' string from the J_XY param."""
    J_x_str, J_y_str = value.split('|', 1)
    J_x = int(J_x_str)
    J_y = int(J_y_str)

    # Clamp the joystick vector to the max radius (100) the RC app can send,
    # without touching its direction. (Previously this went through
    # round(atan2(...)) which rounds the angle to whole RADIANS -- only
    # ~7 distinct directions on the whole circle -- collapsing most stick
    # positions onto the same handful of directions.)
    radius = sqrt(J_x ** 2 + J_y ** 2)
    if radius > 100:
        scale = 100 / radius
        J_x = round(J_x * scale)
        J_y = round(J_y * scale)
    radius = round(min(radius, 100))

    print(f"J_x {J_x}   J_y {J_y}")

    mode = esp_context.RC_data["J_mode"]

    # The RC app only ever sends J_XY, never an explicit "gait:" command.
    # If we're currently stopped (boot default changed, or esp_ble.py forced
    # a STOP on disconnect), a movement-intent joystick mode should bring
    # the robot back to walking instead of leaving it stuck forever.
    if esp_context.RC_data["gait"] == "STOP" and mode in ("sides", "steer"):
        esp_context.RC_data["gait"] = "WALK"

    if mode == "sides":
        esp_context.RC_data["dx"] = J_x * .45
        esp_context.RC_data["dy"] = J_y * .45
        esp_context.RC_data["speed"] = abs(radius)
        esp_context.RC_data["turn_angle"] = 0

    elif mode == "steer":
        esp_context.RC_data["turn_angle"] = round(J_x * .10)
        esp_context.RC_data["dx"] = 0
        esp_context.RC_data["dy"] = J_y * .45
        esp_context.RC_data["speed"] = abs(radius)

    elif mode == "shift":
        esp_context.RC_data["dx"] = J_x * .45
        esp_context.RC_data["dy"] = J_y * .45
        esp_context.RC_data["speed"] = 0
        esp_context.RC_data["turn_angle"] = 0
        esp_context.motion_smooth_rate = .35

    elif mode == "tilt":
        esp_context.RC_data["rx"] = J_x * .35
        esp_context.RC_data["ry"] = J_y * .35
        esp_context.RC_data["speed"] = 0
        esp_context.RC_data["turn_angle"] = 0
        esp_context.motion_smooth_rate = .55

    print("dx: ", esp_context.RC_data["dx"],
          " dy: ", esp_context.RC_data["dy"],
          " speed: ", esp_context.RC_data["speed"],
          " turn_angle: ", esp_context.RC_data["turn_angle"])


def parse_and_update(param_string):
    """Parse a ';'-separated 'param:value' command string and update RC_data."""
    for pair in param_string.split(';'):
        pair = pair.strip()
        if not pair:
            continue

        if ':' not in pair:
            print(f"Warning: Skipping invalid pair '{pair}'.")
            continue

        param, value = pair.split(':', 1)

        try:
            try:
                value = int(value)
            except ValueError:
                pass  # not a number (e.g. gait name like "WALK") - keep as string

            if param in esp_context.RC_data:
                esp_context.RC_data[param] = value

            if param == "J_XY":
                _apply_joystick(value)

        except ValueError:
            print(f"Warning: Invalid value for {param}. Skipping this pair.")
