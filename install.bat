@echo off
echo ============================================
echo  Instalador do Sistema de Controle de Acesso
echo ============================================
echo.

:: Verifica privilégios de administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Este instalador precisa ser executado como Administrador!
    echo Clique com o botao direito no arquivo e selecione "Executar como administrador"
    echo.
    pause
    exit /b 1
)

:: Solicita informações do administrador
set /p ADMIN_USER=Digite o nome de usuario administrador (padrao: admin): 
if "%ADMIN_USER%"=="" set ADMIN_USER=admin

set /p ADMIN_EMAIL=Digite o email do administrador (padrao: admin@example.com): 
if "%ADMIN_EMAIL%"=="" set ADMIN_EMAIL=admin@example.com

:password
set /p ADMIN_PASS=Digite a senha do administrador (minimo 8 caracteres): 
if "%ADMIN_PASS%"=="" goto password
if not "%ADMIN_PASS:~7%"=="" goto passok
echo A senha deve ter pelo menos 8 caracteres!
goto password
:passok

echo.
echo Preparando instalacao...
echo - Verificando requisitos...

:: Criar pasta de logs
mkdir "%TEMP%\ControleAcesso_Install_Logs" 2>nul

:: Verifica se o Git está instalado
git --version >nul 2>&1
if errorlevel 1 (
    echo - Git nao encontrado. Baixando e instalando Git...
    curl -L -o "%TEMP%\ControleAcesso_Install_Logs\git_installer.exe" "https://github.com/git-for-windows/git/releases/download/v2.41.0.windows.3/Git-2.41.0.3-64-bit.exe"
    "%TEMP%\ControleAcesso_Install_Logs\git_installer.exe" /VERYSILENT /NORESTART
    del "%TEMP%\ControleAcesso_Install_Logs\git_installer.exe"
) else (
    echo - Git ja instalado. OK!
)

:: Baixa e instala Python em uma pasta específica
echo - Configurando Python dedicado...
mkdir "%PROGRAMFILES%\ControleAcesso\Python" 2>nul
curl -L -o "%TEMP%\ControleAcesso_Install_Logs\python_installer.exe" "https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe"
"%TEMP%\ControleAcesso_Install_Logs\python_installer.exe" /quiet TargetDir="%PROGRAMFILES%\ControleAcesso\Python" Include_test=0 Include_pip=1
del "%TEMP%\ControleAcesso_Install_Logs\python_installer.exe"

:: Verifica se o NSSM está instalado
where nssm >nul 2>&1
if errorlevel 1 (
    echo - NSSM nao encontrado. Baixando e instalando NSSM...
    curl -L -o "%TEMP%\ControleAcesso_Install_Logs\nssm.zip" "https://nssm.cc/release/nssm-2.24.zip"
    powershell -Command "Expand-Archive -Path '%TEMP%\ControleAcesso_Install_Logs\nssm.zip' -DestinationPath '%TEMP%\ControleAcesso_Install_Logs\nssm'"
    copy "%TEMP%\ControleAcesso_Install_Logs\nssm\nssm-2.24\win64\nssm.exe" "%SystemRoot%\System32"
    del "%TEMP%\ControleAcesso_Install_Logs\nssm.zip"
    rmdir /s /q "%TEMP%\ControleAcesso_Install_Logs\nssm"
) else (
    echo - NSSM ja instalado. OK!
)

echo.
echo Instalando Sistema de Controle de Acesso...
echo.

:: Cria diretórios da aplicação
echo - Criando diretorios...
mkdir "%PROGRAMFILES%\ControleAcesso\app" 2>nul
mkdir "%PROGRAMFILES%\ControleAcesso\logs" 2>nul
mkdir "%PROGRAMFILES%\ControleAcesso\scripts" 2>nul
mkdir "%PROGRAMFILES%\ControleAcesso\backups" 2>nul

:: Clona o repositório
echo - Baixando codigo fonte...
cd "%PROGRAMFILES%\ControleAcesso\app"
git clone https://github.com/A-Assuncao/controle-acesso-PAMC . > "%TEMP%\ControleAcesso_Install_Logs\git_clone.log" 2>&1

