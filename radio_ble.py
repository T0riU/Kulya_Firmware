# radio_ble.py
#
# BLE Nordic UART Service. Replaces esp_ble.py.

import time
import bluetooth
from micropython import const

try:
    _ticks_diff = time.ticks_diff
except AttributeError:                      # CPython (tests)
    _ticks_diff = lambda a, b: a - b

_TAIL_MAX_MS = 250      # a held-back fragment older than this will never be completed

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_IRQ_MTU_EXCHANGED = const(21)

_UART_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
_UART_TX = (bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E"), bluetooth.FLAG_NOTIFY)
_UART_RX = (bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E"),
            bluetooth.FLAG_WRITE | bluetooth.FLAG_WRITE_NO_RESPONSE)
_UART_SERVICE = (_UART_UUID, (_UART_TX, _UART_RX))


class BLELink:
    def __init__(self, name, st, now_ms):
        self.name = name
        self.st = st
        self.now_ms = now_ms
        self.conn = None
        self.tail = ""                 # unfinished last pair of a command split over several BLE packets
        self.tail_ms = 0
        self.frag = 20                  # payload of a full packet (MTU 23 - 3); updated on MTU exchange
        self.ble = bluetooth.BLE()
        self.ble.active(True)
        self.ble.irq(self._irq)
        ((self.h_tx, self.h_rx),) = self.ble.gatts_register_services((_UART_SERVICE,))
        # The default value buffer is 20 bytes: a longer write is silently cut off.
        # append=True keeps back-to-back writes instead of overwriting the first.
        try:
            self.ble.gatts_set_buffer(self.h_rx, 256, True)
        except Exception:
            pass
        self._advertise()

    def _advertise(self):
        nb = self.name.encode()
        adv = bytearray((2, 0x01, 0x06)) + bytearray((len(nb) + 1, 0x09)) + nb
        self.ble.gap_advertise(100_000, adv)     # 100 ms, in us (v4 passed 100 - i.e. 0.1 ms, out of spec)

    def _irq(self, event, data):
        if event == _IRQ_CENTRAL_CONNECT:
            self.conn = data[0]
            self.tail = ""
        elif event == _IRQ_CENTRAL_DISCONNECT:
            self.conn = None
            self.tail = ""
            self.st.on_disconnect()
            self._advertise()
        elif event == _IRQ_MTU_EXCHANGED:
            self.frag = max(20, data[1] - 3)
        elif event == _IRQ_GATTS_WRITE:
            conn, attr = data
            if attr == self.h_rx:
                try:
                    raw = self.ble.gatts_read(self.h_rx)
                    self._feed(raw.decode())
                except Exception:
                    pass                          # garbage bytes - ignore silently

    def _feed(self, chunk):
        """A command longer than one BLE packet arrives in pieces. parse() applies
        every complete "key:value" pair immediately, so a piece cut in the middle
        ("height:1" + "20;") used to be applied as height:1 (-> clamped to 30!).
        A full-size packet that does not end on a delimiter is held back until
        the next packet completes it."""
        now = self.now_ms()
        if self.tail and _ticks_diff(now, self.tail_ms) > _TAIL_MAX_MS:
            self.tail = ""                        # stale: if it were glued to the NEXT, unrelated
                                                  # command it would swallow it ("heig"+"gait:STOP;")
        s = self.tail + chunk
        self.tail = ""
        if len(chunk) >= self.frag and s and s[-1] != ";" and s[-1] != "\n":
            k = max(s.rfind(";"), s.rfind("\n"))
            self.tail = s[k + 1:]
            self.tail_ms = now
            s = s[:k + 1]
            if len(self.tail) > 64:               # nonsense - don't let it grow
                self.tail = ""
        if s:
            self.st.parse(s, now)

    def notify(self, text):
        if self.conn is None:
            return
        try:
            self.ble.gatts_notify(self.conn, self.h_tx, text)
        except Exception:
            pass
