# Tutorial: Rodando o Projeto Django no IIS (Windows)

## Objetivo

Este guia configura o **Sistema de Controle de Acesso PAMC** no **IIS** do Windows, usando:

- ambiente virtual **`venv`** (ou `.venv`, desde que coincida com o `web.config`)
- **HttpPlatformHandler** + **uvicorn**
- **WhiteNoise** para arquivos estáticos em produção
- acesso local (`http://localhost`) e na **rede local**

> **Não inclui** túnel externo (localhost.run, ngrok, etc.).

---

## ⚠️ Instalação em servidor ou pasta NOVA

Se funciona em **outro local** mas **não neste**, quase sempre falta um destes itens — **não vêm do Git**:

| # | Item | Esquecido? | Como resolver |
|---|------|------------|---------------|
| 1 | **HttpPlatformHandler** | Por servidor | Instalar MSI + `iisreset` ([passo 5](#5-instalar-httpplatformhandler)) |
| 2 | **Desbloqueio IIS** (`appcmd unlock`) | Por servidor | [passo 6](#6-desbloquear-seções-do-iis-obrigatório) |
| 3 | **`venv` + dependências** | Sempre | [passo 8](#8-criar-o-venv-e-instalar-dependências) |
| 4 | **Arquivo `.env`** | **Muito comum** | `copy .env.example .env` — **não está no repositório** |
| 5 | **Caminhos no `web.config`** | **Muito comum** | Caminhos absolutos apontam para `C:\inetpub\...` — se a pasta for outra, **não funciona** |
| 6 | **Site criado no IIS** | Por instalação | [passo 12](#12-configurar-o-site-no-iis) |
| 7 | **Permissões** (`icacls`) | Por instalação | [passo 13](#13-permissões-de-pasta) |
| 8 | **`migrate` + `collectstatic`** | Por instalação | [passo 10](#10-preparar-banco-estáticos-e-logs) |
| 9 | **Default Web Site parado** | Comum | Pare o site padrão na porta 80 |
| 10 | **Firewall porta 80** | Rede local | [passo 13b](#13b-firewall-rede-local) |

### Verificação automática (rode no servidor novo)

Na raiz do projeto, **como Administrador**:

```powershell
cd C:\inetpub\wwwroot\controle-acesso-PAMC   # ou sua pasta real
powershell -ExecutionPolicy Bypass -File .\scripts\verificar_instalacao_iis.ps1
```

O script lista `[OK]`, `[AVISO]` e `[ERRO]` para cada item.

### Corrigir caminhos do `web.config` automaticamente

Se o projeto **não** está em `C:\inetpub\wwwroot\controle-acesso-PAMC`:

```powershell
cd D:\caminho\real\controle-acesso-PAMC
powershell -ExecutionPolicy Bypass -File .\scripts\atualizar_web_config.ps1
iisreset
```

---

## Índice

1. [Pré-requisitos](#1-pré-requisitos)
2. [Instalar Python](#2-instalar-python)
3. [Instalar Git](#3-instalar-git)
4. [Ativar o IIS](#4-ativar-o-iis)
5. [Instalar HttpPlatformHandler](#5-instalar-httpplatformhandler)
6. [Desbloquear seções do IIS (obrigatório)](#6-desbloquear-seções-do-iis-obrigatório)
7. [Clonar o repositório](#7-clonar-o-repositório)
8. [Criar o `venv` e instalar dependências](#8-criar-o-venv-e-instalar-dependências)
9. [Configurar `.env`](#9-configurar-env)
10. [Preparar banco, estáticos e logs](#10-preparar-banco-estáticos-e-logs)
11. [Revisar o `web.config`](#11-revisar-o-webconfig)
12. [Configurar o site no IIS](#12-configurar-o-site-no-iis)
13. [Permissões de pasta](#13-permissões-de-pasta)
14. [Testar e aquecer a aplicação](#14-testar-e-aquecer-a-aplicação)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. Pré-requisitos

- Windows 10/11 ou Windows Server
- PowerShell **como Administrador**
- **Python 3.11 ou 3.12** (evite 3.14+ em produção até validar dependências)

---

## 2. Instalar Python

1. Baixe em: https://www.python.org/downloads/windows/
2. Marque **"Add Python to PATH"**
3. Verifique:

```powershell
python --version
```

Opcional — **uv** acelera instalação de pacotes:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

## 3. Instalar Git

```powershell
git --version
```

---

## 4. Ativar o IIS

1. `Win + R` → `optionalfeatures`
2. Marque **Serviços de Informações da Internet**
3. Garanta:
   - Console de Gerenciamento do IIS
   - World Wide Web > Desenvolvimento de Aplicativos > **CGI**
   - World Wide Web > HTTP Comuns > Conteúdo Estático, Documento Padrão
4. **Pare o "Default Web Site"** se existir (evita conflito na porta 80)

---

## 5. Instalar HttpPlatformHandler

1. https://www.iis.net/downloads/microsoft/httpplatformhandler
2. Instale como Administrador
3. `iisreset`

---

## 6. Desbloquear seções do IIS (obrigatório)

Sem este passo → erro **0x80070021** no `web.config`.

```powershell
& "$env:windir\system32\inetsrv\appcmd.exe" unlock config -section:system.webServer/handlers
& "$env:windir\system32\inetsrv\appcmd.exe" unlock config -section:system.webServer/httpPlatform
iisreset
```

> Editar permissões em *Manipuladores* **não resolve** o 0x80070021.

---

## 7. Clonar o repositório

```powershell
cd C:\inetpub\wwwroot
git clone https://github.com/A-Assuncao/controle-acesso-PAMC.git
cd controle-acesso-PAMC
```

---

## 8. Criar o `venv` e instalar dependências

O `web.config` do repositório aponta para **`venv`** (não `.venv`). Use o mesmo nome.

```powershell
cd C:\inetpub\wwwroot\controle-acesso-PAMC

python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Confirme:

```powershell
Test-Path .\venv\Scripts\python.exe   # deve retornar True
python manage.py check
```

Se `Activate.ps1` for bloqueado:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

---

## 9. Configurar `.env`

```powershell
copy .env.example .env
notepad .env
```

Exemplo para IIS:

```env
DJANGO_SECRET_KEY=sua-chave-fixa-aqui
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,SEU_IP_LOCAL
SERVE_STATIC_FILES=True
```

Gere a chave:

```powershell
.\venv\Scripts\Activate.ps1
python manage.py check_secret_key --generate
```

---

## 10. Preparar banco, estáticos e logs

```powershell
cd C:\inetpub\wwwroot\controle-acesso-PAMC
.\venv\Scripts\Activate.ps1

python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser

New-Item -ItemType Directory -Force -Path .\logs
```

**`collectstatic` é obrigatório** — sem ele, páginas carregam sem CSS/JS em produção.

---

## 11. Revisar o `web.config`

> **Instalação nova:** os caminhos no `web.config` do Git são de **exemplo** (`C:\inetpub\wwwroot\...`). Se sua pasta for diferente, o IIS **não acha o Python** e a página fica em branco ou dá timeout.

**Forma recomendada** — regenere com o script (usa a pasta atual automaticamente):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\atualizar_web_config.ps1
```

**Ou edite manualmente** estas 3 linhas para a **pasta real** deste servidor:

| Campo | Deve apontar para |
|-------|-------------------|
| `processPath` | `SUA_PASTA\venv\Scripts\python.exe` |
| `stdoutLogFile` | `SUA_PASTA\logs\uvicorn.log` |
| `PYTHONPATH` | `SUA_PASTA` (raiz do projeto) |

Pontos críticos:

| Item | Valor correto |
|------|---------------|
| `processPath` | `...\venv\Scripts\python.exe` (mesmo nome da pasta do ambiente) |
| `stdoutLogFile` | caminho **absoluto** para `logs\uvicorn.log` |
| `startupTimeLimit` | `120` (segundos para o Django subir na 1ª requisição) |
| **Não usar** | `<customHeaders>` forçando `Content-Type: text/html` — quebra JS/CSS |

O trecho principal deve ser semelhante a:

```xml
<httpPlatform processPath="C:\inetpub\wwwroot\controle-acesso-PAMC\venv\Scripts\python.exe"
              arguments="-m uvicorn controle_acesso.asgi:application --host 127.0.0.1 --port %HTTP_PLATFORM_PORT% --timeout-keep-alive 120"
              startupTimeLimit="120"
              requestTimeout="00:04:00"
              stdoutLogEnabled="true"
              stdoutLogFile="C:\inetpub\wwwroot\controle-acesso-PAMC\logs\uvicorn.log">
```

Variáveis sensíveis vêm do **`.env`**, não do XML.

---

## 12. Configurar o site no IIS

1. `inetmgr` → **Sites** → **Adicionar Site**
2. Nome: `controle-acesso-PAMC`
3. Caminho: `C:\inetpub\wwwroot\controle-acesso-PAMC`
4. Porta: `80`
5. Pool: **Sem código gerenciado**, pipeline **Integrado**
6. **Pare** o *Default Web Site* se ainda estiver na porta 80

---

## 13. Permissões de pasta

Substitua o caminho se o projeto **não** estiver em `C:\inetpub\wwwroot\controle-acesso-PAMC`:

```powershell
$Pasta = "C:\inetpub\wwwroot\controle-acesso-PAMC"   # ajuste aqui
$Pool  = "controle-acesso-PAMC"                       # nome do pool no IIS

icacls $Pasta /grant "IIS_IUSRS:(OI)(CI)M" /T
icacls $Pasta /grant "IIS AppPool\${Pool}:(OI)(CI)M" /T
iisreset
```

Confira o nome do pool em `inetmgr` → **Pools de Aplicativos** (deve coincidir com `$Pool`).

---

## 13b. Firewall (rede local)

Para acessar de **outros computadores** na rede, libere a porta 80:

```powershell
New-NetFirewallRule -DisplayName "IIS Controle Acesso PAMC" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow
```

Inclua o IP desta máquina em `DJANGO_ALLOWED_HOSTS` no `.env`:

```powershell
ipconfig
# Ex.: DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.50
```

> Acesso só em `localhost` no próprio servidor **não precisa** abrir firewall.

---

## 14. Testar e aquecer a aplicação

### Comportamento normal

A **primeira requisição após `iisreset`** pode demorar **30–120 segundos** — o IIS inicia o processo Python + Django + uvicorn. Isso **não é travamento**; aguarde ou veja o log:

```powershell
Get-Content C:\inetpub\wwwroot\controle-acesso-PAMC\logs\uvicorn.log -Wait -Tail 20
```

### Teste rápido (PowerShell)

```powershell
# Deve retornar StatusCode 200 ou 302 (redirect para login)
Invoke-WebRequest http://localhost -UseBasicParsing | Select-Object StatusCode, StatusDescription
```

- **302** → redirecionou para `/login/` (esperado se não autenticado)
- **200** → página ok
- **502** → Python não subiu (veja uvicorn.log)
- **Timeout** → processPath errado ou startupTimeLimit baixo

### URLs

- Local: http://localhost/login/
- Rede: http://SEU_IP/login/

A raiz `/` exige login e redireciona — use **`/login/`** para testar.

### Aquecer após deploy

Após `git pull` ou `iisreset`, abra uma vez:

```powershell
Invoke-WebRequest http://localhost/login/ -UseBasicParsing
```

Só então teste no navegador.

---

## 15. Troubleshooting

### Página em branco ou “carregando” por muito tempo

| Causa | Como verificar | Solução |
|-------|----------------|---------|
| **1ª requisição / cold start** | `uvicorn.log` vazio por ~1 min, depois preenche | Aguarde até 120s; aumente `startupTimeLimit` |
| **`processPath` errado** | `Test-Path .\venv\Scripts\python.exe` → False | Crie `venv` ou ajuste `web.config` |
| **Header `Content-Type` no web.config** | XML com `<customHeaders>` forçando `text/html` | **Remova** o bloco `httpProtocol/customHeaders` |
| **Estáticos não coletados** | CSS/JS 404 no DevTools (F12) | `python manage.py collectstatic --noinput` |
| **WhiteNoise desativado** | `/static/` retorna 404 com `DEBUG=False` | Atualize o código (`whitenoise` no middleware) |
| **Default Web Site na porta 80** | Aparece página padrão do IIS | Pare o site padrão |
| **CDN bloqueada (rede fechada)** | Login lento; fontes do Google não carregam | Normal em rede isolada; aguarde ou use rede com internet na 1ª carga |

### Erro 0x80070021

Repita o [passo 6](#6-desbloquear-seções-do-iis-obrigatório).

### Erro 502.3

```powershell
Get-Content C:\inetpub\wwwroot\controle-acesso-PAMC\logs\uvicorn.log -Tail 50
Test-Path C:\inetpub\wwwroot\controle-acesso-PAMC\venv\Scripts\python.exe
```

Teste manual:

```powershell
.\venv\Scripts\Activate.ps1
python -m uvicorn controle_acesso.asgi:application --host 127.0.0.1 --port 8000
```

Se **8000 funciona** e **80 não** → IIS/`web.config`/permissões.

### Script de diagnóstico completo

Use o script automatizado (recomendado):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verificar_instalacao_iis.ps1
```

Ou manualmente:

```powershell
cd C:\inetpub\wwwroot\controle-acesso-PAMC

Write-Host "=== Python ===" -ForegroundColor Cyan
Test-Path .\venv\Scripts\python.exe

Write-Host "=== Logs ===" -ForegroundColor Cyan
Get-Content .\logs\uvicorn.log -Tail 15 -ErrorAction SilentlyContinue
Get-Content .\logs\django_errors.log -Tail 10 -ErrorAction SilentlyContinue

Write-Host "=== IIS ===" -ForegroundColor Cyan
Import-Module WebAdministration
Get-Website -Name "controle-acesso-PAMC" | Format-Table Name, State
Get-WebAppPoolState -Name "controle-acesso-PAMC"

Write-Host "=== HTTP ===" -ForegroundColor Cyan
try {
    $r = Invoke-WebRequest http://localhost/login/ -UseBasicParsing -TimeoutSec 180
    Write-Host "Status:" $r.StatusCode
} catch {
    Write-Host "Erro:" $_.Exception.Message
}
```

---

## Checklist final — nova instalação

Marque **todos** antes de testar no navegador:

- [ ] HttpPlatformHandler instalado neste **servidor**
- [ ] `appcmd unlock` executado neste **servidor**
- [ ] Projeto clonado na pasta final (ex.: `C:\inetpub\wwwroot\controle-acesso-PAMC`)
- [ ] **`venv`** criado + `pip install -r requirements.txt`
- [ ] **`.env`** criado (`copy .env.example .env`) — **não vem do Git**
- [ ] **`web.config`** com caminhos desta pasta (`atualizar_web_config.ps1`)
- [ ] `migrate` + `collectstatic --noinput` + `createsuperuser`
- [ ] Pasta **`logs`** criada
- [ ] **Site IIS** apontando para a pasta correta, porta 80
- [ ] **Default Web Site** parado
- [ ] **Permissões** `IIS_IUSRS` + pool (`icacls`)
- [ ] **Firewall** porta 80 (se acesso na rede)
- [ ] `verificar_instalacao_iis.ps1` sem `[ERRO]`
- [ ] `iisreset` + aguardar até 120s + testar `http://localhost/login/`

---

## Checklist final — atualização (git pull)

- [ ] `git pull origin main`
- [ ] `pip install -r requirements.txt`
- [ ] `python manage.py migrate`
- [ ] `python manage.py collectstatic --noinput`
- [ ] Se mudou de pasta: `atualizar_web_config.ps1`
- [ ] `iisreset` + testar `/login/`

---

## Referências

- [CONFIGURACAO_AMBIENTE.md](CONFIGURACAO_AMBIENTE.md)
- [HttpPlatformHandler — Microsoft](https://www.iis.net/downloads/microsoft/httpplatformhandler)
- [WhiteNoise — documentação](http://whitenoise.evans.io/)
