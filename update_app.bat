@echo off
REM Wrapper na raiz do projeto para a Tarefa Agendada (AtualizarControleAcesso.xml)
call "%~dp0update\update.bat" silent
exit /b %ERRORLEVEL%
