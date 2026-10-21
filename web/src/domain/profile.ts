// Port do src/cyclone2/profile.py: registro de 680 bytes <-> objeto, e o refazer da curva do gui/editor.py.
import { BUTTONS, PADDLES, TRIGGERS, code, name as keyName } from './keys'
import { PROFILE_SIZE } from './frames'

export type Value = boolean | number | string | Value[] | { [k: string]: Value }
export type Curve = { on: boolean; type: number; curvature: number; points: number[][] }
export type HairTrigger = { on: boolean; mode: number; start: number; end: number }
export type Trigger = { deadzone_on: boolean; deadzone: number[]; hair_trigger: HairTrigger; curve: Curve; [k: string]: Value }
export type ProfileDoc = { name: string; triggers: { LT: Trigger; RT: Trigger }; [k: string]: Value }

type Kind = 'u8' | 'bool' | 'key' | 'keys' | 'u8x4' | 'hair' | 'curve' | 'wheel' | 'name' | 'macro'
type Field = [path: string[], offset: number, kind: Kind]

const STEPS = 30
const SIZE: Record<Kind, number> = { u8: 1, bool: 1, key: 1, keys: 4, u8x4: 4, hair: 3, curve: 13, wheel: 5, name: 32, macro: 152 }
const WHEEL = ['up', 'down', 'left', 'right', 'center']

const deadzone = (p: string[], o: number): Field[] => [[[...p, 'deadzone_on'], o, 'bool'], [[...p, 'deadzone'], o + 1, 'u8x4']]
const curveField = (p: string[], o: number): Field[] => [[[...p, 'curve'], o, 'curve']]

function output(p: string[], o: number): Field[] {
  const names = ['on', 'invert_x', 'invert_y', 'axis_ratio', 'mouse_dpi', 'target', 'cross']
  const out = names.map((n, i): Field => [[...p, 'output', n], o + i, i < 3 ? 'bool' : 'u8'])
  return [...out, [[...p, 'output', 'wheel'], o + 7, 'wheel']]
}

const button = (p: string[], o: number): Field[] => [
  [[...p, 'turbo'], o, 'bool'], [[...p, 'turbo_speed'], o + 1, 'u8'], [[...p, 'map'], o + 2, 'keys'], [[...p, 'toggle'], o + 6, 'bool'],
]

// mesma tabela (path, offset, kind) do _fields() do Python
function fields(): Field[] {
  const f: Field[] = [[['name'], 0, 'name']]
  ;['left', 'right', 'lt', 'rt'].forEach((n, i) => f.push([['motors', n], 32 + i, 'u8']))
  ;['enabled', 'volume', 'mixer', 'mic_mute', 'mic_sensitivity'].forEach((n, i) => f.push([['audio', n], 36 + i, 'u8']))
  ;['shift', 'shift_key', 'dpad_diagonal_lock', 'xinput_abxy_swap', 'switch_abxy_swap', 'report_rate'].forEach((n, i) =>
    f.push([['options', n], 41 + i, n === 'shift_key' || n === 'report_rate' ? 'u8' : 'bool']))
  BUTTONS.forEach((b, i) => f.push(...button(['buttons', b], 64 + 7 * i)))
  PADDLES.forEach((b, i) => {
    const o = 176 + 159 * i
    f.push(...button(['buttons', b], o), [['macros', b], o + 7, 'macro'])
  })
  TRIGGERS.forEach((b, i) => {
    const o = 494 + 28 * i
    const p = ['triggers', b]
    f.push([['buttons', b, 'turbo'], o, 'bool'], [['buttons', b, 'turbo_speed'], o + 1, 'u8'], ...deadzone(p, o + 2),
      [['buttons', b, 'map'], o + 7, 'keys'], [['buttons', b, 'toggle'], o + 11, 'bool'], [[...p, 'hair_trigger'], o + 12, 'hair'],
      ...curveField(p, o + 15))
  })
  ;['left', 'right'].forEach((s, i) => {
    const o = 550 + 32 * i
    const p = ['sticks', s]
    f.push([[...p, 'on'], o, 'bool'], [[...p, 'square'], o + 1, 'bool'], ...deadzone(p, o + 2), ...curveField(p, o + 7), ...output(p, o + 20))
  })
  ;['aim', 'tilt'].forEach((s, i) => {
    const o = 614 + 33 * i
    const p = ['motion', s]
    f.push([[...p, 'activation'], o, 'u8'], [[...p, 'trigger_key'], o + 1, 'key'], [[...p, 'axes'], o + 2, 'u8'],
      ...deadzone(p, o + 3), ...curveField(p, o + 8), ...output(p, o + 21))
  })
  return f
}

