@echo off
echo Atualizando Sistema de Controle de Acesso...

:: Vai para o diretório da aplicação
cd "%PROGRAMFILES%\ControleAcesso"

:: Para o serviço
net stop ControleAcesso

:: Ativa o ambiente virtual
call venv\Scripts\activate

:: Backup do banco de dados
python manage.py dumpdata > backup.json

:: Atualiza o código
git pull

:: Atualiza dependências
pip install -r requirements.txt

:: Aplica migrações
python manage.py migrate

:: Inicia o serviço
net start ControleAcesso

echo Atualizacao concluida!
timeout /t 5 