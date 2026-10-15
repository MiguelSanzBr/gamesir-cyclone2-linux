"""Mixin: device I/O on a worker thread — initial read, profile switching, auto-save, polling, rumble, backups."""
import threading
import time
from tkinter import filedialog

from .. import cli, device, light, profile
from .. import protocol as p
from . import dialogs, theme
from .i18n import _
from .theme import ACCENT, DANGER, MUTED


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

    def set_connected(self, text):
        self.pill.configure(text=f"●  {text}" if text else "○  " + _("controle não encontrado"), fg=ACCENT if text else MUTED)

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
            self.conn_text = _("Conectado · {} · firmware {}").format(p.PIDS.get(pid, hex(pid)), fw)
            self.set_connected(self.conn_text)
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
                if self.conn_text:
                    self.set_connected(self.conn_text)     # recover the pill after a transient error
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
