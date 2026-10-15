"""Shape of the Cyclone 2 drawing, in logical units inside a WIDTH x HEIGHT box (scaled by the UI factor).

The body silhouette was traced from the controller's outline; parts are placed where the real buttons are.
"""
WIDTH, HEIGHT = 442, 318

# body outline, clockwise from the top-left corner (control points of a smooth polygon)
BODY = [(78, 24), (110, 14), (221, 11), (332, 14), (364, 24), (376, 32), (388, 48), (394, 64), (400, 80), (405, 96),
        (411, 112), (416, 128), (422, 144), (427, 160), (431, 176), (435, 192), (438, 208), (440, 224), (441, 240),
        (440, 256), (434, 272), (425, 280), (416, 286), (400, 292), (384, 286), (368, 270), (352, 254), (336, 237),
        (320, 223), (304, 217), (221, 216), (138, 217), (122, 223), (106, 237), (90, 254), (74, 270), (58, 286),
        (42, 292), (26, 286), (17, 280), (8, 272), (1, 256), (0, 240), (1, 224), (3, 208), (6, 192), (10, 176),
        (14, 160), (19, 144), (25, 128), (30, 112), (36, 96), (42, 80), (48, 64), (54, 48), (66, 32)]

# shoulders: bumpers sit on the top corners, triggers peek out behind them
LB_PTS = ((50, 42), (60, 22), (78, 9), (104, 3), (138, 2), (154, 8), (152, 20), (120, 22), (96, 26), (74, 36),
          (60, 50))
LT_PTS = ((80, 8), (90, -6), (112, -12), (136, -10), (148, -2), (140, 4), (110, 4))


def mirror(pts):
    return tuple((WIDTH - x, y) for x, y in pts)


DPAD_CENTER, DPAD_RING = (163, 157), 37
DPAD_ARM, DPAD_HALF = 30, 11     # d-pad cross: arm length and half width
DPAD_DIRS = {"Up": (0, -1), "Right": (1, 0), "Down": (0, 1), "Left": (-1, 0)}


def _dpad(pts, dx, dy):
    """Rotate points drawn for the Up arm towards (dx, dy) and move them onto the d-pad centre."""
    cx, cy = DPAD_CENTER
    return tuple((cx - y * dx - x * dy, cy + x * dx - y * dy) for x, y in pts)


# one arm, and the whole cross, as smoothed polygons: the doubled inner corners stay sharp, the ends come out round
_A, _H = DPAD_ARM, DPAD_HALF
DPAD_ARMS = {n: _dpad(((-_H, -_H), (-_H, -_H), (-_H, -_A), (_H, -_A), (_H, -_H), (_H, -_H)), *d)
             for n, d in DPAD_DIRS.items()}
DPAD_CROSS = tuple(p for d in DPAD_DIRS.values() for p in _dpad(((-_H, -_A), (_H, -_A), (_H, -_H), (_H, -_H)), *d))

# name -> (shape, coords, label). shape: circle (x, y, r) | rect/rrect (x1, y1, x2, y2) | poly (points, label point)
PARTS = {
    "LT": ("poly", (LT_PTS, (114, -3)), "LT"), "RT": ("poly", (mirror(LT_PTS), (328, -3)), "RT"),
    "LB": ("poly", (LB_PTS, (104, 13)), "LB"), "RB": ("poly", (mirror(LB_PTS), (338, 13)), "RB"),
    "LS": ("circle", (109, 85, 26), ""), "RS": ("circle", (276, 152, 26), ""),
    **{n: ("poly", (DPAD_ARMS[n], (DPAD_CENTER[0] + 20 * d[0], DPAD_CENTER[1] + 20 * d[1])), "")
       for n, d in DPAD_DIRS.items()},
    "Y": ("circle", (331, 58, 14), "Y"), "A": ("circle", (331, 116, 14), "A"),
    "X": ("circle", (302, 87, 14), "X"), "B": ("circle", (360, 87, 14), "B"),
    "View": ("rrect", (154, 41, 168, 57), "−"), "Menu": ("rrect", (274, 41, 288, 57), "+"),
    "Home": ("circle", (221, 45, 14), ""), "Capture": ("rrect", (209, 73, 233, 87), "▢"),
    "M": ("rrect", (209, 180, 233, 192), "M"),
    "L4": ("rrect", (128, 298, 166, 314), "L4"), "R4": ("rrect", (276, 298, 314, 314), "R4"),
}
BEHIND = ("LT", "RT")            # parts drawn behind the body
# button roles pick the skin colours (theme.SKINS); everything else uses "btn"
ROLES = {**dict.fromkeys(("A", "B", "X", "Y"), "face"), **dict.fromkeys(("Up", "Down", "Left", "Right"), "dpad"),
         **dict.fromkeys(("LS", "RS"), "stick"), **dict.fromkeys(("LB", "RB"), "shoulder"),
         **dict.fromkeys(("LT", "RT"), "trigger"), "Home": "home"}

STICK_WELLS = {"LS": (109, 85, 33), "RS": (276, 152, 33)}
PLAYER_LEDS = [(221, 114 + 11 * i) for i in range(4)]    # profile indicator dashes, profile 1 at the top
PLAYER_COLORS = ("#7ed321", "#f8e71c", "#f5a623", "#e0262b")

# LED zones: grip light bars are polylines, the rings are arcs around the sticks and Home
GRIP_LEFT = ((44, 122), (37, 145), (44, 172), (70, 190), (96, 202))
ZONE_SHAPES = {"lower_left": ("bar", GRIP_LEFT), "lower_right": ("bar", mirror(GRIP_LEFT)),
               "upper_left": ("ring", (109, 85, 31)), "upper_right": ("ring", (276, 152, 31)),
               "home": ("ring", (221, 45, 17))}

# home-page callouts: label, side, label y, target point on the controller, button (or section) opened on click
CALLOUTS = [("LT / LB", "l", 4, (96, 12), "LB"), ("Analógico esquerdo", "l", 84, (80, 85), "sticks"),
            ("D-pad", "l", 160, (130, 157), "Up"), ("Luzes", "l", 236, (44, 172), "leds"),
            ("RT / RB", "r", 4, (346, 12), "RB"), ("Botões ABXY", "r", 84, (374, 87), "A"),
            ("Analógico direito", "r", 160, (303, 152), "sticks"), ("Traseiros L4 / R4", "r", 300, (314, 306), "R4")]
HOME_OFFSET = 170                # room for the callouts left of the drawing
TOP = 16                         # room above the body for the triggers
