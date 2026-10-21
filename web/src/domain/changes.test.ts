import { lightChanges, profileChanges } from './changes'
import { decode } from './profile'
import { applyPreset, decode as decodeLights } from './lighting'
import { setDeadzone } from './profile'
import { records } from '../adapters/demo/backup'

describe('lista de mudanças pra confirmação', () => {
  it('nada mudou, lista vazia', () => {
    const d = decode(records()[1]!)
    expect(profileChanges(d, structuredClone(d))).toEqual([])
    const l = decodeLights(records()[32]!)
    expect(lightChanges(l, structuredClone(l))).toEqual([])
  })

  it('nome, zona morta (com a curva q ela refaz) e hair trigger', () => {
    const a = decode(records()[1]!)
    const b = structuredClone(a)
    b.name = 'Corrida'
    setDeadzone(b.triggers.LT, [10, 90, 0, 100])
    b.triggers.LT.hair_trigger = { on: false, mode: 1, start: 10, end: 90 }
    b.triggers.RT.hair_trigger = { on: true, mode: 2, start: 20, end: 80 }
    expect(profileChanges(a, b)).toEqual([
      { label: 'Nome do perfil', from: '(sem nome)', to: 'Corrida' },
      { label: 'LT: zona morta', from: '5% a 95%', to: '10% a 90%' },
      { label: 'LT: pontos da curva (refeitos pela zona morta)', from: '0,0 57,64 128,128 198,191 255,255', to: '0,0 48,64 128,128 207,191 255,255' },
      { label: 'LT: hair trigger', from: 'adaptativo, 10% a 90%', to: 'desligado' },
      { label: 'RT: hair trigger', from: 'adaptativo, 10% a 90%', to: 'fixo, 20% a 80%' },
    ])
  })

  it('zona morta religada aparece', () => {
    const a = decode(records()[1]!)
    a.triggers.RT.deadzone_on = false
    const b = structuredClone(a)
    b.triggers.RT.deadzone_on = true
    expect(profileChanges(a, b)).toEqual([{ label: 'RT: zona morta ligada', from: 'não', to: 'sim' }])
  })

  it('luzes: animação ativa, brilho, velocidade, quadros e cores por quadro', () => {
    const a = decodeLights(records()[32]!)
    const b = applyPreset(a, 'Pulse', 1)
    b.active = 1
    b.animations[1]!.brightness = 70
    expect(lightChanges(a, b)).toEqual([
      { label: 'Animação ativa', from: '4', to: '2' },
      { label: 'Animação 2: brilho', from: '100%', to: '70%' },
      { label: 'Animação 2: velocidade', from: '17', to: '5' },
      { label: 'Animação 2: quadros', from: '5', to: '2' },
      expect.objectContaining({ label: 'Animação 2, quadro 1' }),
      expect.objectContaining({ label: 'Animação 2, quadro 2' }),
      expect.objectContaining({ label: 'Animação 2, quadro 3', to: '#000000 #000000 #000000 #000000 #000000' }),
      expect.objectContaining({ label: 'Animação 2, quadro 4' }),
      expect.objectContaining({ label: 'Animação 2, quadro 5' }),
    ])
  })
})
