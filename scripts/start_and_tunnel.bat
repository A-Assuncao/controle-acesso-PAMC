@echo off
echo Iniciando Sistema de Controle de Acesso com acesso remoto...

:: Define o diretório da aplicação
set APP_DIR=%ProgramFiles%\ControleAcesso\app
set VENV_DIR=%ProgramFiles%\ControleAcesso\venv
set SCRIPTS_DIR=%ProgramFiles%\ControleAcesso\scripts

:: Instala dependências necessárias para o Serveo se não estiverem presentes
cd /d "%APP_DIR%"
call "%VENV_DIR%\Scripts\activate.bat"
pip install requests python-dotenv >nul 2>&1

:: Inicia o servidor Django em segundo plano
echo Iniciando servidor Django...
start "Servidor Django" "%SCRIPTS_DIR%\start_server.bat"

:: Aguarda alguns segundos para o servidor iniciar
timeout /t 5 /nobreak

:: Inicia o túnel serveo
echo Iniciando túnel Serveo...
start "Serveo Tunnel" "%SCRIPTS_DIR%\start_serveo.bat"

echo.
echo Sistema iniciado com sucesso!
echo.
echo Mantenha estas janelas abertas para que o sistema continue funcionando.
echo Para encerrar, feche todas as janelas.
echo.
pause 