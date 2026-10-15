"""sync mixin: worker thread, reading, profile switching, auto-save (verified, changed bytes only), polling,
rumble test, backup and restore - all against the in-process fake controller."""
import threading
import time

import pytest

from cyclone2 import cli, device, discovery, profile
from cyclone2 import protocol as p
from cyclone2.gui import sync, theme

from .conftest import BACKUP, badge, doc_of, lights_of, no_state, pump, record, written


REAL_STATE = device.Device.state


def saved(a):
    return "Salvo" in a.status.cget("text") and not a.busy


def test_set_status_and_connected(app):
    app.set_status("oops", True)
    assert app.status.cget("fg") == theme.DANGER and app.status.cget("text") == "oops"
    app.set_status("ok")
    assert app.status.cget("fg") == theme.MUTED
    c = app.pill
    arcs = lambda: {c.itemcget(i, "outline") for i in c.find_all() if c.type(i) == "arc"}
    fills = lambda: [c.itemcget(i, "fill") for i in c.find_all() if c.type(i) == "rectangle"]
    app.set_connected((0x100B, "3.5.6", 80, 0))                # 2.4G dongle: Wi-Fi, battery, firmware in the footer
    assert badge(app) == ("3.5.6", False, "wifi") and arcs() == {theme.ACCENT}
    assert c.itemcget(c.find_withtag("battery")[0], "text") == "80%" and not c.find_withtag("charging")
    app.set_connected((0x1053, "3.5.6", 80, 1))                # cable: a plug; charging: a bolt
    assert badge(app) == ("3.5.6", False, "plug") and c.find_withtag("charging")
    app.set_connected((0x1053, "3.5.6", 10, 0))                # low battery: red level
    assert theme.DANGER in fills()
    app.set_connected((0x1053, "3.5.6", 0, 0))                 # empty: outline and nub only (plus the plug body)
    assert len(fills()) == 3
    app.set_connected((0x1053, "3.5.6", None, None))           # battery unknown: icon and firmware only
    assert not c.find_withtag("battery") and badge(app) == ("3.5.6", False, "plug")
    app.set_connected(None)                                    # not answering: grey Wi-Fi with a red X
    assert badge(app) == (None, True, "wifi") and arcs() == {theme.MUTED}
    app.set_connected(False)                                   # still looking: grey, no X
    assert badge(app) == (None, False, "wifi")


# ---------------------------------------------------------------- run
def test_run_while_busy_is_ignored(app):
    gate = threading.Event()
    seen = []
    app.run("a", lambda d: gate.wait(5), lambda r: seen.append("a"))
    assert app.busy and app.status.cget("text") == "a"
    app.run("b", lambda d: seen.append("b"), lambda r: seen.append("b"))
    gate.set()
    pump(app)
    assert seen == ["a"]


def test_run_success_and_done_may_start_the_next_job(app):
    out = []
    app.run("lbl", lambda d: d.pid, lambda pid: (out.append(pid), app.run("next", lambda d: 7, out.append)))
    pump(app)
    pump(app)
    assert out == [0x1053, 7]


def test_run_no_device_systemexit(app, dlg, monkeypatch):
    monkeypatch.setattr(discovery, "find_devices", lambda: iter([]))
    app.run("lbl", lambda d: None, lambda r: pytest.fail("done"))
    pump(app)
    assert "não encontrado" in app.status.cget("text") and app.status.cget("fg") == theme.DANGER
    assert badge(app)[1] and dlg.errors and not app.busy


def test_run_explains_the_errors_a_user_can_fix(app, dlg, monkeypatch):
    def fail(error):
        def job(dev):
            raise error
        app.run("lbl", job, lambda r: pytest.fail("done"))
        pump(app)
        return app.status.cget("text")
    assert "não respondeu" in fail(device.NoAnswer("no answer to command 11 (controller busy or disconnected)"))
    assert "no answer" not in app.status.cget("text") and dlg.errors
    monkeypatch.setattr(device, "Device", lambda: (_ for _ in ()).throw(device.PermissionDenied("/dev/hidraw9")))
    app.run("lbl", lambda d: None, lambda r: pytest.fail("done"))
    pump(app)
    assert "Sem permissão" in app.status.cget("text") and "/dev/hidraw9" in app.status.cget("text")


