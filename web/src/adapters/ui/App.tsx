import { useCallback, useEffect, useReducer, useRef, useState } from 'react'
import type { ControllerChannel } from '../../application/ports'
import type { ConfigSession } from '../../application/session'
import type { InputState } from '../../domain/frames'
import {
  applyChanges, connect, disconnect, profileId, readProfile, rumbleTest, simulatePress, switchActiveProfile, watchInput,
} from '../../application/usecases'
import { Connect } from './Connect'
import { Icon } from './icons'
import { Info } from './Info'
import { LightingEditor } from './LightingEditor'
import { ProfilePanel, ProfileTabs } from './ProfileEditor'
import { Review } from './Review'
import { SECTIONS, TITLES, type Section } from './sections'
import { initial, pending, reducer } from './state'
import { ThemeToggle } from './ThemeToggle'
import { Triggers } from './Triggers'
import './app.css'

/** O q o main.tsx liga: o seletor WebHID e o controle simulado. */
export type Ports = { hidSupported: boolean; pick: () => Promise<ControllerChannel | null>; demo: () => ControllerChannel }

export function App({ ports }: { ports: Ports }) {
  const [s, dispatch] = useReducer(reducer, initial)
  const [section, setSection] = useState<Section>('triggers')
  const session = useRef<ConfigSession | null>(null)
  const panel = useRef<HTMLElement>(null)
  // fechar a aba/desmontar fecha o canal e para o heartbeat
  useEffect(() => () => void session.current?.close(), [])

  async function run(label: string, job: (session: ConfigSession) => Promise<void>) {
    dispatch({ type: 'busy', text: label })
    try {
      await job(session.current!)
    } catch (e) {
      dispatch({ type: 'error', text: `Erro: ${(e as Error).message}. Confira se o controle continua conectado e tente de novo.` })
    }
  }

  const open = (channel: () => Promise<ControllerChannel | null>) =>
    run('Conectando e lendo o controle…', async () => {
      const c = await connect(await channel(), (battery, charging) => dispatch({ type: 'battery', battery, charging }))
      if (!c) return dispatch({ type: 'done', text: 'Nenhum controle escolhido. Se ele não apareceu na lista, veja “Antes de conectar”.' })
      session.current = c.session
      dispatch({ type: 'connected', info: c.info, profile: c.profile, lighting: c.lighting })
    })

  const load = (n: number) =>
    run(`Lendo o perfil ${n}…`, async (ss) => dispatch({ type: 'loaded', ...(await readProfile(ss, profileId(n))) }))

  // o desenho só monta conectado, então a sessão já existe quando ele assina
  const watch = useCallback((cb: (i: InputState) => void) => watchInput(session.current!, cb), [])
  // soltar o botão pode chegar depois de desconectar
  const press = useCallback((name: string, down: boolean) => session.current && simulatePress(session.current, name, down), [])

  // callout do desenho: abre a seção e leva o foco (e a rolagem) pro painel
  function jump(to: Section) {
    setSection(to)
    panel.current!.focus()
  }

  const plan = pending(s)
  // fechar a aba perde as edições q ainda não foram gravadas
  const dirty = !!plan?.changeSets.length
  useEffect(() => {
    if (!dirty) return
    const warn = (e: BeforeUnloadEvent) => e.preventDefault()
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [dirty])
  const ready = s.info && s.profile && s.lighting && plan
  const busy = !!s.busy
  // grips do desenho: primeiro quadro da animação ativa, com as edições ainda não gravadas
  const lit = s.lighting && s.lighting.doc.animations[s.lighting.doc.active]!.colors[0]!

  return (
    <div className="app">
      <header className="topbar">
        <span className="brand" translate="no">GameSir Cyclone 2 <span className="muted">· Web</span></span>
        {ready && (
          <ProfileTabs id={s.profile!.id} active={s.info!.active} locked={plan.changeSets.length > 0} disabled={busy} onSelect={load} />
        )}
        <div className="topbar-end">
          {ready && (
            <button type="button" className="btn ghost small" disabled={busy}
              onClick={() => run('Desconectando…', async (ss) => {
                session.current = null
                await disconnect(ss)
                dispatch({ type: 'disconnected' })
              })}>Desconectar</button>
          )}
          <ThemeToggle />
        </div>
      </header>
      {s.info?.demo && (
        <p className="demo-banner"><strong>MODO DEMO</strong><span>controle simulado em memória, nada vai pra hardware nenhum.</span></p>
      )}
      <main>
        {!ready ? (
          <Connect hidSupported={ports.hidSupported} busy={busy}
            onConnect={() => open(ports.pick)} onDemo={() => open(async () => ports.demo())} />
        ) : (
          <fieldset className="workspace" disabled={busy}>
            <legend className="sr-only">Configuração</legend>
            <Info info={s.info!} battery={s.battery} charging={s.charging} onCallout={jump} watch={watch} onPress={s.info!.demo ? press : undefined}
              grips={[lit!.lower_left, lit!.lower_right]} />
            <div role="group" aria-label="Seções" className="tiles">
              {SECTIONS.map((k) => (
                <button key={k} type="button" className="tile" aria-pressed={section === k} onClick={() => setSection(k)}>
                  <Icon name={k} size={28} />{TITLES[k]}
                </button>
              ))}
            </div>
            <section ref={panel} className="panel" aria-labelledby="panel-title" tabIndex={-1}>
              <h2 id="panel-title">{TITLES[section]}</h2>
              {section === 'triggers' && <Triggers profile={s.profile!} onEdit={(profile) => dispatch({ type: 'edit', profile })} />}
              {section === 'lights' && <LightingEditor lighting={s.lighting!} onEdit={(lighting) => dispatch({ type: 'editLights', lighting })} />}
              {section === 'rumble' && (
                <div className="card-row">
                  <p className="hint">Liga os dois motores rapidinho pra conferir se o controle tá respondendo. Não grava nada.</p>
                  <button type="button" className="btn"
                    onClick={() => run('Vibrando…', async (ss) => {
                      await rumbleTest(ss)
                      dispatch({ type: 'done', text: 'Teste de vibração concluído.' })
                    })}><Icon name="rumble" /> Testar vibração</button>
                </div>
              )}
              {section === 'profile' && (
                <ProfilePanel profile={s.profile!} active={s.info!.active} locked={plan.changeSets.length > 0}
                  onEdit={(profile) => dispatch({ type: 'edit', profile })} onReload={() => load(s.profile!.id)}
                  onActivate={() => run('Trocando o perfil ativo…', async (ss) => dispatch({ type: 'switched', n: await switchActiveProfile(ss, s.profile!.id) }))} />
              )}
            </section>
            <Review plan={plan} confirming={s.confirming}
              onReview={() => dispatch({ type: 'review' })} onCancel={() => dispatch({ type: 'cancel' })}
              onDiscard={() => dispatch({ type: 'discard' })}
              onConfirm={() => run('Gravando no controle…', async (ss) => dispatch({ type: 'saved', ...(await applyChanges(ss, plan, true)) }))} />
          </fieldset>
        )}
      </main>
      <footer className="statusbar">
        <p role="status" aria-live="polite" className={s.status.error ? 'status error' : busy ? 'status busy' : 'status'}>{s.status.text}</p>
        {s.info && <span className="muted">firmware {s.info.firmware}</span>}
      </footer>
    </div>
  )
}
