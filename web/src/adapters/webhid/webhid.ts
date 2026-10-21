import { OUT, PIDS, USAGE_PAGE, VID } from '../../domain/frames'
import type { ControllerChannel } from '../../application/ports'

// só a interface vendor (usage page 0xFFF0) dos modos q aceitam config
export const FILTERS: HIDDeviceFilter[] = Object.keys(PIDS).map((pid) => ({ vendorId: VID, productId: Number(pid), usagePage: USAGE_PAGE }))

export const hidSupported = (nav: Navigator = navigator): boolean => 'hid' in nav

export class WebHidTransport implements ControllerChannel {
  readonly demo = false
  readonly name: string
  readonly pid: number

  private constructor(private dev: HIDDevice) {
    this.name = dev.productName
    this.pid = dev.productId
  }

  /** Abre o seletor do navegador; null se o usuário cancelar. */
  static async connect(hid: HID = navigator.hid): Promise<WebHidTransport | null> {
    const [dev] = await hid.requestDevice({ filters: FILTERS })
    if (!dev) return null
    if (!dev.opened) await dev.open()
    return new WebHidTransport(dev)
  }

  async send(report: Uint8Array): Promise<void> {
    if (report[0] !== OUT) throw new Error('o canal de config só aceita o report 0x0F')
    // no hidraw o id vai no byte 0; no WebHID ele é argumento e os dados são os outros 63 bytes
    await this.dev.sendReport(OUT, report.slice(1))
  }

  listen(cb: (report: Uint8Array) => void): () => void {
    const h = (e: HIDInputReportEvent) => {
      const r = new Uint8Array(1 + e.data.byteLength)
      r[0] = e.reportId
      r.set(new Uint8Array(e.data.buffer, e.data.byteOffset, e.data.byteLength), 1)
      cb(r)
    }
    this.dev.addEventListener('inputreport', h)
    return () => this.dev.removeEventListener('inputreport', h)
  }

  close(): Promise<void> {
    return this.dev.close()
  }
}
