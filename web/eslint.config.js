import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import tseslint from 'typescript-eslint'

const IMPORT = '@typescript-eslint/no-restricted-imports'
const react = { group: ['react', 'react-dom', 'react/*', 'react-dom/*'], message: 'React fica só no adapter de UI.' }
const adapters = { group: ['**/adapters/**', '../adapters', '../../adapters'], message: 'A camada de dentro não conhece adapter.' }
const dom = ['navigator', 'document', 'window'].map((name) => ({ name, message: 'DOM e navigator ficam nos adapters.' }))
// testes podem cruzar camadas pra montar fixture; a regra vale pro código do app
const tests = ['**/*.test.ts', '**/*.test.tsx']

export default tseslint.config(
  { ignores: ['dist', 'coverage', 'playwright-report', 'test-results'] },
  {
    files: ['**/*.{ts,tsx,js}'],
    extends: [js.configs.recommended, ...tseslint.configs.strict],
    languageOptions: { globals: { ...globals.browser, ...globals.node } },
    plugins: { 'react-hooks': reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      // parse de bytes com noUncheckedIndexedAccess: o tamanho do report já é conferido antes,
      // e trocar o ! por ?? criaria branch morto só pra agradar o tipo
      '@typescript-eslint/no-non-null-assertion': 'off',
    },
  },
  // regra de dependência: domain <- application <- adapters
  {
    files: ['src/domain/**'],
    ignores: tests,
    rules: {
      [IMPORT]: ['error', { patterns: [react, adapters, { group: ['**/application/**', '../application'], message: 'O domain não depende da application.' }] }],
      'no-restricted-globals': ['error', ...dom],
    },
  },
  {
    files: ['src/application/**'],
    ignores: tests,
    rules: {
      [IMPORT]: ['error', { patterns: [react, adapters] }],
      'no-restricted-globals': ['error', ...dom],
    },
  },
  {
    // a UI é adapter de entrada: chama casos de uso, do domain só usa tipos
    files: ['src/adapters/ui/**'],
    ignores: tests,
    rules: {
      [IMPORT]: ['error', {
        patterns: [
          { group: ['**/domain/**'], allowTypeImports: true, message: 'A UI só usa tipos do domain; regra de negócio vem dos casos de uso.' },
          { group: ['**/application/*', '!**/application/usecases'], allowTypeImports: true, message: 'A UI chama os casos de uso (application/usecases).' },
          { group: ['../demo/**', '../webhid/**', '../demo', '../webhid'], message: 'Quem liga os adapters é o main.tsx.' },
        ],
      }],
    },
  },
)
