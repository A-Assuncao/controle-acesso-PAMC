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

:: Verificar Python
echo - Verificando Python...
set PYTHON_CMD=python

:: Testar o comando Python
echo Testando comando Python...
%PYTHON_CMD% --version
if %errorLevel% neq 0 (
    echo.
    echo ERRO: Não foi possível executar o comando Python.
    echo Verifique se o Python está instalado e no PATH do sistema.
    echo.
    pause
    exit /b 1
)

echo Comando Python verificado com sucesso!
call :log "INFO" "Python encontrado."

:: Aviso sobre NSSM
echo.
echo AVISO: O NSSM é necessário para instalar o sistema como serviço do Windows.
echo Se você deseja essa funcionalidade, instale o NSSM manualmente.
echo Download: https://nssm.cc/download
echo.
echo Pressione qualquer tecla para continuar...
pause >nul
call :log "INFO" "Aviso sobre NSSM exibido"

:: Criar diretórios necessários
echo Criando diretorios de instalacao...
call :log "INFO" "Criando diretorios de instalacao"
if not exist "%INSTALL_ROOT%" mkdir "%INSTALL_ROOT%"
if not exist "%APP_DIR%" mkdir "%APP_DIR%"
if not exist "%SCRIPTS_DIR%" mkdir "%SCRIPTS_DIR%"
if not exist "%BACKUPS_DIR%" mkdir "%BACKUPS_DIR%"

:: Copiar arquivos do projeto
echo Copiando arquivos do projeto...
call :log "INFO" "Copiando arquivos do projeto"
xcopy /E /I /Y "%~dp0*" "%APP_DIR%"

:: Criar ambiente virtual
echo Criando ambiente virtual Python...
call :log "INFO" "Criando ambiente virtual Python"
%PYTHON_CMD% -m venv "%VENV_DIR%"
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
%PYTHON_CMD% -m pip install --upgrade pip
if %errorLevel% neq 0 (
    call :log "ERRO" "Falha ao atualizar pip"
    echo ERRO: Falha ao atualizar pip.
    pause
    exit /b 1
)

cd /d "%APP_DIR%"
pip install -r requirements.txt
if %errorLevel% neq 0 (
    call :log "ERRO" "Falha ao instalar dependencias"
    echo ERRO: Falha ao instalar dependencias.
    echo Verifique sua conexao com a internet.
    pause
    exit /b 1
)

:: Verificar dependências críticas
echo Verificando dependências críticas...
call :log "INFO" "Verificando dependências críticas"
%PYTHON_CMD% -c "import django, openpyxl, pandas, reportlab" 2>nul
if %errorLevel% neq 0 (
    call :log "ERRO" "Algumas dependências críticas não foram instaladas corretamente"
    echo ERRO: Algumas dependências críticas não foram instaladas corretamente.
    echo Tentando instalar pacotes específicos...
    
    pip install openpyxl pandas reportlab
    if !errorLevel! neq 0 (
        call :log "ERRO" "Falha ao instalar dependências críticas"
        echo ERRO: Falha ao instalar dependências críticas.
        pause
        exit /b 1
    )
)

:: Configurar arquivo .env
echo Configurando arquivo .env...
call :log "INFO" "Configurando arquivo .env"
echo DEBUG=False > "%APP_DIR%\.env"
echo SECRET_KEY=!RANDOM!!RANDOM!!RANDOM!!RANDOM!!RANDOM!!RANDOM!!RANDOM!!RANDOM! >> "%APP_DIR%\.env"
echo ALLOWED_HOSTS=localhost,127.0.0.1 >> "%APP_DIR%\.env"
echo DATABASE_URL=sqlite:///db.sqlite3 >> "%APP_DIR%\.env"

:: Configurar key_location.txt
echo Configurando key_location.txt...
call :log "INFO" "Configurando key_location.txt"
echo %APP_DIR%\key_location.txt > "%APP_DIR%\key_location.txt"

:: Configurar banco de dados
echo Configurando banco de dados...
call :log "INFO" "Configurando banco de dados"
%PYTHON_CMD% manage.py migrate
if %errorLevel% neq 0 (
    call :log "ERRO" "Falha ao configurar banco de dados"
    echo ERRO: Falha ao configurar banco de dados.
    pause
    exit /b 1
)

:: Coletar arquivos estáticos
echo Coletando arquivos estaticos...
call :log "INFO" "Coletando arquivos estaticos"
%PYTHON_CMD% manage.py collectstatic --noinput
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

:: Configurar variáveis de ambiente para o superusuário
echo DJANGO_SUPERUSER_USERNAME=!ADMIN_USER! > superuser_env.txt
echo DJANGO_SUPERUSER_EMAIL=!ADMIN_EMAIL! >> superuser_env.txt
echo DJANGO_SUPERUSER_PASSWORD=!ADMIN_PASS! >> superuser_env.txt

