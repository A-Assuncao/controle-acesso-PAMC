# Configura e verifica o deploy IIS do Controle de Acesso PAMC.
# Compativel com Windows PowerShell 5.1+
#
# Uso (PowerShell como Administrador, na raiz do projeto):
#   powershell -ExecutionPolicy Bypass -File .\scripts\configurar_iis.ps1
#   powershell -ExecutionPolicy Bypass -File .\scripts\configurar_iis.ps1 -SomenteVerificar
#   powershell -ExecutionPolicy Bypass -File .\scripts\configurar_iis.ps1 -Porta 3000

param(
    [int]$Porta = 3000,
    [string]$NomeSite = "controle-acesso-PAMC",
    [switch]$SomenteVerificar
)

$ErrorActionPreference = "Continue"
$script:erros = 0
$script:avisos = 0
$script:correcoes = 0

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pythonExe = Join-Path $projectRoot "venv\Scripts\python.exe"
$nomePool = $NomeSite
$identidadePool = "IIS AppPool\$nomePool"

function Ok([string]$msg) { Write-Host "[OK]    $msg" -ForegroundColor Green }
function Warn([string]$msg) { Write-Host "[AVISO] $msg" -ForegroundColor Yellow; $script:avisos++ }
function Fail([string]$msg) { Write-Host "[ERRO]  $msg" -ForegroundColor Red; $script:erros++ }
function Fix([string]$msg) { Write-Host "[FIX]   $msg" -ForegroundColor Cyan; $script:correcoes++ }
function Step([string]$msg) {
    Write-Host ""
    Write-Host "=== $msg ===" -ForegroundColor Cyan
}

function Update-WebConfig {
    if (-not (Test-Path $pythonExe)) {
        Warn "web.config nao atualizado - venv ausente"
        return
    }

    New-Item -ItemType Directory -Force -Path (Join-Path $projectRoot "logs") | Out-Null
    $logFile = Join-Path $projectRoot "logs\uvicorn.log"
    $webConfigPath = Join-Path $projectRoot "web.config"

    $xml = @"
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <system.webServer>
    <handlers>
      <add name="httpPlatformHandler" path="*" verb="*" modules="httpPlatformHandler" resourceType="Unspecified" requireAccess="Script" />
    </handlers>
    <httpPlatform processPath="$pythonExe"
                  arguments="-m uvicorn controle_acesso.asgi:application --host 127.0.0.1 --port %HTTP_PLATFORM_PORT% --timeout-keep-alive 120 --log-level info"
                  startupTimeLimit="120"
                  requestTimeout="00:04:00"
                  stdoutLogEnabled="true"
                  stdoutLogFile="$logFile">
      <environmentVariables>
        <environmentVariable name="DJANGO_SETTINGS_MODULE" value="controle_acesso.settings" />
        <environmentVariable name="PYTHONPATH" value="$projectRoot" />
        <environmentVariable name="PYTHONIOENCODING" value="utf-8" />
        <environmentVariable name="PYTHONUTF8" value="1" />
      </environmentVariables>
    </httpPlatform>
  </system.webServer>
</configuration>
"@

    Set-Content -Path $webConfigPath -Value $xml -Encoding UTF8
    Fix "web.config regenerado para esta pasta"
}

function Set-PermissoesIIS {
    icacls $projectRoot /grant "IIS_IUSRS:(OI)(CI)RX" /T | Out-Null
    icacls $projectRoot /grant "${identidadePool}:(OI)(CI)RX" /T | Out-Null

    foreach ($pasta in @("logs", "media")) {
        $caminho = Join-Path $projectRoot $pasta
        New-Item -ItemType Directory -Force -Path $caminho | Out-Null
        icacls $caminho /grant "${identidadePool}:(OI)(CI)M" /T | Out-Null
    }

    icacls $projectRoot /grant "${identidadePool}:(CI)M" | Out-Null

    $dbFile = Join-Path $projectRoot "db.sqlite3"
    if (Test-Path $dbFile) {
        icacls $dbFile /grant "${identidadePool}:M" | Out-Null
    }

    Fix "Permissoes IIS aplicadas para $identidadePool"
}

