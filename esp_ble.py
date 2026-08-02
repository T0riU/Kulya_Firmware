# esp_ble.py
#
# Bluetooth Low Energy link to the mobile RC app, using the Nordic UART
# Service (NUS) profile. The onboard LED blinks while waiting for a
# connection and stays solidly on once connected.

from machine import Pin, Timer
import ubluetooth

import esp_context
import esp_parse_update

# Nordic UART Service (NUS) UUIDs
_NUS_UUID = '6E400001-B5A3-F393-E0A9-E50E24DCCA9E'
_RX_UUID = '6E400002-B5A3-F393-E0A9-E50E24DCCA9E'
_TX_UUID = '6E400003-B5A3-F393-E0A9-E50E24DCCA9E'

_IRQ_CENTRAL_CONNECT = 1
_IRQ_CENTRAL_DISCONNECT = 2
_IRQ_GATTS_WRITE = 3


class ESP32_BLE:
    def __init__(self, name):
        self.led = Pin(2, Pin.OUT)
        self.timer0 = Timer(0)

        self.name = name
        self.tx = None
        self.rx = None
        self.is_connected = False
        self._rx_buffer = b""  # accumulates partial writes until a '\n' terminator arrives

        self.ble = ubluetooth.BLE()
        self.ble.active(True)
        self.disconnected()
        self.ble.irq(self.ble_irq)
        self.register()
        self.advertiser()

        esp_context.ble_instance = self  # let other modules (e.g. gaits) reach send()

    def connected(self):
        self.is_connected = True
        self.led.value(1)
        self.timer0.deinit()

    def disconnected(self):
        self.is_connected = False
        self._rx_buffer = b""  # drop any partial command from the previous connection
        self.timer0.init(period=100, mode=Timer.PERIODIC,
                          callback=lambda t: self.led.value(not self.led.value()))

    def ble_irq(self, event, data):
        if event == _IRQ_CENTRAL_CONNECT:
            self.connected()
            print("[esp_ble.py] BLE RC connected")

        elif event == _IRQ_CENTRAL_DISCONNECT:
            self.advertiser()
            self.disconnected()
            print("[esp_ble.py] BLE RC disconnected")
            # TODO: consider a dedicated "disconnect" behaviour instead of a hard STOP
            esp_context.RC_data["gait"] = "STOP"

        elif event == _IRQ_GATTS_WRITE:
            # IMPORTANT: a single BLE write is NOT guaranteed to contain a
            # whole command. The default ATT MTU (23 bytes) leaves only
            # ~20 usable bytes per "write without response" - anything
            # longer (e.g. "gait:LEG;leg_num:2;coxa:10;femur:0;tibia:0;",
            # 43 bytes) gets split across multiple writes/IRQs. Buffer
            # everything and only parse once we see the '\n' terminator
            # the remote always sends at the end of a command.
            self._rx_buffer += self.ble.gatts_read(self.rx)

            while b'\n' in self._rx_buffer:
                line, self._rx_buffer = self._rx_buffer.split(b'\n', 1)
                message = line.decode('UTF-8').strip()
                if message:
                    print("[esp_ble.py] ", message)
                    esp_parse_update.parse_and_update(message)

            # safety valve: if something is spamming data with no '\n' ever,
            # don't let the buffer grow forever
            if len(self._rx_buffer) > 512:
                print("[esp_ble.py] rx buffer overflow, discarding:", self._rx_buffer[:50])
                self._rx_buffer = b""

    def register(self):
        BLE_NUS = ubluetooth.UUID(_NUS_UUID)
        BLE_RX = (ubluetooth.UUID(_RX_UUID), ubluetooth.FLAG_WRITE)
        BLE_TX = (ubluetooth.UUID(_TX_UUID), ubluetooth.FLAG_NOTIFY)

        BLE_UART = (BLE_NUS, (BLE_TX, BLE_RX))
        SERVICES = (BLE_UART,)
        ((self.tx, self.rx,),) = self.ble.gatts_register_services(SERVICES)

        # Append-mode buffer: queues incoming write data instead of letting
        # a fast second write silently clobber the first before ble_irq()
        # gets scheduled to read it. Without this, back-to-back writes
        # (e.g. several commands sent quickly) can lose data even before
        # it reaches our own _rx_buffer reassembly in ble_irq().
        self.ble.gatts_set_buffer(self.rx, 512, True)

    def send(self, data):
        if not self.is_connected:
            print(f"[esp_ble.py] send() skipped, not connected: {data}")
            return False
        try:
            self.ble.gatts_notify(0, self.tx, data + '\n')
            return True
        except Exception as e:
            print(f"[esp_ble.py] send() failed: {e}")
            return False

    def advertiser(self):
        name_bytes = self.name.encode('utf-8')

        adv_data = bytearray(b'\x02\x01\x02')                       # flags
        adv_data += bytearray([len(name_bytes) + 1, 0x09])          # length + "complete local name" type
        adv_data += name_bytes

        self.ble.gap_advertise(100, adv_data)

        print('[esp_ble.py] BLE advertising started: ', self.name)
