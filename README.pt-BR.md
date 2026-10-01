# devin-orchestrator

Política de fan-out com workers em background para o Devin Desktop.
Decompõe trabalho não-trivial em unidades disjuntas, executa como subagents
em background e mantém a sessão principal interativa — o usuário continua
escrevendo enquanto os workers rodam.

## O que é

Duas camadas:

1. **Skill + regra always-on** (`.devin/skills/devin-orchestrator/`,
   `.devin/rules/background-workers.md`) — instruções ao modelo: tarefa com
   2+ unidades independentes ou escopo grande → fan-out em vez de série.
2. **Planner determinístico** (`src/devin_orchestrator/planner.py`) — os
   limites duros vivem em código, não em prosa. O modelo fornece sinais
   estruturados; o planner devolve quantos workers são permitidos, qual
   perfil usar, e aplica tetos que não podem ser contornados.

## Política (aplicada em código)

| Sinal | Plano |
|---|---|
| `kind=question` ou `estimated_scope=trivial` | 0 workers — inline |
| `independent_units=1`, small/medium | 0 workers — inline |
| `independent_units=N` (N≥2) | min(N, 3) workers em background |
| `kind=refactor` + escopo grande | até 3 workers em fatias disjuntas |
| `DEVIN_INSIDE_SUBAGENT=1` | 0 workers — aninhamento proibido |
| `needs_write=false` ou `kind=review` | `subagent_explore` (read-only) |

Todo plano com workers traz `collect=true`: o pai é obrigado a coletar os
resultados antes de reportar. O plano é apenas dado — sem paths, URLs ou
comandos; o planner não cria repositórios nem toca o filesystem.

## Uso

```bash
pip install -e ".[dev]"
devin-orchestrator plan '{"kind":"implementation","independent_units":3,"needs_write":true,"estimated_scope":"large","summary":"API + UI + testes"}'
```

## Instalação num workspace

Copie `.devin/skills/devin-orchestrator/` para `.devin/skills/` do workspace
e `.devin/rules/background-workers.md` para `.devin/rules/`. A regra é
always-on; a skill é acionada pelo modelo.

## Limites de CPU

- Teto absoluto: **3 workers concorrentes** (`DEVIN_MAX_WORKERS` só reduz).
- Trabalho pesado (build/teste) dentro dos workers roda single-process.
- Prefira workers read-only para investigação.

## Teste

```bash
pytest -q   # matriz comportamental: trivial→0, unidades→min(N,3), aninhado→0, ...
```

## Suporte de plataformas

Política de workspace e wrappers finos — sem código específico de
plataforma. Corre onde o Devin correr; o CI testa em `windows-latest` +
`ubuntu-latest`.
