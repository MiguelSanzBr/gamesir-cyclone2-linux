// Port do src/cyclone2/keys.py: códigos q o firmware usa em remap, macro e ativação do gyro.

const PAD = ['Up', 'Down', 'Left', 'Right', 'LB', 'RB', 'LS', 'RS', 'A', 'B', 'X', 'Y', 'Home', 'View', 'Menu',
  'Capture', 'L4', 'R4', 'LT', 'RT', 'LS_Up', 'LS_Down', 'LS_Left', 'LS_Right', 'RS_Up', 'RS_Down', 'RS_Left', 'RS_Right']
const KEYBOARD = ['ESC', 'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12', '`', '1', '2', '3',
  '4', '5', '6', '7', '8', '9', '0', '-', '=', 'BACKSPACE', 'TAB', 'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '[',
  ']', '\\', 'CAPSLOCK', 'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', ';', "'", 'ENTER', 'LSHIFT', 'Z', 'X', 'C', 'V',
  'B', 'N', 'M', ',', '.', '/', 'RSHIFT', 'LCTRL', 'WIN', 'LALT', 'SPACE', 'RALT', 'RCTRL', 'INSERT', 'HOME', 'PGUP',
  'DELETE', 'END', 'PGDN', 'UP', 'DOWN', 'LEFT', 'RIGHT', 'NUMLOCK', 'NUM/', 'NUM*', 'NUM-', 'NUM+', 'NUM.',
  'NUMENTER', 'NUM0', 'NUM1', 'NUM2', 'NUM3', 'NUM4', 'NUM5', 'NUM6', 'NUM7', 'NUM8', 'NUM9', 'PLAY', 'STOP', 'NEXT',
  'PREV', 'VOLUP', 'VOLDOWN']
const MOUSE = ['MOUSE_LEFT', 'MOUSE_MIDDLE', 'MOUSE_RIGHT', 'MOUSE_5', 'MOUSE_4', 'WHEEL_UP', 'WHEEL_DOWN']

const CODES = new Map<number, string>([
  ...PAD.map((n, i): [number, string] => [i + 1, n]),
  ...KEYBOARD.map((n, i): [number, string] => [i + 50, 'KB_' + n]),
  ...MOUSE.map((n, i): [number, string] => [i + 200, n]),
  [230, 'Mute'],
  [231, 'Shift'],
  [255, 'None'],
])
const NAMES = new Map([...CODES].map(([c, n]) => [n, c]))
export const NONE = 255

// ordem dos botões no registro do perfil (lista "ja" do app), depois paddles e gatilhos
export const BUTTONS = ['Up', 'Down', 'Left', 'Right', 'LB', 'RB', 'LS', 'RS', 'A', 'B', 'X', 'Y', 'Home', 'View', 'Menu',
  'Capture']
export const PADDLES = ['L4', 'R4']
export const TRIGGERS = ['LT', 'RT'] as const

/** Código desconhecido vira "0x.." pra sobreviver ao decode/encode sem perder nada. */
export const name = (code: number): string => CODES.get(code) ?? '0x' + code.toString(16).padStart(2, '0')

export function code(n: string): number {
  const c = NAMES.get(n)
  if (c !== undefined) return c
  if (n.startsWith('0x')) return parseInt(n, 16)
  throw new Error(`unknown key ${n}`)
}
