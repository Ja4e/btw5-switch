#!/usr/bin/env python3

# Simple tool to switch the Creative BT-W5 Bluetooth Audio dongle between AptX Adaptive **Low Latency** or **High Quality** mode.
# Of course, only works with Bluetooth headphones that support AptX Adaptive, such as the Tranya X3
# Reverse engineered based on communication between Creative's desktop app for Windows and the BT-W5
# Might also set other settings as a whole config data array is sent without taking account the existing config.
#
# Usage: sudo ./btw5-switch.py ll  (for low-latency mode)
#        sudo ./btw5-switch.py hq  (for high-quality mode)
#
# requires either sudo or adjusting the permissions on the /dev/bus/usb/... device

import sys
import usb.core
import usb.util
import os
import itertools
import argparse

# Ensure the script is run with root permissions
if os.geteuid() != 0:
    sys.exit("This script must be run as root. Try using 'sudo'.")

# Define argument parser
parser = argparse.ArgumentParser(description='Switch the Creative BT-W5 Bluetooth dongle between AptX Adaptive Low Latency and High Quality modes.')
parser.add_argument('mode', choices=['hq', 'll'], help="Select 'hq' for High Quality mode or 'll' for Low Latency mode")
args = parser.parse_args()

# Find the BT-W5 device
dev = usb.core.find(idVendor=0x041e, idProduct=0x3130)
if dev is None:
    sys.exit("BT-W5 device not found. Check if it is connected or permissions on /dev/bus/usb/...")

# Obtain the first configuration and interface
try:
    cfg = dev.get_active_configuration()
    intf = cfg[(0, 0)]
    ep = intf[0]
    i = intf.bInterfaceNumber
except Exception as e:
    sys.exit(f"Failed to retrieve the device configuration: {e}")

# Detach kernel driver if necessary
reattach = False
if dev.is_kernel_driver_active(i):
    try:
        dev.detach_kernel_driver(i)
        reattach = True
    except usb.core.USBError as e:
        sys.exit(f"Could not detach kernel driver: {e}")

# Data arrays for HQ and LL modes
data_hq = [0x03, 0x5a, 0x6b, 0x03, 0x0a, 0x03, 0x40]  # High Quality
data_ll = [0x03, 0x5a, 0x6b, 0x03, 0x0a, 0x03, 0x20]  # Low Latency

# Select the data based on input
if args.mode == "hq":
    data = data_hq
    print("Switching to AptX Adaptive High Quality mode...")
else:
    data = data_ll
    print("Switching to AptX Adaptive Low Latency mode...")

# Pad data to 65 bytes
data = list(itertools.chain(data, [0x00] * (65 - len(data))))

# Send control transfer to the device
try:
    result = dev.ctrl_transfer(0x21, 0x09, wValue=0x203, wIndex=0x00, data_or_wLength=data)
    if result != len(data):
        raise usb.core.USBError("Incomplete control transfer.")
    print("Mode switch successful.")
except usb.core.USBError as e:
    sys.exit(f"Failed to send control transfer: {e}")

# Reattach the kernel driver if it was detached
if reattach:
    try:
        dev.attach_kernel_driver(i)
    except usb.core.USBError as e:
        sys.exit(f"Could not reattach kernel driver: {e}")

# Clean up and release the device
usb.util.dispose_resources(dev)
