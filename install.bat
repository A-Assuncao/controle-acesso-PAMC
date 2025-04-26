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
if not "%ADMIN_PASS%:~7%"=="" goto passok
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

:: Verifica se o OpenSSH está instalado
ssh -V >nul 2>&1
if errorlevel 1 (
    echo - OpenSSH nao encontrado. Instalando OpenSSH...
    powershell -Command "Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0"
) else (
    echo - OpenSSH ja instalado. OK!
)

echo.
echo Instalando Sistema de Controle de Acesso...
echo.

:: Cria diretórios da aplicação
echo - Criando diretorios...
mkdir "%PROGRAMFILES%\ControleAcesso\app" 2>nul
mkdir "%PROGRAMFILES%\ControleAcesso\logs" 2>nul
mkdir "%PROGRAMFILES%\ControleAcesso\backups" 2>nul
mkdir "%PROGRAMFILES%\ControleAcesso\scripts" 2>nul

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
pip install requests > "%TEMP%\ControleAcesso_Install_Logs\pip_requests.log" 2>&1

:: Configura o banco de dados
echo - Configurando banco de dados...
python manage.py migrate > "%TEMP%\ControleAcesso_Install_Logs\db_migrate.log" 2>&1
python manage.py collectstatic --noinput > "%TEMP%\ControleAcesso_Install_Logs\collectstatic.log" 2>&1

:: Configura arquivos externos (Bootstrap, jQuery, etc.) para uso offline
echo - Baixando recursos para acesso offline...
mkdir "%PROGRAMFILES%\ControleAcesso\app\static\offline" 2>nul
mkdir "%PROGRAMFILES%\ControleAcesso\app\static\offline\css" 2>nul
mkdir "%PROGRAMFILES%\ControleAcesso\app\static\offline\js" 2>nul
mkdir "%PROGRAMFILES%\ControleAcesso\app\static\offline\fonts" 2>nul

:: Download Bootstrap CSS
curl -L -o "%PROGRAMFILES%\ControleAcesso\app\static\offline\css\bootstrap.min.css" "https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css"

:: Download Bootstrap JS
curl -L -o "%PROGRAMFILES%\ControleAcesso\app\static\offline\js\bootstrap.bundle.min.js" "https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"

:: Download jQuery
curl -L -o "%PROGRAMFILES%\ControleAcesso\app\static\offline\js\jquery.min.js" "https://code.jquery.com/jquery-3.6.0.min.js"

:: Download Bootstrap Icons CSS
curl -L -o "%PROGRAMFILES%\ControleAcesso\app\static\offline\css\bootstrap-icons.css" "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css"

:: Download Bootstrap Icons Fonts
curl -L -o "%TEMP%\ControleAcesso_Install_Logs\bootstrap-icons.zip" "https://github.com/twbs/icons/releases/download/v1.10.0/bootstrap-icons-1.10.0.zip"
powershell -Command "Expand-Archive -Path '%TEMP%\ControleAcesso_Install_Logs\bootstrap-icons.zip' -DestinationPath '%TEMP%\ControleAcesso_Install_Logs\bootstrap-icons'"
copy "%TEMP%\ControleAcesso_Install_Logs\bootstrap-icons\fonts\*.*" "%PROGRAMFILES%\ControleAcesso\app\static\offline\fonts\"
del "%TEMP%\ControleAcesso_Install_Logs\bootstrap-icons.zip"
rmdir /s /q "%TEMP%\ControleAcesso_Install_Logs\bootstrap-icons"

:: Download SweetAlert2
curl -L -o "%PROGRAMFILES%\ControleAcesso\app\static\offline\js\sweetalert2.all.min.js" "https://cdn.jsdelivr.net/npm/sweetalert2@11/dist/sweetalert2.all.min.js"

