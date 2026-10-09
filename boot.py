# boot.py
#
# Runs once at power-on, before main.py. Replaces v4's boot.py.


import time
import kconfig

cfg = kconfig.load()

if cfg["cpu_freq_mhz"]:
    try:
        import machine
        machine.freq(cfg["cpu_freq_mhz"] * 1_000_000)
    except Exception as e:
        print("[boot] could not set CPU frequency:", e)

if cfg["boot_delay_s"]:
    print("[boot] %ds window to interrupt (Ctrl-C) before startup" % cfg["boot_delay_s"])
    time.sleep(cfg["boot_delay_s"])

try:
    import main
    main.run()
except KeyboardInterrupt:
    print("[boot] interrupted by user - dropping to REPL")
except Exception as e:
    import sys
    sys.print_exception(e)
    reset_s = cfg["reset_on_crash_s"]
    if reset_s:
        print("[boot] main.run() crashed - rebooting in %ds" % reset_s)
        time.sleep(reset_s)
        import machine
        machine.reset()
    else:
        print("[boot] main.run() crashed - staying in the REPL for debugging")
