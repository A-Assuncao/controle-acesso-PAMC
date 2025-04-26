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
$InstallRoot    = Join-Path $Env:ProgramFiles 'ControleAcesso'
$LogDir         = Join-Path $InstallRoot 'install_logs'
$LogFile        = Join-Path $LogDir 'install_log.txt'
$PythonDir      = Join-Path $InstallRoot 'Python'
$VenvDir        = Join-Path $InstallRoot 'venv'
$AppDir         = Join-Path $InstallRoot 'app'
$ScriptsDir     = Join-Path $InstallRoot 'scripts'
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
    # Garante execução como Administrador
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
               ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        throw 'Este instalador precisa ser executado como Administrador.'
    }

    # Cria diretório de logs
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
        $plainPwd  = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
                        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePwd)
                     )
        if ($plainPwd.Length -lt 8) {
            Write-Log WARN 'Senha com menos de 8 caracteres. Tente novamente.'
        }
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

#region Instala Python isolado e venv
$PythonInstaller = Join-Path $env:TEMP 'python_installer.exe'
try {
    if (-not (Test-Path (Join-Path $PythonDir 'python.exe'))) {
        Write-Log INFO 'Python isolado não encontrado. Baixando e instalando...'
        Download-File 'https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe' $PythonInstaller
        & $PythonInstaller /quiet TargetDir="$PythonDir" Include_test=0 Include_pip=1
        Write-Log INFO 'Python instalado em ' + $PythonDir
    } else {
        Write-Log INFO 'Python isolado já instalado.'
    }

    # Cria virtualenv
    if (-not (Test-Path $VenvDir)) {
        Write-Log INFO 'Criando ambiente virtual Python...'
        & (Join-Path $PythonDir 'python.exe') -m venv $VenvDir
        Write-Log INFO 'Virtualenv criado em ' + $VenvDir
    } else {
        Write-Log INFO 'Virtualenv já existe.'
    }

    $VenvPython = Join-Path $VenvDir 'Scripts\python.exe'
    $VenvPip    = Join-Path $VenvDir 'Scripts\pip.exe'
} catch {
    Write-Log ERROR "Erro na instalação/configuração do Python: $_"
    exit 1
}
#endregion

#region Verifica/Instala NSSM
try {
    if (Get-Command nssm -ErrorAction SilentlyContinue) {
        Write-Log INFO 'NSSM já instalado.'
    } else {
        Write-Log INFO 'NSSM não encontrado. Baixando e instalando manualmente...'
        $ZipFile = Join-Path $env:TEMP 'nssm.zip'
        Download-File 'https://nssm.cc/release/nssm-2.24.zip' $ZipFile
        Expand-Archive -Path $ZipFile -DestinationPath (Join-Path $env:TEMP 'nssm') -Force
        Copy-Item -Path (Join-Path $env:TEMP 'nssm\nssm-2.24\win64\nssm.exe') -Destination "$Env:SystemRoot\System32\nssm.exe" -Force
        Remove-Item $ZipFile -Force
        Write-Log INFO 'NSSM instalado em System32.'
    }
} catch {
    Write-Log ERROR $_
    exit 1
}
#endregion

#region Verifica/Instala OpenSSH
try {
    if (Get-Command ssh -ErrorAction SilentlyContinue) {
        Write-Log INFO 'OpenSSH Client já instalado.'
    } else {
        Write-Log INFO 'Instalando OpenSSH Client via Windows Capability...'
        Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0 -ErrorAction Stop
        Write-Log INFO 'OpenSSH Client instalado.'
    }
} catch {
    Write-Log ERROR $_
    exit 1
}
#endregion

#region Clona repositório da aplicação
try {
    New-Item -ItemType Directory -Path $AppDir -Force | Out-Null
    Set-Location $AppDir
    Write-Log INFO 'Clonando repositório principal...'
    git clone https://github.com/A-Assuncao/controle-acesso-PAMC . --depth 1
    Write-Log INFO 'Repositório clonado.'
} catch {
    Write-Log ERROR "Erro ao clonar o repositório: $_"
    exit 1
}
#endregion

#region Instala dependências Python/Django
try {
    Write-Log INFO 'Instalando/atualizando pip...'
    & $VenvPython -m pip install --upgrade pip

    Write-Log INFO 'Instalando dependências do requirements.txt...'
    & $VenvPip install -r "$AppDir\requirements.txt"

    Write-Log INFO 'Instalando requests separadamente...'
    & $VenvPip install requests
} catch {
    Write-Log ERROR "Erro ao instalar pacotes Python: $_"
    exit 1
}
#endregion

