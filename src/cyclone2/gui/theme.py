"""Colours, fonts, timings and controller skins of the interface.

Values other modules read at call time (``FAMILY``, ``AUTOSAVE_MS``, ``POLL_MS``, ``FRAME_MS``) are always
accessed as ``theme.NAME`` so they can be changed in one place (and patched in tests).
"""
import tkinter.font as tkfont

# palette (same look as the 8BitDo Ultimate 2 configurator)
BG, TILE, TILE_HI, LINE, FG, MUTED, ACCENT, DANGER, WARN = (
    "#1b1b1b", "#262626", "#313131", "#3c3c3c", "#ececec", "#8c8c8c", "#4cd964", "#ff6b6b", "#ffcc66")
BODY_FILL, SEL_FILL = "#222222", "#1d3524"
CALLOUT_FILL, CALLOUT_LINE, CALLOUT_DOT = "#2a1717", "#d6453c", "#f08a80"
GLOW = "#7a1f1a"                 # floor glow under the home drawing

# timings (ms) and the ripple duration (s)
AUTOSAVE_MS, POLL_MS, FRAME_MS, HEARTBEAT_MS = 400, 2500, 33, 1000
PULSE = 0.35

FAMILY = "Sans"          # replaced at startup by pick_family()
PREFERRED_FAMILIES = ("Inter", "Cantarell", "Noto Sans", "DejaVu Sans")


def pick_family(root):
    """Nicest installed UI font (fallback: Tk's generic "Sans")."""
    return next((f for f in PREFERRED_FAMILIES if f in tkfont.families(root)), "Sans")


def font(size, weight="normal"):
    return (FAMILY, size, weight)


# controller skins: body gradient (top, middle, bottom), outline, plate lines, (fill, outline, label) per part
# role, and which LED zones the edition has (the black one only lights the grip bars)
SKINS = {
    "black": dict(name="Preto", body=("#3b3b3e", "#2e2e31", "#222224"), line="#5a5a5e", plate="#47474b",
                  well="#1a1a1c", btn=("#2a2a2d", "#6a6a70", FG), face=("#1f1f22", "#55555c", FG),
                  dpad=("#3a3a3e", "#5d5d63", FG), stick=("#1d1d20", "#48484e", FG),
                  shoulder=("#4a4d51", "#6b6f74", FG), trigger=("#3c3e42", "#5b5e63", FG),
                  home=("#5b5f66", "#e0262b", FG), zones=("lower_left", "lower_right"), led_off="#2a2a2d"),
    "white": dict(name="Branco", body=("#fbfbfb", "#efefef", "#dcdcdc"), line="#b9b9b9", plate="#dedede",
                  well="#e4e4e4", btn=("#d9d9d9", "#9a9a9a", "#555555"), face=("#cfcfcf", "#9a9a9a", "#666666"),
                  dpad=("#cdb67f", "#a8915c", FG), stick=("#cbcbcb", "#9c9c9c", FG),
                  shoulder=("#cdb67f", "#a8915c", "#3b3220"), trigger=("#9a9da2", "#7a7d82", FG),
                  home=("#6d7178", "#e0262b", FG),
                  zones=("lower_left", "lower_right", "upper_left", "upper_right", "home"), led_off="#d0d0d0"),
    "pink": dict(name="Rosa", body=("#fde3ea", "#f6c6d4", "#e9a8bc"), line="#c98aa0", plate="#f2bccc",
                 well="#f8d6e0", btn=("#fbd5e0", "#c98aa0", "#7a3950"), face=("#fff0f4", "#d79bb0", "#b23a62"),
                 dpad=("#fff0f4", "#d79bb0", "#7a3950"), stick=("#f3c1cf", "#c98aa0", FG),
                 shoulder=("#fbd5e0", "#c98aa0", "#7a3950"), trigger=("#e9a8bc", "#c98aa0", FG),
                 home=("#6d7178", "#e0262b", FG),
                 zones=("lower_left", "lower_right", "upper_left", "upper_right", "home"), led_off="#e7b4c3"),
}
DEFAULT_SKIN = "black"
