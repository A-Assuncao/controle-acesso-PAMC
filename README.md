# Sistema de Controle de Acesso PAMC

![Django](https://img.shields.io/badge/Django-4.2%2B-092E20?style=for-the-badge&logo=django)
![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.0-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Production-success?style=for-the-badge)

<div align="center">
  <img src="https://raw.githubusercontent.com/django/django/main/docs/images/django-logo-negative.svg" alt="Django Logo" width="300"/>
  <h3>Sistema completo de gestão e controle de acesso para servidores penitenciários</h3>
  <p><em>Desenvolvido com Django, Bootstrap e tecnologias modernas para máxima confiabilidade</em></p>
</div>

---

## 📋 Índice

- [🔍 Visão Geral](#-visão-geral)
- [✨ Funcionalidades](#-funcionalidades)
- [🏗️ Arquitetura](#-arquitetura)
- [🛠 Tecnologias](#-tecnologias)
- [📦 Requisitos](#-requisitos)
- [💻 Instalação](#-instalação)
- [🚀 Tutorial: IIS + Localhost.run](#-tutorial-iis--localhostrun)
- [⚙️ Configuração](#-configuração)
- [📖 Guia de Uso](#-guia-de-uso)
- [🎓 Ambiente de Treinamento](#-ambiente-de-treinamento)
- [📊 Dashboard e Relatórios](#-dashboard-e-relatórios)
- [🔐 Segurança](#-segurança)
- [💾 Backup e Restauração](#-backup-e-restauração)
- [🌐 Acesso Remoto](#-acesso-remoto)
- [🔧 Desenvolvimento](#-desenvolvimento)
- [📚 Documentação Técnica](#-documentação-técnica)
- [🐛 Troubleshooting](#-troubleshooting)
- [📄 Licença](#-licença)

---

## 🔍 Visão Geral

O **Sistema de Controle de Acesso PAMC** é uma aplicação web robusta desenvolvida especificamente para o controle de acesso em ambientes penitenciários. O sistema oferece gestão completa de servidores, registros de entrada/saída, relatórios detalhados e um ambiente de treinamento separado para capacitação de novos usuários.

### 🎯 Principais Características

- **🛡️ Segurança Avançada**: Autenticação robusta, controle de sessões e logs de auditoria
- **📱 Interface Moderna**: Design responsivo com Bootstrap 5 e UX otimizada
- **🔌 Funcionamento Offline**: Operação completa sem conexão à internet
- **🎓 Ambiente de Treinamento**: Área isolada para capacitação de usuários
- **📊 Relatórios Inteligentes**: Exportação em Excel e filtros avançados
- **🌐 Acesso Remoto**: Integração com Serveo para acesso externo seguro

---

## ✨ Funcionalidades

### 👥 **Gestão de Usuários e Segurança**
- **Controle de Acesso**: Sistema completo de autenticação com níveis hierárquicos
- **Gestão de Senhas**: Sistema moderno de troca de senhas com validação em tempo real
- **Perfis de Usuário**: Configurações personalizadas e controle de permissões
- **Senhas Temporárias**: Geração automática para novos usuários
- **Auditoria Completa**: Logs detalhados de todas as ações do sistema

### 📝 **Controle de Acesso de Servidores**
- **Registro de Entrada/Saída**: Interface intuitiva para controle de acesso
- **Gestão de Plantões**: Organização por turnos (ALFA, BRAVO, CHARLIE, DELTA)
- **Tipos de Funcionário**: Categorização (Plantonista, Expediente, Visitante, Terceirizado)
- **Controle de Veículos**: Validação automática de placas no formato Mercosul
- **Saídas Definitivas**: Processo específico para registros de egresso
- **Edição de Registros**: Sistema completo de edição com justificativas obrigatórias

### 📊 **Dashboard e Monitoramento**
- **Painel em Tempo Real**: Visualização instantânea de entradas, saídas e pendências
- **Cards Informativos**: Totalizadores com cores intuitivas
- **Lista Dinâmica**: Registros ordenados por horário com ações rápidas
- **Filtros Avançados**: Busca por plantão, tipo de funcionário e status
- **Limpeza de Dashboard**: Função para reset do plantão atual

### 📈 **Relatórios e Exportação**
- **Exportação Excel**: Planilhas formatadas com dados completos
- **Histórico Completo**: Consulta de todos os registros com filtros
- **Relatórios por Plantão**: Dados específicos de cada turno
- **Busca Avançada**: Filtros por data, servidor, plantão e status
- **Dados Estruturados**: Informações organizadas para análise

### 🎓 **Ambiente de Treinamento**
- **Dashboard Isolado**: Réplica fiel do sistema principal para práticas
- **Tutoriais em Vídeo**: Biblioteca de vídeos explicativos organizados por categoria
- **Dados de Teste**: Registros fictícios para simulações realísticas
- **Reset de Dados**: Limpeza fácil para recomeçar treinamentos
- **Funcionalidades Completas**: Todas as operações disponíveis para prática

### 🔧 **Administração e Manutenção**
- **Gestão de Servidores**: CRUD completo com validações
- **Importação em Massa**: Upload de planilhas Excel para cadastro
- **Backup Automático**: Rotinas diárias de backup dos dados
- **Limpeza de Banco**: Ferramentas para manutenção dos dados
- **Atualização Automática**: Git pull agendado para atualizações

---

## 🏗️ Arquitetura

O sistema foi desenvolvido seguindo princípios de **arquitetura limpa** e boas práticas:

```
Sistema de Controle de Acesso PAMC/
├── 🎯 Core Application (Django)
│   ├── Models: Servidor, RegistroAcesso, LogAuditoria, PerfilUsuario
│   ├── Views: Dashboard, Treinamento, Relatórios, Administração
│   └── Templates: Interface responsiva com Bootstrap 5
├── 🎓 Training Environment
│   ├── Isolated Models: ServidorTreinamento, RegistroAcessoTreinamento
│   ├── Video Tutorials: Sistema de tutoriais categorizados
│   └── Separate Dashboard: Ambiente completamente isolado
├── 🔐 Security Layer
│   ├── Authentication: Sistema robusto de login/logout
│   ├── Authorization: Middleware de controle de acesso
│   └── Audit Trail: Logs completos de auditoria
└── 🌐 Infrastructure
    ├── Offline Support: Recursos locais para funcionamento sem internet
    ├── Remote Access: Integração com Serveo para túneis
    └── Auto-update: Scripts de atualização automática
```

---

## 🛠 Tecnologias

### 💾 **Backend**
- **Django 4.2+**: Framework web robusto e seguro
- **Python 3.9+**: Linguagem de programação moderna
- **SQLite**: Banco de dados embarcado para máxima portabilidade
- **Django ORM**: Mapeamento objeto-relacional para consultas seguras

### 🎨 **Frontend**
- **Bootstrap 5**: Framework CSS moderno e responsivo
- **JavaScript ES6+**: Interações dinâmicas e validações
- **Bootstrap Icons**: Biblioteca completa de ícones
- **CSS3 Custom**: Estilos personalizados para melhor UX

### 📦 **Dependências Principais**
```python
Django>=4.2.0          # Framework web
django-bootstrap5       # Integração Bootstrap
pandas>=2.0.0          # Manipulação de dados
reportlab>=4.0.4       # Geração de PDFs
openpyxl>=3.1.0        # Manipulação de Excel
python-dotenv>=1.0.0   # Gestão de variáveis de ambiente
requests>=2.31.0       # Requisições HTTP
```

### 🔧 **Ferramentas de Desenvolvimento**
- **UV**: Gerenciador moderno de dependências Python
- **Git**: Controle de versão com atualizações automáticas
- **Pytest**: Framework de testes com cobertura
- **Black/Ruff**: Formatação e linting automático

---

## 📦 Requisitos

### 🖥️ **Sistema**
- **Windows 10/11** ou **Linux** (Ubuntu 20.04+)
- **2GB RAM** mínimo (4GB recomendado)
- **1GB espaço livre** em disco
- **Acesso Administrator** (apenas para instalação)

### 🐍 **Python**
- **Python 3.9+** com pip
- **UV** (instalado automaticamente)
- **Git** (para atualizações automáticas)

---

## 💻 Instalação

### 🚀 **Instalação Automática (Windows)**

1. **Abra o PowerShell como Administrador**
2. **Execute o comando de instalação:**

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force; `
[Net.ServicePointManager]::SecurityProtocol = `
[Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12; `
iex (iwr -UseBasicParsing `
https://raw.githubusercontent.com/A-Assuncao/controle-acesso-PAMC/main/install.ps1).Content
```

3. **Siga as instruções no terminal**

### ⚙️ **O que o instalador faz:**
- ✅ Instala dependências (Python, Git, UV)
- ✅ Configura ambiente virtual com UV
- ✅ Instala o projeto em `%ProgramFiles%\ControleAcesso\`
- ✅ Configura banco de dados SQLite
- ✅ Cria usuário administrador
- ✅ Instala recursos offline (Bootstrap, jQuery, etc.)
- ✅ Configura serviço Windows para execução automática
- ✅ Cria atalhos na área de trabalho
- ✅ Agenda atualizações automáticas (18:00 diário)
- ✅ Configura túnel Serveo para acesso remoto

### 🛠️ **Instalação Manual (Desenvolvimento)**

```bash
# Clone o repositório
git clone https://github.com/A-Assuncao/controle-acesso-PAMC.git
cd controle-acesso-PAMC

# Instale e configure UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Crie e ative ambiente virtual
uv venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Instale dependências
uv pip install -r requirements.txt

# Configure banco de dados
uv run python manage.py migrate
uv run python manage.py collectstatic --noinput

# Crie superusuário
uv run python manage.py createsuperuser

# Inicie o servidor
uv run python manage.py runserver
```

---

## 🚀 Tutorial: IIS + Localhost.run

Para uma configuração completa do sistema usando **Internet Information Services (IIS)** do Windows e acesso externo via **localhost.run**, consulte nosso tutorial detalhado:

### 📖 **[📋 Tutorial Completo: IIS + Localhost.run](TUTORIAL_IIS_LOCALHOST_RUN.md)**

Este tutorial abrange:

- ✅ **Instalação do Python** e configuração do ambiente
- ✅ **Configuração do IIS** com todos os componentes necessários
- ✅ **Instalação do HttpPlatformHandler** para Django
- ✅ **Configuração do site** no Gerenciador do IIS
- ✅ **Execução do Django** localmente via IIS
- ✅ **Acesso via rede local** (IP da máquina)
- ✅ **Configuração do localhost.run** para acesso externo
- ✅ **Troubleshooting** e soluções para problemas comuns

### 🎯 **Resumo Rápido**

```bash
# 1. Instalar Python e Git
# 2. Ativar IIS com componentes necessários
# 3. Instalar HttpPlatformHandler
# 4. Clonar repositório em C:\inetpub\wwwroot\
# 5. Configurar site no IIS
# 6. Configurar ambiente Python
# 7. Executar Django via IIS
# 8. Configurar localhost.run (opcional)
```

### 🔗 **Acesso Resultante**

- **Local**: `http://localhost` ou `http://127.0.0.1`
- **Rede**: `http://192.168.0.10` (IP da máquina)
- **Externo**: `https://gray-cloud.localhost.run` (via túnel)

**📚 [Clique aqui para acessar o tutorial completo](TUTORIAL_IIS_LOCALHOST_RUN.md)**

---

## ⚙️ Configuração

### 🔐 **Variáveis de Ambiente**

Crie um arquivo `.env` na raiz do projeto:

```env
# Configurações do Django
DJANGO_SECRET_KEY=sua_chave_secreta_super_segura
DJANGO_DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,seu_dominio.com

# Banco de dados
DATABASE_URL=sqlite:///db.sqlite3

# Integração Discord (opcional)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/seu_webhook

# Configurações de segurança
SESSION_COOKIE_AGE=7200
SECURE_BROWSER_XSS_FILTER=True
```

### 🗄️ **Configuração de Banco**

Para **desenvolvimento** (padrão):
```env
DATABASE_URL=sqlite:///db.sqlite3
```

Para **produção com PostgreSQL**:
```env
DATABASE_URL=postgresql://usuario:senha@host:porta/banco?sslmode=require
```

---

## 📖 Guia de Uso

### 🚪 **Primeiro Acesso**

1. **Acesse o sistema**: `http://localhost:8000`
2. **Faça login** com as credenciais do administrador
3. **Explore o Dashboard** principal
4. **Configure usuários** em "Gestão de Usuários"
5. **Importe servidores** via planilha Excel (opcional)

### 📝 **Fluxo Principal de Trabalho**

#### **1. Registro de Entrada**
```
Dashboard → Registrar Entrada → Buscar Servidor → Confirmar Dados → Salvar
```

#### **2. Registro de Saída**
```
Dashboard → Localizar Registro → Botão "Saída" → Confirmar → Finalizar
```

#### **3. Edição de Registros**
```
Dashboard → Registro → Editar → Inserir Justificativa → Salvar Alterações
```

#### **4. Relatórios**
```
Menu → Histórico → Aplicar Filtros → Exportar Excel/PDF
```

### 🎯 **Recursos Avançados**

- **Busca Inteligente**: Digite nome, documento ou placa para busca automática
- **Filtros Dinâmicos**: Combine múltiplos critérios para relatórios específicos
- **Ações em Lote**: Selecione múltiplos registros para operações simultâneas
- **Atalhos de Teclado**: Navegue rapidamente com teclas de atalho
- **Auto-save**: Dados salvos automaticamente para evitar perdas

---

## 🎓 Ambiente de Treinamento

O sistema inclui um **ambiente de treinamento completamente isolado** para capacitação de novos usuários.

### 🌟 **Características**

- **🔒 Isolamento Total**: Dados separados do sistema principal
- **📚 Tutoriais Integrados**: Vídeos explicativos para cada funcionalidade
- **🎯 Dados Realísticos**: Simulações próximas do ambiente real
- **🔄 Reset Fácil**: Limpeza rápida para recomeçar treinamentos
- **✅ Funcionalidades Completas**: Todas as operações disponíveis

### 📺 **Tutoriais em Vídeo**

Os tutoriais estão organizados por categoria:

- **📥 Registro de Entrada**: Como registrar novos acessos
- **📤 Registro de Saída**: Procedimentos de saída
- **✏️ Edição de Registros**: Como editar e justificar alterações
- **🗑️ Exclusão de Registros**: Processo seguro de exclusão
- **📊 Gestão da Planilha**: Exportação e manipulação de dados
- **⚙️ Funcionalidades Gerais**: Navegação e recursos do sistema

### 🎯 **Como Usar o Treinamento**

1. **Acesse**: Menu → Ambiente de Treinamento
2. **Assista**: Tutoriais específicos para cada função
3. **Pratique**: Use o dashboard de treinamento livremente
4. **Reset**: Limpe os dados quando necessário
5. **Repita**: Quantas vezes precisar até dominar

---

## 📊 Dashboard e Relatórios

### 📈 **Dashboard Principal**

O dashboard oferece visão completa e em tempo real:

```
┌─────────────────────────────────────────────────────────────┐
│  🏠 Dashboard - Sistema de Controle de Acesso PAMC          │
├─────────────────────────────────────────────────────────────┤
│  📊 Cards de Status:                                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │ 📥 Entradas │ │ 📤 Saídas   │ │ ⏳ Pendentes │           │
│  │     125     │ │     118     │ │      7      │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
│                                                              │
│  🕒 Plantão Atual: ALFA | Hora: 14:30 | 👥 Operador: João  │
│                                                              │
│  📋 Lista de Registros Ativos:                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Nome           │ Entrada │ Status    │ Ações          │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │ João Silva     │ 08:00   │ 🔴 Pendente│ [Saída][Edit] │   │
│  │ Maria Santos   │ 08:15   │ ✅ Saiu    │ [View][Edit]  │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 📋 **Relatórios Disponíveis**

#### **📊 Histórico Completo**
- Todos os registros com filtros avançados
- Exportação em Excel com formatação profissional
- Busca por período, plantão, servidor ou status
- Ordenação por múltiplos critérios

#### **📈 Relatório de Plantão**
- Dados específicos de cada turno
- Estatísticas de entrada/saída
- Identificação de pendências
- Resumo executivo automático

#### **🔍 Relatórios Personalizados**
- Filtros combinados por múltiplos critérios
- Exportação em diferentes formatos
- Agendamento de relatórios automáticos
- Compartilhamento via email/Discord

---

## 🔐 Segurança

### 🛡️ **Camadas de Segurança**

#### **🔑 Autenticação**
- Sistema robusto de login/logout
- Senhas com validação avançada (8+ caracteres, maiúscula, minúscula, número, especial)
- Senhas temporárias para novos usuários
- Controle de sessões com timeout automático

#### **🚪 Autorização**
- Middleware de controle de acesso
- Níveis hierárquicos de permissão
- Proteção de rotas sensíveis
- Separação entre usuários comuns e administradores

#### **📝 Auditoria**
- Log completo de todas as ações
- Rastreamento de alterações com justificativas
- Histórico imutável de operações
- Identificação de usuários responsáveis

### 🔒 **Validações e Proteções**

- **CSRF Protection**: Proteção contra ataques cross-site
- **XSS Prevention**: Sanitização de entradas de usuário
- **SQL Injection**: ORM Django para consultas seguras
- **Rate Limiting**: Controle de tentativas de login
- **Secure Headers**: Cabeçalhos de segurança configurados

### 📊 **Monitoramento**

- Logs detalhados em `%PROGRAMFILES%\ControleAcesso\logs\`
- Alertas automáticos para ações críticas
- Relatórios de segurança periódicos
- Backup automático de logs de auditoria

---

## 💾 Backup e Restauração

### 🔄 **Backup Automático**

O sistema realiza backups automáticos diários:

```powershell
# Localização dos backups
%PROGRAMFILES%\ControleAcesso\backups\

# Formato dos arquivos
backup_2024-01-15.json
backup_2024-01-16.json
backup_2024-01-17.json
```

### 💾 **Backup Manual**

Para criar um backup manual:

```bash
# Via comando Django
uv run python manage.py dumpdata --indent 2 > backup_manual.json

# Via cópia direta do SQLite
cp db.sqlite3 backup_db_$(date +%Y%m%d).sqlite3
```

### 🔄 **Restauração**

Para restaurar um backup:

```bash
# Método 1: Via Django loaddata
uv run python manage.py loaddata backup_2024-01-15.json

# Método 2: Substituição direta do banco
cp backup_db_20240115.sqlite3 db.sqlite3
```

### ☁️ **Backup em Nuvem**

Configure backup automático para nuvem (opcional):

```env
# No arquivo .env
BACKUP_CLOUD_PROVIDER=aws_s3
BACKUP_BUCKET=meu-bucket-backup
AWS_ACCESS_KEY_ID=sua_chave
AWS_SECRET_ACCESS_KEY=sua_chave_secreta
```

---

## 🌐 Acesso Remoto

### 🚇 **Túnel Serveo**

O sistema inclui integração com Serveo para acesso remoto seguro:

#### **🔧 Configuração Automática**
- Script Python para estabelecer túnel
- Reconexão automática em caso de queda
- Envio automático de URL via Discord webhook
- Logs detalhados de conexão

#### **🔗 Como Funciona**
```bash
# O script automaticamente:
1. Inicia servidor Django local (localhost:8000)
2. Estabelece túnel SSH com Serveo
3. Obtém URL público (ex: https://abcd1234.serveo.net)
4. Envia URL para Discord/Telegram
5. Monitora conexão e reconecta se necessário
```

#### **📱 Uso Prático**
1. Execute o atalho "Controle de Acesso" na área de trabalho
2. Aguarde a URL ser enviada no Discord
3. Acesse de qualquer lugar com a URL recebida
4. Login funciona normalmente

### 🔐 **Segurança do Acesso Remoto**

- **HTTPS Forçado**: Apenas conexões criptografadas
- **Autenticação Obrigatória**: Login necessário para qualquer acesso
- **Session Security**: Cookies seguros e timeout automático
- **Rate Limiting**: Proteção contra ataques de força bruta

---

## 🔧 Desenvolvimento

### 🛠️ **Configuração do Ambiente de Desenvolvimento**

```bash
# 1. Clone e configure
git clone https://github.com/A-Assuncao/controle-acesso-PAMC.git
cd controle-acesso-PAMC

# 2. Configure UV (gerenciador moderno)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv

# 3. Ative ambiente virtual
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# 4. Instale dependências de desenvolvimento
uv pip install -r requirements.txt
uv pip install pytest pytest-django black ruff mypy

# 5. Configure banco de desenvolvimento
uv run python manage.py migrate
uv run python manage.py loaddata fixtures/dev_data.json
uv run python manage.py createsuperuser

# 6. Execute testes
uv run pytest

# 7. Inicie servidor de desenvolvimento
uv run python manage.py runserver
```

### 📋 **Comandos Úteis**

```bash
# Testes com cobertura
uv run pytest --cov=core --cov-report=html

# Formatação de código
uv run black .
uv run ruff check .

# Verificação de tipos
uv run mypy core/

# Migrações
uv run python manage.py makemigrations
uv run python manage.py migrate

# Coleta de arquivos estáticos
uv run python manage.py collectstatic
```

### 🏗️ **Estrutura do Projeto**

```
controle-acesso-PAMC/
├── 📁 core/                    # Aplicação principal
│   ├── 📁 models/             # Modelos de dados
│   ├── 📁 views/              # Lógica de negócio
│   ├── 📁 templates/          # Templates HTML
│   ├── 📁 static/             # Arquivos estáticos
│   ├── 📁 tests/              # Testes automatizados
│   └── 📁 management/         # Comandos personalizados
├── 📁 scripts/                # Scripts de automação
├── 📁 static/                 # Recursos estáticos globais
├── 📁 staticfiles/           # Arquivos coletados (produção)
└── 📄 requirements.txt       # Dependências Python
```

### 🧪 **Testes**

O projeto inclui cobertura abrangente de testes:

```bash
# Executar todos os testes
uv run pytest

# Testes com cobertura detalhada
uv run pytest --cov=core --cov-report=term-missing

# Testes específicos
uv run pytest core/tests/test_models.py
uv run pytest core/tests/test_views.py::TestDashboard
```

---

## 📚 Documentação Técnica

### 🗄️ **Modelos de Dados**

#### **👤 Servidor**
```python
class Servidor(models.Model):
    nome = CharField(max_length=100)
    numero_documento = CharField(max_length=20)
    tipo_funcionario = CharField(choices=TIPO_FUNCIONARIO_CHOICES)
    plantao = CharField(choices=PLANTAO_CHOICES)
    setor = CharField(max_length=100)
    veiculo = CharField(validators=[PlacaValidator])
    ativo = BooleanField(default=True)
```

#### **📝 RegistroAcesso**
```python
class RegistroAcesso(models.Model):
    servidor = ForeignKey(Servidor)
    operador = ForeignKey(User)
    tipo_acesso = CharField(choices=['ENTRADA', 'SAIDA'])
    data_hora = DateTimeField()
    data_hora_saida = DateTimeField(null=True)
    saida_pendente = BooleanField(default=True)
    observacao = TextField(null=True)
    # ... campos de auditoria
```

### 🔌 **APIs Internas**

#### **📊 Dashboard API**
```python
# Endpoint: /dashboard/
# Retorna: Dashboard com estatísticas em tempo real
{
    "total_entradas": 125,
    "total_saidas": 118,
    "pendentes": 7,
    "plantao_atual": "ALFA",
    "registros_ativos": [...]
}
```

#### **🔍 Busca de Servidores**
```python
# Endpoint: /buscar-servidor/
# Parâmetros: q (query string)
# Retorna: Lista de servidores correspondentes
[
    {
        "id": 1,
        "nome": "João Silva",
        "documento": "12345678900",
        "plantao": "ALFA"
    }
]
```

### 🔧 **Middleware Personalizado**

#### **🔐 TrocaSenhaMiddleware**
- Força troca de senha para usuários com senhas temporárias
- Redireciona automaticamente para página de troca
- Permite acesso apenas a rotas essenciais

#### **📝 AuditoriaMiddleware**
- Registra automaticamente todas as ações dos usuários
- Captura IPs, user agents e timestamps
- Armazena em LogAuditoria para rastreabilidade

---

## 🐛 Troubleshooting

### ❗ **Problemas Comuns**

#### **🚫 Erro: "Python não encontrado"**
```bash
# Solução: Instalar Python 3.9+
# Windows: https://python.org/downloads/
# Linux: sudo apt install python3.9 python3.9-venv
```

#### **🔐 Erro: "Permissão negada" (Windows)**
```powershell
# Solução: Executar como Administrador
# Botão direito → "Executar como administrador"
```

#### **🌐 Erro: "Serveo não conecta"**
```bash
# Soluções:
1. Verificar conexão com internet
2. Tentar porta diferente
3. Reiniciar o script start_serveo.py
4. Verificar logs em %PROGRAMFILES%\ControleAcesso\logs\
```