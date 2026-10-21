import type { Lighting, Profile } from '../../domain/aggregates'
import type { ControllerInfo, ProfileId } from '../../domain/values'
import { planChanges } from '../../application/usecases'

type Records = { profile: Profile; lighting: Lighting }
export type State = {
  info: ControllerInfo | null
  busy: string | null
  status: { text: string; error: boolean }
  battery: number | null
  charging: boolean
  stored: Records | null // como tá no controle
  profile: Profile | null // com as edições ainda não gravadas
  lighting: Lighting | null
  confirming: boolean
}

export type Action =
  | { type: 'busy' | 'error' | 'done'; text: string }
  | ({ type: 'connected'; info: ControllerInfo } & Records)
  | ({ type: 'loaded' } & Records)
  | ({ type: 'saved'; bytes: number } & Records)
  | { type: 'switched'; n: ProfileId }
  | { type: 'battery'; battery: number; charging: boolean }
  | { type: 'edit'; profile: Profile }
  | { type: 'editLights'; lighting: Lighting }
  | { type: 'disconnected' | 'discard' | 'review' | 'cancel' }

const ok = (text: string) => ({ text, error: false })

export const initial: State = {
  info: null, busy: null, status: ok(''), battery: null, charging: false, stored: null, profile: null, lighting: null, confirming: false,
}

const load = (r: Records) => ({ stored: r, profile: r.profile, lighting: r.lighting })

export function reducer(s: State, a: Action): State {
  switch (a.type) {
    case 'busy':
      return { ...s, busy: a.text, status: ok(a.text) }
    case 'error':
      return { ...s, busy: null, confirming: false, status: { text: a.text, error: true } }
    case 'done':
      return { ...s, busy: null, status: ok(a.text) }
    case 'connected':
      return {
        ...initial, info: a.info, ...load(a),
        status: ok(a.info.demo ? 'Modo demo: controle simulado, nada sai do navegador.' : 'Configuração lida do controle.'),
      }
    case 'loaded':
      return { ...s, busy: null, ...load(a), status: ok(`Perfil ${a.profile.id} lido do controle.`) }
    case 'saved':
      return { ...s, busy: null, confirming: false, ...load(a), status: ok(`Gravado e conferido no controle (${a.bytes} bytes).`) }
    case 'switched':
      return { ...s, busy: null, info: { ...s.info!, active: a.n }, status: ok(`Perfil ${a.n} ativo no controle.`) }
    case 'battery':
      return a.battery === s.battery && a.charging === s.charging ? s : { ...s, battery: a.battery, charging: a.charging }
    case 'edit':
      return { ...s, profile: a.profile }
    case 'editLights':
      return { ...s, lighting: a.lighting }
    case 'discard':
      return { ...s, ...load(s.stored!), confirming: false, status: ok('Alterações descartadas.') }
    case 'review':
      return { ...s, confirming: true }
    case 'cancel':
      return { ...s, confirming: false }
    case 'disconnected':
      return { ...initial, status: ok('Desconectado.') }
  }
}

/** O plano do q seria gravado agora (PlanChanges), ou null sem conexão. */
export const pending = (s: State) => (s.profile && s.lighting ? planChanges(s.profile, s.lighting) : null)
