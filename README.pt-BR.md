<div align="center">

<img src="assets/banner.svg" alt="devin-bridge" width="100%"/>

<a href="https://github.com/Icaro0310/devin-bridge/actions/workflows/tests.yml"><img src="https://github.com/Icaro0310/devin-bridge/actions/workflows/tests.yml/badge.svg" alt="tests"/></a>


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

### Rótulos de sessão (`--label`)

Toda sessão que a bridge *cria* é marcada para que a automação a jusante
(classificação do devin-janitor, scorekeeping do devin-dream) reconheça
sessões criadas pela bridge de forma determinística:

```bash
devin-bridge new "$HOME/src/meu-repo" --label janitor:classification
devin-bridge prompt "$HOME/src/meu-repo" "..." --label dream:scorekeeping
```

- O formato é `origin:purpose` (padrão `bridge:unlabeled`). Cada parte é
  um slug (`[A-Za-z0-9._-]`, ≤64 chars) — um rótulo nunca carrega texto
  de prompt nem conteúdo de sessão.
- O rótulo é enviado ao agente em `_meta` do `session/new`
  (`{"devin-bridge": {origin, purpose, label}}`), o ponto de extensão
  previsto na spec ACP. Se o Devin persiste `_meta` é não-documentado.
- O **registo autoritativo** é um sidecar local `session-labels.json`
  mapeando `sessionId → {label, origin, purpose, createdAt, cwd}`,
  gravado atomicamente no diretório de estado da bridge:
  `$XDG_STATE_HOME/devin-bridge` (Linux), `%LOCALAPPDATA%\devin-bridge`
  (Windows). Sobreposição via `DEVIN_BRIDGE_STATE_DIR` ou `--state-dir`.
- Sessões retomadas mantêm o rótulo com que foram criadas; a bridge
  nunca rotula sessões que não criou. `devin-bridge sessions` mostra o
  rótulo registado por sessão.

Presets nomeados (`--preset`, ou `policy --init --preset <nome>`):

- `ask` — o padrão fail-closed; tudo exige aprovação.
- `read-only` — nega terminal/fsWrite/network; leituras ficam abertas exceto
  ficheiros de credenciais. Para intake e automação que só observa.
- `full` — permite tudo. **Risco alto** — só ambientes descartáveis de
  confiança; o CLI avisa sempre que é selecionado.

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


### `probe` — ACP compatibility probe (BR-1)

`devin-bridge probe` verifica o handshake ACP de ponta a ponta: `initialize` +
`authenticate`, then (unless `--no-session`) a `session/new` in a temp dir
labelled `bridge:probe` — which `devin-janitor` can later reap as an
automatic session. Output is a JSON compat report (checks, models,
configOptions); exit code 1 on failure. This is the foundation for
`devin-internals-spec`'s drift checks.

### `intake` — file-based mailbox (BR-3)

`devin-bridge intake` processes task files dropped in
`<state-dir>/mailbox/inbox/*.json` — **sem listener de rede**. A task is
`{"task": "prompt text", "repo"?: "<dir>", "model"?: "<id>"}`.

- Tasks are **entrada não confiável**: they only become a prompt inside a normal
  session, so the active policy still gates every capability (default
  `ask` = human approves each step).
- FIFO by filename; each file moves inbox → processing → done/failed, with
  `.result.json` / `.err` sidecars.
- `inbox/` must be owner-only (`chmod 700`); files over 64KB and tasks over
  16k chars are rejected.
- `--dry-run` validates without creating sessions; `--repo` sets a default
  cwd for tasks without `repo`.

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

## Quando usar

- Você quer scriptar sessões Devin por repo — criar, retomar, dar prompt — fora da UI interativa.
- Você quer um gate de permissões: `policy.json` permite/nega/pergunta por tipo de tool, deny vence, fail-closed por defeito.
- Você quer deixar um loop de agente a correr sem auto-aprovar cada pedido de terminal e filesystem.
- Você quer testar primeiro o que uma política decidiria: `devin-bridge policy --check terminal "<cmd>"`.

## Quando NÃO usar

- Você precisa de servidores MCP do lado do agente — a bridge envia `mcpServers: []`.
- Você não tolera internals não documentados: usa o modo `acp` do CLI e auth `_meta.api_key`, que podem mudar sem aviso.
- Você quer assumir uma sessão já aberta noutro lado — `session/load` falha com `session_locked`.

## FAQ

**Como scripto sessões Devin sem auto-aprovar cada permissão?** Execute `devin-bridge policy --init`, depois `devin-bridge new "<repo>"` e `devin-bridge prompt "<repo>" "..."`. Cada pedido `terminal/*`, `fs/*` e de permissão passa pelo seu `policy.json` — tudo o que não estiver explicitamente permitido é negado, e decisões `ask` perguntam interativamente apenas num TTY.

**Do que o devin-bridge precisa para autenticar?** De nada extra. Lê `windsurf_api_key` do `credentials.toml` existente do Devin CLI (`%APPDATA%\devin\` no Windows, `$XDG_DATA_HOME/devin/` no Linux) e resolve o CLI a partir do `PATH` ou de `DEVIN_CLI_PATH`. O token nunca é logado nem persistido.

**É seguro correr o devin-bridge sem supervisão?** Mais seguro do que auto-aprovar snippets, com ressalvas. O defeito é fail-closed: pedidos desconhecidos são negados, e execuções não interativas ficam fechadas a menos que `--yes` seja passado. Ainda depende de internals não documentados do modo `acp`, por isso fixe uma versão testada do Devin CLI.

## Licença

MIT — ver [LICENSE](LICENSE).


---

Se isso te poupou tempo de depuração, uma ⭐ no repositório ajuda outras pessoas a encontrá-lo.
