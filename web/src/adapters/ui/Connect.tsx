import { Controller } from './Controller'
import { Icon } from './icons'

const LINUX = 'https://github.com/MiguelSanzBr/gamesir-cyclone2-linux'
// sem luzes lidas ainda: as cores do print do app Linux
const GRIPS = ['#a24cf0', '#18c95a'] as const

type Props = { hidSupported: boolean; busy: boolean; onConnect: () => void; onDemo: () => void }

export function Connect({ hidSupported, busy, onConnect, onDemo }: Props) {
  return (
    <section className="landing" aria-labelledby="connect-title">
      <div className="landing-art"><Controller grips={GRIPS} /></div>
      <div className="landing-copy">
        <p className="eyebrow">Configurador no navegador</p>
        <h1 id="connect-title" translate="no">GameSir Cyclone 2</h1>
        <p className="lead">
          Ajusta gatilhos, hair trigger, luzes e perfis direto pelo <span translate="no">WebHID</span>, sem instalar nada. Lê primeiro, deixa você
          editar e só grava depois de você conferir a lista do q vai mudar.
        </p>
        {!hidSupported && (
          <p role="alert" id="no-hid" className="notice warning">
            <Icon name="alert" />
            <span>Este navegador não tem <span translate="no">WebHID</span>. Use Chrome ou Edge no computador pra conectar o controle. O modo demo funciona em qualquer navegador.</span>
          </p>
        )}
        <div className="actions">
          <button type="button" className="btn primary" disabled={busy || !hidSupported} onClick={onConnect}
            aria-describedby={hidSupported ? undefined : 'no-hid'}>
            <Icon name="plug" /> Conectar controle
          </button>
          <button type="button" className="btn" disabled={busy} onClick={onDemo}>
            <Icon name="flask" /> Entrar no modo demo
          </button>
        </div>
        <details className="notes">
          <summary>Antes de conectar</summary>
          <ul>
            <li>
              O controle precisa estar num modo q aceita configuração, o mesmo q o GameSir Connect configura: cabo
              (USB 3537:0x101D ou 0x1053) ou 2.4G (0x102A, ou 0x100B pelo dongle). Em outro modo a interface de config
              (usage page 0xFFF0) nem aparece pro navegador.
            </li>
            <li>
              No Linux o Chrome abre o controle pelo hidraw, e sem permissão ele não aparece na lista. Instale a regra
              udev <code translate="no">70-gamesir-cyclone2.rules</code> do projeto <a href={LINUX}>gamesir-cyclone2-linux</a> e
              reconecte o controle.
            </li>
          </ul>
        </details>
      </div>
    </section>
  )
}
