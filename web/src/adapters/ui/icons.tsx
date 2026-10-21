import type { ReactNode } from 'react'

// ícones de linha dos blocos, port do ControllerView.icon do app Linux (centro em 0,0)
const rays = [[0, -1], [0, 1], [-1, 0], [1, 0], [0.7, 0.7], [-0.7, 0.7], [0.7, -0.7], [-0.7, -0.7]]
const ICONS = {
  triggers: <><rect x={-9} y={-13} width={18} height={26} rx={8} /><path d="M-9 -2H9" /></>,
  lights: <><circle r={6} />{rays.map(([dx, dy]) => <path key={`${dx}${dy}`} d={`M${dx! * 9} ${dy! * 9}L${dx! * 13} ${dy! * 13}`} />)}</>,
  rumble: <>{[-10, -3, 4, 11].map((x) => <path key={x} d={`M${x} -10Q${x - 3} -4 ${x} 0T${x} 10`} />)}</>,
  profile: <><circle cy={-8} r={5} /><path d="M-11 10a11 11 0 0 1 22 0" /></>,
  sun: <><circle r={5} />{rays.map(([dx, dy]) => <path key={`${dx}${dy}`} d={`M${dx! * 8.5} ${dy! * 8.5}L${dx! * 11.5} ${dy! * 11.5}`} />)}</>,
  moon: <path d="M6 7.5A10 10 0 0 1 -4.5 -9.5 10.5 10.5 0 1 0 9.5 4 9 9 0 0 1 6 7.5Z" />,
  plug: <path d="M-5 -12v6M5 -12v6M-9 -6h18v4a9 9 0 0 1-18 0zM0 7v6" />,
  check: <path d="M-8 0l5 5 11-11" />,
  alert: <><path d="M0 -12L12 10H-12Z" /><path d="M0 -4v6M0 6v.5" /></>,
  flask: <path d="M-4 -12h8M-3 -12v8l-8 14a2 2 0 0 0 2 3h18a2 2 0 0 0 2-3l-8-14v-8M-6 4h12" />,
}
export type IconName = keyof typeof ICONS

export function Icon({ name, size = 20 }: { name: IconName; size?: number }): ReactNode {
  return (
    <svg className="icon" width={size} height={size} viewBox="-16 -16 32 32" aria-hidden="true" focusable="false"
      fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      {ICONS[name]}
    </svg>
  )
}
