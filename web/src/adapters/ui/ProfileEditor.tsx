import type { Profile } from '../../domain/aggregates'
import { rename } from '../../application/usecases'

type Tabs = { id: number; active: number; locked: boolean; disabled: boolean; onSelect: (n: number) => void }

/** Abas Perfil 1 a 4 da barra de cima: trocar lê o perfil do controle. */
export function ProfileTabs({ id, active, locked, disabled, onSelect }: Tabs) {
  return (
    <fieldset className="tabs" disabled={locked || disabled}>
      <legend className="sr-only">Perfil em edição{locked && ' (grave ou descarte antes de trocar)'}</legend>
      {[1, 2, 3, 4].map((n) => (
        <label key={n} className="tab" title={locked ? 'Grave ou descarte antes de trocar' : undefined}>
          <input type="radio" name="profile" checked={id === n} onChange={() => onSelect(n)}
            aria-label={n === active ? `Perfil ${n} (ativo)` : `Perfil ${n}`} />
          Perfil {n}
          {n === active && <span className="dot ok" aria-hidden="true" />}
        </label>
      ))}
    </fieldset>
  )
}

type Panel = { profile: Profile; active: number; locked: boolean; onEdit: (p: Profile) => void; onReload: () => void; onActivate: () => void }

export function ProfilePanel({ profile, active, locked, onEdit, onReload, onActivate }: Panel) {
  return (
    <div className="stack">
      <div className="field">
        <label htmlFor="profile-name">Nome do perfil</label>
        <input id="profile-name" name="profile-name" type="text" autoComplete="off" spellCheck={false} value={profile.doc.name} placeholder="(sem nome)"
          onChange={(e) => onEdit(rename(profile, e.target.value))} aria-describedby="name-hint" />
        <p id="name-hint" className="hint">Até 31 bytes em UTF-8; o resto é cortado num caractere inteiro.</p>
      </div>
      <div className="card-row">
        <div>
          <h3>Perfil {profile.id} no controle</h3>
          <p className="hint">
            {profile.id === active ? 'Este já é o perfil q o controle tá usando.' : 'Trocar o perfil ativo é na hora e não grava memória, igual o botão do controle.'}
          </p>
        </div>
        <div className="actions">
          <button type="button" className="btn" disabled={profile.id === active} onClick={onActivate}>Tornar ativo no controle</button>
          <button type="button" className="btn ghost" disabled={locked} onClick={onReload}>Ler do controle de novo</button>
        </div>
      </div>
    </div>
  )
}