:: Criar superusuário usando manage.py
echo Executando createsuperuser...
call :log "INFO" "Executando createsuperuser com %ADMIN_USER%"
set /p DJANGO_SUPERUSER_USERNAME=<superuser_env.txt
set /p DJANGO_SUPERUSER_EMAIL=<superuser_env.txt
set /p DJANGO_SUPERUSER_PASSWORD=<superuser_env.txt
%PYTHON_CMD% manage.py createsuperuser --noinput
if %errorLevel% neq 0 (
    call :log "ERRO" "Falha ao criar superusuario com manage.py"
    echo ERRO: Falha ao criar superusuario com manage.py.
    
    :: Tentar método alternativo com shell
    echo Tentando método alternativo...
    %PYTHON_CMD% manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('!ADMIN_USER!', '!ADMIN_EMAIL!', '!ADMIN_PASS!') if not User.objects.filter(username='!ADMIN_USER!').exists() else print('Usuario ja existe')"
    if !errorLevel! neq 0 (
        call :log "ERRO" "Falha ao criar superusuario com método alternativo"
        echo ERRO: Falha ao criar superusuario.
        pause
        exit /b 1
    )
)

:: Limpar arquivo temporário
del superuser_env.txt

:: Copiar scripts
echo Copiando e corrigindo scripts...
call :log "INFO" "Copiando e corrigindo scripts para o diretorio de instalacao"

:: Verificar e criar diretório de scripts
if not exist "%SCRIPTS_DIR%" mkdir "%SCRIPTS_DIR%"

:: Criar/atualizar scripts
echo Criando scripts essenciais...

:: 1. Corrigir script update.bat
echo @echo off > "%SCRIPTS_DIR%\update.bat"
echo echo Atualizando Sistema de Controle de Acesso... >> "%SCRIPTS_DIR%\update.bat"
echo. >> "%SCRIPTS_DIR%\update.bat"
echo :: Vai para o diretório da aplicação >> "%SCRIPTS_DIR%\update.bat"
echo cd /d "%APP_DIR%" >> "%SCRIPTS_DIR%\update.bat"
echo. >> "%SCRIPTS_DIR%\update.bat"
echo :: Verifica se o serviço está instalado antes de tentar parar >> "%SCRIPTS_DIR%\update.bat"
echo sc query ControleAcesso >nul 2>&1 >> "%SCRIPTS_DIR%\update.bat"
echo if not %%errorlevel%% == 1060 ( >> "%SCRIPTS_DIR%\update.bat"
echo     echo Parando servico ControleAcesso... >> "%SCRIPTS_DIR%\update.bat"
echo     net stop ControleAcesso >> "%SCRIPTS_DIR%\update.bat"
echo ) >> "%SCRIPTS_DIR%\update.bat"
echo. >> "%SCRIPTS_DIR%\update.bat"
echo :: Ativa o ambiente virtual >> "%SCRIPTS_DIR%\update.bat"
echo call "%VENV_DIR%\Scripts\activate.bat" >> "%SCRIPTS_DIR%\update.bat"
echo. >> "%SCRIPTS_DIR%\update.bat"
echo :: Backup do banco de dados >> "%SCRIPTS_DIR%\update.bat"
echo echo Criando backup do banco de dados... >> "%SCRIPTS_DIR%\update.bat"
echo if not exist "%BACKUPS_DIR%" mkdir "%BACKUPS_DIR%" >> "%SCRIPTS_DIR%\update.bat"
echo %PYTHON_CMD% manage.py dumpdata ^> "%BACKUPS_DIR%\backup_%%date:~6,4%%-%%date:~3,2%%-%%date:~0,2%%.json" >> "%SCRIPTS_DIR%\update.bat"
echo. >> "%SCRIPTS_DIR%\update.bat"
echo :: Atualiza dependências >> "%SCRIPTS_DIR%\update.bat"
echo echo Atualizando dependencias... >> "%SCRIPTS_DIR%\update.bat"
echo pip install -r requirements.txt >> "%SCRIPTS_DIR%\update.bat"
echo. >> "%SCRIPTS_DIR%\update.bat"
echo :: Aplica migrações >> "%SCRIPTS_DIR%\update.bat"
echo echo Aplicando migracoes do banco de dados... >> "%SCRIPTS_DIR%\update.bat"
echo %PYTHON_CMD% manage.py migrate >> "%SCRIPTS_DIR%\update.bat"
echo. >> "%SCRIPTS_DIR%\update.bat"
echo :: Coleta arquivos estáticos >> "%SCRIPTS_DIR%\update.bat"
echo echo Coletando arquivos estaticos... >> "%SCRIPTS_DIR%\update.bat"
echo %PYTHON_CMD% manage.py collectstatic --noinput >> "%SCRIPTS_DIR%\update.bat"
echo. >> "%SCRIPTS_DIR%\update.bat"
echo :: Inicia os serviços se estiverem instalados >> "%SCRIPTS_DIR%\update.bat"
echo sc query ControleAcesso >nul 2>&1 >> "%SCRIPTS_DIR%\update.bat"
echo if not %%errorlevel%% == 1060 ( >> "%SCRIPTS_DIR%\update.bat"
echo     echo Iniciando servico ControleAcesso... >> "%SCRIPTS_DIR%\update.bat"
echo     net start ControleAcesso >> "%SCRIPTS_DIR%\update.bat"
echo ) >> "%SCRIPTS_DIR%\update.bat"
echo. >> "%SCRIPTS_DIR%\update.bat"
echo echo Atualizacao concluida! >> "%SCRIPTS_DIR%\update.bat"
echo echo. >> "%SCRIPTS_DIR%\update.bat"
echo echo Pressione qualquer tecla para sair... >> "%SCRIPTS_DIR%\update.bat"
echo pause^>nul >> "%SCRIPTS_DIR%\update.bat"
call :log "INFO" "Script update.bat corrigido"

