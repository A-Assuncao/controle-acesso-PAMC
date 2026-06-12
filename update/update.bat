@echo off
setlocal EnableDelayedExpansion
goto :main

:: update\update.bat — atualiza controle-acesso-PAMC em producao (IIS)
:: Uso:
::   update.bat              duplo clique (pausa no final)
::   update.bat silent       tarefa agendada
::   update.bat -SemGit      sem git pull (copia manual de arquivos)

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

:limpar_pycache
    if not exist "%PROJECT_ROOT%\core" (
        call :log "AVISO: Pasta core nao encontrada; pulando limpeza de cache."
        exit /b 0
    )
    set "PYCACHE_COUNT=0"
    for /f "delims=" %%D in ('dir /s /b /ad "%PROJECT_ROOT%\core\__pycache__" 2^>nul') do (
        rd /s /q "%%D" 2>nul
        set /a PYCACHE_COUNT+=1
    )
    call :log "Cache Python limpo (!PYCACHE_COUNT! pastas __pycache__)."
    exit /b 0

:recarregar_iis
    where iisreset >nul 2>nul
    if errorlevel 1 (
        call :log "AVISO: iisreset nao encontrado. Recicle o App Pool manualmente no IIS."
        exit /b 0
    )
    call :log "Reciclando IIS (iisreset)..."
    iisreset /restart >>"%LOG_FILE%" 2>&1
    if errorlevel 1 (
        call :log "AVISO: iisreset falhou. Recicle o App Pool manualmente."
    ) else (
        call :log "IIS reiniciado."
    )
    exit /b 0

:pos_deploy
    if not exist "%VENV_ACTIVATE%" (
        call :log "ERRO: venv nao encontrado: %VENV_ACTIVATE%"
        exit /b 1
    )

    pushd "%PROJECT_ROOT%"
    call "%VENV_ACTIVATE%"
    if errorlevel 1 (
        call :log "ERRO: Falha ao ativar o venv."
        popd
        exit /b 1
    )

    if "!HAD_CHANGES!"=="1" (
        call :log "Aplicando dependencias e migracoes..."
        python -m pip install -r requirements.txt >>"%LOG_FILE%" 2>&1
        if errorlevel 1 (
            call :log "ERRO: pip install falhou. Veja %LOG_FILE%"
            popd
            exit /b 1
        )
        call :log "Dependencias OK."

        python manage.py migrate --noinput >>"%LOG_FILE%" 2>&1
        if errorlevel 1 (
            call :log "ERRO: migrate falhou. Veja %LOG_FILE%"
            popd
            exit /b 1
        )
        call :log "Migracoes aplicadas."

        python manage.py collectstatic --noinput >>"%LOG_FILE%" 2>&1
        if errorlevel 1 (
            call :log "AVISO: collectstatic falhou (ver log)."
        ) else (
            call :log "Arquivos estaticos atualizados."
        )
    ) else (
        call :log "Pulando pip/migrate/collectstatic (sem mudancas no Git)."
    )
    popd
    exit /b 0

:main
    set "SCRIPT_DIR=%~dp0"
    for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"

    set "LOG_DIR=%SCRIPT_DIR%logs"
    set "LOG_FILE=%LOG_DIR%\update.log"
    set "TEMP_FILE=%TEMP%\controle_acesso_git_pull.txt"
    set "VENV_ACTIVATE=%PROJECT_ROOT%\venv\Scripts\activate.bat"
    set "HAD_CHANGES=0"
    set "SKIP_GIT=0"
    set "MODE=console"

    if /i "%~1"=="-SemGit" set "SKIP_GIT=1"
    if /i "%~1"=="silent" set "MODE=silent"

    if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" 2>nul

    cls
    call :log "=== Iniciando atualizacao do Controle de Acesso ==="
    call :log "Projeto: %PROJECT_ROOT%"

    call :check_internet
    if errorlevel 1 goto :error

    call :check_write_permission
    if errorlevel 1 goto :error

    if "!SKIP_GIT!"=="1" (
        call :log "Modo -SemGit: pulando git pull (arquivos copiados manualmente)."
        set "HAD_CHANGES=0"
        goto :after_git
    )

    where git >nul 2>nul
    if errorlevel 1 (
        call :log "ERRO: Git nao instalado ou fora do PATH."
        call :log "Dica: use update.bat -SemGit se voce copiou os arquivos manualmente."
        goto :error
    )

    if not exist "%PROJECT_ROOT%\.git" (
        call :log "AVISO: %PROJECT_ROOT% nao e repositorio Git (.git ausente)."
        call :log "Dica: clone o repo OU copie core\admin.py manualmente e rode: update.bat -SemGit"
        goto :error
    )

    pushd "%PROJECT_ROOT%"
    git rev-parse --is-inside-work-tree >nul 2>&1
    if errorlevel 1 (
        call :log "ERRO: Git nao reconhece a pasta como work tree valida."
        popd
        goto :error
    )

    call :log "Executando git pull origin main..."
    git pull origin main>"%TEMP_FILE%" 2>&1
    set "PULL_ERROR=!ERRORLEVEL!"
    popd

    if !PULL_ERROR! neq 0 (
        call :log "ERRO: git pull falhou (codigo !PULL_ERROR!). Saida:"
        type "%TEMP_FILE%"
        type "%TEMP_FILE%">>"%LOG_FILE%"
        findstr /i /c:"Authentication failed" "%TEMP_FILE%" >nul && (
            call :log "Causa provavel: autenticacao Git (SSH/chave ou token)."
        )
        findstr /i /c:"not a git repository" "%TEMP_FILE%" >nul && (
            call :log "Causa provavel: pasta .git invalida ou corrompida."
        )
        findstr /i /c:"would be overwritten by merge" "%TEMP_FILE%" >nul && (
            call :log "Causa provavel: arquivos locais modificados no servidor."
        )
        goto :error
    )

    type "%TEMP_FILE%"
    findstr /i /c:"Already up to date" "%TEMP_FILE%" >nul
    if not errorlevel 1 (
        call :log "Repositorio ja estava atualizado (git)."
        set "HAD_CHANGES=0"
    ) else (
        call :log "Atualizacao Git detectada."
        set "HAD_CHANGES=1"
    )

:after_git
    call :limpar_pycache
    call :pos_deploy
    if errorlevel 1 goto :error

    call :recarregar_iis
    goto :fim

:fim
    call :log "=== Finalizado com sucesso ==="
    if exist "%TEMP_FILE%" del "%TEMP_FILE%" >nul 2>nul
    if /i not "!MODE!"=="silent" pause
    exit /b 0

:error
    call :log "=== Atualizacao encerrada com erro ==="
    if exist "%TEMP_FILE%" del "%TEMP_FILE%" >nul 2>nul
    if /i not "!MODE!"=="silent" pause
    exit /b 1
