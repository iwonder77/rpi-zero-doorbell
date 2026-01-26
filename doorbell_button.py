#!usr/bin/env python3
"""
interactive: Townhome Doorbell
filename: cam_button.py
description: button-triggered live camera preview
---DEVELOPMENT VERSION (uses QtGL preview)---

author: Isai Sanchez
date: 01-21-2026
hardware:
    - Raspberry Pi 4 Model B
    - Arducam IMX708 12MP 75D (SKU: B0312)
    - Acer 15.6" Monitor
    - Momentary arcade push button wired to GPIO_17 and GND (N.O.)
notes:
    gpiozero's button callbacks run in a BACKGROUND THREAD, not the main thread
    QT (used by Preview.QTGL to open preview window) requires all GUI operations on the MAIN THREAD

    solution:
    The callback function (`on_button_pressed()`) ONLY sets a flag, while the main loop checks this flag and
    performs the actual camera operations. Similar pattern to an Interrupt Service Routine (ISR) on microcontrollers, which
    should also ONLY set a flag or modify volatile variables, then act upon them in `loop()`
"""

import signal
import time

from gpiozero import Button
from picamera2 import Picamera2, Preview

# --------------------
# Configuration
# --------------------
BUTTON_GPIO = 17
ACTIVE_DURATION = 10.0  # num of seconds camera stays on
POLL_INTERVAL = 0.1  # main loop cycle time in seconds

# --------------------
# Global state variables
# --------------------
camera_active = False
pending_activation = False  # flag set by the button press callback
activation_timestamp = 0.0
shutdown_requested = False

# --------------------
# Camera init
# --------------------
picam2 = Picamera2()
preview_config = picam2.create_preview_configuration(main={"size": (1920, 1080)})
picam2.configure(preview_config)

# --------------------
# Button setup
# --------------------
button = Button(BUTTON_GPIO, pull_up=True, bounce_time=0.05)


# --------------------
# Signal handling
# --------------------
def handle_shutdown(signum, frame):
    global shutdown_requested
    print(f"\nReceived signal {signum}, requesting shutdown...")
    shutdown_requested = True


signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)


# --------------------
# Button callback (runs in background thread!)
# --------------------
def on_button_pressed():
    """
    IMPORTANT: This runs in gpiozero's background thread. We MUST NOT do GUI
    operations here, only set flags
    """
    global pending_activation
    if camera_active or pending_activation:
        # ignore button presses while already active or about to be
        return

    print("[callback] Button pressed - setting pending flag")
    pending_activation = True


# attach callback function
button.when_pressed = on_button_pressed


# --------------------
# Camera control (must run in main thread)
# --------------------
def activate_camera():
    # start preview and camera
    global camera_active, activation_timestamp
    print("[main] Activating camera...")

    try:
        picam2.start_preview(Preview.QTGL, width=1920, height=1080)
        picam2.start()
        activation_timestamp = time.monotonic()
        camera_active = True
        print("[main] Camera active")
    except Exception as e:
        print(f"[main] ERROR starting camera: {e}")
        camera_active = False


def deactivate_camera():
    # stop camera and preview
    global camera_active

    print("[main] Deactivating camera...")
    try:
        picam2.stop()
        picam2.stop_preview()
    except Exception as e:
        print(f"[main] ERROR stopping camera: {e}")
    finally:
        camera_active = False
        print("[main] Camera inactive")


# --------------------
# Main loop
# --------------------
print("=" * 50)
print("System ready. Press button to activate camera.")
print("Press Ctrl+C to exit.")
print("=" * 50)

try:
    while not shutdown_requested:
        # PENDING -> ACTIVE state transition
        if pending_activation and not camera_active:
            pending_activation = False  # clear pending flag first, then activate
            activate_camera()

        # ACTIVE -> IDLE (timeout)
        if camera_active:
            elapsed = time.monotonic() - activation_timestamp
            if elapsed >= ACTIVE_DURATION:
                deactivate_camera()

        time.sleep(POLL_INTERVAL)
finally:
    print("\n" + "=" * 50)
    print("Shutting down...")
    if camera_active:
        deactivate_camera()
    picam2.close()
    print("Clean shutdown complete.")
    print("=" * 50)
