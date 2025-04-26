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
    Write-Log ERROR $_
    exit 1
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
        if ($plainPwd.Length -lt 8) {
            Write-Log WARN 'Senha deve ter >= 8 caracteres.'
        }
    } until ($plainPwd.Length -ge 8)
    Write-Log INFO "Credenciais: $AdminUser / $AdminEmail"
} catch {
    Write-Log ERROR $_
    exit 1
}
#endregion

#region Função de download genérico
function Download-File {
    param([string]$Url, [string]$OutFile)
    try {
        Invoke-WebRequest -Uri $Url -OutFile $OutFile -UseBasicParsing -ErrorAction Stop
        Write-Log INFO "Download: $Url"
    } catch {
        throw "Erro ao baixar $Url — $_"
    }
}
#endregion

#region Verifica/Instala Git
try {
    if (Get-Command git -ErrorAction SilentlyContinue) {
        Write-Log INFO 'Git instalado.'
    } else {
        Write-Log INFO 'Instalando Git via winget...'
        winget install --id Git.Git -e --silent
        Write-Log INFO 'Git ok.'
    }
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

#region Python isolado + venv
$pyInstaller = Join-Path $env:TEMP 'python-installer.exe'
try {
    if (-not (Test-Path "$PythonDir\python.exe")) {
        Write-Log INFO 'Instalando Python isolado...'
        Download-File 'https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe' $pyInstaller
        & $pyInstaller /quiet TargetDir="$PythonDir" Include_test=0 Include_pip=1
        Write-Log INFO 'Python isolado instalado.'
    }
    if (-not (Test-Path $VenvDir)) {
        Write-Log INFO 'Criando venv...'
        & "$PythonDir\python.exe" -m venv $VenvDir
        Write-Log INFO 'venv criado.'
    }
    $VenvPython = "$VenvDir\Scripts\python.exe"
    $VenvPip    = "$VenvDir\Scripts\pip.exe"
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

#region NSSM
try {
    if (Get-Command nssm -ErrorAction SilentlyContinue) {
        Write-Log INFO 'NSSM instalado.'
    } else {
        Write-Log INFO 'Instalando NSSM...'
        $zip = Join-Path $env:TEMP 'nssm.zip'
        Download-File 'https://nssm.cc/release/nssm-2.24.zip' $zip
        Expand-Archive $zip -DestinationPath (Join-Path $env:TEMP 'nssm') -Force
        Copy-Item "$env:TEMP\nssm\nssm-2.24\win64\nssm.exe" "$Env:SystemRoot\System32\nssm.exe" -Force
        Write-Log INFO 'NSSM instalado.'
    }
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

#region OpenSSH Client
try {
    if (Get-Command ssh -ErrorAction SilentlyContinue) {
        Write-Log INFO 'OpenSSH Client instalado.'
    } else {
        Write-Log INFO 'Instalando OpenSSH Client...'
        Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0 -ErrorAction Stop
        Write-Log INFO 'OpenSSH instalado.'
    }
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

#region Clonar aplicação
try {
    New-Item $AppDir -ItemType Directory -Force | Out-Null
    Set-Location $AppDir
    Write-Log INFO 'Clonando repositório...'
    git clone https://github.com/A-Assuncao/controle-acesso-PAMC . --depth 1
    Write-Log INFO 'Repositório clonado.'
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

#region Instalar dependências Django
try {
    Write-Log INFO 'Atualizando pip...'
    & $VenvPython -m pip install --upgrade pip
    Write-Log INFO 'Instalando requirements...'
    & $VenvPip install -r "$AppDir\requirements.txt"
    Write-Log INFO 'Instalando requests...'
    & $VenvPip install requests
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

#region Migrar banco e coletar estáticos
try {
    Write-Log INFO 'Executando migrate...'
    & $VenvPython "$AppDir\manage.py" migrate
    Write-Log INFO 'Collectstatic...'
    & $VenvPython "$AppDir\manage.py" collectstatic --noinput
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

#region Baixar recursos offline
$offline = Join-Path $AppDir 'static\offline'
try {
    Write-Log INFO 'Preparando recursos offline...'
    New-Item -Path "$offline\css","$offline\js","$offline\fonts" -ItemType Directory -Force | Out-Null
    Download-File 'https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css' "$offline\css\bootstrap.min.css"
    Download-File 'https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js' "$offline\js\bootstrap.bundle.min.js"
    Download-File 'https://code.jquery.com/jquery-3.6.0.min.js' "$offline\js\jquery.min.js"
    $zip = Join-Path $env:TEMP 'bi.zip'
    Download-File 'https://github.com/twbs/icons/releases/download/v1.10.0/bootstrap-icons-1.10.0.zip' $zip
    Expand-Archive $zip -DestinationPath (Join-Path $env:TEMP 'bi') -Force
    Copy-Item "$env:TEMP\bi\fonts\*" "$offline\fonts" -Force
    Remove-Item $zip -Force
    Download-File 'https://cdn.jsdelivr.net/npm/sweetalert2@11/dist/sweetalert2.all.min.js' "$offline\js\sweetalert2.all.min.js"
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

#region Processar templates para offline
try {
    Write-Log INFO 'Substituindo URLs nos templates...'
    $patterns = @{
        "href=\"https://cdn.jsdelivr.net/npm/bootstrap@5[^"]*\"" = 'href="/static/offline/css/bootstrap.min.css"'
        "src=\"https://cdn.jsdelivr.net/npm/bootstrap@5[^"]*\""  = 'src="/static/offline/js/bootstrap.bundle.min.js"'
        "src=\"https://code.jquery.com/jquery[^"]*\""           = 'src="/static/offline/js/jquery.min.js"'
        "href=\"https://cdn.jsdelivr.net/npm/bootstrap-icons[^"]*\"" = 'href="/static/offline/css/bootstrap-icons.css"'
        "src=\"https://cdn.jsdelivr.net/npm/sweetalert2[^"]*\""  = 'src="/static/offline/js/sweetalert2.all.min.js"'
    }
    Get-ChildItem "$AppDir\core\templates" -Filter *.html -Recurse | ForEach-Object {
        $content  = Get-Content $_.FullName -Raw
        $modified = $content
        foreach ($pattern in $patterns.Keys) {
            $modified = [regex]::Replace($modified, $pattern, $patterns[$pattern])
        }
        if ($modified -ne $content) {
            Set-Content -Path $_.FullName -Value $modified
            Write-Log INFO "Template modificado: $($_.FullName)"
        }
    }
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

#region Re-collectstatic offline
try {
    Write-Log INFO 'Re-collectstatic offline...'
    & $VenvPython "$AppDir\manage.py" collectstatic --noinput
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

#region Criar superusuário Django
try {
    Write-Log INFO 'Criando superusuário...'
