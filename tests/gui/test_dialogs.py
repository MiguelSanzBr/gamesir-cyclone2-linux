"""Styled message boxes, the dark title bar request and the hand cursor."""
import ctypes
import tkinter as tk
from types import SimpleNamespace

import pytest

from cyclone2.gui import dialogs, titlebar, widgets
from cyclone2.gui.i18n import _

from .conftest import fire, walk

ASKYESNO, SHOWERROR = dialogs.askyesno, dialogs.showerror       # the autouse fixture replaces them in dialogs


# ---------------------------------------------------------------- message boxes
@pytest.fixture
def shown(shared_app):
    """A transient dialog of a withdrawn window is withdrawn too: show the shared App while a box is open."""
    shared_app.deiconify()
    shared_app.update()
    yield shared_app
    shared_app.withdraw()


def _answer(app, label):
    """Press the button ``label`` of the open dialog once it is up."""
    def press():
        box = next(w for w in app.winfo_children() if isinstance(w, dialogs.Dialog))
        btn = next(w for w in walk(box) if getattr(w, "text", None) == label)
        btn.event_generate("<Button-1>")
    app.after(60, press)


def test_showerror_waits_for_the_button(shown):
    _answer(shown, _("Fechar"))
    assert SHOWERROR("Erro", "boom", parent=shown) is None
    assert not any(isinstance(w, dialogs.Dialog) for w in shown.winfo_children())


def test_askyesno_returns_the_choice(shown):
    _answer(shown, "Sim")
    assert ASKYESNO("Restaurar", "Certeza?", parent=shown) is True
    _answer(shown, "Não")
    assert ASKYESNO("Restaurar", "Certeza?", parent=shown) is False


def test_dialog_closes_with_escape(shown):
    shown.after(60, lambda: next(w for w in shown.winfo_children()
                                       if isinstance(w, dialogs.Dialog)).event_generate("<Escape>"))
    assert ASKYESNO("t", "m", parent=shown) is False


# ---------------------------------------------------------------- hand cursor
def test_hand_cursor_over_clickable_canvas_items(shared_app):
    c = tk.Canvas(shared_app)
    item = c.create_rectangle(0, 0, 10, 10)
    widgets.hand(c, item)
    fire(shared_app, c, item, "<Enter>")
    assert c.cget("cursor") == "hand2"
    fire(shared_app, c, item, "<Leave>")
    assert c.cget("cursor") == ""
    c.destroy()


# ---------------------------------------------------------------- dark title bar
class FakeX:
    """Stands in for libX11: records the properties set; ``tree`` is (status, root, parent, children)."""

    def __init__(self, display=1, tree=(1, 1, 7, 0)):
        self.display, self.tree, self.props, self.freed, self.closed = display, tree, [], [], False

    def XOpenDisplay(self, name):
        return self.display

    def XInternAtom(self, display, name, only):
        return name

    def XQueryTree(self, display, win, root, parent, children, count):
        status, root.value, parent.value, children.value = self.tree
        return status

    def XChangeProperty(self, display, win, prop, kind, fmt, mode, value, n):
        self.props.append((win, prop, value))

    def XFree(self, ptr):
        self.freed.append(ptr)

    def XFlush(self, display):
        pass

    def XCloseDisplay(self, display):
        self.closed = True


def _fake_lib(fake):
    """Every ctypes-style function (attribute assignments allowed) of the fake, as plain callables."""
    class Fn:
        def __init__(self, f):
            self.f = f

        def __call__(self, *a):
            return self.f(*a)
    return SimpleNamespace(**{n: Fn(getattr(fake, n)) for n in dir(FakeX) if n.startswith("X")})


def test_dark_titlebar_sets_both_properties_on_the_window_and_its_wrapper():
    fake = FakeX(tree=(1, 1, 7, 99))
    assert titlebar._set(_fake_lib(fake), b":0", 5)
    assert sorted({w for w, *_r in fake.props}) == [5, 7]               # the root (1) is never touched
    assert {p for _w, p, _v in fake.props} == set(titlebar.PROPERTIES) and fake.closed
    assert fake.freed == [ctypes.c_void_p(99).value] or fake.freed       # the children list is released


def test_dark_titlebar_without_a_tree_or_children():
    for tree in ((0, 0, 0, 0), (1, 1, 7, 0)):
        fake = FakeX(tree=tree)
        assert titlebar._set(_fake_lib(fake), b":0", 5) and not fake.freed and fake.closed
    assert {w for w, *_r in fake.props} == {5, 7}


def test_dark_titlebar_without_a_display():
    fake = FakeX(display=0)
    assert titlebar._set(_fake_lib(fake), b":0", 5) is False and not fake.props and not fake.closed


def test_dark_titlebar_uses_the_real_library(shared_app):
    assert titlebar.dark_titlebar(shared_app) is True


def test_dark_on_show_applies_when_the_window_itself_is_mapped(shared_app, monkeypatch):
    calls = []
    monkeypatch.setattr(titlebar, "dark_titlebar", lambda w: calls.append(w))
    top = tk.Toplevel(shared_app)
    try:
        top.withdraw()
        titlebar.dark_on_show(top)
        tk.Label(top, text="child").pack()                    # a child's Map event must not count
        top.deiconify()
        top.update()
        assert calls == [top]
    finally:
        top.destroy()
