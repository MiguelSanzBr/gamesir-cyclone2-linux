import { FILTERS, WebHidTransport, hidSupported } from './webhid'
import { OUT, SWITCH, command } from '../../domain/frames'
import * as F from '../../test/fixtures'
import { hex, unhex } from '../../test/hex'

// navigator.hid falso: o hardware de verdade não roda no CI
class FakeDevice extends EventTarget {
  opened = false
  productName = 'GameSir-Cyclone 2'
  productId = 0x1053
  sendReport = vi.fn(async () => {})
  open = vi.fn(async () => void (this.opened = true))
  close = vi.fn(async () => void (this.opened = false))
  input(reportId: number, bytes: number[]) {
    const e = Object.assign(new Event('inputreport'), { reportId, data: new DataView(Uint8Array.from([0xaa, ...bytes]).buffer, 1) })
    this.dispatchEvent(e)
  }
}

const fakeHid = (devices: FakeDevice[]) => ({ requestDevice: vi.fn(async () => devices) }) as unknown as HID & { requestDevice: ReturnType<typeof vi.fn> }

describe('WebHidTransport', () => {
  it('hidSupported olha se o navegador tem navigator.hid', () => {
    expect(hidSupported({ hid: {} } as Navigator)).toBe(true)
    expect(hidSupported({} as Navigator)).toBe(false)
  })

  it('filtra VID 0x3537, os 4 PIDs configuráveis e a usage page 0xFFF0', () => {
    expect(FILTERS).toEqual([0x101d, 0x102a, 0x1053, 0x100b].map((productId) => ({ vendorId: 0x3537, productId, usagePage: 0xfff0 })).sort((a, b) => a.productId - b.productId))
  })

  it('connect abre o aparelho escolhido', async () => {
    const dev = new FakeDevice()
    const hid = fakeHid([dev])
    const t = (await WebHidTransport.connect(hid))!
    expect(hid.requestDevice).toHaveBeenCalledWith({ filters: FILTERS })
    expect(dev.open).toHaveBeenCalledTimes(1)
    expect([t.demo, t.name, t.pid]).toEqual([false, 'GameSir-Cyclone 2', 0x1053])
  })

  it('connect não reabre aparelho já aberto e devolve null se o usuário cancelar', async () => {
    const dev = new FakeDevice()
    dev.opened = true
    await WebHidTransport.connect(fakeHid([dev]))
    expect(dev.open).not.toHaveBeenCalled()
    expect(await WebHidTransport.connect(fakeHid([]))).toBeNull()
  })

  it('send usa sendReport(0x0F, 63 bytes) e recusa outro report id', async () => {
    const dev = new FakeDevice()
    const t = (await WebHidTransport.connect(fakeHid([dev])))!
    await t.send(command(SWITCH, 3))
    expect(dev.sendReport).toHaveBeenCalledTimes(1)
    const [id, data] = dev.sendReport.mock.calls[0] as unknown as [number, Uint8Array]
    expect(id).toBe(OUT)
    expect(hex(Uint8Array.of(id, ...data))).toBe(F.COMMAND_SWITCH_3)
    await expect(t.send(Uint8Array.of(0x10, 1))).rejects.toThrow('0x0F')
    expect(dev.sendReport).toHaveBeenCalledTimes(1)
  })

  it('listen entrega o report com o id no byte 0 e para de entregar depois do off', async () => {
    const dev = new FakeDevice()
    const t = (await WebHidTransport.connect(fakeHid([dev])))!
    const got: string[] = []
    const off = t.listen((r) => got.push(hex(r)))
    const fw = unhex(F.FIRMWARE_REPORT)
    dev.input(fw[0]!, [...fw.slice(1)])
    off()
    dev.input(0x12, [1])
    expect(got).toEqual([F.FIRMWARE_REPORT])
  })

  it('close fecha o aparelho', async () => {
    const dev = new FakeDevice()
    const t = (await WebHidTransport.connect(fakeHid([dev])))!
    await t.close()
    expect(dev.close).toHaveBeenCalled()
  })
})