function Set-PortaSite {
    param([int]$PortaDestino)

    Import-Module WebAdministration -ErrorAction Stop

    $site = Get-Website -Name $NomeSite -ErrorAction SilentlyContinue
    if (-not $site) {
        Warn "Site $NomeSite nao encontrado - crie manualmente no inetmgr"
        return
    }

    $bindingAtual = $site.bindings.Collection | Where-Object {
        $_.protocol -eq "http" -and $_.bindingInformation -like "*:${PortaDestino}:*"
    }

    if (-not $bindingAtual) {
        $site.bindings.Collection | Where-Object { $_.protocol -eq "http" } | ForEach-Object {
            Remove-WebBinding -Name $NomeSite -BindingInformation $_.bindingInformation
        }
        New-WebBinding -Name $NomeSite -Protocol http -Port $PortaDestino -IPAddress "*"
        Fix "Binding HTTP configurado na porta $PortaDestino"
    }

    Start-Service W3SVC -ErrorAction SilentlyContinue
    if ((Get-Website -Name $NomeSite).State -ne "Started") {
        Start-Website -Name $NomeSite
        Fix "Site $NomeSite iniciado"
    }

    $regra = "IIS Controle Acesso PAMC porta $PortaDestino"
    if (-not (Get-NetFirewallRule -DisplayName $regra -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule -DisplayName $regra -Direction Inbound -Protocol TCP -LocalPort $PortaDestino -Action Allow | Out-Null
        Fix "Firewall liberado na porta $PortaDestino"
    }
}

function Invoke-DjangoSetup {
    if (-not (Test-Path $pythonExe)) { return }

    Push-Location $projectRoot

    $dbFile = Join-Path $projectRoot "db.sqlite3"
    if (-not (Test-Path $dbFile)) {
        & $pythonExe manage.py migrate --noinput 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { Fix "migrate executado - db.sqlite3 criado" }
    }

    $staticDir = Join-Path $projectRoot "staticfiles"
    if (-not ((Test-Path $staticDir) -and (Get-ChildItem $staticDir -ErrorAction SilentlyContinue))) {
        & $pythonExe manage.py collectstatic --noinput 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { Fix "collectstatic executado" }
    }

    Pop-Location
}

function Invoke-Verificacao {
    param([int]$PortaDestino)

    Step "Verificacao"

    if (Test-Path $pythonExe) {
        Ok "venv\Scripts\python.exe existe"
    } else {
        Fail "venv ausente - rode: python -m venv venv; pip install -r requirements.txt"
    }

    $envFile = Join-Path $projectRoot ".env"
    if (Test-Path $envFile) { Ok ".env existe" }
    else { Fail ".env ausente - sera criado na proxima execucao sem -SomenteVerificar" }

    $webConfig = Join-Path $projectRoot "web.config"
    if (Test-Path $webConfig) {
        $content = Get-Content $webConfig -Raw
        if ($content -match [regex]::Escape($projectRoot)) { Ok "web.config aponta para esta pasta" }
        else { Fail "web.config com caminhos errados - rode sem -SomenteVerificar para corrigir" }
        if ($content -match "customHeaders") { Fail "web.config tem customHeaders invalidos" }
    } else {
        Fail "web.config ausente"
    }

    if (Test-Path (Join-Path $projectRoot "logs")) { Ok "pasta logs existe" }
    else { Warn "pasta logs ausente" }

    if (Test-Path (Join-Path $projectRoot "db.sqlite3")) { Ok "db.sqlite3 existe" }
    else { Warn "db.sqlite3 ausente - migrate sera executado na correcao automatica" }

    $staticDir = Join-Path $projectRoot "staticfiles"
    if ((Test-Path $staticDir) -and (Get-ChildItem $staticDir -ErrorAction SilentlyContinue)) {
        Ok "staticfiles populado"
    } else {
        Warn "staticfiles vazio - collectstatic sera executado na correcao automatica"
    }

    try {
        Import-Module WebAdministration -ErrorAction Stop
        $handler = Get-WebGlobalModule -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "*Platform*" }
        if ($handler) { Ok "HttpPlatformHandler instalado" }
        else { Fail "HttpPlatformHandler NAO instalado - baixe em iis.net/downloads/microsoft/httpplatformhandler" }

        $site = Get-Website -Name $NomeSite -ErrorAction SilentlyContinue
        if ($site) {
            if ($site.State -eq "Started") { Ok "Site $NomeSite Started" }
            else { Fail "Site $NomeSite esta $($site.State)" }

            $bindings = $site.bindings.Collection | ForEach-Object { $_.bindingInformation }
            Ok "Bindings: $($bindings -join ', ')"

            if ($site.PhysicalPath.TrimEnd('\') -ne $projectRoot.TrimEnd('\')) {
                Fail "Caminho fisico IIS difere da pasta do projeto"
            }
        } else {
            Fail "Site $NomeSite nao existe no IIS - crie no inetmgr"
        }

        if ((Get-Service W3SVC -ErrorAction SilentlyContinue).Status -eq "Running") {
            Ok "Servico W3SVC em execucao"
        } else {
            Fail "Servico W3SVC parado"
        }

        if (Get-NetTCPConnection -LocalPort $PortaDestino -State Listen -ErrorAction SilentlyContinue) {
            Ok "Porta $PortaDestino em escuta"
        } else {
            Fail "Porta $PortaDestino nao esta em escuta"
        }
    } catch {
        Warn "Nao foi possivel verificar IIS - execute como Administrador"
    }

    if (Test-Path $pythonExe) {
        Push-Location $projectRoot
        & $pythonExe manage.py check 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { Ok "python manage.py check passou" }
        else { Fail "python manage.py check falhou" }
        Pop-Location
    }

    $urlTeste = "http://127.0.0.1:${PortaDestino}/login/"
    try {
        $response = Invoke-WebRequest $urlTeste -UseBasicParsing -TimeoutSec 120 -ErrorAction Stop
        Ok "HTTP respondeu $($response.StatusCode) em $urlTeste"
    } catch {
        $msgErro = $_.Exception.Message
        if ($msgErro -match "timed out") {
            Fail "HTTP timeout em 120s - veja logs\uvicorn.log"
        } elseif ($msgErro -match "502") {
            Fail "HTTP 502 - Python nao subiu - veja logs\uvicorn.log"
        } elseif ($msgErro -match "conectar|connect") {
            Fail "HTTP recusado na porta $PortaDestino"
        } else {
            Warn "HTTP falhou: $msgErro"
        }
    }

    $uvicornLog = Join-Path $projectRoot "logs\uvicorn.log"
    if (Test-Path $uvicornLog) {
        $tail = Get-Content $uvicornLog -Tail 5 -ErrorAction SilentlyContinue
        if ($tail) {
            Write-Host ""
            Write-Host "--- logs\uvicorn.log ---" -ForegroundColor DarkGray
            $tail | ForEach-Object { Write-Host $_ -ForegroundColor DarkGray }
        }
    }
}

Write-Host ""
Write-Host "Controle de Acesso PAMC - Configurador IIS" -ForegroundColor White
Write-Host "Pasta: $projectRoot | Porta: $Porta | Site: $NomeSite" -ForegroundColor DarkGray

if (-not $SomenteVerificar) {
    Step "Correcao automatica"

    if (-not (Test-Path (Join-Path $projectRoot ".env"))) {
        $example = Join-Path $projectRoot ".env.example"
        if (Test-Path $example) {
            Copy-Item $example (Join-Path $projectRoot ".env")
            Fix ".env criado a partir de .env.example - edite DJANGO_SECRET_KEY e ALLOWED_HOSTS"
        } else {
            Warn ".env.example nao encontrado"
        }
    }

    Update-WebConfig
    Set-PermissoesIIS
    Set-PortaSite -PortaDestino $Porta
    Invoke-DjangoSetup

    if ($script:correcoes -gt 0) {
        Write-Host ""
        Fix "Reiniciando IIS - $script:correcoes correcoes aplicadas"
        iisreset | Out-Null
        Start-Sleep -Seconds 5
    }
} else {
    Write-Host ""
    Write-Host "Modo somente verificacao -SomenteVerificar" -ForegroundColor DarkGray
}

Invoke-Verificacao -PortaDestino $Porta

Write-Host ""
if ($script:erros -eq 0 -and $script:avisos -eq 0) {
    Write-Host "Instalacao OK. Acesse: http://localhost:${Porta}/login/" -ForegroundColor Green
} elseif ($script:erros -eq 0) {
    Write-Host "$script:avisos aviso(s). Acesse: http://localhost:${Porta}/login/" -ForegroundColor Yellow
} else {
    Write-Host "$script:erros erro(s), $script:avisos aviso(s). Corrija os itens ERRO acima." -ForegroundColor Red
    Write-Host "Itens manuais: HttpPlatformHandler, criar site no inetmgr, python -m venv venv" -ForegroundColor DarkGray
}
Write-Host ""

exit $script:erros
