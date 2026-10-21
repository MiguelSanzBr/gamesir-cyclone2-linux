import { ConfigSession, NoAnswer, RESEND, TRIES } from './session'
import { DemoTransport } from '../adapters/demo/demo'
import { records } from '../adapters/demo/backup'
import type { ControllerChannel } from './ports'
import { ACK, ANSWER, CURRENT, CURRENT_ACK, HEARTBEAT, IDLE, LIGHTS, READ, READ_ACK, REPORT_SIZE, SWITCH, VIBRATE, WRITE, type InputState } from '../domain/frames'
import * as F from '../test/fixtures'
import { hex } from '../test/hex'

// espelha o tests/test_device.py
const answer = (...a: number[]) => {
  const r = new Uint8Array(REPORT_SIZE)
  r.set([ANSWER, ...a])
  return r
}

/** Transporte onde o teste decide o q volta pra cada report enviado. */
class Scripted implements ControllerChannel {
  readonly demo = false
  readonly name = 'roteiro'
  readonly pid = 0
  sent: Uint8Array[] = []
  private cbs = new Set<(r: Uint8Array) => void>()
  constructor(private reply: (r: Uint8Array, i: number) => Uint8Array[]) {}
  async send(r: Uint8Array) {
    this.sent.push(r)
    const out = this.reply(r, this.sent.length - 1)
    queueMicrotask(() => out.forEach((x) => this.cbs.forEach((cb) => cb(x))))
  }
  listen(cb: (r: Uint8Array) => void) {
    this.cbs.add(cb)
    return () => this.cbs.delete(cb)
  }
  async close() {}
}

const sentCmd = (t: DemoTransport, cmd: number) => t.log.filter((r) => r[1] === cmd)

let t: DemoTransport
let c: ConfigSession

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'setInterval', 'clearInterval'] })
  t = new DemoTransport()
  c = new ConfigSession(t)
})

afterEach(async () => {
  await c.close()
  vi.useRealTimers()
})

const settle = async <T,>(p: Promise<T>) => {
  await vi.advanceTimersByTimeAsync(RESEND * (TRIES + 1))
  return p
}