:: Cria ambiente virtual usando o Python dedicado
echo - Configurando ambiente virtual...
"%PROGRAMFILES%\ControleAcesso\Python\python.exe" -m venv "%PROGRAMFILES%\ControleAcesso\venv"
call "%PROGRAMFILES%\ControleAcesso\venv\Scripts\activate"

:: Instala dependências
echo - Instalando dependencias...
python -m pip install --upgrade pip > "%TEMP%\ControleAcesso_Install_Logs\pip_upgrade.log" 2>&1
pip install -r requirements.txt > "%TEMP%\ControleAcesso_Install_Logs\pip_install.log" 2>&1

:: Configura o banco de dados
echo - Configurando banco de dados...
python manage.py migrate > "%TEMP%\ControleAcesso_Install_Logs\db_migrate.log" 2>&1

:: Cria usuário admin personalizado
echo - Criando usuario administrador...
python manage.py shell -c "from django.contrib.auth.models import User; User.objects.create_superuser('%ADMIN_USER%', '%ADMIN_EMAIL%', '%ADMIN_PASS%') if not User.objects.filter(username='%ADMIN_USER%').exists() else None"

:: Copia os scripts de manutenção
echo - Copiando scripts de manutencao...
xcopy /Y "%PROGRAMFILES%\ControleAcesso\app\scripts\*.*" "%PROGRAMFILES%\ControleAcesso\scripts\"

:: Cria serviço Windows
echo - Instalando servico Windows...
nssm install ControleAcesso "%PROGRAMFILES%\ControleAcesso\venv\Scripts\python.exe"
nssm set ControleAcesso AppDirectory "%PROGRAMFILES%\ControleAcesso\app"
nssm set ControleAcesso AppParameters "manage.py runserver 0.0.0.0:8000"
nssm set ControleAcesso DisplayName "Sistema de Controle de Acesso"
nssm set ControleAcesso Description "Servidor do Sistema de Controle de Acesso"
nssm set ControleAcesso Start SERVICE_AUTO_START
nssm set ControleAcesso AppStdout "%PROGRAMFILES%\ControleAcesso\logs\output.log"
nssm set ControleAcesso AppStderr "%PROGRAMFILES%\ControleAcesso\logs\error.log"

:: Configura atualização automática
echo - Configurando atualizacao automatica...
schtasks /create /tn "AtualizarControleAcesso" /tr "\"%PROGRAMFILES%\ControleAcesso\scripts\update.bat\"" /sc daily /st 03:00 /ru SYSTEM /f

:: Cria atalhos na área de trabalho
echo - Criando atalhos na area de trabalho...
powershell -Command "$WS = New-Object -ComObject WScript.Shell; $SC = $WS.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\Controle de Acesso.url'); $SC.TargetPath = 'http://localhost:8000'; $SC.Save()"

:: Cria pasta de scripts na área de trabalho
mkdir "%USERPROFILE%\Desktop\Scripts Controle de Acesso" 2>nul
copy "%PROGRAMFILES%\ControleAcesso\scripts\*.bat" "%USERPROFILE%\Desktop\Scripts Controle de Acesso\"

:: Inicia o serviço
echo - Iniciando servico...
net start ControleAcesso

echo.
echo ============================================
echo      Instalacao concluida com sucesso!
echo ============================================
echo.
echo Informacoes importantes:
echo - Usuario: %ADMIN_USER%
echo - Email: %ADMIN_EMAIL%
echo - URL do sistema: http://localhost:8000
echo.
echo Atalhos criados:
echo - Acesso ao sistema na area de trabalho
echo - Pasta "Scripts Controle de Acesso" na area de trabalho
echo   contendo scripts de manutencao:
echo   * update.bat - Atualiza o sistema
echo   * backup.bat - Cria backup do banco de dados
echo   * restore.bat - Restaura um backup
echo   * restart.bat - Reinicia o servico
echo.
echo Pressione qualquer tecla para concluir...
pause > nul 