#region Configura banco de dados e estáticos
try {
    Write-Log INFO 'Aplicando migrações Django...'
    & $VenvPython "$AppDir\manage.py" migrate

    Write-Log INFO 'Coletando arquivos estáticos...'
    & $VenvPython "$AppDir\manage.py" collectstatic --noinput
} catch {
    Write-Log ERROR "Erro no migrate/collectstatic: $_"
    exit 1
}
#endregion

#region Recursos offline (CSS, JS, fontes)
$offlineDir = Join-Path $AppDir 'static\offline'
try {
    Write-Log INFO 'Criando diretórios para recursos offline...'
    New-Item -ItemType Directory -Path (Join-Path $offlineDir 'css') -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $offlineDir 'js')  -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $offlineDir 'fonts') -Force | Out-Null

    Write-Log INFO 'Baixando Bootstrap CSS e JS...'
    Download-File 'https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css' (Join-Path $offlineDir 'css\bootstrap.min.css')
    Download-File 'https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js' (Join-Path $offlineDir 'js\bootstrap.bundle.min.js')

    Write-Log INFO 'Baixando jQuery...'
    Download-File 'https://code.jquery.com/jquery-3.6.0.min.js' (Join-Path $offlineDir 'js\jquery.min.js')

    Write-Log INFO 'Baixando Bootstrap Icons e fontes...'
    $iconZip = Join-Path $env:TEMP 'bootstrap-icons.zip'
    Download-File 'https://github.com/twbs/icons/releases/download/v1.10.0/bootstrap-icons-1.10.0.zip' $iconZip
    Expand-Archive -Path $iconZip -DestinationPath (Join-Path $env:TEMP 'bootstrap-icons') -Force
    Copy-Item -Path (Join-Path $env:TEMP 'bootstrap-icons\fonts\*') -Destination (Join-Path $offlineDir 'fonts') -Force
    Remove-Item $iconZip -Force

    Write-Log INFO 'Baixando SweetAlert2...'
    Download-File 'https://cdn.jsdelivr.net/npm/sweetalert2@11/dist/sweetalert2.all.min.js' (Join-Path $offlineDir 'js\sweetalert2.all.min.js')
} catch {
    Write-Log ERROR "Erro ao baixar recursos offline: $_"
    exit 1
}
#endregion

#region Processa templates HTML para uso offline
try {
    Write-Log INFO 'Processando templates para apontar para recursos offline...'
    $patterns = @{
        'href="https://cdn.jsdelivr.net/npm/bootstrap@5[^"]*"' = 'href="/static/offline/css/bootstrap.min.css"'
        'src="https://cdn.jsdelivr.net/npm/bootstrap@5[^"]*"'  = 'src="/static/offline/js/bootstrap.bundle.min.js"'
        'src="https://code.jquery.com/jquery[^"]*"'           = 'src="/static/offline/js/jquery.min.js"'
        'href="https://cdn.jsdelivr.net/npm/bootstrap-icons[^"]*"' = 'href="/static/offline/css/bootstrap-icons.css"'
        'src="https://cdn.jsdelivr.net/npm/sweetalert2[^"]*"'  = 'src="/static/offline/js/sweetalert2.all.min.js"'
    }
    Get-ChildItem -Path (Join-Path $AppDir 'core\templates') -Filter *.html -Recurse | ForEach-Object {
        $content = Get-Content $_.FullName -Raw
        $new     = $content
        foreach ($pat in $patterns.Keys) {
            $new = [regex]::Replace($new, $pat, $patterns[$pat])
        }
        if ($new -ne $content) {
            Set-Content -Path $_.FullName -Value $new
            Write-Log INFO "Template modificado: $($_.FullName)"
        }
    }
    Write-Log INFO 'Templates processados.'
} catch {
    Write-Log ERROR "Erro ao processar templates: $_"
    exit 1
}
#endregion

#region Re-coleta estáticos offline
try {
    Write-Log INFO 'Re-coletando estáticos offline...'
    & $VenvPython "$AppDir\manage.py" collectstatic --noinput
} catch {
    Write-Log ERROR $_
    exit 1
}
#endregion

#region Cria superusuário Django
try {
    Write-Log INFO 'Criando superusuário Django personalizado...'
    & $VenvPython - <<PYCODE
from django.contrib.auth.models import User
if not User.objects.filter(username='$AdminUser').exists():
    User.objects.create_superuser('$AdminUser', '$AdminEmail', '$plainPwd')
PYCODE
    Write-Log INFO 'Superusuário criado/ou já existente.'
} catch {
    Write-Log ERROR "Falha ao criar superusuário: $_"
    exit 1
}
#endregion

