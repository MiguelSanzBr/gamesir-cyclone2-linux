import type { Profile } from '../../domain/aggregates'
import { hairTrigger, setHairTrigger, setTriggerRange, triggerRange } from '../../application/usecases'
import { Range } from './Range'

const NAMES = { LT: 'Gatilho esquerdo', RT: 'Gatilho direito' }

export function Triggers({ profile, onEdit }: { profile: Profile; onEdit: (p: Profile) => void }) {
  return (
    <div className="grid-2">
      {(['LT', 'RT'] as const).map((t) => {
        const tr = profile.doc.triggers[t]
        const h = tr.hair_trigger
        const p = `${t}: `
        const hair = (on: boolean, mode: number, start: number, end: number) => onEdit(setHairTrigger(profile, t, hairTrigger(on, mode, start, end)))
        return (
          <fieldset key={t} className="card trigger">
            <legend className="sr-only">Gatilho {t}</legend>
            <div className="card-head" aria-hidden="true">
              <span className="badge" translate="no">{t}</span>
              <span>{NAMES[t]}</span>
            </div>
            <h3>Zona morta</h3>
            <Range name={`${p}início da zona morta`} label="Início" min={0} max={50} value={tr.deadzone[0]!} unit="%"
              onChange={(v) => onEdit(setTriggerRange(profile, t, triggerRange(v, tr.deadzone[1]!)))} />
            <Range name={`${p}fim da zona morta`} label="Fim" min={50} max={100} value={tr.deadzone[1]!} unit="%"
              onChange={(v) => onEdit(setTriggerRange(profile, t, triggerRange(tr.deadzone[0]!, v)))} />
            <label className="switch-row">
              Hair trigger
              <input type="checkbox" role="switch" className="switch" aria-label={`${p}hair trigger`} checked={h.on} onChange={(e) => hair(e.target.checked, h.mode, h.start, h.end)} />
            </label>
            <div role="radiogroup" aria-label={`${t}: modo do hair trigger`} className="segmented">
              {([[1, 'adaptativo'], [2, 'fixo']] as const).map(([mode, name]) => (
                <label key={mode}>
                  <input type="radio" name={`${t}-mode`} aria-label={`${p}${name}`} checked={h.mode === mode} onChange={() => hair(h.on, mode, h.start, h.end)} />
                  <span className="cap">{name}</span>
                </label>
              ))}
            </div>
            <Range name={`${p}hair trigger início`} label="Início" min={1} max={99} value={h.start} unit="%" onChange={(v) => hair(h.on, h.mode, v, h.end)} />
            <Range name={`${p}hair trigger fim`} label="Fim" min={2} max={100} value={h.end} unit="%" onChange={(v) => hair(h.on, h.mode, h.start, v)} />
          </fieldset>
        )
      })}
    </div>
  )
}
