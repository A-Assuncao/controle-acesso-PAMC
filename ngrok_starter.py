import os
import sys
import time
import json
import urllib.request
import subprocess

def kill_existing_ngrok():
    """Encerra qualquer processo ngrok existente"""
    if sys.platform == 'win32':
        subprocess.run(['taskkill', '/F', '/IM', 'ngrok.exe'], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL)
    else:
        subprocess.run(['pkill', 'ngrok'], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL)
    time.sleep(1)  # Aguarda o processo ser encerrado

def get_ngrok_url():
    """Obtém a URL pública do ngrok"""
    try:
        response = urllib.request.urlopen('http://localhost:4040/api/tunnels')
        data = json.loads(response.read())
        return data['tunnels'][0]['public_url']
    except:
        return None

def start_ngrok():
    """Inicia o ngrok e retorna o processo"""
    # Garante que não há nenhuma instância do ngrok rodando
    kill_existing_ngrok()
    
    # Inicia o ngrok em background
    ngrok_cmd = ['ngrok', 'http', '8000', '--log=stdout']
    with open('ngrok.log', 'w') as log_file:
        ngrok_process = subprocess.Popen(
            ngrok_cmd,
            stdout=log_file,
            stderr=log_file
        )
    
    # Aguarda o ngrok inicializar e obtém a URL
    print("\nIniciando servidor e ngrok...")
    for _ in range(10):  # Tenta por 5 segundos
        time.sleep(0.5)
        url = get_ngrok_url()
        if url:
            print(f"\nNgrok URL: {url}")
            break
    
    print("Interface do ngrok: http://localhost:4040")
    print("Pressione CTRL+C para encerrar o servidor\n")
    
    return ngrok_process 