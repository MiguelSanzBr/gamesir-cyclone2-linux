# GameSir Cyclone 2 in the browser

[Português](README.md)

Configurator for the GameSir Cyclone 2 controller that runs straight in the browser, over WebHID, in React +
TypeScript.

The official app (GameSir Connect) is Windows only. To use the controller on Linux I recovered the protocol and wrote
[gamesir-cyclone2-linux](https://github.com/MiguelSanzBr/gamesir-cyclone2-linux) in Python. This project takes the same
protocol to the browser: open the page in Chrome or Edge, connect the controller and configure it. Nothing to install
besides the udev rule on Linux.

There is a demo mode with a controller simulated in memory, so everything can be tried without the hardware.

## What it does

- Shows device, mode (wired or 2.4G), firmware, dongle, active profile and battery.
- Reads the 4 profiles and switches the active profile on the controller.
- Profile name.
- LT and RT triggers: dead zone (start and end, with the curve rebuilt the way the app does it) and hair trigger
  (on/off, adaptive or fixed, range).
- Lighting: active animation, the app's presets, brightness, speed, frame count and the colour of each LED in each
  frame.
- Rumble test.
- Live input: pressing a button, moving a stick or pulling a trigger on the controller lights that part of the
  drawing (the stick moves, the trigger fills with the pressure). In demo mode clicking the drawing presses the
  simulated button.

The screen follows the Linux app: the controller drawing (ported from the outline in `gui/geometry.py`) with the
grips in the lighting colours, callouts that jump to their section, profile tabs at the top, one tile per section
and the pending changes bar at the bottom. It has a dark and a light theme, follows the system and the button at the
top switches it (the browser bar on mobile follows). With pending changes, closing the tab makes the browser ask
first, so the edits aren't lost.

## How it works

The config channel is the controller's vendor HID interface (usage page `0xFFF0`, VID `0x3537`, PIDs `0x101D`,
`0x102A`, `0x1053`, `0x100B`):

- host to controller: output report `0x0F`, 64 bytes `0F cmd args...`
- controller to host: input report `0x10` with the answer, and `0x12` with the gamepad state (buttons, sticks, battery)
- profile data: `0F 03|04 profile offset_hi offset_lo length data...`, at most 58 bytes per packet

Every encoder and decoder is a direct port of the Python code (`protocol.py`, `profile.py`, `light.py`, `keys.py`,
`device.py`), and the tests use bytes produced by running the Python code, each fixture with a comment naming the
Python function it mirrors (`src/test/fixtures.ts`).

Write safety, same as the Linux project:

1. Read first: on connect it reads the active profile and the lighting record.
2. Editing writes nothing. Edits are staged and the page shows how many are pending.
3. "Revisar e gravar" (review and write) opens a confirmation listing what changes (from → to) and the exact byte range
   of each record.
