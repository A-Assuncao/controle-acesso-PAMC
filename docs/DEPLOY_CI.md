# Deploy CI — GitHub Actions (multi-unidade)

Deploy **imediato** após `git push origin main` em cada unidade de producao (PAMC, CPBV, CPFBV), usando **self-hosted runners** — um agente por servidor, sem VPN entre unidades.

---

## Fluxo

```text
git push main  →  GitHub Actions  →  3 jobs em paralelo
                                      ├─ runner pamc  → update_app.bat
                                      ├─ runner cpbv  → update_app.bat
                                      └─ runner cpfbv → update_app.bat
```

Cada job executa o mesmo comando local:

```bat
C:\inetpub\wwwroot\controle-acesso-PAMC\update_app.bat
```

Isso chama `update\update.bat -NoElevate silent` (sem UAC, sem pause).

Logs por servidor: `logs\update.log`  
Logs no GitHub: aba **Actions** → workflow **Deploy producao** → job da unidade.

---

## Parte 1 — Repositório GitHub (uma vez)

### 1.1 Habilitar Actions

**Settings → Actions → General**

- Actions permissions: permitir workflows
- Workflow permissions: leitura do repositório é suficiente

### 1.2 Workflow

Arquivo: `.github/workflows/deploy-producao.yml`

- Matrix `site: [pamc, cpbv, cpfbv]`
- Caminho único: `APP_PATH: C:\inetpub\wwwroot\controle-acesso-PAMC`
- `fail-fast: false` — falha em uma unidade não cancela as outras

### 1.3 Seu dia a dia (desenvolvimento)

```bat
git add .
git commit -m "..."
git push origin main
```

Acompanhe em **Actions**. Três jobs verdes = três unidades atualizadas.

Execução manual: **Actions → Deploy producao → Run workflow**.

---

## Parte 2 — Cada servidor de produção (PAMC, CPBV, CPFBV)

Repita em **cada** computador onde o app está instalado.

### 2.1 Pré-requisitos

- App IIS funcionando em `C:\inetpub\wwwroot\controle-acesso-PAMC`
- Clone Git com `.git` (repositório **público** — sem PAT)
- `update_app.bat` testado com sucesso

### 2.2 Conta de serviço (Admin, sem UAC)

O `update.bat` manual pede UAC; o automático **não pode** pedir UAC.

Crie em cada servidor (PowerShell **como Administrador**):

```powershell
$senha = Read-Host "Senha para svc-deploy" -AsSecureString
New-LocalUser -Name "svc-deploy" -Password $senha -FullName "Deploy GitHub Runner" `
  -Description "Conta para runner GitHub e update automatico" -PasswordNeverExpires
Add-LocalGroupMember -Group "Administradores" -Member "svc-deploy"
```

Permissão na pasta do app (se o clone foi feito com outro usuário):

```bat
icacls C:\inetpub\wwwroot\controle-acesso-PAMC /grant svc-deploy:(OI)(CI)F /T
```

Teste **sem UAC** antes de instalar o runner:

```bat
runas /user:.\svc-deploy "cmd /c C:\inetpub\wwwroot\controle-acesso-PAMC\update_app.bat"
type C:\inetpub\wwwroot\controle-acesso-PAMC\logs\update.log
```

Se este teste falhar, o runner também falhará.

> **IIS:** a conta do App Pool (`IIS AppPool\...`) continua separada. Não troque o App Pool por causa do runner.

### 2.3 Instalar o runner GitHub

1. GitHub → repositório → **Settings → Actions → Runners → New self-hosted runner → Windows x64**
2. No servidor:

```powershell
New-Item -ItemType Directory -Force -Path C:\ActionsRunner
cd C:\ActionsRunner
# Baixe e extraia o zip conforme instrucoes na tela do GitHub
.\config.cmd --url https://github.com/A-Assuncao/controle-acesso-PAMC --token TOKEN_DA_TELA
```

Durante `config.cmd`:

| Pergunta | PAMC | CPBV | CPFBV |
|----------|------|------|-------|
| Runner name | `pamc-prod` | `cpbv-prod` | `cpfbv-prod` |
| Labels | adicionar **`pamc`** | adicionar **`cpbv`** | adicionar **`cpfbv`** |
| Instalar como serviço? | **Sim** | **Sim** | **Sim** |
| Conta do serviço | `.\svc-deploy` | idem | idem |

3. Confirmar em **Settings → Runners**: status **Idle** (verde).

Labels obrigatórias por unidade: `self-hosted`, `windows` (padrao) + **`pamc`** ou **`cpbv`** ou **`cpfbv`**.

### 2.4 Ordem sugerida de implantacao

1. Instalar runner só no **PAMC** → temporariamente editar workflow com `site: [pamc]` → push → testar
2. CPBV e CPFBV → restaurar matrix completa
3. (Opcional) Manter tarefa agendada 00:00 como backup se runner offline

---

## Adicionar nova unidade

1. Instalar app + runner no servidor novo (label ex.: `nova-unidade`)
2. No workflow, acrescentar na matrix:

```yaml
matrix:
  site: [pamc, cpbv, cpfbv, nova-unidade]
```

3. `git push main` — novo job passa a rodar automaticamente.

Mesmo `APP_PATH` em todos — **nao** precisa duplicar linha de caminho.

Se alguma unidade tiver pasta diferente, avise e use variavel por site (excecao).

---

## Troubleshooting

| Problema | Causa provavel | Acao |
|----------|----------------|------|
| Job fica **Queued** | Runner offline ou label errada | Verificar servico em `services.msc`; labels no GitHub |
| `Permission denied` em `.git` | Conta do runner sem acesso | `icacls` ou re-clone como `svc-deploy` |
| `iisreset` falhou | Runner sem Admin | Conta `svc-deploy` em Administradores |
| Job verde mas site antigo | Sem mudanca no Git | Normal — log diz "Already up to date" |
| UAC no manual, falha no CI | Esperado | CI usa `update_app.bat` (-NoElevate), nao duplo clique em `update.bat` |

### Comandos uteis

```bat
REM Teste local do update (conta de servico)
runas /user:.\svc-deploy "cmd /c C:\inetpub\wwwroot\controle-acesso-PAMC\update_app.bat"

REM Log no servidor
type C:\inetpub\wwwroot\controle-acesso-PAMC\logs\update.log

REM Servico do runner
Get-Service actions.runner.*
```

---

## Relacao com outros mecanismos

| Mecanismo | Quando roda |
|-----------|-------------|
| **GitHub Actions** (este doc) | Imediato apos push em `main` |
| **Tarefa 00:00** (`agendar_atualizacao.ps1`) | Backup diario se runner cair |
| **`update\update.bat` manual** | Manutencao RDP (com UAC) |

---

## Referencias

- [Self-hosted runners (GitHub Docs)](https://docs.github.com/en/actions/hosting-your-own-servers/managing-self-hosted-runners)
- Tutorial IIS local: `docs/TUTORIAL_IIS.md`
- Script de update: `update/update.bat` e `update_app.bat`
