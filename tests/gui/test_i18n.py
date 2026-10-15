"""i18n: language detection, the lookup, completeness of the English table, the language chips and main()."""
import ast
import glob
import os

import pytest

from cyclone2 import keys
from cyclone2.gui import app as app_mod, catalog, geometry, i18n, theme
from cyclone2.gui.i18n import EN, FR, LANGS, _

from .conftest import badge, click, make_app, pump, texts, walk

GUI = os.path.dirname(i18n.__file__)
REAL_SYSTEM_LANG = i18n.system_lang         # the autouse fixture replaces i18n.system_lang during each test


# ---------------------------------------------------------------- detection and lookup
@pytest.mark.parametrize("env, lang", [
    ({}, "en"),
    ({"LANG": "pt_BR.UTF-8"}, "pt"),
    ({"LANG": "en_US.UTF-8"}, "en"),
    ({"LANGUAGE": "pt_BR:en", "LANG": "en_US.UTF-8"}, "pt"),
    ({"LANGUAGE": "en:pt_BR", "LANG": "pt_BR.UTF-8"}, "en"),
    ({"LANGUAGE": "", "LC_ALL": "pt_PT.UTF-8", "LANG": "en_US.UTF-8"}, "pt"),
    ({"LC_ALL": "C", "LC_MESSAGES": "pt_BR.UTF-8"}, "en"),
    ({"LC_MESSAGES": "pt_BR.UTF-8", "LANG": "en_US.UTF-8"}, "pt"),
    ({"LANG": "pt"}, "pt"),
    ({"LANG": "fr_FR.UTF-8"}, "fr"),
    ({"LANGUAGE": "fr:en", "LANG": "en_US.UTF-8"}, "fr"),
    ({"LANG": "de_DE.UTF-8"}, "en"),
])
def test_system_lang(env, lang):
    assert REAL_SYSTEM_LANG(env) == lang


def test_system_lang_defaults_to_the_process_environment(monkeypatch):
    for name in ("LANGUAGE", "LC_ALL", "LC_MESSAGES"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LANG", "pt_BR.UTF-8")
    assert REAL_SYSTEM_LANG() == "pt"


def test_translate(monkeypatch):
    assert _("Botões") == "Botões"                          # default: the Portuguese source text
    monkeypatch.setattr(i18n, "LANG", "en")
    assert _("Botões") == "Buttons" and _("Perfil {}").format(2) == "Profile 2"
    monkeypatch.setattr(i18n, "LANG", "fr")
    assert _("Botões") == "Boutons" and _("Perfil {}").format(2) == "Profil 2"
    assert _("A") == "A" and _("texto desconhecido") == "texto desconhecido"     # unknown keys fall back


def test_missing_translation_falls_back_to_english(monkeypatch):
    monkeypatch.setattr(i18n, "LANG", "fr")
    monkeypatch.setitem(EN, "texto novo", "new text")
    assert _("texto novo") == "new text" and _("texto desconhecido") == "texto desconhecido"
    monkeypatch.setattr(i18n, "LANG", "xx")                 # an unknown language is English too
    assert _("Botões") == "Buttons"


def test_steam_shortcut_target_is_a_valid_key_combination():
    assert [v for v, _t in catalog.SHORTCUTS] == ["KB_LCTRL+KB_2"]
    for value, label in catalog.SHORTCUTS:
        assert (value, label) in catalog.TARGETS and label in EN and label in FR
        assert all(keys.code(k) for k in value.split("+")) and len(value.split("+")) <= 3


def test_langs():
    assert LANGS == {"pt": "Português (Brasil)", "en": "English", "fr": "Français"}


# ---------------------------------------------------------------- the table covers the code
def _sources():
    for path in sorted(glob.glob(os.path.join(GUI, "*.py"))):
        with open(path, encoding="utf-8") as f:
            yield os.path.basename(path), ast.parse(f.read())


def test_every_literal_is_translated_and_no_key_is_unused():
    called, constants = set(), set()
    for name, tree in _sources():
        if name == "i18n.py":
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                constants.add(node.value)
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_"
                    and isinstance(node.args[0], ast.Constant)):
                called.add(node.args[0].value)
    assert called, "no _() calls found"
    assert sorted(called - set(EN)) == []
    assert sorted(set(EN) - constants) == []      # keys that no literal of the GUI uses (also covers catalog labels)
    assert all(EN.values())
    assert set(FR) == set(EN) and all(FR.values())
    assert all(FR[k].count("{}") == k.count("{}") for k in EN)         # placeholders survive the translation


def test_constant_labels_are_translated():
    """Labels kept in Portuguese in the constants are translated where they are shown; names stay as they are."""
    labels = {t for t, _k in catalog.SECTIONS} | {catalog.TARGETS[0][1], catalog.TARGETS[-1][1]}
    for table in (catalog.ACTIVATION, catalog.OUTPUTS, catalog.MOTION, catalog.ZONES, catalog.PRESETS, catalog.STANDBY):
        labels |= {text for _k, text in table}
    labels |= {text for text, *_r in geometry.CALLOUTS} | {sk["name"] for sk in theme.SKINS.values()}
    same = {"Home", "Mouse", "D-pad", "LT / LB", "RT / RB", "1 min", "5 min", "10 min", "20 min"}
    assert sorted(labels - same - set(EN)) == []


