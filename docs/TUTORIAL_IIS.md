# Tutorial: Rodando o Projeto Django no IIS (Windows)

## Objetivo

Este guia configura o **Sistema de Controle de Acesso PAMC** para rodar no **IIS** do Windows, usando:

- ambiente virtual **`.venv`** gerenciado com **uv**
- **HttpPlatformHandler** + **uvicorn**
- acesso local (`http://localhost`) e na **rede local** (IP da máquina)

> **Não inclui** túnel externo (localhost.run, ngrok, etc.). Para acesso fora da rede, use VPN ou infraestrutura corporativa.

---

## Índice

1. [Pré-requisitos](#1-pré-requisitos)
2. [Instalar Python e uv](#2-instalar-python-e-uv)
3. [Instalar Git](#3-instalar-git)
4. [Ativar o IIS](#4-ativar-o-iis)
5. [Instalar HttpPlatformHandler](#5-instalar-httpplatformhandler)
6. [Desbloquear seções do IIS (obrigatório)](#6-desbloquear-seções-do-iis-obrigatório)
7. [Clonar o repositório](#7-clonar-o-repositório)
8. [Criar o ambiente `.venv` e instalar dependências](#8-criar-o-ambiente-venv-e-instalar-dependências)
9. [Configurar variáveis de ambiente (`.env`)](#9-configurar-variáveis-de-ambiente-env)
10. [Preparar banco, estáticos e pastas](#10-preparar-banco-estáticos-e-pastas)
11. [Revisar o `web.config`](#11-revisar-o-webconfig)
12. [Configurar o site no IIS](#12-configurar-o-site-no-iis)
13. [Permissões de pasta](#13-permissões-de-pasta)
14. [Testar o acesso](#14-testar-o-acesso)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. Pré-requisitos

- Windows 10/11 ou Windows Server
- PowerShell **como Administrador**
- Conta com permissão para instalar recursos do Windows e configurar o IIS

**Versão recomendada do Python:** 3.11 ou 3.12 (evite versões muito novas sem testar dependências).

---

## 2. Instalar Python e uv

### Python

1. Baixe em: https://www.python.org/downloads/windows/
2. Durante a instalação, marque **"Add Python to PATH"**
3. Verifique:

```powershell
python --version
```

### uv (gerenciador de ambiente e pacotes)

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Feche e abra o PowerShell, depois confira:

```powershell
uv --version
```

---

## 3. Instalar Git

1. Baixe em: https://git-scm.com/downloads
2. Instale com as opções padrão
3. Verifique:

```powershell
git --version
```

---

## 4. Ativar o IIS

1. Pressione `Win + R`, digite `optionalfeatures` e pressione Enter
2. Marque **Serviços de Informações da Internet**
3. Dentro dele, garanta pelo menos:
   - Console de Gerenciamento do IIS
   - Serviço World Wide Web > Recursos de Aplicativos de Desenvolvimento > **CGI**
   - Serviço World Wide Web > Recursos HTTP Comuns > Conteúdo Estático, Documento Padrão, Erros HTTP
4. Clique em OK e aguarde a instalação

Abra o Gerenciador do IIS:

```powershell
inetmgr
```

---

## 5. Instalar HttpPlatformHandler

1. Baixe em: https://www.iis.net/downloads/microsoft/httpplatformhandler
2. Instale **como Administrador**
3. Reinicie o IIS:

```powershell
iisreset
```

---

## 6. Desbloquear seções do IIS (obrigatório)

Se pular este passo, o IIS retorna o erro **0x80070021** ao ler o `web.config`:

> *Esta seção de configuração não pode ser usada nesse caminho... `system.webServer/handlers`*

Execute **como Administrador**:

```powershell
& "$env:windir\system32\inetsrv\appcmd.exe" unlock config -section:system.webServer/handlers
& "$env:windir\system32\inetsrv\appcmd.exe" unlock config -section:system.webServer/httpPlatform
iisreset
```

### Verificar se desbloqueou

```powershell
& "$env:windir\system32\inetsrv\appcmd.exe" list config -section:system.webServer/handlers /config:* | Select-String overrideMode
```

O `overrideMode` deve permitir alteração no nível do site/aplicação (não `Deny` bloqueando herança).

> **Atenção:** o passo antigo de "Editar permissões de recurso" em *Manipuladores* **não resolve** o erro 0x80070021. É necessário desbloquear a seção com `appcmd`.

---

## 7. Clonar o repositório

```powershell
cd C:\inetpub\wwwroot
git clone https://github.com/A-Assuncao/controle-acesso-PAMC.git
cd controle-acesso-PAMC
```

---

## 8. Criar o ambiente `.venv` e instalar dependências

Sempre use o ambiente virtual **`.venv`** na raiz do projeto (não `venv`).

```powershell
cd C:\inetpub\wwwroot\controle-acesso-PAMC

# Cria .venv com a versão de Python disponível
uv venv .venv

# Ativa o ambiente (obrigatório antes de comandos python/pip)
.\.venv\Scripts\Activate.ps1

# Instala dependências dentro do .venv
uv pip install -r requirements.txt
```

Confirme que o Python do IIS será o do `.venv`:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -c "import django; print(django.get_version())"
```

Se `Activate.ps1` for bloqueado:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

---

## 9. Configurar variáveis de ambiente (`.env`)

```powershell
copy .env.example .env
notepad .env
```

Exemplo mínimo para produção no IIS:

```env
DJANGO_SECRET_KEY=sua-chave-fixa-gerada-com-manage-py-check-secret-key
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,SEU_IP_LOCAL
SERVE_STATIC_FILES=True
```

Gere uma chave segura:

```powershell
.\.venv\Scripts\Activate.ps1
python manage.py check_secret_key --generate
```

Copie a chave gerada para `DJANGO_SECRET_KEY` no `.env`.

Mais detalhes: [CONFIGURACAO_AMBIENTE.md](CONFIGURACAO_AMBIENTE.md)

---

## 10. Preparar banco, estáticos e pastas

Com o `.venv` ativado:

```powershell
cd C:\inetpub\wwwroot\controle-acesso-PAMC
.\.venv\Scripts\Activate.ps1

python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

Crie a pasta de logs usada pelo IIS/uvicorn:

```powershell
New-Item -ItemType Directory -Force -Path .\logs
```

---

## 11. Revisar o `web.config`

O arquivo `web.config` na raiz do projeto deve apontar para o Python do **`.venv`**.

Verifique esta linha (ajuste o caminho se o projeto não estiver em `C:\inetpub\wwwroot\...`):

```xml
<httpPlatform processPath="C:\inetpub\wwwroot\controle-acesso-PAMC\.venv\Scripts\python.exe"
              arguments="-m uvicorn controle_acesso.asgi:application --host 0.0.0.0 --port %HTTP_PLATFORM_PORT%"
              ...>
```

Variáveis importantes já presentes:

- `DJANGO_SETTINGS_MODULE=controle_acesso.settings`
- `PYTHONPATH` apontando para a raiz do projeto

As demais configurações (SECRET_KEY, DEBUG, ALLOWED_HOSTS) vêm do arquivo **`.env`**.

---

## 12. Configurar o site no IIS

1. Abra `inetmgr`
2. Clique com o botão direito em **Sites** → **Adicionar Site**
3. Preencha:
   - **Nome:** `controle-acesso-PAMC`
   - **Caminho físico:** `C:\inetpub\wwwroot\controle-acesso-PAMC`
   - **Porta:** `80`
4. Confirme

### Pool de aplicativos

1. Vá em **Pools de Aplicativos** → selecione o pool do site
2. **Configurações Avançadas:**
   - **Versão do .NET CLR:** `Sem código gerenciado`
   - **Modo de pipeline gerenciado:** `Integrado`
3. **Identidade:** `ApplicationPoolIdentity` (padrão)

---

## 13. Permissões de pasta

O pool do IIS precisa ler/escrever no projeto (banco SQLite, logs, etc.).

```powershell
icacls "C:\inetpub\wwwroot\controle-acesso-PAMC" /grant "IIS_IUSRS:(OI)(CI)M" /T
icacls "C:\inetpub\wwwroot\controle-acesso-PAMC" /grant "IIS AppPool\controle-acesso-PAMC:(OI)(CI)M" /T
```

> Substitua `controle-acesso-PAMC` pelo nome exato do pool, se for diferente.

---

## 14. Testar o acesso

### Local

- http://localhost
- http://127.0.0.1

### Rede local

Descubra o IP:

```powershell
ipconfig
```

Acesse de outro dispositivo na mesma rede:

- `http://192.168.x.x` (use o IP real da máquina)

Certifique-se de incluir esse IP em `DJANGO_ALLOWED_HOSTS` no `.env`.

---

## 15. Troubleshooting

### Erro 0x80070021 — seção `handlers` bloqueada

**Causa:** seção `system.webServer/handlers` bloqueada no IIS.

**Solução:** repita o [passo 6](#6-desbloquear-seções-do-iis-obrigatório) como Administrador e reinicie o IIS.

---

### Erro 500 — aplicação não sobe

1. Verifique o log do uvicorn:

```powershell
Get-Content C:\inetpub\wwwroot\controle-acesso-PAMC\logs\uvicorn.log -Tail 50
```

2. Confirme o Python do `.venv`:

```powershell
Test-Path C:\inetpub\wwwroot\controle-acesso-PAMC\.venv\Scripts\python.exe
```

3. Teste manualmente (com `.venv` ativado):

```powershell
cd C:\inetpub\wwwroot\controle-acesso-PAMC
.\.venv\Scripts\Activate.ps1
python manage.py check
python -m uvicorn controle_acesso.asgi:application --host 127.0.0.1 --port 8000
```

Se funcionar na porta 8000 mas não no IIS, o problema está no IIS/`web.config`/permissões.

---

### `ModuleNotFoundError` (django, pytz, etc.)

Dependências não foram instaladas **dentro do `.venv`**:

```powershell
cd C:\inetpub\wwwroot\controle-acesso-PAMC
.\.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt
```

---

### HTTP 502.3 — Bad Gateway

- HttpPlatformHandler não instalado ou IIS não reiniciado após instalação
- Caminho errado em `processPath` no `web.config` (deve ser `.venv\Scripts\python.exe`)
- `startupTimeLimit` insuficiente (aumente para 60 no `web.config` se o servidor for lento)

---

### Página sem CSS / arquivos estáticos

```powershell
.\.venv\Scripts\Activate.ps1
python manage.py collectstatic --noinput
```

Confirme `SERVE_STATIC_FILES=True` no `.env` (ou `whitenoise` configurado).

---

## Checklist final

- [ ] Python 3.11+ instalado
- [ ] uv instalado
- [ ] IIS + CGI ativados
- [ ] HttpPlatformHandler instalado
- [ ] Seções `handlers` e `httpPlatform` desbloqueadas (`appcmd unlock`)
- [ ] Repositório clonado em `C:\inetpub\wwwroot\controle-acesso-PAMC`
- [ ] Ambiente **`.venv`** criado com `uv venv .venv`
- [ ] Dependências instaladas com `uv pip install -r requirements.txt`
- [ ] Arquivo `.env` configurado
- [ ] `migrate` e `collectstatic` executados
- [ ] `web.config` apontando para `.venv\Scripts\python.exe`
- [ ] Site criado no IIS na porta 80
- [ ] Permissões concedidas a `IIS_IUSRS` e ao pool
- [ ] Acesso local e na rede funcionando

---

## Referências

- [CONFIGURACAO_AMBIENTE.md](CONFIGURACAO_AMBIENTE.md)
- [GUIA_INSTALACAO_ADMIN.md](GUIA_INSTALACAO_ADMIN.md)
- [HttpPlatformHandler — Microsoft](https://www.iis.net/downloads/microsoft/httpplatformhandler)
