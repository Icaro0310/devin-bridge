# devin-bridge

> **Projeto comunitário não-oficial.** Sem afiliação, endosso ou
> patrocínio da Cognition AI. "Devin" é marca da Cognition AI.

**[English](README.md)** · Português (BR)

Uma ponte com política de permissões que dirige o `devin.exe acp` por
fora: cria/retoma sessões Devin isoladas por projeto, envia prompts,
faz stream dos resultados — com um `policy.json` decidindo o que a
sessão pode fazer.

## O problema

Sessões do Devin Desktop não são programáveis. `devin -p` exige
`devin auth login` interativo, `devin list` é um TUI, e os snippets
da comunidade que dirigem `devin.exe acp` diretamente **auto-aprovam
todo pedido de permissão** — ok para demo, perigoso para rodar sem
supervisão num repo real.

## Prior art

Este projeto adapta o cliente provado do `personal-agent-system`
(`gateways/src/devin-acp.js`, ~600 linhas: JSON-RPC NDJSON sobre stdio,
ciclo de vida de sessão, handlers de terminal/fs/permissão,
notificações de modelo/custo) e o dispatcher
(`scripts/devin-repo-task.js`, mapeamento repo→sessionId). Não reinventa
o protocolo — porta-o e adiciona o portão de permissões que faltava.
Ver [docs/SPEC.md](docs/SPEC.md) (inglês).

## O que o torna Devin-nativo

- **Lado a lado:** clientes ACP genéricos auto-aprovam tudo ou delegam
  à config do agente; este passa `terminal/*`, `fs/*` e
  `session/request_permission` por um `policy.json` por repo
  (allow/deny/ask, deny vence, fail-closed por padrão).
- **Sem-Devin:** sem o Devin não faz sentido — o transporte é
  `devin.exe acp`, a auth é o `windsurf_api_key` do IDE em
  `credentials.toml` (sem login PKCE), e as sessões aparecem agrupadas
  por repo no Devin Desktop.
- **Uma frase:** *dirigir o Devin por fora, com cinto de segurança.*

## Instalação

```bash
git clone https://github.com/Icaro0310/devin-bridge.git
cd devin-bridge
npm install -g .        # ou: npm link
```

Requer Node ≥ 20 e Devin Desktop autenticado (lê o session token de
`%APPDATA%\devin\credentials.toml`; o token nunca é logado nem
persistido).

## Uso

```bash
# opcional: escrever a política do projeto
devin-bridge policy --init          # cria ./policy.json (ver policy.example.json)

# criar sessão isolada para um repo (registrada em .sessions.json)
devin-bridge new C:\caminho\para\repo

# despachar um prompt — retoma a sessão mapeada automaticamente
devin-bridge prompt C:\caminho\para\repo "rode os testes e corrija as falhas"
devin-bridge prompt C:\caminho\para\repo --file docs\KICKOFF-M1.md --yes

# inspecionar
devin-bridge sessions
devin-bridge policy --check terminal "rm -rf /"
```

Decisões `ask` da política perguntam ao operador num TTY; execuções
não-interativas permanecem fail-closed a menos que `--yes` seja passado.

## Limitações

- Usa o modo `acp` **não-documentado** e a auth `_meta.api_key` do
  `devin.exe` embutido; ambos podem mudar sem aviso (testado contra
  Devin CLI 3000.10.x).
- Windows-first (paths, semântica de spawn); a CI Linux cobre os testes
  mas sessões reais visam a instalação Desktop no Windows.
- `session/load` não toma sessão aberta noutro processo — falha com
  `session_locked` e o dispatcher cai para `session/new`.
- Não expõe MCP servers do lado do agente (`mcpServers: []` é enviado).

## Desenvolvimento

```bash
npm test        # node --test — runner da stdlib, zero deps
```

Os testes usam um agente ACP falso e roteirizado
(`tests/fixtures/fake-acp.mjs`) sobre stdio real — sem `devin.exe`.

## Licença

MIT — ver [LICENSE](LICENSE).
