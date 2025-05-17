@echo off
setlocal enabledelayedexpansion
title Instalador do Sistema de Controle de Acesso

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

:: Criar diretórios necessários
if not exist "%INSTALL_ROOT%" mkdir "%INSTALL_ROOT%"
if not exist "%APP_DIR%" mkdir "%APP_DIR%"
if not exist "%SCRIPTS_DIR%" mkdir "%SCRIPTS_DIR%"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
if not exist "%BACKUPS_DIR%" mkdir "%BACKUPS_DIR%"

:: Verificar Python
echo Verificando Python...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ERRO: Python nao encontrado! Instale o Python e adicione-o ao PATH.
    echo.
    pause
    exit /b 1
)
echo Python verificado com sucesso!

:: Copiar arquivos do projeto
echo Copiando arquivos do projeto...
xcopy /E /I /Y "%~dp0*" "%APP_DIR%"

:: Criar ambiente virtual
echo Criando ambiente virtual Python...
python -m venv "%VENV_DIR%"
if %errorLevel% neq 0 (
    echo ERRO: Falha ao criar ambiente virtual Python.
    pause
    exit /b 1
)

:: Ativar ambiente virtual e instalar dependências
echo Instalando dependencias...
call "%VENV_DIR%\Scripts\activate.bat"
python -m pip install --upgrade pip
cd /d "%APP_DIR%"
pip install -r requirements.txt
pip install requests python-dotenv

:: Configurar arquivo .env
echo Configurando arquivo .env...
echo DEBUG=False > "%APP_DIR%\.env"
echo SECRET_KEY=!RANDOM!!RANDOM!!RANDOM!!RANDOM!!RANDOM! >> "%APP_DIR%\.env"
echo ALLOWED_HOSTS=localhost,127.0.0.1 >> "%APP_DIR%\.env"
echo DATABASE_URL=sqlite:///db.sqlite3 >> "%APP_DIR%\.env"

:: Configurar banco de dados
echo Configurando banco de dados...
python manage.py migrate
python manage.py collectstatic --noinput

:: Criar superusuário
:create_superuser
echo Criando superusuario...
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
if "!ADMIN_PASS:~7!"=="" (
    echo ERRO: A senha deve ter pelo menos 8 caracteres.
    goto :create_superuser
)

:: Criar superusuário
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('!ADMIN_USER!', '!ADMIN_EMAIL!', '!ADMIN_PASS!') if not User.objects.filter(username='!ADMIN_USER!').exists() else print('Usuario ja existe')"

:: Webhook Discord
echo.
echo Configurando Discord Webhook...
echo DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/1357105951878152435/uE4Uw7-ay4iHtsZvXvi75j0stthrNiE0SU4M_6ntgMbFO5a_2di95C51YIGoJuztkmWb >> "%APP_DIR%\.env"
echo Webhook do Discord configurado com sucesso!

:: Criar script para iniciar o sistema
echo Criando script de inicializacao...
set START_SCRIPT=%SCRIPTS_DIR%\iniciar.bat
echo @echo off > "%START_SCRIPT%"
echo title Sistema de Controle de Acesso >> "%START_SCRIPT%"
echo echo Iniciando Sistema de Controle de Acesso... >> "%START_SCRIPT%"
echo echo. >> "%START_SCRIPT%"
echo cd /d "%APP_DIR%" >> "%START_SCRIPT%"
echo call "%VENV_DIR%\Scripts\activate.bat" >> "%START_SCRIPT%"
echo echo Iniciando o sistema completo... >> "%START_SCRIPT%"
echo echo. >> "%START_SCRIPT%"
echo python "%SCRIPTS_DIR%\start_serveo.py" >> "%START_SCRIPT%"
echo pause >> "%START_SCRIPT%"

:: Criar script para git pull
echo Criando script de atualizacao...
set UPDATE_SCRIPT=%SCRIPTS_DIR%\update.bat
echo @echo off > "%UPDATE_SCRIPT%"
echo cd /d "%APP_DIR%" >> "%UPDATE_SCRIPT%"
echo echo Atualizando via git pull... >> "%UPDATE_SCRIPT%"
echo git pull >> "%UPDATE_SCRIPT%"
echo IF %%ERRORLEVEL%% NEQ 0 ( >> "%UPDATE_SCRIPT%"
echo   echo Erro ao executar git pull. >> "%UPDATE_SCRIPT%"
echo ) ELSE ( >> "%UPDATE_SCRIPT%"
echo   echo Atualizacao concluida com sucesso. >> "%UPDATE_SCRIPT%"
echo ) >> "%UPDATE_SCRIPT%"
echo pause >> "%UPDATE_SCRIPT%"

:: Preparar arquivo Serveo
echo Preparando script do Serveo...
copy "%APP_DIR%\scripts\start_serveo.py" "%SCRIPTS_DIR%\" /Y >nul

:: Configurar atualização automática
echo Configurando atualizacao automatica via git pull para 18:00...
schtasks /create /tn "AtualizarControleAcesso" /tr "\"%UPDATE_SCRIPT%\"" /sc daily /st 18:00 /f
if %errorlevel% == 0 (
    echo Atualizacao automatica via git pull configurada para 18:00 diariamente.
) else (
    echo ERRO: Falha ao configurar atualizacao automatica.
)

:: Criar atalho direto na área de trabalho para executar o script Python
echo Criando atalho na area de trabalho...
set DESKTOP=%USERPROFILE%\Desktop
set SHORTCUT_CMD=powershell "$s=(New-Object -COM WScript.Shell).CreateShortcut('%DESKTOP%\Controle de Acesso.lnk');$s.TargetPath='%VENV_DIR%\Scripts\pythonw.exe';$s.Arguments='%SCRIPTS_DIR%\start_serveo.py';$s.WorkingDirectory='%APP_DIR%';$s.Save()"
%SHORTCUT_CMD%

echo.
echo ================================================
echo Instalacao concluida com sucesso!
echo.
echo Um atalho foi criado na area de trabalho para iniciar o sistema.
echo Clique nele para executar o Sistema de Controle de Acesso.
echo.
echo O sistema ira:
echo  - Iniciar o servidor Django
echo  - Abrir o navegador automaticamente
echo  - Iniciar o tunel Serveo
echo  - Enviar o link do serveo para o Discord
echo.
echo A atualizacao automatica via git pull esta configurada para as 18:00
echo ================================================
echo.
pause 