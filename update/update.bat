@echo off
setlocal EnableDelayedExpansion

:: Diretórios e arquivos
set "LOG_DIR=%~dp0logs"
set "LOG_FILE=%LOG_DIR%\update_%date:~-4,4%-%date:~-10,2%-%date:~-7,2%.log"
set "TEMP_FILE=%TEMP%\git_pull_output.txt"

:: Função de log
:log
    echo [%date:~-4,4%/%date:~-10,2%/%date:~-7,2% %time:~0,8%] %~1 >> "%LOG_FILE%"
    echo [%date:~-4,4%/%date:~-10,2%/%date:~-7,2% %time:~0,8%] %~1
    goto :eof

:: Verifica internet
:check_internet
    ping -n 1 8.8.8.8 >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        call :log "ERRO: Sem conexão com a internet."
        goto :error
    )
    goto :eof

:: Verifica permissão de escrita
:check_write_permission
    echo. > "%LOG_DIR%\test.tmp" 2>nul
    if %ERRORLEVEL% neq 0 (
        call :log "ERRO: Sem permissão de escrita. Execute como administrador."
        goto :error
    )
    del "%LOG_DIR%\test.tmp" >nul 2>nul
    goto :eof

:: Cria pasta de logs
if not exist "%LOG_DIR%" (
    mkdir "%LOG_DIR%" || (
        echo ERRO: Não foi possível criar a pasta de logs.
        exit /b 1
    )
    call :log "Diretório de logs criado: %LOG_DIR%"
)

cls
call :log "=== Iniciando atualização do projeto ==="

:: Verificações
call :check_internet
call :check_write_permission
where git >nul 2>nul || (call :log "ERRO: Git não instalado."; goto :error)
if not exist "%~dp0\.git" (call :log "ERRO: Não é um repositório Git."; goto :error)

cd /d "%~dp0"
call :log "Executando git pull..."
git pull > "%TEMP_FILE%" 2>&1
set "PULL_ERROR=%ERRORLEVEL%"

:: Trata falhas do git pull
if %PULL_ERROR% neq 0 (
    type "%TEMP_FILE%" | findstr /i "not a git repository" >nul && (call :log "ERRO: Repositório inválido."; goto :error)
    type "%TEMP_FILE%" | findstr /i "Authentication failed" >nul && (call :log "ERRO: Autenticação falhou."; goto :error)
    type "%TEMP_FILE%" | findstr /i "unable to access" >nul && (call :log "ERRO: Falha ao acessar o repositório remoto."; goto :error)
    type "%TEMP_FILE%" | findstr /i "would be overwritten" >nul && (call :log "ERRO: Mudanças locais não commitadas."; goto :error)
    type "%TEMP_FILE%" | findstr /i "unrelated histories" >nul && (call :log "ERRO: Históricos incompatíveis."; goto :error)
    call :log "ERRO: Falha no git pull. Veja detalhes abaixo:"
    type "%TEMP_FILE%" >> "%LOG_FILE%"
    goto :error
)

:: Verifica se houve atualização real
type "%TEMP_FILE%" | findstr /i "Already up to date." >nul
if %ERRORLEVEL% equ 0 (
    call :log "Nenhuma atualização detectada no repositório."
    goto :fim
)

:: Ativa ambiente virtual e roda migrações
call :log "Atualização detectada. Rodando migrações..."
call "%~dp0venv\Scripts\activate.bat"
python manage.py makemigrations >> "%LOG_FILE%" 2>>&1
python manage.py migrate >> "%LOG_FILE%" 2>>&1
call :log "Migrações aplicadas com sucesso."

:fim
call :log "=== Finalizado com sucesso ==="
if exist "%TEMP_FILE%" del "%TEMP_FILE%" >nul 2>nul

:: Se rodado com argumento "console", pausa ao final
if "%1"=="console" pause
exit /b 0

:error
call :log "=== Atualização encerrada com erro ==="
if exist "%TEMP_FILE%" del "%TEMP_FILE%" >nul 2>nul
if "%1"=="console" pause
exit /b 1
