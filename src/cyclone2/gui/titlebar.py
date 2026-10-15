"""Ask the window manager for a dark title bar, so the native one (move, resize, maximise, snap...) matches the UI.

KWin (KDE Plasma) reads ``_KDE_NET_WM_COLOR_SCHEME`` and GTK-based managers (GNOME) ``_GTK_THEME_VARIANT``; both are
plain X11 properties of the top-level window, set here through libX11 so no extra tool is needed. Managers that ignore
them keep their own colours.
"""
import ctypes

from .x11 import library

PROPERTIES = {b"_GTK_THEME_VARIANT": b"dark", b"_KDE_NET_WM_COLOR_SCHEME": b"BreezeDark"}
XA_STRING = 31


def dark_titlebar(window):
    """Set the properties on the window Tk hands to the window manager; ``False`` if X11 is not available."""
    lib = library()
    return bool(lib) and _set(lib, window.winfo_screen().encode(), window.winfo_id())


def dark_on_show(window):
    """Ask for the dark title bar every time ``window`` is mapped (a manager may only read the properties then)."""
    window.bind("<Map>", lambda e: e.widget is window and dark_titlebar(window), add="+")


def _set(x, display_name, win):
    x.XOpenDisplay.restype = ctypes.c_void_p
    x.XOpenDisplay.argtypes = [ctypes.c_char_p]
    x.XInternAtom.restype = ctypes.c_ulong
    x.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
    x.XQueryTree.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong),
                             ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_void_p),
                             ctypes.POINTER(ctypes.c_uint)]
    x.XChangeProperty.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_int,
                                  ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    for fn in (x.XFree, x.XFlush, x.XCloseDisplay):        # without argtypes a pointer is passed as a 32-bit int
        fn.argtypes = [ctypes.c_void_p]
    display = x.XOpenDisplay(display_name)
    if not display:
        return False
    try:
        root, parent, children, count = ctypes.c_ulong(), ctypes.c_ulong(), ctypes.c_void_p(), ctypes.c_uint()
        if x.XQueryTree(display, win, root, parent, children, count) and children:
            x.XFree(children)
        for target in {win, parent.value} - {0, root.value}:       # Tk's inner window and the managed wrapper
            for prop, value in PROPERTIES.items():
                x.XChangeProperty(display, target, x.XInternAtom(display, prop, 0), XA_STRING, 8, 0, value,
                                  len(value))
        x.XFlush(display)
        return True
    finally:
        x.XCloseDisplay(display)
