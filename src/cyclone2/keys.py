"""Key codes the firmware uses for remapping, macros and gyro activation (GameSir Connect ``keysDefine``).

Names follow the labels printed on the Cyclone 2 (Xbox layout). The app's own names, where different:
CRO=A, CIR=B, SQU=X, TRI=Y, L1=LB, L2=LT, L3=LS, R1=RB, R2=RT, R3=RS, PS=Home, Sel=View, Sta=Menu,
Camera=Capture, FL1=L4, FR1=R4, Under=Down.
"""

PAD = {1: "Up", 2: "Down", 3: "Left", 4: "Right", 5: "LB", 6: "RB", 7: "LS", 8: "RS", 9: "A", 10: "B", 11: "X",
       12: "Y", 13: "Home", 14: "View", 15: "Menu", 16: "Capture", 17: "L4", 18: "R4", 19: "LT", 20: "RT",
       21: "LS_Up", 22: "LS_Down", 23: "LS_Left", 24: "LS_Right",
       25: "RS_Up", 26: "RS_Down", 27: "RS_Left", 28: "RS_Right"}
KEYBOARD = dict(enumerate(
    ["ESC", "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12", "`", "1", "2", "3", "4", "5",
     "6", "7", "8", "9", "0", "-", "=", "BACKSPACE", "TAB", "Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "[", "]",
     "\\", "CAPSLOCK", "A", "S", "D", "F", "G", "H", "J", "K", "L", ";", "'", "ENTER", "LSHIFT", "Z", "X", "C", "V",
     "B", "N", "M", ",", ".", "/", "RSHIFT", "LCTRL", "WIN", "LALT", "SPACE", "RALT", "RCTRL", "INSERT", "HOME",
     "PGUP", "DELETE", "END", "PGDN", "UP", "DOWN", "LEFT", "RIGHT", "NUMLOCK", "NUM/", "NUM*", "NUM-", "NUM+",
     "NUM.", "NUMENTER", "NUM0", "NUM1", "NUM2", "NUM3", "NUM4", "NUM5", "NUM6", "NUM7", "NUM8", "NUM9", "PLAY",
     "STOP", "NEXT", "PREV", "VOLUP", "VOLDOWN"], start=50))
MOUSE = {200: "MOUSE_LEFT", 201: "MOUSE_MIDDLE", 202: "MOUSE_RIGHT", 203: "MOUSE_5", 204: "MOUSE_4",
         205: "WHEEL_UP", 206: "WHEEL_DOWN"}
SPECIAL = {230: "Mute", 231: "Shift", 255: "None"}

CODES = {**PAD, **{c: "KB_" + n for c, n in KEYBOARD.items()}, **MOUSE, **SPECIAL}
NAMES = {n: c for c, n in CODES.items()}
NONE = 255

# buttons stored in a profile, in record order (the app's ``ja`` list), then the back paddles and triggers
BUTTONS = ["Up", "Down", "Left", "Right", "LB", "RB", "LS", "RS", "A", "B", "X", "Y", "Home", "View", "Menu", "Capture"]
PADDLES = ["L4", "R4"]
TRIGGERS = ["LT", "RT"]
# what a button can be remapped to in the app (``MappingList``), plus "Home" (the Xbox/Guide button, which Steam
# reads as the Steam button)
TARGETS = ["A", "B", "X", "Y", "Up", "Down", "Left", "Right", "LB", "RB", "LT", "RT", "LS", "RS", "View", "Menu",
           "Capture", "Home", "Mute", "Shift", "None"]


def name(code):
    """Name of a key code; unknown codes become ``"0x.."`` so they survive a decode/encode round trip."""
    return CODES.get(code, f"0x{code:02x}")


def code(n):
    if n in NAMES:
        return NAMES[n]
    if isinstance(n, str) and n.startswith("0x"):
        return int(n, 16)
    raise ValueError(f"unknown key {n!r}")
