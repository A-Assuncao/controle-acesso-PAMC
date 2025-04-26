@echo off
echo Iniciando o tunel serveo...

:: Ativa o ambiente virtual
call .venv\Scripts\activate.bat

:: Executa o script Python
python scripts\start_serveo.py

:: Mantém o terminal aberto em caso de erro
pause 