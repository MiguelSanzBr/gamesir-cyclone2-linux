"""The 680-byte profile record: decode to a JSON-friendly dict and encode it back.

Layout (GameSir Connect ``$a.fromBytes``/``fromModel``)::

    0    name, 32 bytes UTF-8
    32   function data, 32 bytes: motors, audio, extend (shift, d-pad lock, ABXY swaps, report rate)
    64   16 buttons x 7 bytes: turbo_en, turbo_speed, map_en, map1, map2, map3, toggle_en
    176  L4, R4 x 159 bytes: the 7 button bytes + a macro (status, cycle time, step count, 30 steps)
    494  LT, RT x 28 bytes: turbo, dead zone, mapping, toggle, hair trigger, response curve
    550  left, right stick x 32 bytes: enable, square, dead zone, curve, output mapping
    614  aim, tilt (gyro) x 33 bytes: activation, trigger key, axes, dead zone, curve, output mapping

Every field is described once in :data:`FIELDS` as ``(path, offset, kind)``. :func:`encode` only writes the
fields whose value differs from the base record, so unknown and reserved bytes are kept as they are.
"""
import copy

from . import keys
from .protocol import PROFILE_SIZE

STEPS = 30


def _deadzone(p, o):
    return [(p + ("deadzone_on",), o, "bool"), (p + ("deadzone",), o + 1, "u8x4")]


def _curve(p, o):
    return [(p + ("curve",), o, "curve")]


def _output(p, o):
    """Output mapping of a stick/gyro: target (1 left stick, 2 right stick, 3 wheel, 4 mouse) and options."""
    names = ("on", "invert_x", "invert_y", "axis_ratio", "mouse_dpi", "target", "cross")
    out = [(p + ("output", n), o + i, "bool" if i < 3 else "u8") for i, n in enumerate(names)]
    return out + [(p + ("output", "wheel"), o + 7, "wheel")]


def _button(p, o):
    return [(p + ("turbo",), o, "bool"), (p + ("turbo_speed",), o + 1, "u8"), (p + ("map",), o + 2, "keys"),
            (p + ("toggle",), o + 6, "bool")]


def _fields():
    f = [(("name",), 0, "name")]
    for i, n in enumerate(("left", "right", "lt", "rt")):
        f.append((("motors", n), 32 + i, "u8"))
    for i, n in enumerate(("enabled", "volume", "mixer", "mic_mute", "mic_sensitivity")):
        f.append((("audio", n), 36 + i, "u8"))
    for i, n in enumerate(("shift", "shift_key", "dpad_diagonal_lock", "xinput_abxy_swap", "switch_abxy_swap",
                           "report_rate")):
        f.append((("options", n), 41 + i, "bool" if n not in ("shift_key", "report_rate") else "u8"))
    for i, b in enumerate(keys.BUTTONS):
        f += _button(("buttons", b), 64 + 7 * i)
    for i, b in enumerate(keys.PADDLES):
        o = 176 + 159 * i
        f += _button(("buttons", b), o) + [(("macros", b), o + 7, "macro")]
    for i, b in enumerate(keys.TRIGGERS):
        o, p = 494 + 28 * i, ("triggers", b)
        f += [(("buttons", b, "turbo"), o, "bool"), (("buttons", b, "turbo_speed"), o + 1, "u8")]
        f += _deadzone(p, o + 2)
        f += [(("buttons", b, "map"), o + 7, "keys"), (("buttons", b, "toggle"), o + 11, "bool"),
              (p + ("hair_trigger",), o + 12, "hair")]
        f += _curve(p, o + 15)
    for i, s in enumerate(("left", "right")):
        o, p = 550 + 32 * i, ("sticks", s)
        f += [(p + ("on",), o, "bool"), (p + ("square",), o + 1, "bool")]
        f += _deadzone(p, o + 2) + _curve(p, o + 7) + _output(p, o + 20)
    for i, s in enumerate(("aim", "tilt")):
        o, p = 614 + 33 * i, ("motion", s)
        f += [(p + ("activation",), o, "u8"), (p + ("trigger_key",), o + 1, "key"), (p + ("axes",), o + 2, "u8")]
        f += _deadzone(p, o + 3) + _curve(p, o + 8) + _output(p, o + 21)
    return f


