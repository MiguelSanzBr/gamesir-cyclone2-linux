import { useEffect, useState, type PointerEvent } from 'react'
import type { InputState } from '../../domain/frames'
import {
  BODY, CALLOUTS, DPAD, DPAD_ARMS, DPAD_ARROWS, DPAD_CROSS, FACE, GRIPS, HOME, PLATE, PLAYER_COLORS, PLAYER_LEDS, SHOULDERS, SMALL, STICKS,
  VIEW, smoothClosed, smoothOpen,
} from './geometry'
import { TITLES, type Section } from './sections'

// skin preta do app Linux (theme.SKINS["black"]): o controle é preto nos dois temas da página
const FG = '#ececec'
const SKIN = {
  line: '#5a5a5e', plate: '#47474b', well: '#1a1a1c', off: '#2a2a2d',
  btn: ['#2a2a2d', '#6a6a70'], face: ['#1f1f22', '#55555c'], dpad: ['#3a3a3e', '#5d5d63'], stick: ['#1d1d20', '#48484e'],
  shoulder: ['#4a4d51', '#6b6f74'], trigger: ['#3c3e42', '#5b5e63'],
} as const
const TARGET: Partial<Record<string, Section>> = { 'LT / LB': 'triggers', 'RT / RB': 'triggers', Luzes: 'lights' }
const body = smoothClosed(BODY)
const cross = smoothClosed(DPAD_CROSS)

type Props = {
  /** cor dos grips esquerdo e direito */
  grips: readonly [string, string]
  /** perfil ativo, acende o traço do indicador; 0 = nenhum */
  active?: number
  /** com callouts: clicar num rótulo abre a seção dele */
  onCallout?: (s: Section) => void
  /** input físico ao vivo; sem ele o desenho fica parado */
  watch?: (cb: (i: InputState) => void) => () => void
  /** só no demo: apertar uma parte do desenho aperta o botão simulado */
  onPress?: (name: string, down: boolean) => void
}

function useInput(watch: Props['watch']): InputState | null {
  const [input, setInput] = useState<InputState | null>(null)
  useEffect(() => {
    if (!watch) return
    let frame = 0
    let last: InputState
    const off = watch((i) => {
      last = i
      // um render por quadro da tela, o 0x12 chega bem mais rápido q isso
      frame ||= requestAnimationFrame(() => {
        frame = 0
        setInput(last)
      })
    })
    return () => {
      off()
      cancelAnimationFrame(frame)
    }
  }, [watch])
  return input
}

const Label = ({ x, y, text }: { x: number; y: number; text: string }) => (
  <text x={x} y={y} className="part-label" fill={FG}>{text}</text>
)

