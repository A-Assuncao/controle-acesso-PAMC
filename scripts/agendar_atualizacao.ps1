# Registra (ou atualiza) tarefa agendada de atualizacao diaria do Controle de Acesso.
# Compativel com Windows PowerShell 5.1+ — executar como Administrador.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File .\scripts\agendar_atualizacao.ps1
#   powershell -ExecutionPolicy Bypass -File .\scripts\agendar_atualizacao.ps1 -Horario "00:00"
#   powershell -ExecutionPolicy Bypass -File .\scripts\agendar_atualizacao.ps1 -Remover

param(
    [string]$ProjectRoot = "",
    [string]$Horario = "00:00",
    [string]$NomeTarefa = "ControleAcesso-AtualizacaoDiaria",
    [switch]$Remover
)

$ErrorActionPreference = "Stop"

if (-not $ProjectRoot) {
    $ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
} else {
    $ProjectRoot = (Resolve-Path $ProjectRoot).Path
}

function Write-Info([string]$msg) { Write-Host "[INFO]  $msg" -ForegroundColor Cyan }
function Write-Ok([string]$msg) { Write-Host "[OK]    $msg" -ForegroundColor Green }
function Write-Warn([string]$msg) { Write-Host "[AVISO] $msg" -ForegroundColor Yellow }

if ($Remover) {
    Unregister-ScheduledTask -TaskName $NomeTarefa -Confirm:$false -ErrorAction SilentlyContinue
    Write-Ok "Tarefa '$NomeTarefa' removida (se existia)."
    exit 0
}

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
if (-not $isAdmin) {
    Write-Warn "Requer Administrador. Reexecutando com elevacao..."
    $argsList = @(
        "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", $MyInvocation.MyCommand.Path,
        "-ProjectRoot", $ProjectRoot,
        "-Horario", $Horario,
        "-NomeTarefa", $NomeTarefa
    )
    Start-Process powershell.exe -Verb RunAs -ArgumentList $argsList
    exit 0
}

$updateBat = Join-Path $ProjectRoot "update_app.bat"
if (-not (Test-Path $updateBat)) {
    throw "update_app.bat nao encontrado em $ProjectRoot"
}

$logsDir = Join-Path $ProjectRoot "logs"
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

# SYSTEM + Administradores precisam escrever logs de update (tarefa roda como SYSTEM)
icacls $logsDir /grant "*S-1-5-18:(OI)(CI)M" /T | Out-Null
icacls $logsDir /grant "*S-1-5-32-544:(OI)(CI)M" /T | Out-Null

$action = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$updateBat`"" `
    -WorkingDirectory $ProjectRoot

$trigger = New-ScheduledTaskTrigger -Daily -At $Horario

$principal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -RestartCount 2 `
    -RestartInterval (New-TimeSpan -Minutes 15)

$description = @"
Atualiza o Controle de Acesso PAMC via git pull + migrate + collectstatic + iisreset.
Horario: $Horario diariamente. Log: $logsDir\update.log
Projeto: $ProjectRoot
"@

Register-ScheduledTask `
    -TaskName $NomeTarefa `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description $description `
    -Force | Out-Null

Write-Ok "Tarefa '$NomeTarefa' registrada para $Horario (conta SYSTEM, RunLevel Highest)."
Write-Info "Comando: $updateBat"
Write-Info "Log: $(Join-Path $logsDir 'update.log')"
Write-Info "Teste manual: schtasks /Run /TN `"$NomeTarefa`""
Write-Warn "Git como SYSTEM: configure credencial/SSH em maquina de producao (veja docs/TUTORIAL_IIS.md)."
