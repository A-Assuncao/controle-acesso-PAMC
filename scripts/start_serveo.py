import subprocess
import sys
import os
import time
import logging
import re
import webbrowser
from pathlib import Path

# Tenta importar módulos opcionais
try:
    from dotenv import load_dotenv
    load_dotenv()  # Carrega variáveis de ambiente
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# Configuração de logging
log_dir = Path(os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'ControleAcesso', 'logs'))
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "serveo.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

# Caminhos importantes
INSTALL_ROOT = os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'ControleAcesso')
APP_DIR = os.path.join(INSTALL_ROOT, 'app')
VENV_DIR = os.path.join(INSTALL_ROOT, 'venv')

# Ajusta o PATH para incluir o ambiente virtual
python_exe = os.path.join(VENV_DIR, 'Scripts', 'python.exe')
if not os.path.exists(python_exe):
    python_exe = sys.executable

def send_to_discord(url):
    """Envia o link do serveo para o Discord via webhook"""
    # Usar o webhook hardcoded caso não encontre no ambiente
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL', 'https://discord.com/api/webhooks/1357105951878152435/uE4Uw7-ay4iHtsZvXvi75j0stthrNiE0SU4M_6ntgMbFO5a_2di95C51YIGoJuztkmWb')
    
    if not REQUESTS_AVAILABLE:
        logging.warning("Módulo requests não instalado. Instalando...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
            import requests
            REQUESTS_AVAILABLE = True
        except:
            logging.error("Falha ao instalar requests. Não é possível enviar para o Discord.")
            return
    
    try:
        payload = {
            "content": f"🌐 Nova URL do Sistema de Controle de Acesso: {url}"
        }
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
        logging.info(f"Link enviado com sucesso para o Discord: {url}")
        print(f"Link enviado para o Discord: {url}")
    except Exception as e:
        logging.error(f"Erro ao enviar para o Discord: {str(e)}")
        print(f"ERRO ao enviar para o Discord: {str(e)}")

def start_django_server():
    """Inicia o servidor Django em um processo separado"""
    logging.info("Iniciando servidor Django...")
    print("Iniciando servidor Django em localhost:8000...")
    
    # Inicia o processo do servidor Django
    try:
        django_process = subprocess.Popen(
            [python_exe, "manage.py", "runserver", "0.0.0.0:8000"],
            cwd=APP_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            universal_newlines=True
        )
        
        # Espera um pouco para o servidor iniciar
        time.sleep(3)
        
        if django_process.poll() is None:
            logging.info("Servidor Django iniciado com sucesso")
            print("Servidor Django rodando em http://localhost:8000")
            
            # Abre o navegador local
            try:
                webbrowser.open('http://localhost:8000')
                logging.info("Navegador aberto em http://localhost:8000")
            except Exception as e:
                logging.error(f"Erro ao abrir navegador: {str(e)}")
                
            return django_process
        else:
            out, err = django_process.communicate()
            logging.error(f"Falha ao iniciar servidor Django: {err}")
            print(f"ERRO: Falha ao iniciar servidor Django: {err}")
            return None
    except Exception as e:
        logging.error(f"Erro ao iniciar Django: {str(e)}")
        print(f"ERRO: Falha ao iniciar Django: {str(e)}")
        return None

def start_serveo(django_process):
    """Inicia o túnel do serveo para a porta 8000"""
    try:
        # Comando para iniciar o serveo
        cmd = "ssh -R 80:localhost:8000 serveo.net"
        
        logging.info("Iniciando túnel do serveo...")
        print("Iniciando túnel do serveo... Aguarde a conexão ser estabelecida.")
        
        # Executa o comando
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Padrão para encontrar a URL do serveo
        url_pattern = r'https?://[^\s]+'
        
        # Monitora a saída do processo
        while True:
            # Verifica se o servidor Django ainda está rodando
            if django_process and django_process.poll() is not None:
                logging.error("O servidor Django foi encerrado. Tentando reiniciar...")
                print("\nO servidor Django foi encerrado. Tentando reiniciar...\n")
                django_process = start_django_server()
                
            output = process.stdout.readline()
            if output:
                output = output.strip()
                logging.info(output)
                print(output)
                
                # Procura por URLs na saída
                if 'Forwarding HTTP traffic from' in output:
                    urls = re.findall(url_pattern, output)
                    if urls:
                        serveo_url = urls[0]
                        print(f"\nURL de acesso externo: {serveo_url}\n")
                        
                        # Salva a URL atual em um arquivo
                        url_file = log_dir / "current_url.txt"
                        with open(url_file, "w") as f:
                            f.write(serveo_url)
                        print(f"URL salva em: {url_file}")
                        
                        # Envia para o Discord
                        send_to_discord(serveo_url)
            
            error = process.stderr.readline()
            if error:
                error = error.strip()
                logging.error(error)
                print(f"ERRO: {error}")
            
            # Verifica se o processo ainda está rodando
            if process.poll() is not None:
                logging.error("O processo do serveo foi encerrado. Tentando reconectar...")
                print("\nO processo do serveo foi encerrado. Tentando reconectar...\n")
                time.sleep(5)  # Espera 5 segundos antes de tentar reconectar
                process = subprocess.Popen(
                    cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                
    except Exception as e:
        logging.error(f"Erro ao iniciar o serveo: {str(e)}")
        print(f"ERRO: Falha ao iniciar o serveo: {str(e)}")
        print("Pressione Enter para sair...")
        input()
        sys.exit(1)

if __name__ == "__main__":
    print("Sistema de Controle de Acesso - Iniciando...")
    print("=" * 50)
    
    # Inicia o servidor Django
    django_process = start_django_server()
    
    # Inicia o túnel Serveo (que monitora e mantém o servidor Django)
    if django_process:
        start_serveo(django_process)
    else:
        logging.error("Não foi possível iniciar o servidor Django. O Serveo não será iniciado.")
        print("ERRO: Não foi possível iniciar o servidor Django. O Serveo não será iniciado.")
        print("Pressione Enter para sair...")
        input()
        sys.exit(1) 