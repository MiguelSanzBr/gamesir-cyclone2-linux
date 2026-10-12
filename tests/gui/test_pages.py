"""pages mixin: layout helpers, home tiles, section pages and navigation, driven through the real widgets."""
import tkinter as tk

import pytest

from cyclone2 import light
from cyclone2 import protocol as p
from cyclone2.gui import catalog, sync, theme, widgets

from .conftest import click, doc_of, lights_of, pump, texts, walk


def pill(root, text):
    return next(w for w in walk(root) if isinstance(w, widgets.Pill) and w.text == text)


def saved(a):
    return "Salvo" in a.status.cget("text") and not a.busy


def toggles(root):
    return [w for w in walk(root) if isinstance(w, widgets.Toggle)]


def sliders(root):
    return [w for w in walk(root) if isinstance(w, widgets.Slider)]


# ---------------------------------------------------------------- navigation
def test_show_packs_only_the_requested_page(app):
    for name in app.pages:
        app.show(name)
        assert app.page == name
        assert [n for n, pg in app.pages.items() if pg.winfo_manager() == "pack"] == [name]


def test_back_button_and_home_tiles(app):
    for title, key in catalog.SECTIONS:
        tile = next(w for w in walk(app.pages["home"]) if isinstance(w, tk.Canvas) and title in texts(w)
                    and str(w.cget("cursor")) == "hand2")                 # (the drawing's callouts share the text)
        app.show("home")
        click(app, tile)
        assert app.page == key
        click(app, pill(app.pages[key], "‹  Início"))
        assert app.page == "home"


def test_home_tile_hover(app):
    tile = next(w for w in walk(app.pages["home"]) if isinstance(w, tk.Canvas) and "Perfil" in texts(w))
    click(app, tile, "<Enter>")
    assert tile.itemcget("bg", "fill") == theme.TILE_HI
    click(app, tile, "<Leave>")
    assert tile.itemcget("bg", "fill") == theme.TILE


def test_refresh_profiles(app):
    assert [b.text for b in app.profile_btns] == ["Perfil 1  ●", "Perfil 2", "Perfil 3", "Perfil 4"]
    assert app.profile_btns[0].fill == theme.TILE and app.profile_btns[1].fill == theme.BG
    app.active = None
    app.refresh_profiles()
    assert app.home_sub.cget("text") == "" and not any(b.text.endswith("●") for b in app.profile_btns)


def test_profile_chip_switches_the_controller(app, fake):
    click(app, app.profile_btns[2])
    pump(app)
    assert fake.current == 3 and app.active == 3 and app.profile_btns[2].text == "Perfil 3  ●"


def test_footer_buttons(app, fake, dlg, tmp_path):
    foot_buttons = {w.text: w for w in walk(app) if isinstance(w, widgets.Pill) and w.text in
                    ("Recarregar", "Restaurar backup", "Backup")}
    assert set(foot_buttons) == {"Recarregar", "Restaurar backup", "Backup"}
    app.v["name"].set("zzz")                                      # unsaved edit is overwritten by a reload
    app.after_cancel(app._save_job)
    app._save_job = None
    click(app, foot_buttons["Recarregar"])
    pump(app)
    assert app.v["name"].get() == doc_of(fake)["name"]
    click(app, foot_buttons["Backup"])                            # cancelled dialog
    click(app, foot_buttons["Restaurar backup"])
    assert not app.busy and not dlg.errors


# ---------------------------------------------------------------- buttons page
def test_mapping_chips_set_the_selected_button(app):
    page = app.pages["buttons"]
    app.select_button("B")
    click(app, pill(page, "X"))
    assert app.v["keys"]["B"].get() == "X" and app.map_choice.get() == "X"
    assert pill(page, "X").base == theme.ACCENT and pill(page, "A").base == theme.TILE_HI
    click(app, pill(page, "Padrão"))
    assert app.v["keys"]["B"].get() == "" and "padrão (B)" in app.map_sub.cget("text")
    click(app, pill(page, "Desativar"))
    assert app.v["keys"]["B"].get() == "None" and "B" in app._remapped
    app.v["keys"]["B"].set("LB+RB")                               # a combination: shown with spaces, no chip lit
    assert "LB + RB" in app.map_sub.cget("text") and app.map_choice.get() != "LB+RB"


