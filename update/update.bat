@echo off
setlocal EnableDelayedExpansion

:: update\update.bat — producao IIS (C:\inetpub\wwwroot\...)
:: Requer Administrador: git pull precisa escrever em .git e iisreset precisa de elevacao.
::
:: Uso:
::   update.bat              duplo clique (pede UAC se necessario)
::   update.bat silent       tarefa agendada (conta SYSTEM/Admin)
::   update.bat -SemGit      sem git pull (copia manual)

if /i not "%~1"=="-NoElevate" (
    net session >nul 2>&1
    if errorlevel 1 (
        echo Solicitando permissao de Administrador...
        powershell -NoProfile -ExecutionPolicy Bypass -Command ^
            "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c \"\"%~f0\" -NoElevate %*\"' -Verb RunAs"
        exit /b 0
    )
)

goto :main

:log
    set "LINE=[%date% %time:~0,8%] %~1"
    echo !LINE!
    >>"%LOG_FILE%" echo !LINE! 2>nul
    goto :eof

:check_internet
    ping -n 1 8.8.8.8 >nul 2>nul
    if errorlevel 1 (
        call :log "ERRO: Sem conexao com a internet."
        exit /b 1
    )
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

    :: Log sempre em %%TEMP%% (inetpub\update\logs costuma bloquear usuario comum)
    set "LOG_FILE=%TEMP%\controle-acesso-update.log"
    set "TEMP_FILE=%TEMP%\controle_acesso_git_pull.txt"
    set "VENV_ACTIVATE=%PROJECT_ROOT%\venv\Scripts\activate.bat"
    set "HAD_CHANGES=0"
    set "SKIP_GIT=0"
    set "MODE=console"

    if /i "%~1"=="-NoElevate" shift
    if /i "%~1"=="-SemGit" set "SKIP_GIT=1"
    if /i "%~1"=="silent" set "MODE=silent"
    if /i "%~2"=="-SemGit" set "SKIP_GIT=1"
    if /i "%~2"=="silent" set "MODE=silent"

    cls
    call :log "=== Iniciando atualizacao do Controle de Acesso ==="
    call :log "Projeto: %PROJECT_ROOT%"
    call :log "Log: %LOG_FILE%"

    call :check_internet
    if errorlevel 1 goto :error

    if "!SKIP_GIT!"=="1" (
        call :log "Modo -SemGit: pulando git pull."
        set "HAD_CHANGES=0"
        goto :after_git
    )

    where git >nul 2>nul
    if errorlevel 1 (
        call :log "ERRO: Git nao instalado ou fora do PATH."
        goto :error
    )

    if not exist "%PROJECT_ROOT%\.git" (
        call :log "ERRO: .git ausente em %PROJECT_ROOT%"
        call :log "Use update.bat -SemGit apos copiar arquivos manualmente."
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
        findstr /i /c:"Permission denied" "%TEMP_FILE%" >nul && (
            call :log "Causa: sem permissao em .git — confirme que o script rodou como Administrador."
            call :log "No CMD Admin: icacls .git /grant Administradores:(OI)(CI)F /T"
        )
        findstr /i /c:"Authentication failed" "%TEMP_FILE%" >nul && (
            call :log "Causa provavel: autenticacao Git."
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
    call :log "Log completo: %LOG_FILE%"
    if exist "%TEMP_FILE%" del "%TEMP_FILE%" >nul 2>nul
    if /i not "!MODE!"=="silent" pause
    exit /b 1
