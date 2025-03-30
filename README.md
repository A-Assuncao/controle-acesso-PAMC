# Sistema de Controle de Acesso - PAMC

Sistema para controle de entrada e saída de pessoas em uma penitenciária, desenvolvido com Django e Bootstrap 5.

## Requisitos

- Python 3.8 ou superior
- PostgreSQL
- pip (gerenciador de pacotes Python)

## Instalação

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/controle-acesso-PAMC.git
cd controle-acesso-PAMC
```

2. Crie um ambiente virtual e ative-o:
```bash
python -m venv venv
# No Windows:
venv\Scripts\activate
# No Linux/Mac:
source venv/bin/activate
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure o banco de dados PostgreSQL:
- Crie um banco de dados chamado `controle_acesso`
- Edite o arquivo `controle_acesso/settings.py` e atualize as configurações do banco de dados:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'controle_acesso',
        'USER': 'seu_usuario',
        'PASSWORD': 'sua_senha',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

5. Execute as migrações:
```bash
python manage.py makemigrations
python manage.py migrate
```

6. Crie um superusuário:
```bash
python manage.py createsuperuser
```

7. Inicie o servidor de desenvolvimento:
```bash
python manage.py runserver
```

8. Acesse o sistema em `http://localhost:8000`

## Funcionalidades

- Cadastro de pessoas com nome, documento e placa de veículo
- Registro de entrada e saída de pessoas
- Histórico de registros com filtros por data
- Geração de relatórios em PDF e Excel
- Sistema de logs de auditoria
- Interface responsiva com Bootstrap 5

## Segurança

- Autenticação de usuários
- Proteção contra alterações não autorizadas nos registros
- Logs de auditoria para rastreamento de ações
- Validação de dados em formulários

## Manutenção

Para manter o sistema atualizado:

1. Atualize as dependências periodicamente:
```bash
pip install -r requirements.txt --upgrade
```

2. Faça backup regular do banco de dados:
```bash
pg_dump -U seu_usuario controle_acesso > backup.sql
```

3. Monitore os logs de auditoria para identificar atividades suspeitas

## Suporte

Em caso de problemas ou dúvidas, abra uma issue no repositório do GitHub.

## Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo LICENSE para detalhes. 