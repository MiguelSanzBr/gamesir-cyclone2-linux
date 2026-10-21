import { expect, test, type Page } from '@playwright/test'

const tile = (page: Page, name: string) => page.getByRole('group', { name: 'Seções' }).getByRole('button', { name, exact: true }).click()

test('modo demo: lê o perfil, muda o hair trigger, confirma e vê gravado', async ({ page }) => {
  await page.goto('./')
  await page.getByRole('button', { name: 'Entrar no modo demo' }).click()
  await expect(page.getByText(/MODO DEMO/)).toBeVisible()

  await expect(page.getByRole('region', { name: 'Controle' }).getByText('Perfil ativo no controle: 1')).toBeVisible()
  await expect(page.getByRole('contentinfo').getByText('firmware 3.5.6')).toBeVisible()
  await expect(page.getByRole('radio', { name: 'Perfil 1 (ativo)' })).toBeChecked()
  const hair = page.getByLabel('RT: hair trigger', { exact: true })
  await expect(hair).toBeChecked()

  await tile(page, 'Perfil')
  await page.getByLabel('Nome do perfil').fill('Corrida')
  await tile(page, 'Gatilhos')
  await hair.uncheck()
  await expect(page.getByRole('region', { name: 'Alterações pendentes' })).toContainText('2 alterações')

  await page.getByRole('button', { name: 'Revisar e gravar' }).click()
  const dialog = page.getByRole('dialog', { name: 'Confirmar gravação' })
  await expect(dialog.getByText('Nome do perfil: (sem nome) → Corrida')).toBeVisible()
  await expect(dialog.getByText('RT: hair trigger: adaptativo, 10% a 90% → desligado')).toBeVisible()
  await dialog.getByRole('button', { name: 'Gravar no controle' }).click()

  await expect(page.getByRole('status')).toHaveText(/Gravado e conferido no controle/)
  await expect(dialog).toBeHidden()

  // lê do controle simulado de novo: o q aparece agora veio da memória do controle, não do formulário
  await tile(page, 'Perfil')
  await page.getByRole('button', { name: 'Ler do controle de novo' }).click()
  await expect(page.getByRole('status')).toHaveText('Perfil 1 lido do controle.')
  await expect(page.getByLabel('Nome do perfil')).toHaveValue('Corrida')
  await tile(page, 'Gatilhos')
  await expect(hair).not.toBeChecked()
})

// fica acesa enquanto o botão do mouse tá segurado, igual botão físico
for (const motion of ['no-preference', 'reduce'] as const) {
  test(`demo: apertar uma parte do desenho acende ela (movimento ${motion})`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: motion })
    await page.goto('./')
    await page.getByRole('button', { name: 'Entrar no modo demo' }).click()
    await expect(page.getByText('Aperte os botões do controle: eles acendem aqui.', { exact: false })).toBeVisible()
    const a = page.locator('[data-part="A"]')
    await a.hover()
    await page.mouse.down()
    await expect(a).toHaveClass(/\blit\b/)
    const transform = () => a.evaluate((e) => getComputedStyle(e).transform)
    // movimento reduzido: só a cor muda, sem afundar
    if (motion === 'reduce') expect(await transform()).toBe('none')
    else await expect.poll(transform).not.toBe('none')
    await page.mouse.up()
    await expect(a).not.toHaveClass(/\blit\b/)
  })
}

test('cabe em 375 px sem rolagem horizontal, em todo painel', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 })
  const width = () => page.evaluate(() => document.documentElement.scrollWidth)
  await page.goto('./')
  expect(await width()).toBeLessThanOrEqual(375)
  await page.getByRole('button', { name: 'Entrar no modo demo' }).click()
  await expect(page.getByRole('heading', { name: 'Cyclone 2' })).toBeVisible()
  for (const name of ['Gatilhos', 'Luzes', 'Vibração', 'Perfil']) {
    await tile(page, name)
    await expect(page.getByRole('region', { name })).toBeVisible()
    expect(await width()).toBeLessThanOrEqual(375)
  }
})

// média de r, g, b do fundo: escuro fica bem abaixo de 80, claro bem acima
const light = (page: Page) => page.evaluate(() => {
  const [r, g, b] = getComputedStyle(document.body).backgroundColor.match(/\d+/g)!.map(Number)
  return (r! + g! + b!) / 3 > 80
})

// cor da barra do navegador: o primeiro theme-color cujo media bate, e ela tem q ser o fundo da página
const bar = (page: Page) => page.evaluate(() => {
  const meta = [...document.querySelectorAll<HTMLMetaElement>('meta[name="theme-color"]')].find((m) => matchMedia(m.media || 'all').matches)!
  return [meta.content, getComputedStyle(document.body).backgroundColor]
})
const hex = (rgb: string) => '#' + rgb.match(/\d+/g)!.map((n) => Number(n).toString(16).padStart(2, '0')).join('')

for (const scheme of ['dark', 'light'] as const) {
  test(`tema ${scheme}: segue o sistema, o botão troca e a escolha fica salva`, async ({ page }) => {
    await page.emulateMedia({ colorScheme: scheme })
    await page.goto('./')
    await expect.poll(() => light(page)).toBe(scheme === 'light')
    const [meta, bg] = await bar(page)
    expect(meta).toBe(hex(bg!))
    await page.getByRole('button', { name: scheme === 'dark' ? 'Usar tema claro' : 'Usar tema escuro' }).click()
    await expect.poll(() => light(page)).toBe(scheme === 'dark')
    await page.reload()
    await expect.poll(() => light(page)).toBe(scheme === 'dark')
    const [forced, forcedBg] = await bar(page)
    expect(forced).toBe(hex(forcedBg!))
    expect(forced).not.toBe(meta)
    await page.getByRole('button', { name: 'Entrar no modo demo' }).click()
    await expect(page.getByRole('img', { name: 'Desenho do GameSir Cyclone 2' })).toBeVisible()
  })
}