:: 2. Corrigir script schedule_update.bat
echo @echo off > "%SCRIPTS_DIR%\schedule_update.bat"
echo echo Configurando atualizacao automatica... >> "%SCRIPTS_DIR%\schedule_update.bat"
echo. >> "%SCRIPTS_DIR%\schedule_update.bat"
echo :: Cria tarefa agendada para atualização diária >> "%SCRIPTS_DIR%\schedule_update.bat"
echo schtasks /create /tn "AtualizarControleAcesso" /tr "\"%SCRIPTS_DIR%\update.bat\"" /sc daily /st 03:00 /f >> "%SCRIPTS_DIR%\schedule_update.bat"
echo. >> "%SCRIPTS_DIR%\schedule_update.bat"
echo :: Verifica se a tarefa foi criada com sucesso >> "%SCRIPTS_DIR%\schedule_update.bat"
echo schtasks /query /tn "AtualizarControleAcesso" >nul 2>&1 >> "%SCRIPTS_DIR%\schedule_update.bat"
echo if %%errorlevel%% == 0 ( >> "%SCRIPTS_DIR%\schedule_update.bat"
echo     echo Atualizacao automatica configurada para executar diariamente as 03:00 >> "%SCRIPTS_DIR%\schedule_update.bat"
echo ) else ( >> "%SCRIPTS_DIR%\schedule_update.bat"
echo     echo ERRO: Falha ao configurar atualizacao automatica >> "%SCRIPTS_DIR%\schedule_update.bat"
echo ) >> "%SCRIPTS_DIR%\schedule_update.bat"
echo. >> "%SCRIPTS_DIR%\schedule_update.bat"
echo echo Pressione qualquer tecla para continuar... >> "%SCRIPTS_DIR%\schedule_update.bat"
echo pause^>nul >> "%SCRIPTS_DIR%\schedule_update.bat"
call :log "INFO" "Script schedule_update.bat corrigido"

:: 3. Corrigir script start_serveo.bat
echo @echo off > "%SCRIPTS_DIR%\start_serveo.bat"
echo echo Iniciando o tunel serveo... >> "%SCRIPTS_DIR%\start_serveo.bat"
echo. >> "%SCRIPTS_DIR%\start_serveo.bat"
echo :: Ativa o ambiente virtual >> "%SCRIPTS_DIR%\start_serveo.bat"
echo cd /d "%APP_DIR%" >> "%SCRIPTS_DIR%\start_serveo.bat"
echo call "%VENV_DIR%\Scripts\activate.bat" >> "%SCRIPTS_DIR%\start_serveo.bat"
echo. >> "%SCRIPTS_DIR%\start_serveo.bat"
echo :: Executa o script Python >> "%SCRIPTS_DIR%\start_serveo.bat"
echo %PYTHON_CMD% "%SCRIPTS_DIR%\start_serveo.py" >> "%SCRIPTS_DIR%\start_serveo.bat"
echo. >> "%SCRIPTS_DIR%\start_serveo.bat"
echo :: Mantém o terminal aberto em caso de erro >> "%SCRIPTS_DIR%\start_serveo.bat"
echo pause >> "%SCRIPTS_DIR%\start_serveo.bat"
call :log "INFO" "Script start_serveo.bat corrigido"

