import subprocess
import sys
import os
import time
import logging
import re
import requests
from pathlib import Path
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Configuração de logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "serveo.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

def send_to_discord(url):
    """Envia o link do serveo para o Discord via webhook"""
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        logging.warning("URL do webhook do Discord não configurada. Pulando envio.")
        return

    try:
        payload = {
            "content": f"🌐 Nova URL do Sistema de Controle de Acesso: {url}"
        }
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
        logging.info("Link enviado com sucesso para o Discord")
    except Exception as e:
        logging.error(f"Erro ao enviar para o Discord: {str(e)}")

def start_serveo():
    """Inicia o túnel do serveo para a porta 8000"""
    try:
        # Comando para iniciar o serveo
        cmd = "ssh -R 80:localhost:8000 serveo.net"
        
        logging.info("Iniciando túnel do serveo...")
        
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
            output = process.stdout.readline()
            if output:
                output = output.strip()
                logging.info(output)
                
                # Procura por URLs na saída
                if 'Forwarding HTTP traffic from' in output:
                    urls = re.findall(url_pattern, output)
                    if urls:
                        serveo_url = urls[0]
                        # Salva a URL atual em um arquivo
                        with open(log_dir / "current_url.txt", "w") as f:
                            f.write(serveo_url)
                        # Envia para o Discord
                        send_to_discord(serveo_url)
            
            error = process.stderr.readline()
            if error:
                logging.error(error.strip())
            
            # Verifica se o processo ainda está rodando
            if process.poll() is not None:
                logging.error("O processo do serveo foi encerrado. Tentando reconectar...")
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
        sys.exit(1)

if __name__ == "__main__":
    start_serveo() 