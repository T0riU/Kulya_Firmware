# kconfig.py
#
# Configuration loader. Four optional sources (built-in defaults are used
# for anything missing):
#   config.json       - everything new: UART, geometry, timing, behaviour
#   legs_config.json  - leg wiring (format UNCHANGED since v4)
#   calibration.json  - per-joint calibration (format UNCHANGED since v4)
#   radio_config.json - ESP-NOW channel (format UNCHANGED since v4)

try:
    import ujson as json
except ImportError:
    import json

CONFIG_FILE = "config.json"
LEGS_FILE = "legs_config.json"
CAL_FILE = "calibration.json"
RADIO_FILE = "radio_config.json"

DEFAULTS = {
    "ble_name": "KULYA v4 OpenSource DIY",   # BLE name - kept as in v4 so the app finds it
    "boot_delay_s": 3,                       # window to press Ctrl-C before main.py starts (in boot.py)
    "reset_on_crash_s": 0,                   # 0 = stay in the REPL after an unhandled crash (dev mode).
                                              # >0 = print the traceback, wait this many seconds, then
                                              # machine.reset() (use this once the robot is deployed
                                              # and nobody is watching the serial console)
    "debug": False,                          # REPL prints (keep off in normal use - print() is slow)
    "wdt_ms": 0,                             # 0 = hardware watchdog disabled
    "cpu_freq_mhz": 0,                       # 0 = leave default; e.g. 240 to force max clock on ESP32

    # --- ch24-style (SSC-32 compatible) servo bus ---------------------
    # NOTE: 9600 is the safe v4 default (works with every board) but an
    # 18-servo frame (~143 bytes) takes ~150 ms to transmit at that rate.
    # If your servo controller supports it, set this to 115200 (frame
    # ~12 ms) for noticeably smoother motion.
    "uart": {"id": 2, "baud": 9600, "tx": None, "rx": None, "txbuf": 1024},
    "tick_ms": 20,            # target loop period; auto-stretched to the UART frame time if needed
    "servo_t_scale": 1.1,     # servo move time 'T' = loop period * this factor
    "refresh_ms": 1000,       # how often to resend ALL channels even if unchanged (keep-alive)

    # --- leg geometry (mm / degrees) -----------------------------------
    "geometry": {
        "a1": 41, "a2": 10, "a3": 81, "a4": 134,          # body radius, coxa, femur, tibia
        "offsets": [0, -7, 23],                            # mechanical zero offsets [coxa, femur, tibia]
        "limits": {"coxa": [-29, 29], "femur": [-70, 90], "tibia": [-90, 36]},
    },
    "poses": {"fold": [0, 94, -113], "cal_limit": 20},     # folded pose; calibration range, deg

    # --- motion ----------------------------------------------------------
    "motion": {
        "vmax_walk": 600.0,      # joint speed cap while walking, deg/s (safety limit)
        "vmax_pose": 350.0,      # ... in pose modes (CE, LEG, dances)
        "vmax_settle": 240.0,    # ... during the auto-transition between modes
        "vmax_boot": 90.0,       # ... for the very first move after power-on (real
                                 # servo position is unknown, so the first move to
                                 # the startup stance must be slow and safe)
        "settle_tol": 1.5,       # transition counts as done once every joint is
                                 # within this many degrees of its target
        "settle_timeout_ms": 1500,
        "tau_body_ms": 120.0,    # smoothing for body height/tilt/shift
        "tau_stride_ms": 70.0,   # smoothing for stride length (joystick)
    },
    "walk": {
        "cycle_ms": [2400, 500],   # walk cycle period at speed=1 and speed=100
        "lift_full_mm": 10.0,      # leg lift scales down for shorter strides (no "marching in place")
        "min_samples": 12,         # min servo frames per walk cycle; the cycle is stretched if the UART is too slow
    },
    "joy": {"deadzone": 6},        # joystick dead zone, % (0 = same behaviour as v4)
    "link": {
        "timeout_ms": 0,           # 0 = disabled. >0: stop the robot if no command arrived for
                                   # this many ms (useful for remotes that stream J_XY continuously)
        "espnow_peers": [],        # ["aa:bb:cc:dd:ee:ff", ...]; empty = accept from anyone
    },
    "dance": {"lift_mm": 40.0, "move_frac": 0.7},
}


def _merge(dst, src):
    for k in src:
        v = src[k]
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _merge(dst[k], v)
        else:
            dst[k] = v


def load_json(path, fallback=None):
    try:
        with open(path) as f:
            return json.load(f)
    except OSError:
        return fallback
    except Exception as e:                 # malformed JSON
        print("[kconfig] cannot parse", path, e)
        return fallback


def _copy(d):
    if isinstance(d, dict):
        return {k: _copy(d[k]) for k in d}
    if isinstance(d, list):
        return list(d)
    return d


# Fallback wiring used only if legs_config.json is missing or invalid.
# Matches the real shipped config (legs_clockwise=True; v4's fallback had
# this set to False by mistake, which would make the robot walk mirrored).
FALLBACK_WIRING = {
    "legs_clockwise": True,
    "0": {"pins": [1, 2, 3], "invert": [True, False, True]},
    "1": {"pins": [6, 7, 8], "invert": [True, False, True]},
    "2": {"pins": [9, 10, 11], "invert": [True, False, True]},
    "3": {"pins": [14, 15, 16], "invert": [True, False, True]},
    "4": {"pins": [17, 18, 19], "invert": [True, False, True]},
    "5": {"pins": [22, 23, 24], "invert": [True, False, True]},
}


def _valid_wiring(w):
    try:
        n = 0
        seen = set()
        while str(n) in w:
            leg = w[str(n)]
            p = leg["pins"]
            if len(p) != 3:
                return 0
            for x in p:
                if not isinstance(x, int) or x < 0 or x in seen:   # duplicate pin = two joints on one servo
                    return 0
                seen.add(x)
            inv = leg.get("invert")
            if inv is not None and len(inv) != 3:                    # a short list crashed Robot.__init__/send()
                return 0
            n += 1
        return n if n >= 2 and n % 2 == 0 else 0
    except Exception:
        return 0


def load():
    cfg = _copy(DEFAULTS)
    user = load_json(CONFIG_FILE, {})
    if isinstance(user, dict):
        _merge(cfg, user)

    wiring = load_json(LEGS_FILE, None)
    n = _valid_wiring(wiring) if isinstance(wiring, dict) else 0
    if not n:
        print("[kconfig] legs_config.json missing/invalid - using built-in wiring")
        wiring = _copy(FALLBACK_WIRING)
        n = 6
    cfg["wiring"] = wiring
    cfg["n_legs"] = n

    cal = load_json(CAL_FILE, {})
    cfg["cal"] = cal if isinstance(cal, dict) else {}

    radio = load_json(RADIO_FILE, {})
    ch = radio.get("channel", 6) if isinstance(radio, dict) else 6
    cfg["channel"] = ch if isinstance(ch, int) and 1 <= ch <= 14 else 6
    return cfg
