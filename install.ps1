<#
.SYNOPSIS
  Instalador completo do Sistema de Controle de Acesso em PowerShell.

.DESCRIPTION
  Esse script:
    • Verifica privilégios de administrador
    • Solicita credenciais ao usuário
    • Instala/verifica Git, Python (isolado em venv), NSSM e OpenSSH
    • Clona o repositório do sistema
    • Cria e usa um ambiente virtual Python dedicado
    • Instala dependências Django e configura o projeto (migrate, collectstatic)
    • Baixa recursos offline (Bootstrap, jQuery, ícones, SweetAlert2)
    • Processa templates para uso offline
    • Cria o superusuário Django
    • Instala serviços Windows via NSSM
    • Cria scripts de inicialização e atualização
    • Agenda tarefas de atualização
    • Inicia serviços
    • Registra logs detalhados em "install_logs\install_log.txt"

.NOTES
  • Todo o Python roda dentro de venv em %ProgramFiles%\ControleAcesso\Python
  • Logging com níveis INFO, WARN, ERROR e timestamps
#>

#region Configurações iniciais
$InstallRoot = Join-Path $Env:ProgramFiles 'ControleAcesso'
$LogDir      = Join-Path $InstallRoot 'install_logs'
$LogFile     = Join-Path $LogDir 'install_log.txt'
$PythonDir   = Join-Path $InstallRoot 'Python'
$VenvDir     = Join-Path $InstallRoot 'venv'
$AppDir      = Join-Path $InstallRoot 'app'
$ScriptsDir  = Join-Path $InstallRoot 'scripts'
#endregion

#region Funções de logging
function Write-Log {
    param(
        [ValidateSet('INFO','WARN','ERROR')][string]$Level,
        [string]$Message
    )
    $ts   = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    $line = "$ts [$Level] $Message"
    try {
        Add-Content -Path $LogFile -Value $line
    } catch {
        Write-Host "Não foi possível escrever no log: $_" -ForegroundColor Red
    }
    switch ($Level) {
        'ERROR' { Write-Host $line -ForegroundColor Red }
        'WARN'  { Write-Host $line -ForegroundColor Yellow }
        default { Write-Host $line }
    }
}
#endregion

#region Início da instalação
try {
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) { throw 'Execute como Administrador.' }
    New-Item -Path $LogDir -ItemType Directory -Force | Out-Null
    Write-Log INFO 'Diretório de logs criado.'
    Write-Log INFO '=== Início da instalação ==='
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

#region Credenciais do administrador
try {
    $AdminUser  = Read-Host 'Usuário admin (padrão: admin)'
    if ([string]::IsNullOrWhiteSpace($AdminUser)) { $AdminUser = 'admin' }
    $AdminEmail = Read-Host 'Email admin (padrão: admin@example.com)'
    if ([string]::IsNullOrWhiteSpace($AdminEmail)) { $AdminEmail = 'admin@example.com' }
    do {
        $securePwd = Read-Host 'Senha admin (mínimo 8 caracteres)' -AsSecureString
        $plainPwd  = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePwd))
        if ($plainPwd.Length -lt 8) { Write-Log WARN 'Senha deve ter ao menos 8 caracteres.' }
    } until ($plainPwd.Length -ge 8)
    Write-Log INFO "Credenciais coletadas: $AdminUser / $AdminEmail"
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

#region Função de download
function Download-File {
    param([string]$Url, [string]$Output)
    try {
        Invoke-WebRequest -Uri $Url -OutFile $Output -UseBasicParsing -ErrorAction Stop
        Write-Log INFO "Download concluído: $Url"
    } catch {
        throw "Erro ao baixar $Url — $_"
    }
}
#endregion

#region Instalar dependências básicas
# Git
try {
    if (Get-Command git -ErrorAction SilentlyContinue) {
        Write-Log INFO 'Git já instalado.'
    } else {
        Write-Log INFO 'Instalando Git via winget...'
        winget install --id Git.Git -e --silent
        Write-Log INFO 'Git instalado.'
    }
} catch {
    Write-Log ERROR $_; exit 1
}