export function Controller({ grips, active = 0, onCallout, watch, onPress }: Props) {
  const pct = (y: number) => `${((y - VIEW.y) / VIEW.h) * 100}%`
  const input = useInput(watch)
  const part = (name: string) => ({ 'data-part': name, className: input?.pressed.has(name) ? 'part lit' : 'part' })

  function press(e: PointerEvent) {
    const name = (e.target as Element).closest('[data-part]')?.getAttribute('data-part')
    if (!name) return
    onPress!(name, true)
    // solta onde o ponteiro for solto, mesmo fora do desenho
    const done = new AbortController()
    const up = () => {
      done.abort()
      onPress!(name, false)
    }
    window.addEventListener('pointerup', up, { signal: done.signal })
    window.addEventListener('pointercancel', up, { signal: done.signal })
  }

  return (
    <div className={onCallout ? 'figure with-callouts' : 'figure'}>
      {/* tradutor automático trocaria o "A" do botão por artigo; o tipo do React não tem translate no SVG */}
      <svg className={onPress ? 'controller pressable' : 'controller'} viewBox={`${VIEW.x} ${VIEW.y} ${VIEW.w} ${VIEW.h}`}
        role="img" aria-label="Desenho do GameSir Cyclone 2" {...{ translate: 'no' }} onPointerDown={onPress && press}>
        <defs>
          <linearGradient id="c2-body" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#3b3b3e" />
            <stop offset="0.5" stopColor="#2e2e31" />
            <stop offset="1" stopColor="#222224" />
          </linearGradient>
          <radialGradient id="c2-glow">
            <stop offset="0" className="glow-in" />
            <stop offset="1" className="glow-out" />
          </radialGradient>
          <filter id="c2-blur" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="5" /></filter>
          <filter id="c2-led" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3" /></filter>
        </defs>
        <ellipse cx={221} cy={298} rx={228} ry={26} fill="url(#c2-glow)" />
        <path d={body} transform="translate(0 7)" className="shadow" filter="url(#c2-blur)" />
        {(['LT', 'RT'] as const).map((n) => (
          <g key={n} {...part(n)}>
            <path d={smoothClosed(SHOULDERS[n])} fill={SKIN.trigger[0]} stroke={SKIN.trigger[1]} strokeWidth={1.5} />
            <path d={smoothClosed(SHOULDERS[n])} className="level" data-level={n} fillOpacity={(input?.[n === 'LT' ? 'lt' : 'rt'] ?? 0) / 255} />
          </g>
        ))}
        <Label x={114} y={-3} text="LT" />
        <Label x={328} y={-3} text="RT" />
        <path d={body} fill="url(#c2-body)" stroke={SKIN.line} strokeWidth={2} />
        {PLATE.map((l, i) => <polyline key={i} points={l.join(' ')} fill="none" stroke={SKIN.plate} strokeWidth={1.2} />)}
        {STICKS.map(([x, y]) => <circle key={x} cx={x} cy={y} r={33} fill={SKIN.well} stroke={SKIN.plate} strokeWidth={1.2} />)}
        <circle cx={DPAD.x} cy={DPAD.y} r={DPAD.ring} fill={SKIN.well} stroke={SKIN.plate} strokeWidth={1.2} />
        <path d={cross} transform="translate(1 2)" fill="#0d0d0e" />
        <path d={cross} fill={SKIN.dpad[0]} stroke={SKIN.dpad[1]} strokeWidth={1.5} />
        {DPAD_ARMS.map(([n, pts]) => <g key={n} {...part(n)}><path d={smoothClosed(pts)} className="arm" /></g>)}
        <g className="deco">
          <circle cx={DPAD.x} cy={DPAD.y} r={4} fill="#a6a6ae" stroke="#d8d8de" />
          {DPAD_ARROWS.map((a, i) => <polygon key={i} points={a.join(' ')} fill="#86868e" />)}
        </g>
        {PLAYER_LEDS.map(([x, y], i) => (
          <path key={y} d={`M${x - 5} ${y}H${x + 5}`} stroke={active === i + 1 ? PLAYER_COLORS[i] : SKIN.off} strokeWidth={3} strokeLinecap="round" />
        ))}
        {(['lower_left', 'lower_right'] as const).map((led, i) => (
          <g key={led} className="grip">
            <path d={smoothOpen(GRIPS[led])} fill="none" stroke={grips[i]} strokeWidth={12} strokeLinecap="round" opacity={0.45} filter="url(#c2-led)" />
            <path d={smoothOpen(GRIPS[led])} fill="none" stroke={grips[i]} strokeWidth={5} strokeLinecap="round" data-led={led} />
          </g>
        ))}
        {(['LB', 'RB'] as const).map((n) => (
          <g key={n} {...part(n)}>
            <path d={smoothClosed(SHOULDERS[n])} fill={SKIN.shoulder[0]} stroke={SKIN.shoulder[1]} strokeWidth={1.5} />
          </g>
        ))}
        <Label x={104} y={13} text="LB" />
        <Label x={338} y={13} text="RB" />
        {STICKS.map(([x, y], i) => {
          const [n, [dx, dy]] = i ? ['RS', input?.right ?? [0, 0]] : ['LS', input?.left ?? [0, 0]]
          // o miolo anda até 7 unidades dentro do poço, como no app Linux
          return (
            <g key={n} data-stick={n} transform={`translate(${dx * 7} ${dy * 7})`}>
              <g {...part(n)}>
                <circle cx={x} cy={y} r={26} fill={SKIN.stick[0]} stroke={SKIN.stick[1]} strokeWidth={1.5} />
                <circle cx={x} cy={y} r={12} fill="none" stroke={SKIN.stick[1]} />
                <path d={`M${x - 3.5} ${y - 19.7}A20 20 0 0 0 ${x - 20} ${y}`} fill="none" stroke="#555557" strokeWidth={2} />
              </g>
            </g>
          )
        })}
        {FACE.map(([t, x, y]) => (
          <g key={t} {...part(t)}>
            <circle cx={x} cy={y} r={14} fill={SKIN.face[0]} stroke={SKIN.face[1]} strokeWidth={1.5} />
            <Label x={x} y={y} text={t} />
          </g>
        ))}
        {SMALL.map(([x1, y1, x2, y2, t, n]) => (
          <g key={n} {...part(n)}>
            <rect x={x1} y={y1} width={x2 - x1} height={y2 - y1} rx={Math.min(4, (y2 - y1) / 4)}
              fill={SKIN.btn[0]} stroke={SKIN.btn[1]} strokeWidth={1.5} />
            <Label x={(x1 + x2) / 2} y={(y1 + y2) / 2} text={t} />
          </g>
        ))}
        <g {...part('Home')}>
          <circle cx={HOME[0]} cy={HOME[1]} r={14} fill="#5b5f66" stroke="#e0262b" strokeWidth={3} />
          <circle cx={HOME[0]} cy={HOME[1]} r={7} fill="#adafb3" />
        </g>
        {onCallout && (
          <g className="callout-lines">
            {CALLOUTS.map(([text, side, y, [tx, ty]]) => {
              const [edge, elbow] = side === 'l' ? [-24, -10] : [466, 452]
              return (
                <g key={text} className={TARGET[text] ? 'on' : 'off'}>
                  <polyline points={`${edge} ${y} ${elbow} ${y} ${tx} ${ty}`} fill="none" />
                  <circle cx={tx} cy={ty} r={3} />
                </g>
              )
            })}
          </g>
        )}
      </svg>
      {onCallout && CALLOUTS.map(([text, side, y]) => {
        const target = TARGET[text]
        const style = { top: pct(y) }
        return target ? (
          <button key={text} type="button" className={`callout ${side}`} style={style}
            aria-label={`${text}: abrir ${TITLES[target]}`} onClick={() => onCallout(target)}>{text}</button>
        ) : (
          <span key={text} className={`callout ${side} static`} style={style}>{text}</span>
        )
      })}
    </div>
  )
}
