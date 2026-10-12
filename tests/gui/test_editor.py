"""editor mixin: profile/lighting dicts <-> widgets, lighting editor (animations, presets, frames, zones, colours)."""
import pytest

from cyclone2 import light, profile
from cyclone2 import protocol as p
from cyclone2.gui import theme
from cyclone2.gui.drawing import mix

from .conftest import click, doc_of, fire, leds_canvas, lights_of, pump, record, texts


def saved(a):
    return "Salvo" in a.status.cget("text") and not a.busy


def anim(fake, i=3):
    return lights_of(fake)["animations"][i]


# ---------------------------------------------------------------- profile <-> widgets
def test_load_without_lights_leaves_light_vars(app):
    app.lights = None
    app.v["light"]["standby"].set(20)
    app.load()
    assert app.v["light"]["standby"].get() == 20 and app._loading is False


def test_gather_without_lights_only_touches_the_profile(app):
    app.lights = None
    app.v["name"].set("so perfil")
    app.gather()
    assert app.doc["name"] == "so perfil"


def test_load_rounds_motors_and_untouched_ones_keep_their_exact_value(mk, fake, fast):
    fake.records[1][32] = 60                                # between two of the five steps
    a = mk(read=False)
    a.read_device()
    pump(a)
    assert a.v["motors"]["left"].get() == 2                 # nearest step: 50%
    a.v["motors"]["rt"].set(4)
    pump(a, lambda: saved(a))
    assert doc_of(fake)["motors"]["left"] == 60 and doc_of(fake)["motors"]["rt"] == 100
    a.v["motors"]["left"].set(2)                            # choosing the step it already shows changes nothing
    a.v["motors"]["left"].set(3)
    pump(a, lambda: "Salvo" in a.status.cget("text") and a.base == record(fake, 1) and not a.busy)
    assert doc_of(fake)["motors"]["left"] == 75


def test_motor_change_writes_the_step_value(app, fake, fast):
    app.v["motors"]["rt"].set(1)
    app.v["motors"]["left"].set(0)
    pump(app, lambda: saved(app))
    m = doc_of(fake)["motors"]
    assert m["rt"] == 25 and m["left"] == 0 and m["right"] == 100 and m["lt"] == 75


def test_every_editable_group_round_trips_through_autosave(app, fake, fast):
    v = app.v
    v["name"].set("Tudo")
    v["sticks"]["right"]["raw"].set(True)
    v["sticks"]["right"]["inv_x"].set(True)
    v["sticks"]["left"]["inv_y"].set(True)
    v["sticks"]["left"]["adz0"].set(7)
    t = v["triggers"]["RT"]
    t["hair"].set(True)
    t["hair_mode"].set(2)
    t["hair_start"].set(20)
    t["hair_end"].set(80)
    g = v["gyro"]["tilt"]
    g["activation"].set(2)
    g["key"].set("RB")
    g["target"].set(4)
    g["ratio"].set(40)
    g["inv_x"].set(True)
    g["inv_y"].set(True)
    g["dz0"].set(15)
    v["opts"]["switch_abxy_swap"].set(True)
    v["opts"]["xinput_abxy_swap"].set(False)
    v["turbo"]["Y"].set(True)
    v["toggle"]["X"].set(True)
    v["keys"]["Menu"].set("LB+RB")
    pump(app, lambda: saved(app))
    d = doc_of(fake)
    assert d["name"] == "Tudo" and d["sticks"]["right"]["square"] and d["sticks"]["right"]["output"]["invert_x"]
    assert d["sticks"]["left"]["output"]["invert_y"] and d["sticks"]["left"]["deadzone"][2] == 7
    assert d["triggers"]["RT"]["hair_trigger"] == {"on": True, "mode": 2, "start": 20, "end": 80}
    m = d["motion"]["tilt"]
    assert (m["activation"], m["trigger_key"], m["output"]["target"], m["output"]["axis_ratio"]) == (2, "RB", 4, 40)
    assert m["output"]["invert_x"] and m["output"]["invert_y"] and m["deadzone"][0] == 15
    assert d["options"]["switch_abxy_swap"] and not d["options"]["xinput_abxy_swap"]
    assert d["buttons"]["Y"]["turbo"] and d["buttons"]["X"]["toggle"] and d["buttons"]["Menu"]["map"] == ["LB", "RB"]
    assert app.base == record(fake, 1)


def test_trigger_dead_zone_rebuilds_the_curve(app, fake, fast):
    old = doc_of(fake)["triggers"]["LT"]
    app.v["triggers"]["LT"]["dz0"].set(30)
    app.v["triggers"]["LT"]["dz1"].set(70)
    pump(app, lambda: saved(app))
    tr = doc_of(fake)["triggers"]["LT"]
    assert tr["deadzone"][:2] == [30, 70] and tr["deadzone"][2:] == old["deadzone"][2:] and tr["deadzone_on"]
    assert tr["curve"]["points"] != old["curve"]["points"] and all(0 <= x <= 255 for pt in tr["curve"]["points"] for x in pt)


