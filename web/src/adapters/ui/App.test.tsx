import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { App, type Ports } from './App'
import { DemoTransport } from '../demo/demo'
import { records } from '../demo/backup'
import { VIBRATE, WRITE } from '../../domain/frames'
import { decode } from '../../domain/profile'
import { decode as decodeLights } from '../../domain/lighting'
import type { ControllerChannel } from '../../application/ports'
import * as F from '../../test/fixtures'
import { unhex } from '../../test/hex'

const setup = (over: Partial<Ports> = {}) => {
  const t = new DemoTransport()
  const ports: Ports = { hidSupported: true, pick: vi.fn(async () => null), demo: () => t, ...over }
  const view = render(<App ports={ports} />)
  return { t, ports, view, user: userEvent.setup() }
}

const status = () => screen.getByRole('status')
const writes = (t: DemoTransport) => t.log.filter((r) => r[1] === WRITE)

async function enterDemo(over: Partial<Ports> = {}) {
  const s = setup(over)
  await s.user.click(screen.getByRole('button', { name: 'Entrar no modo demo' }))
  await screen.findByRole('heading', { name: 'Cyclone 2' })
  return s
}

// cada bloco abre o painel da sua seção
const open = (user: ReturnType<typeof userEvent.setup>, section: string) => user.click(screen.getByRole('button', { name: section }))
const grip = (view: ReturnType<typeof render>, led: string) => view.container.querySelector(`[data-led="${led}"]`)!.getAttribute('stroke')

/** Canal "de verdade" (demo = false) por cima do simulado. */
const realLike = (t: DemoTransport): ControllerChannel => ({
  demo: false, name: 'GameSir-Cyclone 2', pid: 0x101d, send: (r) => t.send(r), listen: (cb) => t.listen(cb), close: () => t.close(),
})

