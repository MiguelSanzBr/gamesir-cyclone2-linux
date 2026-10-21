import { applyLightPreset, editAnimation, lightingChangeSet, loadLighting, loadProfile, profileChangeSet, rename, setActiveAnimation, setFrameColor, setHairTrigger, setTriggerRange } from './aggregates'
import { hairTrigger, profileId, triggerRange } from './values'
import { records } from '../adapters/demo/backup'
import * as F from '../test/fixtures'
import { hex } from '../test/hex'

const profile = () => loadProfile(profileId(1), records()[1]!)
const lighting = () => loadLighting(records()[32]!)

describe('agregado Profile', () => {
  it('carregado do controle não tem mudança', () => {
    const p = profile()
    expect(p.id).toBe(1)
    expect(p.doc.triggers.LT.deadzone).toEqual([5, 95, 0, 100])
    expect(profileChangeSet(p)).toBeNull()
  })

  it('edições não mexem no original e viram um ChangeSet com o intervalo de bytes (profile.encode + changed_span)', () => {
    const p = profile()
    const q = setHairTrigger(setTriggerRange(rename(p, 'Corrida'), 'LT', triggerRange(10, 90)), 'RT', hairTrigger(true, 2, 20, 80))
    expect(profileChangeSet(p)).toBeNull()
    const cs = profileChangeSet(q)!
    expect([cs.record, cs.start, cs.end]).toEqual([1, 0, 537])
    expect(hex(cs.next.slice(0, 7))).toBe(F.ENC_NAME.bytes)
    expect(hex(cs.next.slice(497, 519))).toBe(F.ENC_LT_DEADZONE.bytes)
    expect(hex(cs.next.slice(534, 537))).toBe(F.ENC_RT_HAIR.bytes)
    expect(cs.old).toEqual(records()[1])
  })

  it('só o hair trigger: ChangeSet de 3 bytes', () => {
    const cs = profileChangeSet(setHairTrigger(profile(), 'RT', hairTrigger(true, 2, 20, 80)))!
    expect([cs.start, cs.end]).toEqual(F.ENC_RT_HAIR.span)
  })
})

describe('agregado Lighting', () => {
  it('preset, animação ativa e brilho dão o mesmo ChangeSet do Python (light.apply_preset + encode)', () => {
    const l = editAnimation(setActiveAnimation(applyLightPreset(lighting(), 'Rainbow', 1), 1), 1, { brightness: 70 })
    const cs = lightingChangeSet(l)!
    expect({ span: [cs.start, cs.end], bytes: hex(cs.next.slice(cs.start, cs.end)) }).toEqual(F.LIGHT_EDIT)
    expect(cs.record).toBe(32)
    expect(lightingChangeSet(lighting())).toBeNull()
  })

  it('velocidade, quadros e cor de um LED num quadro', () => {
    const l = setFrameColor(editAnimation(lighting(), 0, { speed: 3, frames: 2 }), 0, 1, 'home', '#00FFaa')
    const an = l.doc.animations[0]!
    expect([an.speed, an.frames, an.colors[1]!.home]).toEqual([3, 2, '#00ffaa'])
    expect(lighting().doc.animations[0]!.speed).toBe(10)
  })

  it('valores fora da faixa estouram', () => {
    expect(() => editAnimation(lighting(), 0, { brightness: 200 })).toThrow()
    expect(() => setActiveAnimation(lighting(), 4)).toThrow()
    expect(() => setFrameColor(lighting(), 0, 8, 'home', '#000000')).toThrow()
  })
})
