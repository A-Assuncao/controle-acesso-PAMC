@echo off
setlocal enabledelayedexpansion

echo ================================================
echo  Instalador do Sistema de Controle de Acesso
echo ================================================
echo.

:: Verifica privilégios de administrador
echo Verificando privilegios de administrador...
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERRO: Este instalador precisa ser executado como Administrador!
    echo Clique com o botao direito no arquivo e selecione "Executar como administrador"
    echo.
    pause
    exit /b 1
)

:: Diretório de instalação
set INSTALL_ROOT=%ProgramFiles%\ControleAcesso
set APP_DIR=%INSTALL_ROOT%\app
set VENV_DIR=%INSTALL_ROOT%\venv
set LOG_DIR=%INSTALL_ROOT%\logs
set SCRIPTS_DIR=%INSTALL_ROOT%\scripts
set BACKUPS_DIR=%INSTALL_ROOT%\backups
set LOG_FILE=%LOG_DIR%\install_log.txt

:: Criar diretório de logs
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: Função para log
call :log "INFO" "Iniciando instalacao do Sistema de Controle de Acesso"

:: Verificar requisitos
echo Verificando requisitos minimos...
call :log "INFO" "Verificando requisitos minimos"

:: Verificar Git
echo - Verificando Git...
where git >nul 2>&1
if %errorLevel% neq 0 (
    call :log "ERRO" "Git nao encontrado. Instalando Git..."
    echo Git nao encontrado. Instalando Git via winget...
    winget install --id Git.Git -e --accept-package-agreements --accept-source-agreements >nul
    if !errorLevel! neq 0 (
        call :log "ERRO" "Falha ao instalar Git. Por favor, instale manualmente."
        echo ERRO: Falha ao instalar Git. Por favor, instale manualmente.
        echo https://git-scm.com/download/win
        pause
        exit /b 1
    )
) else (
    call :log "INFO" "Git encontrado."
    echo - Git encontrado.
)

:: Verificar Python
echo - Verificando Python...
where python >nul 2>&1
if %errorLevel% neq 0 (
    call :log "ERRO" "Python nao encontrado. Instalando Python..."
    echo Python nao encontrado. Instalando Python...
    echo Por favor, instale Python 3.9+ manualmente e adicione-o ao PATH.
    echo https://www.python.org/downloads/
    pause
    exit /b 1
) else (
    python -c "import sys; exit(0) if sys.version_info >= (3, 9) else exit(1)" >nul 2>&1
    if !errorLevel! neq 0 (
        call :log "ERRO" "Python encontrado, mas versao e menor que 3.9"
        echo ERRO: Python encontrado, mas versao e menor que 3.9. Por favor, atualize.
        pause
        exit /b 1
    )
    call :log "INFO" "Python 3.9+ encontrado."
    echo - Python 3.9+ encontrado.
)

:: Verificar OpenSSH (necessário para o serviço Serveo)
echo - Verificando OpenSSH...
where ssh >nul 2>&1
if %errorLevel% neq 0 (
    call :log "AVISO" "OpenSSH nao encontrado. O servico Serveo nao funcionara sem ele."
    echo AVISO: OpenSSH nao encontrado. O servico Serveo nao funcionara sem ele.
    echo Deseja instalar o cliente OpenSSH? (S/N)
    set /p INSTALL_SSH=
    if /i "!INSTALL_SSH!"=="S" (
        call :log "INFO" "Instalando OpenSSH Client..."
        echo Instalando OpenSSH Client...
        powershell -Command "Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0"
        if !errorLevel! neq 0 (
            call :log "ERRO" "Falha ao instalar OpenSSH Client."
            echo ERRO: Falha ao instalar OpenSSH Client. O servico Serveo nao estara disponivel.
        ) else (
            call :log "INFO" "OpenSSH Client instalado com sucesso."
            echo - OpenSSH Client instalado com sucesso.
        )
    )
) else (
    call :log "INFO" "OpenSSH encontrado."
    echo - OpenSSH encontrado.
)

