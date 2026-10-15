"""Shared fixtures and helpers of the GUI tests. They need a real X display and the in-process FakeController.

The real controller must never be touched: every test runs with device discovery returning nothing and
``os.open`` refusing real hidraw nodes, unless the ``fake`` fixture (which opens its own socket) is active.
"""
import os
import re
import time
import tkinter as tk
from types import SimpleNamespace

import pytest

from cyclone2 import device, discovery, light, profile
from cyclone2 import protocol as p
from cyclone2.gui import app as app_mod, dialogs, i18n, sync, theme
from fake_device import FIXTURE

BACKUP = open(FIXTURE, "rb").read()


# ---------------------------------------------------------------- helpers
def pump(app, cond=None, timeout=5.0):
    """Run the Tk event loop until cond() (default: worker finished and its after-callbacks ran)."""
    cond = cond or (lambda: not app.busy)
    end = time.time() + timeout
    while time.time() < end:
        app.update()
        if cond():
            app.update()
            return
        time.sleep(0.003)
    raise AssertionError("pump timeout")


def fire(app, widget, tag, seq="<Button-1>"):
    """Invoke the Python callback bound to a canvas item tag (hit-testing needs a mapped window)."""
    script = widget.tag_bind(tag, seq)
    app.tk.eval(re.sub(r"%.", "0", script))
    app.update()


def walk(w):
    yield w
    for c in w.winfo_children():
        yield from walk(c)


def click(app, w, seq="<Button-1>"):
    """Run the handler bound to `seq` (event_generate does not reach widgets of a withdrawn window)."""
    app.tk.eval(re.sub(r"%.", "0", w.bind(seq)))
    app.update()


def clear_timers(a):
    """Cancel every pending after() timer (debounced saves, polls, retries) and the autosave job."""
    for i in a.tk.splitlist(a.tk.call("after", "info")):
        a.after_cancel(i)
    a._save_job = None


def xy(x, y):
    return SimpleNamespace(x=x, y=y)


def px(img, x, y):
    """RGB of a PhotoImage pixel, or None if transparent."""
    return None if img.transparency_get(x, y) else tuple(img.get(x, y))


def texts(cv):
    return [cv.itemcget(i, "text") for i in cv.find_all() if cv.type(i) == "text"]


def leds_canvas(app):
    return next(c for c, (_, mode) in app.ctrl.items() if mode == "leds")


def no_thread(*a, **kw):
    """Stand-in for threading.Thread that never runs its target."""
    return SimpleNamespace(start=lambda: None)


def make_app(monkeypatch, families=None):
    """A fresh App (own Tk root, no threads/timers); optionally with tkfont.families() faked."""
    monkeypatch.setattr(theme, "FAMILY", theme.FAMILY)          # undo the global assignment made by App.__init__
    monkeypatch.setattr(tk, "_default_root", None)
    if families is not None:
        monkeypatch.setattr(theme.tkfont, "families", lambda root=None: families)
    monkeypatch.setattr(app_mod.threading, "Thread", no_thread)
    a = app_mod.App()
    a.withdraw()
    a.tk.willdispatch()
    clear_timers(a)
    return a


def record(fake, n):
    return bytes(fake.records[n])


def doc_of(fake, n=1):
    return profile.decode(record(fake, n))


def lights_of(fake):
    return light.decode(record(fake, p.LIGHTS))


def written(fake, n):
    """Byte ranges (start, end) of record ``n`` written by WRITE commands."""
    return [(r[3] << 8 | r[4], (r[3] << 8 | r[4]) + r[5]) for r in fake.commands(p.WRITE) if r[2] == n]


def no_state(self, timeout=0.5):
    return None


# ---------------------------------------------------------------- fixtures
@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    """No hardware, no real home directory, no dialogs, no timers behind the tests' back."""
    real_open = os.open

    def guarded(path, flags, *a):
        if str(path).startswith("/dev/hidraw"):
            raise AssertionError(f"real device access: {path}")
        return real_open(path, flags, *a)
    monkeypatch.setattr(os, "open", guarded)
    monkeypatch.setattr(discovery, "find_devices", lambda: iter([]))    # FakeController.install() overrides this
    monkeypatch.setattr(discovery, "SYS", str(tmp_path / "no-sys"))     # even the real find_devices sees nothing
    monkeypatch.setattr(app_mod, "SETTINGS", str(tmp_path / "cfg" / "gui.json"))
    monkeypatch.setattr(i18n, "LANG", "pt")                             # the existing tests assert Portuguese texts
    monkeypatch.setattr(i18n, "system_lang", lambda env=None: "pt")     # ... whatever the locale of the machine is
    d = SimpleNamespace(save="", open="", yes=True, errors=[], asked=[])
    monkeypatch.setattr(sync.filedialog, "asksaveasfilename", lambda **kw: d.save)
    monkeypatch.setattr(sync.filedialog, "askopenfilename", lambda **kw: d.open)
    monkeypatch.setattr(sync.dialogs, "showerror", lambda *a, **kw: d.errors.append(a))
    monkeypatch.setattr(sync.dialogs, "askyesno", lambda *a, **kw: d.asked.append(a) or d.yes)
    monkeypatch.setattr(theme, "POLL_MS", 10 ** 7)
    monkeypatch.setattr(theme, "FRAME_MS", 10 ** 7)
    return d


@pytest.fixture
def dlg(isolated):
    return isolated


@pytest.fixture(scope="session")
def shared_app():
    """One App for the whole run (building the Tk widget tree costs ~0.5 s); mk() resets it per test.
    No input reader thread and no startup timers: those are exercised explicitly."""
    with pytest.MonkeyPatch.context() as mp:
        def boom(*a, **k):
            raise AssertionError("real device access")
        mp.setattr(device, "Device", boom)
        mp.setattr(app_mod.threading, "Thread", no_thread)
        mp.setattr(theme, "POLL_MS", 10 ** 7)
        mp.setattr(theme, "FRAME_MS", 10 ** 7)
        mp.setattr(app_mod, "SETTINGS", os.devnull + "/gui.json")       # unwritable: never touches the real home
        mp.setattr(i18n, "system_lang", lambda env=None: "pt")
        a = app_mod.App()
    a.withdraw()
    a.tk.willdispatch()             # worker thread may call app.after without a running mainloop()
    clear_timers(a)
    yield a
    a.destroy()


@pytest.fixture
def mk(shared_app, fake, monkeypatch):
    """Factory: reset the shared App, read the fake controller (the state stream is not waited for)."""
    a = shared_app
    monkeypatch.setattr(device.Device, "state", no_state)

    def make(read=True, current=1):
        pump(a)
        clear_timers(a)
        fake.current = current
        a.doc = a.base = a.lights = a.lbase = a.active = a.conn_text = None
        a.sel_btn, a.zone, a.frame, a._remapped, a._loading = "A", "all", 0, set(), False
        a.pad_down, a.pad, a.press_t, a._pad_fd = set(), {}, {}, None
        if a.skin != "black":
            a.apply_skin("black")
        a.skin_choice.set("black")
        a.show("home")
        a.refresh_profiles()
        if read:
            a.read_device()
            pump(a)
        return a
    yield make
    pump(a)
    clear_timers(a)


@pytest.fixture
def scratch(shared_app):
    f = tk.Frame(shared_app, bg=theme.BG)
    yield f
    f.destroy()


@pytest.fixture
def app(mk):
    return mk()


@pytest.fixture
def fast(monkeypatch):
    monkeypatch.setattr(theme, "AUTOSAVE_MS", 5)
