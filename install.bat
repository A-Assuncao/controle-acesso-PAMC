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
echo Instalando sistema como servico Windows...
call :log "INFO" "Iniciando instalação como serviço Windows automaticamente"

:: Definir automaticamente que o serviço será instalado
set "INSTALL_SERVICE=S"
call :log "INFO" "Configurado para instalar como serviço: %INSTALL_SERVICE%"

:: Verificar se o NSSM está disponível com tratamento de erro aprimorado
echo Verificando NSSM...
call :log "INFO" "Verificando disponibilidade do NSSM"

:: Criar um arquivo de log específico para o NSSM
echo %date% %time% - Iniciando verificação do NSSM > "%LOG_DIR%\nssm_debug.log"

where nssm >> "%LOG_DIR%\nssm_debug.log" 2>&1
if %errorLevel% neq 0 (
    call :log "ERRO" "NSSM nao encontrado. Tentando usar versão local..."
    echo %date% %time% - NSSM não encontrado. Erro: %errorLevel% >> "%LOG_DIR%\nssm_debug.log"
    echo NSSM nao encontrado no sistema. Tentando usar versão local...
    
    :: Verificar se temos uma cópia do NSSM na pasta tools
    if exist "tools\nssm.exe" (
        echo Cópia local do NSSM encontrada. Instalando...
        call :log "INFO" "Cópia local do NSSM encontrada. Instalando..."
        
        :: Criar diretório temporário para o NSSM
        if not exist "%TEMP%\nssm" mkdir "%TEMP%\nssm"
        copy /y "tools\nssm.exe" "%TEMP%\nssm\nssm.exe" >> "%LOG_DIR%\nssm_debug.log" 2>&1
        
        :: Definir variável para usar a versão local
        set "NSSM_CMD=%TEMP%\nssm\nssm.exe"
        call :log "INFO" "NSSM local configurado em: %NSSM_CMD%"
        echo NSSM configurado. Continuando instalação...
        echo %date% %time% - Usando NSSM local: %NSSM_CMD% >> "%LOG_DIR%\nssm_debug.log"
    ) else {
        call :log "ERRO" "NSSM não encontrado e versão local não disponível"
        echo ERRO: NSSM nao encontrado. O sistema nao sera instalado como servico.
        echo Por favor, instale o NSSM manualmente e tente novamente.
        echo.
        echo O NSSM é necessário para instalar serviços no Windows.
        echo Você pode baixar o NSSM em: https://nssm.cc/download
        echo.
        echo Instruções de instalação do NSSM:
        echo 1. Baixe o arquivo nssm-2.24.zip
        echo 2. Extraia o arquivo
        echo 3. Copie nssm.exe (da pasta win64 se seu Windows for 64-bit) para C:\Windows\System32
        echo.
        call :log "INFO" "Fornecidas instruções detalhadas para instalação do NSSM"
        echo Pressione qualquer tecla para continuar sem instalar o servico...
        pause >nul
        
        :: Definir variável vazia para indicar que NSSM não está disponível
        set "NSSM_CMD="
    }
) else {
    call :log "INFO" "NSSM encontrado. Continuando instalação como serviço."
    echo %date% %time% - NSSM encontrado com sucesso >> "%LOG_DIR%\nssm_debug.log"
    echo NSSM encontrado. Continuando instalação como serviço.
    
    :: Definir variável para usar o NSSM do sistema
    set "NSSM_CMD=nssm"
    echo.
}

echo Usando NSSM: %NSSM_CMD% >> "%LOG_DIR%\nssm_debug.log"
call :log "INFO" "Usando NSSM: %NSSM_CMD%"

:: Criar código de teste para verificar o valor da variável
echo %date% %time% - Verificando valor da variável NSSM_CMD: "%NSSM_CMD%" >> "%LOG_DIR%\nssm_debug.log"

