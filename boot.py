# boot.py
#
# Runs on every boot (including wake-boot from deep sleep). Gives a
# short delay before launching run.py so the programmer can interrupt
# boot over the REPL to reflash firmware.

from utime import sleep

STARTUP_DELAY_S = 3

print('KULYA')
print("ESP32 Started")
print('starting in', STARTUP_DELAY_S)

for i in range(STARTUP_DELAY_S):
    print('.')
    sleep(1)
else:
    import run  # launches all other components
