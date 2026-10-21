// Port do src/cyclone2/device.py (Device) e do _store do cli.py, em cima de qualquer ControllerChannel.
import {
  ACK, CURRENT, CURRENT_ACK, FIRMWARE, FIRMWARE_ACK, READ_ACK, STATE, SWITCH, VIBRATE, busy, chunk, command,
  firmware, IDLE, kind, readRequests, sameInput, sizeOf, state, writeRequests, type InputState, type PadState,
} from '../domain/frames'
import { changedSpan } from '../domain/profile'
import { keepAlive } from './keepAlive'
import type { ControllerChannel } from './ports'

export const TRIES = 10 // o app desiste depois de 10 envios
export const RESEND = 200 // ... reenviando a cada 200 ms sem resposta

export class NoAnswer extends Error {}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))

export class ConfigSession {
  private queue: Promise<unknown> = Promise.resolve()
  private stopKeepAlive: () => void
  private off: () => void
  private input: InputState = IDLE
  private inputs = new Set<(i: InputState) => void>()

  constructor(private t: ControllerChannel, onState?: (s: PadState) => void) {
    this.off = t.listen((r) => {
      if (r[0] !== STATE) return
      const s = state(r)!
      onState?.(s)
      if (sameInput(s, this.input)) return
      this.input = s
      this.inputs.forEach((cb) => cb(s))
    })
    this.stopKeepAlive = keepAlive(t)
  }

  async close(): Promise<void> {
    this.stopKeepAlive()
    this.off()
    await this.t.close()
  }

  /** Manda até chegar resposta do tipo `want` q passe no `match`; ocupado ou silêncio = reenvia. */
  request(report: Uint8Array, want: number, match: (r: Uint8Array) => boolean = () => true): Promise<Uint8Array> {
    // um pedido por vez: a resposta não diz de qual pedido ela é
    const run = this.queue.then(() => this.attempt(report, want, match))
    this.queue = run.catch(() => {})
    return run
  }

  private async attempt(report: Uint8Array, want: number, match: (r: Uint8Array) => boolean): Promise<Uint8Array> {
    for (let i = 0; i < TRIES; i++) {
      const answer = this.wait(want, match) // escuta antes de mandar pra não perder resposta rápida
      await this.t.send(report)
      const r = await answer
      if (r) return r
    }
    throw new NoAnswer(`no answer to command ${report[1]} (controller busy or disconnected)`)
  }

  private wait(want: number, match: (r: Uint8Array) => boolean): Promise<Uint8Array | null> {
    return new Promise((resolve) => {
      const done = (r: Uint8Array | null) => {
        clearTimeout(timer)
        off()
        resolve(r)
      }
      const timer = setTimeout(() => done(null), RESEND)
      const off = this.t.listen((r) => {
        if (busy(r)) done(null) // checa antes: ocupado também é um ACK
        else if (kind(r) === want && match(r)) done(r)
      })
    })
  }

  async firmware(): Promise<[string, string]> {
    return firmware(await this.request(command(FIRMWARE), FIRMWARE_ACK))
  }

  /** Perfil ativo 1-4 (o app trata 0 como 1). */
  async currentProfile(): Promise<number> {
    return (await this.request(command(CURRENT), CURRENT_ACK))[2]! || 1
  }

  async switchProfile(n: number): Promise<void> {
    await this.request(command(SWITCH, n), ACK)
  }

  async readProfile(n: number): Promise<Uint8Array> {
    const buf = new Uint8Array(sizeOf(n))
    for (const req of readRequests(n)) {
      const off = (req[3]! << 8) | req[4]!
      const r = await this.request(req, READ_ACK, (r) => chunk(r).profile === n && chunk(r).offset === off)
      buf.set(chunk(r).data, off)
    }
    return buf
  }

  /** Grava data[start:end] de um registro; o firmware guarda na hora, não tem commit. */
  async writeProfile(n: number, data: Uint8Array, start = 0, end = data.length): Promise<void> {
    if (data.length !== sizeOf(n) || start < 0 || start >= end || end > data.length) {
      throw new Error(`bad range ${start}-${end} for a ${data.length}-byte record ${n}`)
    }
    for (const req of writeRequests(n, data.slice(start, end), start)) await this.request(req, ACK)
  }

  /** Grava só o intervalo q mudou e lê o registro de volta pra conferir; devolve quantos bytes foram. */
  async save(n: number, old: Uint8Array, next: Uint8Array): Promise<number> {
    const span = changedSpan(old, next)
    if (!span) return 0
    await this.writeProfile(n, next, ...span)
    const back = await this.readProfile(n)
    if (changedSpan(back, next)) throw new Error('verificação falhou: o controle não guardou o que foi enviado')
    return span[1] - span[0]
  }

  /** Avisa o input físico já com o atual e depois a cada mudança; devolve a função q para de avisar. */
  watchInput(cb: (i: InputState) => void): () => void {
    this.inputs.add(cb)
    cb(this.input)
    return () => this.inputs.delete(cb)
  }

  /** No demo aperta o botão simulado; no controle de verdade não tem o q apertar. */
  press(name: string, down: boolean): void {
    this.t.press?.(name, down)
  }

  vibrate(left: number, right: number): Promise<void> {
    return this.t.send(command(VIBRATE, 102, 85, left, right))
  }

  /** Teste de vibração do app: liga os dois motores e desliga depois de 1 s. */
  async rumble(): Promise<void> {
    await this.vibrate(160, 160)
    await sleep(1000)
    await this.vibrate(0, 0)
  }
}
