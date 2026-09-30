# Devin Office

Pixel-art office que observa **atividade real** do Devin CLI/Desktop — sessões,
subagents e chamadas MCP — e renderiza cada agente como um personagem animado
num escritório em pixel art, diretamente no browser.

## Arquitetura

```
sessions.db (Windows local, %APPDATA%\devin\cli)
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
- `http://100.102.159.65:8790` — direto via Tailscale

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
