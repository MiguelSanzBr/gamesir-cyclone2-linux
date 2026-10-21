import type { ComponentProps } from 'react'
import type { ControllerInfo } from '../../domain/values'
import { Controller } from './Controller'
import type { Section } from './sections'

type Live = Pick<ComponentProps<typeof Controller>, 'watch' | 'onPress'>
type Props = { info: ControllerInfo; battery: number | null; charging: boolean; grips: readonly [string, string]; onCallout: (s: Section) => void } & Live

export function Info({ info, battery, charging, grips, onCallout, watch, onPress }: Props) {
  return (
    <section className="hero" aria-label="Controle">
      <h1 translate="no">Cyclone 2</h1>
      <p className="sub">Perfil ativo no controle: {info.active}</p>
      <Controller grips={grips} active={info.active} onCallout={onCallout} watch={watch} onPress={onPress} />
      <p className="hint live-hint">Aperte os botões do controle: eles acendem aqui.{info.demo && ' No demo, clique nas partes do desenho.'}</p>
      <div className="device">
        <span className="pill"><span className="dot ok" aria-hidden="true" /><span>{info.mode}</span></span>
        <span className="pill">
          <span className="battery" aria-hidden="true"><span style={{ transform: `scaleX(${(battery ?? 0) / 100})` }} /></span>
          <span>{battery === null ? 'lendo…' : `${battery}%${charging ? ' (carregando)' : ''}`}</span>
        </span>
        {info.dongle && <span className="pill">dongle {info.dongle}</span>}
      </div>
    </section>
  )
}