:: Cria script para modificar templates para usar arquivos offline
echo - Configurando sistema para uso offline...
(
echo import os
echo import re
echo from pathlib import Path
echo.
echo # Diretório de templates
echo template_dir = os.path.join(os.environ.get('PROGRAMFILES'), 'ControleAcesso', 'app', 'core', 'templates')
echo.
echo # Lista de substituições (URL online -> caminho offline)
echo replacements = [
echo     (r'href="https://cdn.jsdelivr.net/npm/bootstrap@5[^"]*"', r'href="/static/offline/css/bootstrap.min.css"'),
echo     (r'src="https://cdn.jsdelivr.net/npm/bootstrap@5[^"]*"', r'src="/static/offline/js/bootstrap.bundle.min.js"'),
echo     (r'src="https://code.jquery.com/jquery[^"]*"', r'src="/static/offline/js/jquery.min.js"'),
echo     (r'href="https://cdn.jsdelivr.net/npm/bootstrap-icons[^"]*"', r'href="/static/offline/css/bootstrap-icons.css"'),
echo     (r'src="https://cdn.jsdelivr.net/npm/sweetalert2[^"]*"', r'src="/static/offline/js/sweetalert2.all.min.js"')
echo ]
echo.
echo def process_templates(directory):
echo     """Processa recursivamente todos os arquivos HTML no diretório"""
echo     dir_path = Path(directory)
echo     for item in dir_path.glob('**/*.html'):
echo         if item.is_file():
echo             process_file(item)
echo.
echo def process_file(file_path):
echo     """Substitui referências online por offline em um arquivo"""
echo     print(f"Processando: {file_path}")
echo     try:
echo         with open(file_path, 'r', encoding='utf-8') as f:
echo             content = f.read()
echo         
echo         # Aplica as substituições
echo         modified = content
echo         for pattern, replacement in replacements:
echo             modified = re.sub(pattern, replacement, modified)
echo         
echo         # Se houve alterações, salva o arquivo modificado
echo         if modified != content:
echo             with open(file_path, 'w', encoding='utf-8') as f:
echo                 f.write(modified)
echo             print(f"Modificado: {file_path}")
echo     except Exception as e:
echo         print(f"Erro ao processar {file_path}: {e}")
echo.
echo if __name__ == "__main__":
echo     process_templates(template_dir)
echo     print("Concluído!")
) > "%PROGRAMFILES%\ControleAcesso\app\offline_setup.py"

python "%PROGRAMFILES%\ControleAcesso\app\offline_setup.py" > "%TEMP%\ControleAcesso_Install_Logs\offline_setup.log" 2>&1

:: Roda o collectstatic novamente para copiar os arquivos offline
python manage.py collectstatic --noinput > "%TEMP%\ControleAcesso_Install_Logs\collectstatic_offline.log" 2>&1

:: Cria usuário admin personalizado
echo - Criando usuario administrador...
python manage.py shell -c "from django.contrib.auth.models import User; User.objects.create_superuser('%ADMIN_USER%', '%ADMIN_EMAIL%', '%ADMIN_PASS%') if not User.objects.filter(username='%ADMIN_USER%').exists() else None"

:: Cria script para iniciar o serveo e enviar webhook
echo - Configurando script do serveo com webhook...
copy "%~dp0scripts\start_serveo.bat" "%PROGRAMFILES%\ControleAcesso\scripts\start_serveo.bat"

:: Cria script para iniciar o servidor Django em modo offline-ready
echo - Configurando script para iniciar o servidor...
(
echo @echo off
echo cd /d "%%~dp0..\app"
echo call "%%PROGRAMFILES%%\ControleAcesso\venv\Scripts\activate"
echo.
echo :: Configurações para continuar funcionando sem internet
echo set DJANGO_OFFLINE_MODE=True
echo.
echo :: Inicia o servidor em modo de produção
echo python run_production.py --insecure
) > "%PROGRAMFILES%\ControleAcesso\scripts\start_server.bat"

:: Cria script de atualização
echo - Configurando script de atualizacao...
(
echo @echo off
echo cd /d "%%~dp0..\app"
echo.
echo :: Verifica conexão com a internet
echo ping -n 1 github.com ^>nul 2^>^&1
echo if errorlevel 1 ^(
echo   echo Sem conexão com a internet. Atualização adiada.
echo   exit /b 0
echo ^)
echo.
echo :: Faz backup do banco de dados
echo copy "%%~dp0..\app\db.sqlite3" "%%~dp0..\backups\db_backup_%%date:~6,4%%_%%date:~3,2%%_%%date:~0,2%%.sqlite3" /Y
echo.
echo :: Para os serviços
echo net stop ControleAcesso
echo net stop ServeoService
echo.
echo :: Atualiza do repositório
echo call "%%PROGRAMFILES%%\ControleAcesso\venv\Scripts\activate"
echo cd "%%PROGRAMFILES%%\ControleAcesso\app"
echo git pull
echo.
echo :: Atualiza dependências
echo pip install -r requirements.txt
echo.
echo :: Atualiza banco de dados
echo python manage.py migrate
echo python manage.py collectstatic --noinput
echo.
echo :: Reinicia os serviços
echo net start ControleAcesso
echo net start ServeoService
echo.
echo :: Reinicia o serveo para obter nova URL
echo call "%%~dp0start_serveo.bat"
) > "%PROGRAMFILES%\ControleAcesso\scripts\update.bat"