def test_explain_is_translated(monkeypatch):
    from cyclone2.gui import i18n
    monkeypatch.setattr(i18n, "LANG", "fr")
    assert sync.explain(device.NoAnswer("x")).startswith("La manette n'a pas répondu")
    monkeypatch.setattr(i18n, "LANG", "en")
    assert sync.explain(device.NotFound("x")).startswith("GameSir Cyclone 2 not found. Plug it in")
    assert sync.explain(IOError("raw")) == "raw"


def test_run_job_error_with_empty_message(app, dlg):
    def job(dev):
        raise IOError()
    app.run("lbl", job, lambda r: pytest.fail("done"))
    pump(app)
    assert app.status.cget("text") == "OSError" and dlg.errors


def test_run_quiet_error_only_marks_the_pill(app, dlg, monkeypatch):
    monkeypatch.setattr(discovery, "find_devices", lambda: iter([]))
    app.set_status("marker")
    app.run("", lambda d: None, lambda r: pytest.fail("done"), quiet=True)
    pump(app)
    assert not dlg.errors and app.status.cget("text") == "marker" and badge(app)[1]


# ---------------------------------------------------------------- read_device
def test_read_device_fills_the_widgets_from_the_fixture(app, fake):
    d = doc_of(fake, 1)
    assert app.active == 1 and app.doc == d and app.base == record(fake, 1) and app.lbase == record(fake, p.LIGHTS)
    v = app.v
    assert v["name"].get() == d["name"] and v["keys"]["L4"].get() == "LS" and v["keys"]["R4"].get() == "RT"
    assert v["opts"]["xinput_abxy_swap"].get() is True and v["opts"]["dpad_diagonal_lock"].get() is False
    assert v["sticks"]["left"]["dz1"].get() == 100 and v["triggers"]["LT"]["dz0"].get() == 5
    assert v["triggers"]["LT"]["dz1"].get() == 95
    assert v["motors"]["left"].get() == 4 and v["motors"]["lt"].get() == 3             # 100% / 75% steps
    assert v["gyro"]["aim"]["activation"].get() == 1 and v["gyro"]["aim"]["key"].get() == "LT"
    assert v["gyro"]["aim"]["target"].get() == 2
    assert v["light"]["anim"].get() == 3 and v["light"]["standby"].get() == 5 and v["light"]["raise_to_wake"].get()
    assert v["light"]["brightness"].get() == 0 and v["light"]["speed"].get() == 10     # animation 4
    assert app.profile_btns[0].text == "Perfil 1  ●" and app.profile_btns[1].text == "Perfil 2"
    assert app.home_sub.cget("text") == "Perfil ativo no controle: 1"
    assert badge(app) == ("3.5.6", False, "plug") and app.conn[:2] == (0x1053, "3.5.6")
    assert "/dev/hidraw-fake" in app.info_label.cget("text") and "Firmware: 3.5.6" in app.info_label.cget("text")
    assert "Bateria" not in app.info_label.cget("text") and "dongle" not in app.info_label.cget("text")
    assert "salvas automaticamente" in app.status.cget("text") and app._save_job is None


def test_read_device_other_active_profile(mk, fake):
    a = mk(current=3)
    assert a.active == 3 and a.doc == doc_of(fake, 3) and a.profile_btns[2].text == "Perfil 3  ●"


def test_read_device_battery_dongle_and_unknown_pid(mk, fake, monkeypatch):
    fake.pid = 0x9999
    a = mk(read=False)
    monkeypatch.setattr(device.Device, "state", lambda self, timeout=0.5: {"battery": 64, "charging": 1})
    monkeypatch.setattr(device.Device, "firmware", lambda self: ("1.2.3", "4.5.6"))
    a.read_device()
    pump(a)
    assert "Bateria: 64%" in a.info_label.cget("text") and "dongle 4.5.6" in a.info_label.cget("text")
    assert a.conn == (0x9999, "1.2.3", 64, 1) and badge(a) == ("1.2.3", False, "plug")


def test_read_device_waits_for_the_state_report(mk, fake, monkeypatch):
    monkeypatch.setattr(device.Device, "state", REAL_STATE)          # mk stubbed it
    a = mk(read=False)
    a.set_status("")
    a.read_device()
    threading.Timer(0.15, lambda: fake.push(fake.state_report(battery=77))).start()
    pump(a)
    assert "Bateria: 77%" in a.info_label.cget("text")