:: 4. Corrigir script start_serveo.py
echo import subprocess >> "%SCRIPTS_DIR%\start_serveo.py"
echo import sys >> "%SCRIPTS_DIR%\start_serveo.py"
echo import os >> "%SCRIPTS_DIR%\start_serveo.py"
echo import time >> "%SCRIPTS_DIR%\start_serveo.py"
echo import logging >> "%SCRIPTS_DIR%\start_serveo.py"
echo import re >> "%SCRIPTS_DIR%\start_serveo.py"
echo from pathlib import Path >> "%SCRIPTS_DIR%\start_serveo.py"
echo. >> "%SCRIPTS_DIR%\start_serveo.py"
echo # Tenta importar requests, mas continua mesmo se falhar >> "%SCRIPTS_DIR%\start_serveo.py"
echo try: >> "%SCRIPTS_DIR%\start_serveo.py"
echo     import requests >> "%SCRIPTS_DIR%\start_serveo.py"
echo     REQUESTS_AVAILABLE = True >> "%SCRIPTS_DIR%\start_serveo.py"
echo except ImportError: >> "%SCRIPTS_DIR%\start_serveo.py"
echo     REQUESTS_AVAILABLE = False >> "%SCRIPTS_DIR%\start_serveo.py"
echo. >> "%SCRIPTS_DIR%\start_serveo.py"
echo # Configuração de logging >> "%SCRIPTS_DIR%\start_serveo.py"
echo log_dir = Path(r'%LOG_DIR%') >> "%SCRIPTS_DIR%\start_serveo.py"
echo log_dir.mkdir(exist_ok=True) >> "%SCRIPTS_DIR%\start_serveo.py"
echo. >> "%SCRIPTS_DIR%\start_serveo.py"
echo logging.basicConfig( >> "%SCRIPTS_DIR%\start_serveo.py"
echo     level=logging.INFO, >> "%SCRIPTS_DIR%\start_serveo.py"
echo     format='%%(asctime)s - %%(levelname)s - %%(message)s', >> "%SCRIPTS_DIR%\start_serveo.py"
echo     handlers=[ >> "%SCRIPTS_DIR%\start_serveo.py"
echo         logging.FileHandler(log_dir / "serveo.log"), >> "%SCRIPTS_DIR%\start_serveo.py"
echo         logging.StreamHandler(sys.stdout) >> "%SCRIPTS_DIR%\start_serveo.py"
echo     ] >> "%SCRIPTS_DIR%\start_serveo.py"
echo ) >> "%SCRIPTS_DIR%\start_serveo.py"
echo. >> "%SCRIPTS_DIR%\start_serveo.py"
echo def send_to_discord(url): >> "%SCRIPTS_DIR%\start_serveo.py"
echo     """Envia o link do serveo para o Discord via webhook""" >> "%SCRIPTS_DIR%\start_serveo.py"
echo     if not REQUESTS_AVAILABLE: >> "%SCRIPTS_DIR%\start_serveo.py"
echo         logging.warning("Módulo requests não instalado. Não é possível enviar para o Discord.") >> "%SCRIPTS_DIR%\start_serveo.py"
echo         return >> "%SCRIPTS_DIR%\start_serveo.py"
echo. >> "%SCRIPTS_DIR%\start_serveo.py"
echo     webhook_url = os.getenv('DISCORD_WEBHOOK_URL') >> "%SCRIPTS_DIR%\start_serveo.py"
echo     if not webhook_url: >> "%SCRIPTS_DIR%\start_serveo.py"
echo         logging.warning("URL do webhook do Discord não configurada. Pulando envio.") >> "%SCRIPTS_DIR%\start_serveo.py"
echo         return >> "%SCRIPTS_DIR%\start_serveo.py"
echo. >> "%SCRIPTS_DIR%\start_serveo.py"
echo     try: >> "%SCRIPTS_DIR%\start_serveo.py"
echo         payload = { >> "%SCRIPTS_DIR%\start_serveo.py"
echo             "content": f"🌐 Nova URL do Sistema de Controle de Acesso: {url}" >> "%SCRIPTS_DIR%\start_serveo.py"
echo         } >> "%SCRIPTS_DIR%\start_serveo.py"
echo         response = requests.post(webhook_url, json=payload) >> "%SCRIPTS_DIR%\start_serveo.py"
echo         response.raise_for_status() >> "%SCRIPTS_DIR%\start_serveo.py"
echo         logging.info("Link enviado com sucesso para o Discord") >> "%SCRIPTS_DIR%\start_serveo.py"
echo     except Exception as e: >> "%SCRIPTS_DIR%\start_serveo.py"
echo         logging.error(f"Erro ao enviar para o Discord: {str(e)}") >> "%SCRIPTS_DIR%\start_serveo.py"
echo. >> "%SCRIPTS_DIR%\start_serveo.py"
echo def start_serveo(): >> "%SCRIPTS_DIR%\start_serveo.py"
echo     """Inicia o túnel do serveo para a porta 8000""" >> "%SCRIPTS_DIR%\start_serveo.py"
echo     try: >> "%SCRIPTS_DIR%\start_serveo.py"
echo         # Comando para iniciar o serveo >> "%SCRIPTS_DIR%\start_serveo.py"
echo         cmd = "ssh -R 80:localhost:8000 serveo.net" >> "%SCRIPTS_DIR%\start_serveo.py"
echo. >> "%SCRIPTS_DIR%\start_serveo.py"
echo         logging.info("Iniciando túnel do serveo...") >> "%SCRIPTS_DIR%\start_serveo.py"
echo         print("Iniciando túnel do serveo... Aguarde a conexão ser estabelecida.") >> "%SCRIPTS_DIR%\start_serveo.py"
echo. >> "%SCRIPTS_DIR%\start_serveo.py"
echo         # Executa o comando >> "%SCRIPTS_DIR%\start_serveo.py"
echo         process = subprocess.Popen( >> "%SCRIPTS_DIR%\start_serveo.py"
echo             cmd, >> "%SCRIPTS_DIR%\start_serveo.py"
echo             shell=True, >> "%SCRIPTS_DIR%\start_serveo.py"
echo             stdout=subprocess.PIPE, >> "%SCRIPTS_DIR%\start_serveo.py"
echo             stderr=subprocess.PIPE, >> "%SCRIPTS_DIR%\start_serveo.py"
echo             universal_newlines=True >> "%SCRIPTS_DIR%\start_serveo.py"
echo         ) >> "%SCRIPTS_DIR%\start_serveo.py"
echo. >> "%SCRIPTS_DIR%\start_serveo.py"
echo         # Padrão para encontrar a URL do serveo >> "%SCRIPTS_DIR%\start_serveo.py"
echo         url_pattern = r'https?://[^\s]+' >> "%SCRIPTS_DIR%\start_serveo.py"
echo. >> "%SCRIPTS_DIR%\start_serveo.py"
echo         # Monitora a saída do processo >> "%SCRIPTS_DIR%\start_serveo.py"
echo         while True: >> "%SCRIPTS_DIR%\start_serveo.py"
echo             output = process.stdout.readline() >> "%SCRIPTS_DIR%\start_serveo.py"
echo             if output: >> "%SCRIPTS_DIR%\start_serveo.py"
echo                 output = output.strip() >> "%SCRIPTS_DIR%\start_serveo.py"
echo                 logging.info(output) >> "%SCRIPTS_DIR%\start_serveo.py"
echo                 print(output) >> "%SCRIPTS_DIR%\start_serveo.py"
echo. >> "%SCRIPTS_DIR%\start_serveo.py"
echo                 # Procura por URLs na saída >> "%SCRIPTS_DIR%\start_serveo.py"
echo                 if 'Forwarding HTTP traffic from' in output: >> "%SCRIPTS_DIR%\start_serveo.py"
echo                     urls = re.findall(url_pattern, output) >> "%SCRIPTS_DIR%\start_serveo.py"
echo                     if urls: >> "%SCRIPTS_DIR%\start_serveo.py"
echo                         serveo_url = urls[0] >> "%SCRIPTS_DIR%\start_serveo.py"
echo                         print(f"\nURL de acesso externo: {serveo_url}\n") >> "%SCRIPTS_DIR%\start_serveo.py"
echo. >> "%SCRIPTS_DIR%\start_serveo.py"
echo                         # Salva a URL atual em um arquivo >> "%SCRIPTS_DIR%\start_serveo.py"
echo                         url_file = log_dir / "current_url.txt" >> "%SCRIPTS_DIR%\start_serveo.py"
echo                         with open(url_file, "w") as f: >> "%SCRIPTS_DIR%\start_serveo.py"
echo                             f.write(serveo_url) >> "%SCRIPTS_DIR%\start_serveo.py"
echo                         print(f"URL salva em: {url_file}") >> "%SCRIPTS_DIR%\start_serveo.py"
echo. >> "%SCRIPTS_DIR%\start_serveo.py"
echo                         # Envia para o Discord >> "%SCRIPTS_DIR%\start_serveo.py"
echo                         if REQUESTS_AVAILABLE: >> "%SCRIPTS_DIR%\start_serveo.py"
echo                             send_to_discord(serveo_url) >> "%SCRIPTS_DIR%\start_serveo.py"
echo. >> "%SCRIPTS_DIR%\start_serveo.py"
echo             error = process.stderr.readline() >> "%SCRIPTS_DIR%\start_serveo.py"
echo             if error: >> "%SCRIPTS_DIR%\start_serveo.py"
echo                 error = error.strip() >> "%SCRIPTS_DIR%\start_serveo.py"
echo                 logging.error(error) >> "%SCRIPTS_DIR%\start_serveo.py"
echo                 print(f"ERRO: {error}") >> "%SCRIPTS_DIR%\start_serveo.py"
echo. >> "%SCRIPTS_DIR%\start_serveo.py"
echo             # Verifica se o processo ainda está rodando >> "%SCRIPTS_DIR%\start_serveo.py"
echo             if process.poll() is not None: >> "%SCRIPTS_DIR%\start_serveo.py"
echo                 logging.error("O processo do serveo foi encerrado. Tentando reconectar...") >> "%SCRIPTS_DIR%\start_serveo.py"
echo                 print("\nO processo do serveo foi encerrado. Tentando reconectar...\n") >> "%SCRIPTS_DIR%\start_serveo.py"
echo                 time.sleep(5)  # Espera 5 segundos antes de tentar reconectar >> "%SCRIPTS_DIR%\start_serveo.py"
echo                 process = subprocess.Popen( >> "%SCRIPTS_DIR%\start_serveo.py"
echo                     cmd, >> "%SCRIPTS_DIR%\start_serveo.py"
echo                     shell=True, >> "%SCRIPTS_DIR%\start_serveo.py"
echo                     stdout=subprocess.PIPE, >> "%SCRIPTS_DIR%\start_serveo.py"
echo                     stderr=subprocess.PIPE, >> "%SCRIPTS_DIR%\start_serveo.py"
echo                     universal_newlines=True >> "%SCRIPTS_DIR%\start_serveo.py"
echo                 ) >> "%SCRIPTS_DIR%\start_serveo.py"
echo. >> "%SCRIPTS_DIR%\start_serveo.py"
echo     except Exception as e: >> "%SCRIPTS_DIR%\start_serveo.py"
echo         logging.error(f"Erro ao iniciar o serveo: {str(e)}") >> "%SCRIPTS_DIR%\start_serveo.py"
echo         print(f"ERRO: Falha ao iniciar o serveo: {str(e)}") >> "%SCRIPTS_DIR%\start_serveo.py"
echo         print("Pressione Enter para sair...") >> "%SCRIPTS_DIR%\start_serveo.py"
echo         input() >> "%SCRIPTS_DIR%\start_serveo.py"
echo         sys.exit(1) >> "%SCRIPTS_DIR%\start_serveo.py"
echo. >> "%SCRIPTS_DIR%\start_serveo.py"
echo if __name__ == "__main__": >> "%SCRIPTS_DIR%\start_serveo.py"
echo     start_serveo() >> "%SCRIPTS_DIR%\start_serveo.py"
call :log "INFO" "Script start_serveo.py corrigido"