:: Só continua se o NSSM estiver disponível
if not "%NSSM_CMD%"=="" (
    call :log "INFO" "NSSM está disponível, continuando instalação do serviço"
    echo %date% %time% - NSSM está disponível, continuando instalação do serviço >> "%LOG_DIR%\nssm_debug.log"
    
    :: Remover serviços existentes se necessário
    echo Verificando serviços existentes...
    call :log "INFO" "Verificando serviços existentes"
    echo %date% %time% - Verificando serviço ControleAcesso >> "%LOG_DIR%\nssm_debug.log"
    
    :: Verifica e remove o serviço ControleAcesso se já existir
    sc query ControleAcesso > "%LOG_DIR%\sc_query_output.log" 2>&1
    if %errorLevel% equ 0 (
        echo Serviço ControleAcesso já existe, removendo...
        call :log "INFO" "Removendo serviço ControleAcesso existente"
        net stop ControleAcesso > "%LOG_DIR%\net_stop_output.log" 2>&1
        %NSSM_CMD% remove ControleAcesso confirm > "%LOG_DIR%\nssm_remove_output.log" 2>&1
        timeout /t 2 >nul
    )
    
    :: Instalar serviço ControleAcesso
    echo Instalando serviço ControleAcesso...
    call :log "INFO" "Instalando serviço ControleAcesso"
    echo %date% %time% - Executando: %NSSM_CMD% install ControleAcesso "%SCRIPTS_DIR%\start_server.bat" >> "%LOG_DIR%\nssm_debug.log"
    
    :: Usar método de instalação direta do NSSM - baseado na documentação
    %NSSM_CMD% install ControleAcesso "%SCRIPTS_DIR%\start_server.bat" > "%LOG_DIR%\nssm_install_output.log" 2>&1
    if not %errorLevel% equ 0 (
        call :log "ERRO" "Falha ao instalar serviço ControleAcesso (Erro: %errorLevel%)"
        echo %date% %time% - Falha na instalação: %errorLevel% >> "%LOG_DIR%\nssm_debug.log"
        type "%LOG_DIR%\nssm_install_output.log" >> "%LOG_DIR%\nssm_debug.log"
        echo ERRO: Falha ao instalar serviço ControleAcesso. Veja %LOG_DIR%\nssm_debug.log
        echo Pressione qualquer tecla para continuar sem o serviço...
        pause >nul
    ) else (
        :: Configurar parâmetros do serviço conforme documentação do NSSM
        echo Configurando parâmetros do serviço...
        call :log "INFO" "Configurando parâmetros do serviço ControleAcesso"
        
        :: Configuração básica
        echo %date% %time% - Configurando DisplayName >> "%LOG_DIR%\nssm_debug.log"
        %NSSM_CMD% set ControleAcesso DisplayName "Sistema de Controle de Acesso" > "%LOG_DIR%\nssm_config1.log" 2>&1
        
        echo %date% %time% - Configurando Description >> "%LOG_DIR%\nssm_debug.log"
        %NSSM_CMD% set ControleAcesso Description "Servidor web do Sistema de Controle de Acesso" > "%LOG_DIR%\nssm_config2.log" 2>&1
        
        echo %date% %time% - Configurando AppDirectory >> "%LOG_DIR%\nssm_debug.log"
        %NSSM_CMD% set ControleAcesso AppDirectory "%APP_DIR%" > "%LOG_DIR%\nssm_config3.log" 2>&1
        
        echo %date% %time% - Configurando Start >> "%LOG_DIR%\nssm_debug.log"
        %NSSM_CMD% set ControleAcesso Start SERVICE_AUTO_START > "%LOG_DIR%\nssm_config4.log" 2>&1
        
        :: Configuração de logs
        echo %date% %time% - Configurando AppStdout >> "%LOG_DIR%\nssm_debug.log"
        %NSSM_CMD% set ControleAcesso AppStdout "%LOG_DIR%\service_stdout.log" > "%LOG_DIR%\nssm_config5.log" 2>&1
        
        echo %date% %time% - Configurando AppStderr >> "%LOG_DIR%\nssm_debug.log"
        %NSSM_CMD% set ControleAcesso AppStderr "%LOG_DIR%\service_stderr.log" > "%LOG_DIR%\nssm_config6.log" 2>&1
        
        :: Configuração de rotação de logs
        echo %date% %time% - Configurando rotação de logs >> "%LOG_DIR%\nssm_debug.log"
        %NSSM_CMD% set ControleAcesso AppRotateFiles 1 > "%LOG_DIR%\nssm_config7.log" 2>&1
        %NSSM_CMD% set ControleAcesso AppRotateBytes 1048576 > "%LOG_DIR%\nssm_config8.log" 2>&1
        
        :: Ações de saída
        echo %date% %time% - Configurando AppExit >> "%LOG_DIR%\nssm_debug.log"
        %NSSM_CMD% set ControleAcesso AppExit Default Restart > "%LOG_DIR%\nssm_config9.log" 2>&1
        %NSSM_CMD% set ControleAcesso AppRestartDelay 30000 > "%LOG_DIR%\nssm_config10.log" 2>&1
        
        :: Iniciar o serviço
        echo Iniciando serviço ControleAcesso...
        call :log "INFO" "Iniciando serviço ControleAcesso"
        echo %date% %time% - Iniciando serviço >> "%LOG_DIR%\nssm_debug.log"
        net start ControleAcesso > "%LOG_DIR%\service_start.log" 2>&1
        
        if %errorLevel% neq 0 (
            call :log "ERRO" "Falha ao iniciar o serviço ControleAcesso (Erro: %errorLevel%)"
            echo %date% %time% - Falha ao iniciar o serviço: %errorLevel% >> "%LOG_DIR%\nssm_debug.log"
            type "%LOG_DIR%\service_start.log" >> "%LOG_DIR%\nssm_debug.log"
            echo ERRO: Falha ao iniciar o serviço ControleAcesso.
            echo O serviço foi criado, mas não pôde ser iniciado.
            echo Verifique o arquivo de log: %LOG_DIR%\service_start.log
            echo.
            echo Pressione qualquer tecla para continuar...
            pause >nul
        ) else (
            call :log "INFO" "Serviço ControleAcesso iniciado com sucesso"
            echo Serviço ControleAcesso iniciado com sucesso!
        )
        
        :: Instalar serviço Serveo
        echo.
        echo Instalando serviço de acesso remoto (Serveo)...
        call :log "INFO" "Instalando serviço Serveo"
        
        :: Define automaticamente que o Serveo será instalado
        set "INSTALL_SERVEO=S"
        call :log "INFO" "Configurado para instalar Serveo: %INSTALL_SERVEO%"
        
        :: Verifica e remove serviço Serveo se já existir
        echo %date% %time% - Verificando serviço ServeoService >> "%LOG_DIR%\nssm_debug.log"
        sc query ServeoService > "%LOG_DIR%\sc_query_serveo.log" 2>&1
        if %errorLevel% equ 0 (
            echo Serviço ServeoService já existe, removendo...
            call :log "INFO" "Removendo serviço ServeoService existente"
            net stop ServeoService > "%LOG_DIR%\serveo_stop.log" 2>&1
            %NSSM_CMD% remove ServeoService confirm > "%LOG_DIR%\serveo_remove.log" 2>&1
            timeout /t 2 >nul
        )
        
        :: Instalar serviço Serveo
        echo %date% %time% - Instalando serviço ServeoService >> "%LOG_DIR%\nssm_debug.log"
        %NSSM_CMD% install ServeoService "%SCRIPTS_DIR%\start_serveo.bat" > "%LOG_DIR%\serveo_install.log" 2>&1
        
        if not %errorLevel% equ 0 (
            call :log "ERRO" "Falha ao instalar serviço ServeoService (Erro: %errorLevel%)"
            echo %date% %time% - Falha na instalação do Serveo: %errorLevel% >> "%LOG_DIR%\nssm_debug.log"
            type "%LOG_DIR%\serveo_install.log" >> "%LOG_DIR%\nssm_debug.log"
            echo ERRO: Falha ao instalar serviço ServeoService.
            echo Pressione qualquer tecla para continuar...
            pause >nul
        ) else (
            :: Configurar parâmetros do serviço Serveo
            echo Configurando serviço ServeoService...
            call :log "INFO" "Configurando parâmetros do serviço ServeoService"
            
            %NSSM_CMD% set ServeoService DisplayName "Serveo - Acesso Remoto" > "%LOG_DIR%\serveo_config1.log" 2>&1
            %NSSM_CMD% set ServeoService Description "Serviço de acesso remoto via Serveo" > "%LOG_DIR%\serveo_config2.log" 2>&1
            %NSSM_CMD% set ServeoService AppDirectory "%APP_DIR%" > "%LOG_DIR%\serveo_config3.log" 2>&1
            %NSSM_CMD% set ServeoService Start SERVICE_AUTO_START > "%LOG_DIR%\serveo_config4.log" 2>&1
            %NSSM_CMD% set ServeoService AppStdout "%LOG_DIR%\serveo_stdout.log" > "%LOG_DIR%\serveo_config5.log" 2>&1
            %NSSM_CMD% set ServeoService AppStderr "%LOG_DIR%\serveo_stderr.log" > "%LOG_DIR%\serveo_config6.log" 2>&1
            %NSSM_CMD% set ServeoService AppRotateFiles 1 > "%LOG_DIR%\serveo_config7.log" 2>&1
            %NSSM_CMD% set ServeoService AppRotateBytes 1048576 > "%LOG_DIR%\serveo_config8.log" 2>&1
            %NSSM_CMD% set ServeoService AppExit Default Restart > "%LOG_DIR%\serveo_config9.log" 2>&1
            
            :: Iniciar o serviço Serveo
            echo Iniciando serviço ServeoService...
            call :log "INFO" "Iniciando serviço ServeoService"
            echo %date% %time% - Iniciando serviço ServeoService >> "%LOG_DIR%\nssm_debug.log"
            net start ServeoService > "%LOG_DIR%\serveo_start.log" 2>&1
            
            if %errorLevel% neq 0 (
                call :log "ERRO" "Falha ao iniciar o serviço ServeoService (Erro: %errorLevel%)"
                echo %date% %time% - Falha ao iniciar Serveo: %errorLevel% >> "%LOG_DIR%\nssm_debug.log"
                type "%LOG_DIR%\serveo_start.log" >> "%LOG_DIR%\nssm_debug.log"
                echo ERRO: Falha ao iniciar o serviço ServeoService.
                echo O serviço foi criado, mas não pôde ser iniciado.
                echo.
                echo Pressione qualquer tecla para continuar...
                pause >nul
            ) else (
                call :log "INFO" "Serviço ServeoService iniciado com sucesso"
                echo Serviço ServeoService iniciado com sucesso!
            )
        )
    )
) else {
    call :log "INFO" "Instalação como serviço Windows ignorada devido à falta do NSSM"
    echo Instalação como serviço Windows ignorada.
    
    :: Tentativa alternativa com PowerShell
    echo %date% %time% - Tentando usar PowerShell como alternativa ao NSSM >> "%LOG_DIR%\nssm_debug.log"
    call :log "INFO" "Tentando usar PowerShell como alternativa para instalar o serviço"
    echo Tentando usar PowerShell como alternativa para instalar o serviço...
    
    echo @echo off > "%SCRIPTS_DIR%\install_service.ps1"
    echo # Script para criar serviço Windows usando PowerShell >> "%SCRIPTS_DIR%\install_service.ps1"
    echo $serviceName = "ControleAcesso" >> "%SCRIPTS_DIR%\install_service.ps1"
    echo $binaryPath = '"%SCRIPTS_DIR%\start_server.bat"' >> "%SCRIPTS_DIR%\install_service.ps1"
    echo try { >> "%SCRIPTS_DIR%\install_service.ps1"
    echo     $service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue >> "%SCRIPTS_DIR%\install_service.ps1"
    echo     if ($service) { >> "%SCRIPTS_DIR%\install_service.ps1"
    echo         Write-Host "O servico ja existe. Removendo..." >> "%SCRIPTS_DIR%\install_service.ps1"
    echo         Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue >> "%SCRIPTS_DIR%\install_service.ps1"
    echo         sc.exe delete $serviceName >> "%SCRIPTS_DIR%\install_service.ps1"
    echo         Start-Sleep -Seconds 2 >> "%SCRIPTS_DIR%\install_service.ps1"
    echo     } >> "%SCRIPTS_DIR%\install_service.ps1"
    echo     New-Service -Name $serviceName -BinaryPathName $binaryPath -DisplayName "Sistema de Controle de Acesso" -Description "Servidor web do Sistema de Controle de Acesso" -StartupType Automatic >> "%SCRIPTS_DIR%\install_service.ps1"
    echo     Write-Host "Servico criado com sucesso." >> "%SCRIPTS_DIR%\install_service.ps1"
    echo     Start-Service -Name $serviceName >> "%SCRIPTS_DIR%\install_service.ps1"
    echo     Write-Host "Servico iniciado com sucesso." >> "%SCRIPTS_DIR%\install_service.ps1"
    echo     exit 0 >> "%SCRIPTS_DIR%\install_service.ps1"
    echo } catch { >> "%SCRIPTS_DIR%\install_service.ps1"
    echo     Write-Host "Erro ao criar o servico: $_" >> "%SCRIPTS_DIR%\install_service.ps1"
    echo     exit 1 >> "%SCRIPTS_DIR%\install_service.ps1"
    echo } >> "%SCRIPTS_DIR%\install_service.ps1"
    
    echo %date% %time% - Executando PowerShell como administrador >> "%LOG_DIR%\nssm_debug.log"
    call :log "INFO" "Executando PowerShell como administrador para criar o serviço"
    
    :: Executar o script com privilégios elevados
    powershell -ExecutionPolicy Bypass -Command "Start-Process powershell -ArgumentList '-ExecutionPolicy Bypass -File \"%SCRIPTS_DIR%\install_service.ps1\"' -Verb RunAs" > "%LOG_DIR%\powershell_output.log" 2>&1
    echo %date% %time% - PowerShell executado com resultado: %errorLevel% >> "%LOG_DIR%\nssm_debug.log"
    
    :: Verificar se o serviço foi criado
    timeout /t 5 >nul
    sc query ControleAcesso > "%LOG_DIR%\ps_service_check.log" 2>&1
    if %errorLevel% equ 0 (
        call :log "INFO" "Serviço criado com sucesso via PowerShell"
        echo Serviço criado com sucesso via PowerShell.
        
        :: Configurar serviço Serveo também
        echo Configurando serviço Serveo via PowerShell...
        echo @echo off > "%SCRIPTS_DIR%\install_serveo.ps1"
        echo # Script para criar serviço Serveo >> "%SCRIPTS_DIR%\install_serveo.ps1"
        echo $serviceName = "ServeoService" >> "%SCRIPTS_DIR%\install_serveo.ps1"
        echo $binaryPath = '"%SCRIPTS_DIR%\start_serveo.bat"' >> "%SCRIPTS_DIR%\install_serveo.ps1"
        echo try { >> "%SCRIPTS_DIR%\install_serveo.ps1"
        echo     $service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue >> "%SCRIPTS_DIR%\install_serveo.ps1"
        echo     if ($service) { >> "%SCRIPTS_DIR%\install_serveo.ps1"
        echo         Write-Host "O servico Serveo ja existe. Removendo..." >> "%SCRIPTS_DIR%\install_serveo.ps1"
        echo         Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue >> "%SCRIPTS_DIR%\install_serveo.ps1"
        echo         sc.exe delete $serviceName >> "%SCRIPTS_DIR%\install_serveo.ps1"
        echo         Start-Sleep -Seconds 2 >> "%SCRIPTS_DIR%\install_serveo.ps1"
        echo     } >> "%SCRIPTS_DIR%\install_serveo.ps1"
        echo     New-Service -Name $serviceName -BinaryPathName $binaryPath -DisplayName "Serveo - Acesso Remoto" -Description "Servico de acesso remoto via Serveo" -StartupType Automatic >> "%SCRIPTS_DIR%\install_serveo.ps1"
        echo     Write-Host "Servico Serveo criado com sucesso." >> "%SCRIPTS_DIR%\install_serveo.ps1"
        echo     Start-Service -Name $serviceName >> "%SCRIPTS_DIR%\install_serveo.ps1"
        echo     Write-Host "Servico Serveo iniciado com sucesso." >> "%SCRIPTS_DIR%\install_serveo.ps1"
        echo     exit 0 >> "%SCRIPTS_DIR%\install_serveo.ps1"
        echo } catch { >> "%SCRIPTS_DIR%\install_serveo.ps1"
        echo     Write-Host "Erro ao criar o servico Serveo: $_" >> "%SCRIPTS_DIR%\install_serveo.ps1"
        echo     exit 1 >> "%SCRIPTS_DIR%\install_serveo.ps1"
        echo } >> "%SCRIPTS_DIR%\install_serveo.ps1"
        
        powershell -ExecutionPolicy Bypass -Command "Start-Process powershell -ArgumentList '-ExecutionPolicy Bypass -File \"%SCRIPTS_DIR%\install_serveo.ps1\"' -Verb RunAs" > "%LOG_DIR%\powershell_serveo_output.log" 2>&1
    ) else {
        call :log "ERRO" "Falha ao criar serviço via PowerShell"
        echo Falha ao criar serviço via PowerShell. 
        echo Verifique o arquivo de log: "%LOG_DIR%\powershell_output.log"
    }
}

