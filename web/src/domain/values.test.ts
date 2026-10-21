import { InvariantError, animationIndex, brightness, color, controllerInfo, frameCount, hairTrigger, profileId, speed, triggerRange } from './values'
import { CHUNK, WRITE, writeFrame } from './frames'

describe('objetos de valor', () => {
  it('ProfileId só 1-4', () => {
    expect([1, 2, 3, 4].map(profileId)).toEqual([1, 2, 3, 4])
    for (const n of [0, 5, 32, 1.5]) expect(() => profileId(n)).toThrow(InvariantError)
  })

  it('TriggerRange: inteiros 0-100 com início <= fim', () => {
    expect(triggerRange(5, 95)).toEqual({ start: 5, end: 95 })
    expect(triggerRange(50, 50)).toEqual({ start: 50, end: 50 })
    for (const [a, b] of [[-1, 50], [10, 101], [60, 40], [1.5, 50]]) expect(() => triggerRange(a!, b!)).toThrow(InvariantError)
  })

  it('HairTrigger: modo 1 (adaptativo) ou 2 (fixo), faixa 0-100', () => {
    expect(hairTrigger(true, 2, 20, 80)).toEqual({ on: true, mode: 2, start: 20, end: 80 })
    expect(() => hairTrigger(true, 3, 20, 80)).toThrow(InvariantError)
    expect(() => hairTrigger(false, 1, 20, 180)).toThrow(InvariantError)
  })

  it('luzes: animação 0-3, brilho 0-100, velocidade 0-20, quadros 1-8, cor #rrggbb', () => {
    expect([animationIndex(3), brightness(100), speed(20), frameCount(8), color('#00FFaa')]).toEqual([3, 100, 20, 8, '#00ffaa'])
    expect(() => animationIndex(4)).toThrow(InvariantError)
    expect(() => brightness(101)).toThrow(InvariantError)
    expect(() => speed(21)).toThrow(InvariantError)
    expect(() => frameCount(0)).toThrow(InvariantError)
    expect(() => color('red')).toThrow(InvariantError)
  })

  it('ControllerInfo traz o nome do modo pelo PID', () => {
    expect(controllerInfo({ name: 'x', pid: 0x102a, demo: false, firmware: '3.5.6', dongle: '1.2', active: 2 })).toEqual({
      name: 'x', pid: 0x102a, mode: 'Cyclone 2 (2.4G)', demo: false, firmware: '3.5.6', dongle: '1.2', active: 2,
    })
    expect(controllerInfo({ name: 'x', pid: 0x1234, demo: false, firmware: '', dongle: '', active: 1 }).mode).toBe('modo 0x1234')
  })
})

describe('frame de escrita', () => {
  it('no máximo 58 bytes de dado e dentro do registro', () => {
    const f = writeFrame(1, 600, new Uint8Array(CHUNK))
    expect([f[1], f[2], (f[3]! << 8) | f[4]!, f[5]]).toEqual([WRITE, 1, 600, 58])
    expect(() => writeFrame(1, 0, new Uint8Array(CHUNK + 1))).toThrow(InvariantError)
    expect(() => writeFrame(1, 670, new Uint8Array(20))).toThrow(InvariantError)
    expect(() => writeFrame(32, 630, new Uint8Array(5))).not.toThrow()
  })
})