const FIELDS = fields()

function get(buf: Uint8Array, o: number, kind: Kind): Value {
  const b = buf.subarray(o, o + SIZE[kind])
  switch (kind) {
    case 'u8':
      return b[0]!
    case 'bool':
      return Boolean(b[0]! & 1)
    case 'key':
      return keyName(b[0]!)
    case 'keys': // map_en + 3 códigos; [] = o botão mantém a função dele
      return b[0]! & 1 ? [...b.subarray(1)].filter((c) => c).map(keyName) : []
    case 'u8x4':
      return [...b]
    case 'hair': // bit 7 = ligado, bit 0/1 = modo 1/2
      return { on: Boolean(b[0]! & 0x80), mode: b[0]! & 2 ? 2 : 1, start: b[1]!, end: b[2]! }
    case 'curve':
      return { on: Boolean(b[0]! & 1), type: b[1]!, curvature: b[2]!, points: [0, 1, 2, 3, 4].map((i) => [b[3 + 2 * i]!, b[4 + 2 * i]!]) }
    case 'wheel':
      return Object.fromEntries(WHEEL.map((d, i) => [d, b[i] ? keyName(b[i]!) : '']))
    case 'name': {
      const end = b.indexOf(0)
      return new TextDecoder().decode(b.subarray(0, end < 0 ? b.length : end)).trim()
    }
    case 'macro': {
      const st = b[0]!
      const steps = []
      for (let i = 0; i < Math.min(b[3]!, STEPS); i++) {
        const s = b.subarray(4 + 5 * i, 9 + 5 * i)
        steps.push({ key: keyName(s[0]!), hold: (s[1]! << 8) | s[2]!, delay: i < STEPS - 1 ? (s[3]! << 8) | s[4]! : 0 })
      }
      return { on: Boolean(st & 1), press_to_trigger: Boolean(st & 2), cycle: Boolean(st & 4), cycle_time: (b[1]! << 8) | b[2]!, steps }
    }
  }
}

type Step = { key: string; hold: number; delay: number }
type Macro = { on: boolean; press_to_trigger: boolean; cycle: boolean; cycle_time: number; steps: Step[] }

function cutName(v: string): number[] {
  // corta em 31 bytes sem quebrar caractere, como o encode/decode "ignore" do Python
  const enc = new TextEncoder()
  let out = ''
  for (const ch of v) {
    if (enc.encode(out + ch).length > 31) break
    out += ch
  }
  const b = new Array<number>(32).fill(0)
  b.splice(0, 0, ...enc.encode(out))
  return b.slice(0, 32)
}

function put(buf: Uint8Array, o: number, kind: Kind, v: Value): void {
  let b: number[]
  switch (kind) {
    case 'u8':
      b = [v as number]
      break
    case 'bool':
      b = [Number(Boolean(v))]
      break
    case 'key':
      b = [code(v as string)]
      break
    case 'keys': {
      const ks = v as string[]
      if (ks.length > 3) throw new Error('at most 3 keys per button')
      b = [Number(ks.length > 0), ...ks.map(code), 0, 0, 0].slice(0, 4)
      break
    }
    case 'u8x4':
      b = [...(v as number[])]
      break
    case 'hair': {
      const h = v as HairTrigger
      b = [h.on ? 0x80 | (h.mode === 2 ? 2 : 1) : 0, h.start, h.end]
      break
    }
    case 'curve': {
      const c = v as Curve
      b = [Number(Boolean(c.on)), c.type, c.curvature, ...c.points.flat()]
      break
    }
    case 'wheel': {
      const w = v as Record<string, string>
      b = WHEEL.map((d) => (w[d] ? code(w[d]) : 0))
      break
    }
    case 'name':
      b = cutName(v as string)
      break
    case 'macro': {
      const m = v as Macro
      if (m.steps.length > STEPS) throw new Error(`at most ${STEPS} macro steps`)
      b = [Number(m.on && m.steps.length > 0) | (Number(m.press_to_trigger) << 1) | (Number(m.cycle) << 2),
        m.cycle_time >> 8, m.cycle_time & 0xff, m.steps.length]
      for (let i = 0; i < STEPS; i++) {
        const s = m.steps[i] ?? { key: '', hold: 0, delay: 0 }
        b.push(s.key ? code(s.key) : 0, s.hold >> 8, s.hold & 0xff)
        if (i < STEPS - 1) b.push(s.delay >> 8, s.delay & 0xff)
      }
      break
    }
  }
  if (b.length !== SIZE[kind] || b.some((x) => !Number.isInteger(x) || x < 0 || x > 255)) {
    throw new Error(`bad value ${JSON.stringify(v)} at offset ${o}`)
  }
  buf.set(b, o)
}