# ---------------------------------------------------------------- language chips and restart
def _chip(a, name):
    return next(w for w in walk(a) if getattr(w, "text", None) == name)


def test_language_chip_saves_and_restarts(monkeypatch):
    app_mod.save_settings({"skin": "pink"})
    a = make_app(monkeypatch)
    assert a.skin == "pink" and a.restart is False and a.lang_choice.get() == "pt"
    assert _chip(a, "English") and _chip(a, "Português (Brasil)") and _chip(a, "Français")       # shown untranslated
    a.lang_choice.set("pt")                                              # same language: nothing happens
    assert a.restart is False and app_mod.load_settings() == {"skin": "pink"}
    a.lang_choice.set("en")
    assert a.restart is True and not a._closing                         # closed once the chip traces finish
    a.update()
    assert a._closing
    assert app_mod.load_settings() == {"skin": "pink", "lang": "en"}      # the other keys are kept
    with pytest.raises(Exception):
        a.winfo_exists()                                                  # the window is gone


def test_language_chip_click(monkeypatch):
    a = make_app(monkeypatch)
    click(a, _chip(a, "English"))
    assert a.restart and app_mod.load_settings() == {"lang": "en"}


def test_app_starts_in_the_saved_language(monkeypatch):
    app_mod.save_settings({"lang": "en"})
    a = make_app(monkeypatch)
    try:
        assert i18n.LANG == "en" and a.lang_choice.get() == "en"
        assert a.title() == "GameSir Cyclone 2 — Linux"
        assert badge(a) == (None, False, "wifi")
        a.active = 2
        a.refresh_profiles()
        assert [b.text for b in a.profile_btns][:2] == ["Profile 1", "Profile 2  ●"]
        assert a.home_sub.cget("text") == "Active profile on the controller: 2"
        shown = {getattr(w, "text", None) for w in walk(a)}
        shown |= {w.cget("text") for w in walk(a) if w.winfo_class() == "Label"}
        shown |= {t for w in walk(a) if w.winfo_class() == "Canvas" for t in texts(w)}
        for expected in ("Buttons", "Sticks", "Triggers", "Rumble", "Gyro", "Lights", "Profile", "Left stick",
                         "ABXY buttons", "Interface language", "Reload", "Restore backup", "Hair trigger",
                         "Left grip", "Always on", "Never"):
            assert expected in shown, expected
        assert "co:Analógico_esquerdo" in {t for c in walk(a) if c.winfo_class() == "Canvas"
                                           for i in c.find_all() for t in c.gettags(i)}     # tags stay Portuguese
        a.set_connected(None)
        assert badge(a) == (None, True, "wifi")
        a.refresh_mapping()
        assert a.map_title.cget("text") == "Button A" and a.map_sub.cget("text") == "current function: default (A)"
    finally:
        a.destroy()


def test_runtime_messages_follow_the_language(mk, monkeypatch):
    a = mk(read=False)
    monkeypatch.setattr(i18n, "LANG", "en")         # the shared window is built in Portuguese; messages are looked up live
    a.read_device()
    pump(a)
    assert a.status.cget("text").startswith("Settings read from the controller")
    assert badge(a)[0] and a.info_label.cget("text").startswith("Device: ")
    a.reset_profile()
    assert a.status.cget("text") == "App defaults restored for this profile."


def test_unknown_saved_language_falls_back_to_the_system(monkeypatch):
    app_mod.save_settings({"lang": "xx"})
    monkeypatch.setattr(i18n, "system_lang", lambda env=None: "en")
    a = make_app(monkeypatch)
    try:
        assert i18n.LANG == "en"
    finally:
        a.destroy()


def test_main_restarts_once_then_exits(monkeypatch):
    built = []

    class Stub:
        def __init__(self):
            built.append(self)
            self.restart = len(built) == 1

        def mainloop(self):
            self.ran = True
    monkeypatch.setattr(app_mod, "App", Stub)
    app_mod.main()
    assert len(built) == 2 and all(b.ran for b in built)


def test_footer_selector_left_of_backup_switches_language(monkeypatch):
    a = make_app(monkeypatch)
    foot = a.status.master
    order = [getattr(w, "text", None) for w in foot.pack_slaves()][1:]     # after the firmware corner
    assert order[:4] == ["Recarregar", "Restaurar backup", "Backup", "Português (Brasil)  ▾"]   # packed right to left
    sel = foot.pack_slaves()[4]
    sel.menu.invoke(1)
    assert a.lang_pick.get() == "en" and a.restart is True
    a.update()
    assert app_mod.load_settings() == {"lang": "en"}
