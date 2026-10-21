import {
  ACK, ANSWER, CHUNK, CURRENT_ACK, HEARTBEAT, LIGHTS, LIGHT_SIZE, PIDS, PROFILE_SIZE, READ, READ_ACK, REPORT_SIZE,
  IDLE, RAW, SHIFT, STATE, SWITCH, VIBRATE, busy, chunk, command, firmware, kind, readRequests, sameInput, sizeOf, state,
  version, writeRequests,
} from './frames'
import * as F from '../test/fixtures'
import { hex, unhex } from '../test/hex'

const answer = (...a: number[]) => {
  const r = new Uint8Array(REPORT_SIZE)
  r.set([ANSWER, ...a])
  return r
}

describe('protocol', () => {
  it('tamanhos dos registros (protocol.size_of)', () => {
    expect(sizeOf(LIGHTS)).toBe(LIGHT_SIZE)
    expect(LIGHT_SIZE).toBe(635)
    for (const n of [1, 2, 3, 4, SHIFT]) expect(sizeOf(n)).toBe(PROFILE_SIZE)
    expect(PROFILE_SIZE).toBe(680)
  })

  it('PIDs dos modos configuráveis (protocol.PIDS)', () => {
    expect(Object.keys(PIDS).map(Number).sort()).toEqual([0x100b, 0x101d, 0x102a, 0x1053])
  })

  it('command monta o report de 64 bytes igual ao Python', () => {
    expect(hex(command(SWITCH, 3))).toBe(F.COMMAND_SWITCH_3)
    expect(hex(command(HEARTBEAT, 0))).toBe(F.COMMAND_HEARTBEAT)
    expect(hex(command(VIBRATE, 102, 85, 160, 160))).toBe(F.COMMAND_VIBRATE)
  })

  it('readRequests cobre o intervalo em pacotes de 58', () => {
    expect(readRequests(1, 100, 200).map(hex)).toEqual(F.READ_REQUESTS_1_100_200)
    const all = readRequests(LIGHTS)
    expect(all).toHaveLength(11)
    expect(hex(all[10]!)).toBe(F.READ_REQUESTS_32_LAST)
    expect(all.every((r) => r[1] === READ)).toBe(true)
  })

  it('writeRequests quebra os dados com offset', () => {
    const data = Uint8Array.from({ length: 150 }, (_, i) => i)
    expect(writeRequests(2, data, 300).map(hex)).toEqual(F.WRITE_REQUESTS_2_300)
    expect(writeRequests(1, new Uint8Array(0))).toEqual([])
    expect(writeRequests(1, new Uint8Array(CHUNK))).toHaveLength(1)
  })

  it('kind, busy e chunk', () => {
    expect(kind(answer(ACK, 0))).toBe(ACK)
    expect(kind(Uint8Array.of(STATE, 5))).toBeNull()
    expect(kind(Uint8Array.of(ANSWER))).toBeNull()
    expect(kind(new Uint8Array(0))).toBeNull()
    expect(busy(answer(ACK, 1))).toBe(true)
    expect(busy(answer(ACK, 0))).toBe(false)
    expect(busy(answer(READ_ACK, 1))).toBe(false)
    expect(chunk(answer(READ_ACK, 1, 1, 2, 3, 9, 8, 7, 6))).toEqual({ profile: 1, offset: 258, data: Uint8Array.of(9, 8, 7) })
  })

  it('version e firmware', () => {
    const enc = (s: string) => new TextEncoder().encode(s)
    expect(version(enc('3\x005\x006'))).toBe('3.5.6')
    expect(version(enc('1\x002\x00 \x00'))).toBe('1.2')
    expect(version(new Uint8Array(3))).toBe('')
    expect(firmware(unhex(F.FIRMWARE_REPORT))).toEqual(F.FIRMWARE)
  })

  it('state decodifica o report 0x12 igual ao Python', () => {
    const s = state(unhex(F.STATE_REPORT))!
    expect({ ...s, pressed: [...s.pressed].sort() }).toEqual(F.STATE)
  })

  it('state recusa outros reports', () => {
    expect(state(new Uint8Array(10))).toBeNull()
    expect(state(answer(CURRENT_ACK, 1))).toBeNull()
  })

  it('state: direções diagonais e hat neutro', () => {
    const r = unhex(F.STATE_REPORT)
    r.fill(0, 53)
    r[58] = 0x0f
    expect(state(r)!.pressed.size).toBe(0)
    r[58] = 5
    expect([...state(r)!.pressed].sort()).toEqual(['Down', 'Left'])
  })

  it('state: analógicos e gatilho no meio, igual ao Python', () => {
    const s = state(unhex(F.STATE_REPORT_2))!
    expect({ ...s, pressed: [...s.pressed].sort() }).toEqual(F.STATE_2)
  })

  // espelha o test_state_every_button_and_direction do tests/test_protocol.py
  it.each(Object.entries(F.STATE_RAW_EACH))('state: só o %s apertado', (name, raw) => {
    const r = unhex(F.STATE_REPORT)
    r.set(unhex(raw), RAW)
    expect([...state(r)!.pressed]).toEqual([name])
  })
})

describe('input ao vivo', () => {
  const input = (report: string) => state(unhex(report))!

  it('IDLE é o controle parado', () => {
    expect(IDLE).toEqual({ pressed: new Set(), left: [0, 0], right: [0, 0], lt: 0, rt: 0 })
  })

  it('sameInput ignora bateria, LED e tremidinha do analógico', () => {
    const a = input(F.STATE_REPORT_2)
    const b = { ...a, battery: 90, charging: 1, animation: 3, left: [a.left[0] + 0.01, a.left[1]] as [number, number], lt: a.lt + 2 }
    expect(sameInput(a, b)).toBe(true)
    expect(sameInput(IDLE, input(F.STATE_REPORT_2))).toBe(false)
  })

  it('sameInput: muda botão, analógico ou gatilho', () => {
    const a = input(F.STATE_REPORT_2)
    expect(sameInput(a, { ...a, pressed: new Set([...a.pressed].slice(1)) })).toBe(false)
    expect(sameInput(a, { ...a, pressed: new Set([...a.pressed].slice(1).concat('A')) })).toBe(false)
    expect(sameInput(a, { ...a, right: [a.right[0], a.right[1] + 0.05] })).toBe(false)
    expect(sameInput(a, { ...a, rt: 5 })).toBe(false)
  })
})
