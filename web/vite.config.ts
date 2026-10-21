/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  // GitHub Pages serve o projeto em /gamesir-cyclone2-linux/
  base: '/gamesir-cyclone2-linux/',
  plugins: [react()],
  server: { port: 5175, strictPort: true },
  preview: { port: 4175, strictPort: true },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        // bootstrap: só monta o <App/> no #root, quem testa isso é o e2e
        'src/main.tsx',
        // ports: só declara interfaces, não sobra nenhuma linha de JS pra medir
        'src/application/ports.ts',
        // setup e fixtures de teste não são código do app
        'src/test/**',
        'src/**/*.test.{ts,tsx}',
      ],
      thresholds: { statements: 100, branches: 100, functions: 100, lines: 100 },
    },
  },
})
