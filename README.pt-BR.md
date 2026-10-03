<div align="center">

<img src="assets/banner.svg" alt="devin-orchestrator" width="100%"/>

</div>

# devin-orchestrator

> Ferramenta comunitária não oficial, sem afiliação ou endosso da Cognition AI.
>
> **[English](README.md)** · Português (BR)

Política de fan-out com workers em background para o Devin Desktop. Fornece
uma skill/regra e um planner determinístico; o Devin executa o plano aprovado.

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
devin-orchestrator plan '{"kind":"implementation","independent_units":3,"needs_write":true,"estimated_scope":"large","summary":"API + UI + testes"}'
```

## Instalação num workspace

Clone o repositório para copiar os ficheiros de extensão do Devin:

```bash
git clone https://github.com/Icaro0310/devin-orchestrator.git
```

Na raiz do workspace, copie os ficheiros com o shell do teu SO.

**Windows (PowerShell):**

```powershell
New-Item -ItemType Directory -Force .devin\skills, .devin\rules | Out-Null
Copy-Item -Recurse devin-orchestrator\.devin\skills\devin-orchestrator .devin\skills\
Copy-Item devin-orchestrator\.devin\rules\background-workers.md .devin\rules\
```

**Linux:**

```bash
mkdir -p .devin/skills .devin/rules
cp -R devin-orchestrator/.devin/skills/devin-orchestrator .devin/skills/
cp devin-orchestrator/.devin/rules/background-workers.md .devin/rules/
```

A regra é always-on; a skill é acionada pelo modelo.

## Limitações

O CLI apenas devolve um plano JSON; não cria workers nem modifica ficheiros.
A skill/regra do workspace fornece instruções; executar workers depende do
suporte de subagents em background do Devin.

## Limites de CPU

- Teto absoluto: **3 workers concorrentes** (`DEVIN_MAX_WORKERS` só reduz).
- Trabalho pesado (build/teste) dentro dos workers roda single-process.
- Prefira workers read-only para investigação.

## Desenvolvimento

```bash
pip install -e ".[dev]"
```

## Teste

```bash
pytest -q   # matriz comportamental: trivial→0, unidades→min(N,3), aninhado→0, ...
```

## Funciona só com o Devin (modo Devin-only)

O planner corre localmente; a execução dos subagentes acontece dentro do
próprio runtime do Devin, por isso o Devin é a única dependência — nenhum
framework de agentes, fila ou servidor de modelos separado para instalar.

## Suporte de plataformas

Política de workspace e wrappers finos — sem código específico de
plataforma. Corre onde o Devin correr; o CI testa em `windows-latest` +
`ubuntu-latest`.

## Licença

MIT — vê [LICENSE](LICENSE).
