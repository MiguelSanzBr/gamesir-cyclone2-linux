// Casos de uso: o q a UI pode fazer com o controle. Só dependem da porta ControllerChannel e do domain.
import {
  lightingChangeSet, loadLighting, loadProfile, profileChangeSet, type ChangeSet, type Lighting, type Profile,
} from '../domain/aggregates'
import { lightChanges, profileChanges, type Change } from '../domain/changes'
import { LIGHTS, type InputState } from '../domain/frames'
import { PRESETS } from '../domain/lighting'
import { controllerInfo, profileId, type ControllerInfo, type ProfileId } from '../domain/values'
import type { ControllerChannel } from './ports'
import { ConfigSession } from './session'

// edições staged: só mexem no doc do agregado, nada vai pro controle aqui
export {
  applyLightPreset, editAnimation, rename, setActiveAnimation, setFrameColor, setHairTrigger, setTriggerRange,
} from '../domain/aggregates'
export { LEDS } from '../domain/lighting'
export { hairTrigger, profileId, triggerRange } from '../domain/values'
export const PRESET_NAMES = Object.keys(PRESETS)

export type Connected = { session: ConfigSession; info: ControllerInfo; profile: Profile; lighting: Lighting }
export type Plan = { profile: Profile; lighting: Lighting; changeSets: ChangeSet[]; changes: Change[]; bytes: number }

/** Abre a sessão no canal escolhido e lê info, perfil ativo e luzes; null se o usuário cancelou. */
export async function connect(channel: ControllerChannel | null, onBattery: (battery: number, charging: boolean) => void): Promise<Connected | null> {
  if (!channel) return null
  const session = new ConfigSession(channel, (s) => onBattery(s.battery, s.charging > 0))
  try {
    const [firmware, dongle] = await session.firmware()
    const active = profileId(await session.currentProfile())
    const { profile, lighting } = await readProfile(session, active)
    const info = controllerInfo({ name: channel.name, pid: channel.pid, demo: channel.demo, firmware, dongle, active })
    return { session, info, profile, lighting }
  } catch (e) {
    await session.close()
    throw e
  }
}

export async function readProfile(session: ConfigSession, id: ProfileId): Promise<{ profile: Profile; lighting: Lighting }> {
  const profile = loadProfile(id, await session.readProfile(id))
  return { profile, lighting: loadLighting(await session.readProfile(LIGHTS)) }
}

export function planChanges(profile: Profile, lighting: Lighting): Plan {
  const changeSets = [profileChangeSet(profile), lightingChangeSet(lighting)].filter((c) => c !== null)
  return {
    profile,
    lighting,
    changeSets,
    changes: [...profileChanges(loadProfile(profile.id, profile.base).doc, profile.doc), ...lightChanges(loadLighting(lighting.base).doc, lighting.doc)],
    bytes: changeSets.reduce((n, c) => n + c.end - c.start, 0),
  }
}

/** Grava só os intervalos do plano, depois de confirmado, e confere lendo de volta (ConfigSession.save). */
export async function applyChanges(session: ConfigSession, plan: Plan, confirmed: boolean): Promise<{ profile: Profile; lighting: Lighting; bytes: number }> {
  if (!confirmed) throw new Error('gravar exige confirmação explícita')
  for (const c of plan.changeSets) await session.save(c.record, c.old, c.next)
  // save() já conferiu byte a byte, então o registro gravado vira a nova base
  const stored = (record: number, base: Uint8Array) => plan.changeSets.find((c) => c.record === record)?.next ?? base
  return {
    profile: loadProfile(plan.profile.id, stored(plan.profile.id, plan.profile.base)),
    lighting: loadLighting(stored(LIGHTS, plan.lighting.base)),
    bytes: plan.bytes,
  }
}

export async function switchActiveProfile(session: ConfigSession, id: ProfileId): Promise<ProfileId> {
  await session.switchProfile(id)
  return profileId(await session.currentProfile())
}

export const rumbleTest = (session: ConfigSession) => session.rumble()
export const watchInput = (session: ConfigSession, cb: (i: InputState) => void) => session.watchInput(cb)
export const simulatePress = (session: ConfigSession, name: string, down: boolean) => session.press(name, down)
export const disconnect = (session: ConfigSession) => session.close()
