"""app: construction, settings file, fonts, scaling, shutdown, skin change and main()."""
import json
import tkinter as tk

import pytest

from cyclone2.gui import app as app_mod, theme

from .conftest import badge, click, make_app, no_thread, pump


def test_family_resolution(monkeypatch):
    a = make_app(monkeypatch, ["DejaVu Sans", "Inter"])
    try:
        assert theme.FAMILY == "Inter" and a.font(10)[0] == "Inter"
    finally:
        a.destroy()
    assert a._closing


def test_construction_state_and_pages(app):
    assert set(app.pages) == {"home", "buttons", "sticks", "triggers", "rumble", "gyro", "leds", "profile"}
    assert len(app.profile_btns) == 4 and app.s >= 1.0 and app.font is theme.font
    assert set(app.v["keys"]) == set(app.v["turbo"]) == set(app.v["toggle"]) and "light" in app.v


def test_startup_timers_read_the_controller(fake):
    # only these two patches are temporary; undoing the test's monkeypatch would also drop the fake controller
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(tk, "_default_root", None)        # a second Tk root must not borrow the shared app's default
        mp.setattr(app_mod.threading, "Thread", no_thread)
        a = app_mod.App()                            # the read timer fires 200 ms after startup
    a.withdraw()
    a.tk.willdispatch()
    try:
        pump(a, lambda: a.doc is not None and not a.busy)
        assert badge(a)[0] == "3.5.6" and a.active == 1
    finally:
        a.destroy()


# ---------------------------------------------------------------- settings file
def test_load_settings(monkeypatch, tmp_path):
    f = tmp_path / "s.json"
    monkeypatch.setattr(app_mod, "SETTINGS", str(f))
    assert app_mod.load_settings() == {}                         # missing file
    f.write_text("{not json")
    assert app_mod.load_settings() == {}                         # corrupt file
    f.write_text('{"skin": "pink"}')
    assert app_mod.load_settings() == {"skin": "pink"}


def test_save_settings_creates_dirs_and_ignores_errors(monkeypatch, tmp_path):
    f = tmp_path / "deep" / "dir" / "s.json"
    monkeypatch.setattr(app_mod, "SETTINGS", str(f))
    app_mod.save_settings({"skin": "white"})
    assert json.loads(f.read_text()) == {"skin": "white"}
    blocker = tmp_path / "file"
    blocker.write_text("x")
    monkeypatch.setattr(app_mod, "SETTINGS", str(blocker / "s.json"))
    app_mod.save_settings({"skin": "pink"})                      # cannot create the directory: silently ignored


@pytest.mark.parametrize("stored,expected", [("white", "white"), ("nope", theme.DEFAULT_SKIN), (None, theme.DEFAULT_SKIN)])
def test_skin_loaded_from_settings(monkeypatch, tmp_path, stored, expected):
    f = tmp_path / "s.json"
    f.write_text(json.dumps({} if stored is None else {"skin": stored}))
    monkeypatch.setattr(app_mod, "SETTINGS", str(f))
    a = make_app(monkeypatch)
    try:
        assert a.skin == expected and a.skin_choice.get() == expected
    finally:
        a.destroy()


# ---------------------------------------------------------------- watch / skin / buttons
def test_watch_schedules_autosave_for_every_setting(app):
    assert app._save_job is None
    app.v["sticks"]["left"]["dz0"].set(app.v["sticks"]["left"]["dz0"].get() + 3)
    assert app._save_job is not None


def test_change_skin_redraws_and_persists(app, tmp_path):
    f = tmp_path / "cfg" / "gui.json"
    app.skin_choice.set("white")
    assert app.skin == "white" and json.loads(f.read_text()) == {"skin": "white"}
    assert app.map_items is app.ctrl[app.map_canvas][0]
    assert app.map_canvas.itemcget(app.map_items["B"]["body"], "fill") == theme.SKINS["white"]["face"][0]
    app.skin_choice.set("white")                                 # same skin: nothing to do
    assert app.skin == "white"
    app.skin_choice.set("pink")
    assert app.skin == "pink" and json.loads(f.read_text())["skin"] == "pink"
    assert len(app.zone_items[app.map_canvas]) == len(theme.SKINS["pink"]["zones"])


def test_change_skin_without_lights(app):
    app.lights = None
    app.change_skin("white")
    assert app.skin == "white"


def test_select_button_syncs_side_toggles(app):
    app.v["turbo"]["B"].set(True)
    app.select_button("B")
    assert app.sel_turbo.get() is True and app.sel_toggle.get() is False
    app.select_button("A")
    assert app.sel_turbo.get() is False


def test_main_runs_mainloop(monkeypatch):
    calls = []

    class Fake:
        def mainloop(self):
            calls.append("loop")
    monkeypatch.setattr(app_mod, "App", Fake)
    app_mod.main()
    assert calls == ["loop"]


def test_main_web_opens_the_browser_instead_of_the_gui(monkeypatch, capsys):
    opened = []
    monkeypatch.setattr(app_mod.webbrowser, "open", opened.append)
    monkeypatch.setattr(app_mod, "App", lambda: (_ for _ in ()).throw(AssertionError("GUI started")))
    app_mod.main(["web"])
    assert opened == [app_mod.WEB_URL]
    assert app_mod.WEB_URL in capsys.readouterr().out
