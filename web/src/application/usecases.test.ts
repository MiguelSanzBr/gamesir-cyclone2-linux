import * as uc from './usecases'
import { DemoTransport } from '../adapters/demo/demo'
import { records } from '../adapters/demo/backup'
import { HEARTBEAT, VIBRATE, WRITE } from '../domain/frames'
import { hairTrigger, triggerRange } from '../domain/values'

const sent = (t: DemoTransport, cmd: number) => t.log.filter((r) => r[1] === cmd)

describe('casos de uso', () => {
  let t: DemoTransport
  let c: uc.Connected
  beforeEach(async () => {
    t = new DemoTransport()
    c = (await uc.connect(t, () => {}))!
  })
  afterEach(() => uc.disconnect(c.session))

  it('Connect: lê info, perfil ativo e luzes; null quando o usuário cancela', async () => {
    expect(c.info).toEqual({ name: 'Cyclone 2 (demo)', pid: 0x1053, mode: 'Cyclone 2 (cabo, ADC)', demo: true, firmware: '3.5.6', dongle: '', active: 1 })
    expect([c.profile.id, c.profile.base, c.lighting.base]).toEqual([1, records()[1], records()[32]])
    expect(await uc.connect(null, () => {})).toBeNull()
  })

  it('Connect avisa a bateria do stream 0x12', async () => {
    const seen: [number, boolean][] = []
    const c2 = (await uc.connect(new DemoTransport(), (b, ch) => seen.push([b, ch])))!
    expect(seen[0]).toEqual([80, false])
    await uc.disconnect(c2.session)
  })

  it('Connect q falha fecha o canal e para o heartbeat', async () => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'setInterval', 'clearInterval'] })
    const bad = new DemoTransport()
    bad.drop = 1000
    const p = uc.connect(bad, () => {})
    const check = expect(p).rejects.toThrow('no answer to command 9')
    await vi.advanceTimersByTimeAsync(5000)
    await check
    const beats = sent(bad, HEARTBEAT).length
    await vi.advanceTimersByTimeAsync(5000)
    expect(sent(bad, HEARTBEAT).length).toBe(beats)
    vi.useRealTimers()
  })

  it('ReadProfile: perfil escolhido e luzes de novo', async () => {
    const r = await uc.readProfile(c.session, 3)
    expect([r.profile.id, r.profile.base, r.lighting.base]).toEqual([3, records()[3], records()[32]])
  })

  it('PlanChanges: nada editado, plano vazio', () => {
    expect(uc.planChanges(c.profile, c.lighting)).toMatchObject({ profile: c.profile, lighting: c.lighting, changeSets: [], changes: [], bytes: 0 })
  })

  it('PlanChanges: um ChangeSet por registro mudado, com a lista legível', () => {
    const p = uc.setHairTrigger(c.profile, 'RT', hairTrigger(true, 2, 20, 80))
    const l = uc.editAnimation(c.lighting, 3, { brightness: 50 })
    const plan = uc.planChanges(p, l)
    expect(plan.changeSets.map((s) => [s.record, s.start, s.end])).toEqual([[1, 534, 537], [32, 376, 377]])
    expect(plan.bytes).toBe(4)
    expect(plan.changes.map((x) => x.label)).toEqual(['RT: hair trigger', 'Animação 4: brilho'])
  })

  it('ApplyChanges sem confirmação não grava nada', async () => {
    const plan = uc.planChanges(uc.rename(c.profile, 'X'), c.lighting)
    await expect(uc.applyChanges(c.session, plan, false)).rejects.toThrow('confirmação')
    expect(sent(t, WRITE)).toHaveLength(0)
    expect(t.records[1]).toEqual(records()[1])
  })

  it('ApplyChanges confirmado grava só os intervalos, confere e devolve a nova base', async () => {
    const p = uc.setTriggerRange(c.profile, 'LT', triggerRange(10, 90))
    const l = uc.setActiveAnimation(c.lighting, 0)
    const r = await uc.applyChanges(c.session, uc.planChanges(p, l), true)
    expect(sent(t, WRITE).map((w) => [w[2], (w[3]! << 8) | w[4]!, w[5]])).toEqual([[1, 497, 22], [32, 0, 1]])
    expect(r.bytes).toBe(23)
    expect(uc.planChanges(r.profile, r.lighting).changeSets).toEqual([])
    expect(r.profile.doc.triggers.LT.deadzone).toEqual([10, 90, 0, 100])
    expect(t.records[32]![0]).toBe(0)
  })

  it('ApplyChanges estoura se o controle não guardar', async () => {
    t.corrupt = true
    await expect(uc.applyChanges(c.session, uc.planChanges(uc.rename(c.profile, 'X'), c.lighting), true)).rejects.toThrow('verificação falhou')
  })

  it('ApplyChanges com plano vazio não manda nada', async () => {
    const r = await uc.applyChanges(c.session, uc.planChanges(c.profile, c.lighting), true)
    expect(r.bytes).toBe(0)
    expect(sent(t, WRITE)).toHaveLength(0)
  })

  it('SwitchActiveProfile troca e confere', async () => {
    expect(await uc.switchActiveProfile(c.session, 3)).toBe(3)
    expect(t.current).toBe(3)
  })

  it('WatchInput e SimulatePress: o desenho acompanha o controle simulado', async () => {
    const seen: string[][] = []
    const off = uc.watchInput(c.session, (i) => seen.push([...i.pressed]))
    uc.simulatePress(c.session, 'Home', true)
    await Promise.resolve()
    off()
    expect(seen).toEqual([[], ['Home']])
  })

  it('teste de vibração', async () => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
    const p = uc.rumbleTest(c.session)
    await vi.advanceTimersByTimeAsync(1000)
    await p
    expect(sent(t, VIBRATE)).toHaveLength(2)
    vi.useRealTimers()
  })

  it('edições e objetos de valor saem pela application', () => {
    expect(uc.PRESET_NAMES).toEqual(['Flow', 'Rainbow', 'Pulse', 'Standoff', 'Alarm', 'Disable'])
    expect(uc.applyLightPreset(c.lighting, 'Disable', 0).doc.animations[0]!.frames).toBe(1)
    expect(uc.setFrameColor(c.lighting, 0, 0, 'home', '#123456').doc.animations[0]!.colors[0]!.home).toBe('#123456')
    expect(uc.LEDS).toHaveLength(5)
    expect(uc.profileId(2)).toBe(2)
    expect(uc.hairTrigger(false, 1, 1, 2).on).toBe(false)
    expect(uc.triggerRange(0, 50).end).toBe(50)
  })
})
