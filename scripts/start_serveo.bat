@echo off
echo Iniciando o tunel serveo...

:: Ativa o ambiente virtual
cd /d "%ProgramFiles%\ControleAcesso\app"
call "%ProgramFiles%\ControleAcesso\venv\Scripts\activate.bat"

:: Executa o script Python
python "%ProgramFiles%\ControleAcesso\scripts\start_serveo.py"

:: Mantém o terminal aberto em caso de erro
pause 