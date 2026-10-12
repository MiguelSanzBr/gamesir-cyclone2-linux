# Changelog

This project follows [Semantic Versioning](https://semver.org/).

## Unreleased

* `c2gui`: the interface is available in English and Brazilian Portuguese. It follows the system language and can
  be changed with the selector next to Backup or on the Profile page.

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
