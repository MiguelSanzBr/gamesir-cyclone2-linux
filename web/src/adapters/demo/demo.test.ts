import { DemoTransport } from './demo'
import { records } from './backup'
import { ACK, ANSWER, CURRENT_ACK, CURRENT, FIRMWARE, HEARTBEAT, READ, STATE, SWITCH, VIBRATE, WRITE, command, state } from '../../domain/frames'
import * as F from '../../test/fixtures'
import { hex } from '../../test/hex'

// espelha o tests/fake_device.py: responde como o firmware, com um report 0x12 antes de cada resposta
async function exchange(t: DemoTransport, report: Uint8Array) {
  const got: Uint8Array[] = []
  const off = t.listen((r) => got.push(r))
  await t.send(report)
  await Promise.resolve()
  off()
  return got
}

describe('DemoTransport', () => {
  it('se identifica como demo, no modo cabo ADC', () => {
    const t = new DemoTransport()
    expect([t.demo, t.pid, t.name]).toEqual([true, 0x1053, 'Cyclone 2 (demo)'])
  })

  it('firmware 3.5.6, com report de estado antes da resposta', async () => {
    const [st, ans] = await exchange(new DemoTransport(), command(FIRMWARE))
    expect(st![0]).toBe(STATE)
    expect(st![36]).toBe(80)
    expect(hex(ans!.slice(0, 9))).toBe('100a3000330035003' + '6')
  })

  it('perfil ativo e troca de perfil', async () => {
    const t = new DemoTransport()
    expect((await exchange(t, command(CURRENT)))[1]!.slice(0, 3)).toEqual(Uint8Array.of(ANSWER, CURRENT_ACK, 1))
    expect((await exchange(t, command(SWITCH, 3)))[1]!.slice(0, 3)).toEqual(Uint8Array.of(ANSWER, ACK, 0))
    expect(t.current).toBe(3)
  })

  it('lê e grava pedaços dos registros', async () => {
    const t = new DemoTransport()
    const [, r] = await exchange(t, command(READ, 1, 0, 10, 4))
    expect(r!.slice(0, 10)).toEqual(Uint8Array.of(ANSWER, 5, 1, 0, 10, 4, ...records()[1]!.slice(10, 14)))
    const [, a] = await exchange(t, command(WRITE, 32, 0, 1, 2, 7, 8))
    expect(a![1]).toBe(ACK)
    expect(t.records[32]!.slice(0, 4)).toEqual(Uint8Array.of(records()[32]![0]!, 7, 8, records()[32]![3]!))
  })

  it('corrupt grava outra coisa, busy responde ocupado, drop ignora', async () => {
    const t = new DemoTransport()
    t.corrupt = true
    await exchange(t, command(WRITE, 2, 0, 0, 1, 0x41))
    expect(t.records[2]![0]).toBe(0x41 ^ 0xff)
    t.busy = 1
    expect((await exchange(t, command(CURRENT)))[1]!.slice(1, 3)).toEqual(Uint8Array.of(ACK, 1))
    t.drop = 1
    expect(await exchange(t, command(CURRENT))).toEqual([])
    expect((await exchange(t, command(CURRENT))).length).toBe(2)
  })

  it('heartbeat só solta estado; vibração e report q não é 0x0F não têm resposta', async () => {
    const t = new DemoTransport()
    const hb = await exchange(t, command(HEARTBEAT, 0))
    expect(hb.map((r) => r[0])).toEqual([STATE])
    expect(await exchange(t, command(VIBRATE, 102, 85, 1, 1))).toEqual([])
    expect(await exchange(t, Uint8Array.of(0x10, CURRENT))).toEqual([])
    expect(t.log.map((r) => r[1])).toEqual([HEARTBEAT, VIBRATE, CURRENT])
  })

  it('close para de responder', async () => {
    const t = new DemoTransport()
    await t.close()
    expect(await exchange(t, command(CURRENT))).toEqual([])
  })

  describe('press simula o input físico', () => {
    const last = async (t: DemoTransport, ...presses: [string, boolean][]) => {
      const got: Uint8Array[] = []
      const off = t.listen((r) => got.push(r))
      for (const [n, down] of presses) t.press(n, down)
      await Promise.resolve()
      off()
      return got.at(-1)!
    }

    // gatilho apertado vai até o fim (255), por isso os bytes 8-9 ficam de fora da comparação com o Python
    it.each(Object.entries(F.STATE_RAW_EACH))('%s: mesmos bits do FakeController.state_report', async (name, raw) => {
      const r = await last(new DemoTransport(), [name, true])
      expect(hex(r.slice(53, 61))).toBe(raw.slice(0, 16))
    })

    it('manda o 0x12 na hora, com d-pad na diagonal, gatilho no fundo e soltar', async () => {
      const t = new DemoTransport()
      const r = await last(t, ['A', true], ['LT', true], ['Up', true], ['Right', true])
      const s = state(r)!
      expect([[...s.pressed].sort(), s.lt, s.rt, s.left, s.right, s.battery]).toEqual([['A', 'LT', 'Right', 'Up'], 255, 0, [0, 0], [0, 0], 80])
      expect([...state(await last(t, ['A', false], ['LT', false], ['Right', false]))!.pressed]).toEqual(['Up'])
      const s2 = state(await last(t, ['Down', true], ['RT', true]))!
      // cima e baixo juntos não existe no hat: fica neutro, igual ao Python
      expect([[...s2.pressed], s2.rt]).toEqual([['RT'], 255])
    })
  })
})
