"""cyclone2 — open-source Linux configurator for the GameSir Cyclone 2 controller.

Package layout:

* :mod:`cyclone2.protocol`  — report ids, commands, packet builders and the state report decoder (pure functions).
* :mod:`cyclone2.keys`      — the firmware's key codes (remap targets, macro steps, gyro trigger keys).
* :mod:`cyclone2.discovery` — finds the controller's vendor config ``hidraw`` node.
* :mod:`cyclone2.device`    — :class:`~cyclone2.device.Device`, the transport (profiles, lighting, switching, rumble).
* :mod:`cyclone2.profile`   — the 680-byte profile record: decode to a dict, encode back, app defaults.
* :mod:`cyclone2.light`     — the 635-byte lighting record and the app's effect presets.
* :mod:`cyclone2.cli`       — the ``c2ctl`` command.
* :mod:`cyclone2.gui`       — the ``c2gui`` Tk interface.
"""

__version__ = "0.1.0b4"
