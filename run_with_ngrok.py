import os
import sys
import time
import json
import logging
from datetime import datetime
import requests
from pyngrok import ngrok, conf
from dotenv import load_dotenv

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.environ.get('PROGRAMFILES', ''), 'ControleAcesso', 'logs', 'ngrok.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Carrega variáveis de ambiente
load_dotenv()

# URL do webhook do Discord
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1357105951878152435/uE4Uw7-ay4iHtsZvXvi75j0stthrNiE0SU4M_6ntgMbFO5a_2di95C51YIGoJuztkmWb"

def send_to_discord(ngrok_url):
    """Envia o URL do ngrok para o Discord via webhook."""
    try:
        current_time = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        message = {
            "content": None,
            "embeds": [
                {
                    "title": "🌐 URL do Servidor PAMC Atualizado",
                    "description": f"O servidor está disponível em um novo endereço:\n\n**{ngrok_url}**",
                    "color": 5814783,  # Azul claro
                    "fields": [
                        {
                            "name": "📅 Data de Atualização",
                            "value": current_time,
                            "inline": True
                        },
                        {
                            "name": "ℹ️ Status",
                            "value": "Online",
                            "inline": True
                        }
                    ],
                    "footer": {
                        "text": "Sistema de Controle de Acesso PAMC"
                    }
                }
            ]
        }
        
        response = requests.post(
            DISCORD_WEBHOOK,
            json=message,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 204:
            logger.info("Mensagem enviada com sucesso para o Discord")
        else:
            logger.error(f"Erro ao enviar mensagem para o Discord: {response.status_code}")
            
    except Exception as e:
        logger.error(f"Erro ao enviar para o Discord: {str(e)}")

def save_ngrok_url(ngrok_url):
    """Salva o URL do ngrok em um arquivo."""
    try:
        url_file = os.path.join(os.environ.get('PROGRAMFILES', ''), 'ControleAcesso', 'app', 'ngrok_url.txt')
        with open(url_file, 'w') as f:
            f.write(f"{ngrok_url}\nAtualizado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        logger.info("URL salvo em: %s", url_file)
    except Exception as e:
        logger.error("Erro ao salvar URL: %s", str(e))

def main():
    """Função principal que mantém o ngrok rodando."""
    logger.info("Iniciando serviço ngrok...")
    
    # Configura o ngrok para reconectar automaticamente
    conf.get_default().monitor_thread = False
    conf.get_default().auth_token = os.getenv('NGROK_AUTH_TOKEN', '')
    
    while True:
        try:
            # Tenta conectar o ngrok
            tunnel = ngrok.connect(8000)
            ngrok_url = tunnel.public_url
            
            logger.info("Ngrok conectado em: %s", ngrok_url)
            
            # Salva e envia o URL
            save_ngrok_url(ngrok_url)
            send_to_discord(ngrok_url)
            
            # Mantém o processo vivo
            while True:
                tunnels = ngrok.get_tunnels()
                if not tunnels:
                    logger.warning("Túnel perdido, reconectando...")
                    break
                time.sleep(60)  # Verifica a cada minuto
                
        except Exception as e:
            logger.error("Erro no ngrok: %s", str(e))
            logger.info("Tentando reconectar em 30 segundos...")
            time.sleep(30)
            
            # Limpa qualquer túnel existente
            try:
                ngrok.kill()
            except:
                pass

if __name__ == '__main__':
    main() 