def test_turbo_and_toggle_switches_follow_the_selected_button(app):
    page = app.pages["buttons"]
    app.select_button("Y")
    turbo, toggle = toggles(page)
    click(app, turbo)
    assert app.v["turbo"]["Y"].get() is True and "Y" in app._remapped
    click(app, toggle)
    assert app.v["toggle"]["Y"].get() is True
    app.select_button("A")
    assert not turbo.var.get()
    app.v["turbo"]["A"].set(True)                                 # the switch follows the stored value
    app.v["turbo"]["A"].set(False)
    click(app, pill(page, "Restaurar todos os botões"))
    assert not app.v["turbo"]["Y"].get() and not app.v["toggle"]["Y"].get() and not app._remapped


# ---------------------------------------------------------------- sticks / triggers / rumble pages
def test_slider_labels_use_their_format(app):
    app.v["sticks"]["left"]["dz0"].set(12)
    labels = [w.cget("text") for w in walk(app.pages["sticks"]) if isinstance(w, tk.Label)]
    assert "12%" in labels
    app.v["motors"]["left"].set(2)
    assert "50%" in [w.cget("text") for w in walk(app.pages["rumble"]) if isinstance(w, tk.Label)]
    app.v["gyro"]["aim"]["ratio"].set(30)
    assert "30" in [w.cget("text") for w in walk(app.pages["gyro"]) if isinstance(w, tk.Label)]
    app.v["light"]["speed"].set(7)                                # default formatter: str
    assert "7" in [w.cget("text") for w in walk(app.pages["leds"]) if isinstance(w, tk.Label)]


def test_sticks_page_toggles_write_the_profile(app, fake, fast):
    left = toggles(app.pages["sticks"])[:3]                       # X, Y, raw output of the left stick
    for t in left:
        click(app, t)
    pump(app, lambda: saved(app))
    st = doc_of(fake)["sticks"]["left"]
    assert st["output"]["invert_x"] and st["output"]["invert_y"] and st["square"]


def test_slider_drag_changes_the_stick_dead_zone(app, fake, fast):
    sl = sliders(app.pages["sticks"])[0]
    pad = 9 * sl.s
    sl.winfo_width = lambda: int(200 + 2 * pad)                   # a 200 px track
    sl._at(type("E", (), {"x": pad + 200 * .4})())                # 40% of 0..50
    assert app.v["sticks"]["left"]["dz0"].get() == 20
    pump(app, lambda: saved(app))
    assert doc_of(fake)["sticks"]["left"]["deadzone"][0] == 20


def test_trigger_hair_mode_chips(app, fake, fast):
    page = app.pages["triggers"]
    chip = [w for w in walk(page) if isinstance(w, widgets.Pill) and w.text == "Fixo"][0]
    click(app, chip)
    assert app.v["triggers"]["LT"]["hair_mode"].get() == 2 and chip.base == theme.ACCENT
    assert app.v["triggers"]["LT"]["hair"].get() is True          # on in the fixture
    click(app, toggles(page)[0])
    click(app, toggles(page)[0])
    pump(app, lambda: saved(app))
    assert doc_of(fake)["triggers"]["LT"]["hair_trigger"] == {"on": True, "mode": 2, "start": 10, "end": 90}


def test_rumble_test_button(app, fake, monkeypatch):
    monkeypatch.setattr(sync.time, "sleep", lambda s: None)
    click(app, pill(app.pages["rumble"], "Vibrar por 1 segundo"))
    pump(app)
    assert "vibração concluído" in app.status.cget("text")
    assert len(sliders(app.pages["rumble"])) == 4