# NSSM
try {
    if (Get-Command nssm -ErrorAction SilentlyContinue) {
        Write-Log INFO 'NSSM já instalado.'
    } else {
        Write-Log INFO 'Baixando e instalando NSSM...'
        $zip = Join-Path $env:TEMP 'nssm.zip'
        Download-File 'https://nssm.cc/release/nssm-2.24.zip' $zip
        Expand-Archive -Path $zip -DestinationPath (Join-Path $env:TEMP 'nssm') -Force
        Copy-Item (Join-Path $env:TEMP 'nssm\nssm-2.24\win64\nssm.exe') "$Env:SystemRoot\System32\nssm.exe" -Force
        Write-Log INFO 'NSSM instalado.'
    }
} catch {
    Write-Log ERROR $_; exit 1
}

# OpenSSH
try {
    if (Get-Command ssh -ErrorAction SilentlyContinue) {
        Write-Log INFO 'OpenSSH Client já instalado.'
    } else {
        Write-Log INFO 'Instalando OpenSSH Client...'
        Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0 -ErrorAction Stop
        Write-Log INFO 'OpenSSH Client instalado.'
    }
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

#region Instalar Python isolado e criar venv
$pythonInstaller = Join-Path $env:TEMP 'python-installer.exe'
try {
    if (-not (Test-Path "$PythonDir\python.exe")) {
        Write-Log INFO 'Baixando Python isolado...'
        Download-File 'https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe' $pythonInstaller
        & $pythonInstaller /quiet TargetDir="$PythonDir" Include_test=0 Include_pip=1
        Write-Log INFO 'Python isolado instalado em $PythonDir.'
    }
    if (-not (Test-Path $VenvDir)) {
        Write-Log INFO 'Criando ambiente virtual...'
        & "$PythonDir\python.exe" -m venv $VenvDir
        Write-Log INFO 'Virtualenv criado em $VenvDir.'
    }
    $VenvPython = "$VenvDir\Scripts\python.exe"
    $VenvPip    = "$VenvDir\Scripts\pip.exe"
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

#region Clonar repositório e instalar Django
try {
    New-Item -Path $AppDir -ItemType Directory -Force | Out-Null
    Set-Location $AppDir
    Write-Log INFO 'Clonando aplicação...'
    git clone https://github.com/A-Assuncao/controle-acesso-PAMC . --depth 1
    Write-Log INFO 'Aplicação clonada.'
    Write-Log INFO 'Atualizando pip...'
    & $VenvPython -m pip install --upgrade pip
    Write-Log INFO 'Instalando dependências...'
    & $VenvPip install -r "$AppDir\requirements.txt"
    Write-Log INFO 'Dependências instaladas.'
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

#region Configurar banco de dados e estáticos
try {
    Write-Log INFO 'Aplicando migrações...'
    & $VenvPython "$AppDir\manage.py" migrate
    Write-Log INFO 'Coletando arquivos estáticos...'
    & $VenvPython "$AppDir\manage.py" collectstatic --noinput
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

#region Baixar recursos para uso offline
$offline = Join-Path $AppDir 'static\offline'
try {
    Write-Log INFO 'Preparando recursos offline...'
    foreach ($sub in 'css','js','fonts') {
        New-Item -Path (Join-Path $offline $sub) -ItemType Directory -Force | Out-Null
    }
    Download-File 'https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css' "$offline\css\bootstrap.min.css"
    Download-File 'https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js' "$offline\js\bootstrap.bundle.min.js"
    Download-File 'https://code.jquery.com/jquery-3.6.0.min.js' "$offline\js\jquery.min.js"
    $iconZip = Join-Path $env:TEMP 'icons.zip'
    Download-File 'https://github.com/twbs/icons/releases/download/v1.10.0/bootstrap-icons-1.10.0.zip' $iconZip
    Expand-Archive -Path $iconZip -DestinationPath (Join-Path $env:TEMP 'icons') -Force
    Copy-Item "$env:TEMP\icons\fonts\*" "$offline\fonts" -Force
    Remove-Item $iconZip -Force
    Download-File 'https://cdn.jsdelivr.net/npm/sweetalert2@11/dist/sweetalert2.all.min.js' "$offline\js\sweetalert2.all.min.js"
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

#region Processar templates para uso offline
try {
    Write-Log INFO 'Substituindo URLs nos templates...'
    $patterns = @{
        'href="https://cdn.jsdelivr.net/npm/bootstrap@5[^"']*"' = 'href="/static/offline/css/bootstrap.min.css"'
        'src="https://cdn.jsdelivr.net/npm/bootstrap@5[^"']*"'  = 'src="/static/offline/js/bootstrap.bundle.min.js"'
        'src="https://code.jquery.com/jquery[^"']*"'           = 'src="/static/off
