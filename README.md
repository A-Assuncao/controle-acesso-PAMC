# Sistema de Controle de Acesso

Sistema para controle de acesso de servidores, desenvolvido em Django.

## Requisitos

- Python 3.9 ou superior
- pip (gerenciador de pacotes do Python)
- ngrok (opcional, para demonstrações)

## Instalação Local

1. Clone o repositório:
```bash
git clone https://github.com/A-Assuncao/controle-acesso-PAMC.git
cd controle-acesso-PAMC
```

2. Crie e ative um ambiente virtual:
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Execute as migrações do banco de dados:
```bash
python manage.py migrate
```

5. Crie um superusuário (administrador):
```bash
python manage.py createsuperuser
```

6. Inicie o servidor:
```bash
# Servidor local
python manage.py runserver

# OU para demonstração com ngrok
python run_with_ngrok.py
```

7. Acesse o sistema:
- Local: http://localhost:8000
- Demonstração: A URL do ngrok será exibida no terminal

## Configurando o ngrok para Demonstrações

1. Instale o ngrok:
```bash
# Windows (com Chocolatey)
choco install ngrok

# Linux
snap install ngrok

# Mac
brew install ngrok
```

2. Autentique o ngrok:
```bash
ngrok config add-authtoken SEU_TOKEN_AQUI
```

3. Para demonstrar o sistema, use:
```bash
python run_with_ngrok.py
```

## Uso

1. Faça login com o usuário administrador criado
2. Cadastre os servidores no sistema
3. Registre entradas e saídas
4. Gere relatórios conforme necessário

## Funcionalidades

- Registro de entrada e saída de servidores
- Controle de plantões
- Histórico de acessos
- Relatórios em Excel
- Gerenciamento de usuários
- Log de auditoria

## Backup

O banco de dados SQLite está localizado em `db.sqlite3`. Faça backups regulares deste arquivo para manter seus dados seguros. 