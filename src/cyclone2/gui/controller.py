"""Mixin: the controller drawing (skins, LED zones, callouts), its per-frame animation and section icons."""
import time
import tkinter.font as tkfont

from . import theme
from .drawing import gradient_fill, mix, rounded, rr_points, set_color, smooth_outline
from .geometry import (BEHIND, BODY, CALLOUTS, DPAD_CENTER, DPAD_RING, HEIGHT, HOME_OFFSET, PARTS, PLAYER_COLORS,
                       PLAYER_LEDS, ROLES, STICK_WELLS, TOP, WIDTH, ZONE_SHAPES)
from .i18n import _
from .theme import ACCENT, BG, BODY_FILL, FG, SEL_FILL, SKINS
from .widgets import hand

SECTION_TARGETS = ("sticks", "leds")      # callout targets that open a page instead of selecting a button


class ControllerView:
    """Needs from the App: ``s``, ``skin``, ``ctrl``, ``zone_items``, ``_imgs``, ``pad``, ``pad_down``,
    ``press_t``, ``sel_btn``, ``_remapped``, ``lights``, ``active``, ``v`` and the ``select_button``/``show``/
    ``pick_zone``/``led_colors`` methods."""

    # ------------------------------------------------------------ drawing
    def draw_controller(self, c, mode, ox=0):
        """Draw the controller on canvas ``c``.

        mode: ``"home"`` (click opens the button page, adds callouts and a glow), ``"map"`` (click selects a
        button) or ``"leds"`` (LED zones are clickable colour targets). ``ox`` shifts the drawing right.
        """
        s, sk = self.s, SKINS[self.skin]
        w = max(1, round(1.5 * s))
        P = lambda *xy: [(v + (ox if i % 2 == 0 else TOP)) * s for i, v in enumerate(xy)]
        body = P(*[v for pt in BODY for v in pt])
        if mode == "home":                                  # soft glow under the controller
            for k in range(10):
                t = k / 9
                rx, ry = 240 - 140 * t, 26 - 16 * t
                c.create_oval(P(221 - rx, 296 - ry, 221 + rx, 296 + ry), outline="", fill=mix(BG, theme.GLOW, .15 + .55 * t))
        c.create_polygon([v + (5 if i % 2 else 0) * s for i, v in enumerate(body)], smooth=True,
                         fill=mix(BG, "#000000", .45), outline="")
        parts = {}

        def make(name):
            shape, xy, label = PARTS[name]
            tag = f"b:{name}"
            base = sk[ROLES.get(name, "btn")]
            pts = None
            if shape == "circle":
                x, y, r = xy
                box = P(x - r, y - r, x + r, y + r)
                glow = c.create_oval(box, outline="", width=max(2, round(2 * s)), state="hidden")
                part = c.create_oval(box, fill=base[0], outline=base[1], width=w * (2 if name == "Home" else 1), tags=tag)
                cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
            elif shape == "poly":
                outline, (lx, ly) = xy
                pts = P(*[v for pt in outline for v in pt])
                box = (min(pts[::2]), min(pts[1::2]), max(pts[::2]), max(pts[1::2]))
                glow = c.create_polygon(pts, smooth=True, fill="", outline="", width=max(2, round(2 * s)), state="hidden")
                part = c.create_polygon(pts, smooth=True, fill=base[0], outline=base[1], width=w, tags=tag)
                cx, cy = (lx + ox) * s, (ly + TOP) * s
            else:
                box = P(*xy)
                glow = c.create_polygon(rr_points(*box, 6 * s), smooth=True, fill="", outline="",
                                        width=max(2, round(2 * s)), state="hidden")
                rad = min(4 * s if shape == "rect" else 8 * s, (box[3] - box[1]) / 2)
                part = rounded(c, *box, rad, fill=base[0], outline=base[1], width=w, tags=tag)
                cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
            extra = [c.create_oval(cx - 12 * s, cy - 12 * s, cx + 12 * s, cy + 12 * s, outline=base[1], tags=tag),
                     c.create_arc(cx - 20 * s, cy - 20 * s, cx + 20 * s, cy + 20 * s, start=100, extent=80,
                                  style="arc", outline=mix(base[0], "#ffffff", .25), width=2 * s, tags=tag)] \
                if name in ("LS", "RS") else []
            if name == "Home":                              # stylised emblem
                extra.append(c.create_oval(cx - 7 * s, cy - 7 * s, cx + 7 * s, cy + 7 * s, fill=mix(base[0], "#ffffff", .5),
                                           outline="", tags=tag))
            text = c.create_text(cx, cy, text=label, fill=base[2], font=theme.font(7, "bold"), tags=tag) if label else None
            bx, by = (cx + 14 * s, cy - 6 * s) if shape == "poly" else (box[2], box[1])
            badge = c.create_oval(bx - 3 * s, by - 3 * s, bx + 3 * s, by + 3 * s, fill=ACCENT, outline=BODY_FILL, state="hidden")
            parts[name] = dict(body=part, text=text, glow=glow, badge=badge, extra=extra, box=box, shape=shape,
                               off=(0.0, 0.0), st=None, glowing=False, base=base, pts=pts)
            if mode == "map":
                c.tag_bind(tag, "<Button-1>", lambda e, n=name: (self.flash(n), self.select_button(n)))
                hand(c, tag)
            elif mode == "home":
                c.tag_bind(tag, "<Button-1>", lambda e, n=name: (self.flash(n), self.select_button(n), self.show("buttons")))
                hand(c, tag)

        for name in BEHIND:
            make(name)
        self._imgs[c] = gradient_fill(c, smooth_outline([(x * s, (y + TOP) * s) for x, y in BODY]),
                                      int(WIDTH * s), int((HEIGHT + TOP) * s), sk["body"])
        c.create_image(ox * s, 0, image=self._imgs[c], anchor="nw")
        c.create_polygon(body, smooth=True, fill="", outline=sk["line"], width=max(1, round(2 * s)))
        pw = max(1, round(1.2 * s))
        for line in (((176, 12), (198, 36), (244, 36), (266, 12)), ((140, 66), (186, 80), (256, 80), (302, 66)),
                     ((186, 80), (166, 112)), ((256, 80), (276, 112))):        # face plate seams
            c.create_line(P(*[v for pt in line for v in pt]), fill=sk["plate"], width=pw)
        for x, y, r in STICK_WELLS.values():
            c.create_oval(P(x - r, y - r, x + r, y + r), fill=sk["well"], outline=sk["plate"], width=pw)
        dx0, dy0 = DPAD_CENTER
        c.create_oval(P(dx0 - DPAD_RING, dy0 - DPAD_RING, dx0 + DPAD_RING, dy0 + DPAD_RING), fill=sk["well"],
                      outline=sk["plate"], width=pw)
        rounded(c, *P(dx0 - 11, dy0 - 11, dx0 + 11, dy0 + 11), 5 * s, fill=sk["dpad"][0], outline="")   # d-pad hub
        self.player_items[c] = [c.create_line(P(x - 5, y, x + 5, y), fill=sk["led_off"], width=3 * s, capstyle="round")
                                for x, y in PLAYER_LEDS]
        zones = {}
        for zone in sk["zones"]:
            kind, geo = ZONE_SHAPES[zone]
            if kind == "bar":
                pts = P(*[v for pt in geo for v in pt])
                halo = c.create_line(pts, smooth=True, fill=sk["led_off"], width=12 * s, capstyle="round")
                item = c.create_line(pts, smooth=True, fill=sk["led_off"], width=5 * s, capstyle="round")
            else:
                x, y, r = geo
                ring = lambda width: c.create_arc(P(x - r, y - r, x + r, y + r), start=0, extent=359.9, style="arc",
                                                  outline=sk["led_off"], width=width)       # arcs: coloured by outline
                halo, item = ring(7 * s), ring(3 * s)
            if mode == "leds":
                for i in (halo, item):
                    c.tag_bind(i, "<Button-1>", lambda e, z=zone: self.pick_zone(z))
                    hand(c, i)
            zones[zone] = (item, halo)
        self.zone_items[c] = zones
        for name in PARTS:
            if name not in BEHIND:
                make(name)
        c.create_oval(P(dx0 - 4, dy0 - 4, dx0 + 4, dy0 + 4), fill="#a6a6ae", outline="#d8d8de")   # metal centre
        arrows = {(0, -1): "Up", (0, 1): "Down", (-1, 0): "Left", (1, 0): "Right"}
        for (dx, dy), name in arrows.items():
            x, y = dx0 + 21 * dx, dy0 + 21 * dy
            c.create_polygon(P(x + 3 * dx, y + 3 * dy, x - 3 * dy - 2 * dx, y - 3 * dx - 2 * dy,
                               x + 3 * dy - 2 * dx, y + 3 * dx - 2 * dy), fill="#77777e", outline="", tags=f"b:{name}")
        if mode == "home":
            self.callouts(c, ox)
        if mode == "leds":
            for item, halo in zones.values():
                c.tag_raise(halo)
                c.tag_raise(item)
        self.ctrl[c] = (parts, mode)
        return parts

    def callouts(self, c, ox):
        """Labels around the home drawing, linked to their part; clicking one opens its page."""
        s = self.s
        for text, side, y, (tx, ty), target in CALLOUTS:
            label = _(text)                                  # the tag below keeps the Portuguese text
            f = tkfont.Font(root=c, font=theme.font(9, "bold"))
            w, h = f.measure(label) / s + 26, 22
            x1 = 6 if side == "l" else 2 * ox + WIDTH - 6 - w
            x2, edge = x1 + w, (x1 + w if side == "l" else x1)
            y, ty = y + TOP, ty + TOP
            tag = "co:" + text.replace(" ", "_")             # Tk splits a tag string at spaces
            rounded(c, x1 * s, (y - h / 2) * s, x2 * s, (y + h / 2) * s, h / 2 * s, fill=theme.CALLOUT_FILL,
                    outline=theme.CALLOUT_LINE, width=max(1, round(1.5 * s)), tags=tag)
            c.create_text((x1 + w / 2) * s, y * s, text=label, fill=FG, font=theme.font(9, "bold"), tags=tag)
            px, py = (tx + ox) * s, ty * s
            mx = (edge + (14 if side == "l" else -14)) * s
            c.create_line(edge * s, y * s, mx, y * s, px, py, fill=theme.CALLOUT_LINE, width=max(1, round(1.5 * s)))
            c.create_oval(px - 3 * s, py - 3 * s, px + 3 * s, py + 3 * s, fill=theme.CALLOUT_DOT, outline="")
            page = target if target in SECTION_TARGETS else "buttons"
            c.tag_bind(tag, "<Button-1>", lambda e, t=target, p=page: (p == "buttons" and self.select_button(t), self.show(p)))
            hand(c, tag)

    def apply_skin(self, name):
        """Redraw every controller drawing with another skin."""
        self.skin = name
        for c, (parts, mode) in list(self.ctrl.items()):
            c.delete("all")
            new = self.draw_controller(c, mode, ox=HOME_OFFSET if mode == "home" else 0)
            if mode == "map":
                self.map_items = new
            elif mode == "home":
                self.home_items = new
        self.refresh_mapping()

    def icon(self, c, kind, x, y):
        """Line icon of a section tile."""
        s, w = self.s, max(1, round(1.6 * self.s))
        P = lambda *xy: [v * s for v in xy]
        if kind == "buttons":
            for dx, dy in ((0, -9), (0, 9), (-9, 0), (9, 0)):
                c.create_oval(P(x + dx - 4, y + dy - 4, x + dx + 4, y + dy + 4), outline=FG, width=w)
        elif kind == "sticks":
            for r in (13, 7, 2):
                c.create_oval(P(x - r, y - r, x + r, y + r), outline=FG, width=w)
        elif kind == "triggers":
            rounded(c, *P(x - 9, y - 13, x + 9, y + 13), 8 * s, fill="", outline=FG, width=w)
            c.create_line(P(x - 9, y - 2, x + 9, y - 2), fill=FG, width=w)
        elif kind == "rumble":
            for dx in (-10, -3, 4, 11):
                c.create_line(P(x + dx, y - 10, x + dx - 3, y - 4, x + dx + 3, y + 4, x + dx, y + 10), fill=FG, width=w, smooth=True)
        elif kind == "gyro":
            c.create_oval(P(x - 14, y - 6, x + 14, y + 6), outline=FG, width=w)
            c.create_oval(P(x - 6, y - 14, x + 6, y + 14), outline=FG, width=w)
            c.create_oval(P(x - 2, y - 2, x + 2, y + 2), fill=FG, outline="")
        elif kind == "leds":
            c.create_oval(P(x - 6, y - 6, x + 6, y + 6), outline=FG, width=w)
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0), (.7, .7), (-.7, .7), (.7, -.7), (-.7, -.7)):
                c.create_line(P(x + dx * 9, y + dy * 9, x + dx * 13, y + dy * 13), fill=FG, width=w)
        else:  # profile
            c.create_oval(P(x - 5, y - 13, x + 5, y - 3), outline=FG, width=w)
            c.create_arc(P(x - 11, y - 1, x + 11, y + 21), start=0, extent=180, style="arc", outline=FG, width=w)

    # ------------------------------------------------------------ live state
    def flash(self, name):
        """Ripple on a button (mouse click feedback; real presses come from the input reader)."""
        self.press_t[name] = time.time()

    def trigger_level(self, name):
        """0..1 pressure of LT/RT from the controller's analog trigger values."""
        key = {"LT": "lt", "RT": "rt"}.get(name)
        return None if key is None else self.pad.get(key, 0) / 255

    def style(self, c, parts, mode, now):
        """Per-frame look of each part: pressed > trigger pressure > selected > normal, plus ripple and stick motion."""
        s = self.s
        for name, p in parts.items():
            level = self.trigger_level(name)
            if name in self.pad_down:
                st = (ACCENT, ACCENT, BG)
            elif level and level > .02:
                st = (mix(p["base"][0], ACCENT, level), ACCENT, p["base"][2])
            elif mode == "map" and name == self.sel_btn:
                st = (SEL_FILL, ACCENT, ACCENT)
            else:
                st = p["base"]
            if st != p["st"]:
                p["st"] = st
                c.itemconfigure(p["body"], fill=st[0], outline=st[1])
                if p["text"]:
                    c.itemconfigure(p["text"], fill=st[2])
            c.itemconfigure(p["badge"], state="normal" if mode != "leds" and name in self._remapped else "hidden")
            t = now - self.press_t.get(name, -1e9)
            if t < theme.PULSE:
                k = t / theme.PULSE
                g = (2 + 9 * k) * s
                x1, y1, x2, y2 = p["box"]
                ox, oy = p["off"]
                box = (x1 - g + ox, y1 - g + oy, x2 + g + ox, y2 + g + oy)
                if p["shape"] == "poly":            # grow the outline around its centre
                    mx, my, f = (x1 + x2) / 2, (y1 + y2) / 2, 1 + g / max((x2 - x1) / 2, 1)
                    c.coords(p["glow"], *[(v - (mx if i % 2 == 0 else my)) * f + (mx if i % 2 == 0 else my)
                                          for i, v in enumerate(p["pts"])])
                else:
                    c.coords(p["glow"], *(box if p["shape"] == "circle" else rr_points(*box, 6 * s + g)))
                c.itemconfigure(p["glow"], outline=mix(ACCENT, BODY_FILL, k), state="normal")
                p["glowing"] = True
            elif p["glowing"]:
                c.itemconfigure(p["glow"], state="hidden")
                p["glowing"] = False
            if name in ("LS", "RS"):
                tx, ty = (v * 7 * s for v in self.pad.get("left" if name == "LS" else "right", (0, 0)))
                dx, dy = tx - p["off"][0], ty - p["off"][1]
                if abs(dx) + abs(dy) > .5:
                    for item in [p["body"], p["text"], p["badge"], *p["extra"]]:
                        if item:
                            c.move(item, dx, dy)
                    p["off"] = (tx, ty)

    def select_button(self, name):
        self.sel_btn = name
        self.map_choice.set(self.v["keys"][name].get())
        self.refresh_mapping()

    def refresh_mapping(self):
        """Badge every button with a custom function, turbo or toggle; update the side panel."""
        v = self.v
        self._remapped = {b for b in v["keys"] if v["keys"][b].get() or v["turbo"][b].get() or v["toggle"][b].get()}
        cur = v["keys"][self.sel_btn].get()
        self.map_title.configure(text=_("Botão {}").format(self.sel_btn))
        self.map_sub.configure(text=_("função atual: {}").format(
            cur.replace("+", " + ") if cur else _("padrão ({})").format(self.sel_btn)))
        now = time.time()
        for c, (parts, mode) in self.ctrl.items():
            self.style(c, parts, mode, now)

    def animate(self):
        """Live LED preview, profile indicator, button presses and stick motion on the visible drawing."""
        now = time.time()
        visible = {"home": "home", "buttons": "map", "leds": "leds"}.get(self.page)
        colors = self.led_colors(now) if self.lights else None
        sk = SKINS[self.skin]
        for c, (parts, mode) in self.ctrl.items():
            if mode != visible:
                continue
            self.style(c, parts, mode, now)
            for i, item in enumerate(self.player_items[c]):
                c.itemconfigure(item, fill=PLAYER_COLORS[i] if self.active == i + 1 else sk["led_off"])
            if colors:
                halo = mix(sk["body"][1], "#000000", .35)
                for zone, (item, glow) in self.zone_items[c].items():
                    set_color(c, item, colors[zone])
                    set_color(c, glow, mix(colors[zone], halo, .7))
        self.after(theme.FRAME_MS, self.animate)
