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
| 7 | **Permissões** (`icacls`) | Por instalação | [passo 13](#13-permissões-de-pasta) — aviso "Testar Configurações" |
| 8 | **`migrate` + `collectstatic`** | Por instalação | [passo 10](#10-preparar-banco-estáticos-e-logs) |
| 9 | **Default Web Site parado** | Comum | Evita conflito se usar porta 80 |
| 10 | **Porta do site IIS** | Comum | Recomendado: **3000** ([passo 12](#12-configurar-o-site-no-iis)) |
| 11 | **Firewall** | Rede local | Liberar a porta escolhida ([passo 13b](#13b-firewall-rede-local)) |

### Verificação e correção automática (um comando)

Na raiz do projeto, **como Administrador**:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\configurar_iis.ps1
```

Este script **corrige e verifica** tudo de uma vez:

- `.env` (cria a partir do exemplo se faltar)
- `web.config` (caminhos desta pasta)
- Permissões IIS (pool + IIS_IUSRS)
- Porta **3000**, firewall e site iniciado
- `migrate` e `collectstatic` (se necessário)
- `iisreset` + teste HTTP

Só verificar, sem alterar nada:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\configurar_iis.ps1 -SomenteVerificar
```

Outra porta: `-Porta 8080`

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

> **Instalação nova:** rode `configurar_iis.ps1` — ele regenera o `web.config` com os caminhos corretos desta pasta.

O `web.config` **não define a porta externa** (3000). Isso é configurado no IIS pelo script unificado.

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

### Porta recomendada: **3000**

Crie o site manualmente no `inetmgr` (uma vez por servidor):

1. **Sites** → **Adicionar Site**
2. Nome: `controle-acesso-PAMC`
3. Caminho: pasta do projeto
4. Porta: `3000` (ou qualquer — o script ajusta depois)

Depois rode o script unificado — ele configura porta, permissões, firewall e reinicia o IIS:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\configurar_iis.ps1
```

### Acesso

- Local: **http://localhost:3000/login/**
- Rede: **http://SEU_IP:3000/login/**

---

## 13. Permissões de pasta

Incluídas automaticamente em `configurar_iis.ps1`. Se o inetmgr mostrar aviso de autenticação pass-through, rode o script novamente como Administrador.

> Em servidor **de domínio**, conceda **Leitura** também a `DOMINIO\NOME_DO_PC$` se necessário.

---

## 13b. Firewall (rede local)

Libere a **mesma porta do site** (ex.: 3000):

```powershell
New-NetFirewallRule -DisplayName "IIS Controle Acesso PAMC porta 3000" -Direction Inbound -Protocol TCP -LocalPort 3000 -Action Allow
```

Inclua o IP desta máquina em `DJANGO_ALLOWED_HOSTS` no `.env` (porta não entra no ALLOWED_HOSTS):

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

- Local: http://localhost:3000/login/
- Rede: http://SEU_IP:3000/login/

> Se usou outra porta, ajuste na URL. O `web.config` **não** precisa ser alterado.

A raiz `/` exige login e redireciona — use **`/login/`** para testar.

### Aquecer após deploy

Após `git pull` ou `iisreset`, abra uma vez:

```powershell
Invoke-WebRequest http://localhost:3000/login/ -UseBasicParsing -TimeoutSec 120
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

### Erro inetmgr: "não pode verificar se a conta interna tem acesso"

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\configurar_iis.ps1
```

### Erro: "Impossível conectar-se ao servidor remoto"

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\configurar_iis.ps1
```

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

### Script de diagnóstico

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\configurar_iis.ps1 -SomenteVerificar
```

---

## Checklist final — nova instalação

Marque **todos** antes de testar no navegador:

- [ ] HttpPlatformHandler instalado neste **servidor**
- [ ] `appcmd unlock` executado neste **servidor**
- [ ] Projeto clonado na pasta final (ex.: `C:\inetpub\wwwroot\controle-acesso-PAMC`)
- [ ] **`venv`** criado + `pip install -r requirements.txt`
- [ ] Site criado no **inetmgr** (uma vez)
- [ ] **`configurar_iis.ps1`** executado (faz .env, web.config, permissoes, migrate, collectstatic, porta 3000)
- [ ] `createsuperuser` (manual, se necessario)
- [ ] Sem `[ERRO]` no script — acesse `http://localhost:3000/login/`

---

## Checklist final — atualização (git pull)

- [ ] `git pull origin main`
- [ ] `pip install -r requirements.txt`
- [ ] `python manage.py migrate`
- [ ] `python manage.py collectstatic --noinput`
- [ ] `configurar_iis.ps1` (ou `-SomenteVerificar` se ja configurado)
- [ ] `iisreset` + testar `/login/`

---

## Referências

- [CONFIGURACAO_AMBIENTE.md](CONFIGURACAO_AMBIENTE.md)
- [HttpPlatformHandler — Microsoft](https://www.iis.net/downloads/microsoft/httpplatformhandler)
- [WhiteNoise — documentação](http://whitenoise.evans.io/)
