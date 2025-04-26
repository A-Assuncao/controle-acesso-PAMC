<#
.SYNOPSIS
  Script de atualização para o Sistema de Controle de Acesso.

.DESCRIPTION
  Este script atualiza o Sistema de Controle de Acesso:
    - Verifica conectividade com a internet
    - Realiza backup do banco de dados
    - Para os serviços do Windows
    - Atualiza o código do repositório Git
    - Atualiza as dependências Python
    - Aplica migrações do banco de dados
    - Reinicia os serviços
    - Atualiza o túnel Serveo para exposição remota
    - Registra logs detalhados de todo o processo

.NOTES
  - Requer permissões de administrador
  - Registra logs em %PROGRAMFILES%\ControleAcesso\logs\update_log.txt
#>

#region Configurações iniciais
# Caminhos importantes
$InstallRoot = Join-Path $Env:ProgramFiles 'ControleAcesso'
$AppDir      = Join-Path $InstallRoot 'app'
$BackupsDir  = Join-Path $InstallRoot 'backups'
$LogsDir     = Join-Path $InstallRoot 'logs'
$LogFile     = Join-Path $LogsDir 'update_log.txt'
$VenvDir     = Join-Path $InstallRoot 'venv'
$ScriptsDir  = Join-Path $InstallRoot 'scripts'
$ServeoScript = Join-Path $ScriptsDir 'start_serveo.ps1'

# Data atual para nome do backup
$CurrentDate = Get-Date -Format "yyyy_MM_dd"
$BackupFile  = Join-Path $BackupsDir "db_backup_$CurrentDate.sqlite3"
#endregion

#region Função de logging
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

#region Verificar privilégios de administrador
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
          ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Este script precisa ser executado como Administrador!" -ForegroundColor Red
    Write-Host "Abra o PowerShell como Administrador e tente novamente." -ForegroundColor Yellow
    exit 1
}
#endregion

#region Início da atualização
try {
    # Certifique-se de que o diretório de logs existe
    if (-not (Test-Path $LogsDir)) {
        New-Item -Path $LogsDir -ItemType Directory -Force | Out-Null
    }

    Write-Log INFO "=== Iniciando processo de atualização do Sistema de Controle de Acesso ==="
    
    # Verificar conexão com a internet
    Write-Log INFO "Verificando conexão com a internet..."
    $internetCheck = Test-Connection -ComputerName github.com -Count 2 -Quiet
    if (-not $internetCheck) {
        Write-Log WARN "Sem conexão com a internet. A atualização será adiada."
        exit 0
    }
    Write-Log INFO "Conexão com a internet confirmada."
    
} catch {
    Write-Log ERROR "Erro ao iniciar atualização: $_"
    exit 1
}
#endregion

#region Backup do banco de dados
try {
    Write-Log INFO "Realizando backup do banco de dados..."
    
    $DbFile = Join-Path $AppDir 'db.sqlite3'
    
    if (-not (Test-Path $BackupsDir)) {
        New-Item -Path $BackupsDir -ItemType Directory -Force | Out-Null
        Write-Log INFO "Diretório de backups criado em $BackupsDir"
    }
    
    if (Test-Path $DbFile) {
        Copy-Item -Path $DbFile -Destination $BackupFile -Force
        Write-Log INFO "Backup realizado com sucesso: $BackupFile"
    } else {
        Write-Log WARN "Arquivo do banco de dados não encontrado em $DbFile"
    }
} catch {
    Write-Log ERROR "Erro durante o backup do banco de dados: $_"
    # Continuamos mesmo com erro no backup, pois podemos não ter um banco ainda
}
#endregion

#region Parar serviços
try {
    Write-Log INFO "Parando serviços do sistema..."
    
    # Parar serviço do Sistema de Controle de Acesso
    if (Get-Service ControleAcesso -ErrorAction SilentlyContinue) {
        Stop-Service -Name ControleAcesso -Force
        Write-Log INFO "Serviço ControleAcesso parado."
    } else {
        Write-Log WARN "Serviço ControleAcesso não encontrado."
    }
    
    # Parar serviço do Túnel Serveo
    if (Get-Service ServeoService -ErrorAction SilentlyContinue) {
        Stop-Service -Name ServeoService -Force
        Write-Log INFO "Serviço ServeoService parado."
    } else {
        Write-Log WARN "Serviço ServeoService não encontrado."
    }
} catch {
    Write-Log ERROR "Erro ao parar serviços: $_"
    # Tentamos continuar mesmo com erro ao parar serviços
}
#endregion

