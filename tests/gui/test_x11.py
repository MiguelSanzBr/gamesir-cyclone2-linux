"""libX11 helper of the window frame: lookups, properties and the move/resize request, on a fake library and on the
real display (which has no window manager here, so it never reports support)."""
import ctypes
from types import SimpleNamespace

import pytest

from cyclone2.gui import x11


class Fn:
    """A ctypes function stand-in: callable, and ``restype`` / ``argtypes`` can be assigned."""

    def __init__(self, f):
        self.f = f

    def __call__(self, *a):
        return self.f(*a)


class FakeLib:
    """libX11 with a window tree, a ``_NET_SUPPORTED`` list and a log of the calls that change something."""

    def __init__(self, supported=("_NET_WM_MOVERESIZE",), tree=(1, 1, 7, 0), property_status=0):
        self.supported, self.tree, self.property_status = supported, tree, property_status
        self.log, self.freed, self._keep = [], [], []
        for name in dir(FakeLib):
            if name.startswith("X"):
                setattr(self, name, Fn(getattr(self, name)))

    @staticmethod
    def atom_of(name):
        return 1000 + sum(map(ord, name))

    def XInternAtom(self, display, name, only):
        return self.atom_of(name.decode())

    def XDefaultRootWindow(self, display):
        return 1

    def XQueryTree(self, display, win, root, parent, children, count):
        status, root.value, parent.value, children.value = self.tree
        return status

    def XGetWindowProperty(self, display, win, prop, off, length, delete, kind, atype, fmt, count, rest, data):
        if self.property_status == 0 and self.supported is not None:
            arr = (ctypes.c_ulong * len(self.supported))(*[self.atom_of(n) for n in self.supported])
            self._keep.append(arr)
            count.value, data.value = len(arr), ctypes.addressof(arr)
        return self.property_status

    def XChangeProperty(self, display, win, prop, kind, fmt, mode, data, n):
        self.log.append(("property", win, prop, fmt, n, list(ctypes.cast(data, ctypes.POINTER(ctypes.c_long))[:n])))

    def XSendEvent(self, display, win, propagate, mask, event):
        e = x11.ClientMessage.from_address(event.value)
        self.log.append(("send", win, mask, e.window, e.message_type, e.format, list(e.data.l)))

    def XUngrabPointer(self, display, time):
        self.log.append(("ungrab",))

    def XFree(self, ptr):
        self.freed.append(ptr)

    def XFlush(self, display):
        pass


def helper(**kw):
    lib = FakeLib(**kw)
    return x11.X11(lib, 99), lib


# ---------------------------------------------------------------- the window manager's support
def test_supports_looks_in_net_supported():
    h, lib = helper(supported=("_NET_WM_STATE", "_NET_WM_MOVERESIZE"))
    assert h.supports("_NET_WM_MOVERESIZE") and not h.supports("_NET_FRAME_EXTENTS") and lib.freed


def test_supports_is_false_without_the_property_or_on_error():
    assert not helper(supported=None)[0].supports("_NET_WM_MOVERESIZE")      # no window manager: no list at all
    assert not helper(property_status=1)[0].supports("_NET_WM_MOVERESIZE")


# ---------------------------------------------------------------- the managed window
def test_managed_is_the_wrapper_of_the_toplevel(shared_app):
    h, lib = helper(tree=(1, 1, 7, 55))
    assert h.managed(shared_app) == 7 and [p.value for p in lib.freed] == [55]


@pytest.mark.parametrize("tree", [(1, 1, 1, 0), (0, 0, 0, 0)])           # parent is the root / the query failed
def test_managed_is_none_without_a_wrapper(shared_app, tree):
    assert helper(tree=tree)[0].managed(shared_app) is None


def test_undecorate_sets_the_motif_hints_once_the_window_exists(shared_app):
    h, lib = helper(tree=(1, 1, 1, 0))
    assert h.undecorate(shared_app) is False and not lib.log
    h, lib = helper()
    assert h.undecorate(shared_app) is True
    (kind, win, prop, fmt, n, data), = lib.log
    assert (kind, win, prop, fmt, n, data) == ("property", 7, lib.atom_of("_MOTIF_WM_HINTS"), 32, 5, [2, 0, 0, 0, 0])


def test_move_resize_releases_the_pointer_and_asks_the_manager(shared_app):
    h, lib = helper()
    h.move_resize(shared_app, x11.MOVE, 120, 45)
    ungrab, send = lib.log
    assert ungrab == ("ungrab",)
    assert send == ("send", 1, x11.SUBSTRUCTURE_MASK, 7, lib.atom_of("_NET_WM_MOVERESIZE"), 32, [120, 45, 8, 1, 1])
    h, lib = helper(tree=(1, 1, 1, 0))                                       # not managed yet: the plain window
    h.move_resize(shared_app, 3, 0, 0)
    assert lib.log[1][3] == shared_app.winfo_id()


# ---------------------------------------------------------------- finding the library and Tk's display
def test_library_falls_back_to_the_usual_names(monkeypatch):
    tried = []

    def cdll(name):
        tried.append(name)
        if name != "libX11.so.6":
            raise OSError(name)
        return "lib"
    monkeypatch.setattr(x11.ctypes, "CDLL", cdll)
    monkeypatch.setattr(x11.ctypes.util, "find_library", lambda name: "libfound.so")
    assert x11.library() == "lib" and tried == ["libfound.so", "libX11.so.6"]
    monkeypatch.setattr(x11.ctypes.util, "find_library", lambda name: None)
    assert x11.library() == "lib"                                            # nothing found: no attempt with None
    monkeypatch.setattr(x11.ctypes, "CDLL", lambda name: (_ for _ in ()).throw(OSError(name)))
    assert x11.library() is None


def test_tk_display_of_the_real_window(shared_app):
    display = x11.tk_display(shared_app)
    assert isinstance(display, int) and display


def test_tk_display_tries_each_tk_library(shared_app, monkeypatch):
    tk = SimpleNamespace(Tk_MainWindow=Fn(lambda interp: 0), Tk_NameToWindow=Fn(lambda *a: 0))

    def cdll(name):
        if name != x11.TK_LIBRARIES[1]:
            raise OSError(name)
        return tk
    monkeypatch.setattr(x11.ctypes, "CDLL", cdll)
    assert not x11.tk_display(shared_app)                                    # no main window: nothing to read
    monkeypatch.setattr(x11.ctypes, "CDLL", lambda name: (_ for _ in ()).throw(OSError(name)))
    assert x11.tk_display(shared_app) is None


# ---------------------------------------------------------------- X11.of
def test_of_needs_every_part(shared_app, monkeypatch):
    monkeypatch.setattr(x11, "library", lambda: None)
    assert x11.X11.of(shared_app) is None
    fake = FakeLib()
    monkeypatch.setattr(x11, "library", lambda: fake)
    monkeypatch.setattr(x11, "tk_display", lambda w: 0)
    assert x11.X11.of(shared_app) is None                                    # no Tk display

    def broken(widget):
        raise AttributeError("Tk_MainWindow")
    monkeypatch.setattr(x11, "tk_display", broken)
    assert x11.X11.of(shared_app) is None                                    # Tk without the symbols
    monkeypatch.setattr(x11, "tk_display", lambda w: 99)
    assert isinstance(x11.X11.of(shared_app), x11.X11)
    monkeypatch.setattr(x11, "library", lambda: FakeLib(supported=()))
    assert x11.X11.of(shared_app) is None                                    # the manager cannot move windows for us


def test_of_on_the_real_display_without_a_window_manager(shared_app):
    assert x11.X11.of(shared_app) is None
