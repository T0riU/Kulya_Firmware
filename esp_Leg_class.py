# esp_Leg_class.py
#
# Represents a single leg of the hexapod: its geometry, servo pins,
# angle limits/calibration and the current/target/past angle state
# used by esp_legmover.py to smoothly interpolate motion.


class Leg:

    def __init__(self, leg_number, pins, leg_angle, invert=None):
        """
        leg_number: 0..5, just an identifier/index - doesn't imply a direction
        pins: [coxa_pin, femur_pin, tibia_pin] channels on the ch24 servo controller
        leg_angle: this leg's mounting angle in degrees (0..359) around the
                body, measured in whichever rotational direction the legs
                are actually wired. Computed by esp_legs_setup.py from
                legs_config.json's single "legs_clockwise" flag - Leg itself
                doesn't care which direction that was, it just uses the
                angle it's given.
        invert: [coxa, femur, tibia] booleans - whether esp_legmover.py should
                mirror that joint's pulse (True) or send it direct (False).
                Needed because servo horns aren't necessarily mounted the same
                way on every leg. Defaults to [True, False, True], matching
                every leg's original hardcoded behaviour - override per leg
                in legs_config.json if your wiring differs.
        """
        self.leg_number = leg_number
        self.leg_angle = leg_angle

        # link lengths and joint offsets, mm / degrees
        self.origin_distance = 41    # a1
        self.coxa_length = 10        # a2
        self.femur_length = 81       # a3
        self.tibia_length = 134      # a4
        self.T2offset_angle = 0
        self.T3offset_angle = -7
        self.T4offset_angle = 23

        # connection to ch24 servo controller
        self.pins = pins
        self.coxa_pin = pins[0]
        self.femur_pin = pins[1]
        self.tibia_pin = pins[2]

        self.invert = invert if invert is not None else [True, False, True]

        # angle limits, degrees
        self.coxa_limits = [-29, 29]
        self.femur_limits = [-70, 90]
        self.tibia_limits = [-90, 36]

        # per-leg calibration offsets, degrees - loaded from calibration.json
        # by esp_legs_setup.py, defaults to [0,0,0] until calibrated
        self.calibration = [0, 0, 0]  # [coxa, femur, tibia]

        # angle state: (coxa_angle, femur_angle, tibia_angle)
        self.past_angles = [0, 0, 0]
        self.current_angles = [0, 0, 0]
        self.target_angles = [0, 0, 0]
        self.on_target = False

    def is_on_target(self):
        self.on_target = (self.target_angles == self.current_angles)
        if self.on_target:
            self.past_angles = list(self.target_angles)
        return self.on_target
