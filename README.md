# Raspberry Pi Zero 2w Doorbell Interactive

## Overview

This repository holds the firmware (python script), systemd service file, and steps for setting up a Raspberry Pi Zero 2w for the Doorbell interactive in the Townhome exhibit of Kidopolis at Thanksgiving Point's Museum of Natural Curiosity.

## Hardware

- Raspberry Pi Zero 2w
- [Arducam IMX708 12MP](https://docs.arducam.com/Raspberry-Pi-Camera/Native-camera/12MP-IMX708/#products-list) camera (SKU: B0312)
- Acer 15.6" Monitor
- Arcade button + ESD protected circuit

## Setup Steps

1. Flash a reliable SD card with Raspberry Pi OS Lite (64-bit) using the [Raspberry Pi Imager](https://www.raspberrypi.com/software/). Ensure the following configuration settings are set:
   - hostname, username, and password (write these down somewhere)
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

6. Install vim and git (optional) and pip, picamera2, and gpiozero with:

```bash
sudo apt install -y vim git python3-pip python3-picamera2 python3-gpiozero
```

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

10. Now with the Wifi steps out of the way, configure the camera if necessary (manufacturer should provide steps). For the Arducam IMX708 12MP camera and Trixie OS:
    - open the firmware config file located in `/boot/firmware/config.txt` in text editor with superuser privileges (sudo)
    - find the line with `camera_auto_detect=1` and replace it with `camera_auto_detect=0`
    - locate the `[all]` section (should be at the bottom) and add the following line directly underneath it: `dtoverlay=imx708`
    - save file and reboot Pi with: `sudo reboot`

11. Connect the camera and test that it is...
    - detected by the Pi: `rpicam-still --list-cameras`
    - capturing proper live feed: `rpicam-still -t 0`

12. Carefully connect the button circuit and test the python script + button interactivity with the simple command: `python doorbell_camera.py`
