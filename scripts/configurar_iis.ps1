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

    # Padrao Microsoft Learn + Lex Li (HttpPlatformHandler + uvicorn ASGI)
    # https://learn.microsoft.com/pt-br/visualstudio/python/configure-web-apps-for-iis-windows
    $xml = @"
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <system.webServer>
    <handlers>
      <add name="httpPlatformHandler" path="*" verb="*" modules="httpPlatformHandler" resourceType="Unspecified" requireAccess="Script" />
    </handlers>
    <httpPlatform processPath="$pythonExe"
                  arguments="-m uvicorn controle_acesso.asgi:application --port %HTTP_PLATFORM_PORT%"
                  startupTimeLimit="120"
                  requestTimeout="00:04:00"
                  processesPerApplication="1"
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

    # venv inteiro: ApplicationPoolIdentity precisa executar python + DLLs (forum Django/IIS)
    $venvDir = Join-Path $projectRoot "venv"
    if (Test-Path $venvDir) {
        icacls $venvDir /grant "IIS_IUSRS:(OI)(CI)RX" /T | Out-Null
        icacls $venvDir /grant "${identidadePool}:(OI)(CI)RX" /T | Out-Null
    }

    foreach ($pasta in @("logs", "media")) {
        $caminho = Join-Path $projectRoot $pasta
        New-Item -ItemType Directory -Force -Path $caminho | Out-Null
        icacls $caminho /grant "IIS_IUSRS:(OI)(CI)M" /T | Out-Null
        icacls $caminho /grant "${identidadePool}:(OI)(CI)M" /T | Out-Null
    }

    icacls $projectRoot /grant "${identidadePool}:(CI)M" | Out-Null

    $dbFile = Join-Path $projectRoot "db.sqlite3"
    if (Test-Path $dbFile) {
        icacls $dbFile /grant "${identidadePool}:M" | Out-Null
    }

    Fix "Permissoes IIS aplicadas para $identidadePool"
}

function Unlock-IisSections {
    $appcmd = Join-Path $env:windir "system32\inetsrv\appcmd.exe"
    if (-not (Test-Path $appcmd)) {
        Fail "appcmd.exe nao encontrado - IIS incompleto"
        return
    }

    foreach ($secao in @("system.webServer/handlers", "system.webServer/httpPlatform")) {
        & $appcmd unlock config /section:$secao 2>&1 | Out-Null
    }

    Fix "Secoes handlers e httpPlatform desbloqueadas (evita 0x80070021)"
}

function Remove-HandlersConflitantes {
    Import-Module WebAdministration -ErrorAction Stop

    $sitePath = "IIS:\Sites\$NomeSite"
    if (-not (Test-Path $sitePath)) { return }

    $handlers = Get-WebHandler -PSPath $sitePath -ErrorAction SilentlyContinue
    if (-not $handlers) { return }

    $conflitos = $handlers | Where-Object {
        $_.Name -ne "httpPlatformHandler" -and (
            $_.Modules -like "*FastCgi*" -or
            $_.Modules -like "*httpPlatform*" -or
            $_.Name -like "*Python*" -or
            $_.Name -like "*wfastcgi*"
        )
    }

    foreach ($handler in $conflitos) {
        Remove-WebHandler -Name $handler.Name -PSPath $sitePath -ErrorAction SilentlyContinue
        Fix "Handler conflitante removido: $($handler.Name) ($($handler.Modules))"
    }
}

function Set-AppPoolConfig {
    Import-Module WebAdministration -ErrorAction Stop

    $poolPath = "IIS:\AppPools\$nomePool"
    if (-not (Test-Path $poolPath)) {
        Warn "App pool $nomePool nao encontrado - crie o site no inetmgr"
        return
    }

    Set-ItemProperty $poolPath -Name managedRuntimeVersion -Value ""
    Set-ItemProperty $poolPath -Name enable32BitAppOnWin64 -Value $false
    Set-ItemProperty $poolPath -Name processModel.loadUserProfile -Value $true
    Set-ItemProperty $poolPath -Name startMode -Value "AlwaysRunning" -ErrorAction SilentlyContinue

    Fix "App pool $nomePool - No Managed Code, 64-bit, loadUserProfile"
}

function Show-LogsDiagnostico {
    $logDir = Join-Path $projectRoot "logs"
    if (-not (Test-Path $logDir)) { return }

    foreach ($pattern in @("iis_startup.log", "uvicorn*.log", "django_errors.log")) {
        Get-ChildItem $logDir -Filter $pattern -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 2 |
            ForEach-Object {
                Write-Host ""
                Write-Host "--- logs\$($_.Name) ---" -ForegroundColor DarkGray
                Get-Content $_.FullName -Tail 12 -ErrorAction SilentlyContinue |
                    ForEach-Object { Write-Host $_ -ForegroundColor DarkGray }
            }
    }
}

