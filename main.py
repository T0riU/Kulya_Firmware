import sys
import time
import kconfig
import robot as robot_mod
import servo
from proto import State
from engine import Engine


def now_ms():
    return time.ticks_ms()


def run():
    cfg = kconfig.load()

    bus = servo.Bus(cfg)
    robot = robot_mod.Robot(cfg, bus)
    st = State(cfg)
    eng = Engine(cfg, robot, st)
    ble = None
    enow = None
    try:
        from radio_ble import BLELink
        ble = BLELink(cfg["ble_name"], st, now_ms)
        eng.notify_cb = ble.notify
    except Exception as e:
        print("[boot] BLE unavailable:", e)
    try:
        from radio_espnow import EspNowLink
        enow = EspNowLink(cfg, st, now_ms)
    except Exception as e:
        print("[boot] ESP-NOW unavailable:", e)

    wdt = None
    if cfg["wdt_ms"]:
        try:
            from machine import WDT
            wdt = WDT(timeout=cfg["wdt_ms"])
        except Exception:
            pass

    tick_ms = cfg["tick_ms"]
    debug = cfg["debug"]

    last = time.ticks_ms()
    dbg_ms = last
    period_est = tick_ms          # our best guess at the real gap until the next frame goes out
    errs = 0
    while True:
        t0 = time.ticks_ms()
        dt_ms = time.ticks_diff(t0, last)
        if dt_ms <= 0:
            dt_ms = 1
        last = t0
        dt = dt_ms / 1000.0
        if dt > 0.25:                 # a long pause (GC/REPL) - don't jump joints in one step
            dt = 0.25

        try:
            if enow is not None:
                enow.poll()
            eng.tick(dt, t0)
            errs = 0
        except Exception as e:
            errs += 1
            if errs == 1:
                sys.print_exception(e)
            if errs >= 25:
                raise
            eng.recover()
        nbytes = robot.send(period_est, dt_ms)
        tx_ms = bus.tx_ms(nbytes) if nbytes else 0.0
        period = tick_ms if tx_ms <= tick_ms else int(tx_ms) + 2
        period_est = period
        eng.frame_s = period / 1000.0

        if wdt:
            wdt.feed()
        if debug and time.ticks_diff(t0, dbg_ms) >= 500:     # ~2 prints/s (it used to print every
            dbg_ms = t0                                       # tick during every other second)
            print(st.gait, [round(x) for x in robot.cur[:3]])

        elapsed = time.ticks_diff(time.ticks_ms(), t0)
        sleep_ms = period - elapsed
        if sleep_ms > 0:
            time.sleep_ms(sleep_ms)
