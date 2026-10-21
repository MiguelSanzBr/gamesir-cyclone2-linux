import { useState } from 'react'
import { Icon } from './icons'

// sem escolha salva segue o sistema; o index.html aplica a salva antes do React pra não piscar
const current = () => document.documentElement.dataset.theme ?? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')

export function ThemeToggle() {
  const [dark, setDark] = useState(() => current() === 'dark')
  function toggle() {
    const next = dark ? 'light' : 'dark'
    document.documentElement.dataset.theme = next
    // igual o index.html: a barra do navegador fica na cor do tema escolhido
    for (const m of document.querySelectorAll<HTMLMetaElement>('meta[name="theme-color"]')) m.setAttribute('media', m.dataset.theme === next ? 'all' : 'not all')
    localStorage.setItem('theme', next)
    setDark(!dark)
  }
  return (
    <button type="button" className="icon-btn" aria-label={dark ? 'Usar tema claro' : 'Usar tema escuro'} onClick={toggle}>
      <Icon name={dark ? 'sun' : 'moon'} />
    </button>
  )
}
