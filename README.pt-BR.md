# devin-switch

> **Projeto comunitário não oficial.** Sem afiliação, endosso ou patrocínio da
> Cognition AI. "Devin" é marca registrada da Cognition AI.

**[English](README.md)** · Português (BR)

O `devin-switch` alterna entre **perfis de configuração do Devin** —
hooks, servidores MCP, modelos, regras de cascade, configurações de UI —
com um snapshot verificado antes de cada escrita e um journal do qual você
pode reverter. **Dry-run por padrão**: nada é escrito sem `--apply`.

## O problema

O comportamento do Devin vive em alguns arquivos JSONC espalhados por duas
raízes: `config.json` + `mcp_config.json` no **diretório de dados**
(`~/.config/devin`, `%APPDATA%/devin`) e `User/settings.json` no
**diretório de config da UI** (`~/.config/Devin`, `%APPDATA%/Devin`).
Querer um setup "corporativo" travado e um "pessoal" permissivo significa
editar os mesmos arquivos de um lado para outro — na mão, sem desfazer.

O `devin-switch` trata cada variante como um diretório declarativo de
overlay e faz a troca com segurança.

## Modelo de segurança

- **Dry-run por padrão** — `use` e `rollback` imprimem um plano com
  máscaras e não escrevem *nada* (nem o journal) sem `--apply`.
- **Snapshot verificado** — antes de qualquer escrita, cada arquivo
  prestes a mudar é copiado para
  `.devin-ecosystem/switch-backups/<ts>/` com um manifesto sha256. As
  cópias são re-hasheadas *e* comparadas com as fontes vivas; qualquer
  divergência aborta antes de escrever um único byte.
- **Escritas atômicas** — arquivo tmp irmão + `os.replace`; nada de
  config pela metade.
- **`credentials.toml` nunca é tocado** — não é lido, não é escrito, nem
  aberto para hash. Um perfil que o inclua recebe `skip`.
- **Segredos mascarados em toda saída** — arquivos com nome de
  credencial (`.env*`, `*.pem`, `*secret*`, …) nunca têm conteúdo
  impresso; dentro de arquivos imprimíveis, valores sob chaves sensíveis
  (`token`, `secret`, `password`, `api_key`, `auth`…) ou que parecem
  tokens (blobs alfanuméricos longos, JWTs, prefixos `sk-`/`ghp_`/`xox`)
  aparecem como `<redacted>`.
- **Sem rede** — só stdlib, Python ≥ 3.10.

## Instalação

Requer Python ≥ 3.10 e `pipx`. **Windows (PowerShell):** instale o `pipx` com `py -m pip install --user pipx`, rode `py -m pipx ensurepath` e reabra o terminal. **Linux (Debian/Ubuntu):** rode `sudo apt install pipx python3-venv` e `pipx ensurepath`; reabra o terminal.

```bash
pipx install "devin-switch @ git+https://github.com/Icaro0310/devin-switch.git"
```

(Ainda não publicado no PyPI; a instalação via GitHub acima é a via oficial.)

## Uso

```bash
devin-switch list                       # perfis descobertos
devin-switch show personal              # o que um perfil gerencia (chaves, não valores)
devin-switch diff corporate personal    # diff mascarado entre dois perfis
devin-switch use personal               # DRY-RUN: plano mascarado por arquivo
devin-switch use personal --apply       # snapshot → verificar → escrever → journal
devin-switch rollback                   # DRY-RUN: o que seria restaurado
devin-switch rollback --apply           # restaura o último backup verificado
devin-switch doctor                     # sanidade da config + perfil mais próximo
```

Todo comando aceita `--data-dir`, `--config-dir` e `--profiles-dir` para
sobrescrever os padrões da plataforma (`--config-dir` cai para
`--data-dir` em layouts de raiz única). O diretório de perfis resolve
nesta ordem: `--profiles-dir` → `$DEVIN_SWITCH_PROFILES_DIR` →
`./profiles` → os exemplos embutidos.

O código de saída é `0` em sucesso/dry-run limpo e `1` em erros — e, no
`doctor`, em qualquer check `FAIL` (como no `devin-doctor`).

## Perfis

Um perfil é um diretório sob `profiles/` cujos arquivos mapeiam 1:1 para o
espaço de config gerenciado — veja [`profiles/README.md`](profiles/README.md):

```
profiles/
  corporate/
    profile.json          # só metadados — nunca copiado
    config.json           # → <data-dir>/config.json
    mcp_config.json       # → <data-dir>/mcp_config.json
    User/settings.json    # → <config-dir>/User/settings.json
  personal/
    ...
```

Overlays são **substituições de arquivo inteiro**, não merges — o que o
perfil traz é o que o arquivo vira. Os arquivos são JSONC: comentários
`//` e `/* */` permitidos, vírgulas à direita não.

### O perfil `lab` (rodadas A/B do G3)

`profiles/lab/` é uma config hermética para avaliação A/B de skills:
modelo pinado — `SWE-2-High` (tier free em 2026-10-04), o mesmo id
em `config.json`, `User/settings.json` e `profile.json`, **sem hooks e sem nenhum servidor MCP** — deliberado, porque
hooks de learning-loop / prompt-logging e o MCP de memória deixariam a
tentativa n aprender com a n-1 — e `autoGenerateMemories` desligado.
Rotule as sessões como `g3-ab`. Ressalva: ainda está em aberto se o
Devin consegue isolar o diretório de config por workspace; se não
conseguir, rode as tentativas **em série** e deixe o `devin-switch`
alternar o `lab` entre elas (`rollback` restaura os bytes anteriores
exatamente). Veja `profiles/README.md`.

## O que acontece no `--apply`

1. **Plano** — por arquivo: `create` / `modify` / `unchanged` / `skip`
   (`credentials.toml`, caminhos inseguros).
2. **Snapshot** — bytes pré-troca copiados para
   `~/.config/Devin/.devin-ecosystem/switch-backups/<timestamp>/` com um
   `manifest.json` registrando sha256 por arquivo (`existed: false` para
   arquivos que a troca criaria).
3. **Verificação** — cada cópia precisa bater com o sha256 registrado *e*
   ainda casar com a fonte viva (captura edições no meio da troca).
   Qualquer problema → aborta, nada escrito, backup mantido como prova.
4. **Escrita** — tmp+rename atômico por arquivo.
5. **Journal** — uma linha JSON em
   `.devin-ecosystem/switch-journal.jsonl`:
   `{ts, action, profile, files_changed, backup_dir}`.

O `rollback` lê a entrada `use` mais recente cujo backup ainda existe,
restaura o snapshot (e apaga arquivos que a troca criou), depois anexa
uma entrada `rollback` — o backup *não* é consumido, então você pode
trocar de novo depois.

## Desenvolvimento

```bash
python -m pytest            # 62 testes, todos em fixtures sintéticas de tmp-dir
python -m devin_switch.cli doctor --profiles-dir profiles
```

A suíte roda inteiramente contra raízes Devin falsas — nenhuma instalação
real é tocada, e fixtures de `credentials.toml` só são verificadas por
digest.

## Relacionados

- [`devin-doctor`](https://github.com/Icaro0310/devin-doctor) — diagnostica
  uma instalação Devin (somente leitura, sempre); o `devin-switch doctor`
  cobre o canto de arquivos de config desse espaço, inline, sem
  dependência.
