// só o q a versão web configura de verdade; botões, analógicos e gyro ficam de fora até ter interface
export const TITLES = { triggers: 'Gatilhos', lights: 'Luzes', rumble: 'Vibração', profile: 'Perfil' } as const
export type Section = keyof typeof TITLES
export const SECTIONS = Object.keys(TITLES) as Section[]
