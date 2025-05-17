@echo off
echo Configurando atualizacao automatica via git pull...

:: Define o diretório da aplicação
set APP_DIR=%ProgramFiles%\ControleAcesso\app
set VENV_DIR=%ProgramFiles%\ControleAcesso\venv

:: Criar script temporário para o git pull
set UPDATE_SCRIPT=%ProgramFiles%\ControleAcesso\scripts\run_git_pull.bat
echo @echo off > "%UPDATE_SCRIPT%"
echo cd /d "%APP_DIR%" >> "%UPDATE_SCRIPT%"
echo git pull >> "%UPDATE_SCRIPT%"
echo IF %%ERRORLEVEL%% NEQ 0 ( >> "%UPDATE_SCRIPT%"
echo   echo Erro ao executar git pull. Verifique a conexão ou repositório. >> "%UPDATE_SCRIPT%"
echo ) ELSE ( >> "%UPDATE_SCRIPT%"
echo   echo Atualização via git pull concluída com sucesso. >> "%UPDATE_SCRIPT%"
echo ) >> "%UPDATE_SCRIPT%"

:: Cria tarefa agendada para atualização diária às 18:00
schtasks /create /tn "AtualizarControleAcesso" /tr "\"%UPDATE_SCRIPT%\"" /sc daily /st 18:00 /f

:: Verifica se a tarefa foi criada com sucesso
schtasks /query /tn "AtualizarControleAcesso" >nul 2>&1
if %errorlevel% == 0 (
    echo Atualização automática via git pull configurada para executar diariamente às 18:00
) else (
    echo ERRO: Falha ao configurar atualização automática
)

echo.
echo Pressione qualquer tecla para continuar...
pause>nul 