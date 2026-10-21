// Port do src/cyclone2/light.py: registro de luzes de 635 bytes (perfil 32, compartilhado) e presets do app.
import { LIGHT_SIZE } from './frames'

// ordem dos 5 LEDs dentro de cada quadro no registro
export const LEDS = ['lower_left', 'lower_right', 'upper_left', 'home', 'upper_right'] as const
export type Led = (typeof LEDS)[number]
export type Frame = Record<Led, string>
export type Animation = { frames: number; effects: number; speed: number; brightness: number; colors: Frame[] }
export type LightsDoc = {
  active: number
  animations: Animation[]
  audio_reactive: boolean
  user_effect: number
  profile_led: string
  raise_to_wake: boolean
  standby: number
}

export const ANIMATIONS = 5
export const FRAMES = 8
export const MAX_SPEED = 20

const toHex = (b: Uint8Array) => '#' + Array.from(b, (x) => x.toString(16).padStart(2, '0')).join('')
const rgb = (c: string) => [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16))

export function decode(data: Uint8Array): LightsDoc {
  if (data.length !== LIGHT_SIZE) throw new Error(`the lighting record has ${LIGHT_SIZE} bytes, got ${data.length}`)
  const animations = Array.from({ length: ANIMATIONS }, (_, a) => {
    const b = data.subarray(1 + 124 * a, 125 + 124 * a)
    const colors = Array.from({ length: FRAMES }, (_, f) =>
      Object.fromEntries(LEDS.map((led, i) => [led, toHex(b.subarray(4 + 15 * f + 3 * i, 7 + 15 * f + 3 * i))])) as Frame)
    return { frames: b[0]!, effects: b[1]!, speed: Math.max(0, MAX_SPEED - b[2]!), brightness: Math.min(b[3]!, 100), colors }
  })
  const t = data.subarray(621)
  return {
    active: data[0]! <= 3 ? data[0]! : 0,
    animations,
    audio_reactive: Boolean(t[0]! & 1),
    user_effect: t[1]!,
    profile_led: toHex(t.subarray(2, 5)),
    raise_to_wake: Boolean(t[5]! & 1),
    standby: t[6]!,
  }
}

/** Objeto -> bytes; o q o objeto não descreve (cauda reservada) vem do base. */
export function encode(doc: LightsDoc, base: Uint8Array): Uint8Array {
  const buf = base.slice()
  buf[0] = doc.active
  doc.animations.forEach((an, a) => {
    const o = 1 + 124 * a
    const speed = Math.min(Math.max(an.speed, 0), MAX_SPEED)
    buf.set([an.frames, an.effects, MAX_SPEED - speed, an.brightness], o)
    an.colors.forEach((frame, f) => LEDS.forEach((led, i) => buf.set(rgb(frame[led]), o + 4 + 15 * f + 3 * i)))
  })
  buf.set([Number(doc.audio_reactive), doc.user_effect, ...rgb(doc.profile_led), Number(doc.raise_to_wake), doc.standby], 621)
  return buf
}

// presets do app (Name, Speed, quadros na ordem Home, UpperLeft, LowerLeft, LowerRight, UpperRight)
const PRESET_ORDER = ['home', 'upper_left', 'lower_left', 'lower_right', 'upper_right'] as const
const all = (c: string) => Array(5).fill(c).join(' ')
const RAW: [string, number, string[]][] = [
  ['Flow', 17, ['FF0000 0000FF 00FF00 FFFF00 FF0000', 'FF8000 FF0000 0000FF 00FF80 FFFF00',
    'FFFF00 FF80FF 800080 0000FF 00FF00', '14FF01 808000 FF0000 FF0000 0000FF', '000FFF 008000 FF0000 808000 FF0080']],
  ['Rainbow', 10, ['FF0000', 'FFA500', 'FFFF00', '00FF00', '00FFFF', '0000FF', 'FF00FF', 'FF0000'].map(all)],
  ['Pulse', 5, ['FF00C8 FF0000 8000FF 8000FF FF0000', '0080FF 000000 0080FF 0080FF 000000']],
  ['Standoff', 10, ['FFFFFF 00B3FF 0040FF FF0500 FF0500']],
  ['Alarm', 18, ['FF0000', '000000', 'FF0000', '000000', '000000', '000000'].map(all)],
  ['Disable', 10, [all('000000')]],
]

export const PRESETS: Record<string, { speed: number; colors: Frame[] }> = Object.fromEntries(
  RAW.map(([name, speed, frames]) => [name, {
    speed,
    colors: frames.map((f) => Object.fromEntries(f.split(' ').map((c, i) => [PRESET_ORDER[i], '#' + c.toLowerCase()])) as Frame),
  }]),
)

const black = (): Frame => Object.fromEntries(LEDS.map((l) => [l, '#000000'])) as Frame

export function applyPreset(doc: LightsDoc, name: string, animation = doc.active): LightsDoc {
  const d = structuredClone(doc)
  const p = PRESETS[name]!
  const an = d.animations[animation]!
  an.speed = p.speed
  an.frames = p.colors.length
  an.colors = Array.from({ length: FRAMES }, (_, f) => (f < p.colors.length ? { ...p.colors[f]! } : black()))
  return d
}

export function solid(doc: LightsDoc, color: string, animation = doc.active): LightsDoc {
  const d = structuredClone(doc)
  const an = d.animations[animation]!
  an.frames = 1
  an.colors = [Object.fromEntries(LEDS.map((l) => [l, color])) as Frame, ...Array.from({ length: FRAMES - 1 }, black)]
  return d
}
