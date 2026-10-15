"""Window frame drawn by the app: a dark title bar (drag, minimise, maximise, close) and resize edges.

The native title bar is removed (see :mod:`.x11`) and the window manager keeps doing the work: it moves and resizes
the window on request, so maximise, snap and the taskbar entry keep working. Where that is not possible, or with
``CYCLONE2_NATIVE_TITLEBAR=1``, :func:`install` does nothing and the native title bar stays.
"""
import os
import tkinter as tk

from . import theme
from .theme import BG, DANGER, LINE, MUTED, TILE
from .x11 import MOVE, X11

BAR = "#141414"
# resize handles: (direction of _NET_WM_MOVERESIZE, cursor, place options) as fractions of the window and pixels
EDGES = (
    (0, "top_left_corner", dict(relx=0, rely=0, anchor="nw", w=8, h=8)),
    (1, "top_side", dict(relx=0, rely=0, relwidth=1, anchor="nw", x=8, w=-16, h=4)),
    (2, "top_right_corner", dict(relx=1, rely=0, anchor="ne", w=8, h=8)),
    (3, "right_side", dict(relx=1, rely=0, relheight=1, anchor="ne", y=8, h=-16, w=4)),
    (4, "bottom_right_corner", dict(relx=1, rely=1, anchor="se", w=8, h=8)),
    (5, "bottom_side", dict(relx=0, rely=1, relwidth=1, anchor="sw", x=8, w=-16, h=4)),
    (6, "bottom_left_corner", dict(relx=0, rely=1, anchor="sw", w=8, h=8)),
    (7, "left_side", dict(relx=0, rely=0, relheight=1, anchor="nw", y=8, h=-16, w=4)),
)


def native():
    return bool(os.environ.get("CYCLONE2_NATIVE_TITLEBAR"))


def install(win, s, resizable=True, minimizable=True, maximizable=True, on_close=None):
    """Replace the native frame of toplevel ``win`` (title already set) by the dark one; call it before packing the
    content. Returns the title bar, or ``None`` when the native frame is kept."""
    x = None if native() else X11.of(win)
    if x is None:
        return None
    win.configure(highlightthickness=1, highlightbackground=LINE, highlightcolor=LINE)
    bar = tk.Frame(win, bg=BAR, height=int(34 * s))
    bar.pack(side="top", fill="x")
    bar.pack_propagate(False)
    title = tk.Label(bar, text=win.title(), bg=BAR, fg=MUTED, font=theme.font(9, "bold"))
    title.pack(side="left", padx=int(14 * s))
    _icon(bar, s, "close", DANGER, on_close or win.destroy).pack(side="right")
    if maximizable:
        _icon(bar, s, "maximize", TILE, lambda: toggle_maximize(win)).pack(side="right")
    if minimizable:
        _icon(bar, s, "minimize", TILE, win.iconify).pack(side="right")
    _drag(win, x, bar, title)
    if maximizable:
        for handle in (bar, title):
            handle.bind("<Double-Button-1>", lambda e: toggle_maximize(win))
    edges = _edges(win, x) if resizable else []
    _undecorate(win, x, edges)
    return bar


def _drag(win, x, *handles):
    """Hand the move over to the window manager once the mouse moves (at the press it would swallow a double click)."""
    armed = [False]

    def move(e):
        if armed[0]:
            armed[0] = False
            x.move_resize(win, MOVE, e.x_root, e.y_root)
    for h in handles:
        h.bind("<Button-1>", lambda e: armed.__setitem__(0, True))
        h.bind("<ButtonRelease-1>", lambda e: armed.__setitem__(0, False))
        h.bind("<B1-Motion>", move)


def _icon(bar, s, kind, hover, cmd):
    w, h = int(46 * s), int(34 * s)
    c = tk.Canvas(bar, width=w, height=h, bg=BAR, highlightthickness=0, cursor="hand2")
    x, y, r = w / 2, h / 2, 5 * s
    if kind == "close":
        c.create_line(x - r, y - r, x + r, y + r, fill=MUTED, width=1.5 * s)
        c.create_line(x - r, y + r, x + r, y - r, fill=MUTED, width=1.5 * s)
    elif kind == "maximize":
        c.create_rectangle(x - r, y - r, x + r, y + r, outline=MUTED, width=1.5 * s)
    else:
        c.create_line(x - r, y + r / 2, x + r, y + r / 2, fill=MUTED, width=1.5 * s)
    c.bind("<Enter>", lambda e: c.configure(bg=hover))
    c.bind("<Leave>", lambda e: c.configure(bg=BAR))
    c.bind("<Button-1>", lambda e: cmd())
    return c


def _edges(win, x):
    handles = []
    for direction, cursor, opts in EDGES:
        f = tk.Frame(win, bg=BG, cursor=cursor)
        f.bind("<Button-1>", lambda e, d=direction: x.move_resize(win, d, e.x_root, e.y_root))
        f.place(**{("width" if k == "w" else "height" if k == "h" else k): v for k, v in opts.items()})
        handles.append(f)
    return handles


def _undecorate(win, x, edges):
    """The server creates the managed window with the first idle cycle; the handles go above the content then."""
    if x.undecorate(win):
        for f in edges:
            tk.Misc.lift(f)
    else:
        win.after(20, lambda: _undecorate(win, x, edges))


def toggle_maximize(win):
    win.attributes("-zoomed", not win.attributes("-zoomed"))
