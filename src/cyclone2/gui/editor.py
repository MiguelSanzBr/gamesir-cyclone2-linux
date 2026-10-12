"""Mixin: moves values between the decoded records (``self.doc`` profile, ``self.lights`` lighting) and the widget
variables (``self.v``); the lighting editor (zones, frames, presets) and the LED preview colours."""
from .. import light, profile
from . import theme
from .catalog import BUTTONS, MOTOR_LEVELS, ZONES
from .drawing import mix
from .theme import ACCENT, BG, FG, SKINS, TILE_HI
from .widgets import Pill

STICK_DZ = ("dz0", "dz1", "adz0")


class Editor:
    # ------------------------------------------------------------ profile <-> widgets
    def load(self):
        """Show ``self.doc``/``self.lights`` in the widgets without triggering auto-save."""
        self._loading = True
        try:
            self._load()
        finally:
            self._loading = False

    def _load(self):
        d, v = self.doc, self.v
        v["name"].set(d["name"])
        for b in BUTTONS:
            k = d["buttons"][b]
            v["keys"][b].set("+".join(k["map"]))
            v["turbo"][b].set(k["turbo"])
            v["toggle"][b].set(k["toggle"])
        for side, sv in v["sticks"].items():
            st = d["sticks"][side]
            for name, val in zip(STICK_DZ, st["deadzone"]):
                sv[name].set(val)
            sv["raw"].set(st["square"])
            sv["inv_x"].set(st["output"]["invert_x"])
            sv["inv_y"].set(st["output"]["invert_y"])
        for t, tv in v["triggers"].items():
            tr = d["triggers"][t]
            tv["dz0"].set(tr["deadzone"][0])
            tv["dz1"].set(tr["deadzone"][1])
            h = tr["hair_trigger"]
            tv["hair"].set(h["on"])
            tv["hair_mode"].set(h["mode"])
            tv["hair_start"].set(h["start"])
            tv["hair_end"].set(h["end"])
        for k, var in v["motors"].items():
            var.set(min(range(5), key=lambda i: abs(MOTOR_LEVELS[i] - d["motors"][k])))
        for k, gv in v["gyro"].items():
            m = d["motion"][k]
            gv["activation"].set(m["activation"])
            gv["key"].set(m["trigger_key"])
            gv["target"].set(m["output"]["target"])
            gv["dz0"].set(m["deadzone"][0])
            gv["ratio"].set(m["output"]["axis_ratio"])
            gv["inv_x"].set(m["output"]["invert_x"])
            gv["inv_y"].set(m["output"]["invert_y"])
        for k, var in v["opts"].items():
            var.set(d["options"][k])
        if self.lights:
            lv, L = v["light"], self.lights
            lv["anim"].set(L["active"])
            lv["standby"].set(L["standby"])
            lv["raise_to_wake"].set(L["raise_to_wake"])
            self.load_animation()
        self.select_button(self.sel_btn)

    def gather(self):
        """Write widget values into ``self.doc`` and ``self.lights`` (only what the widgets edit)."""
        d, v = self.doc, self.v
        d["name"] = v["name"].get()
        for b in BUTTONS:
            k = d["buttons"][b]
            text = v["keys"][b].get()
            k["map"] = text.split("+") if text else []
            if v["turbo"][b].get() != k["turbo"]:               # the app's turbo switch writes 1/0; an
                k["turbo"] = v["turbo"][b].get()                # untouched switch keeps the stored speed
                k["turbo_speed"] = int(k["turbo"])
            k["toggle"] = v["toggle"][b].get()
        for side, sv in v["sticks"].items():
            st = d["sticks"][side]
            self._deadzone(st, [sv["dz0"].get(), sv["dz1"].get(), sv["adz0"].get(), st["deadzone"][3]])
            st["square"] = sv["raw"].get()
            st["output"].update(invert_x=sv["inv_x"].get(), invert_y=sv["inv_y"].get())
        for t, tv in v["triggers"].items():
            tr = d["triggers"][t]
            self._deadzone(tr, [tv["dz0"].get(), tv["dz1"].get(), *tr["deadzone"][2:]])
            tr["hair_trigger"] = {"on": tv["hair"].get(), "mode": tv["hair_mode"].get(),
                                  "start": tv["hair_start"].get(), "end": tv["hair_end"].get()}
        old_levels = {k: min(range(5), key=lambda i: abs(MOTOR_LEVELS[i] - x)) for k, x in d["motors"].items()}
        for k, var in v["motors"].items():
            if var.get() != old_levels[k]:      # keep exact stored values the 5 steps cannot show
                d["motors"][k] = MOTOR_LEVELS[var.get()]
        for k, gv in v["gyro"].items():
            m = d["motion"][k]
            m["activation"] = gv["activation"].get()
            m["trigger_key"] = gv["key"].get()
            self._deadzone(m, [gv["dz0"].get(), *m["deadzone"][1:]])
            m["output"].update(target=gv["target"].get(), axis_ratio=gv["ratio"].get(), invert_x=gv["inv_x"].get(),
                               invert_y=gv["inv_y"].get())
        for k, var in v["opts"].items():
            d["options"][k] = var.get()
        if self.lights:
            lv, L = v["light"], self.lights
            L["active"] = lv["anim"].get()
            L["standby"] = lv["standby"].get()
            L["raise_to_wake"] = lv["raise_to_wake"].get()
            an = self.animation()
            an["brightness"] = lv["brightness"].get()
            an["speed"] = lv["speed"].get()

    @staticmethod
    def _deadzone(rec, dz):
        """Change a dead zone and rebuild the curve from its points in %, like the app does on every save."""
        if dz != rec["deadzone"]:
            pts = [(min(max(x, dz[0]), dz[1]), min(max(y, dz[2]), dz[3]))      # a point may not leave the new
                   for x, y in profile.curve_percent(rec["curve"], rec["deadzone"])]    # range (bytes stay 0-255)
            rec["curve"] = profile.curve(dz, pts, rec["curve"]["type"], rec["curve"]["curvature"])
            rec["deadzone"] = dz
            rec["deadzone_on"] = True

    # ------------------------------------------------------------ lighting editor
    def animation(self):
        return self.lights["animations"][self.v["light"]["anim"].get()]

    def load_animation(self):
        """Show the selected animation: its sliders, frame chips and colours."""
        an = self.animation()
        was, self._loading = self._loading, True
        try:
            self.v["light"]["brightness"].set(an["brightness"])
            self.v["light"]["speed"].set(an["speed"])
        finally:
            self._loading = was
        self.frame = min(self.frame, max(an["frames"], 1) - 1)
        self.refresh_frames()

    def refresh_frames(self):
        """Frame chips of the selected animation and the zone colour dots."""
        bar, s = self.frame_bar, self.s
        for w in bar.winfo_children():
            w.destroy()
        for i in range(max(self.animation()["frames"], 1)):
            on = i == self.frame
            Pill(bar, f"Quadro {i + 1}", s, cmd=lambda i=i: self.select_frame(i), font=theme.font(9), radius=10,
                 padx=8, pady=4, fill=ACCENT if on else TILE_HI, fg=BG if on else FG).pack(side="left", padx=int(2 * s))
        colors = self.animation()["colors"][self.frame]
        for key, cell in self.zone_cells.items():
            cell.itemconfigure("dot", fill=colors["home" if key == "all" else key])   # Pill.draw keeps the dot colour
            cell.set(fill=theme.LINE if key == self.zone else TILE_HI, fg=ACCENT if key == self.zone else FG)
        self.picker.set(colors["home" if self.zone == "all" else self.zone])
        zones = SKINS[self.skin]["zones"]
        self.leds_hint.configure(text="Prévia ao vivo das luzes. Clique numa luz do desenho para pintá-la.\n" + (
            "Este modelo acende só as barras das empunhaduras." if len(zones) < len(ZONES) else ""))

    def select_frame(self, i):
        self.frame = i
        self.refresh_frames()
        self.preview_frame(True)

    def add_frame(self, step):
        an = self.animation()
        n = min(max(an["frames"] + step, 1), light.FRAMES)
        if n != an["frames"]:
            an["frames"] = n
            self.frame = min(self.frame, n - 1)
            self.refresh_frames()
            self.changed()

    def pick_zone(self, zone):
        self.zone = zone
        self.refresh_frames()

    def on_pick(self, color):
        frame = self.animation()["colors"][self.frame]
        for key, _ in ZONES:
            if self.zone in (key, "all"):
                frame[key] = color
        self.refresh_frames()
        self.changed()

    def apply_preset(self, name):
        if not self.lights or not name:
            return
        self.lights = light.apply_preset(self.lights, name, self.v["light"]["anim"].get())
        self.preset_choice.set("")
        self.frame = 0
        self.load_animation()
        self.changed()

    def led_colors(self, now):
        """Colours of the five LED zones at time ``now``: the frame being edited on the lights page, otherwise
        the animation playing (approximate timing), dimmed by its brightness."""
        an = self.animation()
        n = max(an["frames"], 1)
        f = self.frame if self.page == "leds" else int(now / (0.06 + (light.MAX_SPEED - an["speed"]) * 0.05)) % n
        off = SKINS[self.skin]["led_off"]
        return {k: mix(off, c, max(an["brightness"], 0) / 100) for k, c in an["colors"][f].items()}

    # ------------------------------------------------------------ resets
    def reset_mapping(self):
        if self.doc:
            self.doc = profile.reset(self.doc, "mapping")
            self.load()
            self.changed()

    def reset_profile(self):
        if self.doc:
            name = self.doc["name"]
            self.doc = profile.reset(self.doc)
            self.doc["name"] = name
            self.load()
            self.changed()
            self.set_status("Padrões do app restaurados neste perfil.")
