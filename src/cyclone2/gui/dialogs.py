"""Message boxes in the style of the window (``tkinter.messagebox`` would use the plain system look), with the same
frame as the main window."""
import tkinter as tk

from . import chrome, theme
from .i18n import _
from .theme import BG, FG
from .titlebar import dark_on_show
from .widgets import Pill


class Dialog(tk.Toplevel):
    """Modal box over ``parent``: a message and a row of buttons (``(label, value)``); ``result`` is the value of the
    button pressed (``False`` when closed with the title bar or Escape)."""

    def __init__(self, parent, title, message, buttons):
        super().__init__(parent, bg=BG)
        self.withdraw()
        self.title(title)
        self.result = False
        s = parent.s
        if not chrome.install(self, s, resizable=False, minimizable=False, maximizable=False, on_close=self.close):
            dark_on_show(self)
            self.resizable(False, False)
        tk.Label(self, text=message, bg=BG, fg=FG, font=theme.font(10), justify="left",
                 wraplength=int(420 * s)).pack(padx=int(28 * s), pady=int(24 * s))
        row = tk.Frame(self, bg=BG)
        row.pack(fill="x", padx=int(22 * s), pady=(0, int(18 * s)))
        for label, value in reversed(buttons):
            Pill(row, label, s, cmd=lambda v=value: self.close(v)).pack(side="right", padx=int(4 * s))
        self.bind("<Escape>", lambda e: self.close())
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_reqwidth()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_reqheight()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.transient(parent)
        self.deiconify()
        self.update_idletasks()
        self.wait_visibility()                  # a grab needs a mapped window
        self.grab_set()
        self.focus_set()

    def close(self, value=False):
        self.result = value
        self.destroy()


def _ask(parent, title, message, buttons):
    dialog = Dialog(parent, title, message, buttons)
    dialog.wait_window()
    return dialog.result


def showerror(title, message, parent):
    _ask(parent, title, message, [(_("Fechar"), True)])


def askyesno(title, message, parent):
    return _ask(parent, title, message, [(_("Não"), False), (_("Sim"), True)])
