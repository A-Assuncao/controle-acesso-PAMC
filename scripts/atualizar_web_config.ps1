# Gera web.config com caminhos absolutos corretos para ESTE servidor/pasta.
# Execute na raiz do projeto (onde está manage.py):
#   powershell -ExecutionPolicy Bypass -File .\scripts\atualizar_web_config.ps1

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pythonExe = Join-Path $projectRoot "venv\Scripts\python.exe"
$logFile = Join-Path $projectRoot "logs\uvicorn.log"

if (-not (Test-Path $pythonExe)) {
    Write-Host "ERRO: Python nao encontrado em:" -ForegroundColor Red
    Write-Host "  $pythonExe"
    Write-Host ""
    Write-Host "Crie o ambiente virtual antes:" -ForegroundColor Yellow
    Write-Host "  python -m venv venv"
    Write-Host "  .\venv\Scripts\Activate.ps1"
    Write-Host "  pip install -r requirements.txt"
    exit 1
}

New-Item -ItemType Directory -Force -Path (Join-Path $projectRoot "logs") | Out-Null

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

Write-Host "web.config atualizado com sucesso." -ForegroundColor Green
Write-Host "  processPath : $pythonExe"
Write-Host "  PYTHONPATH  : $projectRoot"
Write-Host "  log         : $logFile"
Write-Host ""
Write-Host "Proximo passo: iisreset" -ForegroundColor Cyan
