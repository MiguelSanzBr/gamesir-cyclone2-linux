# GameSir Cyclone 2 no navegador

[English](README.en.md)

Configurador do controle GameSir Cyclone 2 rodando direto no navegador, via WebHID, em React + TypeScript.

O app oficial (GameSir Connect) só existe pra Windows. Pra usar o controle no Linux eu recuperei o protocolo e fiz o
[gamesir-cyclone2-linux](https://github.com/MiguelSanzBr/gamesir-cyclone2-linux), em Python. Este projeto leva o
mesmo protocolo pro navegador: abre a página no Chrome ou no Edge, conecta o controle e configura. Sem instalar nada
além da regra udev no Linux.

Tem modo demo com um controle simulado em memória, então dá pra testar tudo sem o hardware.

## O q dá pra fazer

- Ver aparelho, modo (cabo ou 2.4G), firmware, dongle, perfil ativo e bateria.
- Ler os 4 perfis e trocar o perfil ativo no controle.
- Nome do perfil.
- Gatilhos LT e RT: zona morta (início e fim, com a curva refeita igual o app faz) e hair trigger (liga/desliga,
  adaptativo ou fixo, faixa).
- Luzes: animação ativa, presets do app, brilho, velocidade, número de quadros e a cor de cada LED em cada quadro.
- Teste de vibração.
- Entrada ao vivo: apertar botão, mexer analógico ou puxar gatilho no controle acende a parte no desenho (o
  analógico anda, o gatilho enche pela pressão). No demo, clicar no desenho aperta o botão simulado.

A tela segue o app Linux: o desenho do controle (port do contorno do `gui/geometry.py`) com os grips na cor das
luzes, callouts q levam pra seção, abas de perfil em cima, um bloco por seção e a barra de alterações pendentes
embaixo. Tem tema escuro e claro, segue o sistema e o botão do topo troca (a barra do navegador no celular vai
junto). Com alteração pendente, fechar a aba faz o navegador perguntar antes, pra não perder a edição.

## Como funciona

O canal de config é a interface HID vendor do controle (usage page `0xFFF0`, VID `0x3537`, PIDs `0x101D`, `0x102A`,
`0x1053`, `0x100B`):

- host pro controle: output report `0x0F`, 64 bytes `0F cmd args...`
- controle pro host: input report `0x10` com a resposta, e `0x12` com o estado do gamepad (botões, analógicos, bateria)
- dados de perfil: `0F 03|04 perfil offset_hi offset_lo tamanho dados...`, no máximo 58 bytes por pacote

Cada encoder e decoder é port direto do Python (`protocol.py`, `profile.py`, `light.py`, `keys.py`, `device.py`) e os
testes usam bytes gerados rodando o código Python, com um comentário dizendo qual função cada fixture espelha
(`src/test/fixtures.ts`).

Segurança na gravação, igual o projeto Linux:

1. Lê primeiro: ao conectar, lê o perfil ativo e o registro de luzes.
2. Editar não grava nada. As edições ficam staged e a tela mostra quantas estão pendentes.
3. "Revisar e gravar" abre a confirmação com a lista do q muda (de → pra) e o intervalo exato de bytes de cada
   registro.
4. Só depois do "Gravar no controle" o app manda os pacotes, e só do intervalo q mudou (`changed_span`, o
   `bytesDiff` do app).
5. Lê o registro inteiro de volta e compara. Se não bater, dá erro e as edições continuam pendentes.

Os pedidos são reenviados a cada 200 ms até 10 vezes quando o controle fica calado ou responde "ocupado", a resposta
precisa ser do tipo certo (e na leitura, do mesmo perfil e offset), e o heartbeat sai a cada 1 s enquanto tá
conectado, igual o app oficial.

## Arquitetura

Hexagonal, com o domínio na linguagem do controle:

```
                 adapters de entrada                 adapters de saída
              ┌─────────────────────┐        ┌───────────────────────────────┐
              │  ui/ (React)        │        │  webhid/  (navigator.hid)     │
              │  só chama casos de  │        │  demo/    (controle simulado) │
              │  uso                │        └──────────────┬────────────────┘
              └──────────┬──────────┘                       │ implementa
                         ▼                                  ▼
              ┌──────────────────────────────────────────────────────────────┐
              │ application/  casos de uso: Connect, ReadProfile,            │
              │ PlanChanges, ApplyChanges, SwitchActiveProfile, KeepAlive    │
              │ ConfigSession (reenvio, match, gravação conferida)           │
              │ porta: ControllerChannel                                     │
              └──────────────────────────────┬───────────────────────────────┘
                                             ▼
              ┌──────────────────────────────────────────────────────────────┐
              │ domain/  Profile (id 1-4), Lighting, ChangeSet (intervalo de │
              │ bytes), HairTrigger, TriggerRange, ControllerInfo, frames,   │
              │ encode/decode dos registros. Funções puras, zero I/O.        │
              └──────────────────────────────────────────────────────────────┘
```

Pq assim: o protocolo e as regras de gravação são a parte q não pode errar, então ficam em código puro, testado com
os bytes do Python, sem React nem navegador no meio. O WebHID e o modo demo são só dois jeitos de mandar e receber
report, e os dois passam pela mesma `ConfigSession`, então o modo demo exercita o mesmo caminho do hardware. O
`main.tsx` é a raiz de composição q liga os adapters na UI.

A regra de dependência é aplicada pelo ESLint (`@typescript-eslint/no-restricted-imports` e `no-restricted-globals`
por pasta): domain não importa application, adapters, React nem toca em `navigator`/`document`/`window`;
application não importa adapters nem React; a UI só importa os casos de uso (`application/usecases`), do domain só
tipos. O `src/architecture.test.ts` prova q a regra pega cada violação, e o `npm run lint` no CI barra o build.

## Testes

| Garantia | Teste |
| --- | --- |
| Frames de comando, leitura e escrita byte a byte iguais ao Python | `src/domain/frames.test.ts` |
| Escrita com no máximo 58 bytes de dado e dentro do registro | `src/domain/values.test.ts` (frame de escrita) |
| Decode/encode do perfil de 680 bytes igual ao Python, encode só do q mudou | `src/domain/profile.test.ts` |
| Zona morta refaz a curva igual o `Editor._deadzone` | `src/domain/profile.test.ts` |
| Registro de luzes de 635 bytes e presets iguais ao Python | `src/domain/lighting.test.ts` |
| Faixas válidas (perfil 1-4, zona morta, hair trigger, brilho, velocidade, quadros, cor) | `src/domain/values.test.ts` |
| Edição não muda o original e vira um ChangeSet com o intervalo certo | `src/domain/aggregates.test.ts` |
| Lista legível do q muda | `src/domain/changes.test.ts` |
| Reenvio no silêncio e no "ocupado", desiste depois de 10 envios | `src/application/session.test.ts` |
| Resposta de outro comando, perfil ou offset é ignorada | `src/application/session.test.ts` |
| Grava só o intervalo e confere lendo de volta, falha se o controle não guardar | `src/application/session.test.ts` |
| Heartbeat a cada 1 s e para ao fechar | `src/application/session.test.ts`, `usecases.test.ts` |
| Gravar sem confirmação é recusado | `src/application/usecases.test.ts` |
| Connect lê info, perfil ativo e luzes; fecha o canal se falhar | `src/application/usecases.test.ts` |
| WebHID: filtros VID/PID/usage page, `sendReport(0x0F, 63 bytes)`, input report com o id no byte 0 | `src/adapters/webhid/webhid.test.ts` |
| Controle simulado responde igual o fake do Python | `src/adapters/demo/demo.test.ts` |
| Navegador sem WebHID: aviso e modo demo | `src/adapters/ui/App.test.tsx` |
| Nada grava antes de confirmar; cancelar/Esc não grava; confirmar grava e aplica | `src/adapters/ui/App.test.tsx` |
| Regra de dependência entre camadas | `src/architecture.test.ts` |
| Fluxo completo no Chromium: demo, ler, editar, confirmar, ler de volta; 375 px sem rolagem lateral | `e2e/demo.spec.ts` |

### Cobertura

Vitest com v8, threshold de 100% em statements, branches, functions e lines sobre `src/`. Abaixo disso o
`npm run coverage` sai com erro e o CI falha. Último resultado: 148 testes, 100% em tudo (722 statements, 278
branches, 254 functions, 567 lines).

Fora da medição, cada um com comentário no `vite.config.ts`:

- `src/main.tsx`: bootstrap, só monta o `<App/>` e liga os adapters; quem cobre é o E2E.
- `src/application/ports.ts`: só declara a interface `ControllerChannel`, não sobra JS pra medir.
- `src/test/**` e os `*.test.ts(x)`: código de teste.

### Mutação manual

Quebrei de propósito as proteções principais, rodei a suíte e restaurei:

| Mutação | Resultado |
| --- | --- |
| `applyChanges` grava sem confirmação | 1 teste falhou |
| botão "Revisar e gravar" grava direto | 4 testes falharam |
| WebHID manda com report id `0x10` em vez de `0x0F` | 1 teste falhou |
| report id de saída `0x0E` no domain | 7 testes falharam |
| aceita qualquer resposta, sem conferir o comando | 2 testes falharam |
| leitura sem conferir perfil e offset do pedaço | 1 teste falhou |

## Limites conhecidos

- Só Chrome e Edge no desktop (WebHID). Firefox e Safari ficam só no modo demo.
- O controle precisa estar num modo q aceita config (PIDs acima). No Linux o Chrome abre o controle pelo hidraw,
  então precisa da regra `udev/70-gamesir-cyclone2.rules` do projeto Linux, e depois reconectar o controle.
- Não testei em hardware real. O transporte WebHID é coberto com um `navigator.hid` falso e o resto com o controle
  simulado; o protocolo em si foi validado no projeto Python com um Cyclone 2 preto, firmware 3.5.6, cabo `3537:1053`.
- O hair trigger aceita início e fim entre 0 e 100 sem exigir início < fim, pq nem o Python nem o app oficial (pelo
  q recuperei) exigem. Não sei o q o firmware faz com início > fim.
- A leitura do report `0x12` (botões, analógicos, gatilhos) espelha o `protocol.state` do Python, com fixtures
  geradas por ele, mas não vi o desenho acendendo com um controle de verdade; só no demo.
- O heartbeat sai enquanto tá conectado; o app oficial manda só com a janela em foco.
- Trocar o perfil ativo é imediato, sem a confirmação: não grava memória, é o mesmo q o botão do controle faz.
- Não segue a troca de perfil feita no próprio controle (o GUI Python faz polling); use "Ler do controle de novo".

Não portado (o encode/decode do registro inteiro está portado e testado, falta interface):

- remap de botões, macros, analógicos, gyro, motores e opções (Shift, trava diagonal do d-pad, troca ABXY, report rate)
- camada Shift (perfil 5)
- reset pros padrões do app
- backup e restore
- prévia de LED (comando 13), LED do perfil, standby, raise to wake e audio reactive

## Como rodar

```bash
npm ci
npm run dev          # http://localhost:5175/gamesir-cyclone2-linux/
npm run lint
npm run typecheck
npm run coverage     # testes + gate de 100%
npm run e2e          # Playwright (build + preview na porta 4175)
npm run build
```

Com Docker (builda e serve com nginx em http://localhost:8089/gamesir-cyclone2-linux/):

```bash
docker compose up --build
```

O deploy no GitHub Pages fica em `.github/workflows/pages.yml` e o CI em `.github/workflows/ci.yml`.

## Licença

MIT, veja [LICENSE](LICENSE).
