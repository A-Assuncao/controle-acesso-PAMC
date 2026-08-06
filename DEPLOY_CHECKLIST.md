# Checklist de Deploy - Vercel + Supabase

## ✅ Arquivos Criados

- [x] `vercel.json` - Configuração da Vercel
- [x] `build.sh` - Script de build (collectstatic + migrations)
- [x] `controle_acesso/settings_production.py` - Settings otimizado para produção
- [x] `.env.production.example` - Template de variáveis de ambiente
- [x] `DEPLOY_VERCEL.md` - Documentação completa do deploy
- [x] `requirements.txt` - Adicionado `psycopg2-binary` e `dj-database-url`

## 📋 Próximos Passos

### 1. Criar Conta no Supabase (5 min)
- [ ] Acessar https://supabase.com e fazer login
- [ ] Criar novo projeto
- [ ] Salvar a senha do banco de dados
- [ ] Copiar a Connection String (URI)

### 2. Preparar Repositório (2 min)
- [ ] Fazer push do commit:
  ```bash
  git push origin fix/quality-improvements-2026-06
  ```
- [ ] Ou se preferir fazer merge para main antes:
  ```bash
  git checkout main
  git merge fix/quality-improvements-2026-06
  git push origin main
  ```

### 3. Deploy na Vercel (10 min)
- [ ] Acessar https://vercel.com/new
- [ ] Importar o repositório
- [ ] Configurar:
  - Framework: Other
  - Build Command: `bash build.sh`
  - Output Directory: `staticfiles`
- [ ] Adicionar variáveis de ambiente (ver .env.production.example)
- [ ] Clicar em Deploy

### 4. Executar Migrações (5 min)
- [ ] Após primeiro deploy, executar localmente:
  ```bash
  export DATABASE_URL="sua-connection-string-do-supabase"
  python manage.py migrate
  python manage.py createsuperuser
  ```

### 5. Testar (2 min)
- [ ] Acessar https://seu-projeto.vercel.app/admin/
- [ ] Fazer login com superusuário
- [ ] Verificar se tudo está funcionando

## 🔑 Variáveis de Ambiente Necessárias

Copie de `.env.production.example` e configure na Vercel:

1. `DATABASE_URL` - Connection string do Supabase
2. `DJANGO_SECRET_KEY` - Gerar nova chave
3. `DJANGO_DEBUG` - False
4. `DJANGO_ENVIRONMENT` - production
5. `DJANGO_SETTINGS_MODULE` - controle_acesso.settings_production
6. `DJANGO_ALLOWED_HOSTS` - .vercel.app
7. `UNIDADE_PRISIONAL` - PAMC

## 📊 Planos Gratuitos

- **Vercel**: 100 GB bandwidth/mês ✅
- **Supabase**: 500 MB database + 1 GB storage ✅

## 📚 Documentação Completa

Leia `DEPLOY_VERCEL.md` para instruções detalhadas passo a passo.

## ⚠️ Importante

- A `DJANGO_SECRET_KEY` deve ser diferente da usada em desenvolvimento
- Nunca commite a `DATABASE_URL` ou secrets no repositório
- Configure backups regulares do Supabase
- Monitore o uso de recursos nos dashboards
