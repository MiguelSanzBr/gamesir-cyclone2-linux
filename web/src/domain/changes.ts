// O q vai mudar, em texto, pra tela de confirmação. Os bytes exatos também aparecem lá (intervalo do ChangeSet).
import { ANIMATIONS, FRAMES, LEDS, type LightsDoc } from './lighting'
import type { HairTrigger, ProfileDoc } from './profile'

export type Change = { label: string; from: string; to: string }
type Item<T> = [label: string, show: (d: T) => string]

const hair = (h: HairTrigger) => (h.on ? `${h.mode === 2 ? 'fixo' : 'adaptativo'}, ${h.start}% a ${h.end}%` : 'desligado')

const PROFILE: Item<ProfileDoc>[] = [
  ['Nome do perfil', (d) => d.name || '(sem nome)'],
  ...(['LT', 'RT'] as const).flatMap((t): Item<ProfileDoc>[] => [
    [`${t}: zona morta ligada`, (d) => (d.triggers[t].deadzone_on ? 'sim' : 'não')],
    [`${t}: zona morta`, (d) => `${d.triggers[t].deadzone[0]}% a ${d.triggers[t].deadzone[1]}%`],
    [`${t}: pontos da curva (refeitos pela zona morta)`, (d) => d.triggers[t].curve.points.map((p) => p.join(',')).join(' ')],
    [`${t}: hair trigger`, (d) => hair(d.triggers[t].hair_trigger)],
  ]),
]

const LIGHTS: Item<LightsDoc>[] = [
  ['Animação ativa', (d) => String(d.active + 1)],
  ...Array.from({ length: ANIMATIONS }, (_, a): Item<LightsDoc>[] => [
    [`Animação ${a + 1}: brilho`, (d) => `${d.animations[a]!.brightness}%`],
    [`Animação ${a + 1}: velocidade`, (d) => String(d.animations[a]!.speed)],
    [`Animação ${a + 1}: quadros`, (d) => String(d.animations[a]!.frames)],
    ...Array.from({ length: FRAMES }, (_, f): Item<LightsDoc> =>
      [`Animação ${a + 1}, quadro ${f + 1}`, (d) => LEDS.map((l) => d.animations[a]!.colors[f]![l]).join(' ')]),
  ]).flat(),
]

const diff = <T,>(items: Item<T>[], a: T, b: T): Change[] =>
  items.map(([label, show]) => ({ label, from: show(a), to: show(b) })).filter((c) => c.from !== c.to)

export const profileChanges = (a: ProfileDoc, b: ProfileDoc) => diff(PROFILE, a, b)
export const lightChanges = (a: LightsDoc, b: LightsDoc) => diff(LIGHTS, a, b)