:: 5. Criar script start_server.bat para conveniência
echo @echo off > "%SCRIPTS_DIR%\start_server.bat"
echo echo Iniciando Servidor de Controle de Acesso... >> "%SCRIPTS_DIR%\start_server.bat"
echo cd /d "%APP_DIR%" >> "%SCRIPTS_DIR%\start_server.bat"
echo call "%VENV_DIR%\Scripts\activate.bat" >> "%SCRIPTS_DIR%\start_server.bat"
echo %PYTHON_CMD% manage.py runserver 0.0.0.0:8000 >> "%SCRIPTS_DIR%\start_server.bat"
echo pause >> "%SCRIPTS_DIR%\start_server.bat"
call :log "INFO" "Script start_server.bat criado"

echo Criando atalhos no menu iniciar...
if not exist "%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs\Controle de Acesso" (
    mkdir "%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs\Controle de Acesso"
)
echo @echo off > "%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs\Controle de Acesso\Iniciar Servidor.bat"
echo start "" "%SCRIPTS_DIR%\start_server.bat" >> "%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs\Controle de Acesso\Iniciar Servidor.bat"
echo @echo off > "%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs\Controle de Acesso\Iniciar Serveo.bat"
echo start "" "%SCRIPTS_DIR%\start_serveo.bat" >> "%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs\Controle de Acesso\Iniciar Serveo.bat"
echo @echo off > "%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs\Controle de Acesso\Atualizar Sistema.bat"
echo start "" "%SCRIPTS_DIR%\update.bat" >> "%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs\Controle de Acesso\Atualizar Sistema.bat"

