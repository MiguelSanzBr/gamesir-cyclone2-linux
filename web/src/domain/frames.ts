// Port do src/cyclone2/protocol.py. Funções puras, nada de I/O aqui.
import { InvariantError } from './errors'

export const VID = 0x3537
// PIDs dos modos q aceitam configuração (ConfigModePid no GameSir Connect)
export const PIDS: Record<number, string> = {
  0x101d: 'Cyclone 2 (cabo)',
  0x102a: 'Cyclone 2 (2.4G)',
  0x1053: 'Cyclone 2 (cabo, ADC)',
  0x100b: 'Cyclone 2 (2.4G, dongle)',
}
export const USAGE_PAGE = 0xfff0

export const REPORT_SIZE = 64
export const OUT = 0x0f
export const ANSWER = 0x10
export const STATE = 0x12

export const WRITE = 3
export const READ = 4
export const READ_ACK = 5
export const ACK = 6
export const SWITCH = 7
export const FIRMWARE = 9
export const FIRMWARE_ACK = 10
export const CURRENT = 11
export const CURRENT_ACK = 12
export const VIBRATE = 32
export const HEARTBEAT = 242

export const PROFILES = [1, 2, 3, 4] as const
export const SHIFT = 5
export const LIGHTS = 32
export const PROFILE_SIZE = 680
export const LIGHT_SIZE = 635
export const CHUNK = 58

export const sizeOf = (profile: number): number => (profile === LIGHTS ? LIGHT_SIZE : PROFILE_SIZE)

export function command(cmd: number, ...args: number[]): Uint8Array {
  const r = new Uint8Array(REPORT_SIZE)
  r.set([OUT, cmd, ...args])
  return r
}

export function readRequests(profile: number, start = 0, end = sizeOf(profile)): Uint8Array[] {
  const out = []
  for (let off = start; off < end; off += CHUNK) {
    out.push(command(READ, profile, off >> 8, off & 0xff, Math.min(CHUNK, end - off)))
  }
  return out
}

/** `0F 03 profile off_hi off_lo len data...`: até 58 bytes de dado e sem passar do fim do registro. */
export function writeFrame(profile: number, offset: number, data: Uint8Array): Uint8Array {
  if (data.length > CHUNK || offset + data.length > sizeOf(profile)) {
    throw new InvariantError(`escrita de ${data.length} bytes em ${offset} não cabe no registro ${profile}`)
  }
  return command(WRITE, profile, offset >> 8, offset & 0xff, data.length, ...data)
}

export function writeRequests(profile: number, data: Uint8Array, offset = 0): Uint8Array[] {
  const out = []
  for (let i = 0; i < data.length; i += CHUNK) out.push(writeFrame(profile, offset + i, data.subarray(i, i + CHUNK)))
  return out
}

/** Byte de comando de uma resposta 0x10, ou null pra qualquer outra coisa. */
export const kind = (r: Uint8Array): number | null => (r.length > 1 && r[0] === ANSWER ? r[1]! : null)

/** ACK com byte 2 = 1 é "ocupado, manda de novo". */
export const busy = (r: Uint8Array): boolean => kind(r) === ACK && r[2] === 1

export function chunk(r: Uint8Array): { profile: number; offset: number; data: Uint8Array } {
  return { profile: r[2]!, offset: (r[3]! << 8) | r[4]!, data: r.slice(6, 6 + r[5]!) }
}

/** Os bytes da versão são caracteres separados por NUL: "3\0 5\0 6" vira "3.5.6". */
export function version(raw: Uint8Array): string {
  return [...new TextDecoder().decode(raw)].filter((c) => c.trim() !== '' && c !== '\0').join('.')
}

export const firmware = (r: Uint8Array): [string, string] => [version(r.slice(4, 9)), version(r.slice(12, 17))]

// Report 0x12: os bytes 53-62 repetem o bloco de entrada com o input físico (antes de remap e hair trigger)
export const RAW = 53
export const STATE_BITS: Record<number, Record<number, string>> = {
  5: { 4: 'X', 5: 'A', 6: 'B', 7: 'Y' },
  6: { 0: 'LB', 1: 'RB', 2: 'LT', 3: 'RT', 4: 'View', 5: 'Menu', 6: 'LS', 7: 'RS' },
  7: { 0: 'Home', 1: 'Capture', 3: 'L4', 4: 'R4', 5: 'M' },
}
export const HAT: string[][] = [['Up'], ['Up', 'Right'], ['Right'], ['Down', 'Right'], ['Down'], ['Down', 'Left'], ['Left'], ['Up', 'Left']]

export interface PadState {
  pressed: Set<string>
  left: [number, number]
  right: [number, number]
  lt: number
  rt: number
  charging: number
  battery: number
  animation: number
}

export function state(report: Uint8Array): PadState | null {
  if (report.length < REPORT_SIZE || report[0] !== STATE) return null
  const r = report.subarray(RAW, RAW + 10)
  const axis = (v: number) => (v - 128) / (v >= 128 ? 127 : 128)
  const pressed = new Set<string>()
  for (const [byte, bits] of Object.entries(STATE_BITS)) {
    for (const [bit, name] of Object.entries(bits)) if ((r[+byte]! >> +bit) & 1) pressed.add(name)
  }
  for (const d of HAT[r[5]! & 0x0f] ?? []) pressed.add(d)
  return {
    pressed,
    left: [axis(r[1]!), axis(r[2]!)],
    right: [axis(r[3]!), axis(r[4]!)],
    lt: r[8]!,
    rt: r[9]!,
    charging: report[35]!,
    battery: report[36]!,
    animation: report[37]!,
  }
}

/** Só o input físico, o q o PadInput.pad_state do app Linux guarda pra acender o desenho. */
export type InputState = Pick<PadState, 'pressed' | 'left' | 'right' | 'lt' | 'rt'>
export const IDLE: InputState = { pressed: new Set(), left: [0, 0], right: [0, 0], lt: 0, rt: 0 }

// o 0x12 chega sem parar e o analógico parado treme 1 ou 2 passos; abaixo disso não vale redesenhar
const AXIS_STEP = 0.02
const TRIGGER_STEP = 3

export function sameInput(a: InputState, b: InputState): boolean {
  const near = (x: number[], y: number[], step: number) => x.every((v, i) => Math.abs(v - y[i]!) < step)
  return a.pressed.size === b.pressed.size && [...a.pressed].every((n) => b.pressed.has(n))
    && near([...a.left, ...a.right], [...b.left, ...b.right], AXIS_STEP) && near([a.lt, a.rt], [b.lt, b.rt], TRIGGER_STEP)
}
