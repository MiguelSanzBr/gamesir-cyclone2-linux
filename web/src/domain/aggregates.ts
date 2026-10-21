// Agregados: o q tá gravado no controle (base) + o q o usuário editou (doc). Toda edição devolve um novo,
// e o ChangeSet é o intervalo de bytes q muda, igual o app (bytesDiff) e o Python (changed_span).
import { LIGHTS } from './frames'
import { applyPreset, decode as decodeLights, encode as encodeLights, type Led, type LightsDoc } from './lighting'
import { changedSpan, decode, encode, setDeadzone, type ProfileDoc } from './profile'
import { animationIndex, brightness, color, frameCount, speed, type HairTrigger, type ProfileId, type TriggerRange } from './values'

export type Profile = { readonly id: ProfileId; readonly base: Uint8Array; readonly doc: ProfileDoc }
export type Lighting = { readonly base: Uint8Array; readonly doc: LightsDoc }
/** Bytes [start, end) do registro `record` q mudam; `next` é o registro inteiro depois da gravação. */
export type ChangeSet = { record: number; start: number; end: number; old: Uint8Array; next: Uint8Array }
export type Trigger = 'LT' | 'RT'

export const loadProfile = (id: ProfileId, base: Uint8Array): Profile => ({ id, base, doc: decode(base) })
export const loadLighting = (base: Uint8Array): Lighting => ({ base, doc: decodeLights(base) })

function editDoc(p: Profile, change: (d: ProfileDoc) => void): Profile {
  const doc = structuredClone(p.doc)
  change(doc)
  return { ...p, doc }
}

export const rename = (p: Profile, name: string) => editDoc(p, (d) => (d.name = name))

/** Muda início/fim da zona morta mantendo o anti dead zone, e refaz a curva como o app. */
export const setTriggerRange = (p: Profile, t: Trigger, r: TriggerRange) =>
  editDoc(p, (d) => setDeadzone(d.triggers[t], [r.start, r.end, ...d.triggers[t].deadzone.slice(2)]))

export const setHairTrigger = (p: Profile, t: Trigger, h: HairTrigger) => editDoc(p, (d) => (d.triggers[t].hair_trigger = { ...h }))

function changeSet(record: number, old: Uint8Array, next: Uint8Array): ChangeSet | null {
  const span = changedSpan(old, next)
  return span && { record, start: span[0], end: span[1], old, next }
}

export const profileChangeSet = (p: Profile) => changeSet(p.id, p.base, encode(p.doc, p.base))
export const lightingChangeSet = (l: Lighting) => changeSet(LIGHTS, l.base, encodeLights(l.doc, l.base))

function editLights(l: Lighting, change: (d: LightsDoc) => void): Lighting {
  const doc = structuredClone(l.doc)
  change(doc)
  return { ...l, doc }
}

export const setActiveAnimation = (l: Lighting, i: number) => editLights(l, (d) => (d.active = animationIndex(i)))

export const applyLightPreset = (l: Lighting, name: string, i: number): Lighting => ({ ...l, doc: applyPreset(l.doc, name, animationIndex(i)) })

export function editAnimation(l: Lighting, i: number, patch: { brightness?: number; speed?: number; frames?: number }): Lighting {
  return editLights(l, (d) => {
    const an = d.animations[animationIndex(i)]!
    if (patch.brightness !== undefined) an.brightness = brightness(patch.brightness)
    if (patch.speed !== undefined) an.speed = speed(patch.speed)
    if (patch.frames !== undefined) an.frames = frameCount(patch.frames)
  })
}

export const setFrameColor = (l: Lighting, i: number, frame: number, led: Led, c: string) =>
  editLights(l, (d) => (d.animations[animationIndex(i)]!.colors[frameCount(frame + 1) - 1]![led] = color(c)))