describe('ConfigSession', () => {
  it('manda heartbeat ao abrir e a cada 1 s, e para no close', async () => {
    expect(sentCmd(t, HEARTBEAT)).toHaveLength(1)
    expect(hex(sentCmd(t, HEARTBEAT)[0]!)).toBe(F.COMMAND_HEARTBEAT)
    await vi.advanceTimersByTimeAsync(3000)
    expect(sentCmd(t, HEARTBEAT)).toHaveLength(4)
    await c.close()
    await vi.advanceTimersByTimeAsync(3000)
    expect(sentCmd(t, HEARTBEAT)).toHaveLength(4)
  })

  it('heartbeat q falha não derruba nada', async () => {
    const s = new Scripted(() => [])
    s.send = () => Promise.reject(new Error('desconectado'))
    const c2 = new ConfigSession(s)
    await vi.advanceTimersByTimeAsync(1000)
    await c2.close()
  })

  it('firmware, perfil ativo (0 conta como 1) e troca', async () => {
    expect(await c.firmware()).toEqual(['3.5.6', ''])
    expect(await c.currentProfile()).toBe(1)
    t.current = 0
    expect(await c.currentProfile()).toBe(1)
    await c.switchProfile(3)
    expect([t.current, await c.currentProfile()]).toEqual([3, 3])
  })

  it('estado 0x12 chega no callback com a bateria', async () => {
    const seen: number[] = []
    const c2 = new ConfigSession(t, (s) => seen.push(s.battery))
    await c2.currentProfile()
    expect(seen).toContain(80)
    await c2.close()
  })

  it('watchInput avisa o input atual e depois só quando o controle mexe', async () => {
    const seen: InputState[] = []
    const off = c.watchInput((i) => seen.push(i))
    expect(seen).toEqual([IDLE])
    c.press('B', true)
    await Promise.resolve()
    expect([...seen[1]!.pressed]).toEqual(['B'])
    // heartbeat solta o mesmo estado a cada 1 s: não avisa de novo
    await vi.advanceTimersByTimeAsync(3000)
    expect(seen).toHaveLength(2)
    const late: InputState[] = []
    c.watchInput((i) => late.push(i))
    expect([...late[0]!.pressed]).toEqual(['B'])
    off()
    c.press('B', false)
    await Promise.resolve()
    expect([seen.length, late[1]!.pressed.size]).toEqual([2, 0])
  })

  it('press num controle de verdade não manda nada', async () => {
    const s = new Scripted(() => [])
    const c2 = new ConfigSession(s)
    c2.press('A', true)
    expect(s.sent.map((r) => r[1])).toEqual([HEARTBEAT])
    await c2.close()
  })

  it('reenvia quando o controle fica calado', async () => {
    t.drop = 2
    expect(await settle(c.currentProfile())).toBe(1)
    expect(sentCmd(t, CURRENT)).toHaveLength(3)
  })

  it('reenvia quando o controle responde ocupado', async () => {
    t.busy = 3
    await settle(c.switchProfile(2))
    expect(sentCmd(t, SWITCH)).toHaveLength(4)
    expect(t.current).toBe(2)
  })

  it(`desiste depois de ${TRIES} envios`, async () => {
    t.drop = 1000
    const p = c.currentProfile()
    const check = expect(p).rejects.toThrow(new NoAnswer('no answer to command 11 (controller busy or disconnected)'))
    await vi.advanceTimersByTimeAsync(RESEND * (TRIES + 1))
    await check
    expect(sentCmd(t, CURRENT)).toHaveLength(TRIES)
  })

  it('pula resposta de outro comando e usa o filtro de match', async () => {
    const s = new Scripted(() => [answer(ACK, 0), answer(CURRENT_ACK, 9), answer(CURRENT_ACK, 1)])
    const c2 = new ConfigSession(s)
    const r = await c2.request(Uint8Array.of(0x0f, CURRENT), CURRENT_ACK, (r) => r[2] === 1)
    expect(r[2]).toBe(1)
    expect(s.sent.filter((r) => r[1] === CURRENT)).toHaveLength(1)
    await c2.close()
  })

  it('leitura ignora READ_ACK de outro offset ou perfil', async () => {
    const real = new DemoTransport()
    const s = new Scripted((r) => {
      if (r[1] !== READ) return []
      const good = real.records[r[2]!]!.slice((r[3]! << 8) | r[4]!, ((r[3]! << 8) | r[4]!) + r[5]!)
      return [answer(READ_ACK, r[2]!, 0, 99, r[5]!, ...good.map(() => 0xee)), answer(READ_ACK, 4, r[3]!, r[4]!, r[5]!), answer(READ_ACK, r[2]!, r[3]!, r[4]!, r[5]!, ...good)]
    })
    const c2 = new ConfigSession(s)
    expect(await c2.readProfile(1)).toEqual(records()[1])
    await c2.close()
  })

  it.each([1, 5, LIGHTS])('lê o registro %i inteiro', async (n) => {
    expect(await c.readProfile(n)).toEqual(records()[n])
  })

  it('pedidos simultâneos não se misturam', async () => {
    const [fw, cur, data] = await Promise.all([c.firmware(), c.currentProfile(), c.readProfile(2)])
    expect([fw, cur, data]).toEqual([['3.5.6', ''], 1, records()[2]])
  })

  it('grava o registro inteiro ou só um intervalo', async () => {
    const next = records()[2]!
    next.set([0x61, 0x62], 0)
    next.set(Array.from({ length: 120 }, (_, i) => i), 300)
    await c.writeProfile(2, next)
    expect(t.records[2]).toEqual(next)
    expect(sentCmd(t, WRITE)).toHaveLength(Math.ceil(680 / 58))
    t.log = []
    next[100]! ^= 0xff
    await c.writeProfile(2, next, 100, 101)
    expect(t.records[2]).toEqual(next)
    expect(sentCmd(t, WRITE)).toHaveLength(1)
  })

  it.each([[new Uint8Array(5)], [new Uint8Array(680), 5, 5], [new Uint8Array(680), -1, 3], [new Uint8Array(680), 0, 681]])(
    'recusa intervalo inválido %#', async (data, start?: number, end?: number) => {
      await expect(c.writeProfile(1, data, start, end)).rejects.toThrow('bad range')
    })

  it('save grava só o intervalo q mudou e confere lendo de volta', async () => {
    const old = records()[1]!
    const next = old.slice()
    next[506] = 0
    expect(await c.save(1, old, next)).toBe(1)
    expect(sentCmd(t, WRITE)).toHaveLength(1)
    expect(hex(sentCmd(t, WRITE)[0]!.slice(0, 7))).toBe('0f0301' + '01fa0100')
    expect(t.records[1]).toEqual(next)
  })

  it('save sem mudança não grava nada', async () => {
    expect(await c.save(1, records()[1]!, records()[1]!)).toBe(0)
    expect(sentCmd(t, WRITE)).toHaveLength(0)
  })

  it('save estoura quando o controle não guarda o q foi enviado', async () => {
    t.corrupt = true
    const next = records()[1]!
    next[0] = 0x41
    await expect(c.save(1, records()[1]!, next)).rejects.toThrow('verificação falhou')
  })

  it('teste de vibração liga os motores e desliga depois de 1 s (sync.test_rumble)', async () => {
    const p = c.rumble()
    await vi.advanceTimersByTimeAsync(0)
    expect(sentCmd(t, VIBRATE).map(hex)).toEqual([F.COMMAND_VIBRATE])
    await vi.advanceTimersByTimeAsync(1000)
    await p
    expect(sentCmd(t, VIBRATE)[1]!.slice(0, 6)).toEqual(Uint8Array.of(0x0f, VIBRATE, 102, 85, 0, 0))
  })
})