echo.
echo Pressione qualquer tecla para continuar...
pause >nul

:: Configurar atualizações automáticas automaticamente
echo Configurando atualizacoes automaticas...
call :log "INFO" "Configurando atualizacoes automaticas automaticamente"

:: Definir automaticamente que as atualizações serão configuradas
set "CONFIG_UPDATES=S"
call :log "INFO" "Configurado para atualizações automáticas: %CONFIG_UPDATES%"

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
) else {
    call :log "INFO" "Atualizacoes automaticas configuradas com sucesso."
    echo Atualizacoes automaticas configuradas com sucesso.
}

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
) else {
    echo Para iniciar o servidor manualmente, execute:
    echo   cd "%APP_DIR%"
    echo   "%VENV_DIR%\Scripts\activate.bat"
    echo   %PYTHON_CMD% manage.py runserver
    echo.
    echo Para acessar o sistema, abra o navegador e acesse:
    echo   http://localhost:8000
}

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

:: Iniciar o sistema automaticamente se não estiver instalado como serviço
if /i not "%INSTALL_SERVICE%"=="S" (
    echo Iniciando o sistema automaticamente...
    start "" "%SCRIPTS_DIR%\start_server.bat"
    timeout /t 3 >nul
    start http://localhost:8000/
)

echo.
echo Pressione qualquer tecla para sair...
pause
exit /b 0

:log
echo %date% %time% [%~1] %~2 >> "%LOG_FILE%"
goto :eof

:ExecuteCommand
:: %1 = Comando a ser executado
:: %2 = Arquivo de saída
:: %3 = Arquivo de erro
echo Executando comando: %~1 > "%~2"
echo Executando comando: %~1 > "%~3"
%~1 >> "%~2" 2>> "%~3"
exit /b %errorLevel% 