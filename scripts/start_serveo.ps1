<#
.SYNOPSIS
  Inicia um túnel SSH via Serveo para expor o Sistema de Controle de Acesso.

.DESCRIPTION
  Este script:
    - Inicia um túnel SSH via Serveo para o localhost:8000
    - Captura a URL gerada pelo Serveo
    - Salva a URL em um arquivo para referência
    - Envia notificação webhook (opcional)
    - Mantém o túnel ativo
    - Registra logs detalhados

.NOTES
  - Requer OpenSSH Client instalado
  - Automaticamente tenta reconectar em caso de falha
  - Logs são salvos em %PROGRAMFILES%\ControleAcesso\logs\serveo_log.txt
#>

#region Configurações iniciais
$InstallRoot = Join-Path $Env:ProgramFiles 'ControleAcesso'
$LogsDir     = Join-Path $InstallRoot 'logs'
$LogFile     = Join-Path $LogsDir 'serveo_log.txt'
$UrlFile     = Join-Path $LogsDir 'current_url.txt'

# URL do webhook para notificação (deixe em branco para desativar)
$WebhookUrl = ""

# Porta local do aplicativo Django
$LocalPort = 8000

# Timeout para tentar novamente em caso de falha (em segundos)
$RetryTimeout = 300  # 5 minutos
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

#region Função para enviar notificação webhook
function Send-WebhookNotification {
    param([string]$ServeoUrl)
    
    if ([string]::IsNullOrWhiteSpace($WebhookUrl)) {
        Write-Log INFO "Webhook não configurado. Pulando notificação."
        return
    }
    
    try {
        $ComputerName = $env:COMPUTERNAME
        $Payload = @{
            content = "Nova URL do Sistema de Controle de Acesso disponível para o servidor $ComputerName: $ServeoUrl"
        } | ConvertTo-Json
        
        Invoke-RestMethod -Uri $WebhookUrl -Method Post -Body $Payload -ContentType "application/json"
        Write-Log INFO "Notificação webhook enviada com sucesso."
    } catch {
        Write-Log ERROR "Erro ao enviar notificação webhook: $_"
    }
}
#endregion

#region Função para verificar dependências
function Test-Dependencies {
    # Verificar se o SSH está instalado
    try {
        $sshVersion = ssh -V 2>&1
        Write-Log INFO "OpenSSH encontrado: $sshVersion"
        return $true
    } catch {
        Write-Log ERROR "OpenSSH Client não está instalado. Por favor, instale-o com 'Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0'"
        return $false
    }
}
#endregion

#region Iniciar túnel Serveo
function Start-ServeoTunnel {
    # Certifique-se de que o diretório de logs existe
    if (-not (Test-Path $LogsDir)) {
        New-Item -Path $LogsDir -ItemType Directory -Force | Out-Null
        Write-Log INFO "Diretório de logs criado: $LogsDir"
    }
    
    Write-Log INFO "=== Iniciando túnel Serveo para porta $LocalPort ==="
    
    # Verificar dependências
    if (-not (Test-Dependencies)) {
        return
    }
    
    # Loop principal para manter o túnel ativo e reconectar em caso de falha
    while ($true) {
        try {
            # Iniciar túnel SSH para Serveo
            Write-Log INFO "Estabelecendo conexão com Serveo..."
            
            # Executar comando SSH e capturar saída
            # Usar regex para capturar a URL fornecida pelo Serveo
            $sshProcess = Start-Process -FilePath "ssh" -ArgumentList "-R", "controleacesso:80:localhost:$LocalPort", "serveo.net" -NoNewWindow -RedirectStandardOutput "$LogsDir\serveo_output.txt" -RedirectStandardError "$LogsDir\serveo_error.txt" -PassThru
            
            # Aguardar um momento para a conexão ser estabelecida
            Start-Sleep -Seconds 5
            
            # Verificar se o processo ainda está em execução
            if ($sshProcess.HasExited) {
                Write-Log ERROR "Conexão SSH encerrada prematuramente."
                throw "Processo SSH encerrado com código $($sshProcess.ExitCode)"
            }
            
            # Ler a saída e procurar por um padrão de URL
            if (Test-Path "$LogsDir\serveo_output.txt") {
                $output = Get-Content "$LogsDir\serveo_output.txt" -Raw
                $urlMatch = [regex]::Match($output, 'https?://[a-zA-Z0-9.-]+\.serveo\.net')
                
                if ($urlMatch.Success) {
                    $serveoUrl = $urlMatch.Value
                    Write-Log INFO "URL do Serveo capturada: $serveoUrl"
                    
                    # Salvar URL em arquivo
                    Set-Content -Path $UrlFile -Value $serveoUrl -Force
                    Write-Log INFO "URL salva em $UrlFile"
                    
                    # Enviar notificação webhook
                    Send-WebhookNotification -ServeoUrl $serveoUrl
                    
                    # Manter o processo em execução até que seja encerrado externamente
                    Write-Log INFO "Túnel SSH estabelecido e funcionando. Pressione Ctrl+C para encerrar."
                    $sshProcess.WaitForExit()
                    
                    # Se chegamos aqui, o processo foi encerrado
                    Write-Log WARN "Túnel SSH encerrado. Código de saída: $($sshProcess.ExitCode)"
                } else {
                    Write-Log ERROR "URL do Serveo não encontrada na saída. Verifique $LogsDir\serveo_output.txt"
                    throw "URL do Serveo não encontrada"
                }
            } else {
                Write-Log ERROR "Arquivo de saída do SSH não foi criado."
                throw "Arquivo de saída não existe"
            }
        } catch {
            Write-Log ERROR "Erro no túnel Serveo: $_"
            
            # Tentar matar o processo SSH se ainda estiver rodando
            if ($sshProcess -and -not $sshProcess.HasExited) {
                $sshProcess.Kill()
                Write-Log WARN "Processo SSH forçado a encerrar."
            }
            
            # Aguardar antes de tentar novamente
            Write-Log INFO "Aguardando $RetryTimeout segundos antes de tentar novamente..."
            Start-Sleep -Seconds $RetryTimeout
        }
    }
}
#endregion

# Iniciar o túnel
Start-ServeoTunnel 