#region Atualizar do repositório
try {
    Write-Log INFO "Atualizando código do repositório..."
    
    # Ativar o ambiente virtual
    $ActivateScript = Join-Path $VenvDir "Scripts\Activate.ps1"
    if (Test-Path $ActivateScript) {
        & $ActivateScript
        Write-Log INFO "Ambiente virtual ativado."
    } else {
        Write-Log ERROR "Script de ativação do ambiente virtual não encontrado: $ActivateScript"
        exit 1
    }
    
    # Entrar no diretório do aplicativo
    Set-Location $AppDir
    
    # Descartar alterações locais (em caso de modificação acidental)
    git reset --hard
    
    # Atualizar do repositório
    $gitOutput = git pull 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Log INFO "Repositório atualizado com sucesso."
        Write-Log INFO "Git output: $gitOutput"
    } else {
        Write-Log ERROR "Erro ao atualizar repositório: $gitOutput"
        exit 1
    }
} catch {
    Write-Log ERROR "Erro durante atualização do repositório: $_"
    exit 1
}
#endregion

#region Atualizar dependências
try {
    Write-Log INFO "Atualizando dependências Python..."
    
    # Verificar se pip está disponível
    $pipResult = & python -m pip --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Log ERROR "Erro: pip não está instalado ou não está funcionando: $pipResult"
        exit 1
    }
    
    # Atualizar dependências
    $pipOutput = python -m pip install -r requirements.txt 2>&1
    Write-Log INFO "Dependências atualizadas: $pipOutput"
    
} catch {
    Write-Log ERROR "Erro ao atualizar dependências: $_"
    exit 1
}
#endregion

#region Atualizar banco de dados
try {
    Write-Log INFO "Aplicando migrações ao banco de dados..."
    
    # Aplicar migrações do Django
    $migrateOutput = python manage.py migrate 2>&1
    Write-Log INFO "Migrações aplicadas: $migrateOutput"
    
    # Coletar arquivos estáticos
    $collectstaticOutput = python manage.py collectstatic --noinput 2>&1
    Write-Log INFO "Arquivos estáticos coletados: $collectstaticOutput"
    
} catch {
    Write-Log ERROR "Erro ao atualizar banco de dados: $_"
    exit 1
}
#endregion

#region Reiniciar serviços
try {
    Write-Log INFO "Reiniciando serviços..."
    
    # Iniciar o serviço ControleAcesso
    if (Get-Service ControleAcesso -ErrorAction SilentlyContinue) {
        Start-Service -Name ControleAcesso
        Write-Log INFO "Serviço ControleAcesso iniciado."
    } else {
        Write-Log WARN "Serviço ControleAcesso não encontrado."
    }
    
    # Iniciar o serviço ServeoService
    if (Get-Service ServeoService -ErrorAction SilentlyContinue) {
        Start-Service -Name ServeoService
        Write-Log INFO "Serviço ServeoService iniciado."
    } else {
        Write-Log WARN "Serviço ServeoService não encontrado."
    }
} catch {
    Write-Log ERROR "Erro ao reiniciar serviços: $_"
}
#endregion

#region Reiniciar Serveo para obter nova URL
try {
    Write-Log INFO "Reiniciando túnel Serveo para obter nova URL..."
    
    # Verificar se o script do Serveo existe
    if (Test-Path $ServeoScript) {
        & $ServeoScript
        Write-Log INFO "Script do Serveo executado."
        
        # Verificar a URL gerada
        $UrlFile = Join-Path $LogsDir "current_url.txt"
        if (Test-Path $UrlFile) {
            $url = Get-Content $UrlFile -Raw
            Write-Log INFO "Nova URL do Serveo: $url"
        } else {
            Write-Log WARN "Arquivo com a URL do Serveo não encontrado."
        }
    } else {
        Write-Log WARN "Script do Serveo não encontrado: $ServeoScript"
    }
} catch {
    Write-Log ERROR "Erro ao reiniciar túnel Serveo: $_"
}
#endregion

Write-Log INFO "=== Atualização concluída com sucesso ==="
Write-Host ""
Write-Host "Sistema de Controle de Acesso atualizado com sucesso!" -ForegroundColor Green
Write-Host "URL local: http://localhost:8000" -ForegroundColor Cyan
Write-Host "URL remota: Verifique em $LogsDir\current_url.txt" -ForegroundColor Cyan
Write-Host "" 