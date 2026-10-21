import { changedSpan, curve, curvePercent, decode, encode, setDeadzone, type ProfileDoc } from './profile'
import { records } from '../adapters/demo/backup'
import * as F from '../test/fixtures'
import { hex } from '../test/hex'

const base = () => records()[1]!
const edit = (change: (d: ProfileDoc) => void) => {
  const b = base()
  const d = decode(b)
  change(d)
  const n = encode(d, b)
  const s = changedSpan(b, n)
  return { n, s, out: s && { span: [s[0], s[1]], bytes: hex(n.slice(s[0], s[1])) } }
}

describe('profile', () => {
  it('decode do perfil 1 do backup é igual ao do Python (profile.decode)', () => {
    expect(decode(base())).toEqual(F.PROFILE_1)
  })

  it('decode recusa tamanho errado', () => {
    expect(() => decode(new Uint8Array(10))).toThrow('680')
  })

  it('encode sem mudança devolve os mesmos bytes', () => {
    const b = base()
    expect(encode(decode(b), b)).toEqual(b)
    expect(changedSpan(b, b)).toBeNull()
  })

  it('nome, curto e cortado em caractere inteiro (profile.encode + changed_span)', () => {
    expect(edit((d) => (d.name = 'Corrida')).out).toEqual(F.ENC_NAME)
    expect(edit((d) => (d.name = 'ação'.repeat(10))).out).toEqual(F.ENC_NAME_LONG)
  })

  it('zona morta do LT refaz a curva (Editor._deadzone)', () => {
    const r = edit((d) => setDeadzone(d.triggers.LT, [10, 90, 0, 100]))
    expect(r.out).toEqual(F.ENC_LT_DEADZONE)
    expect(decode(r.n).triggers.LT).toMatchObject(F.LT_AFTER_DEADZONE)
  })

  it('setDeadzone igual não mexe em nada e prende os pontos no novo intervalo', () => {
    const d = decode(base())
    const before = structuredClone(d.triggers.LT)
    setDeadzone(d.triggers.LT, [5, 95, 0, 100])
    expect(d.triggers.LT).toEqual(before)
    setDeadzone(d.triggers.LT, [40, 60, 30, 70])
    // conferido no Python: Editor._deadzone(LT, [40, 60, 30, 70])
    expect(d.triggers.LT.curve.points).toEqual([[0, 0], [0, 0], [128, 128], [255, 255], [255, 255]])
    expect(d.triggers.LT.deadzone).toEqual([40, 60, 30, 70])
  })

  it('hair trigger liga, modo fixo, e desliga (profile.encode + changed_span)', () => {
    expect(edit((d) => (d.triggers.RT.hair_trigger = { on: true, mode: 2, start: 20, end: 80 })).out).toEqual(F.ENC_RT_HAIR)
    expect(edit((d) => (d.triggers.LT.hair_trigger = { on: false, mode: 1, start: 10, end: 90 })).out).toEqual(F.ENC_HAIR_OFF)
  })

  it('hair trigger ligado no modo adaptativo (conferido no Python: span 535-536, 0f)', () => {
    expect(edit((d) => (d.triggers.RT.hair_trigger = { on: true, mode: 1, start: 15, end: 90 })).out).toEqual({ span: [535, 536], bytes: '0f' })
  })

  it('nome de 32 bytes sem NUL no fim (profile.decode)', () => {
    const b = base()
    b.fill(0x41, 0, 32)
    expect(decode(b).name).toBe('A'.repeat(32))
  })

  it('decode do hair trigger lê o bit do modo', () => {
    const b = base()
    b[506] = 0x82
    expect(decode(b).triggers.LT.hair_trigger).toEqual({ on: true, mode: 2, start: 10, end: 90 })
  })

  it('macro, remap, roda, tecla do gyro e motor (profile.encode + decode)', () => {
    const r = edit((d) => {
      const doc = d as unknown as typeof F.DEC_MISC & { buttons: { A: { map: string[] } }; sticks: { left: { output: { wheel: Record<string, string> } } }; motion: { aim: { trigger_key: string } } }
      doc.macros.L4 = { on: true, press_to_trigger: true, cycle: false, cycle_time: 300, steps: [{ key: 'A', hold: 50, delay: 20 }, { key: 'KB_SPACE', hold: 258, delay: 0 }] }
      doc.buttons.A.map = ['B', 'MOUSE_LEFT']
      doc.sticks.left.output.wheel.up = 'KB_W'
      doc.motion.aim.trigger_key = '0x99'
      doc.motors.left = 25
    })
    expect(r.out).toEqual(F.ENC_MISC)
    const d = decode(r.n) as unknown as Record<string, Record<string, Record<string, unknown>>>
    expect({ macros: d.macros, motors: d.motors, A: d.buttons!.A, aim_key: d.motion!.aim!.trigger_key, wheel: (d.sticks!.left!.output as Record<string, unknown>).wheel })
      .toEqual(F.DEC_MISC)
  })

  it('macro com 30 passos: o último não tem delay', () => {
    const steps = Array.from({ length: 30 }, () => ({ key: 'B', hold: 1, delay: 7 }))
    const r = edit((d) => ((d.macros as Record<string, unknown>).R4 = { on: true, press_to_trigger: false, cycle: true, cycle_time: 1, steps }))
    expect(hex(r.n.slice(342, 346))).toBe('0500011e')
    const got = (decode(r.n).macros as Record<string, { steps: { delay: number }[] }>).R4!.steps
    expect(got).toHaveLength(30)
    expect(got[0]!.delay).toBe(7)
    expect(got[29]!.delay).toBe(0)
    r.n[345] = 40
    expect((decode(r.n).macros as Record<string, { steps: unknown[] }>).R4!.steps).toHaveLength(30)
  })

  it('macro ligada sem passos fica desligada', () => {
    expect(edit((d) => ((d.macros as Record<string, unknown>).R4 = { on: true, press_to_trigger: false, cycle: false, cycle_time: 0, steps: [] })).s).toBeNull()
  })

  it('decode do nome troca byte inválido e corta espaço; roda com código desconhecido', () => {
    const b = base()
    b.set([0x20, 0xff, 0x61, 0x20], 0)
    b.set([5, 0x30], 577)
    const d = decode(b)
    expect(d.name).toBe('�a')
    expect(((d.sticks as Record<string, Record<string, Record<string, unknown>>>).left!.output!.wheel)).toEqual({ up: 'LB', down: '0x30', left: '', right: '', center: '' })
  })

  it('documento parcial mantém o resto do base', () => {
    const b = base()
    const n = encode({ name: 'x', triggers: { LT: { deadzone_on: false } } } as unknown as ProfileDoc, b)
    expect(changedSpan(b, n)).toEqual([0, 497])
  })

  it('valores inválidos estouram como no Python (_put)', () => {
    type Loose = Record<string, Record<string, Record<string, unknown>>>
    const bad = (change: (d: Loose) => void) => () => edit((d) => change(d as unknown as Loose))
    expect(bad((d) => (d.buttons!.A!.map = ['A', 'B', 'X', 'Y']))).toThrow('at most 3 keys per button')
    expect(bad((d) => ((d.motors as unknown as Record<string, number>).left = 300))).toThrow('bad value 300 at offset 32')
    expect(bad((d) => (d.macros!.L4!.steps = Array(31).fill({ key: 'A', hold: 0, delay: 0 })))).toThrow('at most 30 macro steps')
    expect(bad((d) => (d.triggers!.LT!.deadzone = [1, 2, 3, NaN]))).toThrow('bad value')
  })

  it('curve e curvePercent iguais ao Python', () => {
    expect(curve([10, 90, 0, 100])).toEqual(F.CURVE_10_90)
    expect(curvePercent(F.PROFILE_1.triggers.LT.curve, [5, 95, 0, 100])).toEqual(F.CURVE_PERCENT)
  })
})
