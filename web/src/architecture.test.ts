// @vitest-environment node
import { ESLint } from 'eslint'

// regra de dependência da arquitetura hexagonal, aplicada pelo ESLint (q roda no CI)
const eslint = new ESLint({ cwd: process.cwd() })
const errors = async (file: string, code: string) => {
  const [r] = await eslint.lintText(code, { filePath: file })
  return r!.messages.map((m) => m.ruleId)
}
const IMPORT = '@typescript-eslint/no-restricted-imports'
const GLOBAL = 'no-restricted-globals'

describe('regra de dependência entre camadas', () => {
  it.each([
    ["import { useState } from 'react'"],
    ["import { DemoTransport } from '../adapters/demo/demo'"],
    ["import { ConfigSession } from '../application/session'"],
    ["import type { ControllerChannel } from '../application/ports'"],
  ])('domain não importa React, adapters nem application: %s', async (code) => {
    expect(await errors('src/domain/x.ts', `${code}\nexport {}`)).toContain(IMPORT)
  })

  it.each([['navigator.hid'], ['document.title'], ['window.alert']])('domain e application não tocam no DOM: %s', async (code) => {
    expect(await errors('src/domain/x.ts', `export const x = () => ${code}`)).toContain(GLOBAL)
    expect(await errors('src/application/x.ts', `export const x = () => ${code}`)).toContain(GLOBAL)
  })

  it.each([["import { createElement } from 'react'"], ["import { WebHidTransport } from '../adapters/webhid/webhid'"]])(
    'application não importa adapters nem React: %s', async (code) => {
      expect(await errors('src/application/x.ts', `${code}\nexport {}`)).toContain(IMPORT)
    })

  it('application pode usar o domain', async () => {
    expect(await errors('src/application/x.ts', "import { command } from '../domain/frames'\nexport const x = command")).toEqual([])
  })

  it.each([
    ["import { decode } from '../../domain/profile'"],
    ["import { DemoTransport } from '../demo/demo'"],
    ["import { WebHidTransport } from '../webhid/webhid'"],
    ["import { ConfigSession } from '../../application/session'"],
  ])('a UI só chama casos de uso: %s', async (code) => {
    expect(await errors('src/adapters/ui/x.ts', `${code}\nexport {}`)).toContain(IMPORT)
  })

  it('a UI pode importar tipos do domain e os casos de uso', async () => {
    const code = "import type { ProfileDoc } from '../../domain/profile'\nimport { connect } from '../../application/usecases'\nexport const x = (d: ProfileDoc) => [d, connect]"
    expect(await errors('src/adapters/ui/x.ts', code)).toEqual([])
  })
})