def test_gyro_activation_is_exclusive(app, fake, fast):
    g = app.v["gyro"]
    assert g["aim"]["activation"].get() == 1 and g["tilt"]["activation"].get() == 0
    g["tilt"]["activation"].set(3)                          # turning tilt on turns aim off
    assert g["aim"]["activation"].get() == 0 and g["tilt"]["activation"].get() == 3
    g["aim"]["activation"].set(2)                           # and the other way round
    assert g["tilt"]["activation"].get() == 0
    g["aim"]["activation"].set(0)                           # switching one off leaves the other alone
    g["tilt"]["activation"].set(1)
    assert g["aim"]["activation"].get() == 0 and g["tilt"]["activation"].get() == 1
    g["tilt"]["activation"].set(0)
    pump(app, lambda: saved(app))
    d = doc_of(fake)["motion"]
    assert d["aim"]["activation"] == 0 and d["tilt"]["activation"] == 0


# ---------------------------------------------------------------- lighting: animations and presets
def test_animation_chips_switch_the_edited_animation(app, fake, fast):
    lv = app.v["light"]
    assert len(app.frame_bar.winfo_children()) == 2                    # animation 4 has two frames
    lv["anim"].set(1)
    assert (lv["brightness"].get(), lv["speed"].get()) == (100, 17) and len(app.frame_bar.winfo_children()) == 5
    assert app.animation() is app.lights["animations"][1]
    app.frame = 4
    lv["anim"].set(0)                                                  # one frame: the selection is clamped
    assert app.frame == 0 and len(app.frame_bar.winfo_children()) == 1 and lv["brightness"].get() == 20
    pump(app, lambda: saved(app))
    assert lights_of(fake)["active"] == 0


def test_sliders_write_brightness_and_speed_of_the_selected_animation(app, fake, fast):
    app.v["light"]["anim"].set(1)
    app.v["light"]["brightness"].set(60)
    app.v["light"]["speed"].set(5)
    pump(app, lambda: saved(app))
    a = anim(fake, 1)
    assert (a["brightness"], a["speed"]) == (60, 5) and anim(fake, 3)["brightness"] == 0


def test_load_animation_does_not_trigger_a_save(app):
    app.v["light"]["anim"].set(2)                                      # trace -> load_animation (guarded)
    app.lights["animations"][2]["brightness"] = 33
    app.load_animation()
    assert app.v["light"]["brightness"].get() == 33 and app._loading is False
    app.after_cancel(app._save_job)                                    # only the chip change itself is pending


def test_load_animation_keeps_loading_flag_it_found(app):
    app._loading = True
    app.load_animation()
    assert app._loading is True
    app._loading = False


def test_apply_preset_replaces_the_animation(app, fake, fast):
    app.preset_choice.set("Rainbow")                                   # what the preset chips do
    assert app.preset_choice.get() == "" and app.frame == 0
    a = app.lights["animations"][3]
    assert a["frames"] == 8 and a["speed"] == 10 and a["colors"][1]["home"] == "#ffa500"
    assert app.v["light"]["speed"].get() == 10 and len(app.frame_bar.winfo_children()) == 8
    pump(app, lambda: saved(app))
    a = anim(fake)
    assert a["frames"] == 8 and a["colors"][0]["lower_left"] == "#ff0000" and a["colors"][7]["home"] == "#ff0000"


def test_apply_preset_ignores_empty_name_and_missing_lights(app):
    before = app.lights
    app.apply_preset("")
    assert app.lights is before and app._save_job is None
    app.lights = None
    app.apply_preset("Flow")
    assert app.lights is None


def test_add_frame_grows_and_shrinks_within_limits(app, fake, fast):
    assert app.animation()["frames"] == 2
    app.add_frame(1)
    assert app.animation()["frames"] == 3 and len(app.frame_bar.winfo_children()) == 3 and app._save_job
    app.frame = 2
    app.add_frame(-1)
    assert app.animation()["frames"] == 2 and app.frame == 1           # selection follows
    app.add_frame(-1)
    app.add_frame(-1)                                                  # at one frame: no-op
    assert app.animation()["frames"] == 1
    for _ in range(10):
        app.add_frame(1)
    assert app.animation()["frames"] == light.FRAMES
    pump(app, lambda: saved(app))
    assert anim(fake)["frames"] == light.FRAMES


def test_frame_buttons_and_chips(app, monkeypatch):
    sent = []
    monkeypatch.setattr(app, "send_now", sent.append)
    plus = next(w for w in app.frame_bar.master.winfo_children() if getattr(w, "text", None) == "+")
    minus = next(w for w in app.frame_bar.master.winfo_children() if getattr(w, "text", None) == "−")
    click(app, plus)
    assert app.animation()["frames"] == 3
    click(app, minus)
    assert app.animation()["frames"] == 2
    chips = app.frame_bar.winfo_children()
    click(app, chips[1])                                               # "Quadro 2"
    assert app.frame == 1 and sent == [p.command(p.LIGHT, 0, 2)]
    assert chips[1] not in app.frame_bar.winfo_children()              # chips are rebuilt on selection
    assert app.frame_bar.winfo_children()[1].fill == theme.ACCENT


