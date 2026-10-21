import { useId, type CSSProperties } from 'react'

// name: nome acessível quando o rótulo visível é curto ("Início" dentro do card do LT)

type Props = { label: string; name?: string; min: number; max: number; value: number; unit?: string; onChange: (v: number) => void }

export function Range({ label, name, min, max, value, unit = '', onChange }: Props) {
  const id = useId()
  // --p pinta a parte cheia do trilho
  const style = { '--p': `${((value - min) / (max - min)) * 100}%` } as CSSProperties
  return (
    <div className="range">
      <label htmlFor={id}>{label}</label>
      {/* o leitor de tela já lê o aria-valuetext; <output> viraria um live region a cada passo */}
      <span className="value" aria-hidden="true">{value}{unit}</span>
      <input id={id} type="range" min={min} max={max} value={value} aria-label={name} aria-valuetext={`${value}${unit}`} style={style}
        onChange={(e) => onChange(Number(e.target.value))} />
    </div>
  )
}