function lookup(doc: unknown, path: string[]): unknown {
  let n = doc
  for (const k of path) {
    if (!(n instanceof Object)) return undefined
    n = (n as Record<string, unknown>)[k]
  }
  return n
}

// JSON.stringify basta: um falso "mudou" só reescreve os mesmos bytes, nunca esconde mudança
const same = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b)

export function decode(data: Uint8Array): ProfileDoc {
  if (data.length !== PROFILE_SIZE) throw new Error(`a profile has ${PROFILE_SIZE} bytes, got ${data.length}`)
  const doc: Record<string, Value> = {}
  for (const [path, o, kind] of FIELDS) {
    let node = doc
    for (const k of path.slice(0, -1)) node = (node[k] ??= {}) as Record<string, Value>
    node[path.at(-1)!] = get(data, o, kind)
  }
  return doc as ProfileDoc
}

/** Objeto -> bytes a partir do base; só os campos q mudaram são escritos, bytes reservados ficam como estão. */
export function encode(doc: ProfileDoc, base: Uint8Array): Uint8Array {
  const old = decode(base)
  const buf = base.slice()
  for (const [path, o, kind] of FIELDS) {
    const v = lookup(doc, path)
    if (v !== undefined && !same(v, lookup(old, path))) put(buf, o, kind, v as Value)
  }
  return buf
}

/** [início, fim) dos bytes diferentes entre dois registros, ou null (bytesDiff do app). */
export function changedSpan(a: Uint8Array, b: Uint8Array): [number, number] | null {
  let start = -1
  let end = -1
  for (let i = 0; i < Math.min(a.length, b.length); i++) {
    if (a[i] !== b[i]) {
      if (start < 0) start = i
      end = i + 1
    }
  }
  return start < 0 ? null : [start, end]
}

// int(x + 0.5) do Python, q é o Math.round do app pros valores usados aqui
const round = (x: number) => Math.trunc(x + 0.5)

export function curve(dz: number[], points: number[][] = [[25, 25], [50, 50], [75, 75]], type = 0, curvature = 100): Curve {
  const [b, e, ab, ae] = dz as [number, number, number, number]
  const scale = (v: number, lo: number, hi: number) => round(((v - lo) / Math.max(hi - lo, 1)) * 255)
  const pts = [[0, 0], ...points.map(([x, y]) => [scale(x!, b, e), scale(y!, ab, ae)]), [255, 255]]
  return { on: true, type, curvature, points: pts }
}

export function curvePercent(c: Curve, dz: number[]): number[][] {
  const [b, e, ab, ae] = dz as [number, number, number, number]
  const back = (v: number, lo: number, hi: number) => round((v / 255) * (hi - lo) + lo)
  return c.points.slice(1, 4).map(([x, y]) => [back(x!, b, e), back(y!, ab, ae)])
}

const clamp = (v: number, lo: number, hi: number) => Math.min(Math.max(v, lo), hi)

/** Troca a zona morta e refaz a curva a partir dos pontos em %, como o Editor._deadzone (e o app). */
export function setDeadzone(rec: Trigger, dz: number[]): void {
  if (same(dz, rec.deadzone)) return
  const pts = curvePercent(rec.curve, rec.deadzone).map(([x, y]) => [clamp(x!, dz[0]!, dz[1]!), clamp(y!, dz[2]!, dz[3]!)])
  rec.curve = curve(dz, pts, rec.curve.type, rec.curve.curvature)
  rec.deadzone = dz
  rec.deadzone_on = true
}
