# Workers em background por padrão

Toda sessão segue a política de fan-out do `devin-orchestrator`:

1. **Tarefa com 2+ unidades independentes ou escopo grande** → decompor e
   disparar workers em background (`run_subagent`, `is_background=true`).
   A sessão principal NÃO executa em série o que pode ser paralelo.
2. **Máximo 3 workers concorrentes** — respeitar CPU limitada; trabalhos
   pesados nos workers rodam sequenciais.
3. **Sem aninhamento** — workers nunca abrem workers.
4. **Sessão responsiva** — depois de disparar, continuar trabalho útil ou
   encerrar o turno informando o que está rodando; nunca fazer polling em
   loop que bloqueie o usuário.
5. **Coleta obrigatória** — resultados são consolidados pelo Boss antes de
   reportar; nunca declarar concluído sem ler os relatórios dos workers.
6. **Trivial inline** — typos, perguntas e unidade única não justificam
   fan-out.

Detalhes e planner determinístico: skill `devin-orchestrator`.
