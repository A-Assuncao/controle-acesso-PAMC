# Sistema de Controle de Acesso PAMC

![Django](https://img.shields.io/badge/Django-4.2%2B-green)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Status](https://img.shields.io/badge/Status-Production-success)

<div align="center">
  <img src="https://raw.githubusercontent.com/django/django/main/docs/images/django-logo-negative.svg" alt="Django Logo" width="300"/>
  <h3>Sistema de gerenciamento e controle de acesso para servidores</h3>
</div>

## 📋 Índice

- [Visão Geral](#-visão-geral)
- [Funcionalidades](#-funcionalidades)
- [Tecnologias](#-tecnologias)
- [Requisitos](#-requisitos)
- [Instalação](#-instalação)
  - [Instalação Automática (Windows)](#instalação-automática-windows)
  - [Instalação Manual](#instalação-manual)
- [Configuração](#-configuração)
- [Uso](#-uso)
- [Backup e Restauração](#-backup-e-restauração)
- [Ambiente de Produção](#-ambiente-de-produção)
- [Funcionamento Offline](#-funcionamento-offline)
- [Atualização](#-atualização)
- [Informações Importantes](#-informações-importantes)
- [Licença](#-licença)

## 🔍 Visão Geral

O Sistema de Controle de Acesso PAMC é uma aplicação web desenvolvida em Django que gerencia o acesso de servidores, registra entradas e saídas, e oferece ferramentas de relatórios e administração. O sistema foi projetado para ser fácil de usar, seguro e funcionar mesmo em ambientes sem conexão à internet.

## ✨ Funcionalidades

- **Gestão de Usuários**
  - Cadastro e gerenciamento de usuários
  - Sistema de autenticação seguro
  - Gerenciamento de senhas temporárias
  - Níveis de acesso personalizados

- **Controle de Acesso**
  - Registro de entrada e saída de servidores
  - Controle de plantões e turnos
  - Histórico completo de acessos

- **Relatórios**
  - Exportação de dados em Excel
  - Relatórios personalizados em PDF
  - Filtros avançados para busca

- **Sistema de Auditoria**
  - Log detalhado de ações dos usuários
  - Rastreamento de alterações
  - Histórico de operações

- **Modo Offline**
  - Funcionamento sem conexão à internet
  - Sincronização quando a conexão for restabelecida
  - Armazenamento local de recursos

## 🛠 Tecnologias

- **Backend**
  - Django 4.2+
  - Python 3.9+
  - SQLite (desenvolvimento) / PostgreSQL (produção opcional)

- **Frontend**
  - Bootstrap 5
  - JavaScript
  - jQuery
  
- **Ferramentas**
  - Ngrok (para acesso remoto)
  - NSSM (para serviço Windows)
  - Django ORM

## 📦 Requisitos

- Windows 10 ou superior
- Pelo menos 1GB de espaço em disco
- Mínimo de 2GB de RAM
- Acesso de Administrador (para instalação)

## 💻 Instalação

### Instalação Automática (Windows)

O sistema possui um instalador automatizado para ambientes Windows:

1. Baixe o arquivo `install.bat` do repositório
2. Clique com o botão direito e selecione "Executar como administrador"
3. Siga as instruções na tela para configurar o sistema
4. O instalador irá:
   - Instalar todas as dependências necessárias
   - Configurar o banco de dados
   - Criar um usuário administrador
   - Configurar o sistema como serviço do Windows
   - Instalar recursos para funcionamento offline

### Instalação Manual

Para instalar manualmente em ambiente de desenvolvimento:

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

4. Configure as variáveis de ambiente:
   - Crie um arquivo `.env` na raiz do projeto
   - Adicione as configurações necessárias (veja a seção Configuração)

5. Execute as migrações:
   ```bash
   python manage.py migrate
   ```

6. Crie um superusuário:
   ```bash
   python manage.py createsuperuser
   ```

7. Inicie o servidor:
   ```bash
   python manage.py runserver
   ```

## ⚙️ Configuração

O sistema utiliza variáveis de ambiente para configuração. Crie um arquivo `.env` na raiz do projeto com:

```
DJANGO_SECRET_KEY=sua_chave_secreta
DJANGO_DEBUG=True  # False em produção
DATABASE_URL=sqlite:///db.sqlite3  # Ou PostgreSQL em produção
```

Para configurar o banco de dados PostgreSQL em produção, use:
```
DATABASE_URL=postgresql://usuario:senha@host:porta/banco?sslmode=require
```

## 📝 Uso

1. Acesse o sistema pelo navegador:
   - Local: http://localhost:8000
   - Produção: URL configurada ou IP do servidor

2. Faça login com as credenciais de administrador

3. No painel principal:
   - Gerencie usuários em "Usuários"
   - Registre entradas e saídas em "Registro"
   - Acesse relatórios na seção "Relatórios"
   - Configure o sistema em "Configurações"

## 💾 Backup e Restauração

### Backup Manual

O banco de dados SQLite está localizado em `db.sqlite3`. Para realizar backup manualmente:

1. Pare o serviço (se estiver em produção)
2. Copie o arquivo `db.sqlite3` para local seguro
3. Reinicie o serviço

### Backup Automático

O sistema realiza backups automáticos diários:
- Os backups são armazenados em `%PROGRAMFILES%\ControleAcesso\backups\`
- Formato: `backup_YYYY-MM-DD.json`

### Restauração

Para restaurar um backup:

```bash
cd "%PROGRAMFILES%\ControleAcesso\app"
call "%PROGRAMFILES%\ControleAcesso\venv\Scripts\activate"
python manage.py loaddata "%PROGRAMFILES%\ControleAcesso\backups\backup_YYYY-MM-DD.json"
```

## 🌐 Ambiente de Produção

Para executar em produção:

1. Modifique as configurações em `.env`:
   ```
   DJANGO_DEBUG=False
   ALLOWED_HOSTS=seu_dominio.com,localhost,127.0.0.1
   ```

2. Colete os arquivos estáticos:
   ```
   python manage.py collectstatic --noinput
   ```

3. Use o servidor web integrado (apenas para teste):
   ```
   python manage.py runserver 0.0.0.0:8000 --insecure
   ```
   
4. Para produção real, use Nginx/Apache com Gunicorn/uWSGI

## 🔌 Funcionamento Offline

O sistema foi projetado para funcionar sem conexão à internet:

- Recursos como Bootstrap, jQuery e ícones são armazenados localmente
- O banco de dados SQLite funciona sem necessidade de servidor externo
- Todas as funcionalidades principais estão disponíveis offline
- O script de instalação configura automaticamente os recursos offline

## 🔄 Atualização

O sistema pode ser atualizado através do script de atualização:

```bash
"%PROGRAMFILES%\ControleAcesso\scripts\update.bat"
```

Este script:
- Realiza backup do banco de dados
- Atualiza o código do repositório
- Atualiza dependências
- Aplica migrações
- Reinicia o serviço

## ⚠️ Informações Importantes

- **Segurança**: Mantenha o acesso ao sistema restrito apenas a usuários autorizados
- **Backups**: Realize backups regulares para evitar perda de dados
- **Atualizações**: Verifique regularmente por atualizações de segurança
- **Logs**: Os logs do sistema são armazenados em `%PROGRAMFILES%\ControleAcesso\logs\`

## 📄 Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

---

<div align="center">
  <p>Desenvolvido por <a href="https://github.com/A-Assuncao">A-Assuncao</a></p>
  <p>© 2023-2024 Sistema de Controle de Acesso PAMC. Todos os direitos reservados.</p>
</div> 