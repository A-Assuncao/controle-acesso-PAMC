# Sistema de Controle de Acesso

Sistema para controle de acesso de servidores, desenvolvido em Django.

## Requisitos

- Python 3.9 ou superior
- pip (gerenciador de pacotes do Python)

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
python manage.py runserver
```

7. Acesse o sistema:
- Local: http://localhost:8000

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
- Modo de treinamento para novos usuários

## Backup

O banco de dados SQLite está localizado em `db.sqlite3`. Faça backups regulares deste arquivo para manter seus dados seguros.

## Executando em Produção Local

Para executar o sistema em modo de produção local, siga estas etapas:

1. **Colete os arquivos estáticos**:
   ```
   python manage.py collectstatic --noinput
   ```

2. **Execute o servidor em modo de produção**:
   ```
   python run_production.py
   ```
   ou
   ```
   python manage.py runserver 0.0.0.0:8000 --insecure
   ```

3. **Acesse o sistema**:
   Abra seu navegador e acesse `http://localhost:8000`

## Observações Importantes

- O modo de produção local (`DEBUG=False`) permite visualizar as páginas de erro personalizadas
- A opção `--insecure` permite que o Django sirva arquivos estáticos mesmo com `DEBUG=False`
- Em um ambiente de produção real, você deve usar um servidor web como Nginx ou Apache para servir arquivos estáticos 