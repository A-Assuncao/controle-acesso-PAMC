@echo off
echo Atualizando Sistema de Controle de Acesso...

:: Vai para o diretório da aplicação
cd "%ProgramFiles%\ControleAcesso\app"

:: Verifica se o serviço está instalado antes de tentar parar
sc query ControleAcesso >nul 2>&1
if not %errorlevel% == 1060 (
    echo Parando servico ControleAcesso...
    net stop ControleAcesso
)

:: Ativa o ambiente virtual
call "%ProgramFiles%\ControleAcesso\venv\Scripts\activate.bat"

:: Backup do banco de dados
echo Criando backup do banco de dados...
if not exist "%ProgramFiles%\ControleAcesso\backups" mkdir "%ProgramFiles%\ControleAcesso\backups"
python manage.py dumpdata > "%ProgramFiles%\ControleAcesso\backups\backup_%date:~6,4%-%date:~3,2%-%date:~0,2%.json"

:: Atualiza o código
git pull

:: Atualiza dependências
echo Atualizando dependencias...
pip install -r requirements.txt

:: Aplica migrações
echo Aplicando migracoes do banco de dados...
python manage.py migrate

:: Coleta arquivos estáticos
echo Coletando arquivos estaticos...
python manage.py collectstatic --noinput

:: Atualiza scripts de manutenção
xcopy /Y "scripts\*.*" "%PROGRAMFILES%\ControleAcesso\scripts\"

:: Inicia os serviços se estiverem instalados
sc query ControleAcesso >nul 2>&1
if not %errorlevel% == 1060 (
    echo Iniciando servico ControleAcesso...
    net start ControleAcesso
)

echo Atualizacao concluida!
echo.
echo Pressione qualquer tecla para sair...
pause>nul 