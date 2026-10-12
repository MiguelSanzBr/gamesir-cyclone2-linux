# GameSir Cyclone 2 configuration protocol

Recovered from GameSir Connect 1.14.5 for Windows. The app is an Electron program, so the protocol lives in
`resources/app.asar` → `dist/electron/main.js` (class `proxyC2`, the command builder `Ro`, the answer decoder
`getCommandType` and the profile serialisers `$a`/`qo`). Every detail below was then checked against a real
controller (firmware 3.5.6, wired, USB id `3537:1053`).

## Transport

The controller exposes an XInput interface (driven by `xpad`) and a HID interface. The HID report descriptor
has a vendor collection on usage page `0xFFF0`:

| Report | Direction | Size | Use |
| --- | --- | --- | --- |
| `0x0F` | host → controller | 63 + id | commands |
| `0x10` | controller → host | 63 + id | answers |
| `0x12` | controller → host | 63 + id | gamepad state stream |

On Linux this is a `/dev/hidraw*` node: write 64 bytes starting with `0F`, and read 64-byte reports starting
with the report id. The kernel gives every input report to each open handle. That is why the GUI can follow
the state stream on one handle while it reads and writes profiles on another.

USB product ids of the configurable modes (`ConfigModePid` in the app):

| PID | Mode |
| --- | --- |
| `0x101D` | wired |
| `0x1053` | wired (ADC sticks) |
| `0x102A` | 2.4 GHz |
| `0x100B` | 2.4 GHz through the dongle |

## Commands

Byte 1 of a report is the command. Answers echo a command number in byte 1.

| Cmd | Request | Answer |
| --- | --- | --- |
| 3 | `0F 03 profile off_hi off_lo len data…` (write ≤ 58 bytes) | `10 06 00` (ack) |
| 4 | `0F 04 profile off_hi off_lo len` (read ≤ 58 bytes) | `10 05 profile off_hi off_lo len data…` |
| 7 | `0F 07 n` switch to profile n | `10 06 00` |
| 9 | `0F 09` firmware version | `10 0A …`: bytes 4–8 controller, 12–16 dongle |
| 11 | `0F 0B` active profile | `10 0C n` |
| 13 | `0F 0D playing frame` LED preview (play, or hold frame 1–8) | none |
| 32 | `0F 20 66 55 left right` rumble | none |
| 242 | `0F F2 00` heartbeat (the app sends it every second) | none |
| — | (unsolicited) profile changed on the controller | `10 0F profile off_hi off_lo len_hi len_lo` |

Other details:

- **Busy.** An ack with byte 2 = 1 means "busy, send again".
- **Retries.** The app resends an unanswered command every 200 ms, up to 10 times.
- **Firmware version format.** The version bytes are characters separated by NULs. `33 00 35 00 36` becomes
  "3.5.6".
- **Saving.** Writes take effect and persist at once; there is no commit command. Like the app, this project
  writes only the changed byte range of a record.

## Records

Profiles 1–4 are the user profiles, 5 is the Shift layer, and 32 is the lighting record, which all profiles
share.

### Profile (680 bytes)

| Offset | Size | Content |
| --- | --- | --- |
| 0 | 32 | name, UTF-8, NUL padded |
| 32 | 4 | motor strength in %: left, right, LT, RT (the app offers 0/25/50/75/100) |
| 36 | 5 | audio (unused on the Cyclone 2) |
| 41 | 6 | Shift on, Shift key, d-pad diagonal lock, XInput ABXY swap, Switch ABXY swap, report rate |
| 47 | 17 | reserved |
| 64 | 16 × 7 | buttons Up, Down, Left, Right, LB, RB, LS, RS, A, B, X, Y, Home, View, Menu, Capture |
| 176 | 2 × 159 | L4, R4: the 7 button bytes + macro |
| 494 | 2 × 28 | LT, RT |
| 550 | 2 × 32 | left, right stick |
| 614 | 2 × 33 | gyro "aim", gyro "tilt" |

**Button (7 bytes):** `turbo_on turbo_speed map_on key1 key2 key3 toggle_on`. With `map_on` = 0 the button
keeps its own function. Up to three keys can be sent at once. The key codes are in `src/cyclone2/keys.py`:

| Codes | Meaning |
| --- | --- |
| 1–28 | gamepad buttons and stick directions |
| 50–154 | keyboard keys |
| 200–206 | mouse buttons and wheel |
| 230 | Mute |
| 231 | Shift |
| 255 | none (button disabled) |

**Macro (152 bytes):**

- 1 status byte: bit 0 on, bit 1 press to trigger, bit 2 loop.
- Loop time, u16 big-endian.
- Step count.
- 30 steps of `key hold_hi hold_lo delay_hi delay_lo`. The last step has no delay.

**Trigger (28 bytes):**

- `turbo_on turbo_speed`.
- Dead zone `on begin end anti_begin anti_end` in %.
- Mapping `map_on k1 k2 k3`, then `toggle_on`.
- Hair trigger `status start end`: status bit 7 = on, bit 0 = adaptive, bit 1 = fixed.
- Curve, 13 bytes: `on type curvature` + 5 `(x, y)` points on 0–255. The first point is (0,0) and the last is
  (255,255).

**Stick (32 bytes):**

- `on raw`.
- Dead zone (5 bytes) and curve (13 bytes), as for the triggers.
- Output mapping (12 bytes): `on invert_x invert_y axis_ratio mouse_dpi target cross up down left right center`.
  The target is 1 left stick, 2 right stick, 3 wheel or 4 mouse.

**Gyro (33 bytes):**

- `activation trigger_key axes`. Activation is 0 off, 1 hold the button, 2 toggle, 3 always.
- Then dead zone, curve and output mapping, as for the sticks.

The app stores curves relative to the dead zone: x = (x% − begin) / (end − begin) × 255. When the dead zone
changes, it rebuilds the points from their percentage values (`profile.curve`/`profile.curve_percent`).

### Lighting (635 bytes)

| Offset | Size | Content |
| --- | --- | --- |
| 0 | 1 | active animation (0–3) |
| 1 | 5 × 124 | animations: frame count, effect count, 20 − speed, brightness %, 8 frames × 5 LEDs × RGB |
| 621 | 14 | audio reactive, user effect, profile LED RGB, raise to wake, standby minutes, 7 reserved |

Each frame lists its LEDs as lower-left, lower-right, upper-left, Home, upper-right. On the black Cyclone 2 only
the two grip bars light up: lower-left is the left grip and lower-right the right grip. The other editions also
have rings around the sticks (upper-left and upper-right) and the Home button.

## State report `0x12`

| Bytes | Content |
| --- | --- |
| 1–9 | processed output: sticks, hat + face buttons, buttons, triggers (after remaps, ABXY swap and hair trigger) |
| 35, 36, 37 | charging, battery %, active animation |
| 53–62 | the same block with the physical input and analog triggers |

The physical block (offsets relative to byte 53):

| Offset | Content |
| --- | --- |
| 1–4 | sticks LX LY RX RY (128 = centre) |
| 5 | low nibble: hat (0 = up, clockwise, 15 = none); bits 4–7: X A B Y |
| 6 | LB RB LT RT View Menu LS RS |
| 7 | bit 0 Home, bit 1 Capture, bit 3 L4, bit 4 R4, bit 5 M |
| 8, 9 | LT, RT (0–255) |
