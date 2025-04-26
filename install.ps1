<#
.SYNOPSIS
  Instalador automatizado do Sistema de Controle de Acesso em PowerShell.

.DESCRIPTION
  Esse script realiza automaticamente:
    • Verifica privilégios de administrador
    • Instala/verifica Git, Python (isolado em venv), NSSM e OpenSSH
    • Clona o repositório do sistema
    • Cria e usa um ambiente virtual Python dedicado
    • Instala dependências Django e configura o projeto (migrate, collectstatic)
    • Baixa recursos offline (Bootstrap, jQuery, ícones, SweetAlert2)
    • Processa templates para uso offline
    • Cria o superusuário Django com credenciais padrão
    • Instala serviços Windows via NSSM
    • Cria scripts de inicialização e atualização
    • Agenda tarefas de atualização automática
    • Configura webhook para integrações
    • Inicia serviços
    • Registra logs detalhados em "install_logs\install_log.txt"

.NOTES
  • Todo o Python roda dentro de venv em %ProgramFiles%\ControleAcesso\Python
  • Logging com níveis INFO, WARN, ERROR e timestamps
  • Execução totalmente automatizada sem interação do usuário
#>

#region Configurações iniciais
$InstallRoot = Join-Path $Env:ProgramFiles 'ControleAcesso'
$LogDir      = Join-Path $InstallRoot 'install_logs'
$LogFile     = Join-Path $LogDir 'install_log.txt'
$PythonDir   = Join-Path $InstallRoot 'Python'
$VenvDir     = Join-Path $InstallRoot 'venv'
$AppDir      = Join-Path $InstallRoot 'app'
$ScriptsDir  = Join-Path $InstallRoot 'scripts'

# Credenciais padrão (não será solicitado ao usuário)
$AdminUser   = 'admin'
$AdminEmail  = 'admin@example.com'
# A senha será solicitada ao usuário durante a instalação

# Configuração de webhook e atualizações
$WebhookUrl  = 'https://webhook.site/seu-endpoint'  # Altere para seu endpoint real
$UpdateFrequency = 'DAILY'  # HOURLY, DAILY, WEEKLY
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
    Write-Log INFO '=== Início da instalação automatizada ==='
    
    # Solicitar senha de administrador
    do {
        $securePwd = Read-Host 'Digite a senha do administrador (mínimo 8 caracteres)' -AsSecureString
        $AdminPass = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePwd))
        if ($AdminPass.Length -lt 8) { 
            Write-Log WARN 'A senha deve ter ao menos 8 caracteres.' 
        }
    } until ($AdminPass.Length -ge 8)
    Write-Log INFO "Senha de administrador configurada com sucesso."
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
        'href="https://cdn.jsdelivr.net/npm/bootstrap@5[^"]*"' = 'href="/static/offline/css/bootstrap.min.css"'
        'src="https://cdn.jsdelivr.net/npm/bootstrap@5[^"]*"'  = 'src="/static/offline/js/bootstrap.bundle.min.js"'
        'src="https://code.jquery.com/jquery[^"]*"'           = 'src="/static/offline/js/jquery.min.js"'
        'href="https://cdn.jsdelivr.net/npm/bootstrap-icons[^"]*"' = 'href="/static/offline/fonts/bootstrap-icons.css"'
        'src="https://cdn.jsdelivr.net/npm/sweetalert2[^"]*"' = 'src="/static/offline/js/sweetalert2.all.min.js"'
    }
    
    Get-ChildItem -Path "$AppDir\templates" -Recurse -Filter "*.html" | ForEach-Object {
        $content = Get-Content $_.FullName -Raw
        foreach ($pattern in $patterns.Keys) {
            $content = $content -replace $pattern, $patterns[$pattern]
        }
        Set-Content -Path $_.FullName -Value $content
        Write-Log INFO "Template processado: $($_.Name)"
    }
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

#region Criar superusuário Django automaticamente
try {
    Write-Log INFO "Criando superusuário Django: $AdminUser"
    $createSuperuser = @"
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='$AdminUser').exists():
    User.objects.create_superuser('$AdminUser', '$AdminEmail', '$AdminPass')
    print('Superusuário criado com sucesso')
else:
    print('Superusuário já existe')
"@
    $createSuperuserPath = Join-Path $env:TEMP "create_superuser.py"
    Set-Content -Path $createSuperuserPath -Value $createSuperuser
    Get-Content $createSuperuserPath | & $VenvPython "$AppDir\manage.py" shell
    Remove-Item $createSuperuserPath -Force
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