describe('tela inicial', () => {
  it('sem WebHID: hero com o desenho, aviso de Chrome/Edge, conectar desabilitado e modo demo', () => {
    setup({ hidSupported: false })
    expect(screen.getByRole('img', { name: 'Desenho do GameSir Cyclone 2' })).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent(/não tem WebHID.*Chrome ou Edge/)
    expect(screen.getByRole('button', { name: 'Conectar controle' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Conectar controle' })).toHaveAccessibleDescription(/não tem WebHID/)
    expect(screen.getByRole('button', { name: 'Entrar no modo demo' })).toBeEnabled()
  })

  it('explica o modo com config e a regra udev do Linux', () => {
    setup()
    expect(screen.queryByRole('alert')).toBeNull()
    expect(screen.getByText(/0x101D/)).toBeInTheDocument()
    expect(screen.getByText(/70-gamesir-cyclone2\.rules/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /gamesir-cyclone2-linux/ })).toHaveAttribute('href', 'https://github.com/MiguelSanzBr/gamesir-cyclone2-linux')
  })

  it('usuário cancela o seletor do navegador', async () => {
    const { user, ports } = setup()
    await user.click(screen.getByRole('button', { name: 'Conectar controle' }))
    expect(ports.pick).toHaveBeenCalled()
    // a lista vazia no Linux sem udev parece cancelamento: aponta pras notas
    await waitFor(() => expect(status()).toHaveTextContent('Nenhum controle escolhido. Se ele não apareceu na lista, veja “Antes de conectar”.'))
  })

  it('erro ao abrir o controle aparece no status', async () => {
    const { user } = setup({ pick: async () => { throw new Error('acesso negado') } })
    await user.click(screen.getByRole('button', { name: 'Conectar controle' }))
    await waitFor(() => expect(status()).toHaveTextContent('Erro: acesso negado. Confira se o controle continua conectado e tente de novo.'))
    expect(status()).toHaveClass('error')
  })

  it('marca, WebHID e nome de arquivo ficam fora do tradutor automático', () => {
    setup({ hidSupported: false })
    expect(screen.getByRole('heading', { name: 'GameSir Cyclone 2' })).toHaveAttribute('translate', 'no')
    expect(within(screen.getByRole('banner')).getByText(/GameSir Cyclone 2/)).toHaveAttribute('translate', 'no')
    expect(screen.getByRole('img', { name: 'Desenho do GameSir Cyclone 2' })).toHaveAttribute('translate', 'no')
    for (const e of screen.getAllByText('WebHID')) expect(e).toHaveAttribute('translate', 'no')
    expect(screen.getAllByText('WebHID')).toHaveLength(2)
    expect(screen.getByText('70-gamesir-cyclone2.rules')).toHaveAttribute('translate', 'no')
  })

  it('controle de verdade: info sem faixa de demo, firmware na barra de status', async () => {
    const t = new DemoTransport()
    t.dongle = '1\x002'
    const { user } = setup({ pick: async () => realLike(t) })
    await user.click(screen.getByRole('button', { name: 'Conectar controle' }))
    const info = await screen.findByRole('region', { name: 'Controle' })
    expect(within(info).getByText('Cyclone 2 (cabo)')).toBeInTheDocument()
    expect(within(info).getByText('dongle 1.2')).toBeInTheDocument()
    expect(within(screen.getByRole('contentinfo')).getByText('firmware 3.5.6')).toBeInTheDocument()
    expect(screen.queryByText(/MODO DEMO/)).toBeNull()
    expect(status()).toHaveTextContent('Configuração lida do controle.')
  })
})

describe('tema', () => {
  // as duas cores da barra do navegador, como no index.html
  const bar = (theme: string) => document.head.querySelector(`meta[name="theme-color"][data-theme="${theme}"]`)!
  beforeEach(() => {
    document.head.innerHTML = '<meta name="theme-color" data-theme="light" media="(prefers-color-scheme: light)">'
      + '<meta name="theme-color" data-theme="dark" media="(prefers-color-scheme: dark)">'
  })
  afterEach(() => {
    delete document.documentElement.dataset.theme
    localStorage.clear()
    document.head.innerHTML = ''
  })

  it('segue o sistema, e o botão troca e lembra a escolha', async () => {
    vi.spyOn(window, 'matchMedia').mockReturnValue({ matches: true } as MediaQueryList)
    const { user } = setup()
    await user.click(screen.getByRole('button', { name: 'Usar tema claro' }))
    expect([document.documentElement.dataset.theme, localStorage.getItem('theme')]).toEqual(['light', 'light'])
    expect([bar('light').getAttribute('media'), bar('dark').getAttribute('media')]).toEqual(['all', 'not all'])
    await user.click(screen.getByRole('button', { name: 'Usar tema escuro' }))
    expect([document.documentElement.dataset.theme, localStorage.getItem('theme')]).toEqual(['dark', 'dark'])
    expect([bar('light').getAttribute('media'), bar('dark').getAttribute('media')]).toEqual(['not all', 'all'])
  })

  it('tema escolhido antes (aplicado pelo index.html) vence o do sistema', () => {
    document.documentElement.dataset.theme = 'light'
    vi.spyOn(window, 'matchMedia').mockReturnValue({ matches: true } as MediaQueryList)
    setup()
    expect(screen.getByRole('button', { name: 'Usar tema escuro' })).toBeInTheDocument()
  })
})

describe('modo demo', () => {
  it('mostra a faixa de demo, o controle, a bateria e o firmware', async () => {
    await enterDemo()
    expect(screen.getByText(/MODO DEMO/)).toBeInTheDocument()
    const info = screen.getByRole('region', { name: 'Controle' })
    expect(within(info).getByText('Perfil ativo no controle: 1')).toBeInTheDocument()
    expect(within(info).getByText('Cyclone 2 (cabo, ADC)')).toBeInTheDocument()
    expect(within(info).getByRole('img', { name: 'Desenho do GameSir Cyclone 2' })).toBeInTheDocument()
    await waitFor(() => expect(within(info).getByText('80%')).toBeInTheDocument())
    expect(within(screen.getByRole('contentinfo')).getByText('firmware 3.5.6')).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: 'Perfil 1 (ativo)' })).toBeChecked()
  })

  it('bateria carregando', async () => {
    const t = new DemoTransport()
    t.charging = true
    await enterDemo({ demo: () => t })
    expect(await screen.findByText('80% (carregando)')).toBeInTheDocument()
  })

  it('blocos só das seções q a versão web suporta, cada um abre o seu painel', async () => {
    const { user } = await enterDemo()
    const tiles = within(screen.getByRole('group', { name: 'Seções' })).getAllByRole('button')
    expect(tiles.map((b) => b.textContent)).toEqual(['Gatilhos', 'Luzes', 'Vibração', 'Perfil'])
    expect(screen.getByRole('button', { name: 'Gatilhos' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('region', { name: 'Gatilhos' })).toBeInTheDocument()
    await open(user, 'Luzes')
    expect(screen.getByRole('button', { name: 'Luzes' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: 'Gatilhos' })).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByRole('region', { name: 'Luzes' })).toBeInTheDocument()
    expect(screen.queryByLabelText('LT: início da zona morta')).toBeNull()
  })

  it('callouts do desenho levam pra seção e põem o foco no painel; os sem suporte são só legenda', async () => {
    const { user } = await enterDemo()
    await user.click(screen.getByRole('button', { name: 'Luzes: abrir Luzes' }))
    expect(screen.getByRole('region', { name: 'Luzes' })).toHaveFocus()
    await user.click(screen.getByRole('button', { name: 'RT / RB: abrir Gatilhos' }))
    expect(screen.getByRole('region', { name: 'Gatilhos' })).toHaveFocus()
    expect(screen.getByRole('button', { name: 'LT / LB: abrir Gatilhos' })).toBeInTheDocument()
    expect(screen.getByText('Analógico esquerdo')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Analógico|D-pad|ABXY|Traseiros/ })).toBeNull()
  })

  it('os grips do desenho mostram a cor das luzes, inclusive a editada', async () => {
    const { user, view } = await enterDemo()
    const doc = decodeLights(records()[32]!)
    const frame = doc.animations[doc.active]!.colors[0]!
    expect([grip(view, 'lower_left'), grip(view, 'lower_right')]).toEqual([frame.lower_left, frame.lower_right])
    await open(user, 'Luzes')
    fireEvent.change(screen.getByLabelText('Grip esquerdo'), { target: { value: '#00ffaa' } })
    expect(grip(view, 'lower_left')).toBe('#00ffaa')
  })

  it('edição fica staged: nada é gravado sem confirmar, e cancelar não grava', async () => {
    const { t, user } = await enterDemo()
    await open(user, 'Perfil')
    await user.type(screen.getByLabelText('Nome do perfil'), 'Corrida')
    await open(user, 'Gatilhos')
    fireEvent.change(screen.getByLabelText('LT: início da zona morta'), { target: { value: '10' } })
    fireEvent.change(screen.getByLabelText('LT: fim da zona morta'), { target: { value: '90' } })
    await user.click(screen.getByLabelText('RT: fixo'))
    fireEvent.change(screen.getByLabelText('RT: hair trigger início'), { target: { value: '20' } })
    fireEvent.change(screen.getByLabelText('RT: hair trigger fim'), { target: { value: '80' } })
    const bar = screen.getByRole('region', { name: 'Alterações pendentes' })
    expect(bar).toHaveTextContent('4 alterações')
    expect(bar).toHaveTextContent('nada foi gravado ainda')
    expect(screen.getByRole('radio', { name: 'Perfil 2' })).toBeDisabled()

    await user.click(screen.getByRole('button', { name: 'Revisar e gravar' }))
    const dialog = screen.getByRole('dialog', { name: 'Confirmar gravação' })
    expect(within(dialog).getByText(/Nome do perfil/)).toHaveTextContent('Nome do perfil: (sem nome) → Corrida')
    expect(within(dialog).getByText(/RT: hair trigger/)).toHaveTextContent('adaptativo, 10% a 90% → fixo, 20% a 80%')
    expect(within(dialog).getByText(/Perfil 1: bytes/)).toHaveTextContent('Perfil 1: bytes 0 a 536 (537 bytes)')
    expect(within(dialog).getByRole('button', { name: 'Gravar no controle' })).toHaveFocus()
    expect(writes(t)).toHaveLength(0)

    await user.click(within(dialog).getByRole('button', { name: 'Cancelar' }))
    expect(screen.queryByRole('dialog')).toBeNull()
    await user.click(screen.getByRole('button', { name: 'Revisar e gravar' }))
    await user.keyboard('a')
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(writes(t)).toHaveLength(0)
    expect(t.records[1]).toEqual(records()[1])
  })

  it('confirmar grava só o intervalo mudado, confere e aplica', async () => {
    const { t, user } = await enterDemo()
    await user.click(screen.getByLabelText('LT: hair trigger'))
    await user.click(screen.getByRole('button', { name: 'Revisar e gravar' }))
    await user.click(screen.getByRole('button', { name: 'Gravar no controle' }))
    await waitFor(() => expect(status()).toHaveTextContent('Gravado e conferido no controle (1 bytes).'))
    expect(writes(t).map((w) => [w[2], (w[3]! << 8) | w[4]!, w[5]])).toEqual([[1, 506, 1]])
    expect(decode(t.records[1]!).triggers.LT.hair_trigger.on).toBe(false)
    expect(screen.queryByRole('region', { name: 'Alterações pendentes' })).toBeNull()
    expect(screen.getByLabelText('LT: hair trigger')).not.toBeChecked()
  })

  it('fechar a aba com alteração pendente pede confirmação do navegador, sem pendência não', async () => {
    const { user } = await enterDemo()
    const leave = () => {
      const e = new Event('beforeunload', { cancelable: true })
      window.dispatchEvent(e)
      return e.defaultPrevented
    }
    expect(leave()).toBe(false)
    await user.click(screen.getByLabelText('LT: hair trigger'))
    expect(leave()).toBe(true)
    await user.click(screen.getByRole('button', { name: 'Descartar' }))
    expect(leave()).toBe(false)
  })

  it('nome do perfil sem corretor nem autocompletar, quadros com teclado numérico', async () => {
    const { user } = await enterDemo()
    await open(user, 'Perfil')
    const name = screen.getByLabelText('Nome do perfil')
    expect(name).toHaveAttribute('spellcheck', 'false')
    expect(name).toHaveAttribute('autocomplete', 'off')
    expect(name).toHaveAttribute('name', 'profile-name')
    await open(user, 'Luzes')
    expect(screen.getByLabelText('Quadros')).toHaveAttribute('inputmode', 'numeric')
    expect(screen.getByLabelText('Quadros')).toHaveAttribute('name', 'frames')
  })

  it('descartar volta pro q tá no controle', async () => {
    const { user } = await enterDemo()
    await open(user, 'Perfil')
    await user.type(screen.getByLabelText('Nome do perfil'), 'X')
    await user.click(screen.getByRole('button', { name: 'Descartar' }))
    expect(screen.getByLabelText('Nome do perfil')).toHaveValue('')
    expect(status()).toHaveTextContent('Alterações descartadas.')
  })

  it('falha na conferência vira erro e não marca como gravado', async () => {
    const { t, user } = await enterDemo()
    t.corrupt = true
    await open(user, 'Perfil')
    await user.type(screen.getByLabelText('Nome do perfil'), 'X')
    await user.click(screen.getByRole('button', { name: 'Revisar e gravar' }))
    await user.click(screen.getByRole('button', { name: 'Gravar no controle' }))
    await waitFor(() => expect(status()).toHaveTextContent('Erro: verificação falhou'))
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(screen.getByRole('region', { name: 'Alterações pendentes' })).toHaveTextContent('1 alteração')
  })

  it('troca o perfil em edição, ativa no controle e lê de novo', async () => {
    const { t, user } = await enterDemo()
    await user.click(screen.getByRole('radio', { name: 'Perfil 3' }))
    await waitFor(() => expect(status()).toHaveTextContent('Perfil 3 lido do controle.'))
    await open(user, 'Perfil')
    await user.click(screen.getByRole('button', { name: 'Tornar ativo no controle' }))
    await waitFor(() => expect(status()).toHaveTextContent('Perfil 3 ativo no controle.'))
    expect(t.current).toBe(3)
    expect(screen.getByRole('radio', { name: 'Perfil 3 (ativo)' })).toBeChecked()
    expect(screen.getByText('Perfil ativo no controle: 3')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Tornar ativo no controle' })).toBeDisabled()
    t.records[3]![0] = 0x5a
    await user.click(screen.getByRole('button', { name: 'Ler do controle de novo' }))
    await waitFor(() => expect(screen.getByLabelText('Nome do perfil')).toHaveValue('Z'))
  })

  it('luzes: animação ativa, preset, brilho, velocidade, quadros na linha do tempo e cor', async () => {
    const { t, user } = await enterDemo()
    await open(user, 'Luzes')
    await user.click(screen.getByRole('radio', { name: 'Animação 2' }))
    await user.click(screen.getByRole('button', { name: 'Rainbow' }))
    fireEvent.change(screen.getByLabelText('Brilho'), { target: { value: '70' } })
    expect(screen.getByLabelText('Velocidade')).toHaveValue('10')
    const timeline = screen.getByRole('group', { name: 'Quadros da animação' })
    expect(within(timeline).getAllByRole('button')).toHaveLength(8)
    await user.click(within(timeline).getByRole('button', { name: 'Quadro 8' }))
    expect(within(timeline).getByRole('button', { name: 'Quadro 8' })).toHaveAttribute('aria-pressed', 'true')
    fireEvent.change(screen.getByLabelText('Quadros'), { target: { value: '3' } })
    expect(within(timeline).getAllByRole('button')).toHaveLength(3)
    expect(within(timeline).getByRole('button', { name: 'Quadro 3' })).toHaveAttribute('aria-pressed', 'true')
    fireEvent.change(screen.getByLabelText('Botão Home'), { target: { value: '#00ffaa' } })
    fireEvent.change(screen.getByLabelText('Velocidade'), { target: { value: '12' } })
    await user.click(screen.getByRole('button', { name: 'Revisar e gravar' }))
    expect(screen.getByText(/Luzes \(registro 32\): bytes/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Gravar no controle' }))
    await waitFor(() => expect(status()).toHaveTextContent('Gravado e conferido'))
    const an = decodeLights(t.records[32]!)
    expect([an.active, an.animations[1]!.brightness, an.animations[1]!.speed, an.animations[1]!.frames, an.animations[1]!.colors[2]!.home])
      .toEqual([1, 70, 12, 3, '#00ffaa'])
  })

  it('quadros fora de 1 a 8 viram o limite mais perto', async () => {
    const { user } = await enterDemo()
    await open(user, 'Luzes')
    fireEvent.change(screen.getByLabelText('Quadros'), { target: { value: '0' } })
    expect(screen.getByLabelText('Quadros')).toHaveValue(1)
    fireEvent.change(screen.getByLabelText('Quadros'), { target: { value: '12' } })
    expect(screen.getByLabelText('Quadros')).toHaveValue(8)
  })

  it('teste de vibração', async () => {
    const { t, user } = await enterDemo()
    await open(user, 'Vibração')
    await user.click(screen.getByRole('button', { name: 'Testar vibração' }))
    await waitFor(() => expect(status()).toHaveTextContent('Teste de vibração concluído.'), { timeout: 3000 })
    expect(t.log.filter((r) => r[1] === VIBRATE)).toHaveLength(2)
  })

  it('desconectar volta pra tela inicial e fecha o canal', async () => {
    const { t, user } = await enterDemo()
    const close = vi.spyOn(t, 'close')
    await user.click(screen.getByRole('button', { name: 'Desconectar' }))
    await waitFor(() => expect(status()).toHaveTextContent('Desconectado.'))
    expect(close).toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Entrar no modo demo' })).toBeInTheDocument()
  })

  it('desmontar a página fecha o canal (para o heartbeat)', async () => {
    const { t, view } = await enterDemo()
    const close = vi.spyOn(t, 'close')
    act(() => view.unmount())
    expect(close).toHaveBeenCalled()
  })

  it('desmontar sem conexão não quebra', () => {
    const { view } = setup()
    expect(() => view.unmount()).not.toThrow()
  })
})

describe('desenho ao vivo', () => {
  const part = (view: ReturnType<typeof render>, name: string) => view.container.querySelector(`[data-part="${name}"]`)!
  const level = (view: ReturnType<typeof render>, name: string) => Number(view.container.querySelector(`[data-level="${name}"]`)!.getAttribute('fill-opacity'))
  const lit = (view: ReturnType<typeof render>) => [...view.container.querySelectorAll('.part.lit')].map((e) => e.getAttribute('data-part'))

  it('demo: apertar uma parte do desenho acende, soltar apaga', async () => {
    const { view, t } = await enterDemo()
    expect(screen.getByText('Aperte os botões do controle: eles acendem aqui. No demo, clique nas partes do desenho.')).toBeInTheDocument()
    fireEvent.pointerDown(part(view, 'A'))
    expect(t.pressed).toEqual(new Set(['A']))
    await waitFor(() => expect(lit(view)).toEqual(['A']))
    fireEvent.pointerUp(window)
    await waitFor(() => expect(lit(view)).toEqual([]))
  })

  it('demo: d-pad por direção, gatilho enche e clicar fora das partes não aperta nada', async () => {
    const { view, t } = await enterDemo()
    fireEvent.pointerDown(part(view, 'Up').querySelector('path')!)
    await waitFor(() => expect(lit(view)).toEqual(['Up']))
    fireEvent.pointerCancel(window)
    await waitFor(() => expect(lit(view)).toEqual([]))
    fireEvent.pointerDown(part(view, 'LT'))
    await waitFor(() => expect(lit(view)).toEqual(['LT']))
    expect([level(view, 'LT'), level(view, 'RT')]).toEqual([1, 0])
    fireEvent.pointerUp(window)
    fireEvent.pointerDown(screen.getByRole('img', { name: 'Desenho do GameSir Cyclone 2' }))
    expect(t.pressed.size).toBe(0)
  })

  it('controle de verdade: acende pelo 0x12, analógico sai do lugar e gatilho enche pela pressão; clicar não aperta', async () => {
    const t = new DemoTransport()
    const cbs = new Set<(r: Uint8Array) => void>()
    const channel: ControllerChannel = {
      ...realLike(t),
      listen: (cb) => {
        cbs.add(cb)
        const off = t.listen(cb)
        return () => {
          cbs.delete(cb)
          off()
        }
      },
    }
    const { user, view } = setup({ pick: async () => channel })
    await user.click(screen.getByRole('button', { name: 'Conectar controle' }))
    await screen.findByRole('heading', { name: 'Cyclone 2' })
    expect(screen.getByText('Aperte os botões do controle: eles acendem aqui.')).toBeInTheDocument()
    // vários 0x12 no mesmo quadro: o desenho só pega o último
    act(() => [F.STATE_REPORT, F.STATE_REPORT_2].forEach((r) => cbs.forEach((cb) => cb(unhex(r)))))
    await waitFor(() => expect(lit(view)).toContain('B'))
    expect(lit(view).sort()).toEqual([...F.STATE_2.pressed].sort())
    expect(level(view, 'LT')).toBeCloseTo(128 / 255)
    expect(view.container.querySelector('[data-stick="LS"]')!.getAttribute('transform')).toBe(`translate(${-0.5 * 7} ${F.STATE_2.left[1]! * 7})`)
    expect(view.container.querySelector('[data-stick="RS"]')!.getAttribute('transform')).toBe('translate(7 -7)')
    fireEvent.pointerDown(part(view, 'A'))
    expect(t.pressed.size).toBe(0)
  })

  it('demo: soltar o botão depois de desconectar não quebra', async () => {
    const { view, t } = await enterDemo()
    fireEvent.pointerDown(part(view, 'Menu'))
    // clique de teclado: não solta o ponteiro antes
    fireEvent.click(screen.getByRole('button', { name: 'Desconectar' }))
    await screen.findByRole('button', { name: 'Entrar no modo demo' })
    fireEvent.pointerUp(window)
    expect(t.pressed).toEqual(new Set(['Menu']))
  })

  it('tela inicial: desenho parado, sem dica de botão', () => {
    const { view } = setup()
    expect(lit(view)).toEqual([])
    expect(screen.queryByText(/eles acendem aqui/)).toBeNull()
  })
})
