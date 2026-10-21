// Objetos de valor: cada um garante a faixa q o firmware/app aceita antes de virar byte.
import { InvariantError } from './errors'
import { PIDS } from './frames'

export { InvariantError }

export type ProfileId = 1 | 2 | 3 | 4
export type TriggerRange = { start: number; end: number }
export type HairTrigger = { on: boolean; mode: number; start: number; end: number }
export type ControllerInfo = { name: string; pid: number; mode: string; demo: boolean; firmware: string; dongle: string; active: ProfileId }

function int(v: number, lo: number, hi: number, what: string): number {
  if (!Number.isInteger(v) || v < lo || v > hi) throw new InvariantError(`${what} fora da faixa ${lo}-${hi}: ${v}`)
  return v
}

export const profileId = (n: number) => int(n, 1, 4, 'perfil') as ProfileId

/** Zona morta do gatilho em %: início <= fim (o curve() do Python aguenta início == fim). */
export function triggerRange(start: number, end: number): TriggerRange {
  int(start, 0, 100, 'início')
  if (start > end) throw new InvariantError(`início ${start} depois do fim ${end}`)
  return { start, end: int(end, 0, 100, 'fim') }
}

/** Modo 1 = adaptativo, 2 = fixo (bits 0/1 do status). */
export function hairTrigger(on: boolean, mode: number, start: number, end: number): HairTrigger {
  if (mode !== 1 && mode !== 2) throw new InvariantError(`modo de hair trigger ${mode}`)
  return { on, mode, start: int(start, 0, 100, 'início'), end: int(end, 0, 100, 'fim') }
}

// o firmware tem 5 animações mas o app só deixa ativar 0-3 (light.decode zera o resto)
export const animationIndex = (n: number) => int(n, 0, 3, 'animação')
export const brightness = (n: number) => int(n, 0, 100, 'brilho')
export const speed = (n: number) => int(n, 0, 20, 'velocidade')
export const frameCount = (n: number) => int(n, 1, 8, 'quadros')

export function color(c: string): string {
  if (!/^#[0-9a-f]{6}$/i.test(c)) throw new InvariantError(`cor ${c}`)
  return c.toLowerCase()
}

export function controllerInfo(i: Omit<ControllerInfo, 'mode'>): ControllerInfo {
  return { ...i, mode: PIDS[i.pid] ?? `modo 0x${i.pid.toString(16)}` }
}
