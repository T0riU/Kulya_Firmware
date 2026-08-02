# esp_now_rx.py
#
# ESP-NOW receiver: listens for commands from a physical RC unit.
# espnow_receive() is meant to be used as a Timer callback (see run.py),
# fired every ~50 ms on the main thread.

import network
import espnow

import esp_parse_update

print('[esp_now_rx.py] - STARTED esp_now Wifi receiver')

wifi = network.WLAN(network.STA_IF)
wifi.active(True)

e = espnow.ESPNow()
e.active(True)

mac = wifi.config('mac')
mac_str = ':'.join('%02x' % b for b in mac)
print('MAC address:', mac_str)


def espnow_receive(t):
    """Timer callback: drain any pending ESP-NOW message and apply it."""
    peer, msg = e.recv(0)
    if msg:
        message = msg.decode('UTF-8').strip()
        print("[esp_now_rx.py] ", message)
        esp_parse_update.parse_and_update(message)
