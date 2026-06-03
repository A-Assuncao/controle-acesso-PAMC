# Tutorial: Rodando o Projeto Django no IIS (Windows)

## Objetivo

Este guia configura o **Sistema de Controle de Acesso PAMC** no **IIS** do Windows, usando:

- ambiente virtual **`venv`** (ou `.venv`, desde que coincida com o `web.config`)
- **HttpPlatformHandler** + **uvicorn**
- **WhiteNoise** para arquivos estáticos em produção
- acesso local (`http://localhost`) e na **rede local**

> **Não inclui** túnel externo (localhost.run, ngrok, etc.).

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

Pontos críticos (já configurados no repositório):

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

```powershell
icacls "C:\inetpub\wwwroot\controle-acesso-PAMC" /grant "IIS_IUSRS:(OI)(CI)M" /T
icacls "C:\inetpub\wwwroot\controle-acesso-PAMC" /grant "IIS AppPool\controle-acesso-PAMC:(OI)(CI)M" /T
iisreset
```

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

## Checklist final

- [ ] Python 3.11/3.12 instalado
- [ ] IIS + CGI + HttpPlatformHandler
- [ ] Seções `handlers` e `httpPlatform` desbloqueadas
- [ ] `venv` criado e `pip install -r requirements.txt`
- [ ] `.env` com `DJANGO_SECRET_KEY` e `DJANGO_ALLOWED_HOSTS`
- [ ] `migrate` + **`collectstatic --noinput`**
- [ ] Pasta `logs` criada
- [ ] `web.config` com `venv\Scripts\python.exe` e **sem** `customHeaders` de Content-Type
- [ ] Default Web Site parado; site na porta 80
- [ ] Permissões IIS_IUSRS + pool
- [ ] Primeira requisição aquecida; `/login/` responde 200 ou 302

---

## Referências

- [CONFIGURACAO_AMBIENTE.md](CONFIGURACAO_AMBIENTE.md)
- [HttpPlatformHandler — Microsoft](https://www.iis.net/downloads/microsoft/httpplatformhandler)
- [WhiteNoise — documentação](http://whitenoise.evans.io/)