# ---------------------------------------------------------------- lighting: zones and colours
def test_zone_pick_by_drawing_and_chips(app):
    cv = leds_canvas(app)
    item, halo = app.zone_items[cv]["lower_right"]
    fire(app, cv, item)
    assert app.zone == "lower_right" and app.zone_cells["lower_right"].base == theme.LINE
    assert app.zone_cells["all"].base == theme.TILE_HI
    assert app.picker.color() == app.animation()["colors"][0]["lower_right"]
    fire(app, cv, halo)
    click(app, app.zone_cells["home"])
    assert app.zone == "home" and app.picker.color() == app.animation()["colors"][0]["home"]
    click(app, app.zone_cells["all"])
    assert app.zone == "all" and app.zone_cells["all"].base == theme.LINE


def test_zone_dots_show_the_frame_colours(app):
    colors = app.animation()["colors"][0]
    for key, cell in app.zone_cells.items():
        assert cell.itemcget("dot", "fill") == colors["home" if key == "all" else key]


def test_colour_picker_writes_the_zone_colour(app, fake, fast):
    app.pick_zone("upper_left")
    app.picker.choose("#123456")
    before = dict(anim(fake)["colors"][0])
    assert app.animation()["colors"][0]["upper_left"] == "#123456" and app.animation()["colors"][0]["home"] == before["home"]
    assert app.zone_cells["upper_left"].itemcget("dot", "fill") == "#123456"
    pump(app, lambda: saved(app))
    c = anim(fake)["colors"][0]
    assert c["upper_left"] == "#123456" and c["home"] == before["home"] and c["lower_left"] == before["lower_left"]


def test_colour_picker_on_all_zones_and_other_frame(app, fake, fast):
    first = dict(anim(fake)["colors"][0])
    app.select_frame(1)
    app.picker.choose("#abcdef")                                       # zone "all"
    assert set(app.animation()["colors"][1].values()) == {"#abcdef"} and app.animation()["colors"][0] == first
    pump(app, lambda: saved(app))
    assert set(anim(fake)["colors"][1].values()) == {"#abcdef"} and anim(fake)["colors"][0] == first


def test_hint_depends_on_the_skin(app):
    assert "só as barras" in app.leds_hint.cget("text")                # black edition: grip bars only
    app.apply_skin("white")
    app.refresh_frames()
    assert "só as barras" not in app.leds_hint.cget("text") and "Clique numa luz" in app.leds_hint.cget("text")


def test_led_colors_edit_frame_vs_playing_animation(app, monkeypatch):
    off = theme.SKINS["black"]["led_off"]
    app.v["light"]["anim"].set(0)
    an = app.animation()
    an["brightness"] = 100
    an["frames"], an["speed"] = 2, light.MAX_SPEED
    an["colors"][0] = dict.fromkeys(light.LEDS, "#ff0000")
    an["colors"][1] = dict.fromkeys(light.LEDS, "#00ff00")
    app.page, app.frame = "leds", 1                                    # lights page: the frame being edited
    assert set(app.led_colors(0).values()) == {"#00ff00"}
    app.page = "home"                                                  # elsewhere: the playing animation, by time
    step = 0.06
    assert set(app.led_colors(0).values()) == {"#ff0000"}
    assert set(app.led_colors(step * 1.1).values()) == {"#00ff00"}
    an["brightness"] = 0                                               # dimmed completely
    assert set(app.led_colors(0).values()) == {off}
    an["brightness"] = -5                                              # negative is treated as 0
    assert set(app.led_colors(0).values()) == {off}
    an["brightness"] = 50
    assert app.led_colors(0)["home"] == mix(off, "#ff0000", .5)
    an["frames"] = 0                                                   # no frames still shows frame 0
    assert set(app.led_colors(5).values()) == {mix(off, "#ff0000", .5)}


# ---------------------------------------------------------------- resets
def test_reset_mapping_clears_the_remaps(app, fake, fast):
    assert app.v["keys"]["L4"].get() == "LS"
    app.reset_mapping()
    assert app.v["keys"]["L4"].get() == "" and not app._remapped
    pump(app, lambda: saved(app))
    assert doc_of(fake)["buttons"]["L4"]["map"] == [] and doc_of(fake)["name"] == app.doc["name"]


def test_reset_profile_keeps_the_name(app, fake, fast):
    app.v["name"].set("Meu perfil")
    app.gather()
    app.v["motors"]["left"].set(1)
    app.reset_profile()
    assert app.v["name"].get() == "Meu perfil" and app.v["motors"]["left"].get() == 3
    assert "Padrões do app" in app.status.cget("text") and app.v["sticks"]["left"]["dz0"].get() == 10
    pump(app, lambda: saved(app))
    d = doc_of(fake)
    assert d["name"] == "Meu perfil" and d["motors"]["left"] == 75 and d["sticks"]["left"]["deadzone"] == [10, 100, 0, 100]


def test_resets_without_a_profile_do_nothing(app):
    app.doc = None
    app.reset_mapping()
    app.reset_profile()
    assert app._save_job is None


def test_texts_of_the_frame_chips(app):
    assert [t for w in app.frame_bar.winfo_children() for t in texts(w)] == ["Quadro 1", "Quadro 2"]
