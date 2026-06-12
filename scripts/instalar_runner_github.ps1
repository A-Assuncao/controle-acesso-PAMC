# Instala o GitHub Actions self-hosted runner (Windows) de forma interativa.
# Pede o token de registro e mostra como obtê-lo no GitHub (com link).
# Usa conta SYSTEM - nao cria usuario local.
#
# Uso (PowerShell como Administrador):
#   powershell -ExecutionPolicy Bypass -File .\scripts\instalar_runner_github.ps1
#   powershell -ExecutionPolicy Bypass -File .\scripts\instalar_runner_github.ps1 -Site pamc
#   powershell -ExecutionPolicy Bypass -File .\scripts\instalar_runner_github.ps1 -SomenteInstrucoes

param(
    [string]$Site = "",
    [string]$Token = "",
    [string]$RepoUrl = "https://github.com/A-Assuncao/controle-acesso-PAMC",
    [string]$RunnerDir = "C:\ActionsRunner",
    [string]$ProjectRoot = "",
    [switch]$SomenteInstrucoes,
    [switch]$NaoAbrirGitHub
)

$ErrorActionPreference = "Stop"

$TokenPageUrl = "$RepoUrl/settings/actions/runners/new"
$RunnersListUrl = "$RepoUrl/settings/actions/runners"

function Write-Titulo([string]$msg) {
    Write-Host ""
    Write-Host $msg -ForegroundColor White
}

function Write-Passo([string]$numero, [string]$msg) {
    Write-Host "  $numero. $msg" -ForegroundColor Gray
}

function Show-InstrucoesToken {
    Write-Titulo 'Como obter o token de registro (valido por ~1 hora)'
    Write-Passo "1" "Abra a pagina de novo runner no GitHub (precisa estar logado com permissao de admin no repo):"
    Write-Host ""
    Write-Host "      $TokenPageUrl" -ForegroundColor Cyan
    Write-Host ""
    Write-Passo "2" "Clique em ""New self-hosted runner"""
    Write-Passo "3" "Escolha sistema operacional: Windows e arquitetura: x64"
    Write-Passo '4' 'Na secao Configure the runner, copie o token exibido apos a opcao --token'
    Write-Host "      (ex.: AXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX)" -ForegroundColor DarkGray
    Write-Passo '5' 'Cole o token aqui quando o script pedir - use logo; expira em ~1 hora'
    Write-Host ""
    Write-Host "  Documentacao oficial:" -ForegroundColor DarkGray
    Write-Host "  https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/adding-self-hosted-runners" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  Runners ja cadastrados:" -ForegroundColor DarkGray
    Write-Host "  $RunnersListUrl" -ForegroundColor DarkGray
}

function Assert-Administrador {
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator
    )
    if (-not $isAdmin) {
        Write-Host "[AVISO] Requer Administrador. Reexecutando com elevacao..." -ForegroundColor Yellow
        $argsList = @(
            "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", $MyInvocation.MyCommand.Path
        )
        if ($Site) { $argsList += @("-Site", $Site) }
        if ($Token) { $argsList += @("-Token", $Token) }
        if ($SomenteInstrucoes) { $argsList += "-SomenteInstrucoes" }
        if ($NaoAbrirGitHub) { $argsList += "-NaoAbrirGitHub" }
        Start-Process powershell.exe -Verb RunAs -ArgumentList $argsList
        exit 0
    }
}