FIELDS = _fields()
# bytes used by each kind
SIZE = {"u8": 1, "bool": 1, "key": 1, "keys": 4, "u8x4": 4, "hair": 3, "curve": 13, "wheel": 5, "name": 32,
        "macro": 152}
WHEEL = ("up", "down", "left", "right", "center")


def _get(buf, o, kind):
    b = buf[o:o + SIZE[kind]]
    if kind == "u8":
        return b[0]
    if kind == "bool":
        return bool(b[0] & 1)
    if kind == "key":
        return keys.name(b[0])
    if kind == "keys":                         # map_en + 3 codes; [] = the button keeps its own function
        return [keys.name(c) for c in b[1:] if c] if b[0] & 1 else []
    if kind == "u8x4":
        return list(b)
    if kind == "hair":                         # status bit 7 = on, bit 0/1 = mode 1/2
        return {"on": bool(b[0] & 0x80), "mode": 2 if b[0] & 2 else 1, "start": b[1], "end": b[2]}
    if kind == "curve":
        return {"on": bool(b[0] & 1), "type": b[1], "curvature": b[2], "points": [list(b[3 + 2 * i:5 + 2 * i]) for i in range(5)]}
    if kind == "wheel":
        return {d: keys.name(c) if c else "" for d, c in zip(WHEEL, b)}
    if kind == "name":
        return b.split(b"\0")[0].decode("utf-8", "replace").strip()
    st = b[0]                                  # macro
    n = min(b[3], STEPS)
    steps = []
    for i in range(n):
        s = b[4 + 5 * i:9 + 5 * i]
        steps.append({"key": keys.name(s[0]), "hold": s[1] << 8 | s[2], "delay": s[3] << 8 | s[4] if i < STEPS - 1 else 0})
    return {"on": bool(st & 1), "press_to_trigger": bool(st & 2), "cycle": bool(st & 4),
            "cycle_time": b[1] << 8 | b[2], "steps": steps}


def _put(buf, o, kind, v):
    if kind == "u8":
        b = [v]
    elif kind == "bool":
        b = [int(bool(v))]
    elif kind == "key":
        b = [keys.code(v)]
    elif kind == "keys":
        if len(v) > 3:
            raise ValueError("at most 3 keys per button")
        codes = [keys.code(k) for k in v]
        b = [1 if v else 0] + codes + [0] * (3 - len(codes))
    elif kind == "u8x4":
        b = list(v)
    elif kind == "hair":
        b = [(0x80 | (2 if v["mode"] == 2 else 1)) if v["on"] else 0, v["start"], v["end"]]
    elif kind == "curve":
        b = [int(bool(v["on"])), v["type"], v["curvature"]] + [x for pt in v["points"] for x in pt]
    elif kind == "wheel":
        b = [keys.code(v[d]) if v[d] else 0 for d in WHEEL]
    elif kind == "name":
        raw = v.encode("utf-8")[:31].decode("utf-8", "ignore").encode()   # cut on a whole character
        b = list(raw.ljust(32, b"\0"))
    else:                                      # macro
        steps = v["steps"]
        if len(steps) > STEPS:
            raise ValueError(f"at most {STEPS} macro steps")
        b = [(1 if v["on"] and steps else 0) | (2 if v["press_to_trigger"] else 0) | (4 if v["cycle"] else 0),
             v["cycle_time"] >> 8, v["cycle_time"] & 0xFF, len(steps)]
        for i in range(STEPS):
            s = steps[i] if i < len(steps) else {"key": None, "hold": 0, "delay": 0}
            b += [keys.code(s["key"]) if s["key"] else 0, s["hold"] >> 8, s["hold"] & 0xFF]
            if i < STEPS - 1:
                b += [s["delay"] >> 8, s["delay"] & 0xFF]
    if len(b) != SIZE[kind] or not all(0 <= x <= 255 for x in b):
        raise ValueError(f"bad value {v!r} at offset {o}")
    buf[o:o + len(b)] = bytes(b)


