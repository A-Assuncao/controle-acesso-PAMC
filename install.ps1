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
    • Cria atalhos e tarefas agendadas
    • Inicia serviços
    • Registra logs detalhados em “install_logs\install_log.txt”

.NOTES
  • Não utiliza Python global — todo o Python roda dentro de venv em %ProgramFiles%\ControleAcesso\Python
  • Rich logs com níveis INFO, WARN, ERROR e timestamps
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
    # Verifica privilégios de administrador
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) { throw 'Este instalador precisa ser executado como Administrador.' }

    # Cria pasta de logs
    New-Item -Path $LogDir -ItemType Directory -Force | Out-Null
    Write-Log INFO 'Diretório de logs criado/confirmado.'
    Write-Log INFO '=== Iniciando instalação do Sistema de Controle de Acesso ==='
} catch {
    Write-Log ERROR $_
    exit 1
}
#endregion

#region Credenciais do administrador
try {
    $AdminUser  = Read-Host 'Digite o nome de usuário administrador (padrão: admin)'
    if ([string]::IsNullOrWhiteSpace($AdminUser)) { $AdminUser = 'admin' }

    $AdminEmail = Read-Host 'Digite o email do administrador (padrão: admin@example.com)'
    if ([string]::IsNullOrWhiteSpace($AdminEmail)) { $AdminEmail = 'admin@example.com' }

    do {
        $securePwd = Read-Host 'Digite a senha do administrador (mínimo 8 caracteres)' -AsSecureString
        $plainPwd  = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePwd))
        if ($plainPwd.Length -lt 8) { Write-Log WARN 'Senha com menos de 8 caracteres. Tente novamente.' }
    } until ($plainPwd.Length -ge 8)

    Write-Log INFO "Credenciais coletadas: usuário='$AdminUser', email='$AdminEmail'."
} catch {
    Write-Log ERROR "Erro ao coletar credenciais: $_"
    exit 1
}
#endregion

#region Função de download genérico
function Download-File {
    param([string]$Url, [string]$OutFile)
    try {
        Invoke-WebRequest -Uri $Url -OutFile $OutFile -UseBasicParsing -ErrorAction Stop
        Write-Log INFO "Download concluído: $Url"
    } catch {
        throw "Falha ao baixar $Url — $_"
    }
}
#endregion

#region Verifica/Instala Git
try {
    if (Get-Command git -ErrorAction SilentlyContinue) {
        Write-Log INFO 'Git já instalado.'
    } else {
        Write-Log INFO 'Git não encontrado. Instalando via winget...'
        winget install --id Git.Git -e --silent
        Write-Log INFO 'Git instalado com sucesso.'
    }
} catch {
    Write-Log ERROR $_
    exit 1
}
#endregion

#region Instala Python isolado e cria venv
$PythonInstaller = Join-Path $env:TEMP 'python_installer.exe'
try {
    if (-not (Test-Path (Join-Path $PythonDir 'python.exe'))) {
        Write-Log INFO 'Baixando e instalando Python isolado...'
        Download-File 'https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe' $PythonInstaller
        & $PythonInstaller /quiet TargetDir="$PythonDir" Include_test=0 Include_pip=1
        Write-Log INFO 'Python instalado em ' + $PythonDir
    } else {
        Write-Log INFO 'Python isolado já instalado.'
    }
    if (-not (Test-Path $VenvDir)) {
        Write-Log INFO 'Criando ambiente virtual...'
        & (Join-Path $PythonDir 'python.exe') -m venv $VenvDir
        Write-Log INFO 'Virtualenv criado em ' + $VenvDir
    } else {
        Write-Log INFO 'Virtualenv já existe.'
    }
    $VenvPython = Join-Path $VenvDir 'Scripts\python.exe'
    $VenvPip    = Join-Path $VenvDir 'Scripts\pip.exe'
} catch {
    Write-Log ERROR "Erro no install/configuração do Python: $_"
    exit 1
}
#endregion

#region Verifica/Instala NSSM
try {
    if (Get-Command nssm -ErrorAction SilentlyContinue) {
        Write-Log INFO 'NSSM já instalado.'
    } else {
        Write-Log INFO 'Instalando NSSM...'
        $zip = Join-Path $env:TEMP 'nssm.zip'
        Download-File 'https://nssm.cc/release/nssm-2.24.zip' $zip
        Expand-Archive -Path $zip -DestinationPath (Join-Path $env:TEMP 'nssm') -Force
        Copy-Item -Path (Join-Path $env:TEMP 'nssm\nssm-2.24\win64\nssm.exe') -Destination "$Env:SystemRoot\System32\nssm.exe" -Force
        Remove-Item $zip -Force
        Write-Log INFO 'NSSM instalado em System32.'
    }
} catch {
    Write-Log ERROR $_
    exit 1
}
#endregion

#region Verifica/Instala OpenSSH Client
try {
    if (Get-Command ssh -ErrorAction SilentlyContinue) {
        Write-Log INFO 'OpenSSH Client já instalado.'
    } else {
        Write-Log INFO 'Instalando OpenSSH Client...'
        Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0 -ErrorAction Stop
        Write-Log INFO 'OpenSSH Client instalado.'
    }
} catch {
    Write-Log ERROR $_
    exit 1
}
#endregion

#region Clona o repositório principal
try {
    New-Item -Path $AppDir -ItemType Directory -Force | Out-Null
    Set-Location $AppDir
    Write-Log INFO 'Clonando o repo...'
    git clone https://github.com/A-Assuncao/controle-acesso-PAMC . --depth 1
    Write-Log INFO 'Repositório clonado.'
} catch {
    Write-Log ERROR "Erro ao clonar: $_"
    exit 1
}
#endregion

#region Instala dependências Django
try {
    Write-Log INFO 'Atualizando pip...'
    & $VenvPython -m pip install --upgrade pip
    Write-Log INFO 'Instalando requisitos...'
    & $VenvPip install -r "$AppDir\requirements.txt"
    Write-Log INFO 'Instalando requests...'
    & $VenvPip install requests
} catch {
    Write-Log ERROR $_
    exit 1
}
#endregion

#region Configura banco e estáticos
try {
    Write-Log INFO 'Executando migrate...'
    & $VenvPython "$AppDir\manage.py" migrate
    Write-Log INFO 'Coletando estáticos...'
    & $VenvPython "$AppDir\manage.py" collectstatic --noinput
} catch {
    Write-Log ERROR $_
    exit 1
}
#endregion

#region Baixa recursos offline\

