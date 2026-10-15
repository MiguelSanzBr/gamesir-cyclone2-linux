# Changelog

This project follows [Semantic Versioning](https://semver.org/).

## 0.1.0-beta.3 — 2026-10-15

* Flatpak: AppStream metadata, desktop entry and icon under the app ID `io.github.miguelsanzbr.gamesir-cyclone2-linux` (`packaging/flatpak/`), ready for a
  Flathub submission. The Flatpak build bundles Tcl/Tk 8.6 and tkinter, which the Freedesktop runtime lacks.

## 0.1.0-beta.2 — 2026-10-15

* AppImage for any distribution, attached to the release with `install-udev.sh`, the udev rule and a short notice
  (built by the manual `appimage` workflow). Thanks to @moi952.
* `c2gui`: the interface is available in English, French and Brazilian Portuguese. It follows the system language
  and can be changed with the selector next to Backup or on the Profile page. (French by @moi952.)
* `c2gui`: dark window frame drawn by the app; the window manager still moves, resizes, snaps and maximises the
  window. `CYCLONE2_NATIVE_TITLEBAR=1` keeps the system title bar. Dialogs use the same style. (@moi952)
* `c2gui`: clear, translated messages when the controller is missing, silent or not accessible. (@moi952)
* `c2gui`: new remap choices "Home" and "Steam quick menu" (Ctrl+2). (@moi952)
* `c2gui`: connection badge as in the 8BitDo Ultimate 2 configurator: Wi-Fi through the 2.4G dongle or a plug on
  the cable, live battery level (red at 15% or less, a bolt while charging), a red X when the controller does
  not answer; the firmware moved to the footer's corner.
* `c2gui`: the d-pad is one rounded cross with larger arrows.
* Checked through the 2.4G dongle as well as on the cable.

## 0.1.0-beta.1 — 2026-10-12

First public beta.

* Reverse-engineered configuration protocol of the GameSir Cyclone 2 (documented in `docs/PROTOCOL.md`) and
  checked on a real controller (firmware 3.5.6).
* `c2ctl`: list, info, dump/apply JSON (whole or partial profiles), switch profile, reset to app defaults,
  lighting (presets, solid colour, brightness, speed, animation), rumble test, backup/restore, live input
  watch. Writes are verified.
* `c2gui`: dark interface in the style of the 8BitDo Ultimate 2 configurator. It includes a live drawing of
  the Cyclone 2 (pressed buttons, sticks, analog triggers, LED zones, profile indicator) and black, white and
  pink skins. Pages: button remapping with turbo and toggle, stick and trigger dead zones, hair trigger,
  motors, gyro, a lighting editor (animations, frames, zones, colour wheel, presets), and profile options.
  Changes are saved automatically and only the changed bytes are written.
* udev rule for user access to the hidraw node; `.deb` package (`packaging/build-deb.sh`).
* Firmware emulator and a test suite with 100% line and branch coverage.