def test_read_device_without_controller(app, dlg, monkeypatch):
    monkeypatch.setattr(discovery, "find_devices", lambda: iter([]))
    doc = app.doc
    app.read_device()
    pump(app)
    assert dlg.errors and badge(app)[1] and app.doc is doc


# ---------------------------------------------------------------- profile switching
def test_select_profile_ignored_without_doc_same_or_busy(app, fake):
    log = len(fake.log)
    app.select_profile(1)                                   # already active
    app.busy = True
    app.select_profile(2)
    app.busy = False
    doc, app.doc = app.doc, None
    app.select_profile(2)
    app.doc = doc
    assert len(fake.log) == log and fake.current == 1 and not app.busy


def test_select_profile_switches_the_controller_and_loads_it(app, fake):
    app.select_profile(2)
    assert app.busy and "Trocando para o perfil 2" in app.status.cget("text")
    pump(app)
    d2 = doc_of(fake, 2)
    assert fake.current == 2 and app.active == 2 and app.doc == d2 and app.base == record(fake, 2)
    assert app.status.cget("text") == "Perfil 2 ativo."
    assert app.v["triggers"]["LT"]["dz0"].get() == 5 and app.v["turbo"]["LT"].get() is True
    assert app.profile_btns[1].text == "Perfil 2  ●" and app.profile_btns[0].text == "Perfil 1"
    assert not written(fake, 1)                             # nothing was pending


def test_select_profile_saves_pending_edits_first(app, fake):
    app.v["name"].set("Antes")                              # debounced save pending
    assert app._save_job is not None
    app.select_profile(4)
    assert app._save_job is None
    pump(app)
    assert doc_of(fake, 1)["name"] == "Antes" and fake.current == 4 and app.active == 4
    assert "Salvo" not in app.status.cget("text")           # status shows the new profile, not the save
    first = [r for r in fake.log if r[1] in (p.WRITE, p.SWITCH)]
    assert first[0][1] == p.WRITE and first[-1][1] == p.SWITCH
    assert app.base == record(fake, 4)


# ---------------------------------------------------------------- auto-save
def test_changed_ignored_without_doc_or_while_loading(app):
    doc = app.doc
    app.doc = None
    app.v["name"].set("x")
    assert app._save_job is None
    app.doc = doc
    app._loading = True
    try:
        app.v["name"].set("y")
    finally:
        app._loading = False
    assert app._save_job is None


def test_changed_debounces(app):
    app.v["name"].set("um")
    first = app._save_job
    assert first and "pendentes" in app.status.cget("text")
    app.v["name"].set("dois")                               # reschedules: the old job is cancelled
    assert app._save_job != first and first not in app.tk.splitlist(app.tk.call("after", "info"))
    app.changed()                                           # also callable without a variable
    assert app._save_job


def test_autosave_writes_only_the_changed_bytes_and_verifies(app, fake, fast):
    before = record(fake, 1)
    app.v["opts"]["dpad_diagonal_lock"].set(True)
    pump(app, lambda: saved(app))
    assert written(fake, 1) == [(43, 44)] and not written(fake, p.LIGHTS)
    after = record(fake, 1)
    assert after[43] == 1 and after[:43] == before[:43] and after[44:] == before[44:]
    assert app.base == after and app._save_job is None and "(1 bytes)" in app.status.cget("text")
    assert fake.commands(p.READ)[-1][2] == 1                # read back for verification


def test_autosave_mapping_chip_turbo_and_toggle(app, fake, fast):
    app.select_button("B")
    app.map_choice.set("X")                                 # what the mapping chips do
    app.sel_turbo.set(True)
    app.sel_toggle.set(True)
    pump(app, lambda: saved(app))
    b = doc_of(fake, 1)["buttons"]["B"]
    assert b["map"] == ["X"] and b["turbo"] is True and b["toggle"] is True and b["turbo_speed"] == 1
    assert "B" in app._remapped and app.map_sub.cget("text") == "função atual: X"


