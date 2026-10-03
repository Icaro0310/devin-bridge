<div align="center">

<img src="assets/banner.svg" alt="devin-office" width="100%"/>

</div>

# Devin Office

> Ferramenta comunitária não oficial para Devin. Sem afiliação, endosso ou
> patrocínio da Cognition AI. Devin é marca da Cognition AI.
>
> **[English](README.md)** · Português (BR)

Dashboard local de sessões ativas do Devin CLI/Desktop e subagents. Lê o banco
de sessões do Devin em modo somente leitura e mostra a atividade no navegador.
Pode rodar na máquina do Devin ou enviar o estado de um probe local para um hub
privado.

O renderer atual usa uma visualização SVG em circuito, não sprites de pixel art.
Os sprites e scripts de geração são material opcional de desenvolvimento; o
dashboard não precisa deles para rodar.

## Preview

![dashboard devin-office — chip Devin com traces vivos para ferramentas e subagentes](assets/demo.png)

Demo ao vivo (dados de exemplo): [icaro0310.github.io/demos/devin-office.html](https://icaro0310.github.io/demos/devin-office.html)

## O que roda

| Componente | Função |
|---|---|
| `daemon.py` | Lê `sessions.db` local em modo somente leitura e serve `/api/state` e o dashboard. Modo independente, sem túnel ou servidor remoto. |
| `probe.py` | No modo split, consulta o estado local e envia atualizações ao hub só quando o estado muda. Controles remotos ficam desativados por padrão. |
| `hub.py` | Serve o dashboard, recebe estado do probe e expõe endpoints de saúde/estado. Escuta apenas em loopback por padrão. |
| `executor.py` | Processo ACP opcional para pedidos message/spawn/kill. Requer Devin CLI autenticado e opt-in explícito. |
| `index.html` | Dashboard SVG autocontido; sem build de JavaScript/CSS. |

`OFFICE_ECO_URL` pode fornecer opcionalmente um JSON de status de outro
sistema. Por padrão, não há dependência de outro dashboard ou serviço do
maintainer.

## Requisitos

- Devin Desktop ou Devin CLI instalado na máquina cujas sessões queres
  observar.
- Python 3.10 ou superior. Dashboard, probe e hub usam apenas a biblioteca
  padrão do Python; não é preciso `pip install`.
- O executável `devin` no `PATH` é necessário apenas para o executor ACP
  opcional.

## Início rápido: uma máquina

Este modo somente leitura é a forma mais simples de experimentar. Dentro do
clone do repositório:

**Windows (PowerShell):**

```powershell
git clone https://github.com/Icaro0310/devin-office.git
cd devin-office
py -3 daemon.py --port 8788
```

**Linux:**

```bash
git clone https://github.com/Icaro0310/devin-office.git
cd devin-office
python3 daemon.py --port 8788
```

Abre `http://localhost:8788`. Encerra com `Ctrl+C`. O processo escuta em
loopback e não escreve nos bancos do Devin.

## Onde estão os dados do Devin

| Store | Windows | Linux |
|---|---|---|
| `sessions.db`, `session_locks/` | `%APPDATA%\devin\cli\` | `$XDG_DATA_HOME/devin/cli/` (padrão `~/.local/share/devin/cli/`) |
| Bancos ACP, `state.vscdb` | `%APPDATA%\Devin\User\` | `$XDG_CONFIG_HOME/Devin/User/` (padrão `~/.config/Devin/User/`) |
| `credentials.toml` (só executor) | `%APPDATA%\devin\` | `$XDG_DATA_HOME/devin/` (padrão `~/.local/share/devin/`) |

`OFFICE_DATA_DIR` e `OFFICE_CONF_DIR` sobrepõem as raízes de dados e de
configuração da UI. Usa-as se o Devin estiver em caminhos XDG personalizados.

## Funciona só com o Devin (modo Devin-only)

O modo standalone acima é o produto completo para uma máquina: um processo
`daemon.py` lê as stores locais do Devin e serve o escritório pixel-art em
`127.0.0.1:8788`. Sem VM, hub, túnel ou segunda máquina — o modo split abaixo
é estritamente opcional, para quando *tu* quiseres um dashboard noutro
computador.

Postura de segurança do modo standalone: bind só em loopback, acesso
somente-leitura aos bancos do Devin, apenas endpoints GET, e leituras
cross-origin restritas a origens loopback (define `OFFICE_CORS_ORIGIN`
explicitamente se um dashboard noutro host/porta precisar mesmo de ler
`/api/state`).

## Modo split: probe local e hub privado

Usa este modo quando o Devin deve enviar estado de sessões a outro computador
ou servidor. O hub serve a página; o probe fica junto aos dados locais do Devin.

### Hub (servidor Linux)

O padrão seguro é loopback. Para acesso remoto, escuta apenas numa interface
privada, como o endereço da tua VPN/Tailscale, define um token aleatório longo
e restringe a porta `8790` no firewall:

```bash
export OFFICE_BIND='<ip-da-interface-privada>'
export OFFICE_TOKEN='<mesmo-segredo-aleatorio-usado-pelo-probe>'
python3 hub.py --port 8790
```

Um bind fora de loopback recusa iniciar sem `OFFICE_TOKEN`. O hub usa HTTP
simples: mantém-no numa rede privada confiável ou coloca-o atrás de um reverse
proxy com TLS/autenticação configurados. `/api/state` e `/api/health` são
legíveis por clientes que alcançam a interface; o token protege POST de
ingestão e comandos, não os endpoints de leitura.

### Probe (Windows PowerShell)

Se o hub estiver acessível pela rede privada:

```powershell
$env:OFFICE_HUB = 'http://<endereco-privado-do-hub>:8790'
$env:OFFICE_TOKEN = '<mesmo-segredo-aleatorio-usado-pelo-hub>'
py -3 probe.py --interval 3
```

Para um hub apenas em loopback, abre um túnel SSH noutro terminal e define
`OFFICE_HUB` como `http://localhost:8790`.

### Probe (Linux)

```bash
export OFFICE_HUB='http://<endereco-privado-do-hub>:8790'
export OFFICE_TOKEN='<mesmo-segredo-aleatorio-usado-pelo-hub>'
python3 probe.py --interval 3
```

Para um hub apenas em loopback, corre `ssh -N -L 8790:127.0.0.1:8790
<user>@<server>` num segundo terminal e mantém `OFFICE_HUB` em
`http://localhost:8790`.

O probe envia metadados de sessões e atividade de ferramentas ao hub. Não o
apontes para um host público ou não confiável.

## Controles de sessão opcionais

A observação é somente leitura. Os endpoints `message`, `spawn` e `kill` do hub
ficam **desativados por padrão**. Para os ativar, define
`OFFICE_CONTROL_ENABLED=1` no hub e no probe, usa o mesmo `OFFICE_TOKEN` nos
dois e mantém a comunicação numa rede privada. O executor local inicia
`devin acp` com o CLI autenticado. Nunca atives controles num endpoint
acessível publicamente.

## Configuração

| Variável | Padrão | Função |
|---|---|---|
| `OFFICE_BIND` | `127.0.0.1` | Endereço de escuta do hub. Fora de loopback exige token. |
| `OFFICE_TOKEN` | não definido | Token partilhado para POST (`X-Office-Token`). Obrigatório para bind fora de loopback. |
| `OFFICE_CONTROL_ENABLED` | desativado | Opt-in para controles message/spawn/kill no hub e no probe. |
| `OFFICE_HUB` | `http://localhost:8790` | Destino do probe; `--hub` sobrepõe. |
| `OFFICE_INTERVAL` | `3` segundos | Intervalo do probe; `--interval` sobrepõe. |
| `OFFICE_ECO_URL` | não definido | Endpoint confiável e opcional com JSON de status do ecossistema. |
| `OFFICE_CORS_ORIGIN` | só loopback | `Access-Control-Allow-Origin` para `/api/state`. Por omissão só origens loopback; nunca `*`. |
| `OFFICE_DATA_DIR` | caminho por SO acima | Sobrepõe a raiz de dados CLI do Devin. |
| `OFFICE_CONF_DIR` | caminho por SO acima | Sobrepõe a raiz de configuração UI do Devin. |
| `OFFICE_DEVIN_EXE` | `devin` no `PATH` | Executável Devin CLI para o executor opcional. |
| `OFFICE_SPAWN_CWD` | pasta acima do clone | Diretório de trabalho das sessões criadas. |
| `OFFICE_SPAWN_MODE` | `smart` | Mode ID das sessões ACP. |
| `OFFICE_PROMPT_TIMEOUT` | `900` segundos | Timeout de prompt ACP. |
| `OFFICE_SSH_HOST` | não definido | Host SSH para o túnel gerido por `up.pyw` no Windows. |
| `OFFICE_PORT` | `8790` | Porta do túnel gerido por `up.pyw`. |

## Manter em execução

- **Windows:** `up.pyw` é um supervisor opcional para modo split. Define
  `OFFICE_HUB` para um hub acessível ou `OFFICE_SSH_HOST` para criar um túnel
  SSH de loopback. Inicia-o pelo Task Scheduler após definires as variáveis
  necessárias para esse utilizador.
- **Linux:** executa o probe num serviço de utilizador, por exemplo
  `systemd --user`. Cria `~/.config/devin-office.env` com `OFFICE_HUB` e
  `OFFICE_TOKEN`, restringe as permissões do ficheiro (`chmod 600`) e usa um
  unit com `EnvironmentFile=%h/.config/devin-office.env`. Não coloques um token
  real num unit commitado.
- **Hub:** usa um gestor de serviços (systemd, PM2 ou equivalente) e mantém o
  bind/firewall numa rede privada.

## Resolução de problemas

- `sessions.db not found`: verifica os caminhos acima ou define
  `OFFICE_DATA_DIR`.
- Sessões GUI ausentes: verifica `OFFICE_CONF_DIR`; a base CLI ainda pode
  funcionar sozinha.
- `devin` não encontrado: instala/autentica o Devin CLI ou define
  `OFFICE_DEVIN_EXE`. Só é necessário para controles.
- O hub rejeita POST do probe: confirma que `OFFICE_TOKEN` é o mesmo nos dois.
- Não aparecem nós do ecossistema: a integração é opcional; define
  `OFFICE_ECO_URL` apenas se tiveres um endpoint compatível.

## Licença e créditos

MIT — vê [LICENSE](LICENSE). A mobília é creditada no código-fonte; os
utilitários opcionais de geração de sprites não são necessários para usar o
Devin Office.
