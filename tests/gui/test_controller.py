"""controller mixin: drawing, skins, callouts, icons, per-frame styling and the mapping highlight."""
import time
import tkinter as tk

import pytest

from cyclone2.gui import catalog, geometry, theme
from cyclone2.gui.drawing import mix

from .conftest import fire, leds_canvas, px


# ---------------------------------------------------------------- drawing
def test_draw_controller_map_and_home_clicks(app):
    for cv, parts, mode in ((app.map_canvas, app.map_items, "map"), (app.home_canvas, app.home_items, "home")):
        assert set(parts) == set(geometry.PARTS) and app.ctrl[cv] == (parts, mode)
    app.show("home")
    fire(app, app.map_canvas, "b:Y")
    assert app.sel_btn == "Y" and "Y" in app.press_t and app.page == "home"
    fire(app, app.home_canvas, "b:X")
    assert app.sel_btn == "X" and "X" in app.press_t and app.page == "buttons"
    assert app.pages["buttons"].winfo_manager() == "pack"


def test_leds_canvas_zones_pick_the_target(app):
    cv = leds_canvas(app)
    assert set(app.zone_items[cv]) == set(theme.SKINS["black"]["zones"]) == {"lower_left", "lower_right"}
    item, halo = app.zone_items[cv]["lower_left"]
    assert cv.type(item) == "line" and cv.type(halo) == "line"
    fire(app, cv, item)
    assert app.zone == "lower_left"
    assert not app.map_canvas.tag_bind(app.zone_items[app.map_canvas]["lower_left"][0], "<Button-1>")   # leds mode only


def test_ring_zones_on_the_other_skins(app):
    app.apply_skin("white")
    cv = leds_canvas(app)
    assert set(app.zone_items[cv]) == {"lower_left", "lower_right", "upper_left", "upper_right", "home"}
    ring, halo = app.zone_items[cv]["upper_right"]
    assert cv.type(ring) == "arc" and cv.type(halo) == "arc"
    fire(app, cv, ring)
    assert app.zone == "upper_right"
    assert cv.type(cv.find_all()[-1]) == "arc"                       # zones are raised above the parts


@pytest.mark.parametrize("text,target,page", [(c[0], c[4], c[4] if c[4] in ("sticks", "leds") else "buttons")
                                               for c in geometry.CALLOUTS])
def test_callouts_open_their_page(app, text, target, page):
    app.show("home")
    fire(app, app.home_canvas, "co:" + text.replace(" ", "_"))
    assert app.page == page
    if page == "buttons":
        assert app.sel_btn == target


def test_callout_geometry_and_modes(app):
    c = app.home_canvas
    assert len(c.find_withtag("co:LT_/_LB")) == 2                        # pill + label
    assert not app.map_canvas.find_withtag("co:LT_/_LB")                 # only the home drawing has callouts
    assert len(c.find_withtag("b:Up")) == 2                              # d-pad part + its arrow
    assert c.bbox("co:RT_/_RB")[0] > c.bbox("co:LT_/_LB")[2]


def test_callout_tags_are_single_words(app):
    """Tk splits a tag string at spaces, so a tag_bind on "co:A B" would never match its items."""
    for text, *_ in geometry.CALLOUTS:
        tag = "co:" + text.replace(" ", "_")
        assert len(app.home_canvas.find_withtag(tag)) == 2 and app.home_canvas.tag_bind(tag, "<Button-1>")


@pytest.mark.parametrize("kind", [k for _, k in catalog.SECTIONS])
def test_icon_kinds(app, kind, scratch):
    cv = tk.Canvas(scratch)
    app.icon(cv, kind, 50, 50)
    assert cv.find_all()


# ---------------------------------------------------------------- live state
def test_flash_and_trigger_level(app):
    app.flash("A")
    assert time.time() - app.press_t["A"] < 1
    assert app.trigger_level("A") is None
    assert app.trigger_level("LT") == 0 and app.trigger_level("RT") == 0
    app.pad = {"lt": 255, "rt": 51}
    assert app.trigger_level("LT") == 1 and app.trigger_level("RT") == pytest.approx(.2)


