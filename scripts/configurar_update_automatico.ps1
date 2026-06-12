# Configura update automatico sem criar usuarios locais.
# Usa contas built-in: SYSTEM (tarefa agendada / runner) e Administradores.
#
# Uso (PowerShell como Administrador, na raiz do projeto):
#   powershell -ExecutionPolicy Bypass -File .\scripts\configurar_update_automatico.ps1
#   powershell -ExecutionPolicy Bypass -File .\scripts\configurar_update_automatico.ps1 -SomenteVerificar
#   powershell -ExecutionPolicy Bypass -File .\scripts\configurar_update_automatico.ps1 -SemTarefaAgendada
#   powershell -ExecutionPolicy Bypass -File .\scripts\configurar_update_automatico.ps1 -RemoverTarefa

param(
    [string]$ProjectRoot = "",
    [string]$Horario = "00:00",
    [string]$NomeTarefa = "ControleAcesso-AtualizacaoDiaria",
    [switch]$SomenteVerificar,
    [switch]$SemTarefaAgendada,
    [switch]$RemoverTarefa
)

$ErrorActionPreference = "Stop"
$script:erros = 0
$script:avisos = 0
$script:correcoes = 0

if (-not $ProjectRoot) {
    $ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
} else {
    $ProjectRoot = (Resolve-Path $ProjectRoot).Path
}

$updateBat = Join-Path $ProjectRoot "update_app.bat"
$logsDir = Join-Path $ProjectRoot "logs"
$gitDir = Join-Path $ProjectRoot ".git"
$venvDir = Join-Path $ProjectRoot "venv"
$dbFile = Join-Path $ProjectRoot "db.sqlite3"

function Ok([string]$msg) { Write-Host "[OK]    $msg" -ForegroundColor Green }
function Warn([string]$msg) { Write-Host "[AVISO] $msg" -ForegroundColor Yellow; $script:avisos++ }
function Fail([string]$msg) { Write-Host "[ERRO]  $msg" -ForegroundColor Red; $script:erros++ }
function Fix([string]$msg) { Write-Host "[FIX]   $msg" -ForegroundColor Cyan; $script:correcoes++ }
function Step([string]$msg) {
    Write-Host ""
    Write-Host "=== $msg ===" -ForegroundColor Cyan
}

function Assert-Administrador {
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator
    )
    if (-not $isAdmin) {
        throw "Execute como Administrador."
    }
}

function Set-PermissoesUpdate {
    # SYSTEM = tarefa agendada e runner GitHub (NT AUTHORITY\SYSTEM)
    # S-1-5-32-544 = Administradores (conta existente de manutencao)
    $contas = @(
        @{ Sid = "S-1-5-18"; Nome = "SYSTEM" },
        @{ Sid = "S-1-5-32-544"; Nome = "Administradores" }
    )

    New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

    foreach ($conta in $contas) {
        icacls $ProjectRoot /grant "*$($conta.Sid):(OI)(CI)M" /T | Out-Null
    }

    if (Test-Path $gitDir) {
        foreach ($conta in $contas) {
            icacls $gitDir /grant "*$($conta.Sid):(OI)(CI)F" /T | Out-Null
        }
    }

    if (Test-Path $venvDir) {
        foreach ($conta in $contas) {
            icacls $venvDir /grant "*$($conta.Sid):(OI)(CI)M" /T | Out-Null
        }
    }

    if (Test-Path $dbFile) {
        icacls $dbFile /grant "SYSTEM:M" | Out-Null
        icacls $dbFile /grant "Administradores:M" | Out-Null
    }

    Fix "Permissoes de update para SYSTEM e Administradores (sem usuario novo)"
}

function Set-GitConfigUpdate {
    if (-not (Test-Path $gitDir)) {
        Warn '.git ausente - clone o repositorio antes do update automatico'
        return
    }

    $safeDir = $ProjectRoot -replace '\\', '/'
    & git config --system "safe.directory" $safeDir 2>$null
    if ($LASTEXITCODE -eq 0) {
        Fix "git safe.directory configurado (maquina): $safeDir"
    } else {
        Warn "Nao foi possivel definir git config --system (git instalado?)"
    }

    $origin = ""
    Push-Location $ProjectRoot
    try {
        $origin = (git remote get-url origin 2>$null)
    } finally {
        Pop-Location
    }

    if ($origin -match "^git@") {
        Warn 'Remote SSH detectado - configure chave em C:\Windows\System32\config\systemprofile\.ssh para SYSTEM'
        Write-Host "        Repo publico HTTPS nao precisa de chave. Veja docs/INSTALACAO_PRODUCAO.md" -ForegroundColor DarkGray
    } elseif ($origin) {
        Ok "Remote Git: $origin"
    }
}

