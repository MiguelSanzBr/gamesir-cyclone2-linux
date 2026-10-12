# Architecture

```
src/cyclone2/
├── protocol.py     report ids, commands, packet builders, state-report decoder (pure functions)
├── keys.py         firmware key codes <-> names (remap targets, macro steps, gyro keys)
├── discovery.py    sysfs scan: the hidraw node with the vendor usage page 0xFFF0
├── device.py       Device: request/answer with resends, read/write records, switch, firmware, rumble, state
├── profile.py      680-byte profile <-> nested dict (FIELDS table), encode only what changed, app defaults
├── light.py        635-byte lighting record <-> dict, the app's effect presets
├── cli.py          c2ctl (argparse)
└── gui/
    ├── theme.py        palette, fonts, timings, controller skins (black, white, pink)
    ├── catalog.py      UI vocabulary: sections, remap targets, gyro options, LED zones, presets
    ├── geometry.py     Cyclone 2 drawing coordinates (body, parts, LED zones, callouts)
    ├── drawing.py      rounded shapes, gradient fill, colour maths
    ├── widgets.py      Pill, panel, field, Slider, Toggle, ColorPicker
    ├── controller.py   ControllerView mixin: draw/animate the controller, mapping highlight
    ├── pages.py        Pages mixin: layout helpers, home + section pages, navigation
    ├── editor.py       Editor mixin: dicts <-> Tk variables, lighting editor, LED preview colours
    ├── sync.py         DeviceSync mixin: worker-thread I/O, profile switching, auto-save, polling, backups
    ├── live_input.py   PadInput mixin: state-report reader thread, heartbeat, LED frame preview
    └── app.py          App = Pages + ControllerView + Editor + DeviceSync + PadInput + tk.Tk
```

`drawing.py` and `widgets.py` are shared with the 8BitDo Ultimate 2 configurator
([8bitdo-ultimate2-linux](https://github.com/MiguelSanzBr/8bitdo-ultimate2-linux)), so both apps look the same.

## Layers

1. **protocol** and **keys** know bytes on the wire and nothing else.
2. **discovery** and **device** do the I/O. `Device` looks up `discovery.find_devices()` at call time, so tests can
   swap it. `Device.request()` resends a command every 200 ms (up to 10 times, like the app) and skips state
   reports and unrelated answers.
3. **profile** and **light** are pure data transformation. `profile.decode()` uses the declarative `FIELDS` table of
   `(path, offset, kind)`. `encode()` writes only the fields whose decoded value changed, so unknown or untouched
   bytes survive exactly.
4. **cli** and **gui** are front ends. Neither knows about packets or offsets.

## GUI data flow

```
controller ──read_device()──▶ base/lbase (bytes) ──decode──▶ doc/lights (dicts) ──load()──▶ Tk variables ──▶ widgets
widgets ──trace──▶ changed() ──debounce──▶ autosave(): gather() → encode → changed_span → Device.write_profile(range)
```

* Device I/O runs on short-lived worker threads (`DeviceSync.run`). Results come back through `after(0, …)` to the Tk
  thread, and `busy` serialises the jobs.
* Selecting a profile switches it on the controller too, as the app does. Pending edits are saved in the same job.
* `poll()` reads the active profile every `theme.POLL_MS`, so a change made on the controller is followed.
* The input thread (`PadInput._read_pad`) opens its own handle on the hidraw node. It reads the `0x12` state
  stream, sends the heartbeat every second, and carries fire-and-forget commands such as the LED frame preview.
  `animate()` turns its data into visuals every `theme.FRAME_MS`.

## Testing

`tests/fake_device.py` emulates the firmware over a `SOCK_SEQPACKET` socketpair, which keeps the 64-byte report
boundaries and works with `select`. Its records start from a backup of a real controller
(`tests/fixtures/backup.bin`). `FakeController.install(monkeypatch)` makes `Device()` find and open it. GUI tests
build a real Tk `App` (an X display is required; CI uses `xvfb-run`). Coverage is enforced at 100% lines and
branches (`.coveragerc`).
