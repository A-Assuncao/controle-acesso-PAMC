@echo off
:: Cria tarefa agendada para atualização diária
schtasks /create /tn "AtualizarControleAcesso" /tr "\"%PROGRAMFILES%\ControleAcesso\update.bat\"" /sc daily /st 03:00 /ru SYSTEM

echo Atualizacao automatica configurada para executar diariamente as 03:00
timeout /t 5 