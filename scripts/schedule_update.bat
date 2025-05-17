@echo off
echo Configurando atualizacao automatica...

:: Cria tarefa agendada para atualização diária
schtasks /create /tn "AtualizarControleAcesso" /tr "\"%ProgramFiles%\ControleAcesso\scripts\update.bat\"" /sc daily /st 03:00 /f

:: Verifica se a tarefa foi criada com sucesso
schtasks /query /tn "AtualizarControleAcesso" >nul 2>&1
if %errorlevel% == 0 (
    echo Atualizacao automatica configurada para executar diariamente as 03:00
) else (
    echo ERRO: Falha ao configurar atualizacao automatica
)

echo.
echo Pressione qualquer tecla para continuar...
pause>nul 