4. Only after "Gravar no controle" (write to the controller) are packets sent, and only for the changed range
   (`changed_span`, the app's `bytesDiff`).
5. The whole record is read back and compared. If it does not match, an error is shown and the edits stay pending.

Requests are resent every 200 ms, up to 10 times, while the controller is silent or answers "busy"; the answer must be
of the right kind (and, for reads, for the same profile and offset); the heartbeat goes out every second while
connected, like the official app.

## Architecture

Hexagonal, with the domain in the controller's own language:

```
                 driving adapters                    driven adapters
              ┌─────────────────────┐        ┌───────────────────────────────┐
              │  ui/ (React)        │        │  webhid/  (navigator.hid)     │
              │  only calls use     │        │  demo/    (simulated device)  │
              │  cases              │        └──────────────┬────────────────┘
              └──────────┬──────────┘                       │ implements
                         ▼                                  ▼
              ┌──────────────────────────────────────────────────────────────┐
              │ application/  use cases: Connect, ReadProfile,               │
              │ PlanChanges, ApplyChanges, SwitchActiveProfile, KeepAlive    │
              │ ConfigSession (resend, answer matching, verified writes)     │
              │ port: ControllerChannel                                      │
              └──────────────────────────────┬───────────────────────────────┘
                                             ▼
              ┌──────────────────────────────────────────────────────────────┐
              │ domain/  Profile (id 1-4), Lighting, ChangeSet (byte range), │
              │ HairTrigger, TriggerRange, ControllerInfo, frames, record    │
              │ encode/decode. Pure functions, no I/O.                       │
              └──────────────────────────────────────────────────────────────┘
```

Why: the protocol and the write rules are the part that cannot be wrong, so they live in pure code, tested against the
Python bytes, with no React or browser involved. WebHID and the demo mode are just two ways to send and receive
reports, and both go through the same `ConfigSession`, so the demo mode exercises the same path as the hardware.
`main.tsx` is the composition root that plugs the adapters into the UI.

The dependency rule is enforced by ESLint (`@typescript-eslint/no-restricted-imports` and `no-restricted-globals` per
folder): domain does not import application, adapters or React and does not touch `navigator`/`document`/`window`;
application does not import adapters or React; the UI imports only the use cases (`application/usecases`) and only
types from the domain. `src/architecture.test.ts` proves the rule catches each violation, and `npm run lint` in CI
fails the build.

## Tests

| Guarantee | Test |
| --- | --- |
| Command, read and write frames byte for byte equal to Python | `src/domain/frames.test.ts` |
| Writes carry at most 58 data bytes and stay inside the record | `src/domain/values.test.ts` (write frame) |
| 680-byte profile decode/encode equal to Python, encode only what changed | `src/domain/profile.test.ts` |
| Dead zone rebuilds the curve like `Editor._deadzone` | `src/domain/profile.test.ts` |
| 635-byte lighting record and presets equal to Python | `src/domain/lighting.test.ts` |
| Valid ranges (profile 1-4, dead zone, hair trigger, brightness, speed, frames, colour) | `src/domain/values.test.ts` |
| Editing leaves the original alone and becomes a ChangeSet with the right range | `src/domain/aggregates.test.ts` |
| Readable list of what changes | `src/domain/changes.test.ts` |
| Resend on silence and on "busy", give up after 10 sends | `src/application/session.test.ts` |
| Answers for another command, profile or offset are ignored | `src/application/session.test.ts` |
| Writes only the range and reads it back, fails if the controller did not keep it | `src/application/session.test.ts` |
| Heartbeat every second, stops on close | `src/application/session.test.ts`, `usecases.test.ts` |
| Writing without confirmation is refused | `src/application/usecases.test.ts` |
| Connect reads info, active profile and lighting; closes the channel on failure | `src/application/usecases.test.ts` |
| WebHID: VID/PID/usage page filters, `sendReport(0x0F, 63 bytes)`, input report with the id in byte 0 | `src/adapters/webhid/webhid.test.ts` |
| Simulated controller answers like the Python fake | `src/adapters/demo/demo.test.ts` |
| Browser without WebHID: warning and demo mode | `src/adapters/ui/App.test.tsx` |
| Nothing is written before confirming; cancel/Esc writes nothing; confirm writes and applies | `src/adapters/ui/App.test.tsx` |
| Dependency rule between layers | `src/architecture.test.ts` |
| Full flow in Chromium: demo, read, edit, confirm, read back; 375 px with no horizontal scroll | `e2e/demo.spec.ts` |

### Coverage

Vitest with v8, 100% threshold on statements, branches, functions and lines over `src/`. Below that `npm run coverage`
exits with an error and CI fails. Last result: 148 tests, 100% on everything (722 statements, 278 branches, 254
functions, 567 lines).

Excluded from measurement, each with a comment in `vite.config.ts`:

- `src/main.tsx`: bootstrap, it only mounts `<App/>` and wires the adapters; the E2E covers it.
- `src/application/ports.ts`: only declares the `ControllerChannel` interface, no JS left to measure.
- `src/test/**` and the `*.test.ts(x)` files: test code.

### Manual mutation check

I broke the main protections on purpose, ran the suite and restored them:

| Mutation | Result |
| --- | --- |
| `applyChanges` writes without confirmation | 1 test failed |
| "Revisar e gravar" button writes directly | 4 tests failed |
| WebHID sends report id `0x10` instead of `0x0F` | 1 test failed |
| outgoing report id `0x0E` in the domain | 7 tests failed |
| accepts any answer without checking the command | 2 tests failed |
| read without checking the chunk's profile and offset | 1 test failed |

## Known limits

- Chrome and Edge on desktop only (WebHID). Firefox and Safari get the demo mode only.
- The controller must be in a config-capable mode (PIDs above). On Linux Chrome opens the controller through hidraw,
  so it needs `udev/70-gamesir-cyclone2.rules` from the Linux project, then a replug.
- Not exercised on real hardware. The WebHID transport is covered with a fake `navigator.hid` and the rest with the
  simulated controller; the protocol itself was validated in the Python project with a black Cyclone 2, firmware
  3.5.6, wired `3537:1053`.
- Hair trigger start and end accept 0 to 100 without requiring start < end, because neither the Python code nor the
  official app (as far as I recovered it) requires it. I do not know what the firmware does with start > end.
- Report `0x12` decoding (buttons, sticks, triggers) mirrors the Python `protocol.state`, with fixtures generated
  by it, but I have not seen the drawing light up with a real controller, only in demo mode.
- The heartbeat goes out while connected; the official app only sends it while its window has focus.
- Switching the active profile is immediate, with no confirmation: it writes no memory, it is what the controller's
  own button does.
- It does not follow a profile change made on the controller itself (the Python GUI polls); use "Ler do controle de
  novo" (read from the controller again).

Not ported (the full record encode/decode is ported and tested, the UI is missing):

- button remapping, macros, sticks, gyro, motors and options (Shift, d-pad diagonal lock, ABXY swap, report rate)
- Shift layer (profile 5)
- reset to the app defaults
- backup and restore
- LED preview (command 13), profile LED, standby, raise to wake and audio reactive

## Running

```bash
npm ci
npm run dev          # http://localhost:5175/gamesir-cyclone2-linux/
npm run lint
npm run typecheck
npm run coverage     # tests + 100% gate
npm run e2e          # Playwright (build + preview on port 4175)
npm run build
```

With Docker (builds and serves with nginx at http://localhost:8089/gamesir-cyclone2-linux/):

```bash
docker compose up --build
```

The GitHub Pages deploy is in `.github/workflows/pages.yml` and CI in `.github/workflows/ci.yml`.

## License

MIT, see [LICENSE](LICENSE).
