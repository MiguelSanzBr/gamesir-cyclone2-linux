// Controle simulado em memória, port do tests/fake_device.py: responde no canal de config igual ao firmware.
import {
  ACK, ANSWER, CURRENT, CURRENT_ACK, FIRMWARE, FIRMWARE_ACK, HAT, HEARTBEAT, OUT, RAW, READ, READ_ACK, REPORT_SIZE, STATE, STATE_BITS,
  SWITCH, WRITE,
} from '../../domain/frames'
import { records } from './backup'
import type { ControllerChannel } from '../../application/ports'

const enc = new TextEncoder()

export class DemoTransport implements ControllerChannel {
  readonly demo = true
  readonly name = 'Cyclone 2 (demo)'
  readonly pid = 0x1053
  records = records()
  current = 1
  battery = 80
  charging = false
  dongle = ''
  // botões pra simular falha, como no fake do Python
  drop = 0
  busy = 0
  corrupt = false
  log: Uint8Array[] = []
  pressed = new Set<string>()
  private listeners = new Set<(r: Uint8Array) => void>()
  private closed = false

  listen(cb: (r: Uint8Array) => void): () => void {
    this.listeners.add(cb)
    return () => this.listeners.delete(cb)
  }

  async close(): Promise<void> {
    this.closed = true
  }

  async send(r: Uint8Array): Promise<void> {
    this.log.push(r)
    const cmd = r[1]!
    if (this.closed || r[0] !== OUT) return
    // o firmware não responde heartbeat, vibração nem prévia de LED; o estado chega pelo stream 0x12
    if (cmd === HEARTBEAT) return this.emit(this.stateReport())
    if (![FIRMWARE, CURRENT, SWITCH, READ, WRITE].includes(cmd)) return
    if (this.drop) {
      this.drop--
      return
    }
    if (this.busy) {
      this.busy--
      return this.answer(ACK, 1)
    }
    const n = r[2]!
    const off = (r[3]! << 8) | r[4]!
    const size = r[5]!
    if (cmd === FIRMWARE) return this.answer(FIRMWARE_ACK, 0x30, 0, ...enc.encode('3\x005\x006'), 0, 0, 0, ...enc.encode(this.dongle))
    if (cmd === CURRENT) return this.answer(CURRENT_ACK, this.current)
    if (cmd === SWITCH) {
      this.current = n
      return this.answer(ACK, 0)
    }
    if (cmd === READ) return this.answer(READ_ACK, n, r[3]!, r[4]!, size, ...this.records[n]!.slice(off, off + size))
    const data = r.slice(6, 6 + size)
    if (this.corrupt) data[0]! ^= 0xff
    this.records[n]!.set(data, off)
    this.answer(ACK, 0)
  }

  press(name: string, down: boolean): void {
    if (down) this.pressed.add(name)
    else this.pressed.delete(name)
    this.emit(this.stateReport())
  }

  // port do FakeController.state_report; gatilho apertado no demo vai até o fundo
  private stateReport(): Uint8Array {
    const r = new Uint8Array(REPORT_SIZE)
    r[0] = STATE
    r[35] = Number(this.charging)
    r[36] = this.battery
    r.fill(128, RAW + 1, RAW + 5)
    const dirs = ['Up', 'Right', 'Down', 'Left'].filter((d) => this.pressed.has(d))
    const hat = HAT.findIndex((h) => h.length === dirs.length && h.every((d) => dirs.includes(d)))
    r[RAW + 5] = hat < 0 ? 0x0f : hat
    for (const [byte, bits] of Object.entries(STATE_BITS)) {
      for (const [bit, name] of Object.entries(bits)) if (this.pressed.has(name)) r[RAW + +byte]! |= 1 << +bit
    }
    r[RAW + 8] = this.pressed.has('LT') ? 255 : 0
    r[RAW + 9] = this.pressed.has('RT') ? 255 : 0
    return r
  }

  private answer(...data: number[]) {
    const r = new Uint8Array(REPORT_SIZE)
    r.set([ANSWER, ...data])
    this.emit(this.stateReport(), r)
  }

  private emit(...reports: Uint8Array[]) {
    queueMicrotask(() => reports.forEach((r) => this.listeners.forEach((cb) => cb(r))))
  }
}