def test_untouched_turbo_keeps_its_stored_speed(mk, fake, fast):
    a = mk(current=2)                                       # profile 2: LT/RT turbo on with speed 10
    assert a.v["turbo"]["LT"].get() is True
    a.v["keys"]["A"].set("B")                               # edit something else
    pump(a, lambda: saved(a))
    d = doc_of(fake, 2)
    assert d["buttons"]["LT"]["turbo"] is True and d["buttons"]["LT"]["turbo_speed"] == 10
    assert d["buttons"]["RT"]["turbo_speed"] == 10 and d["buttons"]["A"]["map"] == ["B"]
    a.v["turbo"]["LT"].set(False)                           # switching it off writes 0
    pump(a, lambda: "Salvo" in a.status.cget("text") and not a.busy and a.base == record(fake, 2))
    assert doc_of(fake, 2)["buttons"]["LT"]["turbo"] is False and doc_of(fake, 2)["buttons"]["LT"]["turbo_speed"] == 0


def test_autosave_dead_zone_rebuilds_the_curve(app, fake, fast):
    old = doc_of(fake, 1)["sticks"]["left"]
    pts = profile.curve_percent(old["curve"], old["deadzone"])
    assert min(x for x, _ in pts) < 20                      # a stored point lies below the new dead zone
    app.v["sticks"]["left"]["dz0"].set(20)
    pump(app, lambda: saved(app))
    st = doc_of(fake, 1)["sticks"]["left"]
    assert st["deadzone"][0] == 20 and st["deadzone_on"] is True
    clamped = [(max(x, 20), y) for x, y in pts]             # points cannot leave the dead zone range
    assert st["curve"] == profile.curve(st["deadzone"], clamped, old["curve"]["type"], old["curve"]["curvature"])
    assert st["curve"]["points"][1][0] == 0 and st["curve"] != old["curve"]


def test_autosave_lighting_changes_use_the_lighting_record(app, fake, fast):
    app.v["light"]["standby"].set(20)
    app.v["light"]["raise_to_wake"].set(False)
    app.v["light"]["brightness"].set(55)
    pump(app, lambda: saved(app))
    L = lights_of(fake)
    assert L["standby"] == 20 and L["raise_to_wake"] is False and L["animations"][3]["brightness"] == 55
    assert not written(fake, 1) and written(fake, p.LIGHTS) and app.lbase == record(fake, p.LIGHTS)


def test_autosave_profile_and_lighting_together(app, fake, fast):
    app.v["name"].set("Duplo")
    app.v["light"]["standby"].set(0)
    pump(app, lambda: saved(app))
    assert doc_of(fake, 1)["name"] == "Duplo" and lights_of(fake)["standby"] == 0
    assert written(fake, 1) and written(fake, p.LIGHTS)


def test_autosave_no_changes_clears_status(app, fake):
    app.set_status("Alterações pendentes…")
    app.autosave()
    assert app.status.cget("text") == "" and not app.busy and not fake.commands(p.WRITE)


def test_autosave_waits_while_busy(app, fake):
    app.v["name"].set("Espera")
    app.after_cancel(app._save_job)
    app.busy = True
    app.autosave()
    assert app._save_job is not None and not fake.commands(p.WRITE)
    app.busy = False
    app.after_cancel(app._save_job)
    app.autosave()
    pump(app, lambda: saved(app))
    assert doc_of(fake, 1)["name"] == "Espera"


def test_saved_without_changes_keeps_the_status(app):
    app.set_status("antes")
    app._saved(1, app.base, None, app.lbase, None)
    assert app.status.cget("text") == "antes"


def test_autosave_verify_failure(app, fake, dlg, fast):
    base = app.base
    fake.corrupt = True                                     # the controller stores something else
    app.v["name"].set("Falha")
    pump(app, lambda: bool(dlg.errors) and not app.busy)
    assert "verificação falhou" in app.status.cget("text") and app.status.cget("fg") == theme.DANGER
    assert app.base is base and badge(app)[1]


# ---------------------------------------------------------------- poll
def test_poll_follows_a_profile_change_made_on_the_controller(app, fake):
    fake.current = 3
    app.set_status("marker")
    app.poll()
    assert app.busy and app.status.cget("text") == "marker"     # quiet
    pump(app)
    assert app.active == 3 and app.doc == doc_of(fake, 3) and app.profile_btns[2].text == "Perfil 3  ●"
    assert app.status.cget("text") == "O controle mudou para o perfil 3."
    assert app.tk.splitlist(app.tk.call("after", "info"))       # poll re-arms itself
    log = len(fake.log)
    app.poll()                                                  # unchanged: the profile is not read again
    pump(app)
    assert not [r for r in fake.log[log:] if r[1] == p.READ]


