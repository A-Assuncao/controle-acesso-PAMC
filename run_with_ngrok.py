import os
import sys
import subprocess
from django.core.management import execute_from_command_line
from ngrok_starter import start_ngrok

def run_server():
    # Configura o Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'controle_acesso.settings')
    
    # Inicia o ngrok
    ngrok_process = start_ngrok()
    
    try:
        # Inicia o servidor Django diretamente
        sys.argv = ['manage.py', 'runserver', '8000']
        execute_from_command_line(sys.argv)
    except KeyboardInterrupt:
        print("\nEncerrando servidor...")
    finally:
        # Encerra o ngrok
        ngrok_process.terminate()
        try:
            ngrok_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            ngrok_process.kill()

if __name__ == '__main__':
    run_server() 