:: Verificar NSSM (necessário para instalar como serviço)
echo - Verificando NSSM...
where nssm >nul 2>&1
if %errorLevel% neq 0 (
    call :log "AVISO" "NSSM nao encontrado. O sistema nao sera instalado como servico."
    echo AVISO: NSSM nao encontrado. O sistema nao sera instalado como servico.
    echo Deseja baixar e instalar NSSM para executar como servico? (S/N)
    set /p INSTALL_NSSM=
    if /i "!INSTALL_NSSM!"=="S" (
        call :log "INFO" "Baixando NSSM..."
        echo Baixando NSSM...
        
        :: Criar diretório temporário
        mkdir "%TEMP%\nssm_install" 2>nul
        
        :: Baixar o NSSM
        powershell -Command "(New-Object System.Net.WebClient).DownloadFile('https://nssm.cc/release/nssm-2.24.zip', '%TEMP%\nssm_install\nssm.zip')"
        if !errorLevel! neq 0 (
            call :log "ERRO" "Falha ao baixar NSSM."
            echo ERRO: Falha ao baixar NSSM. O sistema nao sera instalado como servico.
        ) else (
            :: Extrair o NSSM
            powershell -Command "Expand-Archive -Path '%TEMP%\nssm_install\nssm.zip' -DestinationPath '%TEMP%\nssm_install' -Force"
            
            :: Copiar o executável do NSSM para o diretório do Windows
            if exist "%TEMP%\nssm_install\nssm-2.24\win64\nssm.exe" (
                copy "%TEMP%\nssm_install\nssm-2.24\win64\nssm.exe" "%WINDIR%\System32" /y
            ) else (
                copy "%TEMP%\nssm_install\nssm-2.24\win32\nssm.exe" "%WINDIR%\System32" /y
            )
            
            call :log "INFO" "NSSM instalado com sucesso."
            echo - NSSM instalado com sucesso.
        )
        
        :: Limpar diretório temporário
        rmdir /s /q "%TEMP%\nssm_install" 2>nul
    )
) else (
    call :log "INFO" "NSSM encontrado."
    echo - NSSM encontrado.
)

:: Criar diretórios necessários
echo Criando diretorios de instalacao...
call :log "INFO" "Criando diretorios de instalacao"
if not exist "%INSTALL_ROOT%" mkdir "%INSTALL_ROOT%"
if not exist "%APP_DIR%" mkdir "%APP_DIR%"
if not exist "%SCRIPTS_DIR%" mkdir "%SCRIPTS_DIR%"
if not exist "%BACKUPS_DIR%" mkdir "%BACKUPS_DIR%"

:: Clonar repositório
echo Clonando repositorio...
call :log "INFO" "Clonando repositorio do GitHub"
cd /d "%APP_DIR%"
git clone https://github.com/A-Assuncao/controle-acesso-PAMC . --depth 1
if %errorLevel% neq 0 (
    call :log "ERRO" "Falha ao clonar repositorio"
    echo ERRO: Falha ao clonar repositorio.
    echo Verifique sua conexao com a internet e se o Git esta configurado corretamente.
    pause
    exit /b 1
)

:: Criar ambiente virtual
echo Criando ambiente virtual Python...
call :log "INFO" "Criando ambiente virtual Python"
python -m venv "%VENV_DIR%"
if %errorLevel% neq 0 (
    call :log "ERRO" "Falha ao criar ambiente virtual"
    echo ERRO: Falha ao criar ambiente virtual Python.
    pause
    exit /b 1
)

:: Ativar ambiente virtual e instalar dependências
echo Instalando dependencias...
call :log "INFO" "Instalando dependencias"
call "%VENV_DIR%\Scripts\activate.bat"
python -m pip install --upgrade pip
if %errorLevel% neq 0 (
    call :log "ERRO" "Falha ao atualizar pip"
    echo ERRO: Falha ao atualizar pip.
    pause
    exit /b 1
)

pip install -r requirements.txt
if %errorLevel% neq 0 (
    call :log "ERRO" "Falha ao instalar dependencias"
    echo ERRO: Falha ao instalar dependencias.
    echo Verifique sua conexao com a internet.
    pause
    exit /b 1
)

