import type { Plan } from '../../application/usecases'
import { Icon } from './icons'

type Props = { plan: Plan; confirming: boolean; onReview: () => void; onCancel: () => void; onDiscard: () => void; onConfirm: () => void }

const recordName = (n: number) => (n === 32 ? 'Luzes (registro 32)' : `Perfil ${n}`)

export function Review({ plan, confirming, onReview, onCancel, onDiscard, onConfirm }: Props) {
  const n = plan.changes.length
  if (!plan.changeSets.length) return null
  return (
    <section className="actionbar" aria-label="Alterações pendentes">
      <p>
        <span className="count">{n}</span> <strong>{n === 1 ? 'alteração' : 'alterações'}</strong>
        <span className="muted">, nada foi gravado ainda</span>
      </p>
      <div className="actions">
        <button type="button" className="btn ghost" onClick={onDiscard}>Descartar</button>
        <button type="button" className="btn primary" onClick={onReview}>Revisar e gravar</button>
      </div>
      {confirming && (
        <div className="backdrop">
          <div role="dialog" aria-modal="true" aria-labelledby="review-title" className="dialog"
            onKeyDown={(e) => e.key === 'Escape' && onCancel()}>
            <h2 id="review-title">Confirmar gravação</h2>
            <ul className="changes">
              {plan.changes.map((c) => <li key={c.label}>{c.label}: {c.from} → {c.to}</li>)}
            </ul>
            <p className="hint">Só estes bytes vão pro controle, e depois o registro é lido de volta pra conferir:</p>
            <ul className="bytes">
              {plan.changeSets.map((c) => (
                <li key={c.record}>{recordName(c.record)}: bytes {c.start} a {c.end - 1} ({c.end - c.start} bytes)</li>
              ))}
            </ul>
            <div className="actions end">
              <button type="button" className="btn ghost" onClick={onCancel}>Cancelar</button>
              <button type="button" className="btn primary" autoFocus onClick={onConfirm}><Icon name="check" /> Gravar no controle</button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