function Register-TarefaUpdate {
    param([string]$HorarioDestino)

    if (-not (Test-Path $updateBat)) {
        Fail "update_app.bat ausente em $ProjectRoot"
        return
    }

    $action = New-ScheduledTaskAction `
        -Execute "cmd.exe" `
        -Argument "/c `"$updateBat`"" `
        -WorkingDirectory $ProjectRoot

    $trigger = New-ScheduledTaskTrigger -Daily -At $HorarioDestino

    $principal = New-ScheduledTaskPrincipal `
        -UserId "SYSTEM" `
        -LogonType ServiceAccount `
        -RunLevel Highest

    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -MultipleInstances IgnoreNew `
        -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
        -RestartCount 2 `
        -RestartInterval (New-TimeSpan -Minutes 15)

    $description = @"
Update Controle de Acesso PAMC (git pull + pip + migrate + collectstatic + iisreset).
Conta: SYSTEM (built-in). Horario: $HorarioDestino. Log: $logsDir\update.log
"@

    Register-ScheduledTask `
        -TaskName $NomeTarefa `
        -Action $action `
        -Trigger $trigger `
        -Principal $principal `
        -Settings $settings `
        -Description $description `
        -Force | Out-Null

    Fix "Tarefa '$NomeTarefa' registrada ($HorarioDestino, conta SYSTEM)"
}

function Remove-TarefaUpdate {
    Unregister-ScheduledTask -TaskName $NomeTarefa -Confirm:$false -ErrorAction SilentlyContinue
    Fix "Tarefa '$NomeTarefa' removida (se existia)"
}

function Invoke-VerificacaoUpdate {
    Step "Verificacao update automatico"

    if (Test-Path $updateBat) { Ok "update_app.bat existe" }
    else { Fail "update_app.bat ausente" }

    if (Test-Path $gitDir) { Ok ".git existe" }
    else { Fail ".git ausente" }

    $tarefa = Get-ScheduledTask -TaskName $NomeTarefa -ErrorAction SilentlyContinue
    if ($tarefa) {
        $state = $tarefa.State
        Ok "Tarefa agendada '$NomeTarefa' ($state)"
        $tarefa.Triggers | ForEach-Object {
            if ($_.StartBoundary) {
                Ok "Horario: $($_.StartBoundary)"
            }
        }
    } else {
        Warn "Tarefa '$NomeTarefa' nao registrada"
    }

    $safeDirs = & git config --system --get-all safe.directory 2>$null
    $pathNorm = $ProjectRoot -replace '\\', '/'
    if ($safeDirs -contains $pathNorm) {
        Ok "git safe.directory inclui este projeto"
    } else {
        Warn "git safe.directory nao inclui $pathNorm - rode sem -SomenteVerificar"
    }

    $runner = Get-Service -Name "actions.runner.*" -ErrorAction SilentlyContinue
    if ($runner) {
        Ok "Servico GitHub Runner: $($runner.Name) ($($runner.Status))"
    } else {
        Write-Host '[INFO]  GitHub Runner nao instalado (opcional - deploy imediato no push)' -ForegroundColor DarkGray
    }
}

Write-Host ""
Write-Host "Controle de Acesso PAMC - Update automatico (sem usuario novo)" -ForegroundColor White
Write-Host "Pasta: $ProjectRoot | Tarefa: $NomeTarefa | Horario: $Horario" -ForegroundColor DarkGray

if ($RemoverTarefa) {
    Assert-Administrador
    Remove-TarefaUpdate
    exit 0
}

if (-not $SomenteVerificar) {
    Assert-Administrador
    Step "Configuracao"
    Set-PermissoesUpdate
    Set-GitConfigUpdate
    if (-not $SemTarefaAgendada) {
        Register-TarefaUpdate -HorarioDestino $Horario
    }
} else {
    Write-Host ""
    Write-Host "Modo somente verificacao" -ForegroundColor DarkGray
}

Invoke-VerificacaoUpdate

Write-Host ""
if ($script:erros -eq 0) {
    Write-Host "Update automatico OK. Teste: schtasks /Run /TN `"$NomeTarefa`"" -ForegroundColor Green
    Write-Host "Log: $logsDir\update.log" -ForegroundColor DarkGray
} else {
    Write-Host "$script:erros erro(s), $script:avisos aviso(s)." -ForegroundColor Red
}
Write-Host ""

exit $script:erros
