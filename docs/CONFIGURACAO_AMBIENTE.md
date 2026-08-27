# 🔧 Configuração de Variáveis de Ambiente

Este guia explica como configurar as variáveis de ambiente para o sistema de Controle de Acesso PAMC.

## 📋 **Configuração Inicial**

### 1. Copie o arquivo de exemplo
```bash
copy .env.example .env
```

### 2. Configure as variáveis obrigatórias no arquivo `.env`

## 🔐 **Configurações Críticas de Segurança**

### SECRET_KEY (GERAÇÃO AUTOMÁTICA INTELIGENTE)

O sistema agora usa a função `get_random_secret_key()` do Django para gerar automaticamente uma chave segura quando não há uma definida no ambiente.

**🎯 Vantagens:**
- ✅ **Desenvolvimento:** Funciona imediatamente sem configuração
- ✅ **Segurança:** Sempre gera chaves criptograficamente seguras  
- ✅ **Flexibilidade:** Permite chave fixa em produção
- ✅ **Sem hardcoding:** Elimina chaves inseguras no código

### Configuração da SECRET_KEY
```env
# Opcional para desenvolvimento (será gerada automaticamente)
# DJANGO_SECRET_KEY=sua-chave-secreta-super-forte-aqui

# Para produção, descomente e configure:
DJANGO_SECRET_KEY=sua-chave-secreta-super-forte-aqui
```
> **💡 DESENVOLVIMENTO:** Se não definir, o Django gerará automaticamente uma chave segura  
> **⚠️ PRODUÇÃO:** OBRIGATÓRIO definir uma chave fixa! Gere em https://djecrety.ir/

### DEBUG (OBRIGATÓRIO CONFIGURAR)
```env
# Desenvolvimento
DJANGO_DEBUG=True

# Produção
DJANGO_DEBUG=False
```

### HOSTS PERMITIDOS
```env
# Desenvolvimento
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Produção (substitua pelos seus domínios)
DJANGO_ALLOWED_HOSTS=seu-sistema.pamc.am.gov.br,10.0.0.100
```

Para acesso interno pelo nome da máquina via mDNS, inclua também o nome curto e o domínio
`.local`. Exemplo para a UPRRO:

```env
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,192.168.0.2,uprro,uprro.local
```