call :log "INFO" "Atalhos criados no menu iniciar"
call :log "INFO" "Scripts corrigidos e criados com sucesso"

echo Scripts corrigidos e criados com sucesso em %SCRIPTS_DIR%

:: Verificar se instalação NSSM está sendo executada
echo.
echo Verificando se deseja instalar como servico Windows...
call :log "INFO" "Verificando se deseja instalar como servico Windows"
echo Deseja instalar o sistema como servico do Windows? (S/N)
set /p INSTALL_SERVICE=
echo Resposta do usuario: %INSTALL_SERVICE%
call :log "INFO" "Resposta do usuario para instalar como servico: %INSTALL_SERVICE%"

:: Adicionar tratamento para resposta vazia ou não reconhecida
if "%INSTALL_SERVICE%"=="" (
    set INSTALL_SERVICE=N
    echo Nenhuma resposta fornecida, assumindo 'N'.
    call :log "INFO" "Nenhuma resposta fornecida para instalar servico, assumindo N"
)

echo Opção selecionada: %INSTALL_SERVICE%

if /i "%INSTALL_SERVICE%"=="S" (
    call :log "INFO" "Instalando o sistema como servico do Windows"
    echo Instalando o sistema como servico do Windows...
    
    :: Verificar se o NSSM está disponível
    echo Verificando NSSM...
    where nssm >nul 2>&1
    if !errorLevel! neq 0 (
        call :log "ERRO" "NSSM nao encontrado. O sistema nao sera instalado como servico."
        echo ERRO: NSSM nao encontrado. O sistema nao sera instalado como servico.
        echo Por favor, instale o NSSM manualmente e tente novamente.
        echo Download: https://nssm.cc/download
        echo.
        echo Pressione qualquer tecla para continuar sem instalar o servico...
        pause >nul
    ) else (
        call :log "INFO" "NSSM encontrado. Continuando instalação como serviço."
        echo NSSM encontrado. Continuando instalação como serviço.
        echo.
        echo Configurando servico ControleAcesso usando NSSM...
        call :log "INFO" "Configurando servico ControleAcesso usando NSSM"
        
        :: Salvar os comandos em um arquivo de log para diagnóstico
        echo Tentando executar: nssm install ControleAcesso "%SCRIPTS_DIR%\start_server.bat" > "%LOG_DIR%\nssm_commands.log"
        
        :: Instala o serviço principal com tratamento de erros
        nssm install ControleAcesso "%SCRIPTS_DIR%\start_server.bat" >nul 2>"%LOG_DIR%\nssm_install_error.log"
        if !errorLevel! neq 0 (
            call :log "ERRO" "Falha ao instalar servico ControleAcesso com NSSM (Erro: !errorLevel!)"
            echo ERRO: Falha ao instalar servico ControleAcesso com NSSM.
            echo Codigo de erro: !errorLevel!
            echo Verifique o arquivo de log: "%LOG_DIR%\nssm_install_error.log"
            echo.
            echo Pressione qualquer tecla para continuar sem instalar o servico...
            pause >nul
        ) else (
            echo Servico criado. Configurando parametros...
            call :log "INFO" "Serviço ControleAcesso criado. Configurando parâmetros."
            
            nssm set ControleAcesso DisplayName "Sistema de Controle de Acesso" >>"%LOG_DIR%\nssm_commands.log" 2>&1
            nssm set ControleAcesso Description "Servidor web do Sistema de Controle de Acesso" >>"%LOG_DIR%\nssm_commands.log" 2>&1
            nssm set ControleAcesso Start SERVICE_AUTO_START >>"%LOG_DIR%\nssm_commands.log" 2>&1
            nssm set ControleAcesso AppStdout "%LOG_DIR%\service_stdout.log" >>"%LOG_DIR%\nssm_commands.log" 2>&1
            nssm set ControleAcesso AppStderr "%LOG_DIR%\service_stderr.log" >>"%LOG_DIR%\nssm_commands.log" 2>&1
            
            echo Configuração do serviço concluída.
            echo.
            echo Iniciando servico ControleAcesso...
            call :log "INFO" "Tentando iniciar o serviço ControleAcesso"
            
            net start ControleAcesso >"%LOG_DIR%\service_start.log" 2>&1
            if !errorLevel! neq 0 (
                call :log "ERRO" "Falha ao iniciar o servico ControleAcesso (Erro: !errorLevel!)"
                echo ERRO: Falha ao iniciar o servico ControleAcesso.
                echo Codigo de erro: !errorLevel!
                echo Verifique o arquivo de log: "%LOG_DIR%\service_start.log"
                echo O servico foi criado mas nao foi iniciado.
                echo Tente iniciar manualmente ou reinicie o computador.
                
                echo Pressione qualquer tecla para continuar...
                pause >nul
            ) else (
                call :log "INFO" "Servico ControleAcesso iniciado com sucesso"
                echo Servico ControleAcesso iniciado com sucesso.
            )
            
            :: Pergunta se deseja instalar o Serveo como serviço
            echo.
            echo Deseja instalar o servico de acesso remoto (Serveo)? (S/N)
            set /p INSTALL_SERVEO=
            echo Resposta: !INSTALL_SERVEO!
            call :log "INFO" "Resposta para instalar Serveo: !INSTALL_SERVEO!"
            
            if "!INSTALL_SERVEO!"=="" (
                set INSTALL_SERVEO=N
                echo Nenhuma resposta fornecida, assumindo 'N'.
                call :log "INFO" "Nenhuma resposta fornecida para Serveo, assumindo N"
            )
            
            if /i "!INSTALL_SERVEO!"=="S" (
                call :log "INFO" "Instalando o servico Serveo"
                echo Instalando o servico Serveo...
                echo Tentando instalar Serveo... >> "%LOG_DIR%\nssm_commands.log"
                
                nssm install ServeoService "%SCRIPTS_DIR%\start_serveo.bat" >nul 2>>"%LOG_DIR%\nssm_install_error.log"
                if !errorLevel! neq 0 (
                    call :log "ERRO" "Falha ao instalar servico ServeoService (Erro: !errorLevel!)"
                    echo ERRO: Falha ao instalar servico ServeoService.
                    echo Codigo de erro: !errorLevel!
                    echo Verifique o arquivo de log: "%LOG_DIR%\nssm_install_error.log"
                    
                    echo Pressione qualquer tecla para continuar...
                    pause >nul
                ) else (
                    echo Servico Serveo criado. Configurando parametros...
                    call :log "INFO" "Serviço ServeoService criado. Configurando parâmetros."
                    
                    nssm set ServeoService DisplayName "Serveo - Acesso Remoto" >>"%LOG_DIR%\nssm_commands.log" 2>&1
                    nssm set ServeoService Description "Servico de acesso remoto via Serveo para o Sistema de Controle de Acesso" >>"%LOG_DIR%\nssm_commands.log" 2>&1
                    nssm set ServeoService Start SERVICE_AUTO_START >>"%LOG_DIR%\nssm_commands.log" 2>&1
                    nssm set ServeoService AppStdout "%LOG_DIR%\serveo_stdout.log" >>"%LOG_DIR%\nssm_commands.log" 2>&1
                    nssm set ServeoService AppStderr "%LOG_DIR%\serveo_stderr.log" >>"%LOG_DIR%\nssm_commands.log" 2>&1
                    
                    echo Iniciando servico ServeoService...
                    call :log "INFO" "Tentando iniciar o serviço ServeoService"
                    
                    net start ServeoService >"%LOG_DIR%\serveo_start.log" 2>&1
                    if !errorLevel! neq 0 (
                        call :log "ERRO" "Falha ao iniciar o servico ServeoService (Erro: !errorLevel!)"
                        echo ERRO: Falha ao iniciar o servico ServeoService.
                        echo Verifique o arquivo de log: "%LOG_DIR%\serveo_start.log"
                        echo O servico foi criado mas nao foi iniciado.
                        
                        echo Pressione qualquer tecla para continuar...
                        pause >nul
                    ) else (
                        call :log "INFO" "Servico ServeoService iniciado com sucesso"
                        echo Servico ServeoService iniciado com sucesso.
                    )
                )
            ) else (
                call :log "INFO" "Usuário optou por não instalar o serviço Serveo"
                echo Instalação do serviço Serveo ignorada.
            )
        )
    )
) else (
    call :log "INFO" "Usuário optou por não instalar como serviço Windows"
    echo Instalação como serviço Windows ignorada.
)

