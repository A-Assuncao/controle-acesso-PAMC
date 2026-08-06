# Guia de Deploy na Vercel com Supabase

Este guia explica como fazer deploy do sistema de Controle de Acesso PAMC na Vercel usando Supabase como banco de dados PostgreSQL gratuito.

## Pré-requisitos

- Conta na [Vercel](https://vercel.com)
- Conta no [Supabase](https://supabase.com)
- [Vercel CLI](https://vercel.com/cli) instalado (opcional, mas recomendado)

## Passo 1: Configurar o Supabase

1. Acesse [supabase.com](https://supabase.com) e faça login
2. Clique em "New Project"
3. Preencha os dados:
   - **Name**: controle-acesso-pamc (ou nome de sua preferência)
   - **Database Password**: Crie uma senha forte e **salve em local seguro**
   - **Region**: Escolha a região mais próxima (ex: South America - São Paulo)
   - **Pricing Plan**: Free (0$/mês)
4. Aguarde alguns minutos até o projeto ser criado
5. Após criado, vá em **Settings → Database**
6. Copie a **Connection String** no formato "URI" (começa com `postgresql://`)
7. A string terá este formato:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxxxxxxxxxxx.supabase.co:5432/postgres
   ```
8. Substitua `[YOUR-PASSWORD]` pela senha que você criou no passo 3

## Passo 2: Preparar o Repositório

1. Certifique-se de que o projeto está em um repositório Git (GitHub, GitLab ou Bitbucket)
2. Faça commit dos novos arquivos criados:
   ```bash
   git add .
   git commit -m "feat: adiciona configuração para deploy na Vercel"
   git push origin main
   ```

## Passo 3: Deploy na Vercel

### Opção A: Via Interface Web (Recomendado)

1. Acesse [vercel.com/new](https://vercel.com/new)
2. Importe seu repositório Git
3. Configure o projeto:
   - **Framework Preset**: Other
   - **Build Command**: `bash build.sh`
   - **Output Directory**: `staticfiles`
4. Adicione as variáveis de ambiente (clique em "Environment Variables"):

   ```
   DATABASE_URL = postgresql://postgres:[PASSWORD]@db.xxxxx.supabase.co:5432/postgres
   DJANGO_SECRET_KEY = (gere uma chave forte - veja abaixo)
   DJANGO_DEBUG = False
   DJANGO_ENVIRONMENT = production
   DJANGO_ALLOWED_HOSTS = .vercel.app
   DJANGO_SETTINGS_MODULE = controle_acesso.settings_production
   UNIDADE_PRISIONAL = PAMC
   ```

5. Para gerar uma `DJANGO_SECRET_KEY` segura, use:
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

6. Clique em "Deploy"

### Opção B: Via CLI

```bash
# Instalar Vercel CLI (se ainda não tiver)
npm i -g vercel

# Login na Vercel
vercel login

# Deploy
vercel

# Adicionar variáveis de ambiente
vercel env add DATABASE_URL
# Cole a connection string do Supabase quando solicitado

vercel env add DJANGO_SECRET_KEY
# Cole a secret key gerada quando solicitado

vercel env add DJANGO_DEBUG
# Digite: False

vercel env add DJANGO_ENVIRONMENT
# Digite: production

vercel env add DJANGO_ALLOWED_HOSTS
# Digite: .vercel.app

vercel env add DJANGO_SETTINGS_MODULE
# Digite: controle_acesso.settings_production

vercel env add UNIDADE_PRISIONAL
# Digite: PAMC

# Fazer deploy em produção
vercel --prod
```

## Passo 4: Executar Migrações

Após o primeiro deploy, você precisa executar as migrações do Django:

### Opção A: Via Supabase SQL Editor

1. No Supabase, vá em **SQL Editor**
2. Execute o seguinte comando para verificar se o banco está acessível:
   ```sql
   SELECT version();
   ```

### Opção B: Localmente apontando para o Supabase

```bash
# Configure a variável de ambiente localmente
export DATABASE_URL="postgresql://postgres:[PASSWORD]@db.xxxxx.supabase.co:5432/postgres"

# Execute as migrações
python manage.py migrate

# Crie um superusuário
python manage.py createsuperuser
```

## Passo 5: Configurar Arquivos Estáticos

Os arquivos estáticos já são coletados automaticamente durante o build via `build.sh`.

## Passo 6: Acessar o Sistema

1. Após o deploy, a Vercel fornecerá uma URL (ex: `https://seu-projeto.vercel.app`)
2. Acesse `https://seu-projeto.vercel.app/admin/`
3. Faça login com o superusuário criado

## Variáveis de Ambiente Opcionais

Você pode adicionar outras variáveis conforme necessário:

```
EMAIL_HOST_USER = seu-email@gmail.com
EMAIL_HOST_PASSWORD = sua-senha-de-app
DEFAULT_FROM_EMAIL = "Sistema PAMC <seu-email@gmail.com>"
CUSTOM_DOMAINS = seudominio.com,www.seudominio.com
```

## Domínio Personalizado

Para adicionar um domínio próprio:

1. No painel da Vercel, vá em **Settings → Domains**
2. Adicione seu domínio
3. Configure os registros DNS conforme instruções da Vercel
4. Adicione o domínio às variáveis de ambiente:
   - `DJANGO_ALLOWED_HOSTS`: adicione seu domínio
   - `CUSTOM_DOMAINS`: liste seus domínios separados por vírgula

## Monitoramento

- **Logs da Vercel**: Acesse o painel da Vercel → seu projeto → Deployments → clique no deployment → Functions
- **Logs do Supabase**: Acesse o painel do Supabase → Logs

## Troubleshooting

### Erro: "DisallowedHost"
- Verifique se `DJANGO_ALLOWED_HOSTS` inclui `.vercel.app` ou seu domínio personalizado

### Erro: "Could not connect to database"
- Verifique se a `DATABASE_URL` está correta
- Confirme que a senha não contém caracteres especiais que precisam ser URL-encoded

### Migrações não executaram
- Execute `python manage.py migrate` localmente apontando para o banco Supabase
- Ou use o Supabase SQL Editor para executar as migrações manualmente

### Arquivos estáticos não carregam
- Verifique se `whitenoise` está instalado
- Confirme que `STATICFILES_STORAGE` está configurado corretamente

## Custos

- **Vercel Free Plan**: 100 GB bandwidth/mês, serverless functions ilimitadas
- **Supabase Free Plan**: 500 MB database, 1 GB file storage, 2 GB bandwidth/mês

Ambos os planos gratuitos são suficientes para começar!

## Backup Automático

O Supabase Free Plan não inclui backups automáticos. Para fazer backup manual:

1. No Supabase, vá em **Database → Backups**
2. Clique em "Download backup"
3. Ou use `pg_dump` localmente:
   ```bash
   pg_dump "postgresql://postgres:[PASSWORD]@db.xxxxx.supabase.co:5432/postgres" > backup.sql
   ```

## Próximos Passos

- Configure um domínio personalizado
- Configure email (Gmail SMTP ou serviço transacional)
- Configure backups regulares
- Monitore uso de recursos nos painéis Vercel e Supabase