#region Configurar webhook
try {
    Write-Log INFO "Configurando webhook para integrações..."
    $webhookConfig = @"
WEBHOOK_URL = "$WebhookUrl"
WEBHOOK_EVENTS = ['login', 'logout', 'access_denied', 'access_granted']
"@
    $webhookConfigPath = Join-Path $AppDir "webhooks.py"
    Set-Content -Path $webhookConfigPath -Value $webhookConfig
    Write-Log INFO "Webhook configurado com sucesso"
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

#region Criar scripts de serviço
try {
    Write-Log INFO "Criando scripts de serviço..."
    New-Item -Path $ScriptsDir -ItemType Directory -Force | Out-Null
    
    # Script de inicialização do servidor
    $startScript = @"
@echo off
cd "$AppDir"
"$VenvPython" "$AppDir\manage.py" runserver 0.0.0.0:8000
"@
    Set-Content -Path "$ScriptsDir\start_server.bat" -Value $startScript
    
    # Script de atualização
    $updateScript = @"
@echo off
cd "$AppDir"
git pull
"$VenvPip" install -r requirements.txt
"$VenvPython" "$AppDir\manage.py" migrate
"$VenvPython" "$AppDir\manage.py" collectstatic --noinput
"@
    Set-Content -Path "$ScriptsDir\update.bat" -Value $updateScript
    
    # Script de notificação webhook
    $webhookScript = @"
@echo off
cd "$AppDir"
"$VenvPython" "$AppDir\manage.py" send_webhook_notification --event "system_update" --message "Sistema atualizado com sucesso"
"@
    Set-Content -Path "$ScriptsDir\webhook_notify.bat" -Value $webhookScript
    
    Write-Log INFO "Scripts de serviço criados com sucesso"
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

#region Instalar serviços Windows via NSSM
try {
    Write-Log INFO "Instalando serviço do servidor Django..."
    
    # Remover serviço anterior se existir
    nssm stop "ControleAcesso" 2>$null
    nssm remove "ControleAcesso" confirm 2>$null
    
    # Instalar serviço
    nssm install "ControleAcesso" "$Env:ComSpec" "/c $ScriptsDir\start_server.bat"
    nssm set "ControleAcesso" DisplayName "Sistema de Controle de Acesso"
    nssm set "ControleAcesso" Description "Serviço do Sistema de Controle de Acesso PAMC"
    nssm set "ControleAcesso" Start SERVICE_AUTO_START
    nssm set "ControleAcesso" AppStdout "$LogDir\django_stdout.log"
    nssm set "ControleAcesso" AppStderr "$LogDir\django_stderr.log"
    nssm set "ControleAcesso" AppRotateFiles 1
    nssm set "ControleAcesso" AppRotateBytes 10485760
    
    Write-Log INFO "Serviço instalado com sucesso"
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

#region Agendar tarefa de atualização automática
try {
    Write-Log INFO "Agendando tarefa de atualização automática..."
    
    # Remover tarefa anterior se existir
    schtasks /delete /tn "ControleAcesso_Update" /f 2>$null
    
    # Definir frequência da atualização
    switch ($UpdateFrequency) {
        'HOURLY' { $schedule = '/sc HOURLY' }
        'WEEKLY' { $schedule = '/sc WEEKLY /d SUN' }
        default  { $schedule = '/sc DAILY' }
    }
    
    # Criar tarefa agendada
    schtasks /create /tn "ControleAcesso_Update" /tr "$ScriptsDir\update.bat" $schedule /st 03:00 /ru SYSTEM /rl HIGHEST /f
    
    # Agendar notificação webhook após atualização
    schtasks /create /tn "ControleAcesso_WebhookNotify" /tr "$ScriptsDir\webhook_notify.bat" $schedule /st 03:15 /ru SYSTEM /rl HIGHEST /f
    
    Write-Log INFO "Tarefas agendadas com sucesso"
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

#region Iniciar serviços
try {
    Write-Log INFO "Iniciando serviço..."
    nssm start "ControleAcesso"
    Write-Log INFO "Serviço iniciado com sucesso"
} catch {
    Write-Log ERROR $_; exit 1
}
#endregion

Write-Log INFO "=== Instalação concluída com sucesso ==="
Write-Host "`nInstalação completa do Sistema de Controle de Acesso concluída com sucesso!" -ForegroundColor Green
Write-Host "URL de acesso: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Usuário admin: $AdminUser" -ForegroundColor Cyan
Write-Host "Senha admin: $AdminPass" -ForegroundColor Cyan
Write-Host "Logs de instalação: $LogFile" -ForegroundColor Cyan
