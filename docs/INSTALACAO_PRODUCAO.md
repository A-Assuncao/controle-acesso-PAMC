# Instalação e operação em produção (Windows + IIS)

Guia **único** para instalar uma unidade nova, manter o site no ar e receber deploy automático via Git.

**Stack:** Django 6.0 · Python 3.12–3.14 · IIS + HttpPlatformHandler + uvicorn · WhiteNoise  
**Contas:** SYSTEM e Administradores (built-in) — **não crie usuário local** para update/runner.

---

## Índice

1. [Nova unidade — passo a passo](#1-nova-unidade--passo-a-passo)
2. [Scripts — o que cada um faz](#2-scripts--o-que-cada-um-faz)
3. [Deploy automático (GitHub Actions)](#3-deploy-automático-github-actions)
4. [Atualização no dia a dia](#4-atualização-no-dia-a-dia)
5. [Problemas comuns](#5-problemas-comuns)
6. [Outros documentos](#6-outros-documentos)

---

## 1. Nova unidade — passo a passo

```text
[A] Windows + IIS + Python + Git     (manual, uma vez)
[B] Clone + venv + .env + site IIS   (manual, uma vez)
[C] configurar_iis.ps1               (automático)
[D] instalar_runner_github.ps1       (opcional — deploy no push)
[E] Testes
```

### A — Pré-requisitos (manual)

| Item | Ação |
|------|------|
| IIS | `optionalfeatures` → Serviços de Informações da Internet |
| WAS + W3SVC | `Start-Service WAS; Start-Service W3SVC` |
| HttpPlatformHandler | [MSI](https://www.iis.net/downloads/microsoft/httpplatformhandler) → `iisreset` |
| Python **3.12+** | [python.org](https://www.python.org/downloads/windows/) — **Install for all users**, ex.: `C:\Python314\` — **não** só `AppData` |
| Git | `git --version` |
| Default Web Site | Parar se usar porta 80 para outro site |

Desbloqueio IIS (ou deixe o script da fase C fazer):

```powershell
& "$env:windir\system32\inetsrv\appcmd.exe" unlock config -section:system.webServer/handlers
& "$env:windir\system32\inetsrv\appcmd.exe" unlock config -section:system.webServer/httpPlatform
```

### B — Projeto (manual)

PowerShell **como Administrador**:

```powershell
cd C:\inetpub\wwwroot
git clone https://github.com/A-Assuncao/controle-acesso-PAMC.git
cd controle-acesso-PAMC

& "C:\Python314\python.exe" -m venv venv
.\venv\Scripts\pip install -r requirements.txt

copy .env.example .env
notepad .env
```

`.env` mínimo em produção: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, `DJANGO_ALLOWED_HOSTS` (detalhes em [CONFIGURACAO_AMBIENTE.md](CONFIGURACAO_AMBIENTE.md)).

**Site no inetmgr** (uma vez):

| Campo | Valor |
|-------|--------|
| Nome | `controle-acesso-PAMC` |
| Pasta | `C:\inetpub\wwwroot\controle-acesso-PAMC` |
| Porta | `3000` |

#### Acesso pelo nome da unidade (`.local`)

Quando o nome da máquina estiver publicado na rede por mDNS, a unidade pode ser acessada como
`http://<sigla>.local`, sem depender de o usuário conhecer o IP e sem informar `:3000`.

1. Confirme, em outro computador da mesma rede, que o nome responde:

```powershell
$sigla="uprro"; Test-NetConnection "${sigla}.local" -Port 3000
```

2. Inclua o nome curto e o nome `.local` no `.env`:

```env
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,<ip-atual>,<sigla>,<sigla>.local
```

3. Crie no site da aplicação um binding HTTP na porta 80 com o host `<sigla>.local`:

```powershell
$sigla="uprro"; Import-Module WebAdministration; if(-not (Get-WebBinding -Name "controle-acesso-PAMC" -Protocol http | Where-Object {$_.bindingInformation -eq "*:80:${sigla}.local"})){New-WebBinding -Name "controle-acesso-PAMC" -Protocol http -Port 80 -HostHeader "${sigla}.local"}; iisreset
```

Troque o valor de `$sigla` em cada unidade. Exemplo para a UPRRO: `http://uprro.local`.

O binding com host específico pode coexistir com o `Default Web Site` na porta 80. O endereço
`.local` normalmente funciona apenas na mesma sub-rede; entre VLANs ou quando mDNS estiver
bloqueado, configure o nome no DNS da rede. Uma reserva DHCP mantém o Windows em DHCP e evita
mudanças inesperadas de endereço.

### C — Configurar tudo (um comando)

```powershell
cd C:\inetpub\wwwroot\controle-acesso-PAMC
powershell -ExecutionPolicy Bypass -File .\scripts\configurar_iis.ps1
.\venv\Scripts\python.exe manage.py createsuperuser
```

Inclui: `.env`, unlock, `web.config`, permissões, app pool, porta 3000, firewall, migrate, collectstatic, **tarefa de update 00:00 (SYSTEM)**, `iisreset`, teste HTTP.

Verificar sem alterar: `-SomenteVerificar`

Teste: **http://localhost:3000/login/**

Se configurou o nome da unidade: **http://&lt;sigla&gt;.local/login/**

### D — Runner GitHub (deploy no `git push`)

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\instalar_runner_github.ps1
```

Pede **nome da unidade** (`pamc`, `cpbv`, …) e **token** ([gerar no GitHub](https://github.com/A-Assuncao/controle-acesso-PAMC/settings/actions/runners/new), válido ~1 h).

Unidade **nova** no CI: adicione o nome em `.github/workflows/deploy-producao.yml` → `matrix.site`.

### E — Testes

```powershell
Invoke-WebRequest http://localhost:3000/login/ -UseBasicParsing
schtasks /Run /TN "ControleAcesso-AtualizacaoDiaria"
Get-Content .\logs\update.log -Tail 30
Get-Service actions.runner.*   # se instalou runner
```

### Bloco copiar/colar

```powershell
cd C:\inetpub\wwwroot
git clone https://github.com/A-Assuncao/controle-acesso-PAMC.git
cd controle-acesso-PAMC
& "C:\Python314\python.exe" -m venv venv
.\venv\Scripts\pip install -r requirements.txt
copy .env.example .env
notepad .env
# inetmgr: site controle-acesso-PAMC porta 3000

powershell -ExecutionPolicy Bypass -File .\scripts\configurar_iis.ps1
.\venv\Scripts\python.exe manage.py createsuperuser
powershell -ExecutionPolicy Bypass -File .\scripts\instalar_runner_github.ps1
```

---

## 2. Scripts — o que cada um faz

| Script | Quando usar |
|--------|-------------|
| **`configurar_iis.ps1`** | Instalação/reparo IIS + site + update diário |
| **`configurar_update_automatico.ps1`** | Só reconfigurar update (sem IIS) |
| **`instalar_runner_github.ps1`** | Deploy imediato no `git push` (opcional) |
| **`update_app.bat`** | Update manual, tarefa 00:00 ou runner |
| **`update/update.bat`** | Update manual com UAC (duplo clique) |

---

## 3. Deploy automático (GitHub Actions)

```text
git push main  →  Actions  →  runner da unidade  →  update_app.bat
```

- Workflow: `.github/workflows/deploy-producao.yml`
- Labels por unidade: `self-hosted`, `windows`, **`pamc`** / **`cpbv`** / **`cpfbv`**
- Runner: serviço **`NT AUTHORITY\SYSTEM`**
- Log no servidor: `logs\update.log`

| Mecanismo | Quando | Conta |
|-----------|--------|-------|
| GitHub Actions | Após push em `main` | SYSTEM |
| Tarefa 00:00 | Backup diário | SYSTEM |
| `update\update.bat` | Manutenção manual | Admin (UAC) |

---

## 4. Atualização no dia a dia

**Desenvolvimento:** `git push origin main` → Actions atualiza as unidades com runner.

**Servidor (manual):**

```bat
C:\inetpub\wwwroot\controle-acesso-PAMC\update_app.bat
```

**Reconfigurar IIS/update após mudança grande:**

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\configurar_iis.ps1
```

---

## 5. Problemas comuns

| Sintoma | Solução |
|---------|---------|
| Site não inicia — WAS/W3SVC parados | `Start-Service WAS; Start-Service W3SVC` ou `configurar_iis.ps1` |
| Erro **0x80070021** no web.config | `appcmd unlock` (fase A ou script) |
| Log uvicorn: **AppData / Acesso negado** | Recrie `venv` com Python global (`C:\Python314\`), não AppData |
| **502.3** / log vazio | `Get-ChildItem .\logs\uvicorn*.log`; `configurar_iis.ps1` |
| HTTP timeout na 1ª carga | Normal após `iisreset` — aguarde até 2 min |
| `no such table: core_*` | `.\venv\Scripts\python.exe manage.py migrate` |
| Update: Permission denied em `.git` | `configurar_update_automatico.ps1` |
| Runner **Queued** | Serviço `actions.runner.*` parado ou label errada |
| Token runner inválido | Gere novo token e rode `instalar_runner_github.ps1` de novo |

Logs úteis:

```powershell
Get-Content .\logs\update.log -Tail 40
Get-ChildItem .\logs\uvicorn*.log | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | Get-Content -Tail 30
Get-Content .\venv\pyvenv.cfg
```

---

## 6. Outros documentos

| Arquivo | Uso |
|---------|-----|
| **[CONFIGURACAO_AMBIENTE.md](CONFIGURACAO_AMBIENTE.md)** | Variáveis `.env`, sessão, banco |
| **[CHANGELOG.md](CHANGELOG.md)** | Histórico de versões |

O painel admin customizado (templates, CSS/JS) acompanha o código a cada `git pull`; não há passo de instalação separado.
