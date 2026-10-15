"""The window frame drawn by the app, driven with a fake window-manager helper (the CI display has no manager)."""
import tkinter as tk
from types import SimpleNamespace

import pytest

from cyclone2.gui import chrome, dialogs, x11

from .conftest import click, make_app, pump, walk

ASKYESNO = dialogs.askyesno                         # the autouse fixture replaces it in dialogs


class FakeX:
    """Records what the frame asks of the window manager; ``undecorate`` fails ``not_ready`` times first."""

    def __init__(self, not_ready=0):
        self.not_ready, self.undecorated, self.requests = not_ready, 0, []

    def undecorate(self, widget):
        self.undecorated += 1
        return self.undecorated > self.not_ready

    def move_resize(self, widget, direction, x_root, y_root):
        self.requests.append((direction, x_root, y_root))


@pytest.fixture
def fake_x(monkeypatch):
    fake = FakeX()
    monkeypatch.setattr(chrome.X11, "of", staticmethod(lambda widget: fake))
    return fake


def _frame(app, **kw):
    top = tk.Toplevel(app, bg="#1b1b1b")
    top.title("Frame test")
    top.geometry("500x400+50+60")
    bar = chrome.install(top, 1.0, **kw)
    tk.Label(top, text="content").pack(expand=True)
    top.update()
    return top, bar


def _icons(bar):
    return [c for c in bar.pack_slaves() if isinstance(c, tk.Canvas)]      # packed right to left: close, max, min


def _edges(top):
    return [w for w in top.place_slaves()]


def test_the_frame_is_installed_only_where_the_manager_can_help(shared_app, monkeypatch):
    monkeypatch.setattr(chrome.X11, "of", staticmethod(lambda widget: None))
    top = tk.Toplevel(shared_app)
    assert chrome.install(top, 1.0) is None and not top.pack_slaves()
    top.destroy()


def test_native_title_bar_on_request(shared_app, monkeypatch, fake_x):
    monkeypatch.setenv("CYCLONE2_NATIVE_TITLEBAR", "1")
    top = tk.Toplevel(shared_app)
    assert chrome.install(top, 1.0) is None and not fake_x.undecorated
    top.destroy()


def test_bar_title_buttons_and_edges(shared_app, fake_x):
    top, bar = _frame(shared_app)
    try:
        assert bar.cget("bg") == chrome.BAR and len(_icons(bar)) == 3 and len(_edges(top)) == 8
        assert top.title() in [w.cget("text") for w in walk(bar) if w.winfo_class() == "Label"]
        assert fake_x.undecorated == 1
    finally:
        top.destroy()


def test_dragging_the_bar_starts_the_move_once_the_mouse_moves(shared_app, fake_x):
    top, bar = _frame(shared_app)
    try:
        bar.event_generate("<Button-1>")
        assert not fake_x.requests                       # a click alone (or a double click) must not start a move
        bar.event_generate("<B1-Motion>", rootx=120, rooty=45)
        bar.event_generate("<B1-Motion>", rootx=130, rooty=50)
        assert fake_x.requests == [(x11.MOVE, 120, 45)]
        bar.event_generate("<ButtonRelease-1>")
        bar.event_generate("<B1-Motion>")
        assert len(fake_x.requests) == 1
    finally:
        top.destroy()


def test_edges_resize_through_the_manager(shared_app, fake_x):
    top, _bar = _frame(shared_app)
    try:
        by_cursor = {w.cget("cursor"): w for w in _edges(top)}
        assert set(by_cursor) == {c for _d, c, _o in chrome.EDGES}
        for direction, cursor, _opts in chrome.EDGES:
            by_cursor[cursor].event_generate("<Button-1>", rootx=10 * direction, rooty=3)
        assert fake_x.requests == [(d, 10 * d, 3) for d, _c, _o in chrome.EDGES]
    finally:
        top.destroy()


def test_window_buttons(shared_app, fake_x, monkeypatch):
    seen = []
    monkeypatch.setattr(chrome, "toggle_maximize", lambda win: seen.append("max"))
    top = tk.Toplevel(shared_app)
    top.geometry("500x400+50+60")
    top.iconify = lambda: seen.append("min")
    bar = chrome.install(top, 1.0)
    tk.Label(top, text="content").pack(expand=True)
    top.update()
    close, maximize, minimize = _icons(bar)
    maximize.event_generate("<Button-1>")
    minimize.event_generate("<Button-1>")
    assert seen == ["max", "min"]
    close.event_generate("<Enter>")
    assert close.cget("bg") != chrome.BAR
    close.event_generate("<Leave>")
    assert close.cget("bg") == chrome.BAR
    click(shared_app, bar, "<Double-Button-1>")
    assert seen[-1] == "max"
    close.event_generate("<Button-1>")
    shared_app.update()
    assert not top.winfo_exists()


def test_toggle_maximize_flips_the_zoomed_state():
    state = {"zoomed": False}
    win = SimpleNamespace(attributes=lambda name, value=None: state.update(zoomed=value) if value is not None
                          else state["zoomed"])
    chrome.toggle_maximize(win)
    assert state["zoomed"] is True
    chrome.toggle_maximize(win)
    assert state["zoomed"] is False


def test_options_leave_out_buttons_and_edges(shared_app, fake_x):
    closed = []
    top, bar = _frame(shared_app, resizable=False, minimizable=False, maximizable=False,
                      on_close=lambda: closed.append(1))
    try:
        assert len(_icons(bar)) == 1 and not _edges(top)
        assert not bar.bind("<Double-Button-1>")                  # nothing to toggle
        _icons(bar)[0].event_generate("<Button-1>")
        assert closed == [1]
    finally:
        top.destroy()


def test_undecorate_is_retried_until_the_window_exists(shared_app, monkeypatch):
    fake = FakeX(not_ready=2)
    monkeypatch.setattr(chrome.X11, "of", staticmethod(lambda widget: fake))
    top, _bar = _frame(shared_app)
    try:
        pump(shared_app, lambda: fake.undecorated >= 3)
        assert fake.undecorated == 3
    finally:
        top.destroy()


# ---------------------------------------------------------------- the main window and the boxes use it
def test_main_window_uses_the_frame_when_available(monkeypatch, fake_x):
    a = make_app(monkeypatch)
    try:
        assert a.pack_slaves()[0].cget("bg") == chrome.BAR
    finally:
        a.destroy()


def test_dialog_has_only_a_close_button_in_the_frame(shared_app, fake_x):
    shared_app.deiconify()
    shared_app.update()
    try:
        def close():
            box = next(w for w in shared_app.winfo_children() if isinstance(w, dialogs.Dialog))
            _icons(box.pack_slaves()[0])[0].event_generate("<Button-1>")
        shared_app.after(80, close)
        assert ASKYESNO("t", "m", parent=shared_app) is False
        assert fake_x.undecorated >= 1
    finally:
        shared_app.withdraw()
