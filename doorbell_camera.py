#!/usr/bin/env python3
"""
interactive: Smarthome Doorbell
filename: doorbell_camera.py
description: button-triggered live camera preview
author: Isai Sanchez
date: 01-21-2026
hardware:
    - Raspberry Pi Zero 2W
    - Arducam IMX708 12MP 75D (SKU: B0312)
    - Acer 15.6" Monitor
    - Momentary arcade push button wired to GPIO_17 and GND (N.O.)
notes:
    gpiozero's button callbacks run in a BACKGROUND THREAD, not the main thread
    QT (used by Preview.QTGL to open preview window) requires all GUI operations on the MAIN THREAD
    it is also a good idea to use main thread for DRM when connectead to a headless Pi

    solution:
    The callback function (`on_button_pressed()`) ONLY sets a flag, while the main loop checks this flag and
    performs the actual camera operations. Similar pattern to an Interrupt Service Routine (ISR) on microcontrollers, which
    should also ONLY set a flag or modify volatile variables, then act upon them in `loop()`
"""

import signal
import time

from gpiozero import Button
from picamera2 import Picamera2, Preview
from systemd import daemon  # sd_notify bindings (package: python3-systemd)

# --------------------
# Configuration
# --------------------
BUTTON_GPIO = 17
ACTIVE_DURATION = 7.0  # num of seconds camera stays on
POLL_INTERVAL = 0.1  # main loop cycle time in seconds
CAMERA_INIT_RETRY_SEC = 2.0  # wait between camera init attempts at startup

# --------------------
# Global state variables
# --------------------
camera_active = False
pending_activation = False  # flag set by the button press callback
activation_timestamp = 0.0
shutdown_requested = False


# --------------------
# Signal handling
# --------------------
def handle_shutdown(signum, frame):
    global shutdown_requested
    print(f"\nReceived signal {signum}, requesting shutdown...")
    shutdown_requested = True


# Register handlers BEFORE the camera init retry loop below, so a stop request
# (SIGTERM from systemd, or SIGINT from Ctrl+C) can break us out of retrying
# instead of leaving us stuck waiting on a camera that may never appear.
signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)


# --------------------
# Camera init (with retry)
# --------------------
def init_camera():
    """
    Construct and configure the camera, retrying until it succeeds.

    At boot the camera sensor is sometimes not enumerated yet by the time this
    script starts. A single Picamera2() call would then raise and the whole
    process would crash. Rather than die, we retry on a fixed backoff until the
    sensor shows up (or until a shutdown is requested). This pairs with the
    systemd 'StartLimitIntervalSec=0' setting: between the two, a slow or flaky
    camera at startup self-heals instead of taking the exhibit down.
    """
    while not shutdown_requested:
        try:
            cam = Picamera2()
            preview_config = cam.create_preview_configuration(
                main={"size": (1920, 1080)}
            )
            cam.configure(preview_config)
            print("[init] Camera initialized")
            return cam
        except Exception as e:
            print(f"[init] ERROR initializing camera: {e}")
            print(f"[init] Retrying in {CAMERA_INIT_RETRY_SEC:.1f}s...")
            time.sleep(CAMERA_INIT_RETRY_SEC)
    return None  # shutdown requested before the camera ever came up


picam2 = init_camera()


# --------------------
# Button setup
# --------------------
button = Button(BUTTON_GPIO, pull_up=False, bounce_time=0.05)


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
        picam2.start_preview(Preview.DRM, width=1920, height=1080)
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

# Tell systemd we are fully initialized and the camera is up. This is the
# handshake for the service's Type=notify: systemd holds the unit in the
# "activating" state until it receives READY=1, then marks it active. We send
# this only after init_camera() has succeeded, so "active" means truly ready.
# (No-op when not running under systemd, e.g. when testing the script by hand.)
daemon.notify("READY=1")

try:
    while not shutdown_requested:
        # Pet the systemd watchdog once per cycle. systemd expects a WATCHDOG=1
        # ping at least every WatchdogSec seconds (see the service file). If the
        # main loop ever stops cycling -- e.g. a picamera2 call hangs instead of
        # returning -- these pings stop and systemd restarts the service for us.
        # A plain crash is already covered by Restart=always; this catches the
        # nastier case where the process is alive but frozen.
        daemon.notify("WATCHDOG=1")

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
    if picam2 is not None:  # may be None if we were told to stop mid-init
        picam2.close()
    print("Clean shutdown complete.")
    print("=" * 50)