#region Configura scripts de inicialização e atualização
try {
    Write-Log INFO 'Configurando scripts de inicialização e atualização...'
    New-Item -ItemType Directory -Path $ScriptsDir -Force | Out-Null

    # Copia scripts estáticos (start_serveo.bat, etc.)
    Copy-Item -Path (Join-Path $PSScriptRoot 'scripts\*') -Destination $ScriptsDir -Recurse -Force
    Write-Log INFO 'Scripts copiados para ' + $ScriptsDir

    # Gera start_server.bat
    @"
@echo off
cd /d "%~dp0..\app"
call "%ProgramFiles%\ControleAcesso\venv\Scripts\activate"
set DJANGO_OFFLINE_MODE=True
python run_production.py --insecure
"@ | Out-File -FilePath (Join-Path $ScriptsDir 'start_server.bat') -Encoding ASCII

    # Gera update.bat
    @"
@echo off
cd /d "%~dp0..\app"
ping -n 1 github.com >nul 2>&1 || (echo Sem internet; exit /b 0)
copy "%~dp0..\app\db.sqlite3" "%~dp0..\backups\db_%date:~6,4%_%date:~3,2%_%date:~0,2%.sqlite3" /Y
net stop ControleAcesso & net stop ServeoService
call "%ProgramFiles%\ControleAcesso\venv\Scripts\activate"
git pull
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
net start ControleAcesso & net start ServeoService
call "%~dp0start_serveo.bat"
"@ | Out-File -FilePath (Join-Path $ScriptsDir 'update.bat') -Encoding ASCII

    Write-Log INFO 'Scripts de inicialização e atualização configurados.'
} catch {
    Write-Log ERROR $_
    exit 1
}
#endregion

#region Instala serviços via NSSM
try {
    Write-Log INFO 'Instalando serviços Windows via NSSM...'
    & nssm install ControleAcesso "$ScriptsDir\start_server.bat"
    & nssm set ControleAcesso DisplayName "Sistema de Controle de Acesso"
    & nssm set ControleAcesso Description "Servidor Django do Controle de Acesso"
    & nssm set ControleAcesso Start SERVICE_AUTO_START
    & nssm set ControleAcesso AppStdout "$InstallRoot\logs\django_output.log"
    & nssm set ControleAcesso AppStderr "$InstallRoot\logs\django_error.log"

    & nssm install ServeoService "$ScriptsDir\start_serveo.bat"
    & nssm set ServeoService DisplayName "Serveo Tunnel"
    & nssm set ServeoService Description "Túnel SSH da aplicação"
    & nssm set ServeoService Start SERVICE_AUTO_START
    & nssm set ServeoService AppStdout "$InstallRoot\logs\serveo_output.log"
    & nssm set ServeoService AppStderr "$InstallRoot\logs\serveo_error.log"
    & nssm set ServeoService DependOnService ControleAcesso

    Write-Log INFO 'Serviços registrados.'
} catch {
    Write-Log ERROR "Erro ao registrar serviços: $_"
    exit 1
}
#endregion

#region Agendamento de tarefas
try {
    Write-Log INFO 'Agendando atualização automática...'
    schtasks /Create /TN "AtualizarControleAcesso_Manha" /TR "`"$ScriptsDir\update.bat`"" /SC DAILY /ST 06:00 /RU SYSTEM /F | Out-Null
    schtasks /Create /TN "AtualizarControleAcesso_Tarde" /TR "`"$ScriptsDir\update.bat`"" /SC DAILY /ST 18:00 /RU SYSTEM /F | Out-Null
    Write-Log INFO 'Tarefas agendadas às 06:00 e 18:00.'
} catch {
    Write-Log ERROR $_
    exit 1
}
#endregion

#region Inicia serviços
try {
    Write-Log INFO 'Iniciando serviços...'
    Start-Service ControleAcesso
    Start-Service ServeoService
    Write-Log INFO 'Serviços iniciados com sucesso.'
} catch {
    Write-Log ERROR $_
    exit 1
}
#endregion

Write-Log INFO '=== Instalação concluída com sucesso! ==='
Write-Host "`nInstalação finalizada. Usuário: $AdminUser | Email: $AdminEmail"
Write-Host "Logs em: $LogDir`n"
