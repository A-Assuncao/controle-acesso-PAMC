# Atualiza um unico site (usado por atualizar_todos.ps1).
param(
    [Parameter(Mandatory)][string]$Id,
    [Parameter(Mandatory)][string]$Caminho,
    [string]$Nome = "",
    [string]$Tipo = "local",
    [string]$Computador = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$display = if ($Nome) { $Nome } else { $Id }

if ($DryRun) {
    Write-Output "DRYRUN|$display|0"
    exit 0
}

$updateBat = Join-Path $Caminho "update_app.bat"
$tipoNorm = ($Tipo | ForEach-Object { $_.ToString().ToLower() })
if (-not $tipoNorm) { $tipoNorm = "local" }

try {
    if ($tipoNorm -eq "local") {
        if (-not (Test-Path $updateBat)) {
            throw "update_app.bat nao encontrado: $updateBat"
        }
        $proc = Start-Process -FilePath "cmd.exe" `
            -ArgumentList "/c `"$updateBat`"" `
            -WorkingDirectory $Caminho `
            -Wait -PassThru -NoNewWindow
        Write-Output "OK|$display|$($proc.ExitCode)"
        exit $proc.ExitCode
    }

    if ($tipoNorm -eq "remoto") {
        if (-not $Computador) { throw "Site remoto sem computador" }
        $exitCode = Invoke-Command -ComputerName $Computador -ScriptBlock {
            param($Path)
            $bat = Join-Path $Path "update_app.bat"
            if (-not (Test-Path $bat)) { throw "update_app.bat nao encontrado: $bat" }
            $p = Start-Process -FilePath "cmd.exe" -ArgumentList "/c `"$bat`"" `
                -WorkingDirectory $Path -Wait -PassThru -NoNewWindow
            return $p.ExitCode
        } -ArgumentList $Caminho
        Write-Output "OK|$display|$exitCode"
        exit [int]$exitCode
    }

    throw "Tipo invalido: $Tipo"
} catch {
    Write-Output "ERRO|$display|$($_.Exception.Message)"
    exit 1
}
