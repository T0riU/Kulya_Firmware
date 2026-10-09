# radio_espnow.py
#
# Receives commands from the physical remote over ESP-NOW. Replaces
# esp_now_rx.py.

import network
import espnow


def _mac(m):
    """"aa:bb:cc:dd:ee:ff" -> 6 bytes. recv() returns the sender as bytes, so a
    string allowlist never matched and EVERY packet was dropped."""
    if isinstance(m, (bytes, bytearray)):
        return bytes(m)
    b = bytes(int(p, 16) for p in m.replace("-", ":").split(":"))
    if len(b) != 6:
        raise ValueError(m)
    return b


class EspNowLink:
    def __init__(self, cfg, st, now_ms):
        self.st = st
        self.now_ms = now_ms
        allow = set()
        for m in cfg["link"]["espnow_peers"]:
            try:
                allow.add(_mac(m))
            except Exception:
                print("[espnow] bad MAC in link.espnow_peers:", m)
        self.allow = allow or None
        sta = network.WLAN(network.STA_IF)
        sta.active(True)
        sta.disconnect()
        try:
            sta.config(channel=cfg["channel"])
        except Exception:
            pass
        self.e = espnow.ESPNow()
        self.e.active(True)
        try:
            self.e.add_peer(b"\xff" * 6)          # broadcast peer, same as v4
        except Exception:
            pass

    def poll(self):
        """Parse every packet currently queued. Returns True if anything
        was received."""
        got = False
        e = self.e
        while True:
            mac, msg = e.recv(0)
            if mac is None or msg is None:
                break
            got = True
            if self.allow is not None and bytes(mac) not in self.allow:
                continue
            try:
                self.st.parse(msg.decode(), self.now_ms())
            except Exception:
                pass
        return got
