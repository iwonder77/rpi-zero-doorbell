# Raspberry Pi Zero 2w Doorbell Interactive

## Overview

This repository holds the firmware (python script), systemd service file, and steps for setting up a Raspberry Pi Zero 2W for the Doorbell interactive in the Smarthome exhibit of Kidopolis at Thanksgiving Point's Museum of Natural Curiosity.

### Privacy

The exhibit shows a **live preview only**. No frames are ever written to disk,
nothing is recorded, and nothing is transmitted. If a visitor or parent asks,
that is the answer.

### Network

The exhibit needs **no network to run**. WiFi is only used for SSH access,
package and firmware updates (like in first-time setup), and clock sync. If the museum WiFi is down for a week the doorbell keeps working perfectly.

## Hardware

- Raspberry Pi Zero 2W
- [Arducam IMX708 12MP](https://docs.arducam.com/Raspberry-Pi-Camera/Native-camera/12MP-IMX708/#products-list) camera (SKU: B0312)
- Acer 15.6" Monitor
- Arcade button (N.O.) + Pull-up, RC and ESD protection circuit

## First-Time Setup

1. Flash a reliable SD card with Raspberry Pi OS Lite (64-bit) using the [Raspberry Pi Imager](https://www.raspberrypi.com/software/). Ensure the following configuration settings are set:
   - hostname, username=`doorbell`, and password (write these down somewhere)
   - capital city: Washington D.C.
   - time zone: America/Denver
   - keyboard layout: us
   - **Case Sensitive** SSID (TPI-Employee) and password
   - enable SSH
2. Insert SD card into slot, connect monitor and keyboard, then boot up the Pi (visually inspect boot up process and take note of any errors)
   - NOTE: make sure you have a reliable power supply (I went with a 5V 3A rated one), lots of issues stem from a faulty power supply
3. Once the tty1 console login screen appears, sign in with username and password (or SSH into the Pi if you prefer)
4. Check network connection by executing: `ping -c 3 google.com`
   - NOTE: network connection may take a couple of minutes, also the Pi Zero 2w only supports 2.4GHz Wifi, so make sure you have a solid connection (I found putting it close to the shop router and connecting via SSH worked well)
   - if network connection is successful, skip to step 5, if it is not successful, you will have to troubleshoot each layer of the connnection process to see where things went wrong (we need wifi for package updates and installation)
     - Layer 0: Wifi hardware/driver loaded
     - Layer 1: Wifi associated
     - Layer 2: IP address assigned
     - Layer 3: Gateway reachable (can we reach the router?)
     - Layer 4: DNS working (can we resolve names to IPs?)
     - Layer 5: internet reachable (can we reach external servers?)
5. Update package lists by executing:

```bash
sudo apt update
sudo apt upgrade -y
```

6. Install vim and git (optional) and pip, picamera2, gpiozero, and the systemd Python bindings with:

```bash
sudo apt install -y vim git python3-pip python3-picamera2 python3-gpiozero python3-systemd
```

- NOTE: `python3-systemd` provides the `sd_notify` bindings the script uses for its systemd watchdog (READY/WATCHDOG handshake). It must be installed before running the script or the service, otherwise the `from systemd import daemon` import will fail.

7. While we've got Wifi working, download the systemd service file into our home directory (~) using wget:

```bash
wget https://raw.githubusercontent.com/iwonder77/rpi-zero-doorbell/refs/heads/main/doorbell.service
```

8. Create a directory for the python script and navigate to it with:

```bash
mkdir doorbell_camera
cd doorbell_camera
```

9. Download the python script into this directory with wget:

```bash
wget https://raw.githubusercontent.com/iwonder77/rpi-zero-doorbell/refs/heads/main/doorbell_camera.py
```

10. Now with the Wifi steps out of the way, configure the camera settings if necessary (manufacturer should provide steps). For the Arducam IMX708 12MP camera and Trixie OS:
    - open the firmware config file in a text editor with superuser privileges: `sudo vim /boot/firmware/config.txt`
    - find the line with `camera_auto_detect=1` and replace it with `camera_auto_detect=0`
    - locate the `[all]` section (should be at the bottom) and add the following line directly underneath it: `dtoverlay=imx708`
    - save file and shutdown Pi with: `sudo shutdown now`

11. While the Pi is OFF, connect the camera and button circuit carefully (refer to schematic)

12. Turn the Pi back ON, and perform the following test steps after logging in:
    - check camera is detected by the Pi: `rpicam-still --list-cameras`
    - check camera shows proper live feed on monitor: `rpicam-still -t 0` (Ctrl+C to exit)
    - check Python script works: `python doorbell_camera/doorbell_camera.py`

13. Before testing the systemd service file, we need to make sure the previously downloaded `doorbell.service` file has the correct paths. Open it up with a text editor and make sure the `ExecStart=` and `WorkingDirectory=` lines have the correct paths (directory and file names) to the python script

14. Once you've verified the `doorbell.service` file works, copy it to the appropriate systemd directory with: `sudo cp doorbell.service /etc/systemd/system`

15. Tell systemd to reread the service files with: `sudo systemctl daemon-reload`

16. Start the doorbell service file now with: `sudo systemctl start doorbell.service`
    - after a couple of seconds, the button + camera should be working automatically without having to run the python script manually!

17. Enable the service file on boot with: `sudo systemctl enable doorbell.service`

18. Reboot the pi with `sudo reboot` and then, **without logging in**, verify autonomous operation by pressing the arcade button and confirm the camera feed appears on the monitor. This behavior proves the exhibit runs hands-free across power cycles, which is exactly how it must behave in the Smarthome exhibit. Now we must disable both the boot up text and the login screen text so that the screen remains completely black when idle, and shows the camera screen when button is pressed.

19. to disable boot up text, login normally and open the firmware cmdline boot file in a text editor with superuser privileges: `sudo vim /boot/firmware/cmdline.txt`
    - find and replace `console=tty1` with `console=tty3`
    - append the following to the end of line 1: `logo.nologo loglevel=3 vt.global_cursor_default=0`
    - **NOTE**: The file must remain ONE LINE ONLY otherwise you'll get some boot issues

20. to disable login screen text info simply run: `sudo systemctl disable getty@tty1.service`
    - **NOTE**: From now on, whenever you boot up the pi the screen should be pitch black, if you ever want to troubleshoot or continue running commands in the Pi's terminal, simply press "Ctrl + Alt + F2" (also try F3/F4/F4/F6) to switch between different virtual consoles. This should land you in a fresh `login:` prompt.

21. **Production Lockdown step** (do this LAST, only after all the previous steps have passed): enable the overlay filesystem to make the OS immune to SD-card corruption from power loss (the #1 cause of dead exhibits after an abrupt shutdown).
    - run `sudo raspi-config`
    - go to _Performance Options_ → _Overlay File System_ and enable it
    - when prompted _"Would you like the boot partition to be write-protected?"_, answer **yes** (the boot partition is never written during normal operation, so locking it closes the last path to SD corruption)
    - reboot when prompted
    - ⚠️ **IMPORTANT:** once the overlay is enabled, the OS root and boot partition are read-only — no changes you make (config edits, script updates, package installs, `apt upgrade`) will survive a reboot. To make future changes you must re-run `sudo raspi-config`, **disable** the Overlay File System (and boot write-protection), reboot, make your changes, then re-enable the overlay and reboot again.

## Making Changes to a Deployed Pi

When a deployed Pi is locked down with the overlay filesystem, you **cannot** just edit the files and reboot - your changes will silently vanish on the next startup. Additionally, changes should be made by pulling from the source of truth, this repo. Never hand-edit the Pi since that can cause sync issues. Here's how to make edits to a deployed Pi:

### 1. Check the lock state

```bash
findmnt -n -o SOURCE /  # "overlay" = locked , "/dev/mmcblk0p2" = unlocked
mount | grep boot       # look for "ro" (locked) or "rw" (unlocked)
```

### 2. Unlock (if locked)

`sudo raspi-config` → _Performance Options_ → _Overlay File System_

- enable overlay? → **No**
- write-protect boot? → **No**

Reboot, then re-run step 1 and confirm you see `/dev/mmcblk0p2` and `rw`. Do not continue until you do.

### 3. Push from your computer

`git push origin main` once your done with the changes to the python script or the service file. The Pi will download from GitHub.

### 4. Stop the service and download the new files

```bash
sudo systemctl stop doorbell.service   # frees the camera for manual testing

cd ~/doorbell_camera
wget -O doorbell_camera.py
https://raw.githubusercontent.com/iwonder77/rpi-zero-doorbell/refs/heads/main/doorbell_camera.py

cd ~
wget -O doorbell.service
https://raw.githubusercontent.com/iwonder77/rpi-zero-doorbell/refs/heads/main/doorbell.service
```

Couple of notes:

- the `-O` flag overwrites the current file
- confirm you got the new version by grepping for something you just added

### 5. Test by hand, then as a service

```bash
python3 ~/doorbell_camera/doorbell_camera.py    # Ctrl+C to quit
```

Then:

```bash
  sudo cp ~/doorbell.service /etc/systemd/system/
  sudo systemctl daemon-reload                              # systemd caches unit
                                                            # files; without this it
                                                            # keeps using the old one
  systemd-analyze verify /etc/systemd/system/doorbell.service   # no output = OK
  sudo systemctl start doorbell.service
  systemctl status doorbell.service                         # want "active (running)"
  journalctl -u doorbell.service -f                         # Ctrl+C stops WATCHING,
                                                            # not the service
```

### 7. Re-lock

`sudo raspi-config` → _Performance Options_ → _Overlay File System_ → **Yes**
to both prompts. Reboot. Confirm `findmnt -n -o SOURCE /` says `overlay`.

Test the button once more in the locked state — that's the configuration that
actually ships.

### Rollback

- **Unlocked:** copy the files back from `~/backup/`, `daemon-reload`, restart.
- **Locked:** pull the power. Everything since the last boot is discarded
  automatically. That's the entire point of the overlay.
