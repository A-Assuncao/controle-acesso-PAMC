@echo off
setlocal EnableDelayedExpansion

:: Configuracoes
set "LOG_DIR=%~dp0logs"
set "LOG_FILE=%LOG_DIR%\update.log"
set "TEMP_FILE=%TEMP%\git_pull_output.txt"

:: Funcao para registrar logs
:log
    echo [%date:~-4,4%/%date:~-7,2%/%date:~-10,2% %time:~0,8%] %~1 >> "%LOG_FILE%"
    echo [%date:~-4,4%/%date:~-7,2%/%date:~-10,2% %time:~0,8%] %~1
goto :eof

:: Funcao para verificar conexao com internet
:check_internet
    ping -n 1 8.8.8.8 >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        call :log "ERRO: Sem conexao com a internet. Verifique sua conexao."
        goto :error
    )
goto :eof

:: Funcao para verificar permissao de escrita
:check_write_permission
    echo. > "%LOG_DIR%\test.tmp" 2>nul
    if %ERRORLEVEL% neq 0 (
        call :log "ERRO: Sem permissao de escrita no diretorio. Execute como administrador."
        goto :error
    )
    del "%LOG_DIR%\test.tmp" >nul 2>nul
goto :eof

:: Cria diretorio de logs se nao existir
if not exist "%LOG_DIR%" (
    mkdir "%LOG_DIR%" 2>nul
    if %ERRORLEVEL% neq 0 (
        echo ERRO: Nao foi possivel criar o diretorio de logs.
        echo Execute o script como administrador.
        pause
        exit /b 1
    )
    call :log "Diretorio de logs criado: %LOG_DIR%"
)

:: Limpa a tela
cls

:: Registra inicio da execucao
call :log "=== Iniciando atualizacao do repositorio ==="
call :log "Diretorio atual: %~dp0"

:: Verifica conexao com internet
call :check_internet

:: Verifica permissao de escrita
call :check_write_permission

:: Verifica se o Git esta instalado
where git >nul 2>nul
if %ERRORLEVEL% neq 0 (
    call :log "ERRO: Git nao encontrado no sistema. Por favor, instale o Git."
    goto :error
)

:: Verifica se e um repositorio Git
if not exist "%~dp0.git" (
    call :log "ERRO: Diretorio atual nao e um repositorio Git."
    goto :error
)

:: Navega ate o diretorio
cd /d "%~dp0"
if %ERRORLEVEL% neq 0 (
    call :log "ERRO: Falha ao navegar para o diretorio do repositorio."
    goto :error
)

:: Verifica status do Git
call :log "Verificando status do repositorio..."
git status >nul 2>nul
if %ERRORLEVEL% neq 0 (
    call :log "ERRO: Falha ao verificar status do repositorio."
    goto :error
)

:: Verifica se o repositorio tem um remote configurado
git remote -v >nul 2>nul
if %ERRORLEVEL% neq 0 (
    call :log "ERRO: Nenhum remote configurado no repositorio."
    goto :error
)

:: Verifica se ha alteracoes locais
git status --porcelain >nul 2>nul
if %ERRORLEVEL% equ 0 (
    call :log "ATENCAO: Existem alteracoes locais nao commitadas."
    call :log "Recomendado: Faça commit ou stash das alteracoes antes de atualizar."
)

:: Executa o git pull com timeout
call :log "Executando git pull..."
git pull > "%TEMP_FILE%" 2>&1
set "PULL_ERROR=%ERRORLEVEL%"

:: Analisa o resultado do git pull
if %PULL_ERROR% neq 0 (
    type "%TEMP_FILE%" | findstr /i "fatal: not a git repository" >nul
    if %ERRORLEVEL% equ 0 (
        call :log "ERRO: Diretorio nao e um repositorio Git valido."
        goto :error
    )
    
    type "%TEMP_FILE%" | findstr /i "fatal: Authentication failed" >nul
    if %ERRORLEVEL% equ 0 (
        call :log "ERRO: Falha na autenticacao. Verifique suas credenciais."
        goto :error
    )
    
    type "%TEMP_FILE%" | findstr /i "fatal: unable to access" >nul
    if %ERRORLEVEL% equ 0 (
        call :log "ERRO: Nao foi possivel acessar o repositorio remoto."
        call :log "Verifique sua conexao com a internet e as credenciais."
        goto :error
    )
    
    type "%TEMP_FILE%" | findstr /i "error: Your local changes would be overwritten" >nul
    if %ERRORLEVEL% equ 0 (
        call :log "ERRO: Alteracoes locais seriam sobrescritas."
        call :log "Faça commit ou stash das alteracoes antes de atualizar."
        goto :error
    )
    
    type "%TEMP_FILE%" | findstr /i "fatal: refusing to merge unrelated histories" >nul
    if %ERRORLEVEL% equ 0 (
        call :log "ERRO: Historias nao relacionadas. Use --allow-unrelated-histories."
        goto :error
    )
    
    call :log "ERRO: Falha ao executar git pull."
    type "%TEMP_FILE%" >> "%LOG_FILE%"
    goto :error
)

:: Registra sucesso
call :log "=== Atualizacao concluida com sucesso! ==="
echo.
echo Atualizacao concluida com sucesso!
echo Verifique o arquivo de log em: %LOG_FILE%
echo.

:: Limpa arquivo temporario
if exist "%TEMP_FILE%" del "%TEMP_FILE%" >nul 2>nul

pause
goto :eof

:error
    call :log "=== ERRO: Atualizacao falhou! ==="
    echo.
    echo Ocorreu um erro durante a atualizacao.
    echo Verifique o arquivo de log em: %LOG_FILE%
    echo.
    
    :: Limpa arquivo temporario
    if exist "%TEMP_FILE%" del "%TEMP_FILE%" >nul 2>nul
    
    pause
    exit /b 1 