"""Find the Cyclone 2's vendor config ``hidraw`` node in sysfs."""
import glob
import os

from . import protocol

SYS, DEV = "/sys", "/dev"   # roots, overridable by tests


def _read(path):
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError:
        return b""


def find_devices():
    """Yield ``(hidraw_path, pid)`` for every GameSir interface whose report descriptor has usage page 0xFFF0."""
    for d in sorted(glob.glob(SYS + "/class/hidraw/hidraw*")):
        ue = _read(d + "/device/uevent").decode(errors="replace")
        hid_id = next((l.split("=")[1] for l in ue.splitlines() if l.startswith("HID_ID=")), "")
        try:
            _, vid, pid = (int(x, 16) for x in hid_id.split(":"))
        except ValueError:
            continue
        if vid == protocol.VID and protocol.USAGE_PAGE in _read(d + "/device/report_descriptor"):
            yield DEV + "/" + os.path.basename(d), pid