:: Configurar banco de dados
echo Configurando banco de dados...
call :log "INFO" "Configurando banco de dados"
python manage.py migrate
if %errorLevel% neq 0 (
    call :log "ERRO" "Falha ao configurar banco de dados"
    echo ERRO: Falha ao configurar banco de dados.
    pause
    exit /b 1
)

:: Coletar arquivos estáticos
echo Coletando arquivos estaticos...
call :log "INFO" "Coletando arquivos estaticos"
python manage.py collectstatic --noinput
if %errorLevel% neq 0 (
    call :log "ERRO" "Falha ao coletar arquivos estaticos"
    echo ERRO: Falha ao coletar arquivos estaticos.
    pause
    exit /b 1
)

:: Criar superusuário
:create_superuser
echo Criando superusuario...
call :log "INFO" "Criando superusuario"
echo Por favor, informe os dados do superusuario (administrador):
set /p ADMIN_USER=Usuario (default: admin): 
if "!ADMIN_USER!"=="" set ADMIN_USER=admin

set /p ADMIN_EMAIL=Email (default: admin@example.com): 
if "!ADMIN_EMAIL!"=="" set ADMIN_EMAIL=admin@example.com

set /p ADMIN_PASS=Senha (minimo 8 caracteres): 
if "!ADMIN_PASS!"=="" (
    echo ERRO: A senha nao pode ser vazia.
    goto :create_superuser
)
if "!ADMIN_PASS:~8!"=="" (
    echo ERRO: A senha deve ter pelo menos 8 caracteres.
    goto :create_superuser
)

:: Criar superusuário usando script Python
echo from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('%ADMIN_USER%', '%ADMIN_EMAIL%', '%ADMIN_PASS%') if not User.objects.filter(username='%ADMIN_USER%').exists() else print('Usuario ja existe') > create_superuser.py
python create_superuser.py
if %errorLevel% neq 0 (
    call :log "ERRO" "Falha ao criar superusuario"
    echo ERRO: Falha ao criar superusuario.
    pause
    exit /b 1
)
del create_superuser.py

:: Copiar scripts
echo Copiando scripts...
call :log "INFO" "Copiando scripts para o diretorio de instalacao"
copy "%APP_DIR%\scripts\*.bat" "%SCRIPTS_DIR%\" /y
copy "%APP_DIR%\scripts\*.py" "%SCRIPTS_DIR%\" /y

:: Configurar script de inicialização do servidor
echo @echo off > "%SCRIPTS_DIR%\start_server.bat"
echo cd /d "%APP_DIR%" >> "%SCRIPTS_DIR%\start_server.bat"
echo call "%VENV_DIR%\Scripts\activate.bat" >> "%SCRIPTS_DIR%\start_server.bat"
echo python manage.py runserver 0.0.0.0:8000 >> "%SCRIPTS_DIR%\start_server.bat"

:: Configurar script de inicialização do Serveo
echo @echo off > "%SCRIPTS_DIR%\start_serveo.bat"
echo echo Iniciando o tunel serveo... >> "%SCRIPTS_DIR%\start_serveo.bat"
echo cd /d "%APP_DIR%" >> "%SCRIPTS_DIR%\start_serveo.bat"
echo call "%VENV_DIR%\Scripts\activate.bat" >> "%SCRIPTS_DIR%\start_serveo.bat"
echo python "%SCRIPTS_DIR%\start_serveo.py" >> "%SCRIPTS_DIR%\start_serveo.bat"
echo pause >> "%SCRIPTS_DIR%\start_serveo.bat"

