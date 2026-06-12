# Sistema de Controle de Acesso

![Django](https://img.shields.io/badge/Django-4.2%2B-092E20?style=for-the-badge&logo=django)
![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.0-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Production-success?style=for-the-badge)

<div align="center">
  <img src="https://static.djangoproject.com/img/logos/django-logo-negative.svg" alt="Django Logo" width="300"/>
  <h3>Sistema completo de gestão e controle de acesso para servidores penitenciários</h3>
  <p><em>Desenvolvido com Django, Bootstrap e tecnologias modernas para máxima confiabilidade</em></p>
</div>

---

## 📋 Índice

- [🔍 Visão Geral](#-visão-geral)
- [🚀 Tutorial: IIS + Localhost.run](#-tutorial-iis--localhostrun)
- [✨ Funcionalidades](#-funcionalidades)
- [🏗️ Arquitetura](#-arquitetura)
- [🛠 Tecnologias](#-tecnologias)
- [📦 Requisitos](#-requisitos)
- [💻 Instalação](#-instalação)
- [⚙️ Configuração](#-configuração)
- [📖 Guia de Uso](#-guia-de-uso)
- [🎓 Ambiente de Treinamento](#-ambiente-de-treinamento)
- [📊 Dashboard e Relatórios](#-dashboard-e-relatórios)
- [👥 Sistema de Usuários e Perfis](#-sistema-de-usuários-e-perfis)
- [🔐 Segurança](#-segurança)
- [🐛 Sistema de Logging e Debug](#-sistema-de-logging-e-debug)
- [💾 Backup e Restauração](#-backup-e-restauração)
- [🌐 Acesso Remoto](#-acesso-remoto)
- [🔧 Desenvolvimento](#-desenvolvimento)
- [📚 Documentação Técnica](#-documentação-técnica)
- [🐛 Troubleshooting](#-troubleshooting)
- [📋 Changelog](#-changelog)
- [📄 Licença](#-licença)

---

## 🔍 Visão Geral

O **Sistema de Controle de Acesso** é uma aplicação web robusta desenvolvida especificamente para o controle de acesso em ambientes penitenciários. O sistema oferece gestão completa de servidores, registros de entrada/saída, relatórios detalhados, sistema avançado de perfis de usuário e um ambiente de treinamento separado para capacitação.

### 🎯 Principais Características

- **🛡️ Segurança Avançada**: Sistema de perfis hierárquicos, alertas de segurança e logs de auditoria completos
- **📱 Interface Moderna**: Design responsivo com Bootstrap 5, SweetAlert2 e UX otimizada
- **🔌 Funcionamento Offline**: Operação completa sem conexão à internet
- **🎓 Ambiente de Treinamento**: Área isolada para capacitação com tutoriais em vídeo
- **📊 Relatórios Inteligentes**: Exportação em Excel/PDF e filtros avançados
- **🌐 Acesso na Rede Local**: Deploy no IIS com acesso via IP da máquina
- **🔍 Sistema de Debug**: Logging avançado com captura de erros detalhada
- **⚙️ Configuração Inteligente**: SECRET_KEY automática, configuração via .env e comandos personalizados

> 📋 **[Ver Histórico Completo de Mudanças](docs/CHANGELOG.md)** - Todas as versões, melhorias e novidades detalhadas

---

## 🚀 Tutorial: IIS no Windows

### 📝 **Configuração para Produção Local**

Para configurar o sistema no **IIS** do Windows (ambiente `.venv`, HttpPlatformHandler, rede local):

📖 **[Tutorial IIS — Windows](docs/TUTORIAL_IIS.md)**

Este tutorial aborda:
- 🔧 Instalação do IIS e HttpPlatformHandler
- 🐍 Ambiente virtual `.venv` com **uv**
- 🔓 Desbloqueio das seções `handlers` e `httpPlatform` (erro 0x80070021)
- ⚙️ Configuração do `web.config` e variáveis `.env`
- 🔒 Permissões e troubleshooting

---

## ✨ Funcionalidades

### 👥 **Sistema de Usuários e Perfis**
- **4 Tipos de Perfil**: Administrador, Staff, Operador e Visualização
- **Controle Granular**: Permissões específicas por tipo de usuário
- **Senhas Inteligentes**: Geração automática no padrão `usuario@1234`
- **Senhas Sempre Visíveis**: Usuários de visualização têm senhas sempre disponíveis
- **Alertas de Segurança**: Avisos especiais para administradores ao fazer inclusões
- **Gestão Simplificada**: Interface intuitiva para criação e edição de usuários

### 📝 **Controle de Acesso de Servidores**
- **Registro de Entrada/Saída**: Interface intuitiva com validações avançadas
- **Gestão de Plantões**: Organização por turnos (ALFA, BRAVO, CHARLIE, DELTA)
- **Tipos de Funcionário**: Categorização (Plantonista, Expediente, Visitante, Terceirizado)
- **Controle de Veículos**: Validação automática de placas no formato Mercosul
- **Saídas Definitivas**: Processo específico para registros de egresso
- **Edição Completa**: Sistema de edição com justificativas obrigatórias e auditoria

### 🔐 **Segurança e Auditoria**
- **Logs Detalhados**: Captura completa de todas as ações do sistema
- **Middleware de Segurança**: Interceptação e logging de erros automático
- **Páginas de Erro Personalizadas**: Interface amigável com informações técnicas
- **Controle de Sessões**: Timeout automático e validação de permissões
- **Alertas Contextuais**: Avisos específicos baseados no perfil do usuário

### 📊 **Dashboard e Monitoramento**
- **Painel em Tempo Real**: Visualização instantânea de entradas, saídas e pendências
- **Cards Informativos**: Totalizadores com cores intuitivas e badges
- **Lista Dinâmica**: Registros ordenados por horário com ações contextuais
- **Filtros Avançados**: Busca por plantão, tipo de funcionário e status
- **Menu Contextual**: Ações rápidas com clique direito
- **Limpeza Inteligente**: Função para reset do plantão com preservação de pendências

### 📈 **Relatórios e Exportação**
- **Exportação Excel**: Planilhas formatadas com dados completos e filtros
- **Histórico Completo**: Consulta de todos os registros com rastreabilidade
- **Relatórios por Plantão**: Dados específicos de cada turno
- **Busca Avançada**: Filtros combinados por múltiplos critérios
- **Relatórios de Faltas**: Geração automática de PDFs de controle

### 🎓 **Ambiente de Treinamento**
- **🔒 Isolamento Total**: Dados completamente separados do sistema principal
- **📚 Tutoriais Integrados**: Vídeos explicativos organizados por categoria
- **🎯 Dados Realísticos**: Simulações próximas do ambiente real
- **🔄 Reset Completo**: Limpeza fácil para recomeçar treinamentos
- **✅ Funcionalidades Idênticas**: Todas as operações disponíveis para prática

### 🔧 **Administração e Manutenção**
- **Gestão de Servidores**: CRUD completo com validações e auditoria
- **Importação em Massa**: Upload de planilhas Excel para cadastro automático
- **Sistema de Backup**: Scripts automáticos de backup e restauração
- **Limpeza de Dados**: Ferramentas para manutenção da base de dados
- **Atualização Automática**: Scripts de atualização via Git com logs; deploy imediato multi-unidade via [GitHub Actions](docs/DEPLOY_CI.md)

---

## 🏗️ Arquitetura

O sistema segue princípios de **Clean Architecture**, **SOLID** e **modularização**:

### 🎯 **Arquitetura Modular Completa**

```
core/
├── 📁 views/                    # ARQUITETURA MODULAR
│   ├── __init__.py             # Hub central de compatibilidade
│   ├── base_views.py           # 🏠 Views básicas (welcome, home)
│   ├── servidor_views.py       # 👥 CRUD completo de servidores
│   ├── registro_views.py       # 📝 Sistema de registros de produção
│   ├── user_views.py          # 🔐 Gerenciamento de usuários
│   ├── relatorio_views.py     # 📊 Histórico e relatórios
│   └── treinamento_views.py   # 🎓 Ambiente de treinamento
├── 📁 models.py                 # Modelos de dados organizados
├── 📁 utils.py                  # Funções auxiliares centralizadas
├── 📁 decorators.py            # Decoradores de permissão
├── 📁 middleware.py            # Middleware de segurança
├── 📁 forms.py                 # Formulários Django
└── 📁 templates/               # Templates responsivos
```

### 🏗️ **Princípios Aplicados**

#### ✅ **SOLID Principles**
- **S** - Single Responsibility: Cada módulo tem responsabilidade única
- **O** - Open/Closed: Extensível sem modificar código existente  
- **L** - Liskov Substitution: Módulos intercambiáveis
- **I** - Interface Segregation: Interfaces específicas por módulo
- **D** - Dependency Inversion: Dependências abstraídas

#### 🧩 **Clean Architecture**
- **Separação de Responsabilidades**: Views organizadas por domínio
- **Independência de Frameworks**: Lógica de negócio isolada
- **Testabilidade**: Módulos independentes facilitam testes
- **Manutenibilidade**: Código fácil de entender e modificar

### 📊 **Estrutura de Views (44 views organizadas)**

| Módulo | Views | Responsabilidade |
|--------|-------|------------------|
| `base_views.py` | 2 | Interface básica (welcome, home) |
| `servidor_views.py` | 9 | CRUD servidores + importação |
| `registro_views.py` | 12 | Sistema registros produção |
| `user_views.py` | 6 | Gestão usuários e perfis |
| `relatorio_views.py` | 1 | Histórico e relatórios |
| `treinamento_views.py` | 14 | Ambiente treinamento + auxiliares |

### 🔄 **Benefícios da Arquitetura**

- **🔧 Manutenibilidade**: Código organizado e fácil de entender
- **📈 Escalabilidade**: Fácil adicionar novas funcionalidades  
- **🧪 Testabilidade**: Módulos independentes para testes unitários
- **👥 Colaboração**: Equipes podem trabalhar em paralelo
- **🔍 Debugabilidade**: Erros mais fáceis de localizar e corrigir
- **📚 Legibilidade**: Estrutura clara e bem documentada

### 🌐 **Camadas do Sistema**

```
🎯 Presentation Layer (Templates + Static)
├── Bootstrap 5 + SweetAlert2 + JavaScript ES6+
├── Templates responsivos e acessíveis
└── Interface moderna e intuitiva

🧠 Business Logic Layer (Views Modulares)
├── base_views: Funcionalidades básicas
├── servidor_views: Lógica de servidores  
├── registro_views: Controle de acesso
├── user_views: Gestão de usuários
├── relatorio_views: Relatórios e histórico
└── treinamento_views: Ambiente isolado

🔧 Service Layer (Utils + Decorators)
├── Funções auxiliares centralizadas
├── Decoradores de permissão
├── Middleware de segurança
└── Validadores customizados

💾 Data Layer (Models + Database)
├── Models Django bem estruturados
├── SQLite para portabilidade máxima
├── Migrações versionadas
└── Auditoria completa
```

---

## 🛠 Tecnologias

### 💾 **Backend**
- **Django 4.2+**: Framework web robusto e seguro
- **Python 3.9+**: Linguagem de programação moderna
- **SQLite**: Banco de dados embarcado para máxima portabilidade
- **UV**: Gerenciador moderno de dependências e ambientes virtuais

### 🎨 **Frontend**
- **Bootstrap 5**: Framework CSS moderno e responsivo
- **SweetAlert2**: Alertas e modais elegantes
- **Bootstrap Icons**: Biblioteca completa de ícones
- **JavaScript ES6+**: Interações dinâmicas e validações

### 🔧 **Ferramentas e Bibliotecas**
```python
Django>=4.2.0          # Framework web principal
django-bootstrap5       # Integração Bootstrap
pandas>=2.0.0          # Manipulação de dados
reportlab>=4.0.4       # Geração de PDFs
openpyxl>=3.1.0        # Manipulação de Excel
python-dotenv>=1.0.0   # Gestão de variáveis de ambiente
requests>=2.31.0       # Requisições HTTP
whitenoise             # Servir arquivos estáticos
pytz                   # Manipulação de timezones
```

### 🛡️ **Segurança e Logging**
- **Middleware Personalizado**: Captura automática de erros
- **Logging Estruturado**: Arquivos separados por tipo de log
- **Handlers de Erro**: Páginas 500 personalizadas com debug
- **Validação Avançada**: Validadores customizados para dados

---

## 📦 Requisitos

### 🖥️ **Sistema**
- **Windows 10/11** ou **Linux** (Ubuntu 20.04+)
- **2GB RAM** mínimo (4GB recomendado)
- **1GB espaço livre** em disco
- **Acesso Administrator** (apenas para instalação)

### 🐍 **Python e Dependências**
- **Python 3.9+** com pip
- **UV** (gerenciador moderno - instalado automaticamente)
- **Git** (para atualizações automáticas)

---

## 💻 Instalação

### 🚀 **Instalação com UV (Recomendada)**

1. **Instale o UV (se não tiver)**:
```bash
# Linux/Mac
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

2. **Clone e configure o projeto**:
```bash
# Clone o repositório
git clone https://github.com/A-Assuncao/controle-acesso-PAMC.git
cd controle-acesso-PAMC

# Crie ambiente virtual com UV
uv venv

# Ative o ambiente virtual
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Instale dependências
uv pip install -r requirements.txt

# Configure banco de dados
uv run python manage.py migrate

# Crie superusuário
uv run python manage.py createsuperuser

# Colete arquivos estáticos
uv run python manage.py collectstatic --noinput

# Inicie o servidor
uv run python manage.py runserver
```

### ⚙️ **O que a instalação configura:**
- ✅ Ambiente virtual isolado com UV
- ✅ Banco de dados SQLite configurado
- ✅ Arquivos estáticos coletados
- ✅ Sistema de logging configurado
- ✅ Middleware de segurança ativo
- ✅ Páginas de erro personalizadas

---

## ⚙️ Configuração

### 🔐 **Configuração de Ambiente Inteligente**

O sistema possui **configuração automática** de ambiente com fallback inteligente:

#### **📋 Configuração Rápida (Opcional)**
```bash
# 1. Copie o arquivo de exemplo
copy .env.example .env

# 2. Para desenvolvimento: funciona sem configuração!
# Para produção: configure as variáveis críticas
```

#### **⚡ SECRET_KEY Automática**
- **🚀 Desenvolvimento:** Gera automaticamente via `get_random_secret_key()`  
- **🔒 Produção:** Use chave fixa no `.env` para persistência de sessions

#### **🛠️ Comando de Gerenciamento da SECRET_KEY**
```bash
# Verificar status atual
python manage.py check_secret_key

# Ver informações detalhadas
python manage.py check_secret_key --show-current

# Gerar nova chave para produção
python manage.py check_secret_key --generate
```

#### **📝 Arquivo .env Completo (Produção)**
```env
# SEGURANÇA
DJANGO_SECRET_KEY=sua-chave-gerada-pelo-comando
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,seu-dominio.com

# SESSÃO (14400 = 4 horas)
SESSION_COOKIE_AGE=14400
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# LOCALIZAÇÃO
TIME_ZONE=America/Manaus
LANGUAGE_CODE=pt-br

# INTEGRAÇÃO CANAIMÉ
CANAIME_LOGIN_URL=https://canaime.com.br/sgp2rr/login/login_principal.php
CANAIME_AREAS_URL=https://canaime.com.br/sgp2rr/areas/unidades/index.php

# LOGS E MONITORAMENTO
LOGS_DIR=logs
LOG_LEVEL=INFO
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/seu-webhook

# APLICAÇÃO
UNIDADE_PRISIONAL=Centro de Detenção Provisória de Manaus
HTTP_PLATFORM_PORT=8000
```

> 📖 **Guia Detalhado:** Consulte [`CONFIGURACAO_AMBIENTE.md`](docs/CONFIGURACAO_AMBIENTE.md) para configuração completa

### 📁 **Estrutura de Diretórios**

O sistema cria automaticamente as seguintes pastas:

```
controle-acesso-PAMC/
├── 📁 logs/                   # Arquivos de log
│   ├── django_errors.log     # Erros do sistema
│   └── debug.log             # Logs de debug
├── 📁 docs/                  # Documentação (CHANGELOG, guias, tutoriais)
│   └── 📄 TUTORIAL_IIS.md
├── 📁 update/                # Scripts de atualização
│   ├── 📄 update.bat         # Script Windows
│   └── 📄 AtualizarControleAcesso.xml
└── 📁 static/               # Arquivos estáticos
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
Dashboard → Clique Direito no Registro → Editar → Inserir Justificativa → Salvar
```

#### **4. Relatórios**
```
Menu → Histórico → Aplicar Filtros → Exportar Excel/PDF
```

### 🎯 **Recursos Avançados**

- **Menu Contextual**: Clique direito nos registros para ações rápidas
- **Busca Inteligente**: Digite nome, documento ou placa para busca automática
- **Filtros Dinâmicos**: Combine múltiplos critérios para relatórios específicos
- **Alertas Contextuais**: Avisos específicos baseados no perfil do usuário
- **Auto-save**: Dados salvos automaticamente para evitar perdas

---

## 🎓 Ambiente de Treinamento

O sistema inclui um **ambiente de treinamento completamente isolado** para capacitação de novos usuários.

### 🌟 **Características**

- **🔒 Isolamento Total**: Dados separados do sistema principal
- **📚 Tutoriais Integrados**: Vídeos explicativos para cada funcionalidade
- **🎯 Dados Realísticos**: Simulações próximas do ambiente real
- **🔄 Reset Completo**: Limpeza fácil para recomeçar treinamentos
- **✅ Funcionalidades Idênticas**: Todas as operações disponíveis para prática

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
│  📋 Lista de Registros com Menu Contextual:                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Nome           │ Entrada │ Status    │ Ações          │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │ João Silva     │ 08:00   │ 🔴 Pendente│ [Menu Context] │   │
│  │ Maria Santos   │ 08:15   │ ✅ Saiu    │ [Menu Context] │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 📋 **Relatórios Disponíveis**

#### **📊 Histórico Completo**
- Todos os registros com filtros avançados
- Exportação em Excel com formatação profissional
- Busca por período, plantão, servidor ou status
- Tags de alteração (ORIGINAL, EDITADO, EXCLUÍDO)

#### **📈 Relatório de Plantão**
- Dados específicos de cada turno
- Estatísticas de entrada/saída
- Identificação de pendências
- Resumo executivo automático

#### **🔍 Relatórios de Faltas**
- Geração automática de PDFs
- Listagem de ISVs presentes
- Controle de permutas/reposição
- Exportação para análise

---

## 👥 Sistema de Usuários e Perfis

### 🎭 **Tipos de Perfil**

O sistema possui 4 tipos de perfil com permissões específicas:

#### **🔑 Administrador (is_superuser=True)**
- **Acesso Total**: Todas as funcionalidades do sistema
- **Alertas de Segurança**: Avisos ao fazer inclusões operacionais
- **Gestão Completa**: Usuários, servidores, configurações
- **Acesso Admin**: Interface administrativa do Django

#### **👤 Staff**
- **Gestão de Usuários**: Criar, editar e gerenciar usuários
- **Relatórios Completos**: Acesso a histórico e exportações
- **Configurações**: Acesso a funcionalidades administrativas
- **Dashboard Completo**: Todas as operações do dashboard

#### **🔧 Operador (Padrão)**
- **Dashboard Completo**: Registrar entradas/saídas
- **Edição de Registros**: Com justificativas obrigatórias
- **Exclusão de Registros**: Com justificativas obrigatórias
- **Limpeza de Dashboard**: Reset do plantão atual
- **Relatórios**: Visualização e exportação

#### **👁️ Visualização**
- **Apenas Visualização**: Não pode registrar entradas
- **Retirar Faltas**: Única ação permitida
- **Exportar Excel**: Relatórios somente
- **Senha Sempre Visível**: Para facilitar acesso
- **Sem Gestão**: Não acessa servidores ou configurações

### 🔐 **Gestão de Senhas**

#### **Padrão de Senhas Temporárias**
- **Formato**: `usuario@1234` (números aleatórios)
- **Exemplos**: `joao@7392`, `maria.silva@1847`, `admin@5629`
- **Troca Obrigatória**: Para todos exceto visualização

#### **Usuários de Visualização**
- **Senha Sempre Visível**: Na lista de usuários
- **Sem Troca Obrigatória**: Podem usar a senha indefinidamente
- **Geração Automática**: Nova senha quando necessário
- **Fácil Acesso**: Para facilitar uso operacional

### 🎨 **Interface de Gestão**

#### **Lista de Usuários**
- **Badges Coloridos**: Identificação visual do tipo
- **Status da Senha**: Temporária/Definitiva/Sempre Visível
- **Ações Rápidas**: Redefinir senha, editar, ativar/desativar
- **Filtros**: Por tipo de usuário e status

#### **Criação de Usuários**
- **Seleção de Tipo**: Radio buttons com descrições
- **Operador Pré-selecionado**: Tipo padrão
- **Validações**: Nome completo obrigatório
- **Feedback**: Mensagens claras sobre ações realizadas

---

## 🔐 Segurança

### 🛡️ **Camadas de Segurança**

#### **🔑 Autenticação Robusta**
- Sistema robusto de login/logout
- Senhas com validação avançada
- Senhas temporárias para novos usuários
- Controle de sessões com timeout automático

#### **🚪 Autorização Hierárquica**
- 4 níveis de permissão bem definidos
- Middleware de controle de acesso
- Decorators específicos por funcionalidade
- Proteção de rotas sensíveis

#### **⚠️ Alertas de Segurança**
- **Administradores**: Avisos ao fazer inclusões operacionais
- **SweetAlert2**: Interface elegante para confirmações
- **Contextuais**: Mensagens específicas por situação
- **Preventivos**: Evitam ações não recomendadas

#### **📝 Auditoria Completa**
- Log completo de todas as ações
- Rastreamento de alterações com justificativas
- Histórico imutável de operações
- Identificação de usuários responsáveis

### 🔒 **Validações e Proteções**

- **CSRF Protection**: Proteção contra ataques cross-site
- **XSS Prevention**: Sanitização de entradas de usuário
- **SQL Injection**: ORM Django para consultas seguras
- **Secure Headers**: Cabeçalhos de segurança configurados
- **Session Security**: Cookies seguros e validação contínua

---

## 🐛 Sistema de Logging e Debug

### 📊 **Sistema de Logging Avançado**

#### **📁 Arquivos de Log**
```
logs/
├── django_errors.log    # Erros críticos
└── debug.log           # Informações detalhadas
```

#### **🔍 Tipos de Log**
- **ERROR**: Erros críticos que afetam funcionamento
- **INFO**: Informações gerais de funcionamento
- **DEBUG**: Detalhes técnicos para troubleshooting
- **WARNING**: Avisos que não impedem funcionamento

### 🚨 **Páginas de Erro Personalizadas**

#### **Erro 500 - Servidor Interno**
- **Interface Amigável**: Página elegante com Bootstrap
- **Informações Técnicas**: Traceback completo para desenvolvedores
- **Botão Copiar**: Copia erro para área de transferência
- **Informações da Requisição**: Dados completos para debug
- **Logging Automático**: Erro salvo automaticamente nos logs

#### **Middleware de Captura**
- **ErrorLoggingMiddleware**: Captura todos os erros automaticamente
- **Informações Detalhadas**: URL, usuário, IP, user-agent
- **Traceback Completo**: Stack trace para identificar origem
- **Filtragem de Senhas**: Remove dados sensíveis dos logs

### 🔧 **Ferramentas de Debug**

#### **Decorator @log_errors**
```python
@log_errors  # Captura erros específicos da view
@login_required
def minha_view(request):
    # Sua lógica aqui
```

#### **Logging Estruturado**
```python
import logging
logger = logging.getLogger('core')

logger.info("Operação realizada com sucesso")
logger.error("Erro crítico detectado")
logger.debug("Informação técnica detalhada")
```

### 📈 **Monitoramento**

- **Logs Rotativos**: Arquivos organizados por data
- **Alertas Automáticos**: Notificações para erros críticos
- **Relatórios de Erro**: Análise periódica de problemas
- **Performance**: Monitoring de tempo de resposta

---

## 💾 Backup e Restauração

### 🔄 **Backup Automático**

#### **Script de Atualização (update.bat / update_app.bat)**
```batch
# update/update.bat     — manual (pode pedir UAC) ou flags -NoElevate / -SemGit
# update_app.bat        — raiz do projeto; tarefa 00:00, GitHub Actions (sem UAC)
# Funcionalidades:
- ✅ Verificação de internet
- ✅ Git pull automático
- ✅ Detecção de mudanças
- ✅ Aplicação de migrações
- ✅ Logs em logs\update.log
- ✅ Tratamento de erros
```

**Deploy imediato (PAMC + CPBV + CPFBV):** após `git push main`, runners self-hosted executam `update_app.bat` em cada unidade. Ver [docs/DEPLOY_CI.md](docs/DEPLOY_CI.md).

#### **Backup Manual**
```bash
# Via comando Django
uv run python manage.py dumpdata --indent 2 > backup_manual.json

# Via cópia direta do SQLite
cp db.sqlite3 backup_db_$(date +%Y%m%d).sqlite3
```

### 🔄 **Restauração**

```bash
# Método 1: Via Django loaddata
uv run python manage.py loaddata backup_manual.json

# Método 2: Substituição direta do banco
cp backup_db_20241215.sqlite3 db.sqlite3
```

### ☁️ **Configurações Avançadas**

```env
# No arquivo .env
BACKUP_RETENTION_DAYS=30
BACKUP_CLOUD_PROVIDER=local
AUTO_BACKUP_ENABLED=true
```

---

## 🌐 Acesso na Rede Local

Com o IIS configurado conforme o [Tutorial IIS](docs/TUTORIAL_IIS.md):

1. Descubra o IP da máquina: `ipconfig`
2. Inclua o IP em `DJANGO_ALLOWED_HOSTS` no `.env`
3. Acesse de outro dispositivo na mesma rede: `http://192.168.x.x`

Para acesso externo à internet, use VPN ou infraestrutura corporativa aprovada pela instituição.

---

## 🔧 Desenvolvimento

### 🛠️ **Configuração do Ambiente de Desenvolvimento**

```bash
# 1. Clone e configure
git clone https://github.com/A-Assuncao/controle-acesso-PAMC.git
cd controle-acesso-PAMC

# 2. Configure UV (gerenciador moderno)
curl -LsSf https://astral.sh/uv/install.sh | sh  # Linux/Mac
# ou
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows

# 3. Crie e ative ambiente virtual
uv venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# 4. Instale dependências de desenvolvimento
uv pip install -r requirements.txt
uv pip install pytest pytest-django black ruff mypy

# 5. Configure banco de desenvolvimento
uv run python manage.py migrate
uv run python manage.py createsuperuser

# 6. Execute testes
uv run pytest

# 7. Inicie servidor de desenvolvimento
uv run python manage.py runserver
```

### 📋 **Comandos Úteis**

#### **🔐 Comandos de Gerenciamento Personalizados**

```bash
# 🔑 SECRET_KEY - Comando personalizado para gerenciar chaves
python manage.py check_secret_key              # Status atual
python manage.py check_secret_key --show-current  # Informações detalhadas
python manage.py check_secret_key --generate    # Gerar nova chave para produção

# 👥 GRUPOS - Configurar grupos e permissões
python manage.py setup_groups                   # Criar grupos de administradores
```

#### **🧪 Desenvolvimento e Testes**

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

### 🏗️ **Estrutura do Projeto Atualizada**

```
controle-acesso-PAMC/
├── 📁 core/                    # Aplicação principal
│   ├── 📁 models.py           # Modelos com perfis de usuário
│   ├── 📁 views.py            # Views com logging avançado
│   ├── 📁 middleware.py       # Middleware de segurança
│   ├── 📁 decorators.py       # Decorators de permissão
│   ├── 📁 templates/          # Templates com SweetAlert2
│   ├── 📁 static/             # JS com funcionalidades avançadas
│   └── 📁 management/         # Comandos personalizados
├── 📁 docs/                   # Documentação
│   ├── 📄 TUTORIAL_IIS.md
│   ├── 📄 CONFIGURACAO_AMBIENTE.md    # Guia completo de configuração
│   ├── 📄 CHANGELOG.md              # Histórico de mudanças e versões
│   ├── 📄 ADMIN_MELHORIAS.md        # Melhorias do admin
│   └── 📄 GUIA_INSTALACAO_ADMIN.md  # Guia de instalação do admin
├── 📁 update/                 # Scripts de atualização
│   ├── 📄 update.bat         # Script Windows
│   └── 📄 AtualizarControleAcesso.xml
├── 📁 logs/                   # Arquivos de log
│   ├── 📄 django_errors.log  # Erros do sistema
│   └── 📄 debug.log          # Logs de debug
└── 📄 requirements.txt       # Dependências atualizadas
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
uv run pytest core/tests/test_security.py
```

---

## 📚 Documentação Técnica

### 🗄️ **Modelos de Dados Atualizados**

#### **👤 PerfilUsuario**
```python
class PerfilUsuario(models.Model):
    TIPO_USUARIO_CHOICES = [
        ('OPERADOR', 'Operador'),
        ('VISUALIZACAO', 'Visualização'),
        ('STAFF', 'Staff'),
        ('ADMIN', 'Administrador'),
    ]
    
    usuario = OneToOneField(User, related_name='perfil')
    precisa_trocar_senha = BooleanField(default=False)
    senha_temporaria = CharField(max_length=50)
    tipo_usuario = CharField(choices=TIPO_USUARIO_CHOICES)
    
    # Métodos de permissão
    def pode_registrar_acesso(self): ...
    def pode_excluir_registros(self): ...
    def pode_gerenciar_servidores(self): ...
```

#### **📝 RegistroAcesso (Melhorado)**
```python
class RegistroAcesso(models.Model):
    STATUS_ALTERACAO_CHOICES = [
        ('ORIGINAL', 'Original'),
        ('EDITADO', 'Editado'),
        ('EXCLUIDO', 'Excluído'),
    ]
    
    servidor = ForeignKey(Servidor)
    operador = ForeignKey(User)
    # ... campos existentes ...
    status_alteracao = CharField(choices=STATUS_ALTERACAO_CHOICES)
    justificativa = TextField()
    registro_original = ForeignKey('self')
```

### 🔌 **APIs Internas Atualizadas**

#### **📊 Dashboard API**
```python
# Endpoint: /registros-plantao/
# Retorna: Dashboard com estatísticas em tempo real
{
    "status": "success",
    "total_entradas": 125,
    "total_saidas": 118,
    "pendentes": 7,
    "registros": [...],
    "estatisticas": {...}
}
```

#### **👥 Gestão de Usuários API**
```python
# Endpoint: /usuarios/criar/
# Dados: tipo_usuario, first_name, last_name, username
# Retorna: Usuário criado com senha temporária
{
    "status": "success",
    "message": "Usuário criado com sucesso",
    "senha_temporaria": "usuario@1234"
}
```

### 🔧 **Middleware Personalizado Atualizado**

#### **🔐 TrocaSenhaMiddleware**
- Força troca de senha para usuários com senhas temporárias
- Exceção para usuários de visualização
- Redireciona automaticamente para página de troca
- Permite acesso apenas a rotas essenciais

#### **🐛 ErrorLoggingMiddleware**
- Captura automaticamente todos os erros
- Registra informações detalhadas da requisição
- Filtra dados sensíveis (senhas) dos logs
- Integra com sistema de logging estruturado

### 🎨 **Decorators de Permissão**

```python
@pode_registrar_acesso      # Permite registrar entrada/saída
@pode_excluir_registros     # Permite excluir registros
@pode_gerenciar_servidores  # Permite acessar gestão de servidores
@pode_limpar_dashboard      # Permite limpar planilha
@pode_saida_definitiva      # Permite registrar saídas definitivas
```

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

#### **🐛 Erro 500 - Servidor Interno**
```bash
# Soluções:
1. Verificar logs em logs/django_errors.log
2. Ativar DEBUG=True no settings.py (desenvolvimento)
3. Verificar permissões de escrita na pasta logs/
4. Executar: uv run python manage.py check
```

#### **👥 Erro: "Perfil de usuário não encontrado"**
```bash
# Solução: Executar comando de criação de perfis
uv run python manage.py shell -c "
from django.contrib.auth.models import User
from core.models import PerfilUsuario
for user in User.objects.filter(perfil__isnull=True):
    PerfilUsuario.objects.create(usuario=user, tipo_usuario='OPERADOR')
"
```

#### **🔑 Problemas com SECRET_KEY**
```bash
# ✅ SECRET_KEY sendo regenerada a cada restart (desenvolvimento)
# Isso é normal! Para fixar uma chave:
python manage.py check_secret_key --generate
# Copie a chave gerada para o .env

# ❌ Sessions invalidadas após restart
# Solução: Defina DJANGO_SECRET_KEY no .env
echo "DJANGO_SECRET_KEY=sua-chave-aqui" >> .env

# 🔍 Verificar se a chave está sendo lida do .env
python manage.py check_secret_key --show-current
```

#### **🌐 Erro 0x80070021 no IIS (handlers bloqueados)**
```powershell
# Execute como Administrador:
& "$env:windir\system32\inetsrv\appcmd.exe" unlock config -section:system.webServer/handlers
& "$env:windir\system32\inetsrv\appcmd.exe" unlock config -section:system.webServer/httpPlatform
iisreset
```
Consulte também: [docs/TUTORIAL_IIS.md](docs/TUTORIAL_IIS.md)

### 🔍 **Logs de Debug**

#### **Localização dos Logs**
```
logs/
├── django_errors.log    # Erros críticos
└── debug.log           # Informações detalhadas
```

#### **Como Ler os Logs**
```bash
# Últimos erros
tail -f logs/django_errors.log

# Buscar erro específico
grep "ERROR" logs/django_errors.log | tail -10

# Logs de um usuário específico
grep "usuario_teste" logs/debug.log
```

### 🛠️ **Comandos de Diagnóstico**

```bash
# 🔑 Verificar configuração de SECRET_KEY
python manage.py check_secret_key
python manage.py check_secret_key --show-current

# 🔧 Verificar integridade do sistema
uv run python manage.py check

# 📊 Verificar migrações pendentes
uv run python manage.py showmigrations

# ⚙️ Testar configurações
uv run python manage.py shell -c "from django.conf import settings; print(f'DEBUG: {settings.DEBUG}')"

# 👥 Verificar permissões de usuários
uv run python manage.py shell -c "
from core.models import PerfilUsuario
for p in PerfilUsuario.objects.all():
    print(f'{p.usuario.username}: {p.tipo_usuario}')
"

# 🌍 Verificar variáveis de ambiente
uv run python manage.py shell -c "
import os
vars_importantes = ['DJANGO_SECRET_KEY', 'DJANGO_DEBUG', 'TIME_ZONE']
for var in vars_importantes:
    valor = os.getenv(var, 'NÃO DEFINIDA')
    print(f'{var}: {valor}')
"
```

---

## 📋 Changelog

Para ver todas as mudanças, melhorias e novidades de cada versão, consulte o arquivo **[CHANGELOG.md](docs/CHANGELOG.md)**.

### 🔗 **Versões Recentes**

- **[v3.1.0](docs/CHANGELOG.md#310---2025-01-xx---configuração-inteligente)** - Configuração Inteligente
- **[v3.0.0](docs/CHANGELOG.md#300---2024-12-xx---arquitetura-modular)** - Arquitetura Modular
- **[v2.0.0](docs/CHANGELOG.md#200---2024-11-xx---sistema-avançado)** - Sistema Avançado

> 📖 **Histórico Completo**: O CHANGELOG contém todas as 6 versões principais com mais de 54 commits organizados por funcionalidade.

---

## 📄 Licença

Este projeto está licenciado sob a **Licença MIT** - veja o arquivo [LICENSE](LICENSE) para detalhes.

---

<div align="center">
  <h3>🚀 Sistema de Controle de Acesso PAMC</h3>
  <p><em>Desenvolvido com ❤️ para máxima segurança e eficiência</em></p>
  <p>
    <strong>Versão Atual:</strong> 3.1.0 (Configuração Inteligente) | 
    <strong>Última Atualização:</strong> Janeiro 2025 |
    <strong>Changelog:</strong> <a href="docs/CHANGELOG.md">📋 Ver Mudanças</a>
  </p>
</div>