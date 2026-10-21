import { HEARTBEAT, command } from '../domain/frames'
import type { ControllerChannel } from './ports'

export const HEARTBEAT_MS = 1000

/** Política do app oficial: heartbeat na hora e a cada 1 s enquanto conectado, mantém a sessão de config viva. */
export function keepAlive(ch: ControllerChannel): () => void {
  // se falhar o controle sumiu; o próximo pedido estoura com a mensagem certa
  const beat = () => void ch.send(command(HEARTBEAT, 0)).catch(() => {})
  beat()
  const timer = setInterval(beat, HEARTBEAT_MS)
  return () => clearInterval(timer)
}
