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
        $plainPwd  = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
                        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePwd))
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

#region Download genérico
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

#region Git
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
        Copy-Item "$env:TEMP\nssm\nssm-2.24\win64\nssm.exe" "$Env:SystemRoot\System32" -Force
        Write-Log INFO 'NSSM instalado.'
    }
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

#region OpenSSH
try {
    if (Get-Command ssh -ErrorAction SilentlyContinue) {
        Write-Log INFO 'OpenSSH ok.'
    } else {
        Write-Log INFO 'Instalando OpenSSH Client...'
        Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0 -ErrorAction Stop
        Write-Log INFO 'OpenSSH instalado.'
    }
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

#region Clonar app
try {
    New-Item $AppDir -ItemType Directory -Force | Out-Null
    Set-Location $AppDir
    Write-Log INFO 'Clonando repo...'
    git clone https://github.com/A-Assuncao/controle-acesso-PAMC . --depth 1
    Write-Log INFO 'Clone concluído.'
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

#region Dependências Django
try {
    Write-Log INFO 'pip upgrade...'
    & $VenvPython -m pip install --upgrade pip
    Write-Log INFO 'Instalando requirements...'
    & $VenvPip install -r "$AppDir\requirements.txt"
    Write-Log INFO 'Instalando requests...'
    & $VenvPip install requests
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

#region Migrar & static
try {
    Write-Log INFO 'Migrando DB...'
    & $VenvPython "$AppDir\manage.py" migrate
    Write-Log INFO 'Collectstatic...'
    & $VenvPython "$AppDir\manage.py" collectstatic --noinput
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

#region Recursos offline
$offline = Join-Path $AppDir 'static\offline'
try {
    Write-Log INFO 'Criando pastas offline...'
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

#region Processar templates
try {
    Write-Log INFO 'Substituindo URLs nos templates...'
    $patterns = @{
        'href="https://cdn.jsdelivr.net/npm/bootstrap@5[^"']*"' = 'href="/static/offline/css/bootstrap.min.css"'
        'src="https://cdn.jsdelivr.net/npm/bootstrap@5[^"']*"'  = 'src="/static/offline/js/bootstrap.bundle.min.js"'
        'src="https://code.jquery.com/jquery[^"']*"'           = 'src="/static/offline/js/jquery.min.js"'
        'href="https://cdn.jsdelivr.net/npm/bootstrap-icons[^"']*"' = 'href="/static/offline/css/bootstrap-icons.css"'
        'src="https://cdn.jsdelivr.net/npm/sweetalert2[^"']*"'  = 'src="/static/offline/js/sweetalert2.all.min.js"'
    }
    Get-ChildItem "$AppDir\core\templates" -Filter *.html -Recurse | ForEach-Object {
        $c = Get-Content $_.FullName -Raw
        $n = $c
        foreach ($p in $patterns.Keys) { $n = [regex]::Replace($n, $p, $patterns[$p]) }
        if ($n -ne $c) { Set-Content $_.FullName $n; Write-Log INFO "Template modificado: $_" }
    }
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

#region Re-collect static
try {
    Write-Log INFO 'Re-collectstatic offline...'
    & $VenvPython "$AppDir\manage.py" collectstatic --noinput
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

#region Superusuário
try {
    Write-Log INFO 'Criando superusuário...'
    & $VenvPython "$AppDir\manage.py" shell -c "from django.contrib.auth.models import User; if not User.objects.filter(username='$AdminUser').exists(): User.objects.create_superuser('$AdminUser','$AdminEmail','$plainPwd')"
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

#region Scripts e serviços
try {
    New-Item -ItemType Directory -Path $ScriptsDir -Force | Out-Null
    Copy-Item "$PSScriptRoot\scripts\*" $ScriptsDir -Recurse -Force

    # start_server.bat
    @"
@echo off
cd /d "%~dp0..\app"
call "%ProgramFiles%\ControleAcesso\venv\Scripts\activate"
set DJANGO_OFFLINE_MODE=True
python run_production.py --insecure
"@ | Out-File "$ScriptsDir\start_server.bat" -Encoding ASCII

    # update.bat
    @"
@echo off
cd /d "%~dp0..\app"
ping -n 1 github.com >nul 2>&1 || exit /b 0
copy "%~dp0..\app\db.sqlite3" "%~dp0..\backups\db_%date:~6,4%_%date:~3,2%_%date:~0,2%.sqlite3" /Y
net stop ControleAcesso & net stop ServeoService
call "%ProgramFiles%\ControleAcesso\venv\Scripts\activate"
git pull
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
net start ControleAcesso & net start ServeoService
call "%~dp0start_serveo.bat"
"@ | Out-File "$ScriptsDir\update.bat" -Encoding ASCII

    Write-Log INFO 'Scripts gerados.'

    # NSSM services
    & nssm install ControleAcesso "$ScriptsDir\start_server.bat"
    & nssm set ControleAcesso AppStartup SERVICE_AUTO_START
    & nssm set ControleAcesso AppStdout "$InstallRoot\logs\django_output.log"
    & nssm set ControleAcesso AppStderr "$InstallRoot\logs\django_error.log"

    & nssm install ServeoService "$ScriptsDir\start_serveo.bat"
    & nssm set ServeoService AppStartup SERVICE_AUTO_START
    & nssm set ServeoService AppStdout "$InstallRoot\logs\serveo_output.log"
    & nssm set ServeoService AppStderr "$InstallRoot\logs\serveo_error.log"
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

#region Agendamento
try {
    schtasks /create /tn "AtualizarControleAcesso_Manha" /tr "\"$ScriptsDir\update.bat\"" /sc daily /st 06:00 /ru SYSTEM /f
    schtasks /create /tn "AtualizarControleAcesso_Tarde" /tr "\"$ScriptsDir\update.bat\"" /sc daily /st 18:00 /ru SYSTEM /f
    Write-Log INFO 'Tarefas agendadas.'
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

#region Início serviços
try {
    Start-Service ControleAcesso; Start-Service ServeoService
    Write-Log INFO 'Serviços iniciados.'
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

Write-Log INFO '=== Instalação concluída ==='
Write-Host "Instalação completa. Usuário: $AdminUser | Logs: $LogDir"