:: Configurar script de atualização
echo @echo off > "%SCRIPTS_DIR%\update.bat"
echo echo Atualizando Sistema de Controle de Acesso... >> "%SCRIPTS_DIR%\update.bat"
echo cd /d "%APP_DIR%" >> "%SCRIPTS_DIR%\update.bat"
echo :: Para os serviços >> "%SCRIPTS_DIR%\update.bat"
echo net stop ControleAcesso >> "%SCRIPTS_DIR%\update.bat"
echo :: Ativa o ambiente virtual >> "%SCRIPTS_DIR%\update.bat"
echo call "%VENV_DIR%\Scripts\activate.bat" >> "%SCRIPTS_DIR%\update.bat"
echo :: Backup do banco de dados >> "%SCRIPTS_DIR%\update.bat"
echo python manage.py dumpdata ^> "%BACKUPS_DIR%\backup_%%date:~6,4%%-%%date:~3,2%%-%%date:~0,2%%.json" >> "%SCRIPTS_DIR%\update.bat"
echo :: Atualiza o código >> "%SCRIPTS_DIR%\update.bat"
echo git pull >> "%SCRIPTS_DIR%\update.bat"
echo :: Atualiza dependências >> "%SCRIPTS_DIR%\update.bat"
echo pip install -r requirements.txt >> "%SCRIPTS_DIR%\update.bat"
echo :: Aplica migrações >> "%SCRIPTS_DIR%\update.bat"
echo python manage.py migrate >> "%SCRIPTS_DIR%\update.bat"
echo :: Atualiza arquivos estáticos >> "%SCRIPTS_DIR%\update.bat"
echo python manage.py collectstatic --noinput >> "%SCRIPTS_DIR%\update.bat"
echo :: Inicia os serviços >> "%SCRIPTS_DIR%\update.bat"
echo net start ControleAcesso >> "%SCRIPTS_DIR%\update.bat"
echo echo Atualizacao concluida! >> "%SCRIPTS_DIR%\update.bat"
echo timeout /t 5 >> "%SCRIPTS_DIR%\update.bat"

:: Configurar script de agendamento de atualizações
echo @echo off > "%SCRIPTS_DIR%\schedule_update.bat"
echo :: Cria tarefa agendada para atualização diária >> "%SCRIPTS_DIR%\schedule_update.bat"
echo schtasks /create /tn "AtualizarControleAcesso_Manha" /tr "\"%SCRIPTS_DIR%\update.bat\"" /sc daily /st 03:00 /ru SYSTEM /f >> "%SCRIPTS_DIR%\schedule_update.bat"
echo schtasks /create /tn "AtualizarControleAcesso_Tarde" /tr "\"%SCRIPTS_DIR%\update.bat\"" /sc daily /st 15:00 /ru SYSTEM /f >> "%SCRIPTS_DIR%\schedule_update.bat"
echo echo Atualizacao automatica configurada para executar diariamente as 03:00 e 15:00 >> "%SCRIPTS_DIR%\schedule_update.bat"
echo timeout /t 5 >> "%SCRIPTS_DIR%\schedule_update.bat"

:: Instalar como serviço do Windows
echo Deseja instalar o sistema como servico do Windows? (S/N)
set /p INSTALL_SERVICE=
if /i "%INSTALL_SERVICE%"=="S" (
    call :log "INFO" "Instalando o sistema como servico do Windows"
    echo Instalando o sistema como servico do Windows...
    
    :: Verificar se o NSSM está disponível
    where nssm >nul 2>&1
    if !errorLevel! neq 0 (
        call :log "ERRO" "NSSM nao encontrado. O sistema nao sera instalado como servico."
        echo ERRO: NSSM nao encontrado. O sistema nao sera instalado como servico.
    ) else (
        :: Instala o serviço principal
        nssm install ControleAcesso "%SCRIPTS_DIR%\start_server.bat"
        nssm set ControleAcesso DisplayName "Sistema de Controle de Acesso"
        nssm set ControleAcesso Description "Servidor web do Sistema de Controle de Acesso"
        nssm set ControleAcesso Start SERVICE_AUTO_START
        
        :: Inicia o serviço
        net start ControleAcesso
        if !errorLevel! neq 0 (
            call :log "ERRO" "Falha ao iniciar o servico ControleAcesso."
            echo ERRO: Falha ao iniciar o servico ControleAcesso.
        ) else (
            call :log "INFO" "Servico ControleAcesso iniciado com sucesso."
            echo Servico ControleAcesso iniciado com sucesso.
        )
        
        :: Pergunta se deseja instalar o Serveo como serviço
        echo Deseja instalar o servico de acesso remoto (Serveo)? (S/N)
        set /p INSTALL_SERVEO=
        if /i "!INSTALL_SERVEO!"=="S" (
            call :log "INFO" "Instalando o servico Serveo"
            echo Instalando o servico Serveo...
            
            nssm install ServeoService "%SCRIPTS_DIR%\start_serveo.bat"
            nssm set ServeoService DisplayName "Serveo - Acesso Remoto"
            nssm set ServeoService Description "Servico de acesso remoto via Serveo para o Sistema de Controle de Acesso"
            nssm set ServeoService Start SERVICE_AUTO_START
            nssm set ServeoService AppStdout "%LOG_DIR%\serveo_stdout.log"
            nssm set ServeoService AppStderr "%LOG_DIR%\serveo_stderr.log"
            
            :: Inicia o serviço Serveo
            net start ServeoService
            if !errorLevel! neq 0 (
                call :log "ERRO" "Falha ao iniciar o servico ServeoService."
                echo ERRO: Falha ao iniciar o servico ServeoService.
            ) else (
                call :log "INFO" "Servico ServeoService iniciado com sucesso."
                echo Servico ServeoService iniciado com sucesso.
            )
        )
    )
)

