import '@testing-library/jest-dom/vitest'

// jsdom não tem matchMedia; o tema segue o sistema por ele (claro por padrão aqui)
if (typeof window !== 'undefined') window.matchMedia = (query: string) => ({ matches: false, media: query }) as MediaQueryList