def test_poll_skipped_without_doc_busy_or_pending_save(app, fake):
    log = len(fake.log)
    doc = app.doc
    app.doc = None
    app.poll()
    app.doc = doc
    app.busy = True
    app.poll()
    app.busy = False
    app._save_job = "pending"
    app.poll()
    app._save_job = None
    assert len(fake.log) == log and not app.busy


def test_poll_error_is_silent_but_marks_disconnected_then_recovers(app, dlg, monkeypatch):
    conn = app.conn
    with monkeypatch.context() as mp:
        mp.setattr(discovery, "find_devices", lambda: iter([]))
        app.poll()
        pump(app)
    assert not dlg.errors and badge(app)[1]
    app.pad = {"battery": 42, "charging": 1}                   # the state stream brings a newer battery level
    app.poll()                                                  # the controller is back: the badge recovers
    pump(app)
    assert app.conn == conn[:2] + (42, 1) and badge(app) == (conn[1], False, "plug")
    app.pad = {}
    app.conn = None                                             # never read successfully: nothing to restore
    app.set_connected(None)
    app.poll()
    pump(app)
    assert badge(app)[1]


# ---------------------------------------------------------------- rumble
def test_test_rumble_sends_vibrate_commands(app, fake, monkeypatch):
    real = time.sleep
    monkeypatch.setattr(sync.time, "sleep", lambda s: real(0.02) if s >= 1 else real(s))
    app.test_rumble()
    pump(app)
    deadline = time.time() + 2
    while len(fake.commands(p.VIBRATE)) < 2 and time.time() < deadline:
        real(0.005)
    vib = [tuple(r[2:6]) for r in fake.commands(p.VIBRATE)]
    assert vib == [(102, 85, 160, 160), (102, 85, 0, 0)]
    assert "vibração concluído" in app.status.cget("text")


# ---------------------------------------------------------------- backup / restore
def test_backup_cancel_and_save(app, fake, dlg, tmp_path):
    dlg.save = ""
    app.backup()
    assert not app.busy
    dlg.save = str(tmp_path / "b.bin")
    app.backup()
    pump(app)
    assert (tmp_path / "b.bin").read_bytes() == b"".join(record(fake, n) for n in cli.RECORDS) == BACKUP
    assert "Backup salvo" in app.status.cget("text")


def test_restore_cancel_wrong_size_and_refusal(app, fake, dlg, tmp_path):
    before = {n: record(fake, n) for n in cli.RECORDS}
    app.restore()                                           # cancelled dialog
    assert not dlg.errors and not dlg.asked
    bad = tmp_path / "bad.bin"
    bad.write_bytes(b"123")
    dlg.open = str(bad)
    app.restore()
    assert "Arquivo inválido (3 bytes" in dlg.errors[-1][1] and not dlg.asked
    good = tmp_path / "good.bin"
    good.write_bytes(BACKUP)
    dlg.open, dlg.yes = str(good), False
    app.restore()                                           # the user says no
    assert len(dlg.asked) == 1 and not app.busy and before == {n: record(fake, n) for n in cli.RECORDS}


def test_restore_writes_everything_verifies_and_rereads(app, fake, dlg, tmp_path):
    new = {n: bytearray(r) for n, r in fake.records.items()}
    d = profile.decode(bytes(new[1]))
    d["name"] = "Restaurado"
    new[1] = bytearray(profile.encode(d, bytes(new[1])))
    new[4][0:4] = b"Quad"
    new[p.LIGHTS][0] = 1
    f = tmp_path / "restore.bin"
    f.write_bytes(b"".join(bytes(new[n]) for n in cli.RECORDS))
    dlg.open = str(f)
    app.restore()
    pump(app)
    pump(app)                                               # restore's done() starts a fresh read
    assert all(record(fake, n) == bytes(new[n]) for n in cli.RECORDS)
    assert app.v["name"].get() == "Restaurado" and app.lights["active"] == 1 and app.base == bytes(new[1])
    assert "Backup restaurado" in app.status.cget("text") or "Configuração lida" in app.status.cget("text")


def test_restore_verification_failure(app, fake, dlg, tmp_path):
    f = tmp_path / "r.bin"
    f.write_bytes(BACKUP)
    dlg.open = str(f)
    fake.corrupt = True
    app.restore()
    pump(app)
    assert "verificação falhou" in app.status.cget("text") and dlg.errors