Com um binding IIS na porta 80 usando o host `uprro.local`, o endereço fica
`http://uprro.local`, sem precisar informar a porta 3000. Consulte
[INSTALACAO_PRODUCAO.md](INSTALACAO_PRODUCAO.md#acesso-pelo-nome-da-unidade-local).

## 🗄️ **Configuração de Banco de Dados**

### SQLite (padrão - desenvolvimento)
```env
DATABASE_URL=sqlite:///db.sqlite3
```

### PostgreSQL (recomendado para produção)
```env
DATABASE_URL=postgresql://usuario:senha@localhost:5432/controle_acesso
```

### MySQL/MariaDB
```env
DATABASE_URL=mysql://usuario:senha@localhost:3306/controle_acesso
```

## ⏱️ **Configurações de Sessão**

### Tempo de sessão (em segundos)
```env
# 2 horas = 7200 segundos
SESSION_COOKIE_AGE=7200

# 8 horas = 28800 segundos
SESSION_COOKIE_AGE=28800
```

### Segurança de cookies
```env
# Desenvolvimento (HTTP)
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False

# Produção (HTTPS)
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

## 🌐 **Configurações do Sistema Canaimé**

Se você precisar conectar com um sistema Canaimé diferente:

```env
CANAIME_BASE_URL=https://seu-canaime.com.br
CANAIME_LOGIN_URL=https://seu-canaime.com.br/sgp2rr/login/login_principal.php
CANAIME_AREAS_URL=https://seu-canaime.com.br/sgp2rr/areas/unidades/index.php
```

## 📍 **Configurações Regionais**

### Fuso horário
```env
# Amazonas (padrão)
TIME_ZONE=America/Manaus

# Brasília
TIME_ZONE=America/Sao_Paulo

# Acre
TIME_ZONE=America/Rio_Branco
```

### Idioma
```env
LANGUAGE_CODE=pt-br
```

## 📊 **Configurações de Logging**

```env
# Diretório de logs
LOGS_DIR=logs

# Nível de detalhamento
LOG_LEVEL=INFO    # Produção
LOG_LEVEL=DEBUG   # Desenvolvimento/Depuração
```

## 🔔 **Notificações Discord**

Para receber notificações de erros no Discord:

1. Crie um webhook no seu servidor Discord
2. Configure a URL:
```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/seu-webhook-id/seu-token
```

## 🏢 **Configurações Específicas da Unidade**

```env
UNIDADE_PRISIONAL=Centro de Detenção Provisória de Manaus
```

### Modo Staff para cursos (opcional)

O modo de curso adiciona, na lista de usuários, um controle exclusivo para
superusuários promoverem temporariamente todos os usuários não administradores
a Staff. O mesmo controle restaura as permissões anteriores ao final do curso.

```env
COURSE_STAFF_TOGGLE_ENABLED=True
```

A variável é opcional e o padrão é `False`. Instalações que não possuam essa
configuração continuam funcionando normalmente e não exibem o controle. Depois
de alterar o valor, reinicie a aplicação. Apenas superusuários conseguem ver ou
executar a ação, mesmo quando o recurso está habilitado.

## 🖥️ **Configurações do Servidor**

### Porta do servidor
```env
# Porta padrão
HTTP_PLATFORM_PORT=8000

# Porta customizada
HTTP_PLATFORM_PORT=8080
```

## 📁 **Exemplo Completo para Produção**

```env
# SEGURANÇA
DJANGO_SECRET_KEY=django-insecure-&x*4@3+_sua-chave-real-super-forte-aqui
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=controle-acesso.pamc.am.gov.br,10.0.0.100

# BANCO DE DADOS
DATABASE_URL=postgresql://app_user:senha_forte@10.0.0.50:5432/controle_acesso

# SESSÃO
SESSION_COOKIE_AGE=28800
SESSION_COOKIE_SECURE=True  
CSRF_COOKIE_SECURE=True

# LOCALIZAÇÃO
TIME_ZONE=America/Manaus
LANGUAGE_CODE=pt-br

# LOGS
LOG_LEVEL=INFO

# NOTIFICAÇÕES
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123456789/seu-token-aqui

# UNIDADE
UNIDADE_PRISIONAL=Centro de Detenção Provisória de Manaus

# SERVIDOR
HTTP_PLATFORM_PORT=80
```

## 🔍 **Verificação da Configuração**

Para verificar se suas configurações estão funcionando:

1. **Teste básico:**
```bash
python manage.py check
```

2. **Teste de conexão com banco:**
```bash
python manage.py migrate --dry-run
```

3. **Verificar SECRET_KEY gerada automaticamente:**
```bash
# Comando personalizado para verificar a SECRET_KEY
python manage.py check_secret_key

# Ou visualizar detalhes completos
python manage.py check_secret_key --show-current

# Ou gerar uma nova chave para produção
python manage.py check_secret_key --generate
```

4. **Verificar logs:**
   - Verifique se a pasta `logs/` foi criada
   - Execute a aplicação e veja se não há erros nos logs

## 🛠️ **Comando Personalizado para SECRET_KEY**

Foi criado um comando de gerenciamento personalizado para facilitar o trabalho com a SECRET_KEY:

### Verificar status atual
```bash
python manage.py check_secret_key
```

### Ver informações detalhadas
```bash
python manage.py check_secret_key --show-current
```

### Gerar nova chave para produção
```bash
python manage.py check_secret_key --generate
```

**💡 Exemplo de uso:**
1. Em desenvolvimento, rode `python manage.py check_secret_key` para ver se está usando chave automática
2. Para produção, rode `python manage.py check_secret_key --generate` para gerar uma chave
3. Copie a chave gerada para seu arquivo `.env` de produção

## 🆘 **Solução de Problemas**

### Erro: "Secret key not configured"
- **Desenvolvimento:** Esse erro não deve mais ocorrer (chave é gerada automaticamente)
- **Produção:** Verifique se `DJANGO_SECRET_KEY` está definida no `.env`
- Certifique-se que o arquivo `.env` está no diretório raiz do projeto

### Erro: "Database connection failed"
- Verifique a `DATABASE_URL`
- Teste a conexão com o banco separadamente
- Certifique-se que o banco/servidor está rodando

### Erro: "Allowed hosts validation failed"
- Configure `DJANGO_ALLOWED_HOSTS` com o IP/domínio correto
- Em desenvolvimento, use `localhost,127.0.0.1`

### Sessões expirando muito rápido
- Aumente `SESSION_COOKIE_AGE`
- Verifique se `SESSION_SAVE_EVERY_REQUEST=True`

## 📝 **Notas Importantes**

- ⚠️ **Nunca** commite o arquivo `.env` no Git
- 🔄 Reinicie o servidor após alterar o `.env`
- 🔐 Use senhas/chaves fortes em produção
- 📊 Monitor os logs regularmente
- 🔄 Faça backup das configurações de produção
