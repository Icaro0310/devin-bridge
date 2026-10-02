# Devin Office

> **EN:** A pixel-art office that renders **real Devin CLI/Desktop activity** —
> sessions, subagents and MCP calls — as animated characters in your browser.
> Zero-dependency Python hub + probe; point it at your own `sessions.db` and VM.
> Docs below are in Portuguese.

Pixel-art office que observa **atividade real** do Devin CLI/Desktop — sessões,
subagents e chamadas MCP — e renderiza cada agente como um personagem animado
num escritório em pixel art, diretamente no browser.

## Arquitetura

```
sessions.db (máquina local — Windows %APPDATA%\devin\cli ou
             Linux ~/.local/share/devin/cli)
    │
    ▼
probe.py ── HTTP POST /api/ingest ──► hub.py (VM, PM2: devin-office)
(local, muda só                      serve /root/devin-office/
 quando o estado muda)                      │
                                            ▼
                              index.html ◄── GET /api/state (browser)
                              renderer single-file DOM/CSS
```

- **`probe.py`** — probe magro (~20 MB RAM) que corre na máquina Windows.
  Recolhe o WorldState via `daemon.collect_state()` (lê `sessions.db` em WAL
  read-only + `jev_log.db` + heartbeat) e faz POST para o hub **apenas quando
  o estado muda** (hash SHA-1).
- **`daemon.py`** — wrapper/collector local; também funciona standalone como
  smoke test servindo `/api/state` + `index.html` na porta 8788.
- **`hub.py`** — hub zero-deps (stdlib only) na VM. Recebe `POST /api/ingest`,
  serve `index.html`, `/api/state`, `/api/health` e `/assets/*` na porta 8790.
  Auth opcional via env `OFFICE_TOKEN` (header `X-Office-Token`).
- **`up.pyw`** — supervisor local (pythonw, sem janela) que mantém o túnel SSH
  (`-L 8790:127.0.0.1:8790 devin-vm`) e o probe vivos, re-spawnando se morrerem.
- **`index.html`** — renderer single-file: DOM/CSS, sem canvas nem deps.

## URLs

- `http://localhost:8790` — via túnel SSH (mantido pelo `up.pyw`)
- `http://<your-vm>:8790` — direto via Tailscale/LAN (ex.: `100.x.y.z:8790`)

## Monta no teu setup / Run it on your own Devin install

Tudo é **Python stdlib — zero deps, zero build**. Os paths do Devin são
detectados por SO e todos os endpoints são configuráveis por env var.

### Modo standalone (uma máquina, sem VM — o mais fácil)

```bash
python3 daemon.py --port 8788     # Linux/macOS
py daemon.py --port 8788          # Windows
```

Serve `index.html` + `/api/state` diretamente — abre `http://localhost:8788`
e o escritório já renderiza as tuas sessões Devin. Não precisa de hub, probe,
túnel nem PM2.

### Modo split (probe no laptop → hub na VM/servidor)

```bash
# na VM/servidor:
python3 hub.py                    # escuta :8790, serve o frontend

# na máquina onde o Devin corre:
OFFICE_HUB=http://<vm>:8790 OFFICE_TOKEN=<segredo-partilhado> \
    python3 probe.py --interval 3
```

### Onde ele procura os dados do Devin

| | Windows | Linux |
|---|---|---|
| `sessions.db`, `session_locks/` | `%APPDATA%\devin\cli\` | `~/.local/share/devin/cli/` |
| `acp-messages/`, `state.vscdb` | `%APPDATA%\Devin\User\` | `~/.config/Devin/User/` |
| `credentials.toml` (executor) | `%APPDATA%\devin\` | `~/.local/share/devin/` |

### Variáveis de ambiente

| Var | Default | O que faz |
|---|---|---|
| `OFFICE_DATA_DIR` | deteção por SO (tabela acima) | override do data dir do Devin |
| `OFFICE_CONF_DIR` | deteção por SO | override do config dir do Devin |
| `OFFICE_HUB` | `http://localhost:8790` | URL do hub para o probe |
| `OFFICE_TOKEN` | — | auth partilhado (`X-Office-Token`); define também no hub |
| `OFFICE_DEVIN_EXE` | `devin` no PATH | path do executável Devin p/ o executor ACP |
| `OFFICE_SPAWN_CWD` / `OFFICE_SPAWN_MODE` | repo root / `smart` | cwd e modeId dos spawns via executor |
| `OFFICE_PROMPT_TIMEOUT` | `900` | timeout (s) dos prompts ACP |

