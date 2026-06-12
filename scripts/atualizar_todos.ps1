# Atualiza todos os sites de producao configurados em deploy/sites.json.
#
# Fluxo:
#   git push origin main
#   .\atualizar_producao.bat
#
# Uso:
#   .\scripts\atualizar_todos.ps1
#   .\scripts\atualizar_todos.ps1 -Somente pamc,cpbv
#   .\scripts\atualizar_todos.ps1 -Sequencial
#   .\scripts\atualizar_todos.ps1 -DryRun

param(
    [string]$ConfigPath = "",
    [string[]]$Somente = @(),
    [switch]$Sequencial,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$siteScript = Join-Path $PSScriptRoot "atualizar_site.ps1"

if (-not $ConfigPath) {
    $ConfigPath = Join-Path $projectRoot "deploy\sites.json"
}

$logDir = Join-Path $projectRoot "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logOrchestrator = Join-Path $logDir "atualizar_todos.log"

function Write-Log([string]$msg, [string]$cor = "White") {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
    Add-Content -Path $logOrchestrator -Value $line -Encoding UTF8
    Write-Host $line -ForegroundColor $cor
}

function Invoke-UmSite {
    param($Site)

    $nome = if ($Site.nome) { $Site.nome } else { $Site.id }
    if ($Site.ativo -eq $false) {
        Write-Log "[$nome] Pulado (ativo=false)" Yellow
        return 0
    }

    Write-Log "[$nome] Iniciando ($($Site.tipo))..." Cyan

    $args = @(
        "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", $siteScript,
        "-Id", $Site.id,
        "-Caminho", $Site.caminho,
        "-Nome", $nome,
        "-Tipo", ($Site.tipo | ForEach-Object { $_ })
    )
    if ($Site.computador) {
        $args += @("-Computador", $Site.computador)
    }
    if ($DryRun) { $args += "-DryRun" }

    $proc = Start-Process -FilePath "powershell.exe" -ArgumentList $args `
        -Wait -PassThru -NoNewWindow

    return $proc.ExitCode
}

function Show-LogTail {
    param($Site)

    $nome = if ($Site.nome) { $Site.nome } else { $Site.id }
    $logPath = Join-Path $Site.caminho "logs\update.log"
    $tipo = ($Site.tipo | ForEach-Object { $_.ToString().ToLower() })

    if ($tipo -eq "remoto" -and $Site.computador) {
        try {
            $linhas = Invoke-Command -ComputerName $Site.computador -ScriptBlock {
                param($P)
                $f = Join-Path $P "logs\update.log"
                if (Test-Path $f) { Get-Content $f -Tail 6 } else { @() }
            } -ArgumentList $Site.caminho -ErrorAction SilentlyContinue
            foreach ($l in $linhas) { Write-Log "  $l" DarkGray }
        } catch { }
        return
    }

    if (Test-Path $logPath) {
        Get-Content $logPath -Tail 6 -ErrorAction SilentlyContinue | ForEach-Object {
            Write-Log "  $_" DarkGray
        }
    }
}

# --- main ---

Write-Log "=== Atualizacao multi-site ===" Cyan
Write-Log "Config: $ConfigPath"

if (-not (Test-Path $ConfigPath)) {
    Write-Log "ERRO: copie deploy\sites.example.json para deploy\sites.json" Red
    exit 1
}

$config = Get-Content $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
$sites = @($config.sites | Where-Object { $_ -and $_.ativo -ne $false })

if ($Somente.Count -gt 0) {
    $filtro = $Somente | ForEach-Object { $_.ToLower() }
    $sites = @($sites | Where-Object { $filtro -contains $_.id.ToLower() })
}

if ($sites.Count -eq 0) {
    Write-Log "Nenhum site ativo para atualizar." Red
    exit 1
}

Write-Log "Sites: $(($sites | ForEach-Object { if ($_.nome) { $_.nome } else { $_.id } }) -join ', ')" Cyan

$ok = 0
$erros = 0

if ($Sequencial) {
    foreach ($site in $sites) {
        $code = Invoke-UmSite -Site $site
        $nome = if ($site.nome) { $site.nome } else { $site.id }
        if ($code -eq 0) {
            Write-Log "[$nome] OK" Green
            if (-not $DryRun) { Show-LogTail -Site $site }
            $ok++
        } else {
            Write-Log "[$nome] FALHOU (exit $code)" Red
            $erros++
        }
    }
} else {
    $jobs = foreach ($site in $sites) {
        Start-Job -Name $site.id -ScriptBlock {
            param($Script, $SiteObj, $DryRunFlag)
            $nome = if ($SiteObj.nome) { $SiteObj.nome } else { $SiteObj.id }
            $args = @(
                "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-File", $Script,
                "-Id", $SiteObj.id,
                "-Caminho", $SiteObj.caminho,
                "-Nome", $nome,
                "-Tipo", ($SiteObj.tipo | ForEach-Object { $_ })
            )
            if ($SiteObj.computador) { $args += @("-Computador", $SiteObj.computador) }
            if ($DryRunFlag) { $args += "-DryRun" }
            $p = Start-Process powershell.exe -ArgumentList $args -Wait -PassThru -NoNewWindow
            return [PSCustomObject]@{ Site = $SiteObj; ExitCode = $p.ExitCode }
        } -ArgumentList $siteScript, $site, $DryRun
    }

    Write-Log "Paralelo: $($jobs.Count) site(s)..." Cyan
    $jobs | Wait-Job | Out-Null

    foreach ($job in $jobs) {
        $r = Receive-Job -Job $job
        Remove-Job -Job $job -Force
        $nome = if ($r.Site.nome) { $r.Site.nome } else { $r.Site.id }
        if ($r.ExitCode -eq 0) {
            Write-Log "[$nome] OK" Green
            if (-not $DryRun) { Show-LogTail -Site $r.Site }
            $ok++
        } else {
            Write-Log "[$nome] FALHOU (exit $($r.ExitCode))" Red
            $erros++
        }
    }
}

Write-Log "=== Resumo: $ok OK, $erros falha(s) | Log: $logOrchestrator ===" $(if ($erros -eq 0) { "Green" } else { "Red" })
if ($erros -gt 0) { exit 1 }
exit 0
