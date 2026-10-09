# servo.py
#
# Single owner of the UART connection to the ch24 servo controller.

class Bus:
    def __init__(self, cfg):
        from machine import UART
        u = cfg["uart"]
        kw = {"baudrate": int(u["baud"])}
        if u.get("tx") is not None:
            kw["tx"] = u["tx"]
        if u.get("rx") is not None:
            kw["rx"] = u["rx"]
        if u.get("txbuf"):
            kw["txbuf"] = u["txbuf"]     
        self.baud = int(u["baud"])
        self.uart = UART(int(u["id"]), **kw)

    def write(self, s):
        self.uart.write(s)

    def tx_ms(self, nbytes):
        """Transmit time for nbytes over UART (8N1 = 10 bits/byte), in ms."""
        return nbytes * 10000.0 / self.baud + 1.0
