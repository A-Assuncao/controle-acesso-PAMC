@echo off
echo Iniciando o servidor Django...

:: Define o diretório da aplicação
set APP_DIR=%ProgramFiles%\ControleAcesso\app
set VENV_DIR=%ProgramFiles%\ControleAcesso\venv

:: Vai para o diretório da aplicação
cd /d "%APP_DIR%"

:: Ativa o ambiente virtual
call "%VENV_DIR%\Scripts\activate.bat"

:: Inicia o servidor
echo Iniciando o servidor Django na porta 8000...
python manage.py runserver 0.0.0.0:8000

:: Em caso de erro, mantém a janela aberta
pause 