---
name: devin-orchestrator
description: "Fan-out de trabalho para subagents em background mantendo a sessão principal responsiva. O agente-Boss decompõe a tarefa, o planner determinístico aplica limites (máx 3 workers, sem aninhamento), e o usuário continua interagindo enquanto os workers correm."
triggers:
  - model
---

# Devin Orchestrator — workers em background por padrão

Quando uma tarefa tem **2+ unidades de trabalho independentes** ou escopo
grande, NÃO execute tudo em série na sessão principal. Decomponha, dispare
workers em background e mantenha a sessão livre para o usuário continuar
escrevendo.

## Por quê

- Tarefas em série bloqueiam a sessão: o usuário espera na fila para dar o
  próximo parecer.
- Workers em background correm em paralelo; o Boss (sessão principal)
  consolida e reporta. O usuário pode falar a qualquer momento.

## Fluxo obrigatório

1. **Decompor** — identifique unidades de trabalho genuinamente disjuntas
   (arquivos/repos diferentes, etapas sem dependência entre si).
2. **Planejar** — antes de disparar, gere o plano:
   ```bash
   devin-orchestrator plan '{"kind":"implementation","independent_units":3,"needs_write":true,"estimated_scope":"large","summary":"API + UI + testes"}'
   ```
   O planner aplica os limites em código — não tente contorná-lo.
3. **Disparar em background** — `run_subagent(is_background=true)` por
   unidade, no máximo o número do plano (≤3). Prompt completo e autônomo:
   paths, convenções, o que entregar de volta. Workers são stateless.
4. **Não bloquear** — continue trabalho útil na sessão principal ou encerre
   o turno informando o que está rodando. NUNCA faça polling em loop.
5. **Consolidar** — ao receber `<subagent_completion_notification>` (ou
   `read_subagent`), valide o resultado e reporte ao usuário. `collect=true`
   no plano é contrato: nunca reporte concluído sem coletar.

## Quando NÃO abrir workers

- Correções triviais, typos, respostas a perguntas — execute inline.
- Trabalho de uma unidade só — a sobrecarga de coordenação não compensa.
- Dentro de um worker — aninhamento é proibido (`DEVIN_INSIDE_SUBAGENT=1`
  faz o planner retornar 0 workers).

## Limites de CPU (máquina limitada)

- Teto absoluto: **3 workers concorrentes** (`DEVIN_MAX_WORKERS` só reduz).
- Tarefas pesadas (build/teste) nos workers: rodar sequencialmente ou com
  `-j1`/single-process, não em fan-out interno.
- Prefira workers read-only (`subagent_explore`) para investigação —
  `needs_write=false` no spec. Só use `subagent_general` quando o trabalho
  exige escrita/execução.

## Regras duras

- Nunca crie repositórios, branches remotos ou sessões ACP dentro de um
  worker sem pedido explícito.
- Nunca peça a um worker para abrir outro worker.
- Não replique trabalho: prompts disjuntos, arquivos disjuntos.
- O Boss responde ao usuário; workers nunca falam com o usuário diretamente.

## Planner (código, não opinião)

`src/devin_orchestrator/planner.py` — entrada é um spec JSON com sinais
estruturados (`kind`, `independent_units`, `estimated_scope`, `needs_write`);
saída é `{workers, mode, profiles, collect, warnings}`. A decisão de *como*
decompor é do modelo; os limites são do código.