### O que ajustar ao teu gosto

- **Roster de raças**: o mapeamento perfil→raça vive em `daemon.py`
  (keywords) e nos sprites `assets/chars/ai_<raca>.png` (7×3 frames, 48×48).
- **`jev_log.db` / `heartbeat/state.json`**: opcionais — são lidos de
  `../` se existirem (sinais ambient do meu ecossistema); sem eles o
  escritório funciona na mesma, só sem os personagens "ambient".
- **Executor** (`executor.py`): controlo real — spawn/message/kill de
  sessões ACP. Precisa do `devin` CLI autenticado. Se não quiseres
  controlo (só observação), não o lances: probe+daemon bastam.

## Deploy na VM

O hub serve `/root/devin-office/` na VM. Para atualizar sprites + renderer:

```bash
scp assets/chars/ai_*.png index.html devin-vm:/tmp/ && \
ssh devin-vm "mv /tmp/ai_*.png /root/devin-office/assets/chars/ && \
              mv /tmp/index.html /root/devin-office/index.html && \
              pm2 restart devin-office"
```

## Persistência

- **VM**: `hub.py` corre sob PM2 (`pm2 restart devin-office`), com resurrect
  garantido via supervisord.
- **Local (Windows)**: `up.pyw` é lançado no logon pela Startup folder
  (atalho `.vbs` em `shell:startup`) — mantém túnel + probe vivos e escreve
  em `up.log`.

## Raças (roster)

Cada subagent é mapeado deterministicamente para uma raça a partir de
keywords do seu perfil:

| Raça | Classe | Nota |
|------|--------|------|
| Mago | — | o boss: DEVIN |
| Orc | Druida | |
| Elfo | Arqueiro | |
| Anjo | Paladino | |
| Duende | Feiticeiro | |
| Anão | Guerreiro | |
| Demônio | Bruxo | |
| Vampiro | Artíficie | |
| Lobisomem | Xamã | |

Sheets finais: `assets/chars/ai_<raca>.png` — 7×3 frames de 48×48
(rows: down / up / right). Sheets originais 4×4 estilo RPG Maker em
`assets/chars/race_<raca>.png`.

## Sprite pipeline

```
tools/gen_rpgmaker.py   →  ai-src/rpgmaker/<raca>/  (4×4 sheets via Gemini headless,
                                                      venv do frame-ronin-mcp)
tools/fix_sheets.py     →  assets/chars/ai_<raca>.png
                           (cleanup por connected-component: isola o blob certo
                            em cada cell, content-crop, bottom-anchor 48×48,
                            deteção de grid por imagem → sheet office 7×3)
tools/make_races.py, tools/gen_races_ai.py  →  pipeline alternativo/legado
```

`previews/` contém gifs/pngs de verificação gerados durante o pipeline
(contact sheets, frames individuais, `_races_anim.gif`).

## Requisitos

- Python 3 (hub/probe/daemon: stdlib only, zero deps)
- Pillow (+ numpy, scipy para `fix_sheets.py`) — apenas para as tools de sprites
- `frame-ronin-mcp` venv para `gen_rpgmaker.py` (Gemini headless)

## Créditos

- Mobília do escritório: **pixel-agents** (MIT) via
  [harishkotra/agent-office](https://github.com/harishkotra/agent-office)
- Sprites das raças: gerados por AI (pipeline acima)