:: Configurar atualizações automáticas
echo Deseja configurar atualizacoes automaticas? (S/N)
set /p CONFIG_UPDATES=
if /i "%CONFIG_UPDATES%"=="S" (
    call :log "INFO" "Configurando atualizacoes automaticas"
    echo Configurando atualizacoes automaticas...
    
    call "%SCRIPTS_DIR%\schedule_update.bat"
    
    if !errorLevel! neq 0 (
        call :log "ERRO" "Falha ao configurar atualizacoes automaticas."
        echo ERRO: Falha ao configurar atualizacoes automaticas.
    ) else (
        call :log "INFO" "Atualizacoes automaticas configuradas com sucesso."
        echo Atualizacoes automaticas configuradas com sucesso.
    )
)

:: Criar atalho na área de trabalho
echo Criando atalho na area de trabalho...
call :log "INFO" "Criando atalho na area de trabalho"

echo [InternetShortcut] > "%PUBLIC%\Desktop\Controle de Acesso.url"
echo URL=http://localhost:8000/ >> "%PUBLIC%\Desktop\Controle de Acesso.url"
echo IconIndex=0 >> "%PUBLIC%\Desktop\Controle de Acesso.url"

:: Finalizar instalação
cls
echo ================================================
echo     Sistema de Controle de Acesso instalado!
echo ================================================
echo.
echo Para acessar o sistema:
echo - Use o atalho na area de trabalho ou acesse http://localhost:8000
echo.
if /i "%INSTALL_SERVICE%"=="S" (
    echo O sistema foi instalado como servico e ja esta em execucao.
) else (
    echo Para iniciar o sistema manualmente:
    echo - Execute: %SCRIPTS_DIR%\start_server.bat
)
echo.
if /i "%INSTALL_SERVEO%"=="S" (
    echo O acesso remoto via Serveo foi configurado.
    echo O URL de acesso externo estara disponivel no arquivo:
    echo - %LOG_DIR%\current_url.txt (apos alguns minutos)
)
echo.
echo Credenciais de administrador:
echo Usuario: %ADMIN_USER%
echo Senha: %ADMIN_PASS%
echo.
echo Logs de instalacao: %LOG_FILE%
echo.
call :log "INFO" "Instalacao concluida com sucesso"

if /i not "%INSTALL_SERVICE%"=="S" (
    echo Deseja iniciar o sistema agora? (S/N)
    set /p START_NOW=
    if /i "!START_NOW!"=="S" (
        start "" "%SCRIPTS_DIR%\start_server.bat"
        start http://localhost:8000/
    )
)

echo.
echo Pressione qualquer tecla para sair...
pause > nul
exit /b 0

:: Função de log
:log
set "level=%~1"
set "message=%~2"
set "timestamp=%date% %time%"
echo %timestamp% [%level%] %message% >> "%LOG_FILE%"
goto :eof 