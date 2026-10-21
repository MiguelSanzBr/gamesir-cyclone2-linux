import { useState } from 'react'
import type { Lighting } from '../../domain/aggregates'
import type { Led } from '../../domain/lighting'
import { LEDS, PRESET_NAMES, applyLightPreset, editAnimation, setActiveAnimation, setFrameColor } from '../../application/usecases'
import { Range } from './Range'

const LED_NAMES: Record<Led, string> = {
  lower_left: 'Grip esquerdo',
  lower_right: 'Grip direito',
  upper_left: 'Anel do analógico esquerdo',
  home: 'Botão Home',
  upper_right: 'Anel do analógico direito',
}

type Props = { lighting: Lighting; onEdit: (l: Lighting) => void }

export function LightingEditor({ lighting, onEdit }: Props) {
  const [picked, setFrame] = useState(0)
  const a = lighting.doc.active
  const an = lighting.doc.animations[a]!
  // menos quadros do q o selecionado: edita o último q sobrou
  const frame = Math.min(picked, an.frames - 1)
  return (
    <div className="stack">
      <p className="hint">As luzes valem pra todos os perfis. No Cyclone 2 preto só os dois grips acendem.</p>
      <div role="radiogroup" aria-label="Animação ativa" className="segmented wide">
        {[0, 1, 2, 3].map((i) => (
          <label key={i}>
            <input type="radio" name="animation" checked={a === i} onChange={() => onEdit(setActiveAnimation(lighting, i))} />
            Animação {i + 1}
          </label>
        ))}
      </div>
      <div role="group" aria-labelledby="presets-title">
        <h3 id="presets-title">Presets</h3>
        <div className="chips">
          {PRESET_NAMES.map((p) => <button key={p} type="button" className="chip" onClick={() => onEdit(applyLightPreset(lighting, p, a))}>{p}</button>)}
        </div>
      </div>
      <div className="grid-2 tight">
        <Range label="Brilho" min={0} max={100} value={an.brightness} unit="%" onChange={(v) => onEdit(editAnimation(lighting, a, { brightness: v }))} />
        <Range label="Velocidade" min={0} max={20} value={an.speed} onChange={(v) => onEdit(editAnimation(lighting, a, { speed: v }))} />
      </div>
      <div className="timeline-head">
        <h3 id="frames-title">Linha do tempo</h3>
        <label className="stepper">
          Quadros
          <input type="number" name="frames" inputMode="numeric" min={1} max={8} value={an.frames}
            onChange={(e) => onEdit(editAnimation(lighting, a, { frames: Math.min(Math.max(Number(e.target.value), 1), 8) }))} />
        </label>
      </div>
      <div role="group" aria-label="Quadros da animação" className="timeline">
        {an.colors.slice(0, an.frames).map((c, f) => (
          <button key={f} type="button" className="frame" aria-label={`Quadro ${f + 1}`} aria-pressed={f === frame} onClick={() => setFrame(f)}>
            <span className="dots" aria-hidden="true">{LEDS.map((led) => <span key={led} style={{ background: c[led] }} />)}</span>
            <span aria-hidden="true">{f + 1}</span>
          </button>
        ))}
      </div>
      <div className="swatches">
        {LEDS.map((led) => {
          const color = an.colors[frame]![led]
          return (
            <div key={led} className="swatch">
              <input id={`led-${led}`} type="color" value={color} onChange={(e) => onEdit(setFrameColor(lighting, a, frame, led, e.target.value))} />
              <label htmlFor={`led-${led}`}>{LED_NAMES[led]}</label>
              <code aria-hidden="true">{color}</code>
            </div>
          )
        })}
      </div>
    </div>
  )
}