function Get-UnidadeNome {
    if ($Site) {
        Write-Host "[INFO]  Unidade informada: $Site" -ForegroundColor Cyan
        return $Site.ToLower()
    }

    Write-Titulo "Nome da unidade deste servidor"
    Write-Host "  Esse nome vira a label do runner no GitHub Actions." -ForegroundColor Gray
    Write-Host "  Deve coincidir com uma entrada em matrix.site no workflow deploy-producao.yml." -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Unidades atuais no repositorio: pamc, cpbv, cpfbv" -ForegroundColor DarkGray
    Write-Host "  Exemplos de runner gerado: pamc-prod, cpbv-prod" -ForegroundColor DarkGray
    Write-Host ""

    $unidadesConhecidas = @("pamc", "cpbv", "cpfbv")

    do {
        $nome = (Read-Host "Nome da unidade (ex.: pamc)").Trim().ToLower()
        if ([string]::IsNullOrWhiteSpace($nome)) {
            Write-Host "  Informe um nome (nao pode ficar vazio)." -ForegroundColor Yellow
            continue
        }
        if ($nome -notmatch '^[a-z0-9-]+$') {
            Write-Host "  Use apenas letras minusculas, numeros e hifen." -ForegroundColor Yellow
            continue
        }
        if ($unidadesConhecidas -notcontains $nome) {
            Write-Host "  [AVISO] '$nome' nao esta na matrix atual (pamc, cpbv, cpfbv)." -ForegroundColor Yellow
            $confirmar = Read-Host "  Continuar mesmo assim? (s/N)"
            if ($confirmar -notmatch '^[sS]') { continue }
        }
        return $nome
    } while ($true)
}

function Get-RegistrationToken {
    if ($Token) { return $Token.Trim() }

    Show-InstrucoesToken

    if (-not $NaoAbrirGitHub) {
        $abrir = Read-Host "Abrir a pagina do GitHub no navegador agora? (S/n)"
        if ($abrir -eq "" -or $abrir -match '^[sS]') {
            Start-Process $TokenPageUrl
            Write-Host "  Pagina aberta. Gere o token e volte aqui." -ForegroundColor Green
        }
    }

    Write-Host ""
    $tokenInformado = Read-Host 'Cole o token de registro (valor apos --token no GitHub)'
    if ([string]::IsNullOrWhiteSpace($tokenInformado)) {
        throw "Token nao informado. Rode o script novamente apos gerar o token no GitHub."
    }
    return $tokenInformado.Trim()
}

function Get-LatestRunnerDownloadUrl {
    $apiUrl = "https://api.github.com/repos/actions/runner/releases/latest"
    $release = Invoke-RestMethod -Uri $apiUrl -Headers @{ "User-Agent" = "controle-acesso-PAMC" }
    $asset = $release.assets | Where-Object { $_.name -like "actions-runner-win-x64-*.zip" } | Select-Object -First 1
    if (-not $asset) {
        throw "Nao foi possivel encontrar o pacote actions-runner-win-x64 na release mais recente."
    }
    return @{
        Url = $asset.browser_download_url
        Version = $release.tag_name
    }
}

function Install-RunnerPackage {
    param(
        [string]$DownloadUrl,
        [string]$Version,
        [string]$Destino
    )

    if (Test-Path $Destino) {
        $servico = Get-Service -Name "actions.runner.*" -ErrorAction SilentlyContinue
        if ($servico -and $servico.Status -eq "Running") {
            Write-Host "[INFO]  Parando servico do runner existente..." -ForegroundColor Cyan
            Stop-Service $servico.Name -Force -ErrorAction SilentlyContinue
        }
    } else {
        New-Item -ItemType Directory -Force -Path $Destino | Out-Null
    }

    icacls $Destino /grant "SYSTEM:(OI)(CI)F" /T | Out-Null
    icacls $Destino /grant "Administradores:(OI)(CI)F" /T | Out-Null

    $zipPath = Join-Path $env:TEMP "actions-runner-win-x64.zip"
    Write-Host "[INFO]  Baixando runner $Version ..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $zipPath -UseBasicParsing

    Write-Host "[INFO]  Extraindo em $Destino ..." -ForegroundColor Cyan
    Expand-Archive -Path $zipPath -DestinationPath $Destino -Force
    Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
}

