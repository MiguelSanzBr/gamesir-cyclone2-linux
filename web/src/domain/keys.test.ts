import { BUTTONS, NONE, PADDLES, TRIGGERS, code, name } from './keys'

// valores tirados do dicionário CODES do keys.py
describe('keys', () => {
  it('nomes dos códigos do controle, teclado, mouse e especiais', () => {
    expect(name(1)).toBe('Up')
    expect(name(28)).toBe('RS_Right')
    expect(name(50)).toBe('KB_ESC')
    expect(name(119)).toBe('KB_SPACE')
    expect(name(154)).toBe('KB_VOLDOWN')
    expect(name(200)).toBe('MOUSE_LEFT')
    expect(name(231)).toBe('Shift')
    expect(name(NONE)).toBe('None')
  })

  it('código desconhecido vira 0x.. e volta igual (keys.name/keys.code)', () => {
    expect(name(0x30)).toBe('0x30')
    expect(code('0x30')).toBe(0x30)
    expect(name(0)).toBe('0x00')
  })

  it('code é o inverso de name', () => {
    for (let c = 0; c < 256; c++) expect(code(name(c))).toBe(c)
  })

  it('nome inválido estoura', () => {
    expect(() => code('Banana')).toThrow('unknown key')
  })

  it('ordem dos botões no registro', () => {
    expect(BUTTONS).toHaveLength(16)
    expect(BUTTONS[8]).toBe('A')
    expect(PADDLES).toEqual(['L4', 'R4'])
    expect(TRIGGERS).toEqual(['LT', 'RT'])
  })
})