def test_style_states(app):
    cv, parts = app.map_canvas, app.map_items
    now = time.time()
    app.sel_btn = "B"
    app.style(cv, parts, "map", now)
    assert parts["B"]["st"] == (theme.SEL_FILL, theme.ACCENT, theme.ACCENT)
    assert parts["Y"]["st"] == parts["Y"]["base"]
    app.pad_down.add("Y")
    app.pad = {"lt": 128, "rt": 2}                                       # LT about half pressed, RT below the threshold
    app.style(cv, parts, "map", now)
    assert parts["Y"]["st"] == (theme.ACCENT, theme.ACCENT, theme.BG)
    lt = parts["LT"]
    assert lt["st"] == (mix(lt["base"][0], theme.ACCENT, 128 / 255), theme.ACCENT, lt["base"][2])
    assert parts["RT"]["st"] == parts["RT"]["base"]
    assert cv.itemcget(parts["Y"]["body"], "fill") == theme.ACCENT
    assert cv.itemcget(lt["body"], "fill") == lt["st"][0] != lt["base"][0]
    assert parts["LS"]["text"] is None and cv.itemcget(parts["LS"]["body"], "fill") == parts["LS"]["base"][0]
    app.style(cv, parts, "map", now)                                     # nothing changed: items are left alone
    app.style(app.home_canvas, app.home_items, "home", now)              # the selection highlight is map-only
    assert app.home_items["B"]["st"] == app.home_items["B"]["base"]


def test_style_badges_follow_remap(app):
    app._remapped = {"Y"}
    now = time.time()
    lc = leds_canvas(app)
    app.style(app.map_canvas, app.map_items, "map", now)
    app.style(lc, app.ctrl[lc][0], "leds", now)
    assert app.map_canvas.itemcget(app.map_items["Y"]["badge"], "state") == "normal"
    assert app.map_canvas.itemcget(app.map_items["A"]["badge"], "state") == "hidden"
    assert lc.itemcget(app.ctrl[lc][0]["Y"]["badge"], "state") == "hidden"


def test_style_ripple_and_stick_motion(app):
    cv, parts = app.map_canvas, app.map_items
    app.flash("A")                                                       # circle
    app.flash("LT")                                                      # polygon
    app.flash("View")                                                    # rounded rectangle
    app.style(cv, parts, "map", time.time())
    assert cv.itemcget(parts["A"]["glow"], "state") == "normal" and parts["A"]["glowing"]
    assert cv.itemcget(parts["LT"]["glow"], "state") == "normal"
    assert cv.itemcget(parts["View"]["glow"], "state") == "normal"
    gx, pts = cv.coords(parts["LT"]["glow"]), parts["LT"]["pts"]          # poly glow: the outline scaled up around its centre
    assert len(gx) == len(pts) and max(gx[::2]) - min(gx[::2]) > max(pts[::2]) - min(pts[::2])
    app.press_t["A"] = app.press_t["LT"] = app.press_t["View"] = time.time() - 5       # ripple over
    app.style(cv, parts, "map", time.time())
    assert cv.itemcget(parts["A"]["glow"], "state") == "hidden" and not parts["A"]["glowing"]
    app.style(cv, parts, "map", time.time())                             # nothing glowing: stays hidden
    app.pad = {"left": (1, 0), "right": (0, -1)}                         # stick caps follow the axes
    before = cv.coords(parts["LS"]["body"])
    app.style(cv, parts, "map", time.time())
    assert parts["LS"]["off"][0] > 5 and parts["RS"]["off"][1] < -5
    assert cv.coords(parts["LS"]["body"])[0] > before[0]
    off = parts["LS"]["off"]
    app.style(cv, parts, "map", time.time())                             # same position: below the movement threshold
    assert parts["LS"]["off"] == off
    app.pad = {}
    app.style(cv, parts, "map", time.time())
    assert parts["LS"]["off"] == (0, 0)


def test_animate_draws_the_visible_canvas_only(app):
    sk = theme.SKINS["black"]
    app.page = "leds"
    app.lights["animations"][app.v["light"]["anim"].get()].update(brightness=100)
    app.frame = 0
    app.animate()
    lc, hc = leds_canvas(app), app.home_canvas
    colors = app.led_colors(time.time())
    item, glow = app.zone_items[lc]["lower_left"]
    assert lc.itemcget(item, "fill") == colors["lower_left"]
    halo = mix(sk["body"][1], "#000000", .35)
    assert lc.itemcget(glow, "fill") == mix(colors["lower_left"], halo, .7)
    assert hc.itemcget(app.zone_items[hc]["lower_left"][0], "fill") == sk["led_off"]       # not visible: untouched
    assert app.tk.splitlist(app.tk.call("after", "info"))                                 # re-armed
    app.page = "buttons"
    app.animate()
    app.page = "profile"                                                  # no drawing on this page
    app.animate()


def test_animate_arc_zones_player_leds_and_no_lights(app):
    app.apply_skin("pink")
    app.page = "home"
    app.lights = None                                                     # nothing read yet: LEDs keep the "off" colour
    app.active = 2
    app.animate()
    hc, sk = app.home_canvas, theme.SKINS["pink"]
    assert hc.itemcget(app.zone_items[hc]["home"][0], "outline") == sk["led_off"]
    lines = app.player_items[hc]
    assert hc.itemcget(lines[1], "fill") == geometry.PLAYER_COLORS[1] and hc.itemcget(lines[0], "fill") == sk["led_off"]


