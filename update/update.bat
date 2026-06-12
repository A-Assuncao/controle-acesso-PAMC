@echo off
setlocal EnableDelayedExpansion
goto :main

:: ---------------------------------------------------------------------------
:: Subrotinas (devem ficar antes do :main apenas com goto :main no inicio)
:: ---------------------------------------------------------------------------

:log
    echo [%date% %time:~0,8%] %~1
    echo [%date% %time:~0,8%] %~1>> "%LOG_FILE%"
    goto :eof

:check_internet
    ping -n 1 8.8.8.8 >nul 2>nul
    if errorlevel 1 (
        call :log "ERRO: Sem conexao com a internet."
        exit /b 1
    )
    exit /b 0

:check_write_permission
    echo.>"%LOG_DIR%\test.tmp" 2>nul
    if errorlevel 1 (
        call :log "ERRO: Sem permissao de escrita em %LOG_DIR%. Execute como administrador."
        exit /b 1
    )
    del "%LOG_DIR%\test.tmp" >nul 2>nul
    exit /b 0

:main
    :: Pasta deste script: ...\controle-acesso-PAMC\update\
    set "SCRIPT_DIR=%~dp0"
    for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"

    set "LOG_DIR=%SCRIPT_DIR%logs"
    set "LOG_FILE=%LOG_DIR%\update.log"
    set "TEMP_FILE=%TEMP%\controle_acesso_git_pull.txt"
    set "VENV_ACTIVATE=%PROJECT_ROOT%\venv\Scripts\activate.bat"

    if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" 2>nul

    cls
    call :log "=== Iniciando atualizacao do Controle de Acesso ==="
    call :log "Projeto: %PROJECT_ROOT%"

    call :check_internet
    if errorlevel 1 goto :error

    call :check_write_permission
    if errorlevel 1 goto :error

    where git >nul 2>nul
    if errorlevel 1 (
        call :log "ERRO: Git nao instalado ou fora do PATH."
        goto :error
    )

    if not exist "%PROJECT_ROOT%\.git" (
        call :log "ERRO: Pasta do projeto nao e um repositorio Git: %PROJECT_ROOT%"
        goto :error
    )

    cd /d "%PROJECT_ROOT%"
    call :log "Executando git pull origin main..."
    git pull origin main>"%TEMP_FILE%" 2>&1
    set "PULL_ERROR=!ERRORLEVEL!"

    if !PULL_ERROR! neq 0 (
        findstr /i "not a git repository" "%TEMP_FILE%" >nul && (
            call :log "ERRO: Repositorio Git invalido."
            goto :error
        )
        findstr /i "Authentication failed" "%TEMP_FILE%" >nul && (
            call :log "ERRO: Autenticacao Git falhou."
            goto :error
        )
        findstr /i "unable to access" "%TEMP_FILE%" >nul && (
            call :log "ERRO: Falha ao acessar o repositorio remoto."
            goto :error
        )
        findstr /i "would be overwritten" "%TEMP_FILE%" >nul && (
            call :log "ERRO: Mudancas locais conflitam com o pull."
            goto :error
        )
        findstr /i "unrelated histories" "%TEMP_FILE%" >nul && (
            call :log "ERRO: Historicos Git incompativeis."
            goto :error
        )
        call :log "ERRO: git pull falhou. Detalhes:"
        type "%TEMP_FILE%">>"%LOG_FILE%"
        type "%TEMP_FILE%"
        goto :error
    )

    findstr /i "Already up to date" "%TEMP_FILE%" >nul
    set "HAD_CHANGES=1"
    if not errorlevel 1 (
        call :log "Repositorio ja estava atualizado (git)."
        set "HAD_CHANGES=0"
    ) else (
        type "%TEMP_FILE%"
        call :log "Atualizacao Git detectada."
    )

    call :log "Limpando cache Python (.pyc)..."
    for /d /r "%PROJECT_ROOT%\core" %%D in (__pycache__) do (
        if exist "%%D" rd /s /q "%%D" 2>nul
    )

    if not exist "%VENV_ACTIVATE%" (
        call :log "ERRO: venv nao encontrado em %VENV_ACTIVATE%"
        goto :error
    )

    call "%VENV_ACTIVATE%"
    if errorlevel 1 (
        call :log "ERRO: Falha ao ativar o ambiente virtual."
        goto :error
    )

    if "!HAD_CHANGES!"=="1" (
        call :log "Aplicando dependencias e migracoes..."
        python -m pip install -r requirements.txt >>"%LOG_FILE%" 2>&1
        if errorlevel 1 (
            call :log "ERRO: pip install falhou. Veja %LOG_FILE%"
            goto :error
        )
        call :log "Dependencias OK."

        python manage.py migrate --noinput >>"%LOG_FILE%" 2>&1
        if errorlevel 1 (
            call :log "ERRO: migrate falhou. Veja %LOG_FILE%"
            goto :error
        )
        call :log "Migracoes aplicadas."

        python manage.py collectstatic --noinput >>"%LOG_FILE%" 2>&1
        if errorlevel 1 (
            call :log "AVISO: collectstatic falhou (ver log). Continuando..."
        ) else (
            call :log "Arquivos estaticos atualizados."
        )
    ) else (
        call :log "Pulando pip/migrate/collectstatic (sem mudancas no Git)."
    )

    where iisreset >nul 2>nul
    if not errorlevel 1 (
        call :log "Reciclando IIS (iisreset) para recarregar codigo Python..."
        iisreset /restart >>"%LOG_FILE%" 2>&1
        if errorlevel 1 (
            call :log "AVISO: iisreset falhou. Recicle o App Pool manualmente."
        ) else (
            call :log "IIS reiniciado."
        )
    ) else (
        call :log "AVISO: iisreset nao encontrado. Reinicie o site/App Pool manualmente."
    )

    goto :fim

:fim
    call :log "=== Finalizado com sucesso ==="
    if exist "%TEMP_FILE%" del "%TEMP_FILE%" >nul 2>nul
    if /i not "%~1"=="silent" pause
    exit /b 0

:error
    call :log "=== Atualizacao encerrada com erro ==="
    if exist "%TEMP_FILE%" del "%TEMP_FILE%" >nul 2>nul
    if /i not "%~1"=="silent" pause
    exit /b 1
