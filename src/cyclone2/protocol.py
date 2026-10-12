"""Constants and frame format of the GameSir Cyclone 2 config channel (pure functions, no I/O).

Recovered from GameSir Connect 1.14.5 (``proxyC2`` and its command builder). The channel is the vendor
HID interface with usage page 0xFFF0:

* host -> controller: output report ``0x0F``, 64 bytes ``0F cmd args...``
* controller -> host: input report ``0x10`` with the answer, ``10 cmd ...``
* input report ``0x12`` streams the gamepad state (buttons, sticks, battery, current LED colours)

Profile data travels as ``0F 03|04 profile offset_hi offset_lo length data...`` (at most 58 data bytes).
"""

VID = 0x3537
# USB product ids of the config-capable modes (GameSir Connect ``Modes[].ConfigModePid``)
PIDS = {0x101D: "Cyclone 2 (cabo)", 0x102A: "Cyclone 2 (2.4G)", 0x1053: "Cyclone 2 (cabo, ADC)",
        0x100B: "Cyclone 2 (2.4G, dongle)"}
USAGE_PAGE = b"\x06\xf0\xff"     # report descriptor item "Usage Page (0xFFF0)"

REPORT_SIZE = 64
OUT, ANSWER, STATE = 0x0F, 0x10, 0x12   # report ids

# commands (byte 1 of a report)
WRITE, READ, READ_ACK, ACK, SWITCH = 3, 4, 5, 6, 7
FIRMWARE, FIRMWARE_ACK, CURRENT, CURRENT_ACK = 9, 10, 11, 12
LIGHT, LIGHT_ACK, CHANGED = 13, 14, 15
VIBRATE, HEARTBEAT = 32, 242

# profile numbers: 1-4 are the user profiles, 5 the Shift layer, 32 the (global) lighting record
PROFILES = (1, 2, 3, 4)
SHIFT, LIGHTS = 5, 32
CURRENT_NUMBER = 48              # profile number in a CHANGED notice when the active profile changed
PROFILE_SIZE, LIGHT_SIZE = 680, 635
CHUNK = 58                       # data bytes per write/read packet


def size_of(profile):
    return LIGHT_SIZE if profile == LIGHTS else PROFILE_SIZE


def command(cmd, *args):
    """A 64-byte output report ``0F cmd args...`` (zero padded)."""
    return bytes([OUT, cmd, *args]).ljust(REPORT_SIZE, b"\0")


def read_requests(profile, start=0, end=None):
    """Read commands covering bytes ``start:end`` of a profile (the app reads in 58-byte packets)."""
    end = size_of(profile) if end is None else end
    return [command(READ, profile, off >> 8, off & 0xFF, min(CHUNK, end - off)) for off in range(start, end, CHUNK)]


def write_requests(profile, data, offset=0):
    """Write commands that store ``data`` at ``offset`` of a profile."""
    return [command(WRITE, profile, (offset + i) >> 8, (offset + i) & 0xFF, len(data[i:i + CHUNK]), *data[i:i + CHUNK])
            for i in range(0, len(data), CHUNK)]


def kind(report):
    """Command byte of an answer report, or ``None`` for anything else (gamepad state, other report ids)."""
    return report[1] if len(report) > 1 and report[0] == ANSWER else None


def busy(report):
    """An ``ACK`` with byte 2 = 1 means "busy, send again" (``AckWithBusy``)."""
    return kind(report) == ACK and report[2] == 1


def chunk(report):
    """``(profile, offset, data)`` of a ``READ_ACK`` report."""
    n = report[5]
    return report[2], report[3] << 8 | report[4], bytes(report[6:6 + n])


def version(raw):
    """Firmware version string the way the app shows it: NULs and spaces dropped, digits joined by dots
    (``b"3\\x005\\x006"`` -> ``"3.5.6"``)."""
    return ".".join(c for c in raw.decode("utf-8", "replace") if not c.isspace() and c != "\0")


def firmware(report):
    """``(controller, dongle)`` versions from a ``FIRMWARE_ACK`` report."""
    return version(bytes(report[4:9])), version(bytes(report[12:17]))


# gamepad state report (``0x12``). Bytes 1-9 are the processed output (after remaps, ABXY swap, hair trigger);
# bytes 53-62 repeat that block with the physical input and analog triggers, which is what is decoded here
# (the app reads L4/R4/M from it too). Offsets below are relative to byte 53.
RAW = 53
STATE_BITS = {5: {4: "X", 5: "A", 6: "B", 7: "Y"},
              6: {0: "LB", 1: "RB", 2: "LT", 3: "RT", 4: "View", 5: "Menu", 6: "LS", 7: "RS"},
              7: {0: "Home", 1: "Capture", 3: "L4", 4: "R4", 5: "M"}}
HAT = {0: ("Up",), 1: ("Up", "Right"), 2: ("Right",), 3: ("Down", "Right"), 4: ("Down",), 5: ("Down", "Left"),
       6: ("Left",), 7: ("Up", "Left")}


def state(report):
    """Decode a ``0x12`` report: physically pressed buttons, sticks (-1..1, y down), triggers (0-255), battery."""
    if len(report) < REPORT_SIZE or report[0] != STATE:
        return None
    r = report[RAW:RAW + 10]
    axis = lambda v: (v - 128) / (127 if v >= 128 else 128)
    pressed = {n for byte, bits in STATE_BITS.items() for bit, n in bits.items() if r[byte] >> bit & 1}
    pressed.update(HAT.get(r[5] & 0x0F, ()))
    return {"pressed": pressed, "left": (axis(r[1]), axis(r[2])), "right": (axis(r[3]), axis(r[4])),
            "lt": r[8], "rt": r[9], "charging": report[35], "battery": report[36], "animation": report[37]}