function Invoke-HttpWarmup {
    param([int]$PortaDestino)

    $urlTeste = "http://127.0.0.1:${PortaDestino}/login/"
    $maxTentativas = 6

    Write-Host ""
    Write-Host "  Aquecendo aplicacao em $urlTeste (cold start pode levar 1-3 min)..." -ForegroundColor DarkGray

    for ($t = 1; $t -le $maxTentativas; $t++) {
        $pythonProcs = @(Get-Process -Name python* -ErrorAction SilentlyContinue)
        if ($pythonProcs.Count -gt 0) {
            $pids = ($pythonProcs | Select-Object -ExpandProperty Id) -join ", "
            Write-Host "  Processo Python detectado (PID $pids)" -ForegroundColor DarkGray
        }

        try {
            $response = Invoke-WebRequest $urlTeste -UseBasicParsing -TimeoutSec 60 -ErrorAction Stop
            Ok "HTTP respondeu $($response.StatusCode) em $urlTeste"
            return
        } catch {
            $msgErro = $_.Exception.Message
            $ehTimeout = ($msgErro -match "timed out|tempo limite|Timeout")

            if ($t -lt $maxTentativas) {
                Write-Host "  Tentativa $t/$maxTentativas - ainda subindo..." -ForegroundColor DarkGray
                Start-Sleep -Seconds 20
                continue
            }

            if ($ehTimeout) {
                Fail "HTTP timeout - Python nao respondeu. Veja logs\iis_startup.log"
            } elseif ($msgErro -match "502") {
                Fail "HTTP 502 - Python nao subiu. Veja logs\iis_startup.log"
            } elseif ($msgErro -match "conectar|connect") {
                Fail "HTTP recusado na porta $PortaDestino"
            } else {
                Warn "HTTP falhou: $msgErro"
            }
        }
    }
}

function Start-ServicosIIS {
    # WAS deve iniciar antes do W3SVC
    $servicos = @(
        @{ Nome = "WAS";   Label = "Windows Process Activation Service" },
        @{ Nome = "W3SVC"; Label = "World Wide Web Publishing Service" }
    )

    foreach ($svc in $servicos) {
        $service = Get-Service -Name $svc.Nome -ErrorAction SilentlyContinue
        if (-not $service) {
            Fail "Servico $($svc.Nome) nao instalado - ative o IIS em optionalfeatures"
            continue
        }

        if ($service.StartType -eq "Disabled") {
            Set-Service -Name $svc.Nome -StartupType Automatic
            Fix "$($svc.Nome) configurado para iniciar automaticamente"
        }

        if ($service.Status -ne "Running") {
            try {
                Start-Service -Name $svc.Nome -ErrorAction Stop
                Fix "$($svc.Nome) iniciado - $($svc.Label)"
            } catch {
                Fail "Nao foi possivel iniciar $($svc.Nome) - execute como Administrador"
            }
        }
    }
}

function Set-PortaSite {
    param([int]$PortaDestino)

    Start-ServicosIIS

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
        if ($content -match "FastCgi|wfastcgi") { Fail "web.config usa FastCGI - use apenas HttpPlatformHandler" }
        if ($content -match "%HTTP_PLATFORM_PORT%") { Ok "web.config usa porta dinamica HTTP_PLATFORM_PORT" }
        else { Fail "web.config sem --port %HTTP_PLATFORM_PORT% nos arguments" }
    } else {
        Fail "web.config ausente - rode configurar_iis.ps1 para gerar"
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

            $sitePath = "IIS:\Sites\$NomeSite"
            $fastCgi = Get-WebHandler -PSPath $sitePath -ErrorAction SilentlyContinue |
                Where-Object { $_.Modules -like "*FastCgi*" -or $_.Name -like "*wfastcgi*" }
            if ($fastCgi) {
                Fail "Handler FastCGI encontrado no site - remova (nao usar wfastcgi)"
            } else {
                Ok "Sem handlers FastCGI no site"
            }
        } else {
            Fail "Site $NomeSite nao existe no IIS - crie no inetmgr"
        }

        $poolPath = "IIS:\AppPools\$nomePool"
        if (Test-Path $poolPath) {
            $runtime = (Get-ItemProperty $poolPath).managedRuntimeVersion
            if ($runtime -eq "") { Ok "App pool sem .NET (No Managed Code)" }
            else { Fail "App pool com .NET $runtime - defina No Managed Code" }

            $bit32 = (Get-ItemProperty $poolPath).enable32BitAppOnWin64
            if (-not $bit32) { Ok "App pool 64-bit (Python 64-bit)" }
            else { Fail "App pool 32-bit ativo - desative para Python 64-bit" }
        }

        $was = Get-Service WAS -ErrorAction SilentlyContinue
        if ($was -and $was.Status -eq "Running") {
            Ok "Servico WAS em execucao"
        } else {
            Fail "Servico WAS parado - necessario para iniciar sites IIS"
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

        & $pythonExe manage.py check --deploy 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { Ok "python manage.py check --deploy passou" }
        else { Warn "check --deploy com avisos - revise DEBUG/ALLOWED_HOSTS/HTTPS no .env" }
        Pop-Location
    }

    Invoke-HttpWarmup -PortaDestino $PortaDestino
    Show-LogsDiagnostico
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

    Unlock-IisSections
    Update-WebConfig
    Set-PermissoesIIS
    Set-AppPoolConfig
    Remove-HandlersConflitantes
    Set-PortaSite -PortaDestino $Porta
    Invoke-DjangoSetup

    if ($script:correcoes -gt 0) {
        Write-Host ""
        Fix "Reiniciando IIS - $script:correcoes correcoes aplicadas"
        iisreset | Out-Null
        Start-Sleep -Seconds 10
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
