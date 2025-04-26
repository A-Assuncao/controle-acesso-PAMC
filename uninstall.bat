@echo off
echo ================================================
echo  Desinstalador do Sistema de Controle de Acesso
echo ================================================
echo.

:: Verifica privilégios de administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Este desinstalador precisa ser executado como Administrador!
    echo Clique com o botao direito no arquivo e selecione "Executar como administrador"
    echo.
    pause
    exit /b 1
)

echo AVISO: Este script ira remover completamente o Sistema de Controle de Acesso.
echo Todos os dados serao perdidos e nao poderao ser recuperados.
echo.
set /p CONFIRM=Tem certeza que deseja continuar? (S/N): 
if /i "%CONFIRM%" neq "S" (
    echo Desinstalacao cancelada.
    exit /b 0
)

echo.
echo Iniciando processo de desinstalacao...
echo.

:: Remove as tarefas agendadas
echo - Removendo tarefas agendadas...
schtasks /delete /tn "AtualizarControleAcesso_Manha" /f >nul 2>&1
schtasks /delete /tn "AtualizarControleAcesso_Tarde" /f >nul 2>&1

:: Para e remove os serviços Windows
echo - Parando e removendo servicos...
net stop ServeoService >nul 2>&1
net stop ControleAcesso >nul 2>&1
nssm remove ServeoService confirm >nul 2>&1
nssm remove ControleAcesso confirm >nul 2>&1

:: Remove atalhos
echo - Removendo atalhos...
del /f /q "%PUBLIC%\Desktop\Controle de Acesso.url" >nul 2>&1
del /f /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\ControleAcesso\Controle de Acesso.url" >nul 2>&1
rmdir /s /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\ControleAcesso" >nul 2>&1

:: Remove o atalho da barra de tarefas (se existir)
del /f /q "%APPDATA%\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar\Controle de Acesso.url" >nul 2>&1

:: Faz backup do banco de dados antes de remover
echo - Criando backup final do banco de dados...
if exist "%PROGRAMFILES%\ControleAcesso\app\db.sqlite3" (
    mkdir "%USERPROFILE%\ControleAcesso_Backup" >nul 2>&1
    copy "%PROGRAMFILES%\ControleAcesso\app\db.sqlite3" "%USERPROFILE%\ControleAcesso_Backup\db_backup_final.sqlite3" >nul 2>&1
    echo   Backup salvo em: %USERPROFILE%\ControleAcesso_Backup\db_backup_final.sqlite3
)

:: Remove diretório principal do programa
echo - Removendo arquivos do programa...
rmdir /s /q "%PROGRAMFILES%\ControleAcesso" >nul 2>&1

:: Remove Python dedicado (se foi instalado pelo instalador)
if exist "%PROGRAMFILES%\ControleAcesso\Python" (
    echo - Removendo Python dedicado...
    rmdir /s /q "%PROGRAMFILES%\ControleAcesso\Python" >nul 2>&1
)

echo.
echo ================================================
echo      Desinstalacao concluida com sucesso!
echo ================================================
echo.
echo Um backup final do banco de dados foi salvo em:
echo %USERPROFILE%\ControleAcesso_Backup\db_backup_final.sqlite3
echo.
echo Se desejar remover completamente todos os dados,
echo incluindo o backup, delete a pasta:
echo %USERPROFILE%\ControleAcesso_Backup
echo.
echo Pressione qualquer tecla para concluir...
pause > nul 