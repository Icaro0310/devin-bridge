<div align="center">

<img src="assets/banner.svg" alt="devin-bridge" width="100%"/>

</div>

# devin-bridge

> **Projeto comunitário não-oficial.** Sem afiliação, endosso ou
> patrocínio da Cognition AI. "Devin" é marca da Cognition AI.

**[English](README.md)** · Português (BR)

Uma ponte com política de permissões que dirige `devin acp` no Windows e
Linux: cria/retoma sessões Devin isoladas por projeto, envia prompts e faz
stream dos resultados. Um `policy.json` controla o que a sessão pode fazer.

## O problema

Sessões do Devin Desktop não são programáveis. `devin -p` exige
`devin auth login` interativo, `devin list` é um TUI, e os snippets
da comunidade que dirigem `devin.exe acp` diretamente **auto-aprovam
todo pedido de permissão** — ok para demo, perigoso para rodar sem
supervisão num repo real.

## Prior art

A ferramenta implementa ACP via JSON-RPC NDJSON sobre stdio, gere o ciclo
de vida das sessões e aplica decisões de permissão a pedidos de terminal,
filesystem e acesso. Não reinventa o protocolo; acrescenta o gate de política.
Ver [docs/SPEC.md](docs/SPEC.md) (inglês).

## O que o torna Devin-nativo

- **Lado a lado:** clientes ACP genéricos auto-aprovam tudo ou delegam
  à config do agente; este passa `terminal/*`, `fs/*` e
  `session/request_permission` por um `policy.json` por repo
  (allow/deny/ask, deny vence, fail-closed por padrão).
- **Sem-Devin:** sem o Devin não faz sentido — o transporte é `devin acp`,
  autenticado pelo `windsurf_api_key` do IDE em `credentials.toml` (sem login
  PKCE), e as sessões aparecem agrupadas por repo no Devin Desktop.
- **Uma frase:** *dirigir o Devin por fora, com cinto de segurança.*

## Instalação

Requer Node.js ≥ 20, Git e Devin CLI/Desktop autenticado.

**Windows (PowerShell):**

```powershell
git clone https://github.com/Icaro0310/devin-bridge.git
cd devin-bridge
npm install -g .
```

**Linux:**

```bash
git clone https://github.com/Icaro0310/devin-bridge.git
cd devin-bridge
npm install -g .
```

O bridge lê `windsurf_api_key` de `%APPDATA%\\devin\\credentials.toml` no
Windows e `$XDG_DATA_HOME/devin/credentials.toml` no Linux (por omissão
`~/.local/share/devin/credentials.toml`). Usa `DEVIN_CREDENTIALS_PATH` para
sobrepor; o executável é procurado no `PATH` ou em `DEVIN_CLI_PATH`. O token
nunca é registado nem persistido.

## Uso

Os comandos `new` e `prompt` guardam o mapeamento repo→sessão em
`.sessions.json`. Mantém esse ficheiro local e fora de commits: contém IDs de
sessão e caminhos da máquina.

**Windows (PowerShell):**

```powershell
devin-bridge policy --init
devin-bridge new "C:\src\meu-repo"
devin-bridge prompt "C:\src\meu-repo" "rode os testes e corrija as falhas"
devin-bridge prompt "C:\src\meu-repo" --file docs\KICKOFF.md
devin-bridge sessions
devin-bridge policy --check terminal "rm -rf /"
```

**Linux:**

```bash
devin-bridge policy --init
devin-bridge new "$HOME/src/meu-repo"
devin-bridge prompt "$HOME/src/meu-repo" "rode os testes e corrija as falhas"
devin-bridge prompt "$HOME/src/meu-repo" --file docs/KICKOFF.md
devin-bridge sessions
devin-bridge policy --check terminal "rm -rf /"
```

Decisões `ask` perguntam ao operador num TTY; em execuções não-interativas,
ficam negadas por omissão a menos que `--yes` seja passado.

## Funciona só com o Devin (modo Devin-only)

O devin-bridge *é* o caminho Devin-only: fala diretamente com `devin acp`
usando o `credentials.toml` que o Devin CLI já guarda — sem segundo runtime,
sem broker de mensagens, sem API key extra. Os requisitos são só Node.js >= 20
e um Devin CLI autenticado (`devin` no PATH ou `DEVIN_CLI_PATH`). A política
de permissões é fail-closed por omissão: tudo o que não for permitido
explicitamente é negado, e as credenciais nunca são logadas nem persistidas.

## Suporte de plataformas

Windows e Linux são suportados e cobertos pela CI. O CLI `devin` precisa estar
no `PATH` ou ser indicado em `DEVIN_CLI_PATH`. Credenciais usam o path padrão
por SO ou `DEVIN_CREDENTIALS_PATH`.

## Limitações

- Usa o modo `acp` **não-documentado** e a auth `_meta.api_key` do Devin CLI;
  ambos podem mudar sem aviso (testado contra Devin CLI 3000.10.x).
- `session/load` não toma sessão aberta noutro processo — falha com
  `session_locked` e o dispatcher cai para `session/new`.
- Não expõe MCP servers do lado do agente (`mcpServers: []` é enviado).

## Desenvolvimento

```bash
npm test        # node --test — runner da stdlib, zero deps
```

Os testes usam um agente ACP falso e roteirizado
(`tests/fixtures/fake-acp.mjs`) sobre stdio real — sem o CLI Devin ou credenciais.

## Licença

MIT — ver [LICENSE](LICENSE).
