"""Mixin: device I/O on a worker thread — initial read, profile switching, auto-save, polling, rumble, backups."""
import threading
import time
from tkinter import filedialog

from .. import cli, device, light, profile
from .. import protocol as p
from . import dialogs, theme
from .i18n import _
from .theme import ACCENT, BG, DANGER, MUTED

WIRELESS = (0x102A, 0x100B)     # 2.4G PIDs (protocol.PIDS): Wi-Fi icon; the cable gets a plug


def explain(error):
    """Clear, translated text for the errors a user can fix; anything else keeps its own message."""
    if isinstance(error, device.NotFound):
        return _("Controle GameSir Cyclone 2 não encontrado. Conecte-o com o cabo ou o dongle 2.4G.")
    if isinstance(error, device.NoAnswer):
        return _("O controle não respondeu. Verifique se ele está ligado e conectado (cabo ou dongle 2.4G) e tente de novo.")
    if isinstance(error, device.PermissionDenied):
        return _("Sem permissão para acessar o controle ({}). Instale a regra udev (veja o README).").format(error.path)
    return str(error) or error.__class__.__name__


class DeviceSync:
    # ------------------------------------------------------------ status line / connection pill
    def set_status(self, text, error=False):
        self.status.configure(text=text, fg=DANGER if error else MUTED)

    def set_connected(self, state):
        """Connection badge, as in the 8BitDo app: link icon (Wi-Fi through the 2.4G dongle, a plug on the cable) and
        battery; the firmware goes to the footer's corner. ``state``: ``(pid, firmware, battery %, charging)`` when
        connected (battery may be ``None``), ``None`` when the controller does not answer (grey icon with a red X),
        ``False`` while still looking (grey Wi-Fi)."""
        c, s = self.pill, self.s
        c.delete("all")
        col, w = ACCENT if state else MUTED, max(1, round(2 * s))
        if state and state[0] not in WIRELESS:                 # plug: cable, body, two prongs
            c.create_line(2 * s, 12 * s, 8 * s, 12 * s, fill=col, width=w, capstyle="round")
            c.create_rectangle(8 * s, 6 * s, 16 * s, 18 * s, fill=col, outline="")
            for y in (9, 15):
                c.create_line(16 * s, y * s, 21 * s, y * s, fill=col, width=w, capstyle="round")
        else:                                                  # Wi-Fi: three arcs over a dot
            x, y = 11 * s, 17 * s
            for r in (5, 9.5, 14):
                c.create_arc(x - r * s, y - r * s, x + r * s, y + r * s, start=50, extent=80, style="arc", outline=col,
                             width=w)
            c.create_oval(x - 2 * s, y - 2 * s, x + 2 * s, y + 2 * s, fill=col, outline="")
        if state is None:                                      # red X over the bottom-right of the icon
            c.create_line(15 * s, 10 * s, 22 * s, 17 * s, fill=DANGER, width=w, capstyle="round")
            c.create_line(15 * s, 17 * s, 22 * s, 10 * s, fill=DANGER, width=w, capstyle="round")
        self.fw_label.configure(text=f"firmware {state[1]}" if state else "")
        if state and state[2] is not None:                     # battery outline, fill to the level, then the %
            battery, px, bw, bh, top = state[2], 32 * s, 22 * s, 11 * s, 6 * s
            c.create_rectangle(px, top, px + bw, top + bh, outline=col, width=max(1, round(1.5 * s)))
            c.create_rectangle(px + bw, top + 3 * s, px + bw + 2.5 * s, top + bh - 3 * s, fill=col, outline="")
            level = min(max(battery, 0), 100) / 100
            if level:
                c.create_rectangle(px + 2 * s, top + 2 * s, px + 2 * s + (bw - 4 * s) * level, top + bh - 2 * s,
                                   fill=DANGER if battery <= 15 else col, outline="")
            if state[3]:                                       # charging: a bolt across the battery
                bx, by = px + bw / 2, top + bh / 2
                bolt = (1.5, -6, -3, 1, 0, 1, -1.5, 6, 3, -1, 0, -1)
                c.create_polygon([(by if i % 2 else bx) + v * s for i, v in enumerate(bolt)], fill=BG, outline=col,
                                 width=1, tags="charging")
            c.create_text(px + bw + 6 * s, 11.5 * s, text=f"{battery}%", anchor="w", fill=col, font=theme.font(9),
                          tags="battery")
        c.configure(width=c.bbox("all")[2] + 2)

    # ------------------------------------------------------------ worker
    def run(self, label, job, done, quiet=False):
        """Run ``job(dev)`` on a worker thread; ``done(result)`` runs on the Tk thread.

        ``quiet`` (background polling): no status text and no error dialog, only the connection pill.
        """
        if self.busy:
            return
        self.busy = True
        if not quiet:
            self.set_status(label)

        def work():
            dev = None
            try:
                dev = device.Device()
                res = job(dev)
                cb = lambda: done(res)
            except BaseException as e:     # Device uses sys.exit for user-facing errors
                msg = explain(e)
                if quiet:
                    cb = lambda: self.set_connected(None)
                else:
                    cb = lambda: (self.set_status(msg, True), self.set_connected(None),
                                  dialogs.showerror(_("Erro"), msg, parent=self))
            finally:
                if dev:
                    dev.close()
            # idle first: ``done`` may start the next job (restore re-reads the controller)
            self.after(0, lambda: (self._idle(), cb()))
        threading.Thread(target=work, daemon=True).start()

    def _idle(self):
        self.busy = False

    # ------------------------------------------------------------ reading
    def read_device(self):
        """Read the active profile and the lighting from the controller and show them."""
        def job(dev):
            n = dev.current_profile()
            return dev.path, dev.pid, dev.firmware(), n, dev.read_profile(n), dev.read_profile(p.LIGHTS), dev.state()

        def done(r):
            path, pid, (fw, dongle), n, data, ldata, st = r
            self.show_profile(n, data)
            self.lbase, self.lights = ldata, light.decode(ldata)
            self.conn = (pid, fw, st and st["battery"], st and st["charging"])
            self.set_connected(self.conn)
            battery = "\n" + _("Bateria: {}%").format(st["battery"]) if st else ""
            self.info_label.configure(text=_("Dispositivo: {}\nFirmware: {}").format(path, fw) + (f" · dongle {dongle}" if dongle else "")
                                      + battery)
            self.load()
            self.set_status(_("Configuração lida do controle. As mudanças são salvas automaticamente."))
        self.run(_("Lendo do controle…"), job, done)

    def show_profile(self, n, data):
        self.active, self.base, self.doc = n, data, profile.decode(data)
        self.refresh_profiles()

    def select_profile(self, n):
        """Make profile ``n`` active on the controller (as the app does) and edit it; pending edits of the
        current profile are saved first, in the same job."""
        if self.doc is None or n == self.active or self.busy:
            return
        if self._save_job:
            self.after_cancel(self._save_job)
            self._save_job = None
        self.gather()
        pending = self._pending()

        def job(dev):
            self._write(dev, *pending)
            dev.switch_profile(n)
            return dev.read_profile(n)

        def done(data):
            self._saved(*pending)
            self.show_profile(n, data)
            self.load()
            self.set_status(_("Perfil {} ativo.").format(n))
        self.run(_("Trocando para o perfil {}…").format(n), job, done)

    # ------------------------------------------------------------ auto-save
    def changed(self, var=None):
        """A setting changed: save shortly (debounced), like the app's immediate writes."""
        if self._loading or self.doc is None:
            return
        if self._save_job:
            self.after_cancel(self._save_job)
        self._save_job = self.after(theme.AUTOSAVE_MS, self.autosave)
        self.set_status(_("Alterações pendentes…"))

    def _pending(self):
        """What to write: ``(profile number, new bytes, changed span, new lighting bytes, its span)``."""
        new = profile.encode(self.doc, self.base)
        lnew = light.encode(self.lights, self.lbase)
        return self.active, new, profile.changed_span(self.base, new), lnew, profile.changed_span(self.lbase, lnew)

    @staticmethod
    def _write(dev, n, new, span, lnew, lspan):
        for rec, data, sp in ((n, new, span), (p.LIGHTS, lnew, lspan)):
            if sp:
                dev.write_profile(rec, data, *sp)
                if dev.read_profile(rec)[sp[0]:sp[1]] != data[sp[0]:sp[1]]:
                    raise IOError(_("verificação falhou: o controle não guardou o que foi enviado"))

    def _saved(self, n, new, span, lnew, lspan):
        self.base, self.lbase = new, lnew
        size = sum(sp[1] - sp[0] for sp in (span, lspan) if sp)
        if size:
            self.set_status(_("✓ Salvo no controle ({} bytes).").format(size))

    def autosave(self):
        """Write only the changed byte ranges of the profile and the lighting, then verify them."""
        self._save_job = None
        if self.busy:
            self._save_job = self.after(300, self.autosave)
            return
        self.gather()
        pending = self._pending()
        if not pending[2] and not pending[4]:
            self.set_status("")
            return
        self.run(_("Salvando no controle…"), lambda dev: self._write(dev, *pending), lambda _: self._saved(*pending))

    # ------------------------------------------------------------ live state
    def poll(self):
        """Follow the active profile (it can also be changed on the controller itself)."""
        if self.doc is not None and not self.busy and self._save_job is None:
            def job(dev):
                n = dev.current_profile()
                return n, (dev.read_profile(n) if n != self.active else None)

            def done(r):
                n, data = r
                if self.conn:
                    if self.pad.get("battery") is not None:          # live battery from the state stream
                        self.conn = self.conn[:2] + (self.pad["battery"], self.pad["charging"])
                    self.set_connected(self.conn)          # recover the badge after a transient error
                if data is not None:
                    self.show_profile(n, data)
                    self.load()
                    self.set_status(_("O controle mudou para o perfil {}.").format(n))
            self.run("", job, done, quiet=True)
        self.after(theme.POLL_MS, self.poll)

    def test_rumble(self):
        def job(dev):
            dev.vibrate(160, 160)
            time.sleep(1)
            dev.vibrate(0, 0)
        self.run(_("Vibrando…"), job, lambda r: self.set_status(_("✓ Teste de vibração concluído.")))

    # ------------------------------------------------------------ backups
    def backup(self):
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".bin",
                                            initialfile=f"cyclone2-backup-{time.strftime('%Y%m%d-%H%M')}.bin")
        if path:
            def job(dev):
                with open(path, "wb") as f:
                    f.write(b"".join(dev.read_profile(n) for n in cli.RECORDS))
            self.run(_("Fazendo backup…"), job, lambda r: self.set_status(_("Backup salvo em {}").format(path)))

    def restore(self):
        path = filedialog.askopenfilename(parent=self, filetypes=[("Backup", "*.bin")])
        if not path:
            return
        with open(path, "rb") as f:
            data = f.read()
        if len(data) != cli.BACKUP_SIZE:
            return dialogs.showerror(_("Erro"), _("Arquivo inválido ({} bytes, esperado {}).").format(
                len(data), cli.BACKUP_SIZE), parent=self)
        if not dialogs.askyesno(_("Restaurar"), _("Substituir todos os perfis e as luzes por este backup?"),
                                  parent=self):
            return

        def job(dev):
            off = 0
            for n in cli.RECORDS:
                rec = data[off:off + p.size_of(n)]
                off += len(rec)
                dev.write_profile(n, rec)
                if dev.read_profile(n) != rec:
                    raise IOError(_("verificação falhou"))

        def done(r):
            self.set_status(_("Backup restaurado e verificado."))
            self.read_device()
        self.run(_("Restaurando…"), job, done)
