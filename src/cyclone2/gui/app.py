"""The ``c2gui`` main window: state, layout skeleton and the mixins that do the work."""
import json
import os
import threading
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

from .. import keys
from . import i18n, theme
from .catalog import BUTTONS, MOTION, SECTIONS
from .controller import ControllerView
from .editor import Editor
from .i18n import LANGS, _
from .live_input import PadInput
from .pages import Pages
from .sync import DeviceSync
from .theme import BG, FG, MUTED, SKINS, TILE
from .widgets import Pill

SETTINGS = os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), "cyclone2", "gui.json")


def load_settings():
    try:
        with open(SETTINGS, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_settings(data):
    try:
        os.makedirs(os.path.dirname(SETTINGS), exist_ok=True)
        with open(SETTINGS, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except OSError:
        pass                       # only a convenience (the drawing colour)


class App(Pages, ControllerView, Editor, DeviceSync, PadInput, tk.Tk):
    """Main window. ``self.v`` holds one Tk variable per editable setting of the active profile."""

    def __init__(self):
        super().__init__()
        saved = load_settings().get("lang")
        i18n.LANG = saved if saved in LANGS else i18n.system_lang()
        self.restart = False               # set when the language changes: main() builds a new window
        self.title("GameSir Cyclone 2 — Linux")
        self.configure(bg=BG)
        theme.FAMILY = theme.pick_family(self)
        # UI scale from the real font size (desktop DPI/font scaling); 10pt Sans is ~15px tall at 96 dpi
        self.s = max(1.0, tkfont.Font(root=self, font=theme.font(10)).metrics("linespace") / 15)
        self.doc = self.base = None        # decoded profile being edited / its bytes on the controller
        self.lights = self.lbase = None    # same for the (global) lighting record
        self.active = None                 # profile in use on the controller (1-4)
        self.busy = False
        self.sel_btn = "A"
        self.zone, self.frame = "all", 0   # lighting editor: colour target and frame being edited
        self._loading = False
        self._save_job = None
        self.skin = load_settings().get("skin", theme.DEFAULT_SKIN)
        self.skin = self.skin if self.skin in SKINS else theme.DEFAULT_SKIN
        self._imgs = {}                    # canvas -> body gradient image (kept referenced)
        self.ctrl = {}                     # canvas -> (parts, mode) of every controller drawing
        self.zone_items = {}               # canvas -> {zone: (item, halo)}
        self.player_items = {}             # canvas -> profile indicator items
        self.page = "home"
        self.pad, self.pad_down = {}, set()   # last decoded state report / buttons held on the controller
        self.press_t = {}                  # button -> time of the last press (ripple animation)
        self._remapped = set()
        self._closing = False
        self._pad_fd = None
        self.conn_text = None              # pill text of the last successful read
        self._style()
        self._vars()
        self._build()
        w, h = int(1180 * self.s), int(860 * self.s)
        self.geometry(f"{min(w, int(self.winfo_screenwidth() * .95))}x{min(h, int(self.winfo_screenheight() * .9))}")
        self.after(200, self.read_device)
        self.after(theme.POLL_MS, self.poll)
        self.after(theme.FRAME_MS, self.animate)
        threading.Thread(target=self._read_pad, daemon=True).start()

    def destroy(self):
        self._closing = True
        for job in self.tk.splitlist(self.tk.call("after", "info")):   # timers would outlive the window
            self.after_cancel(job)
        super().destroy()

    font = staticmethod(theme.font)

    def _style(self):
        st = ttk.Style(self)
        st.theme_use("clam")
        st.configure(".", background=BG, foreground=FG, font=theme.font(10))

    def _vars(self):
        V, I, B = tk.StringVar, tk.IntVar, tk.BooleanVar
        self.v = {
            "name": V(), "keys": {b: V() for b in BUTTONS}, "turbo": {b: B() for b in BUTTONS},
            "toggle": {b: B() for b in BUTTONS},
            "sticks": {s: {"dz0": I(), "dz1": I(), "adz0": I(), "raw": B(), "inv_x": B(), "inv_y": B()}
                       for s in ("left", "right")},
            "triggers": {t: {"dz0": I(), "dz1": I(), "hair": B(), "hair_mode": I(), "hair_start": I(), "hair_end": I()}
                         for t in keys.TRIGGERS},
            "motors": {m: I() for m in ("left", "right", "lt", "rt")},
            "gyro": {g: {"activation": I(), "key": V(), "target": I(), "dz0": I(), "ratio": I(), "inv_x": B(),
                         "inv_y": B()} for g, _ in MOTION},
            "opts": {o: B() for o in ("dpad_diagonal_lock", "xinput_abxy_swap", "switch_abxy_swap")},
            "light": {"anim": I(), "brightness": I(), "speed": I(), "standby": I(), "raise_to_wake": B()},
        }
        self.preset_choice = V()
        self.skin_choice = V(value=self.skin)
        self.lang_choice = V(value=i18n.LANG)

    def _watch(self):
        """Every setting change schedules an automatic save (the official app also applies changes at once)."""
        def each(node):
            for var in node.values():
                if isinstance(var, dict):
                    each(var)
                else:
                    var.trace_add("write", lambda *_, var=var: self.changed(var))
        each(self.v)

    def _build(self):
        s = self.s
        head = tk.Frame(self, bg=BG)
        head.pack(fill="x", padx=int(24 * s), pady=(int(16 * s), 0))
        tk.Label(head, text="GameSir Connect · Linux", bg=BG, fg=MUTED, font=theme.font(9)).pack(side="left")
        self.profile_btns = [Pill(head, _("Perfil {}").format(i) + "  ●", s, cmd=lambda i=i: self.select_profile(i),
                                  fill=BG, fg=MUTED, hover=TILE, padx=14, pady=6) for i in range(1, 5)]
        for b in reversed(self.profile_btns):
            b.pack(side="right", padx=2)

        foot = tk.Frame(self, bg=BG)
        foot.pack(side="bottom", fill="x", padx=int(24 * s), pady=int(14 * s))
        for text, cmd in ((_("Recarregar"), self.read_device), (_("Restaurar backup"), self.restore), ("Backup", self.backup)):
            self.button(foot, text, cmd).pack(side="right", padx=int(4 * s))
        self.status = tk.Label(foot, text="", bg=BG, fg=MUTED, anchor="w", font=theme.font(9))
        self.status.pack(side="left", fill="x", expand=True)

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)
        self.pages = {"home": self._p_home(body)}
        builders = {"buttons": self._p_buttons, "sticks": self._p_sticks, "triggers": self._p_triggers,
                    "rumble": self._p_rumble, "gyro": self._p_gyro, "leds": self._p_leds, "profile": self._p_profile}
        for title, key in SECTIONS:
            page = tk.Frame(body, bg=BG)
            top = tk.Frame(page, bg=BG, height=int(46 * s))
            top.pack(fill="x", padx=int(24 * s), pady=(int(10 * s), int(6 * s)))
            back = Pill(top, _("‹  Início"), s, cmd=lambda: self.show("home"), fill=BG, fg=MUTED, hover=TILE, padx=12,
                        pady=6)
            back.place(relx=0, rely=.5, anchor="w")
            tk.Label(top, text=_(title), bg=BG, fg=FG, font=theme.font(17)).place(relx=.5, rely=.5, anchor="center")
            inner = tk.Frame(page, bg=BG)
            inner.pack(fill="both", expand=True, padx=int(24 * s), pady=int(8 * s))
            builders[key](inner)
            self.pages[key] = page
        for group in ("keys", "turbo", "toggle"):
            for var in self.v[group].values():
                var.trace_add("write", lambda *_: self.refresh_mapping())
        self.v["light"]["anim"].trace_add("write", lambda *_: self.lights and not self._loading and self.load_animation())
        self.preset_choice.trace_add("write", lambda *_: self.apply_preset(self.preset_choice.get()))
        self.skin_choice.trace_add("write", lambda *_: self.change_skin(self.skin_choice.get()))
        self.lang_choice.trace_add("write", lambda *_: self.change_lang(self.lang_choice.get()))
        self._watch()
        self.refresh_profiles()
        self.show("home")

    def select_button(self, name):
        super().select_button(name)
        self.sel_turbo.set(self.v["turbo"][name].get())
        self.sel_toggle.set(self.v["toggle"][name].get())

    def change_skin(self, name):
        if name != self.skin:
            self.apply_skin(name)
            save_settings({**load_settings(), "skin": name})
            if self.lights:
                self.refresh_frames()


    def change_lang(self, code):
        """Save the language and close this window; :func:`main` opens a new one (device state is re-read)."""
        if code != i18n.LANG:
            save_settings({**load_settings(), "lang": code})
            self.restart = True
            self.after_idle(self.destroy)       # let the chip traces of this change finish first


def main():
    while True:
        app = App()
        app.mainloop()
        if not getattr(app, "restart", False):
            break
