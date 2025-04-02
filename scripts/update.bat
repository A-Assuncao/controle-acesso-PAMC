@echo off
echo Atualizando Sistema de Controle de Acesso...

:: Vai para o diretório da aplicação
cd "%PROGRAMFILES%\ControleAcesso\app"

:: Para os serviços
net stop ControleAcessoNgrok
net stop ControleAcesso

:: Ativa o ambiente virtual
call "%PROGRAMFILES%\ControleAcesso\venv\Scripts\activate"

:: Backup do banco de dados
python manage.py dumpdata > "%PROGRAMFILES%\ControleAcesso\backups\backup_%date:~6,4%-%date:~3,2%-%date:~0,2%.json"

:: Atualiza o código
git pull

:: Atualiza dependências
pip install -r requirements.txt

:: Aplica migrações
python manage.py migrate

:: Atualiza scripts de manutenção
xcopy /Y "scripts\*.*" "%PROGRAMFILES%\ControleAcesso\scripts\"

:: Inicia os serviços
net start ControleAcesso
timeout /t 5
net start ControleAcessoNgrok

echo Atualizacao concluida!
timeout /t 5 