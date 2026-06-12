@echo off
REM Atualiza PAMC + CPBV + CPFBV (ou sites em deploy\sites.json)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\atualizar_todos.ps1" %*
exit /b %ERRORLEVEL%
