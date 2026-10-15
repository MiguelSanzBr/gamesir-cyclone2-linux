"""The little of X11 needed for a window frame drawn by the app, over Tk's own display connection.

A frameless but *managed* window (``_MOTIF_WM_HINTS`` without decorations) keeps its taskbar entry, focus, maximise and
snap; moving and resizing are delegated to the window manager with ``_NET_WM_MOVERESIZE``, as Qt's ``startSystemMove``
does. Everything is optional: :meth:`X11.of` returns ``None`` when the library, Tk's display or the window manager
support is missing, and the caller then keeps the native title bar.
"""
import ctypes
import ctypes.util

TK_LIBRARIES = ("libtk8.6.so.0", "libtk8.6.so", "libtk8.7.so", "libtk8.5.so")
MOVE, SOURCE_APP = 8, 1                  # _NET_WM_MOVERESIZE direction "move" (0-7 are the resize edges) / source
CLIENT_MESSAGE, SUBSTRUCTURE_MASK = 33, (1 << 19) | (1 << 20)
XA_ATOM = 4


class _Data(ctypes.Union):
    _fields_ = [("l", ctypes.c_long * 5)]


class ClientMessage(ctypes.Structure):
    _fields_ = [("type", ctypes.c_int), ("serial", ctypes.c_ulong), ("send_event", ctypes.c_int),
                ("display", ctypes.c_void_p), ("window", ctypes.c_ulong), ("message_type", ctypes.c_ulong),
                ("format", ctypes.c_int), ("data", _Data)]


def library():
    """libX11, found by the loader's search or by its usual file names (``find_library`` needs tools that a bundled
    Python, such as the AppImage's, may not have); ``None`` if there is none."""
    for name in filter(None, (ctypes.util.find_library("X11"), "libX11.so.6", "libX11.so")):
        try:
            return ctypes.CDLL(name)
        except OSError:
            continue
    return None


def _declare(x):
    ptr, ulong, integer = ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int
    sigs = {
        "XInternAtom": (ulong, [ptr, ctypes.c_char_p, integer]),
        "XDefaultRootWindow": (ulong, [ptr]),
        "XQueryTree": (integer, [ptr, ulong, ctypes.POINTER(ulong), ctypes.POINTER(ulong), ctypes.POINTER(ptr),
                                 ctypes.POINTER(ctypes.c_uint)]),
        "XChangeProperty": (integer, [ptr, ulong, ulong, ulong, integer, integer, ptr, integer]),
        "XGetWindowProperty": (integer, [ptr, ulong, ulong, ctypes.c_long, ctypes.c_long, integer, ulong,
                                         ctypes.POINTER(ulong), ctypes.POINTER(integer), ctypes.POINTER(ulong),
                                         ctypes.POINTER(ulong), ctypes.POINTER(ptr)]),
        "XSendEvent": (integer, [ptr, ulong, integer, ctypes.c_long, ptr]),
        "XUngrabPointer": (integer, [ptr, ulong]),
        "XFree": (integer, [ptr]),
        "XFlush": (integer, [ptr]),
    }
    for name, (res, args) in sigs.items():      # without these ctypes passes pointers as 32-bit ints and crashes
        fn = getattr(x, name)
        fn.restype, fn.argtypes = res, args


def tk_display(widget):
    """``Display *`` of Tk's connection (the first member of every ``Tk_Window``), or ``None``."""
    interp = ctypes.c_void_p(widget.tk.interpaddr())
    for name in TK_LIBRARIES:
        try:
            tk = ctypes.CDLL(name)
        except OSError:
            continue
        tk.Tk_MainWindow.restype = tk.Tk_NameToWindow.restype = ctypes.c_void_p
        tk.Tk_MainWindow.argtypes = [ctypes.c_void_p]
        tk.Tk_NameToWindow.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_void_p]
        main = tk.Tk_MainWindow(interp)
        win = main and tk.Tk_NameToWindow(interp, str(widget).encode(), main)
        return win and ctypes.c_void_p.from_address(win).value
    return None


class X11:
    def __init__(self, lib, display):
        _declare(lib)
        self.x, self.display = lib, display
        self.root = lib.XDefaultRootWindow(display)

    @classmethod
    def of(cls, widget):
        """The helper for ``widget``'s display if the window manager can move and resize windows for us."""
        lib = library()
        try:
            display = lib and tk_display(widget)
            helper = display and cls(lib, display)
        except AttributeError:                      # a Tk without the symbols
            return None
        return helper if helper and helper.supports("_NET_WM_MOVERESIZE") else None

    def atom(self, name):
        return self.x.XInternAtom(self.display, name.encode(), 0)

    def supports(self, name):
        """Is ``name`` listed in the window manager's ``_NET_SUPPORTED``?"""
        kind, fmt, count, rest, data = (ctypes.c_ulong(), ctypes.c_int(), ctypes.c_ulong(), ctypes.c_ulong(),
                                        ctypes.c_void_p())
        status = self.x.XGetWindowProperty(self.display, self.root, self.atom("_NET_SUPPORTED"), 0, 4096, 0, XA_ATOM,
                                           kind, fmt, count, rest, data)
        if status or not data:
            return False
        try:
            atoms = (ctypes.c_ulong * count.value).from_address(data.value)
            return self.atom(name) in list(atoms)
        finally:
            self.x.XFree(data)

    def managed(self, widget):
        """The window the window manager manages: the parent Tk wraps around the toplevel's own window (``None`` while
        the window has not been created by the server yet)."""
        win, root, parent, children, count = (widget.winfo_id(), ctypes.c_ulong(), ctypes.c_ulong(),
                                              ctypes.c_void_p(), ctypes.c_uint())
        if self.x.XQueryTree(self.display, win, root, parent, children, count) and children:
            self.x.XFree(children)
        return parent.value if parent.value not in (0, root.value) else None

    def undecorate(self, widget):
        """Remove the system title bar and borders; ``False`` if the window is not ready yet."""
        win = self.managed(widget)
        if win is None:
            return False
        hints = (ctypes.c_long * 5)(2, 0, 0, 0, 0)          # MWM_HINTS_DECORATIONS set, decorations = none
        prop = self.atom("_MOTIF_WM_HINTS")
        self.x.XChangeProperty(self.display, win, prop, prop, 32, 0, ctypes.cast(hints, ctypes.c_void_p), 5)
        self.x.XFlush(self.display)
        return True

    def move_resize(self, widget, direction, x_root, y_root):
        """Let the window manager drag (``MOVE``) or resize (0-7: edges clockwise from the top left) the window."""
        win = self.managed(widget) or widget.winfo_id()
        event = ClientMessage(type=CLIENT_MESSAGE, window=win, message_type=self.atom("_NET_WM_MOVERESIZE"), format=32)
        event.data.l[:] = [x_root, y_root, direction, 1, SOURCE_APP]
        self.x.XUngrabPointer(self.display, 0)               # Tk's implicit grab would keep the manager from taking over
        self.x.XSendEvent(self.display, self.root, 0, SUBSTRUCTURE_MASK, ctypes.cast(ctypes.byref(event), ctypes.c_void_p))
        self.x.XFlush(self.display)
