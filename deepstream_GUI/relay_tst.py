#!/usr/bin/env python3
import time

try:
    import Jetson.GPIO as GPIO
except ImportError:
    raise SystemExit("Install Jetson.GPIO:  sudo apt-get install -y python3-jetson-gpio")

# ==== CONFIG ====
BOARD_PIN = 12          # physical pin number on the 40-pin header (GPIO18)
ACTIVE_LOW = True       # set True for most relay boards; False if your relay expects HIGH
PULSE_MS = 500          # how long to energize the relay
IDLE_MS = 800           # gap between pulses when looping
REPEAT = 3              # how many test pulses

def relay_on(pin):
    GPIO.output(pin, GPIO.LOW if ACTIVE_LOW else GPIO.HIGH)

def relay_off(pin):
    GPIO.output(pin, GPIO.HIGH if ACTIVE_LOW else GPIO.LOW)

def main():
    print(f"[INFO] Using BOARD pin {BOARD_PIN} (ACTIVE_LOW={ACTIVE_LOW})")
    GPIO.setmode(GPIO.BOARD)   # use physical pin numbering
    # Set initial state = not energized
    initial = GPIO.HIGH if ACTIVE_LOW else GPIO.LOW
    GPIO.setup(BOARD_PIN, GPIO.OUT, initial=initial)

    try:
        for i in range(1, REPEAT+1):
            print(f"[TEST] Pulse {i}/{REPEAT} ...")
            relay_on(BOARD_PIN)
            time.sleep(PULSE_MS/1000.0)
            relay_off(BOARD_PIN)
            time.sleep(IDLE_MS/1000.0)
        print("[DONE] If your relay clicked, wiring & polarity are correct.")
    finally:
        GPIO.cleanup()
        print("[CLEANUP] GPIO released.")

if __name__ == "__main__":
    main()

