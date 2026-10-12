"""The 635-byte lighting record (profile number 32, shared by all profiles) and the app's effect presets.

Layout (GameSir Connect ``qo.fromBytes``/``fromModel``)::

    0    active animation (0-3)
    1    5 animations x 124 bytes: frame count, effect count, speed (stored as 20 - speed), brightness,
         8 frames x 5 LEDs x RGB
    621  audio reactive, user effect, profile LED RGB, raise to wake, standby minutes, 7 reserved bytes

The five LEDs of a frame are stored in the order :data:`LEDS`.
"""
import copy

from .protocol import LIGHT_SIZE

LEDS = ("lower_left", "lower_right", "upper_left", "home", "upper_right")
ANIMATIONS, FRAMES, MAX_SPEED = 5, 8, 20
STANDBY = (0, 1, 5, 10, 20)      # minutes the app offers for "auto sleep" (0 = never)


def _hex(b):
    return "#" + bytes(b).hex()


def _rgb(c):
    return bytes.fromhex(c[1:7])


def decode(data):
    if len(data) != LIGHT_SIZE:
        raise ValueError(f"the lighting record has {LIGHT_SIZE} bytes, got {len(data)}")
    anims = []
    for a in range(ANIMATIONS):
        b = data[1 + 124 * a:125 + 124 * a]
        frames = [{led: _hex(b[4 + 15 * f + 3 * i:7 + 15 * f + 3 * i]) for i, led in enumerate(LEDS)} for f in range(FRAMES)]
        anims.append({"frames": b[0], "effects": b[1], "speed": max(0, MAX_SPEED - b[2]), "brightness": min(b[3], 100),
                      "colors": frames})
    t = data[621:]
    return {"active": data[0] if data[0] <= 3 else 0, "animations": anims, "audio_reactive": bool(t[0] & 1),
            "user_effect": t[1], "profile_led": _hex(t[2:5]), "raise_to_wake": bool(t[5] & 1), "standby": t[6]}


def encode(doc, base):
    """Dict -> lighting bytes; bytes the dict does not describe (reserved tail) come from ``base``."""
    buf = bytearray(base)
    buf[0] = doc["active"]
    for a, an in enumerate(doc["animations"]):
        o = 1 + 124 * a
        speed = min(max(an["speed"], 0), MAX_SPEED)
        buf[o:o + 4] = bytes([an["frames"], an["effects"], MAX_SPEED - speed, an["brightness"]])
        for f, frame in enumerate(an["colors"]):
            for i, led in enumerate(LEDS):
                p = o + 4 + 15 * f + 3 * i
                buf[p:p + 3] = _rgb(frame[led])
    buf[621:628] = bytes([int(doc["audio_reactive"]), doc["user_effect"], *_rgb(doc["profile_led"]),
                          int(doc["raise_to_wake"]), doc["standby"]])
    return bytes(buf)


# effect presets of the app (``Name``, ``Speed``, frames as Home, UpperLeft, LowerLeft, LowerRight, UpperRight)
_P = [("Flow", 17, ["FF0000 0000FF 00FF00 FFFF00 FF0000", "FF8000 FF0000 0000FF 00FF80 FFFF00",
                    "FFFF00 FF80FF 800080 0000FF 00FF00", "14FF01 808000 FF0000 FF0000 0000FF",
                    "000FFF 008000 FF0000 808000 FF0080"]),
      ("Rainbow", 10, [" ".join([c] * 5) for c in ("FF0000", "FFA500", "FFFF00", "00FF00", "00FFFF", "0000FF",
                                                    "FF00FF", "FF0000")]),
      ("Pulse", 5, ["FF00C8 FF0000 8000FF 8000FF FF0000", "0080FF 000000 0080FF 0080FF 000000"]),
      ("Standoff", 10, ["FFFFFF 00B3FF 0040FF FF0500 FF0500"]),
      ("Alarm", 18, ["FF0000 " * 4 + "FF0000", "000000 " * 4 + "000000"] * 2 + ["000000 " * 4 + "000000"] * 2),
      ("Disable", 10, ["000000 " * 4 + "000000"])]
PRESET_ORDER = ("home", "upper_left", "lower_left", "lower_right", "upper_right")


PRESETS = {name: {"speed": speed, "colors": [dict(zip(PRESET_ORDER, ("#" + c.lower() for c in f.split()))) for f in frames]}
           for name, speed, frames in _P}
BLACK = dict.fromkeys(LEDS, "#000000")


def apply_preset(doc, name, animation=None):
    """Load an app preset into an animation (default: the active one), like the app's preset buttons."""
    doc = copy.deepcopy(doc)
    p = PRESETS[name]
    an = doc["animations"][doc["active"] if animation is None else animation]
    an["speed"], an["frames"] = p["speed"], len(p["colors"])
    an["colors"] = [dict(p["colors"][f]) if f < len(p["colors"]) else dict(BLACK) for f in range(FRAMES)]
    return doc


def solid(doc, color, animation=None):
    """One static colour on every LED of an animation."""
    doc = copy.deepcopy(doc)
    an = doc["animations"][doc["active"] if animation is None else animation]
    an["frames"] = 1
    an["colors"] = [dict.fromkeys(LEDS, color)] + [dict(BLACK) for _ in range(FRAMES - 1)]
    return doc
