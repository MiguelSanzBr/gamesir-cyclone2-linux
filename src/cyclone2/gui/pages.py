"""Mixin: layout helpers (cards, sliders, chips…), the home page, the section pages and navigation."""
import tkinter as tk

from .. import light
from . import theme
from .i18n import LANGS, _
from .catalog import (ACTIVATION, GYRO_KEYS, MOTION, MOTOR_LEVELS, OUTPUTS, PRESETS, SECTIONS, STANDBY, TARGETS,
                      ZONES)
from .drawing import rounded
from .geometry import HEIGHT, HOME_OFFSET, TOP, WIDTH
from .theme import ACCENT, BG, FG, LINE, MUTED, SKINS, TILE, TILE_HI
from .widgets import ColorPicker, Pill, Slider, Toggle, field, panel


class Pages:
    """Builds the widgets bound to ``self.v`` (see :class:`cyclone2.gui.app.App`)."""

    # ------------------------------------------------------------ helpers
    def button(self, parent, text, cmd, primary=False):
        return Pill(parent, text, self.s, cmd=cmd, fill=ACCENT if primary else TILE_HI, fg=BG if primary else FG,
                    hover="#62e07a" if primary else LINE, font=theme.font(10, "bold" if primary else "normal"))

    def card(self, parent, title=None, side=None):
        """Rounded card; returns the inner frame to fill."""
        s = self.s
        c, f = panel(parent, s)
        if side:
            c.pack(side=side, fill="both", expand=True, padx=int(6 * s), pady=int(6 * s))
        else:
            c.pack(fill="x", padx=int(6 * s), pady=int(6 * s))
        if title:
            tk.Label(f, text=title, bg=TILE, fg=FG, font=theme.font(11, "bold")).pack(anchor="w", pady=(0, int(8 * s)))
        return f

    @staticmethod
    def row(parent):
        r = tk.Frame(parent, bg=parent["bg"])
        r.pack(fill="x")
        return r

    def label(self, parent, text):
        tk.Label(parent, text=text, bg=parent["bg"], fg=MUTED, font=theme.font(9)).pack(anchor="w", pady=(int(6 * self.s), 0))

    def slider(self, parent, label, var, lo, hi, fmt=str):
        bg = parent["bg"]
        r = tk.Frame(parent, bg=bg)
        r.pack(fill="x", pady=int(5 * self.s))
        top = tk.Frame(r, bg=bg)
        top.pack(fill="x")
        tk.Label(top, text=label, bg=bg, fg=MUTED, font=theme.font(9)).pack(side="left")
        val = tk.Label(top, bg=bg, fg=FG, font=theme.font(9, "bold"))
        val.pack(side="right")
        Slider(r, var, lo, hi, self.s).pack(fill="x", pady=(int(2 * self.s), 0))
        var.trace_add("write", lambda *_: val.configure(text=fmt(var.get())))

    def toggle(self, parent, label, var):
        r = tk.Frame(parent, bg=parent["bg"])
        r.pack(fill="x", pady=int(5 * self.s))
        tk.Label(r, text=label, bg=parent["bg"], fg=FG, font=theme.font(10)).pack(side="left")
        Toggle(r, var, self.s).pack(side="right")

    def chips(self, parent, var, options, cols):
        """Grid of selectable chips bound to a variable (options: list of ``(value, label)``)."""
        s = self.s
        grid = tk.Frame(parent, bg=parent["bg"])
        grid.pack(fill="x", pady=int(4 * s))
        labels = []
        for i, (value, text) in enumerate(options):
            c = Pill(grid, _(text), s, cmd=lambda v=value: var.set(v), font=theme.font(9), radius=10, padx=10, pady=6)
            c.grid(row=i // cols, column=i % cols, sticky="ew", padx=int(3 * s), pady=int(3 * s))
            labels.append((value, c))
        for col in range(cols):
            grid.columnconfigure(col, weight=1)

        def paint(*_):
            for value, c in labels:
                on = str(var.get()) == str(value)
                c.set(fill=ACCENT if on else TILE_HI, fg=BG if on else FG)
        var.trace_add("write", paint)
        paint()
        return grid

    def drawing(self, parent, mode, ox=0):
        c = tk.Canvas(parent, width=int((WIDTH + 2 * ox) * self.s), height=int((HEIGHT + TOP) * self.s), bg=BG,
                      highlightthickness=0)
        return c, self.draw_controller(c, mode, ox=ox)

    # ------------------------------------------------------------ pages
    def _p_home(self, parent):
        s = self.s
        page = tk.Frame(parent, bg=BG)
        tk.Label(page, text="Cyclone 2", bg=BG, fg=FG, font=theme.font(18)).pack(pady=(int(14 * s), 0))
        self.home_sub = tk.Label(page, text="", bg=BG, fg=MUTED, font=theme.font(10))
        self.home_sub.pack(pady=(int(2 * s), int(6 * s)))
        self.home_canvas, self.home_items = self.drawing(page, "home", ox=HOME_OFFSET)
        self.home_canvas.pack()
        tk.Label(page, text=_("Aperte os botões do controle: eles acendem aqui."), bg=BG, fg=MUTED,
                 font=theme.font(8)).pack()
        self.pill = tk.Label(page, text=_("procurando controle…"), bg=BG, fg=MUTED, font=theme.font(9))
        self.pill.pack(pady=int(8 * s))
        tiles = tk.Frame(page, bg=BG)
        tiles.pack(pady=int(10 * s))
        for title, key in SECTIONS:
            t = tk.Canvas(tiles, width=int(104 * s), height=int(96 * s), bg=BG, highlightthickness=0, cursor="hand2")
            t.pack(side="left", padx=int(5 * s))
            rounded(t, 1, 1, 103 * s, 95 * s, 16 * s, fill=TILE, outline="", tags="bg")
            self.icon(t, key, 52, 36)
            t.create_text(52 * s, 74 * s, text=_(title), fill=FG, font=theme.font(9))
            t.bind("<Button-1>", lambda e, k=key: self.show(k))
            t.bind("<Enter>", lambda e, t=t: t.itemconfigure("bg", fill=TILE_HI))
            t.bind("<Leave>", lambda e, t=t: t.itemconfigure("bg", fill=TILE))
        return page

    def _p_buttons(self, p):
        s = self.s
        left = tk.Frame(p, bg=BG)
        left.pack(side="left", fill="y", padx=(0, int(16 * s)))
        self.map_canvas, self.map_items = self.drawing(left, "map")
        self.map_canvas.pack(pady=int(20 * s))
        tk.Label(left, text=_("Clique num botão do controle para escolher a função dele.\n"
                               "L4/R4: botões traseiros · ● verde: botão personalizado."),
                 bg=BG, fg=MUTED, font=theme.font(9), justify="left").pack(anchor="w")
        right = self.card(p, side="left")
        self.map_title = tk.Label(right, bg=TILE, fg=FG, font=theme.font(13, "bold"))
        self.map_title.pack(anchor="w")
        self.map_sub = tk.Label(right, bg=TILE, fg=MUTED, font=theme.font(9))
        self.map_sub.pack(anchor="w", pady=(0, int(8 * s)))
        self.map_choice = tk.StringVar()
        self.map_choice.trace_add("write", lambda *_: self.v["keys"][self.sel_btn].get() != self.map_choice.get()
                                  and self.v["keys"][self.sel_btn].set(self.map_choice.get()))
        self.chips(right, self.map_choice, TARGETS, 4)
        self.sel_turbo, self.sel_toggle = tk.BooleanVar(), tk.BooleanVar()
        self.toggle(right, _("Turbo (disparo automático)"), self.sel_turbo)
        self.toggle(right, _("Disparo contínuo (aperta uma vez, segura)"), self.sel_toggle)
        for var, key in ((self.sel_turbo, "turbo"), (self.sel_toggle, "toggle")):
            var.trace_add("write", lambda *_, var=var, key=key: self.v[key][self.sel_btn].get() != var.get()
                          and self.v[key][self.sel_btn].set(var.get()))
        self.button(right, _("Restaurar todos os botões"), self.reset_mapping).pack(anchor="w", pady=(int(10 * s), 0))

    def _p_sticks(self, p):
        pct = lambda v: f"{v}%"
        cols = self.row(p)
        for side, lbl in (("left", "Analógico esquerdo"), ("right", "Analógico direito")):
            c = self.card(cols, _(lbl), side="left")
            v = self.v["sticks"][side]
            self.slider(c, _("Zona morta interna"), v["dz0"], 0, 50, pct)
            self.slider(c, _("Zona morta externa (alcance máximo)"), v["dz1"], 50, 100, pct)
            self.slider(c, _("Anti-zona morta"), v["adz0"], 0, 50, pct)
            self.toggle(c, _("Inverter eixo X"), v["inv_x"])
            self.toggle(c, _("Inverter eixo Y"), v["inv_y"])
            self.toggle(c, _("Saída bruta (ignora zona morta e curva)"), v["raw"])
        tk.Label(p, text=_("A zona morta e a curva seguem o modelo do app: os pontos da curva são recalculados quando a "
                           "zona morta muda."), bg=BG, fg=MUTED, font=theme.font(9)).pack(anchor="w", padx=int(8 * self.s))

    def _p_triggers(self, p):
        pct = lambda v: f"{v}%"
        cols = self.row(p)
        for t, lbl in (("LT", "Gatilho LT"), ("RT", "Gatilho RT")):
            c = self.card(cols, _(lbl), side="left")
            v = self.v["triggers"][t]
            self.slider(c, _("Início (zona morta)"), v["dz0"], 0, 50, pct)
            self.slider(c, _("Fim (pressão total)"), v["dz1"], 50, 100, pct)
            self.toggle(c, _("Gatilho rápido (hair trigger)"), v["hair"])
            self.chips(c, v["hair_mode"], [(1, _("Adaptativo")), (2, _("Fixo"))], 2)
            self.slider(c, _("Faixa: início"), v["hair_start"], 1, 99, pct)
            self.slider(c, _("Faixa: fim"), v["hair_end"], 2, 100, pct)

    def _p_rumble(self, p):
        level = lambda v: f"{MOTOR_LEVELS[v]}%"
        cols = self.row(p)
        c = self.card(cols, _("Motores das empunhaduras"), side="left")
        self.slider(c, _("Motor esquerdo"), self.v["motors"]["left"], 0, 4, level)
        self.slider(c, _("Motor direito"), self.v["motors"]["right"], 0, 4, level)
        c = self.card(cols, _("Motores dos gatilhos"), side="left")
        self.slider(c, _("Gatilho LT"), self.v["motors"]["lt"], 0, 4, level)
        self.slider(c, _("Gatilho RT"), self.v["motors"]["rt"], 0, 4, level)
        c = self.card(p, _("Teste"))
        self.button(c, _("Vibrar por 1 segundo"), self.test_rumble).pack(anchor="w")

    def _p_gyro(self, p):
        cols = self.row(p)
        for key, lbl in MOTION:
            c = self.card(cols, _(lbl), side="left")
            v = self.v["gyro"][key]
            self.label(c, _("Ativação"))
            self.chips(c, v["activation"], ACTIVATION, 2)
            self.label(c, _("Botão de ativação"))
            self.chips(c, v["key"], [(k, k) for k in GYRO_KEYS], 4)
            self.label(c, _("Movimento vira"))
            self.chips(c, v["target"], OUTPUTS, 3)
            self.slider(c, _("Zona morta"), v["dz0"], 0, 50, lambda x: f"{x}%")
            self.slider(c, _("Proporção X/Y"), v["ratio"], 0, 100, lambda x: f"{x}")
            self.toggle(c, _("Inverter eixo X"), v["inv_x"])
            self.toggle(c, _("Inverter eixo Y"), v["inv_y"])
        for key, __ in MOTION:          # like the app: only one gyro function can be active at a time
            other = next(k for k, __ in MOTION if k != key)
            self.v["gyro"][key]["activation"].trace_add(
                "write", lambda *_, k=key, o=other: self.v["gyro"][k]["activation"].get() > 0
                and self.v["gyro"][o]["activation"].get() > 0 and self.v["gyro"][o]["activation"].set(0))

    def _p_leds(self, p):
        s, lv = self.s, self.v["light"]
        left = tk.Frame(p, bg=BG)
        left.pack(side="left", fill="y", padx=(0, int(16 * s)))
        cv = self.drawing(left, "leds")[0]
        cv.pack(pady=int(10 * s))
        self.leds_hint = tk.Label(left, bg=BG, fg=MUTED, font=theme.font(9), justify="left")
        self.leds_hint.pack(anchor="w", pady=(0, int(6 * s)))
        right = tk.Frame(p, bg=BG)
        right.pack(side="left", fill="both", expand=True)
        c = self.card(right, _("Animação"))
        self.chips(c, lv["anim"], [(i, _("Animação {}").format(i + 1)) for i in range(4)], 4)
        self.label(c, _("Efeitos prontos"))
        self.chips(c, self.preset_choice, PRESETS, 6)
        r = self.row(c)
        self.frame_bar = tk.Frame(r, bg=TILE)
        self.frame_bar.pack(side="left", fill="x", expand=True, pady=int(6 * s))
        for text, step in (("+", 1), ("−", -1)):
            Pill(r, text, s, cmd=lambda st=step: self.add_frame(st), font=theme.font(10, "bold"), padx=12,
                 pady=4).pack(side="right", padx=int(2 * s))
        c = self.card(right, _("Cor"))
        grid = tk.Frame(c, bg=TILE)
        grid.pack(fill="x")
        self.zone_cells = {}
        for i, (key, label) in enumerate(ZONES + [("all", "Todas")]):
            cell = Pill(grid, _(label), s, cmd=lambda k=key: self.pick_zone(k), font=theme.font(9), radius=10,
                        padx=10, pady=7, dot=True)
            cell.grid(row=i // 3, column=i % 3, sticky="ew", padx=int(3 * s), pady=int(3 * s))
            self.zone_cells[key] = cell
        for col in range(3):
            grid.columnconfigure(col, weight=1)
        self.picker = ColorPicker(c, s, self.on_pick)
        self.picker.pack(anchor="w", pady=(int(8 * s), 0))
        c = self.card(left, _("Brilho e velocidade"))      # under the drawing: the right column is full
        self.slider(c, _("Brilho"), lv["brightness"], 0, 100, lambda x: f"{x}%")
        self.slider(c, _("Velocidade"), lv["speed"], 0, light.MAX_SPEED)

    def _p_profile(self, p):
        s = self.s
        c = self.card(p, _("Perfil selecionado"))
        r = self.row(c)
        tk.Label(r, text=_("Nome"), bg=TILE, fg=MUTED, font=theme.font(9)).pack(side="left", padx=(0, int(10 * s)))
        field(r, self.v["name"], 24, theme.font(10), s).master.pack(side="left")
        o = self.v["opts"]
        self.toggle(c, _("Travar diagonais do D-pad"), o["dpad_diagonal_lock"])
        self.toggle(c, _("Trocar A/B e X/Y no modo XInput"), o["xinput_abxy_swap"])
        self.toggle(c, _("Trocar A/B e X/Y no modo Switch"), o["switch_abxy_swap"])
        self.button(c, _("Restaurar padrões deste perfil"), self.reset_profile).pack(anchor="w", pady=(int(10 * s), 0))
        c = self.card(p, _("Controle"))
        self.info_label = tk.Label(c, bg=TILE, fg=MUTED, font=theme.font(9), justify="left")
        self.info_label.pack(anchor="w")
        self.label(c, _("Desligar as luzes sem uso após"))     # lighting record settings, shared by all profiles
        self.chips(c, self.v["light"]["standby"], STANDBY, 5)
        self.toggle(c, _("Acordar ao levantar o controle"), self.v["light"]["raise_to_wake"])
        self.label(c, _("Cor do desenho"))
        self.chips(c, self.skin_choice, [(k, v["name"]) for k, v in SKINS.items()], 3)
        self.label(c, _("Idioma da interface"))
        self.chips(c, self.lang_choice, list(LANGS.items()), 3)

    # ------------------------------------------------------------ navigation
    def show(self, name):
        for page in self.pages.values():
            page.pack_forget()
        self.pages[name].pack(fill="both", expand=True)
        if (name == "leds") != (self.page == "leds"):
            self.preview_frame(name == "leds")
        self.page = name

    def refresh_profiles(self):
        """Profile chips (● = active on the controller) and the home subtitle."""
        for j, b in enumerate(self.profile_btns, start=1):
            on = j == self.active
            b.set(text=_("Perfil {}").format(j) + ("  ●" if on else ""), fill=TILE if on else BG, fg=ACCENT if on else MUTED)
        self.home_sub.configure(text="" if self.active is None else _("Perfil ativo no controle: {}").format(self.active))