def test_animate_arcs_follow_the_led_colours(app):
    app.apply_skin("white")
    an = app.animation()
    an["brightness"] = 100
    an["colors"][0]["home"] = "#00ff00"
    app.frame, app.page = 0, "leds"
    app.animate()
    lc = leds_canvas(app)
    ring, glow = app.zone_items[lc]["home"]
    assert lc.itemcget(ring, "outline") == "#00ff00"
    assert lc.itemcget(glow, "outline") == mix("#00ff00", mix(theme.SKINS["white"]["body"][1], "#000000", .35), .7)


# ---------------------------------------------------------------- mapping highlight
def test_refresh_mapping_describes_the_selected_button(app):
    assert app.map_title.cget("text") == "Botão A" and app.map_sub.cget("text") == "função atual: padrão (A)"
    assert app.map_canvas.itemcget(app.map_items["A"]["body"], "outline") == theme.ACCENT      # selected
    app.select_button("L4")
    assert app.map_title.cget("text") == "Botão L4" and "função atual: LS" == app.map_sub.cget("text")
    assert app.map_choice.get() == "LS"


def test_refresh_mapping_badges(app):
    assert app._remapped == {"L4", "R4"}                                  # the fixture remaps both back buttons
    app.v["keys"]["Y"].set("Home")
    app.v["turbo"]["B"].set(True)
    app.v["toggle"]["X"].set(True)
    assert app._remapped == {"L4", "R4", "Y", "B", "X"}
    assert app.map_canvas.itemcget(app.map_items["Y"]["badge"], "state") == "normal"
    assert app.home_canvas.itemcget(app.home_items["Y"]["badge"], "state") == "normal"
    app.select_button("Y")
    assert app.map_canvas.itemcget(app.map_items["Y"]["text"], "fill") == theme.ACCENT      # selected text
    app.v["keys"]["Y"].set("")
    assert "Y" not in app._remapped and app.map_canvas.itemcget(app.map_items["Y"]["badge"], "state") == "hidden"


# ---------------------------------------------------------------- skins
@pytest.mark.parametrize("name", ["white", "pink", "black"])
def test_apply_skin_draws_skin_colours(app, name):
    sk = theme.SKINS[name]
    app.apply_skin(name)
    assert app.skin == name
    assert app.map_items is app.ctrl[app.map_canvas][0] and app.home_items is app.ctrl[app.home_canvas][0]
    assert len(app.ctrl) == 3 and len(app._imgs) == 3 and len(app.zone_items) == 3 and len(app.player_items) == 3
    for c, (parts, mode) in app.ctrl.items():
        for pname, p in parts.items():
            assert p["base"] == sk[geometry.ROLES.get(pname, "btn")]
            shown = (theme.SEL_FILL, theme.ACCENT, theme.ACCENT) if (mode, pname) == ("map", app.sel_btn) else p["base"]
            assert p["st"] == shown                                      # refresh_mapping restyled the new items
            assert c.itemcget(p["body"], "fill") == shown[0] and c.itemcget(p["body"], "outline") == shown[1]
        assert len(parts["LS"]["extra"]) == 2 and c.type(parts["LS"]["extra"][1]) == "arc"      # stick cap highlight
        assert len(parts["Home"]["extra"]) == 1 and not parts["A"]["extra"]
        assert set(app.zone_items[c]) == set(sk["zones"])
        image = [i for i in c.find_all() if c.type(i) == "image"]
        assert len(image) == 1 and app._imgs[c].width() > 0
        for n in ("LT", "RT"):                                           # triggers sit behind the body image
            assert parts[n]["shape"] == "poly" and parts[n]["body"] < image[0] < parts["A"]["body"]
        for n in ("LB", "RB"):                                           # bumpers (poly too) are drawn over it
            assert parts[n]["shape"] == "poly" and parts[n]["body"] > image[0]
        assert parts["A"]["pts"] is None and parts["A"]["shape"] == "circle"
        img = app._imgs[c]
        assert px(img, 0, 0) is None and px(img, int(220 * app.s), int(100 * app.s))        # body filled, corner not


def test_apply_skin_keeps_the_drawings_interactive(app):
    app.apply_skin("pink")
    app.apply_skin("white")
    cv = leds_canvas(app)
    fire(app, cv, app.zone_items[cv]["home"][0])
    assert app.zone == "home"
    fire(app, app.map_canvas, "b:Y")                                     # redrawn parts are still clickable
    assert app.sel_btn == "Y"
    fire(app, app.home_canvas, "b:X")
    assert app.sel_btn == "X" and app.page == "buttons"
    assert app.map_items["X"]["st"] == (theme.SEL_FILL, theme.ACCENT, theme.ACCENT)
