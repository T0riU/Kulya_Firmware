# esp_gait_selector.py
#
# Called once by run.py. Loops forever, watching esp_context.RC_data["gait"]
# and dispatching to the matching gait_*(legs) function. Each gait
# function itself loops internally for as long as its gait name stays
# selected, so gait_selector only needs to re-check every so often.

from utime import sleep
import esp_context

from esp_gait_walk import gait_walk
from esp_gait_ce import gait_ce
from esp_gait_leg import gait_leg
from esp_gait_roll import gait_roll
from esp_gait_wave import gait_wave
from esp_gait_dance import gait_dance
from esp_gait_zero import gait_zero, gait_zero_all
from esp_gait_cal import gait_cal
from esp_gait_save import gait_save
from esp_gait_getcal import gait_getcal

from esp_legs_setup import legs

GAITS = {
    'WALK': gait_walk,
    'CE': gait_ce,
    'LEG': gait_leg,
    'ROLL': gait_roll,
    'WAVE': gait_wave,        # wave ONE leg (select via leg_num) - was two separate gaits "wavl"/"wavr"
    'DANCE': gait_dance,      # scripted whole-body dance routine
    'ZERO': gait_zero,        # center ONE leg (select via leg_num), for horn mounting
    'ZEROALL': gait_zero_all, # center ALL legs at once, for horn mounting
    'CAL': gait_cal,          # live software calibration (select leg via leg_num)
    'SAVE': gait_save,        # one-shot: write current calibration to flash, then bounces back to CAL
    'GETCAL': gait_getcal,    # one-shot: send current calibration for leg_num back to the remote
    # 'STOP' intentionally has no handler: robot stays idle.
    # >>HERE<< an idle gait could be added if the robot should do
    # something while parked in STOP.
}


def gait_selector():
    print('gait_selector:   Started')
    while True:
        gait_fn = GAITS.get(esp_context.RC_data["gait"])
        if gait_fn is not None:
            try:
                gait_fn(legs)
            except Exception as e:
                # A crash INSIDE a gait must never take down the whole
                # selector loop - without this, one bad value (e.g. an
                # out-of-range leg_num) would silently kill gait_selector
                # forever, and the robot would stop responding to ANY
                # command until a full reboot, with no sign of why.
                print(f"[esp_gait_selector.py] gait '{esp_context.RC_data['gait']}' crashed: {e}")
                esp_context.RC_data["gait"] = "STOP"

        sleep(.5)