# ---------------------------------------------------------------- gyro page
def test_gyro_chips_activation_key_and_target(app, fake, fast):
    page = app.pages["gyro"]
    aim_cards = [w for w in walk(page) if isinstance(w, widgets.Pill) and w.text == "Apertar liga/desliga"]
    assert len(aim_cards) == 2                                    # one card per function (aim, tilt)
    click(app, aim_cards[1])                                      # tilt: toggle on -> aim is turned off
    assert app.v["gyro"]["tilt"]["activation"].get() == 2 and app.v["gyro"]["aim"]["activation"].get() == 0
    click(app, [w for w in walk(page) if isinstance(w, widgets.Pill) and w.text == "RB"][1])
    click(app, [w for w in walk(page) if isinstance(w, widgets.Pill) and w.text == "Mouse"][1])
    pump(app, lambda: saved(app))
    m = doc_of(fake)["motion"]
    assert m["tilt"]["activation"] == 2 and m["aim"]["activation"] == 0
    assert m["tilt"]["trigger_key"] == "RB" and m["tilt"]["output"]["target"] == 4


# ---------------------------------------------------------------- lights page
def test_lights_page_pieces(app):
    page = app.pages["leds"]
    assert [pill(page, f"Animação {i}").text for i in range(1, 5)]
    assert {pill(page, label).text for _, label in catalog.PRESETS}
    assert {pill(page, label).text for _, label in catalog.ZONES} | {"Todas"} == {c.text for c in app.zone_cells.values()}
    click(app, pill(page, "Animação 2"))
    assert app.v["light"]["anim"].get() == 1 and pill(page, "Animação 2").base == theme.ACCENT
    click(app, pill(page, "Pulso"))                               # preset chip
    assert app.lights["animations"][1]["frames"] == 2 and app.preset_choice.get() == ""
    assert isinstance(app.picker, widgets.ColorPicker) and len(sliders(page)) == 2


# ---------------------------------------------------------------- profile page
def test_profile_page_name_options_and_lighting_settings(app, fake, fast):
    page = app.pages["profile"]
    entry = next(w for w in walk(page) if isinstance(w, tk.Entry))
    entry.delete(0, "end")
    entry.insert(0, "Novo nome")
    t = toggles(page)
    assert len(t) == 4                                            # three options + raise to wake
    click(app, t[0])
    click(app, pill(page, "20 min"))
    click(app, t[3])
    pump(app, lambda: saved(app))
    d = doc_of(fake)
    assert d["name"] == "Novo nome" and d["options"]["dpad_diagonal_lock"]
    assert lights_of(fake)["standby"] == 20 and lights_of(fake)["raise_to_wake"] is False
    assert app.info_label.cget("text").startswith("Dispositivo:")


def test_reset_profile_button(app):
    click(app, pill(app.pages["profile"], "Restaurar padrões deste perfil"))
    assert "Padrões do app" in app.status.cget("text")


def test_skin_chips_change_the_drawing_and_persist(app, tmp_path):
    page = app.pages["profile"]
    click(app, pill(page, "Branco"))
    assert app.skin == "white" and "white" in (tmp_path / "cfg" / "gui.json").read_text()
    assert pill(page, "Branco").base == theme.ACCENT and pill(page, "Preto").base == theme.TILE_HI


def test_helper_widgets_directly(app, scratch):
    row = app.row(scratch)
    assert row.master is scratch and row.winfo_manager() == "pack"
    app.label(scratch, "rótulo")
    assert "rótulo" in [w.cget("text") for w in scratch.winfo_children() if isinstance(w, tk.Label)]
    var = tk.IntVar(master=app, value=1)
    grid = app.chips(scratch, var, [(1, "um"), (2, "dois")], 1)
    chips = [w for w in grid.winfo_children()]
    assert [c.base for c in chips] == [theme.ACCENT, theme.TILE_HI]
    click(app, chips[1])
    assert var.get() == 2 and chips[0].base == theme.TILE_HI
    primary = app.button(scratch, "ok", lambda: None, primary=True)
    plain = app.button(scratch, "ok", lambda: None)
    assert primary.base == theme.ACCENT and plain.base == theme.TILE_HI
    f = app.card(scratch)                                         # no title, not side-packed
    assert f.master.winfo_manager() == "pack"
    f = app.card(scratch, "Título", side="left")
    assert "Título" in texts(f.master) or any(w.cget("text") == "Título" for w in f.winfo_children())
