import { FRAMES, LEDS, PRESETS, applyPreset, decode, encode, solid } from './lighting'
import { changedSpan } from './profile'
import { records } from '../adapters/demo/backup'
import * as F from '../test/fixtures'
import { hex } from '../test/hex'

const base = () => records()[32]!

describe('light', () => {
  it('decode do registro 32 do backup é igual ao do Python (light.decode)', () => {
    expect(decode(base())).toEqual(F.LIGHTS)
  })

  it('decode recusa tamanho errado', () => {
    expect(() => decode(new Uint8Array(5))).toThrow('635')
  })

  it('decode prende animação ativa, velocidade e brilho (conferido no Python)', () => {
    const b = base()
    b.set([7], 0)
    b.set([25, 150], 3)
    const d = decode(b)
    expect([d.active, d.animations[0]!.speed, d.animations[0]!.brightness]).toEqual([0, 0, 100])
  })

  it('encode sem mudança devolve os mesmos bytes', () => {
    expect(encode(decode(base()), base())).toEqual(base())
  })

  it('preset Rainbow na animação 1, ativa e brilho 70 (light.apply_preset + encode + changed_span)', () => {
    const d = applyPreset(decode(base()), 'Rainbow', 1)
    d.active = 1
    d.animations[1]!.brightness = 70
    const n = encode(d, base())
    const [s, e] = changedSpan(base(), n)!
    expect({ span: [s, e], bytes: hex(n.slice(s, e)) }).toEqual(F.LIGHT_EDIT)
  })

  it('encode prende a velocidade em 0-20 (conferido no Python: bytes 20 e 0)', () => {
    const d = decode(base())
    d.animations[0]!.speed = 99
    d.animations[1]!.speed = -5
    const n = encode(d, base())
    expect([n[3], n[1 + 124 + 2]]).toEqual([0, 20])
  })

  it('cauda: LED do perfil e standby (conferido no Python: span 624-628, 0000010a)', () => {
    const d = decode(base())
    Object.assign(d, { standby: 10, raise_to_wake: true, profile_led: '#ff0000', audio_reactive: true })
    const n = encode(d, base())
    const [s, e] = changedSpan(base(), n)!
    expect([s, e, hex(n.slice(s, e))]).toEqual([624, 628, '0000010a'])
  })

  it('presets iguais ao light.PRESETS', () => {
    expect(PRESETS).toEqual(F.PRESETS)
  })

  it('preset na animação ativa completa com quadros pretos (light.apply_preset)', () => {
    const before = decode(base())
    const d = applyPreset(before, 'Pulse')
    const an = d.animations[3]!
    expect([d.active, an.frames, an.speed]).toEqual([3, 2, 5])
    expect(an.colors[1]).toEqual({ home: '#0080ff', upper_left: '#000000', lower_left: '#0080ff', lower_right: '#0080ff', upper_right: '#000000' })
    expect(an.colors[2]).toEqual(Object.fromEntries(LEDS.map((l) => [l, '#000000'])))
    expect(an.colors).toHaveLength(FRAMES)
    expect(before).toEqual(F.LIGHTS)
  })

  it('solid pinta um quadro só (light.solid)', () => {
    expect(solid(decode(base()), '#00ffaa', 2).animations[2]).toEqual(F.SOLID_ANIM_2)
    const an = solid(decode(base()), '#123456').animations[3]!
    expect([an.frames, an.colors[0]]).toEqual([1, Object.fromEntries(LEDS.map((l) => [l, '#123456']))])
  })
})