def _lookup(doc, path):
    for k in path:
        doc = doc[k]
    return doc


def decode(data):
    """Profile bytes -> nested dict (see :data:`FIELDS` for the paths)."""
    if len(data) != PROFILE_SIZE:
        raise ValueError(f"a profile has {PROFILE_SIZE} bytes, got {len(data)}")
    doc = {}
    for path, o, kind in FIELDS:
        node = doc
        for k in path[:-1]:
            node = node.setdefault(k, {})
        node[path[-1]] = _get(data, o, kind)
    return doc


def encode(doc, base):
    """Dict -> profile bytes, starting from ``base``; only fields that differ from ``base`` are written."""
    old = decode(base)
    buf = bytearray(base)
    for path, o, kind in FIELDS:
        try:
            v = _lookup(doc, path)
        except (KeyError, TypeError):
            continue                           # missing in a partial document: keep the base value
        if v != _lookup(old, path):
            _put(buf, o, kind, v)
    return bytes(buf)


def changed_span(a, b):
    """``(start, end)`` of the bytes that differ between two records, or ``None`` (the app's ``bytesDiff``)."""
    diff = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
    return (diff[0], diff[-1] + 1) if diff else None


def _round(x):
    return int(x + 0.5)                        # JavaScript Math.round for the non-negative values used here


def curve(deadzone, points=((25, 25), (50, 50), (75, 75)), type=0, curvature=100):
    """Curve record the app writes for three control points given in % (``m()`` in the app): x is scaled
    into the dead zone range, y into the anti-dead-zone range, both to 0-255; the ends are fixed."""
    b, e, ab, ae = deadzone
    scale = lambda v, lo, hi: _round((v - lo) / max(hi - lo, 1) * 255)
    pts = [[0, 0]] + [[scale(x, b, e), scale(y, ab, ae)] for x, y in points] + [[255, 255]]
    return {"on": True, "type": type, "curvature": curvature, "points": pts}


def curve_percent(c, deadzone):
    """The three control points of a stored curve back in % (the app's ``l()``/``c()``), so the curve can be
    rebuilt with :func:`curve` when the dead zone changes."""
    b, e, ab, ae = deadzone
    back = lambda v, lo, hi: _round(v / 255 * (hi - lo) + lo)
    return [(back(x, b, e), back(y, ab, ae)) for x, y in c["points"][1:4]]


def reset(doc, part=None):
    """App defaults for a section (``"mapping"``, ``"sticks"``, ``"triggers"``, ``"motion"``, ``"motors"``)
    or for all of them (``part=None``), like the app's "reset" buttons. Returns a new dict."""
    doc = copy.deepcopy(doc)
    output = lambda target: {"on": True, "invert_x": False, "invert_y": False, "axis_ratio": 50, "mouse_dpi": 50,
                             "target": target, "cross": 0, "wheel": dict.fromkeys(WHEEL, "")}
    if part in (None, "mapping"):
        for b in doc["buttons"].values():
            b.update(map=[], turbo=False, turbo_speed=0, toggle=False)
        for m in doc["macros"].values():
            m.update(on=False, press_to_trigger=False, cycle=False, cycle_time=0, steps=[])
    if part in (None, "sticks"):
        for i, s in enumerate(doc["sticks"].values()):
            s.update(on=True, square=False, deadzone_on=True, deadzone=[10, 100, 0, 100],
                     curve=curve([10, 100, 0, 100]), output=output(i + 1))
    if part in (None, "motion"):
        for i, s in enumerate(doc["motion"].values()):
            s.update(activation=0, trigger_key="None", axes=2, deadzone_on=True, deadzone=[10, 100, 0, 100],
                     curve=curve([10, 100, 0, 100]), output=output(i + 1))
    if part in (None, "triggers"):
        for t in doc["triggers"].values():
            t.update(deadzone_on=True, deadzone=[5, 95, 0, 100], curve=curve([5, 95, 0, 100]))
            t["hair_trigger"].update(on=False, mode=1)      # the app leaves the range bytes as they are
    if part in (None, "motors"):
        doc["motors"] = dict.fromkeys(("left", "right", "lt", "rt"), 75)
    return doc
