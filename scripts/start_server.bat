@echo off
echo Iniciando Servidor de Controle de Acesso...

:: Ativa o ambiente virtual
cd /d "%ProgramFiles%\ControleAcesso\app"
call "%ProgramFiles%\ControleAcesso\venv\Scripts\activate.bat"

:: Inicia o servidor Django
python manage.py runserver 0.0.0.0:8000

:: Mantém o terminal aberto em caso de erro
pause 