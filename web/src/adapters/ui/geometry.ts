// Desenho do Cyclone 2, port do gui/geometry.py do projeto Linux: mesmas coordenadas lógicas numa caixa 442 x 318.
type Pt = readonly [number, number]

export const WIDTH = 442
export const HEIGHT = 318
export const TOP = 16 // espaço acima do corpo pros gatilhos
// o brilho embaixo e o L4/R4 passam um pouco do corpo
export const VIEW = { x: 0, y: -TOP, w: WIDTH, h: HEIGHT + TOP + 6 }

const mirror = (pts: readonly Pt[]): Pt[] => pts.map(([x, y]) => [WIDTH - x, y])
const xy = (p: Pt) => `${p[0]} ${p[1]}`
const mid = (a: Pt, b: Pt) => `${(a[0] + b[0]) / 2} ${(a[1] + b[1]) / 2}`

/** Polígono smooth=True do Tk: spline quadrática passando pelo meio das arestas, com o vértice de controle. */
export function smoothClosed(pts: readonly Pt[]): string {
  const n = pts.length
  return `M${mid(pts[n - 1]!, pts[0]!)}` + pts.map((p, i) => `Q${xy(p)} ${mid(p, pts[(i + 1) % n]!)}`).join('') + 'Z'
}

/** Linha smooth=True do Tk: igual o polígono, mas começa e termina nas pontas. */
export function smoothOpen(pts: readonly Pt[]): string {
  const last = pts.length - 1
  return `M${xy(pts[0]!)}` + pts.slice(1, last).map((p, i) => `Q${xy(p)} ${i === last - 2 ? xy(pts[last]!) : mid(p, pts[i + 2]!)}`).join('')
}

// contorno do corpo, horário a partir do canto de cima à esquerda
export const BODY: Pt[] = [[78, 24], [110, 14], [221, 11], [332, 14], [364, 24], [376, 32], [388, 48], [394, 64], [400, 80],
  [405, 96], [411, 112], [416, 128], [422, 144], [427, 160], [431, 176], [435, 192], [438, 208], [440, 224], [441, 240],
  [440, 256], [434, 272], [425, 280], [416, 286], [400, 292], [384, 286], [368, 270], [352, 254], [336, 237], [320, 223],
  [304, 217], [221, 216], [138, 217], [122, 223], [106, 237], [90, 254], [74, 270], [58, 286], [42, 292], [26, 286],
  [17, 280], [8, 272], [1, 256], [0, 240], [1, 224], [3, 208], [6, 192], [10, 176], [14, 160], [19, 144], [25, 128],
  [30, 112], [36, 96], [42, 80], [48, 64], [54, 48], [66, 32]]

const LB: Pt[] = [[50, 42], [60, 22], [78, 9], [104, 3], [138, 2], [154, 8], [152, 20], [120, 22], [96, 26], [74, 36], [60, 50]]
const LT: Pt[] = [[80, 8], [90, -6], [112, -12], [136, -10], [148, -2], [140, 4], [110, 4]]
export const SHOULDERS = { LT, RT: mirror(LT), LB, RB: mirror(LB) }

export const DPAD = { x: 163, y: 157, ring: 37, arm: 30, half: 11 }
const DIRS: Pt[] = [[0, -1], [1, 0], [0, 1], [-1, 0]]
// gira pontos desenhados pro braço de cima na direção (dx, dy) e leva pro centro do d-pad
const turn = (pts: Pt[], [dx, dy]: Pt) => pts.map(([x, y]): Pt => [DPAD.x - y * dx - x * dy, DPAD.y + x * dx - y * dy])
// cruz inteira num polígono só: o canto de dentro repetido fica vivo, a ponta sai redonda
export const DPAD_CROSS = DIRS.flatMap((d) => turn([[-DPAD.half, -DPAD.arm], [DPAD.half, -DPAD.arm], [DPAD.half, -DPAD.half], [DPAD.half, -DPAD.half]], d))
// um braço por direção, pra acender só o q tá apertado (DPAD_ARMS do Python)
const H = DPAD.half
export const DPAD_ARMS = (['Up', 'Right', 'Down', 'Left'] as const).map((n, i) => [n, turn([[-H, -H], [-H, -H], [-H, -DPAD.arm], [H, -DPAD.arm], [H, -H], [H, -H]], DIRS[i]!)] as const)
export const DPAD_ARROWS = DIRS.map(([dx, dy]): Pt[] => {
  const x = DPAD.x + (DPAD.arm - 11) * dx
  const y = DPAD.y + (DPAD.arm - 11) * dy
  return [[x + 4.5 * dx, y + 4.5 * dy], [x - 4.5 * dy - 3 * dx, y - 4.5 * dx - 3 * dy], [x + 4.5 * dy - 3 * dx, y + 4.5 * dx - 3 * dy]]
})

export const STICKS: Pt[] = [[109, 85], [276, 152]]
export const FACE = [['Y', 331, 58], ['A', 331, 116], ['X', 302, 87], ['B', 360, 87]] as const
// x1, y1, x2, y2, texto, botão
export const SMALL = [[154, 41, 168, 57, '−', 'View'], [274, 41, 288, 57, '+', 'Menu'], [209, 73, 233, 87, '▢', 'Capture'],
  [209, 180, 233, 192, 'M', 'M'], [128, 298, 166, 314, 'L4', 'L4'], [276, 298, 314, 314, 'R4', 'R4']] as const
export const HOME: Pt = [221, 45]
export const PLATE: Pt[][] = [[[176, 12], [198, 36], [244, 36], [266, 12]], [[140, 66], [186, 80], [256, 80], [302, 66]],
  [[186, 80], [166, 112]], [[256, 80], [276, 112]]]
export const PLAYER_LEDS: Pt[] = [0, 1, 2, 3].map((i) => [221, 114 + 11 * i])
export const PLAYER_COLORS = ['#7ed321', '#f8e71c', '#f5a623', '#e0262b']

// barras de luz dos grips: no Cyclone 2 preto só elas acendem
const GRIP: Pt[] = [[44, 122], [37, 145], [44, 172], [70, 190], [96, 202]]
export const GRIPS = { lower_left: GRIP, lower_right: mirror(GRIP) }

// callouts da tela inicial: texto, lado, y do rótulo, ponto no controle
export const CALLOUTS = [
  ['LT / LB', 'l', 4, [96, 12]], ['Analógico esquerdo', 'l', 84, [80, 85]], ['D-pad', 'l', 160, [130, 157]],
  ['Luzes', 'l', 236, [44, 172]], ['RT / RB', 'r', 4, [346, 12]], ['Botões ABXY', 'r', 84, [374, 87]],
  ['Analógico direito', 'r', 160, [303, 152]], ['Traseiros L4 / R4', 'r', 300, [314, 306]],
] as const
