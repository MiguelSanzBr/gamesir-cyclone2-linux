/** Canal de config do controle: manda report 0x0F e recebe 0x10/0x12 com o id no byte 0. */
export interface ControllerChannel {
  readonly demo: boolean
  readonly name: string
  readonly pid: number
  send(report: Uint8Array): Promise<void>
  listen(cb: (report: Uint8Array) => void): () => void
  close(): Promise<void>
  /** Só o controle simulado: aperta ou solta um botão físico e manda o 0x12 como o firmware. */
  press?(name: string, down: boolean): void
}
