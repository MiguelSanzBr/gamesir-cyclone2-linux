import { initial, pending, reducer, type State } from './state'
import { records } from '../demo/backup'
import { loadLighting, loadProfile, rename, setActiveAnimation } from '../../domain/aggregates'
import { controllerInfo } from '../../domain/values'

const info = controllerInfo({ demo: true, name: 'Cyclone 2 (demo)', pid: 0x1053, firmware: '3.5.6', dongle: '', active: 2 })
const recs = (n: 1 | 2 | 3 | 4) => ({ profile: loadProfile(n, records()[n]!), lighting: loadLighting(records()[32]!) })
const ready = (): State => reducer(initial, { type: 'connected', info, ...recs(2) })

describe('reducer', () => {
  it('conectado: edita o perfil ativo, nada pendente', () => {
    const s = ready()
    expect([s.profile!.id, s.info!.active, s.profile!.doc.name, s.lighting!.doc.active, s.busy]).toEqual([2, 2, '', 3, null])
    expect(s.status.text).toMatch(/demo/i)
    expect(pending(s)!.changeSets).toEqual([])
  })

  it('conectado em controle de verdade tem outro texto', () => {
    const s = reducer(initial, { type: 'connected', info: { ...info, demo: false }, ...recs(1) })
    expect(s.status.text).toBe('Configuração lida do controle.')
  })

  it('sem conexão não tem nada pendente', () => {
    expect(pending(initial)).toBeNull()
  })

  it('ocupado, erro e feito', () => {
    let s = reducer(ready(), { type: 'busy', text: 'Lendo…' })
    expect([s.busy, s.status]).toEqual(['Lendo…', { text: 'Lendo…', error: false }])
    s = reducer({ ...s, confirming: true }, { type: 'error', text: 'falhou' })
    expect([s.busy, s.confirming, s.status]).toEqual([null, false, { text: 'falhou', error: true }])
    s = reducer(reducer(s, { type: 'busy', text: 'x' }), { type: 'done', text: 'pronto' })
    expect([s.busy, s.status.text]).toEqual([null, 'pronto'])
  })

  it('edição fica pendente até gravar, e descartar volta pro q tá no controle', () => {
    let s = ready()
    s = reducer(s, { type: 'edit', profile: rename(s.profile!, 'X') })
    s = reducer(s, { type: 'editLights', lighting: setActiveAnimation(s.lighting!, 0) })
    const p = pending(s)!
    expect(p.changeSets.map((c) => [c.record, c.start, c.end])).toEqual([[2, 0, 1], [32, 0, 1]])
    expect(p.changes.map((c) => c.label)).toEqual(['Nome do perfil', 'Animação ativa'])
    s = reducer(s, { type: 'review' })
    expect(s.confirming).toBe(true)
    s = reducer(s, { type: 'cancel' })
    expect(s.confirming).toBe(false)
    s = reducer(s, { type: 'discard' })
    expect([s.profile!.doc.name, s.lighting!.doc.active, s.status.text]).toEqual(['', 3, 'Alterações descartadas.'])
  })

  it('gravado: o q foi conferido vira a nova base', () => {
    const base = records()[2]!
    base[0] = 0x41
    const s = reducer({ ...ready(), confirming: true, busy: 'Gravando…' }, { type: 'saved', profile: loadProfile(2, base), lighting: loadLighting(records()[32]!), bytes: 1 })
    expect([s.profile!.doc.name, s.stored!.profile.doc.name, s.confirming, s.busy, s.status.text]).toEqual(['A', 'A', false, null, 'Gravado e conferido no controle (1 bytes).'])
  })

  it('perfil lido de novo e perfil ativo trocado', () => {
    let s = reducer(ready(), { type: 'loaded', ...recs(3) })
    expect([s.profile!.id, s.status.text]).toEqual([3, 'Perfil 3 lido do controle.'])
    s = reducer(s, { type: 'switched', n: 3 })
    expect([s.info!.active, s.status.text]).toEqual([3, 'Perfil 3 ativo no controle.'])
  })

  it('bateria só muda o estado quando muda de verdade', () => {
    const s = reducer(ready(), { type: 'battery', battery: 80, charging: false })
    expect([s.battery, s.charging]).toEqual([80, false])
    expect(reducer(s, { type: 'battery', battery: 80, charging: false })).toBe(s)
    expect(reducer(s, { type: 'battery', battery: 80, charging: true }).charging).toBe(true)
  })

  it('desconectar zera tudo', () => {
    const s = reducer(ready(), { type: 'disconnected' })
    expect([s.info, s.profile, s.status.text]).toEqual([null, null, 'Desconectado.'])
  })
})