echo.
echo Pressione qualquer tecla para continuar...
pause >nul

:: Configurar atualizações automáticas
echo Deseja configurar atualizacoes automaticas? (S/N)
set /p CONFIG_UPDATES=
if /i "%CONFIG_UPDATES%"=="S" (
    call :log "INFO" "Configurando atualizacoes automaticas"
    echo Configurando atualizacoes automaticas...
    
    :: Configurar script de atualização
    echo @echo off > "%SCRIPTS_DIR%\update.bat"
    echo echo Atualizando Sistema de Controle de Acesso... >> "%SCRIPTS_DIR%\update.bat"
    echo cd /d "%APP_DIR%" >> "%SCRIPTS_DIR%\update.bat"
    echo :: Para os serviços >> "%SCRIPTS_DIR%\update.bat"
    echo net stop ControleAcesso >> "%SCRIPTS_DIR%\update.bat"
    echo :: Ativa o ambiente virtual >> "%SCRIPTS_DIR%\update.bat"
    echo call "%VENV_DIR%\Scripts\activate.bat" >> "%SCRIPTS_DIR%\update.bat"
    echo :: Backup do banco de dados >> "%SCRIPTS_DIR%\update.bat"
    echo %PYTHON_CMD% manage.py dumpdata ^> "%BACKUPS_DIR%\backup_%%date:~6,4%%-%%date:~3,2%%-%%date:~0,2%%.json" >> "%SCRIPTS_DIR%\update.bat"
    echo :: Atualiza dependências >> "%SCRIPTS_DIR%\update.bat"
    echo pip install -r requirements.txt >> "%SCRIPTS_DIR%\update.bat"
    echo :: Aplica migrações >> "%SCRIPTS_DIR%\update.bat"
    echo %PYTHON_CMD% manage.py migrate >> "%SCRIPTS_DIR%\update.bat"
    echo :: Atualiza arquivos estáticos >> "%SCRIPTS_DIR%\update.bat"
    echo %PYTHON_CMD% manage.py collectstatic --noinput >> "%SCRIPTS_DIR%\update.bat"
    echo :: Inicia os serviços >> "%SCRIPTS_DIR%\update.bat"
    echo net start ControleAcesso >> "%SCRIPTS_DIR%\update.bat"
    echo echo Atualizacao concluida! >> "%SCRIPTS_DIR%\update.bat"
    echo timeout /t 5 >> "%SCRIPTS_DIR%\update.bat"
    
    :: Configurar agendamento
    echo @echo off > "%SCRIPTS_DIR%\schedule_update.bat"
    echo :: Cria tarefa agendada para atualização diária >> "%SCRIPTS_DIR%\schedule_update.bat"
    echo schtasks /create /tn "AtualizarControleAcesso" /tr "\"%SCRIPTS_DIR%\update.bat\"" /sc daily /st 03:00 /ru SYSTEM /f >> "%SCRIPTS_DIR%\schedule_update.bat"
    echo echo Atualizacao automatica configurada para executar diariamente as 03:00 >> "%SCRIPTS_DIR%\schedule_update.bat"
    echo timeout /t 5 >> "%SCRIPTS_DIR%\schedule_update.bat"
    
    :: Executar o script de agendamento
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

:: Finalização
echo.
echo ================================================
echo  Instalacao concluida com sucesso!
echo ================================================
echo.
echo O sistema foi instalado em: %INSTALL_ROOT%

if /i "%INSTALL_SERVICE%"=="S" (
    echo O sistema foi instalado como servico e ja esta em execucao.
    echo Para acessar o sistema, abra o navegador e acesse:
    echo   http://localhost:8000
) else (
    echo Para iniciar o servidor manualmente, execute:
    echo   cd "%APP_DIR%"
    echo   "%VENV_DIR%\Scripts\activate.bat"
    echo   %PYTHON_CMD% manage.py runserver
    echo.
    echo Para acessar o sistema, abra o navegador e acesse:
    echo   http://localhost:8000
)

if /i "%INSTALL_SERVEO%"=="S" (
    echo.
    echo O acesso remoto via Serveo foi configurado.
    echo O URL de acesso externo estara disponivel no arquivo:
    echo   %LOG_DIR%\current_url.txt (apos alguns minutos)
)

echo.
echo Usuario: %ADMIN_USER%
echo Email: %ADMIN_EMAIL%
echo.

if /i not "%INSTALL_SERVICE%"=="S" (
    echo Deseja iniciar o sistema agora? (S/N)
    set /p START_NOW=
    if /i "!START_NOW!"=="S" (
        start "" "%SCRIPTS_DIR%\start_server.bat"
        start http://localhost:8000/
    )
)

pause
exit /b 0

:log
echo %date% %time% [%~1] %~2 >> "%LOG_FILE%"
goto :eof 