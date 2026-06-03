# Verifica itens que costumam ser esquecidos em instalacao NOVA no IIS.
# Execute na raiz do projeto como Administrador:
#   powershell -ExecutionPolicy Bypass -File .\scripts\verificar_instalacao_iis.ps1

$ErrorActionPreference = "Continue"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$erros = 0
$avisos = 0

function Ok($msg) { Write-Host "[OK]    $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "[AVISO] $msg" -ForegroundColor Yellow; $script:avisos++ }
function Fail($msg) { Write-Host "[ERRO]  $msg" -ForegroundColor Red; $script:erros++ }

Write-Host ""
Write-Host "=== Verificacao IIS - $projectRoot ===" -ForegroundColor Cyan
Write-Host ""

# 1. venv
$pythonExe = Join-Path $projectRoot "venv\Scripts\python.exe"
if (Test-Path $pythonExe) { Ok "venv\Scripts\python.exe existe" }
else { Fail "venv nao encontrado. Rode: python -m venv venv && pip install -r requirements.txt" }

# 2. .env (NAO vem do Git)
$envFile = Join-Path $projectRoot ".env"
if (Test-Path $envFile) { Ok ".env existe" }
else { Fail ".env ausente. Rode: copy .env.example .env && notepad .env" }

# 3. web.config caminhos
$webConfig = Join-Path $projectRoot "web.config"
if (Test-Path $webConfig) {
    $content = Get-Content $webConfig -Raw
    if ($content -match [regex]::Escape($projectRoot)) {
        Ok "web.config aponta para esta pasta"
    } else {
        Fail "web.config tem caminhos de OUTRA maquina/pasta. Rode: .\scripts\atualizar_web_config.ps1"
    }
    if ($content -match "customHeaders") {
        Fail "web.config tem customHeaders (Content-Type) - remova ou regenere com atualizar_web_config.ps1"
    }
} else {
    Fail "web.config nao encontrado. Rode: .\scripts\atualizar_web_config.ps1"
}

# 4. logs
$logsDir = Join-Path $projectRoot "logs"
if (Test-Path $logsDir) { Ok "pasta logs existe" }
else { Warn "pasta logs ausente. Rode: New-Item -ItemType Directory -Force -Path .\logs" }

# 5. banco
$dbFile = Join-Path $projectRoot "db.sqlite3"
if (Test-Path $dbFile) { Ok "db.sqlite3 existe" }
else { Warn "db.sqlite3 ausente. Rode: python manage.py migrate" }

# 6. estaticos
$staticDir = Join-Path $projectRoot "staticfiles"
if ((Test-Path $staticDir) -and (Get-ChildItem $staticDir -ErrorAction SilentlyContinue)) {
    Ok "staticfiles/ populado (collectstatic feito)"
} else {
    Warn "staticfiles/ vazio ou ausente. Rode: python manage.py collectstatic --noinput"
}

# 7. HttpPlatformHandler
try {
    Import-Module WebAdministration -ErrorAction Stop
    $handler = Get-WebGlobalModule -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "*Platform*" }
    if ($handler) { Ok "HttpPlatformHandler instalado ($($handler.Name))" }
    else { Fail "HttpPlatformHandler NAO instalado. Baixe em: https://www.iis.net/downloads/microsoft/httpplatformhandler" }
} catch {
    Warn "Nao foi possivel verificar modulos IIS (execute como Admin?)"
}

# 8. Site IIS
try {
    $site = Get-Website -ErrorAction SilentlyContinue | Where-Object { $_.PhysicalPath -like "*controle-acesso-PAMC*" -or $_.Name -like "*controle*" }
    if ($site) {
        Ok "Site IIS encontrado: $($site.Name) [$($site.State)]"
        if ($site.PhysicalPath -ne $projectRoot) {
            Fail "Caminho fisico do site ($($site.PhysicalPath)) difere da pasta atual ($projectRoot)"
        }
    } else {
        Fail "Site IIS nao encontrado. Crie em inetmgr apontando para: $projectRoot"
    }

    $defaultSite = Get-Website -Name "Default Web Site" -ErrorAction SilentlyContinue
    if ($defaultSite -and $defaultSite.State -eq "Started") {
        Warn "Default Web Site ainda ATIVO - pode conflitar na porta 80"
    }
} catch {
    Warn "Nao foi possivel verificar sites IIS"
}

# 9. Django check
if (Test-Path $pythonExe) {
    Push-Location $projectRoot
    $check = & $pythonExe manage.py check 2>&1
    if ($LASTEXITCODE -eq 0) { Ok "python manage.py check passou" }
    else { Fail "python manage.py check falhou: $check" }
    Pop-Location
}

# 10. Teste HTTP local
try {
    $response = Invoke-WebRequest "http://localhost/login/" -UseBasicParsing -TimeoutSec 30 -ErrorAction Stop
    Ok "HTTP localhost/login/ respondeu: $($response.StatusCode)"
} catch {
    if ($_.Exception.Message -match "timed out") {
        Fail "HTTP timeout - app nao subiu. Veja logs\uvicorn.log (cold start pode levar 120s)"
    } elseif ($_.Exception.Message -match "502") {
        Fail "HTTP 502 - Python nao iniciou. Veja logs\uvicorn.log e processPath no web.config"
    } else {
        Warn "HTTP teste falhou: $($_.Exception.Message)"
    }
}

# 11. uvicorn log
$uvicornLog = Join-Path $projectRoot "logs\uvicorn.log"
if (Test-Path $uvicornLog) {
    $tail = Get-Content $uvicornLog -Tail 5 -ErrorAction SilentlyContinue
    if ($tail) {
        Write-Host ""
        Write-Host "--- Ultimas linhas de logs\uvicorn.log ---" -ForegroundColor DarkGray
        $tail | ForEach-Object { Write-Host $_ -ForegroundColor DarkGray }
    } else {
        Warn "logs\uvicorn.log existe mas esta vazio (IIS ainda nao iniciou o Python)"
    }
}

Write-Host ""
if ($erros -eq 0 -and $avisos -eq 0) {
    Write-Host "Tudo OK. Se o navegador ainda falhar, aguarde 120s apos iisreset e teste http://localhost/login/" -ForegroundColor Green
} elseif ($erros -eq 0) {
    Write-Host "$avisos aviso(s). Revise acima." -ForegroundColor Yellow
} else {
    Write-Host "$erros erro(s) e $avisos aviso(s). Corrija os itens [ERRO] acima." -ForegroundColor Red
}
Write-Host ""

exit $erros
