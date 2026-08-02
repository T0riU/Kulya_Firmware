# esp_legmover.py
#
# Runs on its own thread (see run.py). Continuously interpolates each
# leg's current_angles towards target_angles and streams the resulting
# servo pulse-width command string to the ch24 servo controller over UART.
#
# Angles are produced elsewhere (esp_inverse_kinematics.IK, or directly by
# a gait module) and simply consumed here.

import machine
from time import sleep

import esp_context
from esp_legs_setup import legs

uart = machine.UART(2, 9600)

DEG_MIN, DEG_MAX = -90, 90
PULSE_MIN, PULSE_MAX = 500, 2500

SPEED_MIN, SPEED_MAX = 1, 100
STEPS_MIN, STEPS_MAX = 10, 1   # inverted on purpose: higher speed -> fewer substeps


def deg2pulse(angle):
    """Map a servo angle in degrees to a pulse-width value, clamped to the
    physically safe range regardless of how large angle/calibration/offset is."""
    pulse = int((angle - DEG_MIN) * (PULSE_MAX - PULSE_MIN) / (DEG_MAX - DEG_MIN) + PULSE_MIN)
    return min(max(pulse, PULSE_MIN), PULSE_MAX)


def speed2steps(speed):
    """Map a 1..100 speed value to the number of interpolation substeps."""
    return ((speed - SPEED_MIN) * (STEPS_MAX - STEPS_MIN) / (SPEED_MAX - SPEED_MIN) + STEPS_MIN)


def _joint_pulse(leg, joint_index, offset_angle):
    """Pulse for one joint of one leg, honoring that leg's own
    invert[] flag instead of assuming every leg is wired the same way."""
    angle = leg.current_angles[joint_index] + leg.calibration[joint_index] + offset_angle
    pulse = deg2pulse(angle)
    if leg.invert[joint_index]:
        pulse = 3000 - pulse
    return pulse


def _build_command_string(servo_interval):
    """Build the ch24 command string for the current angle of every leg."""
    parts = []
    for leg in legs:
        parts.append('#' + str(leg.pins[0]))
        parts.append('P' + str(_joint_pulse(leg, 0, leg.T2offset_angle)))
        parts.append('#' + str(leg.pins[1]))
        parts.append('P' + str(_joint_pulse(leg, 1, leg.T3offset_angle)))
        parts.append('#' + str(leg.pins[2]))
        parts.append('P' + str(_joint_pulse(leg, 2, leg.T4offset_angle)))

    parts.append('T' + str(round(servo_interval * 1000)))
    return ''.join(parts)


def legmover():
    print("LegMover STARTED")

    substep = 0

    while True:
        if not esp_context.legmover_on:
            continue

        esp_interval = int(esp_context.RC_data["espi"]) / 1000
        servo_interval = int(esp_context.RC_data["servoi"]) / 1000
        current_speed = int(esp_context.RC_data["speed"])

        if current_speed >= 1:
            substeps_number = speed2steps(current_speed)

            for leg in legs:
                for i in range(3):
                    leg.current_angles[i] = (leg.past_angles[i]
                                              + substep * (leg.target_angles[i] - leg.past_angles[i]) / substeps_number)

            substep += 1
            if substep >= substeps_number:
                for leg in legs:
                    leg.current_angles = list(leg.target_angles)
                substep = 0  # start the next segment exactly at past_angles, not one substep ahead

        else:  # current_speed == 0: smooth (low-pass filtered) motion instead of stepping
            rate = esp_context.motion_smooth_rate
            for leg in legs:
                for i in range(3):
                    leg.current_angles[i] = (leg.target_angles[i] * (1 - rate)
                                              + leg.current_angles[i] * rate)
                    if abs(leg.target_angles[i] - leg.current_angles[i]) < 0.5:
                        leg.current_angles[i] = leg.target_angles[i]

        uart.write(_build_command_string(servo_interval) + '\r\n')
        sleep(esp_interval)
