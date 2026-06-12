@echo off
REM Wrapper na raiz — usado pela Tarefa Agendada (ControleAcesso-AtualizacaoDiaria)
call "%~dp0update\update.bat" -NoElevate silent
exit /b %ERRORLEVEL%