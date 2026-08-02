# run.py
#
# Launches every subsystem of the robot: BLE link, ESP-NOW receiver,
# the leg-mover thread, then finally hands control to the gait selector.

from time import sleep

import esp_context     # shared state received from the RC
import esp_legs_setup  # initializes each leg and builds the `legs` collection

# Bluetooth Low Energy (BLE) link to the mobile RC app.
# Runs via a system IRQ callback, no polling needed here.
from esp_ble import ESP32_BLE
ESP32_BLE("KULYA v4 OpenSource DIY")

# ESP-NOW link to a physical RC unit, polled every 50 ms via hardware timer.
from esp_now_rx import espnow_receive
from machine import Timer
# Timer(0) is already used by esp_ble.py for the connection-status LED,
# and some MicroPython/ESP32 builds no longer accept the virtual Timer(-1),
# so this uses hardware timer 1.
tim = Timer(1)
tim.init(period=50, mode=Timer.PERIODIC, callback=espnow_receive)

# Leg interpolation + servo UART output runs on its own thread.
import _thread
from esp_legmover import legmover
_thread.start_new_thread(legmover, ())

sleep(.100)
esp_context.legmover_on = True
print("esp_context.legmover_on =", esp_context.legmover_on)

# Everything is set up: hand off to the gait selector, which runs forever.
from esp_gait_selector import gait_selector
gait_selector()