function Register-Runner {
    param(
        [string]$Destino,
        [string]$Url,
        [string]$RegistrationToken,
        [string]$RunnerName,
        [string]$Labels
    )

    $configCmd = Join-Path $Destino "config.cmd"
    if (-not (Test-Path $configCmd)) {
        throw "config.cmd nao encontrado em $Destino"
    }

    Push-Location $Destino
    try {
        Write-Host "[INFO]  Registrando runner '$RunnerName' (labels: $Labels) como servico SYSTEM..." -ForegroundColor Cyan

        $proc = Start-Process -FilePath "cmd.exe" -ArgumentList @(
            "/c", "config.cmd",
            "--url", $Url,
            "--token", $RegistrationToken,
            "--name", $RunnerName,
            "--labels", $Labels,
            "--unattended",
            "--replace",
            "--runasservice",
            "--windowsLogonAccount", "NT AUTHORITY\SYSTEM",
            "--windowsLogonPassword", ""
        ) -Wait -PassThru -NoNewWindow

        if ($proc.ExitCode -ne 0) {
            throw "config.cmd falhou (codigo $($proc.ExitCode)). Token expirado ou runner ja registrado?"
        }
    } finally {
        Pop-Location
    }
}

function Test-RunnerInstalado {
    $servicos = @(Get-Service -Name "actions.runner.*" -ErrorAction SilentlyContinue)
    if ($servicos.Count -eq 0) {
        Write-Host "[AVISO] Nenhum servico actions.runner.* encontrado." -ForegroundColor Yellow
        return
    }

    foreach ($svc in $servicos) {
        $cor = if ($svc.Status -eq "Running") { "Green" } else { "Yellow" }
        Write-Host "[OK]    Servico $($svc.Name): $($svc.Status)" -ForegroundColor $cor
    }

    Write-Host ""
    Write-Host "  Confirme em: $RunnersListUrl" -ForegroundColor DarkGray
    Write-Host "  Status esperado: Idle (verde)" -ForegroundColor DarkGray
}

# --- Main ---

Write-Titulo "Controle de Acesso PAMC - Instalar GitHub Actions Runner"
Write-Host "  Repositório: $RepoUrl" -ForegroundColor DarkGray
Write-Host "  Pasta runner: $RunnerDir" -ForegroundColor DarkGray
Write-Host "  Conta do servico: NT AUTHORITY\SYSTEM (sem usuario novo)" -ForegroundColor DarkGray

if ($SomenteInstrucoes) {
    Show-InstrucoesToken
    exit 0
}

Assert-Administrador

Write-Titulo "Informacoes necessarias"
Write-Host "  O script vai pedir:" -ForegroundColor Gray
Write-Host "    1. Nome da unidade deste servidor (ex.: pamc)" -ForegroundColor Gray
Write-Host "    2. Token de registro do GitHub (~1 hora de validade)" -ForegroundColor Gray
Write-Host ""

$siteLabel = Get-UnidadeNome
$runnerName = "$siteLabel-prod"
$labels = "self-hosted,windows,$siteLabel"

Write-Host ""
Write-Host "[OK]    Runner: $runnerName | Labels: $labels" -ForegroundColor Green

$registrationToken = Get-RegistrationToken

if (-not $ProjectRoot) {
    $ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

$updateScript = Join-Path $PSScriptRoot "configurar_update_automatico.ps1"
if (Test-Path $updateScript) {
    Write-Titulo "Preparando permissoes de update (SYSTEM)"
    & $updateScript -ProjectRoot $ProjectRoot -SemTarefaAgendada
    if ($LASTEXITCODE -ne 0) {
        Write-Host '[AVISO] configurar_update_automatico retornou avisos - verifique antes do primeiro deploy.' -ForegroundColor Yellow
    }
}

$runnerInfo = Get-LatestRunnerDownloadUrl
Install-RunnerPackage -DownloadUrl $runnerInfo.Url -Version $runnerInfo.Version -Destino $RunnerDir
Register-Runner `
    -Destino $RunnerDir `
    -Url $RepoUrl `
    -RegistrationToken $registrationToken `
    -RunnerName $runnerName `
    -Labels $labels

Write-Titulo "Instalacao concluida"
Test-RunnerInstalado

Write-Host ""
Write-Host "Proximo passo: git push origin main e acompanhe em Actions." -ForegroundColor Green
Write-Host ""