:: Cria serviço Windows para o Django
echo - Instalando servico Django...
nssm install ControleAcesso "%PROGRAMFILES%\ControleAcesso\scripts\start_server.bat"
nssm set ControleAcesso DisplayName "Sistema de Controle de Acesso"
nssm set ControleAcesso Description "Servidor do Sistema de Controle de Acesso"
nssm set ControleAcesso Start SERVICE_AUTO_START
nssm set ControleAcesso AppStdout "%PROGRAMFILES%\ControleAcesso\logs\django_output.log"
nssm set ControleAcesso AppStderr "%PROGRAMFILES%\ControleAcesso\logs\django_error.log"

:: Cria serviço Windows para o serveo
echo - Instalando servico serveo...
nssm install ServeoService "%PROGRAMFILES%\ControleAcesso\scripts\start_serveo.bat"
nssm set ServeoService DisplayName "Serveo Tunnel"
nssm set ServeoService Description "Serviço de túnel para exposição da aplicação"
nssm set ServeoService Start SERVICE_AUTO_START
nssm set ServeoService AppStdout "%PROGRAMFILES%\ControleAcesso\logs\serveo_output.log"
nssm set ServeoService AppStderr "%PROGRAMFILES%\ControleAcesso\logs\serveo_error.log"
nssm set ServeoService DependOnService ControleAcesso

:: Cria atalho na área de trabalho
echo - Criando atalhos do sistema...
powershell -Command "$WS = New-Object -ComObject WScript.Shell; $SC = $WS.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\Controle de Acesso.url'); $SC.TargetPath = 'http://localhost:8000'; $SC.Save()"

:: Cria atalho no Menu Iniciar
echo - Criando atalho no Menu Iniciar...
powershell -Command "$WS = New-Object -ComObject WScript.Shell; $StartMenu = [Environment]::GetFolderPath('StartMenu') + '\Programs'; if(!(Test-Path -Path \"$StartMenu\ControleAcesso\")) { New-Item -Path \"$StartMenu\ControleAcesso\" -ItemType Directory -Force }; $SC = $WS.CreateShortcut(\"$StartMenu\ControleAcesso\Controle de Acesso.url\"); $SC.TargetPath = 'http://localhost:8000'; $SC.IconLocation = '%SystemRoot%\System32\imageres.dll,6'; $SC.Save()"

:: Cria atalho e fixa na barra de tarefas (funciona no Windows 10/11)
echo - Fixando atalho na barra de tarefas...
powershell -Command "$TargetPath = 'http://localhost:8000'; $ShortcutPath = \"$env:TEMP\ControleAcesso.url\"; $WS = New-Object -ComObject WScript.Shell; $SC = $WS.CreateShortcut($ShortcutPath); $SC.TargetPath = $TargetPath; $SC.IconLocation = '%SystemRoot%\System32\imageres.dll,6'; $SC.Save(); $Shell = New-Object -ComObject Shell.Application; $Folder = $Shell.Namespace((Split-Path $ShortcutPath)); $Item = $Folder.ParseName((Split-Path $ShortcutPath -Leaf)); $Item.InvokeVerb('taskbarpin'); Start-Sleep -Seconds 1"

:: Configura atualização automática
echo - Configurando atualizacao automatica...
schtasks /create /tn "AtualizarControleAcesso_Manha" /tr "\"%PROGRAMFILES%\ControleAcesso\scripts\update.bat\"" /sc daily /st 06:00 /ru SYSTEM /f
schtasks /create /tn "AtualizarControleAcesso_Tarde" /tr "\"%PROGRAMFILES%\ControleAcesso\scripts\update.bat\"" /sc daily /st 18:00 /ru SYSTEM /f

:: Inicia os serviços
echo - Iniciando servicos...
net start ControleAcesso
net start ServeoService

echo.
echo ============================================
echo      Instalacao concluida com sucesso!
echo ============================================
echo.
echo Informacoes importantes:
echo - Usuario: %ADMIN_USER%
echo - Email: %ADMIN_EMAIL%
echo - URL local: http://localhost:8000
echo - URL remota: Verifique no Discord ou no arquivo:
echo   %PROGRAMFILES%\ControleAcesso\logs\current_url.txt
echo.
echo Logs do sistema:
echo - Django: %PROGRAMFILES%\ControleAcesso\logs\django_*.log
echo - Serveo: %PROGRAMFILES%\ControleAcesso\logs\serveo*.log
echo.
echo Scripts de manutencao:
echo Os scripts de manutencao estao em:
echo %PROGRAMFILES%\ControleAcesso\scripts
echo.
echo Atualizacao automatica configurada para executar as 06:00 e 18:00
echo.
echo Pressione qualquer tecla para concluir...
pause > nul 